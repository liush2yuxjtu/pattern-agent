"""Independent fixed-proxy arm-in-sleeve readback; no placement/solver import.

Virtual opening caps are oracle geometry only. A numerically threaded arm is
not human fit, physical-trajectory acceptance, or a substitute for the existing
zero cloth/body-crossing and strict cloth-self-intersection checks.
"""
from __future__ import annotations

import base64
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[3]
PROXY_METADATA_FILE = Path(__file__).with_name("proxy-arm-joints.json")
TRIANGLE_ORACLE = ROOT / "experiments/oneshot_control/independent_oracle_v2.py"
sys.path.insert(0, str(TRIANGLE_ORACLE.parent))
from independent_oracle_v2 import intersect_pairs

# Same proper-intersection precision as the existing independent frame audit.
# Near-surface anatomical samples are INCONCLUSIVE, never accepted by rounding.
NUMERICAL_M = 1e-6


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _unpack(value, dtype="<f4"):
    return np.frombuffer(base64.b64decode(value, validate=True), dtype=dtype)


@lru_cache(maxsize=2)
def _source_joints(canonical_path, expected_sha):
    """Recompute factual joints from raw source IDs, never saved target XYZ."""
    canonical_raw = Path(canonical_path).read_bytes()
    if _sha(canonical_raw) != expected_sha:
        raise ValueError("Canonical body source SHA differs from this input")
    canonical = json.loads(canonical_raw)
    obj_path = ROOT / "experiments/teagan_sites_studio/app/dist/models/makehuman-base.obj"
    obj_raw = obj_path.read_bytes()
    obj_sha = _sha(obj_raw)
    if obj_sha != canonical["source"]["sourceSHA256"]:
        raise ValueError("Original OBJ differs from canonical body provenance")
    rig_path = ROOT / "web/human-studio/assets/human.json"
    rig_raw = rig_path.read_bytes()
    rig = json.loads(rig_raw)
    provenance_path = ROOT / "web/human-studio/assets/provenance.json"
    provenance_raw = provenance_path.read_bytes()
    rig_provenance = json.loads(provenance_raw)
    if (obj_sha != rig_provenance["sources"]["3dobjs/base.obj"]
            or _sha(rig_raw) != rig_provenance["human_sha256"]):
        raise ValueError("Rig helper IDs are not bound to this original OBJ")
    vertices = np.array([list(map(float, line.split()[1:4]))
                        for line in obj_raw.decode().splitlines() if line.startswith("v ")])
    if len(vertices) != 19158 or len(rig["bones"]) != 163:
        raise ValueError("Unexpected original vertex/rig layout")
    ground = []
    for side, landmark in [("L", "shoulderLeft"), ("R", "shoulderRight")]:
        raw_shoulder = vertices[rig["joints"][f"upperarm01.{side}____head"]].mean(0) * .1
        ground.append(float(canonical["landmarks"][landmark][1]) - raw_shoulder[1])
        if not np.allclose(raw_shoulder[[0, 2]], np.asarray(canonical["landmarks"][landmark])[[0, 2]],
                           atol=2e-8, rtol=0):
            raise ValueError("Canonical source shoulder does not match the raw helper")
    if abs(ground[0] - ground[1]) > 1e-12:
        raise ValueError("Bilateral canonical source grounding disagrees")
    joints, helper_ids = {}, {}
    for side in ["L", "R"]:
        points, side_ids = [], {}
        for label, bone in [("shoulder", "upperarm01"), ("elbow", "lowerarm01"), ("wrist", "wrist")]:
            key = f"{bone}.{side}____head"
            indices = rig["joints"][key]
            points.append(vertices[indices].mean(0) * .1 + [0, ground[0], 0])
            side_ids[label] = indices
        joints[side] = np.asarray(points)
        helper_ids[side] = side_ids
    sources = {
        str(Path(canonical_path).relative_to(ROOT)): expected_sha,
        str(obj_path.relative_to(ROOT)): obj_sha,
        str(rig_path.relative_to(ROOT)): _sha(rig_raw),
        str(provenance_path.relative_to(ROOT)): _sha(provenance_raw),
    }
    return canonical, joints, {
        "canonical_sha256": expected_sha, "original_obj_sha256": obj_sha,
        "rig_asset_sha256": _sha(rig_raw), "rig_provenance_sha256": _sha(provenance_raw),
        "raw_dm_to_m_scale": .1, "canonical_ground_translation_m": [0, ground[0], 0],
        "joint_helper_original_obj_ids": helper_ids, "source_hashes": sources,
        "joint_method": "Mean original OBJ helper IDs, scale .1, canonical bilateral landmark ground",
        "coordinates_not_read_from_proxy_metadata": True,
        "human_studio_morphed_coordinates_not_used": True,
    }


