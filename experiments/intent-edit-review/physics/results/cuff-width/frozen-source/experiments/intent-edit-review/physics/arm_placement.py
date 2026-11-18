"""Place the original sleeve material around the actual canonical proxy arms.

This changes initial XYZ only, after ``improve_initial_placement``. It is not a
physical solve or a contact/fit acceptance. In particular the resulting cloth
can still intersect the body. The original source-reference shell must remain
separate and unchanged.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator

from initial_placement import _array_digest, _fem_harmonic, _json_digest

JOINT_FILE = Path(__file__).with_name("proxy-arm-joints.json")


def _smoothstep(value):
    value = np.clip(value, 0., 1.)
    return value * value * (3. - 2. * value)


def _unit(value):
    length = np.linalg.norm(value, axis=1)
    if np.any(length < 1e-12) or not np.isfinite(length).all():
        raise ValueError("Arm placement has a degenerate moving frame")
    return value / length[:, None]


def _verified_joints(body_path_or_bodydata):
    """Bind the small derived rig record to the actual unchanged collider.

    The packed physics body and the canonical file use the same f32 geometry.
    Comparing their coordinate/index hashes also rejects changed geometry with
    a stale claimed source hash. Runtime does not need the large original OBJ;
    its helper derivation is independently checked by the local test.
    """
    raw = JOINT_FILE.read_bytes()
    record = json.loads(raw)
    if record.get("format") != "canonical-proxy-arm-joints/1":
        raise ValueError("Unsupported canonical arm joint record")
    expected = record["canonical_body"]
    if isinstance(body_path_or_bodydata, (str, Path)):
        body_raw = Path(body_path_or_bodydata).read_bytes()
        if hashlib.sha256(body_raw).hexdigest() != expected["sha256"]:
            raise ValueError("Arm joints do not match this canonical body source")
        body = json.loads(body_raw)
    elif isinstance(body_path_or_bodydata, dict):
        body = body_path_or_bodydata
    else:
        raise ValueError("Expected the canonical body path, asset, or packed body")
    if isinstance(body.get("positions"), str):
        if body.get("source_sha256") != expected["sha256"]:
            raise ValueError("Packed body source differs from the canonical arm rig")
        points = np.frombuffer(base64.b64decode(body["positions"], validate=True), dtype="<f4")
        faces = np.frombuffer(base64.b64decode(body["indices"], validate=True), dtype="<i4")
    else:
        points = np.asarray(body["positions"], dtype="<f4").reshape(-1)
        faces = np.asarray(body["triangles"], dtype="<i4").reshape(-1)
    if (len(points) != expected["vertices"] * 3 or len(faces) != expected["triangles"] * 3
            or hashlib.sha256(points.tobytes()).hexdigest() != expected["positions_f32_sha256"]
            or hashlib.sha256(faces.tobytes()).hexdigest() != expected["triangles_i32_sha256"]):
        raise ValueError("Actual body coordinates/topology differ from the verified canonical arm rig")
    if not np.isfinite(points).all():
        raise ValueError("Body has nonfinite coordinates")
    return record, hashlib.sha256(raw).hexdigest()


def _sleeve_domain(certificate, builder, name, count):
    patch = certificate["patches"][name]
    boundary = []
    for key, reverse in builder.loops[name]:
        q = np.asarray(certificate["segments"][key]["parameter"], dtype=float)
        values = np.asarray(builder.segments[key]["domain"](q), dtype=float)
        if values.shape != (len(q), 2) or not np.isfinite(values).all():
            raise ValueError("Invalid source sleeve boundary (u,theta)")
        if reverse:
            values = values[::-1]
        boundary.extend(values[:-1])
    nb = int(patch["boundary_count"])
    if len(boundary) != nb or len(patch["flat_points"]) != count:
        raise ValueError("Sleeve material domain differs from the source panel")
    domain = _fem_harmonic(np.asarray(patch["flat_points"], dtype=float) / 1000,
                           np.asarray(patch["local_faces"]), np.asarray(boundary))
    if domain[:, 0].min() < -1e-9 or domain[:, 0].max() > 1 + 1e-9:
        raise ValueError("Sleeve FEM longitudinal domain leaves the original tube")
    return domain


def retarget_sleeves(positions, certificate, panels, global_ids, builder,
                     translation, placement_depth, body_path_or_bodydata):
    """Return a source-preserving sleeve seed and explicit initialisation record.

    Reuse the original UV-FEM (u,theta) and tube cross sections, transport them
    along the same-source actual elbow/wrist chain, then blend with the supplied
    seed over u in [0,.25]. The cuff is 25 mm beyond the actual wrist in the
    anatomical wrist-tail direction. Sewn armholes and all nonsleeve XYZ stay
    bit-exact; underarm seam aliases move together. The distal sleeve does not
    inherit the old x-dependent 220 mm forward-placement warp.

    UV, mesh faces, the 15 seam declarations, the body and all input objects
    remain unchanged. This function neither changes nor returns a replacement
    source reference. Callers must retain that original reference separately.
    """
    original = np.asarray(positions, dtype=np.float64)
    raw_ids = np.asarray(global_ids)
    translation = np.asarray(translation, dtype=float)
    if original.ndim != 2 or original.shape[1] != 3 or not np.isfinite(original).all():
        raise ValueError("Initial positions must be finite Nx3 coordinates")
    if raw_ids.ndim != 1 or len(raw_ids) != len(original) or raw_ids.dtype.kind not in "iu":
        raise ValueError("Every initial position needs an integer source global ID")
    if translation.shape != (3,) or not np.isfinite(translation).all():
        raise ValueError("World translation must be a finite 3-vector")
    scale = float(placement_depth["scale"])
    offset, arm_offset = float(placement_depth["offset_m"]), float(placement_depth["arm_offset_m"])
    if not np.isfinite([scale, offset, arm_offset]).all() or scale <= 0:
        raise ValueError("Invalid initial depth-placement transform")
    record, joint_sha = _verified_joints(body_path_or_bodydata)
    before_certificate, before_panels = _json_digest(certificate), _json_digest(panels)
    before_ids = _array_digest(raw_ids, "<i8")
    before_body = (_json_digest(body_path_or_bodydata)
                   if isinstance(body_path_or_bodydata, dict) else None)
    ids = raw_ids.astype(np.int64, copy=False)
    aliases = {}
    for i, gid in enumerate(ids):
        aliases.setdefault(int(gid), []).append(i)
    for group in aliases.values():
        if any(not np.array_equal(original[group[0]], original[i]) for i in group[1:]):
            raise ValueError("Input seam aliases do not share exact positions")
    output = original.copy()
    coverage = np.zeros(len(original), dtype=np.int8)
    sleeve_mask = np.zeros(len(original), dtype=bool)
    cap_mask = np.zeros(len(original), dtype=bool)
    records = []
    grid = np.linspace(0., 1., 513)
    convert = lambda value: np.asarray(value, dtype=float)[:, [0, 2, 1]] * [1, 1, -1] + translation
    for panel in panels:
        name = panel["name"]
        start, count = int(panel["start"]), int(panel["vertices"])
        if start < 0 or count <= 0 or start + count > len(original):
            raise ValueError("Panel range is out of bounds")
        coverage[start:start + count] += 1
        if not name.startswith("sleeve."):
            continue
        if name not in ("sleeve.left", "sleeve.right"):
            raise ValueError("Unsupported source sleeve side")
        side = name.split(".")[1]
        anatomical_side, sign = ("R", -1) if side == "left" else ("L", 1)
        domain = _sleeve_domain(certificate, builder, name, count)
        u, theta = domain.T
        u = np.clip(u, 0., 1.)
        tube = builder.targets["tube." + side]
        old_center = (convert(tube(grid, np.zeros(len(grid))))
                      + convert(tube(grid, np.full(len(grid), np.pi)))) / 2
        old_radial = _unit(convert(tube(grid, np.zeros(len(grid)))) - old_center)
        old_tangent = _unit(np.gradient(old_center, grid, axis=0))
        old_front = _unit(np.cross(old_tangent, old_radial) * sign)
        cap_center = old_center[0].copy()
        cap_center[2] = cap_center[2] * scale + offset + arm_offset * _smoothstep((abs(cap_center[0]) - .25) / .20)
        joints = {key: np.asarray(value["canonical_m"], dtype=float)
                  for key, value in record["joint_coordinates"][anatomical_side].items()}
        if any(value.shape != (3,) or not np.isfinite(value).all() for value in joints.values()):
            raise ValueError("Invalid verified arm joint coordinates")
        wrist_direction = _unit((joints["wrist_tail"] - joints["wrist"])[None])[0]
        control = np.array([cap_center, joints["elbow"], joints["wrist"],
                            joints["wrist"] + .025 * wrist_direction])
        arclength = np.r_[0., np.cumsum(np.linalg.norm(np.diff(control, axis=0), axis=1))]
        if np.any(np.diff(arclength) < 1e-10):
            raise ValueError("Degenerate actual arm placement path")
        knots = arclength / arclength[-1]
        center = PchipInterpolator(knots, control, axis=0)(grid)
        tangent = _unit(np.gradient(center, grid, axis=0))
        front = np.tile([0., 0., 1.], (len(grid), 1))
        front = _unit(front - tangent * np.sum(front * tangent, axis=1)[:, None])
        radial = np.cross(front, tangent) * sign
        sample = lambda value: np.column_stack([np.interp(u, grid, value[:, k]) for k in range(3)])
        relative = convert(tube(u, theta)) - sample(old_center)
        placed = sample(center)
        for old_axis, new_axis in ((old_radial, radial), (old_front, front), (old_tangent, tangent)):
            placed += sample(new_axis) * np.sum(relative * sample(old_axis), axis=1)[:, None]
        blend = _smoothstep(u / .25)
        placed = original[start:start + count] * (1 - blend[:, None]) + placed * blend[:, None]
        nb = int(certificate["patches"][name]["boundary_count"])
        cap_local = np.flatnonzero((np.arange(count) < nb) & (abs(u) < 1e-12))
        if len(cap_local) < 3:
            raise ValueError("Sleeve has no actual sewn armhole boundary")
        placed[cap_local] = original[start + cap_local]
        output[start:start + count] = placed
        sleeve_mask[start:start + count] = True
        cap_mask[start + cap_local] = True
        records.append({"panel": name, "anatomical_side": anatomical_side,
                        "domain_method": "unchanged material UV-metric FEM (u,theta)",
                        "rest_uv_sha256": _array_digest(certificate["patches"][name]["flat_points"], "<f8"),
                        "local_faces_sha256": _array_digest(certificate["patches"][name]["local_faces"], "<i8"),
                        "fixed_armhole_vertices": len(cap_local),
                        "actual_joints_m": {key: value.tolist() for key, value in joints.items()},
                        "control_points_m": control.tolist(), "control_u": knots.tolist(),
                        "target_centerline_length_m": float(np.linalg.norm(np.diff(center, axis=0), axis=1).sum())})
    if np.any(coverage != 1) or len(records) != 2:
        raise ValueError("Panels must cover the complete source mesh with exactly two supported sleeves")
    for group in aliases.values():
        fixed = next((i for i in group if not sleeve_mask[i] or cap_mask[i]), None)
        chosen = group[0] if fixed is None else fixed
        if fixed is None and any(np.linalg.norm(output[i] - output[chosen]) > 2e-12 for i in group):
            raise ValueError("Retargeted underarm seam aliases disagree")
        for i in group:
            output[i] = output[chosen]
    if output[~sleeve_mask].tobytes() != original[~sleeve_mask].tobytes():
        raise ValueError("Arm initialisation changed a nonsleeve panel")
    if output[cap_mask].tobytes() != original[cap_mask].tobytes():
        raise ValueError("Arm initialisation changed a sewn armhole anchor")
    if not np.isfinite(output).all():
        raise ValueError("Arm initialisation produced nonfinite positions")
    if (before_certificate != _json_digest(certificate) or before_panels != _json_digest(panels)
            or before_ids != _array_digest(raw_ids, "<i8")
            or (before_body is not None and before_body != _json_digest(body_path_or_bodydata))):
        raise ValueError("Arm initialisation mutated a source/body input")
    gap = max((float(np.linalg.norm(output[i] - output[group[0]]))
               for group in aliases.values() for i in group), default=0.)
    metadata = {"method": "actual-canonical-arm UV-FEM tube transport/1",
                "role": "initial sleeve XYZ only; not source reference or physical frame",
                "physical_acceptance": "NOT_RUN", "physical_fit": "NOT_RUN",
                "body_contact_acceptance": "NOT_RUN", "self_intersection_acceptance": "NOT_RUN",
                "does_not_replace_source_reference": True,
                "joint_record": JOINT_FILE.name, "joint_record_sha256": joint_sha,
                "original_obj_sha256": record["source_obj"]["sha256"],
                "canonical_body_sha256": record["canonical_body"]["sha256"],
                "canonical_geometry_hashes_verified": True,
                "source_certificate_sha256_before": before_certificate,
                "source_certificate_sha256_after": _json_digest(certificate),
                "panel_declarations_sha256": before_panels, "global_ids_sha256": before_ids,
                "nonsleeve_positions_bit_exact": True, "sewn_armhole_positions_bit_exact": True,
                "max_seam_alias_gap_m": gap,
                "changed_vertices": int(np.any(output != original, axis=1).sum()),
                "max_initialisation_move_m": float(np.linalg.norm(output - original, axis=1).max()),
                "cap_blend_end_u": .25, "cuff_beyond_wrist_m": .025, "panels": records}
    return output, metadata
