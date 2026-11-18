"""Measure folds on the interior edges of individual cloth pieces."""

import io
import math

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import Normalize
import numpy as np


def measure_folds(positions, uv, faces, threshold_deg):
    # Match exporter splits only when both position and rest-pattern UV agree.
    _, vertex_ids = np.unique(np.column_stack((positions, uv)), axis=0, return_inverse=True)
    xyz, flat = positions[faces], uv[faces]
    normals = np.cross(xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0])
    size = np.linalg.norm(normals, axis=1)
    valid = size > 1e-10
    normals[valid] /= size[valid, None]
    corners = vertex_ids[faces].astype(np.int64)
    edges = np.stack((corners, np.roll(corners, -1, axis=1)), axis=2).reshape(-1, 2)
    keys = np.sort(edges, axis=1)
    order = np.lexsort((keys[:, 1], keys[:, 0]))
    sorted_keys = keys[order]
    starts = np.flatnonzero(np.r_[True, np.any(sorted_keys[1:] != sorted_keys[:-1], axis=1)])
    counts = np.diff(np.r_[starts, len(order)])
    pairs = starts[counts == 2]
    a, b = order[pairs], order[pairs + 1]
    usable = valid[a // 3] & valid[b // 3] & (a // 3 != b // 3)
    a, b = a[usable], b[usable]
    na, nb = normals[a // 3], normals[b // 3].copy()
    # Inconsistent face winding should not convert a flat patch into a 180° fold.
    nb[edges[a, 0] == edges[b, 0]] *= -1
    angles = np.degrees(np.arctan2(np.linalg.norm(np.cross(na, nb), axis=1), np.sum(na * nb, axis=1)))
    endpoints = np.column_stack((faces[a // 3, a % 3], faces[a // 3, (a + 1) % 3]))
    lengths = np.linalg.norm(positions[endpoints[:, 1]] - positions[endpoints[:, 0]], axis=1)
    sharp = angles >= threshold_deg
    face_angles = np.zeros(len(faces))
    np.maximum.at(face_angles, a // 3, angles)
    np.maximum.at(face_angles, b // 3, angles)
    total_length = float(lengths.sum())
    sharp_length = float(lengths[sharp].sum())
    stats = {
        "fold_interior_edge_count": len(angles),
        "fold_boundary_edge_count": int(np.sum(counts == 1)),
        "fold_nonmanifold_edge_count": int(np.sum(counts > 2)),
        "fold_unmeasurable_two_face_edge_count": int(len(pairs) - len(angles)),
        "fold_threshold_deg": threshold_deg,
        "fold_p95_deg": float(np.quantile(angles, .95)) if len(angles) else None,
        "fold_max_deg": float(angles.max()) if len(angles) else None,
        "fold_edges_at_or_above_threshold": int(sharp.sum()),
        "fold_edge_length_at_or_above_threshold_mm": sharp_length,
        "fold_edge_length_share_pct": 100 * sharp_length / total_length if total_length else None,
    }
    return stats, (xyz, face_angles, flat, uv[endpoints[sharp]])


def png(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=160)
    plt.close(fig)
    return buffer.getvalue()


def render_folds(pieces, title, threshold, scale_max):
    xyz = np.concatenate([geometry[0] for geometry in pieces.values()])
    face_angles = np.concatenate([geometry[1] for geometry in pieces.values()])
    norm = Normalize(0, scale_max, clip=True)
    palette = plt.get_cmap("magma")
    colors = palette(norm(face_angles))
    fig, axes = plt.subplots(2, 2, figsize=(11, 9), layout="constrained")
    fig.suptitle(f"{title} — fold angles")
    views = (
        ("Front", xyz[:, :, 0], xyz[:, :, 2]),
        ("Back", -xyz[:, :, 0], -xyz[:, :, 2]),
        ("+X side", -xyz[:, :, 2], xyz[:, :, 0]),
        ("−X side", xyz[:, :, 2], -xyz[:, :, 0]),
    )
    for axis, (label, horizontal, depth) in zip(axes.flat, views):
        order = np.argsort(depth.mean(axis=1))
        xy = np.stack((horizontal, xyz[:, :, 1]), axis=-1)
        axis.add_collection(PolyCollection(xy[order], facecolors=colors[order],
                                           edgecolors="face", linewidths=.12, antialiaseds=False))
        axis.autoscale_view()
        axis.set_aspect("equal")
        axis.set_axis_off()
        axis.set_title(label, loc="left")
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=palette), ax=axes, orientation="horizontal",
                 shrink=.67, aspect=32, label="Largest neighboring face angle (°) · end color caps the display")
    spatial = png(fig)

    columns = min(3, len(pieces))
    rows = math.ceil(len(pieces) / columns)
    fig, axes = plt.subplots(rows, columns, figsize=(4 * columns, 3.45 * rows + .6),
                             squeeze=False, layout="constrained")
    fig.suptitle(f"{title} — fold edges on flat pieces\nInterior edges at or above {threshold:g}° · each piece fitted to its panel")
    for axis in axes.flat:
        axis.set_axis_off()
    for axis, (name, (_, _, triangles, creases)) in zip(axes.flat, pieces.items()):
        axis.add_collection(PolyCollection(triangles, facecolors="#e9edf1", edgecolors="face", linewidths=.12))
        axis.add_collection(LineCollection(creases, colors="#a92e22", linewidths=.68))
        axis.autoscale_view()
        axis.invert_yaxis()  # CLO export uses downward-increasing V.
        axis.set_aspect("equal")
        axis.set_title(f"{name} · {len(creases):,} edges", loc="left")
    return spatial, png(fig)