def _bind_proxy_provenance(provenance):
    """Check the shared record's provenance; deliberately ignore its joint XYZ."""
    raw = PROXY_METADATA_FILE.read_bytes()
    record = json.loads(raw)
    if (record.get("format") != "canonical-proxy-arm-joints/1"
            or record["canonical_body"]["sha256"] != provenance["canonical_sha256"]
            or record["source_obj"]["sha256"] != provenance["original_obj_sha256"]
            or record["rig"]["sha256"] != provenance["rig_asset_sha256"]
            or record["rig"]["provenance_sha256"] != provenance["rig_provenance_sha256"]):
        raise ValueError("Proxy joint metadata source provenance disagrees with raw anatomy")
    transform = record["transform"]
    if (transform["raw_obj_to_canonical_m_scale"] != .1
            or not np.allclose(transform["raw_obj_to_canonical_translation_m"],
                               provenance["canonical_ground_translation_m"], atol=1e-12, rtol=0)):
        raise ValueError("Proxy joint metadata unit/ground provenance disagrees")
    for side, side_ids in provenance["joint_helper_original_obj_ids"].items():
        for name, indices in side_ids.items():
            if record["joint_coordinates"][side][name]["original_obj_vertex_ids"] != indices:
                raise ValueError("Proxy metadata helper IDs disagree with the raw rig")
    return _sha(raw)


def _context(data):
    packed = data["body"]
    source_path = (ROOT / packed["source"]).resolve()
    if not source_path.is_relative_to(ROOT):
        raise ValueError("Canonical body source must be inside this repository")
    canonical, joints, original_provenance = _source_joints(str(source_path), packed["source_sha256"])
    provenance = dict(original_provenance)
    provenance["source_hashes"] = dict(original_provenance["source_hashes"])
    proxy_sha = _bind_proxy_provenance(provenance)
    provenance["proxy_metadata_sha256"] = proxy_sha
    provenance["source_hashes"][str(PROXY_METADATA_FILE.relative_to(ROOT))
                                 if PROXY_METADATA_FILE.is_relative_to(ROOT) else PROXY_METADATA_FILE.name] = proxy_sha
    provenance["source_hashes"][str(Path(__file__).relative_to(ROOT))] = _sha(Path(__file__).read_bytes())
    provenance["source_hashes"][str(TRIANGLE_ORACLE.relative_to(ROOT))] = _sha(TRIANGLE_ORACLE.read_bytes())
    bv = _unpack(packed["positions"]).astype(float).reshape(-1, 3)
    bf = _unpack(packed["indices"], "<i4").reshape(-1, 3)
    if not np.array_equal(bv, np.asarray(canonical["positions"], dtype="<f4").astype(float).reshape(-1, 3)):
        raise ValueError("Actual body positions changed with a stale source SHA")
    if not np.array_equal(bf, np.asarray(canonical["triangles"], int).reshape(-1, 3)):
        raise ValueError("Actual body topology differs from the canonical source")
    return trimesh.Trimesh(bv, bf, process=False), joints, provenance


def _solid_angle_winding(points, triangles):
    """Van Oosterom-Strackee solid angle in f64, independent of ray parity."""
    a = triangles[None, :, 0] - points[:, None]
    b = triangles[None, :, 1] - points[:, None]
    c = triangles[None, :, 2] - points[:, None]
    la, lb, lc = (np.linalg.norm(value, axis=-1) for value in [a, b, c])
    determinant = np.sum(a * np.cross(b, c), axis=-1)
    denominator = (la * lb * lc + np.sum(a * b, axis=-1) * lc
                   + np.sum(a * c, axis=-1) * lb + np.sum(b * c, axis=-1) * la)
    return (2 * np.arctan2(determinant, denominator)).sum(axis=1) / (4 * np.pi)


