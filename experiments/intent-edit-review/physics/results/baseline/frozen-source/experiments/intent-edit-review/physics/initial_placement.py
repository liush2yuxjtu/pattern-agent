"""UV-metric, fixed-boundary initialisation for the source-bound experiment.

This prepares a lower-distortion seed. It is not a physical solve, collision
acceptance, fit result, or replacement for the independently retained source
reference. The fixed boundary can itself be inside the actual body.
"""
from __future__ import annotations

import hashlib
import json
import warnings

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import MatrixRankWarning, spsolve


def _json_digest(value):
    def convert(item):
        if isinstance(item, np.ndarray):
            return item.tolist()
        if isinstance(item, np.generic):
            return item.item()
        raise TypeError(f"Unsupported certificate value: {type(item).__name__}")
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                     allow_nan=False, default=convert).encode()
    return hashlib.sha256(raw).hexdigest()


def _array_digest(value, dtype):
    array = np.ascontiguousarray(value, dtype=dtype)
    return hashlib.sha256(str(array.shape).encode() + array.tobytes()).hexdigest()


def _fem_harmonic(points_m, triangles, boundary_values):
    """Solve integral grad(N_i).grad(N_j), not an unweighted graph Laplacian.

    Boundary samples come first, as in the existing source triangulator. The
    stiffness is assembled from the unchanged material UV triangle metric.
    Negative individual cotangents are retained; this is the FEM Dirichlet
    system rather than a clamped or resampled graph approximation.
    """
    points = np.asarray(points_m, dtype=np.float64)
    raw_faces = np.asarray(triangles)
    values = np.asarray(boundary_values, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all():
        raise ValueError("Material UV must be finite Nx2 coordinates")
    if raw_faces.ndim != 2 or raw_faces.shape[1] != 3 or raw_faces.dtype.kind not in "iu":
        raise ValueError("Material triangles must be an integer Mx3 array")
    faces = raw_faces.astype(np.int64, copy=False)
    if not len(faces) or faces.min() < 0 or faces.max() >= len(points):
        raise ValueError("Material triangle indices are missing or out of range")
    if values.ndim != 2 or not 0 < len(values) <= len(points) or not np.isfinite(values).all():
        raise ValueError("Boundary values are missing, nonfinite, or inconsistent")
    p = points[faces]
    e1, e2 = p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]
    twice_area = e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]
    if np.any(abs(twice_area) <= 1e-18):
        raise ValueError("Degenerate material UV triangle")
    edges = np.stack([p[:, 2] - p[:, 1], p[:, 0] - p[:, 2], p[:, 1] - p[:, 0]], axis=1)
    gradients = np.stack([edges[:, :, 1], -edges[:, :, 0]], axis=2) / twice_area[:, None, None]
    local = (abs(twice_area) / 2)[:, None, None] * (gradients @ gradients.transpose(0, 2, 1))
    rows = np.repeat(faces, 3, axis=1).ravel()
    columns = np.tile(faces, (1, 3)).ravel()
    stiffness = coo_matrix((local.ravel(), (rows, columns)),
                           shape=(len(points), len(points))).tocsr()
    nb = len(values)
    result = np.empty((len(points), values.shape[1]), dtype=np.float64)
    result[:nb] = values
    if nb < len(points):
        with warnings.catch_warnings():
            warnings.simplefilter("error", MatrixRankWarning)
            try:
                result[nb:] = spsolve(stiffness[nb:, nb:], -stiffness[nb:, :nb] @ values)
            except MatrixRankWarning as exc:
                raise ValueError("Material FEM system has an unanchored component") from exc
    if not np.isfinite(result).all():
        raise ValueError("Material FEM solve produced nonfinite coordinates")
    return result


