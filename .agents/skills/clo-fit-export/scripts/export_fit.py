#!/usr/bin/env python3
"""Export a static CLO fit report from saved simulation artifacts."""

import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import struct
from zipfile import BadZipFile, ZipFile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize
import numpy as np
from fold_preview import measure_folds, render_folds


def read_cloth(path):
    data = path.read_bytes()
    if len(data) < 20 or struct.unpack_from("<III", data) != (0x46546C67, 2, len(data)):
        raise ValueError("Expected a GLB 2 file")
    chunks = {}
    offset = 12
    while offset + 8 <= len(data):
        size, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        if size > len(data) - offset:
            raise ValueError("Truncated GLB chunk")
        chunks[kind] = memoryview(data)[offset:offset + size]
        offset += size
    doc = json.loads(bytes(chunks[0x4E4F534A]))
    binary = chunks[0x004E4942]
    if len(doc["meshes"]) != 1:
        raise ValueError("Export a garment-only GLB with one cloth mesh")

    def array(index, shape, types):
        accessor = doc["accessors"][index]
        view = doc["bufferViews"][accessor["bufferView"]]
        if (accessor["type"] != shape or accessor["componentType"] not in types
                or accessor.get("sparse") or accessor.get("normalized") or view["buffer"] != 0):
            raise ValueError("Expected uncompressed float positions/UVs and unsigned indices")
        dtype = np.dtype({5126: "<f4", 5125: "<u4", 5123: "<u2", 5121: "u1"}[accessor["componentType"]])
        columns = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[shape]
        start = accessor.get("byteOffset", 0)
        stride = view.get("byteStride", columns * dtype.itemsize)
        count = accessor["count"]
        view_start = view.get("byteOffset", 0)
        if (count < 1 or start < 0 or stride < columns * dtype.itemsize
                or start + (count - 1) * stride + columns * dtype.itemsize > view["byteLength"]
                or view_start + view["byteLength"] > len(binary)):
            raise ValueError("Invalid GLB accessor bounds")
        return np.ndarray((count, columns), dtype=dtype, buffer=binary,
                          offset=view_start + start, strides=(stride, dtype.itemsize))

    pieces = []
    for primitive in doc["meshes"][0]["primitives"]:
        if primitive.get("mode", 4) != 4 or primitive.get("targets"):
            raise ValueError("Expected a static triangle mesh")
        attributes = primitive["attributes"]
        xyz = array(attributes["POSITION"], "VEC3", {5126})
        uv = array(attributes["TEXCOORD_0"], "VEC2", {5126})
        triangles = array(primitive["indices"], "SCALAR", {5121, 5123, 5125}).reshape(-1, 3)
        if len(xyz) != len(uv) or triangles.max() >= len(xyz):
            raise ValueError("GLB indices, positions and UVs do not match")
        pieces.append((xyz, uv, triangles))
    if not pieces:
        raise ValueError("No cloth primitives found")
    return pieces


def analyse_piece(xyz, uv, faces, args):
    xyz = xyz[faces].astype(np.float64) * args.position_mm_per_unit
    uv = uv[faces].astype(np.float64) * args.uv_mm_per_unit
    if not np.isfinite(xyz).all() or not np.isfinite(uv).all():
        raise ValueError("Mesh contains non-finite coordinates")

    rest_edges = (uv[:, 1:] - uv[:, :1]).transpose(0, 2, 1)
    draped_edges = (xyz[:, 1:] - xyz[:, :1]).transpose(0, 2, 1)
    areas = np.abs(np.linalg.det(rest_edges)) / 2
    valid = areas > args.min_triangle_area_mm2
    if not valid.any():
        raise ValueError("No valid pattern triangles. Verify that the UVs carry metric pattern coordinates.")
    area = areas[valid]
    deformation = draped_edges[valid] @ np.linalg.inv(rest_edges[valid])
    stretches = np.linalg.svd(deformation, compute_uv=False)[:, 0]
    strain = 100 * (stretches - 1)
    order = np.argsort(strain)
    percentiles = np.interp([.50, .95, .99], np.cumsum(area[order]) / area.sum(), strain[order])
    if not -90 <= percentiles[0] <= 900:
        raise ValueError("Implausible median strain. Verify raw GLB and UV units before exporting.")
    statistics = {
        "strain_p50_pct": float(percentiles[0]),
        "strain_p95_pct": float(percentiles[1]),
        "strain_p99_pct": float(percentiles[2]),
        "area_above_threshold_pct": float(100 * area[strain > args.threshold_pct].sum() / area.sum()),
        "analysed_rest_area_mm2": float(area.sum()),
        "included_triangles": int(valid.sum()),
        "excluded_triangles": int((~valid).sum()),
    }
    return statistics, xyz[valid], strain