def _actual_sleeve(data, positions, panel):
    name, start, count = panel["name"], int(panel["start"]), int(panel["vertices"])
    cert = data["source_sewing"]
    patch = cert["patches"][name]
    if start < 0 or count < 3 or start + count > len(positions):
        raise ValueError("Sleeve panel range is out of bounds")
    local_ids = np.asarray(data["global_ids"])[start:start + count]
    if not np.array_equal(local_ids, patch["global_vertices"]):
        raise ValueError("Sleeve source global IDs differ from the recorded panel")
    local_faces = np.asarray(patch["local_faces"], int)
    if (local_faces.ndim != 2 or local_faces.shape[1] != 3 or not len(local_faces)
            or local_faces.min() < 0 or local_faces.max() >= count):
        raise ValueError("Invalid actual sleeve triangle indices")
    fs, nf = int(panel["face_start"]), int(panel["faces"])
    recorded = np.asarray(data["triangles"], int)[fs:fs + nf] - start
    if not np.array_equal(recorded, local_faces):
        raise ValueError("Recorded sleeve triangles differ from source local faces")
    _, first, inverse = np.unique(local_ids, return_index=True, return_inverse=True)
    actual = positions[start:start + count]
    alias_gap = float(np.linalg.norm(actual - actual[first[inverse]], axis=1).max())
    points, faces = actual[first].tolist(), inverse[local_faces]
    expected = {}
    for opening, keys in [("armhole", [name + ".cap.front", name + ".cap.back"]),
                          ("cuff", [name + ".cuff"])]:
        local = set()
        for key in keys:
            local.update(cert["segments"][key]["local_vertices"])
        if not local or min(local) < 0 or max(local) >= count:
            raise ValueError("Invalid source sleeve opening IDs")
        expected[opening] = set(map(int, inverse[np.array(sorted(local))]))
    edge_uses = {}
    for face in faces:
        for k in range(3):
            a, b = int(face[k]), int(face[(k + 1) % 3])
            edge_uses.setdefault(tuple(sorted((a, b))), []).append((a, b))
    if any(len(entries) > 2 for entries in edge_uses.values()):
        raise ValueError("Actual sleeve has a nonmanifold edge")
    edges = [entry[0] for entry in edge_uses.values() if len(entry) == 1]
    adjacency = {}
    for a, b in edges:
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    if any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise ValueError("Actual sleeve opening is branched")
    remaining, components = set(adjacency), []
    while remaining:
        connected, stack = set(), [next(iter(remaining))]
        while stack:
            vertex = stack.pop()
            if vertex in connected:
                continue
            connected.add(vertex)
            stack.extend(adjacency[vertex])
        remaining -= connected
        components.append(connected)
    if len(components) != 2:
        raise ValueError("Actual sleeve must have exactly two openings")
    caps, boundaries = [], {}
    for component in components:
        labels = [key for key, wanted in expected.items() if component == wanted]
        if len(labels) != 1:
            raise ValueError("Actual sleeve cycles differ from source armhole/cuff IDs")
        label = labels[0]
        boundary = np.asarray(points)[sorted(component)]
        center, ci = boundary.mean(0), len(points)
        points.append(center.tolist())
        cap_faces = [[ci, b, a] for a, b in edges if a in component]
        cap_start = len(caps)
        caps.extend(cap_faces)
        _, singular, vt = np.linalg.svd(boundary - center, full_matrices=False)
        boundaries[label] = {"points": sorted(component), "center_m": center.tolist(),
                             "virtual_cap_face_start": cap_start, "virtual_cap_face_count": len(cap_faces),
                             "pca_normal": vt[-1].tolist(), "pca_singular_m": singular.tolist()}
    if set(boundaries) != {"armhole", "cuff"}:
        raise ValueError("Opening labels are not a distinct armhole and cuff")
    points, caps = np.asarray(points), np.asarray(caps, int)
    closed = trimesh.Trimesh(points, np.vstack([faces, caps]), process=False)
    real = trimesh.Trimesh(points[:len(first)], faces, process=False)
    return real, closed, caps, boundaries, alias_gap


def _bone_surface_hits(mesh, joints):
    starts, vectors = joints[:-1], np.diff(joints, axis=0)
    lengths = np.linalg.norm(vectors, axis=1)
    directions = vectors / lengths[:, None]
    locations, rays, faces = mesh.ray.intersects_location(starts, directions, multiple_hits=True)
    if not len(rays):
        return []
    distance = np.sum((locations - starts[rays]) * directions[rays], axis=1)
    keep = (distance > NUMERICAL_M) & (distance < lengths[rays] - NUMERICAL_M)
    return [{"bone": ["shoulder_to_elbow", "elbow_to_wrist"][int(ray)],
             "distance_from_start_mm": float(d * 1000), "triangle": int(face), "point_m": point.tolist()}
            for ray, d, face, point in zip(rays[keep], distance[keep], faces[keep], locations[keep])]


