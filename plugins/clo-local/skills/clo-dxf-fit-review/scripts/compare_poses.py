#!/usr/bin/env python3
"""Combine verified clo-fit-export results from one garment across poses."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path


def settings(report):
    strain = report["strain"]
    folds = report["folds"]
    return (
        strain["raw_position_mm_per_unit"], strain["raw_uv_mm_per_unit"],
        strain["min_triangle_area_mm2"], folds["threshold_deg"],
        folds["p95_weighting"], folds["length_share_basis"],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fit-skill", type=Path, default=Path(__file__).resolve().parents[2] / "clo-fit-export")
    args = parser.parse_args()
    scripts = args.fit_skill / "scripts"
    if not (scripts / "export_fit.py").is_file():
        parser.error("Provide the installed clo-fit-export directory with --fit-skill.")
    sys.path.insert(0, str(scripts))
    from export_fit import read_cloth
    import numpy as np

    poses = json.loads(args.manifest.read_text(encoding="utf-8"))["poses"]
    labels = [pose["name"] for pose in poses]
    if len(labels) < 2 or any(not name.strip() for name in labels) or len(set(labels)) != len(labels):
        parser.error("Provide at least two poses with distinct nonempty names.")
    base = args.manifest.resolve().parent
    metrics = ("strain_p50_pct", "strain_p95_pct", "area_above_threshold_pct",
               "strain_threshold_pct", "analysed_rest_area_mm2", "fold_p95_deg",
               "fold_edge_length_share_pct")
    rows = []
    for index, pose in enumerate(poses):
        mesh_path = base / pose["glb"]
        report = json.loads((base / pose["statistics"]).read_text(encoding="utf-8"))
        if hashlib.sha256(mesh_path.read_bytes()).hexdigest() != report["folds"]["source_sha256"]:
            parser.error(f"{pose['name']}: GLB differs from the mesh recorded by clo-fit-export.")
        pieces = report["pieces"]
        ids = [piece["piece_id"] for piece in pieces]
        thresholds = [piece["strain_threshold_pct"] for piece in pieces]
        mesh = read_cloth(mesh_path)
        if len(mesh) != len(pieces) or len(set(ids)) != len(ids):
            parser.error(f"{pose['name']}: piece records do not match primitives.")
        config = (ids, thresholds, settings(report))
        if index == 0:
            baseline = mesh
            baseline_config = config
        elif config != baseline_config:
            parser.error(f"{pose['name']}: piece order, identifiers, units or thresholds changed.")
        else:
            for name, (_, uv, faces), (_, ref_uv, ref_faces) in zip(ids, mesh, baseline):
                if (not np.array_equal(faces, ref_faces) or uv.shape != ref_uv.shape
                        or not np.allclose(uv, ref_uv, rtol=0, atol=1e-5)):
                    parser.error(f"{pose['name']} / {name}: flat coordinates or topology changed.")
        for piece in pieces:
            rows.append({"pose": pose["name"], "piece_id": piece["piece_id"],
                         **{key: piece[key] for key in metrics},
                         "fold_threshold_deg": report["folds"]["threshold_deg"],
                         "numeric_stress": report["stress"]["numeric_availability"]})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8-sig", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(poses)} poses, {len(rows)} piece records: {args.out}")


if __name__ == "__main__":
    main()