def read_stress_samples(path, piece_ids):
    if path is None:
        return []
    samples = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = {"piece_id", "location", "stress_kpa"}
        if not fields.issubset(reader.fieldnames or []):
            raise ValueError("Stress CSV needs piece_id, location, stress_kpa columns")
        for line, row in enumerate(reader, 2):
            piece, location, value = ((row.get(name) or "").strip() for name in ("piece_id", "location", "stress_kpa"))
            if piece not in piece_ids or not location or not value:
                raise ValueError(f"Stress CSV row {line} needs a known piece, location and numeric kPa")
            value = float(value)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"Invalid kPa on stress CSV row {line}")
            samples.append({"piece_id": piece, "location": location, "stress_kpa": value})
    if not samples:
        raise ValueError("Stress sample CSV contains no readings")
    return samples


def read_scale(project):
    if not project:
        return None
    with ZipFile(project) as archive:
        if "fitmapsettings.json" not in archive.namelist():
            return None
        settings = json.loads(archive.read("fitmapsettings.json"))
    native = settings.get("stressmap", {})
    if native.get("displayUnit") != 0 or native.get("graphColorType") != 0:
        return None  # Do not label an unrecognized unit or display mode as continuous kPa.
    levels = sorted(native.get("listRanges", []), key=lambda entry: entry["value"])
    if len(levels) < 2 or any(a["value"] >= b["value"] for a, b in zip(levels, levels[1:])):
        return None
    return [{"kpa": level["value"], "rgb": level["v3Color"]} for level in levels]