def improve_initial_placement(certificate, positions, panels, global_ids, builder,
                              translation, placement_depth):
    """Return a new unwelded XYZ array and an explicit initialisation record.

    Front/back interiors use material-metric FEM harmonic XYZ with the *current*
    post-depth-warp boundary fixed. Sleeve interiors use material-metric FEM on
    the existing (u, theta) boundary declaration, then the original tube target
    and world/depth conversion. Band positions are retained. Seam aliases are
    synchronised without changing their existing boundary coordinates.

    All inputs are read-only. Final body geometry, material UVs, topology and
    the source seam declaration are not changed or reinterpreted here.
    """
    original = np.asarray(positions, dtype=np.float64)
    raw_ids = np.asarray(global_ids)
    translation = np.asarray(translation, dtype=np.float64)
    if original.ndim != 2 or original.shape[1] != 3 or not np.isfinite(original).all():
        raise ValueError("Initial positions must be finite Nx3 coordinates")
    if raw_ids.ndim != 1 or len(raw_ids) != len(original) or raw_ids.dtype.kind not in "iu":
        raise ValueError("Seam global IDs must be an integer ID for every position")
    if translation.shape != (3,) or not np.isfinite(translation).all():
        raise ValueError("World translation must be a finite 3-vector")
    scale = float(placement_depth["scale"])
    depth_offset = float(placement_depth["offset_m"])
    arm_offset = float(placement_depth["arm_offset_m"])
    if not np.isfinite([scale, depth_offset, arm_offset]).all() or scale <= 0:
        raise ValueError("Depth placement must have finite offsets and positive scale")
    ids = raw_ids.astype(np.int64, copy=False)
    aliases = {}
    for i, gid in enumerate(ids):
        aliases.setdefault(int(gid), []).append(i)
    for group in aliases.values():
        if any(not np.array_equal(original[group[0]], original[i]) for i in group[1:]):
            raise ValueError("Input seam aliases must already share exact boundary positions")

    certificate_before = _json_digest(certificate)
    panels_before = _json_digest(panels)
    ids_before = _array_digest(ids, "<i8")
    output = original.copy()
    coverage = np.zeros(len(original), dtype=np.int8)
    boundary = np.zeros(len(original), dtype=bool)
    band_slices = []
    records = []
    for panel in panels:
        name = panel["name"]
        start, count = int(panel["start"]), int(panel["vertices"])
        if start < 0 or count <= 0 or start + count > len(original):
            raise ValueError("Panel vertex range is out of bounds")
        coverage[start:start + count] += 1
        patch = certificate["patches"][name]
        points = np.asarray(patch["flat_points"], dtype=np.float64) / 1000
        faces = np.asarray(patch["local_faces"])
        nb = int(patch["boundary_count"])
        if len(points) != count or not 0 < nb <= count:
            raise ValueError("Panel material data and boundary count do not match its positions")
        boundary[start:start + nb] = True
        record = {"panel": name, "vertices": count, "boundary_vertices": nb,
                  "rest_uv_sha256": _array_digest(points, "<f8"),
                  "topology_sha256": _array_digest(faces, "<i8")}
        if name in ("front", "back"):
            output[start:start + count] = _fem_harmonic(points, faces, original[start:start + nb])
            record["method"] = "material-metric FEM harmonic XYZ, fixed current boundary"
        elif name.startswith("sleeve."):
            domains = []
            for key, reverse in builder.loops[name]:
                parameters = np.asarray(certificate["segments"][key]["parameter"], dtype=np.float64)
                values = np.asarray(builder.segments[key]["domain"](parameters), dtype=np.float64)
                if values.shape != (len(parameters), 2) or not np.isfinite(values).all():
                    raise ValueError("Sleeve boundary domain is not finite (u, theta)")
                if reverse:
                    values = values[::-1]
                domains.extend(values[:-1])
            if len(domains) != nb:
                raise ValueError("Sleeve domain boundary differs from the source boundary sample count")
            domain = _fem_harmonic(points, faces, np.asarray(domains))
            local = np.asarray(builder.targets["tube." + name.split(".")[-1]](
                domain[:, 0], domain[:, 1]), dtype=np.float64)
            if local.shape != (count, 3) or not np.isfinite(local).all():
                raise ValueError("Original sleeve tube target produced invalid coordinates")
            world = local[:, [0, 2, 1]] * [1, 1, -1] + translation
            blend = np.clip((abs(world[:, 0]) - .25) / .20, 0, 1)
            blend = blend * blend * (3 - 2 * blend)
            world[:, 2] = world[:, 2] * scale + depth_offset + arm_offset * blend
            # Replaying the coordinate conversion can differ by roundoff at a
            # seam. The supplied, already shared boundary is the exact anchor.
            world[:nb] = original[start:start + nb]
            output[start:start + count] = world
            record.update(method="material-metric FEM (u,theta), original tube and depth placement",
                          domain_min=domain.min(0).tolist(), domain_max=domain.max(0).tolist())
        elif name == "band":
            band_slices.append(slice(start, start + count))
            record["method"] = "unchanged current band"
        else:
            raise ValueError(f"Unsupported source panel: {name}")
        records.append(record)
    if np.any(coverage != 1):
        raise ValueError("Panels must cover each initial position exactly once")
    for group in aliases.values():
        # Prefer an anchored member if the source mapping also contains an
        # interior alias. No new seam pair or weld ID is introduced.
        canonical = next((i for i in group if boundary[i]), group[0])
        for i in group:
            output[i] = output[canonical]
    if output[boundary].tobytes() != original[boundary].tobytes():
        raise ValueError("Initialisation changed a fixed source boundary coordinate")
    if any(output[s].tobytes() != original[s].tobytes() for s in band_slices):
        raise ValueError("Seam alias synchronisation would change the retained band")
    if not np.isfinite(output).all():
        raise ValueError("Initialisation produced nonfinite positions")
    if certificate_before != _json_digest(certificate) or panels_before != _json_digest(panels):
        raise ValueError("Initialisation mutated source material geometry or panel declarations")
    if ids_before != _array_digest(ids, "<i8"):
        raise ValueError("Initialisation mutated seam global IDs")
    max_alias_gap = max((float(np.linalg.norm(output[i] - output[group[0]]))
                         for group in aliases.values() for i in group), default=0.)
    metadata = {
        "method": "fixed-current-boundary UV-metric FEM hybrid/1",
        "role": "initialisation seed only; not a source-reference shell or physical frame",
        "physical_fit": "NOT_RUN", "physical_acceptance": "NOT_RUN",
        "body_contact_acceptance": "NOT_RUN", "self_intersection_acceptance": "NOT_RUN",
        "does_not_replace_source_reference": True,
        "source_certificate_sha256_before": certificate_before,
        "source_certificate_sha256_after": _json_digest(certificate),
        "panel_declarations_sha256": panels_before,
        "global_ids_sha256": ids_before,
        "fixed_boundary_vertices": int(boundary.sum()),
        "fixed_boundary_coordinates_bit_exact": True,
        "max_boundary_delta_m": 0., "max_seam_alias_gap_m": max_alias_gap,
        "changed_vertices": int(np.any(output != original, axis=1).sum()),
        "max_initialisation_move_m": float(np.linalg.norm(output - original, axis=1).max()),
        "panels": records,
    }
    return output, metadata