def _sleeve_check(data, positions, panel, body, joints, global_alias_gap, audit_virtual_caps):
    name = panel["name"]
    side = "R" if name == "sleeve.left" else "L"
    actual = joints[side]
    chain = np.vstack([np.linspace(actual[0], actual[1], 33), np.linspace(actual[1], actual[2], 33)[1:]])
    real, closed, caps, boundaries, alias_gap = _actual_sleeve(data, positions, panel)
    triangles = closed.triangles
    double_area = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1)
    degenerate = int(np.count_nonzero(double_area <= NUMERICAL_M ** 2))
    mesh_valid = closed.is_watertight and closed.is_winding_consistent and closed.volume > 0 and not degenerate
    ray_inside = closed.contains(chain)
    winding = _solid_angle_winding(chain, triangles)
    angle_inside = abs(winding) > .5
    _, distance, _ = trimesh.proximity.closest_point(closed, chain)
    real_hits = _bone_surface_hits(real, actual)
    cap_hits = _bone_surface_hits(trimesh.Trimesh(closed.vertices, caps, process=False), actual)
    for hit in cap_hits:
        hit["opening"] = next(label for label, value in boundaries.items()
                              if value["virtual_cap_face_start"] <= hit["triangle"]
                              < value["virtual_cap_face_start"] + value["virtual_cap_face_count"])
    cap_real = intersect_pairs(closed.vertices, caps, real.vertices, real.faces, epsilon_m=NUMERICAL_M) if audit_virtual_caps else None
    cap_self = intersect_pairs(closed.vertices, caps, epsilon_m=NUMERICAL_M) if audit_virtual_caps else None
    closure_verified = bool(mesh_valid and alias_gap == global_alias_gap == 0.
                            and audit_virtual_caps and not cap_real and not cap_self)
    ray_angle_agree = bool(np.array_equal(ray_inside, angle_inside))
    near_boundary = distance <= NUMERICAL_M
    source_chain_inside = body.contains(chain)
    sampled_enclosed = bool(ray_inside.all() and angle_inside.all())
    unresolved = not closure_verified or not ray_angle_agree or near_boundary.any() or not source_chain_inside.all()
    if unresolved:
        enclosure = "INCONCLUSIVE"
    elif sampled_enclosed and not real_hits and not cap_hits:
        enclosure = "ENCLOSED"
    else:
        enclosure = "PARTIAL_OR_OUTSIDE_CHAIN"
    entering_once = (len(cap_hits) == 1 and cap_hits[0]["opening"] == "armhole"
                     and cap_hits[0]["bone"] == "shoulder_to_elbow")
    inside_indices = np.flatnonzero(ray_inside)
    suffix = bool(len(inside_indices) and np.array_equal(inside_indices, np.arange(inside_indices[0], 65)))
    distal_inside = bool(ray_inside[32:].all() and angle_inside[32:].all())
    # The shoulder may start in the torso, behind the artificial armhole disk.
    # Allow that prefix only with one armhole entry, no fabric crossing, and an
    # uninterrupted inside suffix through the elbow and actual wrist.
    if unresolved:
        threading = "INCONCLUSIVE"
    elif sampled_enclosed and not real_hits and not cap_hits:
        threading = "FULL_CHAIN_ENCLOSED"
    elif not ray_inside[0] and distal_inside and suffix and not real_hits and entering_once:
        threading = "THREADED_THROUGH_ARMHOLE"
    else:
        threading = "MISROUTED_OR_UNCOVERED"
    threaded = threading in ("FULL_CHAIN_ENCLOSED", "THREADED_THROUGH_ARMHOLE")
    joint_rows = {}
    for label, i in [("shoulder", 0), ("elbow", 32), ("wrist", 64)]:
        joint_rows[label] = {"actual_canonical_m": chain[i].tolist(), "inside_ray": bool(ray_inside[i]),
                             "inside_solid_angle": bool(angle_inside[i]), "solid_angle_winding": float(winding[i]),
                             "distance_to_closed_sleeve_mm": float(distance[i] * 1000)}
    return {
        "panel": name, "anatomical_side": side, "numeric_arm_enclosure": enclosure,
        "arm_threading_status": threading, "arm_threaded_to_wrist": threaded,
        "distal_elbow_to_wrist_chain_inside": distal_inside, "joint_checks": joint_rows,
        "arm_chain": {"samples": 65, "points_m": chain.tolist(), "inside_ray": ray_inside.tolist(),
                      "inside_solid_angle": angle_inside.tolist(), "inside_count": int(ray_inside.sum()),
                      "outside_indices": np.flatnonzero(~ray_inside).tolist(),
                      "source_body_inside_count": int(source_chain_inside.sum()), "ray_solid_angle_agree": ray_angle_agree,
                      "solid_angle_winding": winding.tolist(), "min_closed_surface_distance_mm": float(distance.min() * 1000),
                      "near_boundary_indices": np.flatnonzero(near_boundary).tolist()},
        "actual_sleeve_bone_surface_hits": real_hits, "virtual_cap_bone_hits": cap_hits,
        "closure": {"watertight": bool(closed.is_watertight), "winding_consistent": bool(closed.is_winding_consistent),
                    "signed_volume_m3": float(closed.volume), "degenerate_triangles": degenerate,
                    "max_underarm_alias_gap_mm": alias_gap * 1000, "max_source_alias_gap_mm": global_alias_gap * 1000,
                    "virtual_cap_real_surface_pairs": None if cap_real is None else len(cap_real),
                    "virtual_cap_self_pairs": None if cap_self is None else len(cap_self),
                    "cap_real_examples": None if cap_real is None else cap_real[:10],
                    "cap_self_examples": None if cap_self is None else cap_self[:10],
                    "virtual_closure_verified": closure_verified, "virtual_caps_never_enter_physical_mesh": True},
        "wrist_to_actual_cuff_center_mm": float(np.linalg.norm(actual[2] - boundaries["cuff"]["center_m"]) * 1000),
        "opening_geometry": boundaries,
    }