def plot_report(geometry, samples, args, scale):
    triangles = np.concatenate([xyz for xyz, _ in geometry])
    strains = np.concatenate([strain for _, strain in geometry])
    fig, axes = plt.subplots(2, 2, figsize=(11, 10), layout="constrained")
    fig.suptitle(args.title, fontweight="bold", fontsize=18)
    images = [args.stress_front, args.stress_back]
    has_images = any(images)
    for view, path, ax in zip(("Front", "Back"), images, axes[0]):
        ax.set_axis_off()
        ax.set_title(f"CLO stress · {view}", loc="left")
        if path:
            pixels = plt.imread(path)
            if args.stress_crop:
                left, top, right, bottom = args.stress_crop
                if not (0 <= left < right <= pixels.shape[1] and 0 <= top < bottom <= pixels.shape[0]):
                    raise ValueError(f"Stress crop is out of bounds for {path.name}")
                pixels = pixels[top:bottom, left:right]
            ax.imshow(pixels)
        else:
            ax.text(.5, .5, "No saved image for this view", ha="center", va="center", transform=ax.transAxes)

    if has_images and scale:
        low, high = scale[0]["kpa"], scale[-1]["kpa"]
        cmap = LinearSegmentedColormap.from_list("CLO stress", [((s["kpa"] - low) / (high - low), s["rgb"]) for s in scale])
        fig.colorbar(plt.cm.ScalarMappable(norm=Normalize(low, high), cmap=cmap),
                     ax=axes[0], orientation="horizontal", shrink=.64, aspect=35, label="CLO display scale (kPa)")
    elif has_images:
        main_image = axes[0, 0] if args.stress_front else axes[0, 1]
        main_image.text(.5, -.04, "Project color scale unavailable", ha="center", transform=main_image.transAxes)
    elif samples:
        ax = axes[0, 0]
        ax.set_axis_on()
        ax.clear()
        ax.set_title("Recorded CLO stress samples", loc="left")
        ids = list(dict.fromkeys(s["piece_id"] for s in samples))
        ax.scatter([s["stress_kpa"] for s in samples], [ids.index(s["piece_id"]) for s in samples], color="#426982")
        ax.set_yticks(range(len(ids)), ids)
        ax.set_xlabel("Measured sample stress (kPa)")
        axes[0, 1].set_title("")
        axes[0, 1].texts[0].set_text("Point samples only")
    else:
        axes[0, 0].texts[0].set_text("No CLO stress data supplied")

    limits = Normalize(args.strain_min_pct, args.strain_max_pct, clip=True)
    cmap = matplotlib.colormaps["viridis"]
    colors = cmap(limits(strains))
    depth = np.argsort(triangles[:, :, 2].mean(axis=1))
    mins = triangles.reshape(-1, 3).min(axis=0)
    maxs = triangles.reshape(-1, 3).max(axis=0)
    pad = max(maxs[0] - mins[0], maxs[1] - mins[1]) * .025
    for ax, facing in zip(axes[1], (1, -1)):
        order = depth if facing == 1 else depth[::-1]
        xy = triangles[:, :, :2].copy()
        xy[:, :, 0] *= facing
        ax.add_collection(PolyCollection(xy[order], facecolors=colors[order], edgecolors="face",
                                         linewidths=.10, antialiaseds=False))
        xx = sorted((facing * mins[0], facing * maxs[0]))
        ax.set_xlim(xx[0] - pad, xx[1] + pad)
        ax.set_ylim(mins[1] - pad, maxs[1] + pad)
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.set_title(f'Maximum principal strain · {"Front" if facing == 1 else "Back"}', loc="left")
    fig.colorbar(plt.cm.ScalarMappable(norm=limits, cmap=cmap), ax=axes[1], orientation="horizontal",
                 shrink=.64, aspect=35, label="Engineering strain (%) · values outside scale use end colors")
    rendered = io.BytesIO()
    fig.savefig(rendered, format="png", dpi=155)
    plt.close(fig)
    return rendered.getvalue()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--piece-ids", help="Comma-separated IDs in verified GLB primitive order")
    for option in ("project", "stress-front", "stress-back", "stress-samples"):
        parser.add_argument(f"--{option}", type=Path)
    parser.add_argument("--stress-crop", type=int, nargs=4, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"))
    parser.add_argument("--position-mm-per-unit", type=float, default=1)
    parser.add_argument("--uv-mm-per-unit", type=float, default=1)
    parser.add_argument("--min-triangle-area-mm2", type=float, default=.1)
    parser.add_argument("--threshold-pct", type=float, default=10)
    parser.add_argument("--strain-min-pct", type=float, default=-3)
    parser.add_argument("--strain-max-pct", type=float, default=25)
    parser.add_argument("--fold-threshold-deg", type=float, default=15)
    parser.add_argument("--fold-scale-max-deg", type=float, default=45)
    parser.add_argument("--title", default="CLO garment fit")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    numbers = (args.position_mm_per_unit, args.uv_mm_per_unit, args.min_triangle_area_mm2,
               args.threshold_pct, args.strain_min_pct, args.strain_max_pct,
               args.fold_threshold_deg, args.fold_scale_max_deg)
    if not all(math.isfinite(value) for value in numbers):
        parser.error("Numeric settings must be finite")
    if min(args.position_mm_per_unit, args.uv_mm_per_unit) <= 0 or args.min_triangle_area_mm2 < 0:
        parser.error("Coordinate scales must be positive and minimum area must be nonnegative")
    if args.strain_min_pct >= args.strain_max_pct:
        parser.error("Strain color limits must increase")
    if not (0 < args.fold_threshold_deg <= 180 and 0 < args.fold_scale_max_deg <= 180):
        parser.error("Fold threshold and color maximum must be in (0, 180]")
    return args


def export(args):
    paths = [args.out_dir / name for name in ("fit_statistics.json", "fit_statistics.csv", "fit_heatmaps.png",
                                             "fit_fold_views.png", "fit_fold_patterns.png")]
    if not args.overwrite and any(path.exists() for path in paths):
        raise ValueError("Fit output exists. Use an empty output folder or --overwrite.")
    cloth = read_cloth(args.glb)
    if args.piece_ids:
        ids = [piece.strip() for piece in args.piece_ids.split(",")]
        if len(ids) != len(cloth) or len(set(ids)) != len(ids) or not all(ids):
            raise ValueError("Piece IDs must be unique, nonempty, and match the number of primitives")
        if any(piece[0] in "=+-@" or any(ord(c) < 32 for c in piece) for piece in ids):
            raise ValueError("Piece IDs must be plain text labels")
    else:
        ids = [f"piece_{index:02d}" for index in range(1, len(cloth) + 1)]
    samples = read_stress_samples(args.stress_samples, ids)
    scale = read_scale(args.project)
    records, geometry = [], []
    fold_geometry = {}
    for piece_id, (xyz, uv, faces) in zip(ids, cloth):
        stats, mesh, strain = analyse_piece(xyz, uv, faces, args)
        folds, fold_geometry[piece_id] = measure_folds(xyz.astype(np.float64) * args.position_mm_per_unit, uv, faces,
                                                       args.fold_threshold_deg)
        readings = [s["stress_kpa"] for s in samples if s["piece_id"] == piece_id]
        records.append({
            "piece_id": piece_id, **stats, "strain_threshold_pct": args.threshold_pct,
            "stress_sample_count": len(readings),
            "stress_sample_median_kpa": float(np.median(readings)) if readings else None,
            "stress_sample_max_kpa": max(readings) if readings else None,
            **folds,
        })
        geometry.append((mesh, strain))
    screenshots = {side: path.name for side, path in (("front", args.stress_front), ("back", args.stress_back)) if path}
    payload = {
        "schema_version": 2,
        "strain": {
            "source": args.glb.name,
            "definition": "Maximum principal engineering strain in percent. Percentiles use 2D triangle area weights.",
            "raw_position_mm_per_unit": args.position_mm_per_unit,
            "raw_uv_mm_per_unit": args.uv_mm_per_unit,
            "min_triangle_area_mm2": args.min_triangle_area_mm2,
            "display_limits_pct": [args.strain_min_pct, args.strain_max_pct],
        },
        "stress": {
            "numeric_availability": "point_samples" if samples else "unavailable",
            "screenshot_files": screenshots,
            "sample_source": args.stress_samples.name if args.stress_samples else None,
            "scale_source": args.project.name if scale else None,
            "display_scale": scale,
            "samples": samples,
        },
        "folds": {
            "source": args.glb.name,
            "source_sha256": hashlib.sha256(args.glb.read_bytes()).hexdigest(),
            "definition": "Unsigned angle between consistently oriented neighboring faces. Flat is 0 degrees.",
            "scope": "Interior two-face edges within a primitive; identical raw position and UV duplicates are matched.",
            "threshold_deg": args.fold_threshold_deg,
            "display_max_deg": args.fold_scale_max_deg,
            "p95_weighting": "equal per edge",
            "length_share_basis": "draped length of measurable interior edges",
        },
        "pieces": records,
    }
    figure = plot_report(geometry, samples, args, scale)
    fold_views, fold_patterns = render_folds(fold_geometry, args.title, args.fold_threshold_deg, args.fold_scale_max_deg)
    table = io.StringIO(newline="")
    writer = csv.DictWriter(table, list(records[0]))
    writer.writeheader()
    writer.writerows(records)
    contents = [json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                table.getvalue(), figure, fold_views, fold_patterns]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for path, content in zip(paths, contents):
        staging = path.with_suffix(path.suffix + ".tmp")
        if isinstance(content, bytes):
            staging.write_bytes(content)
        else:
            staging.write_text(content, encoding="utf-8-sig" if path.suffix == ".csv" else "utf-8", newline="")
        os.replace(staging, path)
    print(json.dumps({"files": [str(p) for p in paths], "pieces": len(records),
                      "stress_numeric_availability": payload["stress"]["numeric_availability"]}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        export(parse_args())
    except (OSError, ValueError, KeyError, IndexError, BadZipFile, struct.error, np.linalg.LinAlgError) as error:
        raise SystemExit(f"Export failed: {error}") from error