def check_arm_wear(data, positions, *, audit_virtual_caps=True):
    """Independently inspect actual recorded XYZ in the input's panel order.

    both_arms_threaded permits either an entirely enclosed arm chain or one
    proximal entry through the actual source armhole followed by continuous
    enclosure through elbow/wrist. Exits through real fabric or the cuff fail.
    Invalid/unchecked virtual caps, nonzero aliases or ambiguous sign produce
    INCONCLUSIVE and never true. No input or physical mesh is modified.

    Invalid source provenance/recording shape raises ValueError. Per-sleeve
    invalid closure is returned as INCONCLUSIVE, with an explicit error.
    Existing frame body/self/physics audits must still run independently.
    """
    started = time.monotonic()
    positions = np.asarray(positions, dtype=float)
    ids = np.asarray(data["global_ids"])
    if (positions.shape != (len(ids), 3) or not np.isfinite(positions).all()
            or ids.ndim != 1 or ids.dtype.kind not in "iu"):
        raise ValueError("Bad recorded positions/global IDs")
    body, joints, provenance = _context(data)
    _, first, inverse = np.unique(ids, return_index=True, return_inverse=True)
    global_alias_gap = float(np.linalg.norm(positions - positions[first[inverse]], axis=1).max())
    panels = [panel for panel in data["panels"] if panel["name"] in ("sleeve.left", "sleeve.right")]
    if len(panels) != 2 or {panel["name"] for panel in panels} != {"sleeve.left", "sleeve.right"}:
        raise ValueError("Expected exactly the two actual source sleeves")
    rows = []
    for panel in panels:
        try:
            row = _sleeve_check(data, positions, panel, body, joints, global_alias_gap, audit_virtual_caps)
        except ValueError as exc:
            row = {"panel": panel["name"], "arm_threaded_to_wrist": False,
                   "numeric_arm_enclosure": "INCONCLUSIVE", "arm_threading_status": "INCONCLUSIVE",
                   "closure": {"virtual_closure_verified": False}, "error": str(exc)}
        rows.append(row)
    return {
        "format": "independent-numeric-arm-wear/1", "source": provenance, "sleeves": rows,
        "max_source_alias_gap_mm": global_alias_gap * 1000,
        "both_arm_chains_enclosed": all(row["numeric_arm_enclosure"] == "ENCLOSED" for row in rows),
        "both_arms_threaded": all(row["arm_threaded_to_wrist"] for row in rows),
        "scope": "Fixed-proxy shoulder/elbow/wrist bone-chain routing only; no human fit acceptance",
        "geometric_limits": ["65 anatomical samples plus two full bone-segment/surface ray checks",
                             "virtual armhole/cuff fans must be closed, oriented, nondegenerate and nonintersecting",
                             "not all human surface vertices, skin clearance, fit, or continuous-time collision detection"],
        "requires_separate_frame_audits": ["strict cloth self-intersections", "actual cloth/body triangle crossings",
                                           "material, clock, continuation and physical-trajectory checks"],
        "numerical_intersection_epsilon_m": NUMERICAL_M,
        "body_contact_acceptance": "NOT_RUN", "cloth_self_acceptance": "NOT_RUN",
        "physical_acceptance": "NOT_RUN", "physical_fit": "NOT_RUN",
        "wall_seconds": time.monotonic() - started,
    }
