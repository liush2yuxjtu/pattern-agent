"""Locate exact self-crossing clusters and large strain in a saved cloth frame.

Run in Blender Python:
  blender -b --python verification/raised_diagnostic.py -- --run evidence/RUN --frame 141

Cluster size changes only diagnostic grouping, not collision acceptance. Exact
intersection predicates and tolerances are imported from the main verifier.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geometry import EPS, _intersection_pairs


def diagnose(arrays, topology, cluster_mm=50., cluster_count=5, edge_count=10):
    vertices, triangles = arrays['cloth_vertices'], arrays['cloth_triangles']
    rest = np.asarray(topology['rest_vertices'])
    if cluster_mm <= 0:
        raise ValueError('cluster size must be positive')
    pairs = _intersection_pairs(vertices, triangles)
    sleeve_sets = {side: set(topology['sleeve_triangles'][side]) for side in ('L', 'R')}

    def label(face):
        return next((side for side, ids in sleeve_sets.items() if face in ids), 'torso')

    surface_counts = Counter(' / '.join(sorted((label(i), label(j)))) for i, j in pairs)
    bins = {}
    for i, j in pairs:
        centre = vertices[triangles[[i, j]]].mean(axis=(0, 1))
        key = tuple(np.floor(centre / (cluster_mm / 1000)).astype(int))
        bins.setdefault(key, []).append((i, j, centre))
    clusters = []
    for _, items in sorted(bins.items(), key=lambda item: len(item[1]), reverse=True)[:cluster_count]:
        points = np.array([item[2] for item in items])
        clusters.append(dict(count=len(items), centroid=points.mean(axis=0).tolist(),
                             bounds=[points.min(axis=0).tolist(), points.max(axis=0).tolist()],
                             example_pair=[int(items[0][0]), int(items[0][1])]))
    edges = np.unique(np.sort(np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]],
                                              triangles[:, [2, 0]]]), axis=1), axis=0)
    initial_lengths = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
    current_lengths = np.linalg.norm(vertices[edges[:, 0]] - vertices[edges[:, 1]], axis=1)
    if np.any(initial_lengths <= EPS):
        raise ValueError('assembled rest mesh contains an edge at/below numerical epsilon')
    strain = current_lengths / initial_lengths - 1.
    worst = np.argsort(np.abs(strain))[-edge_count:][::-1]
    centres = (vertices[triangles[np.asarray(pairs, dtype=int).ravel()]].mean(axis=1) if pairs else None)
    return dict(pair_count=len(pairs), surface_pair_counts=dict(surface_counts), cluster_size_mm=cluster_mm,
                clusters=clusters,
                crossing_centroid_bounds=([centres.min(axis=0).tolist(), centres.max(axis=0).tolist()]
                                          if centres is not None else None),
                strain_abs_p95_pct=float(np.quantile(np.abs(strain), .95) * 100),
                strain_abs_max_pct=float(np.abs(strain).max() * 100),
                worst_edges=[dict(ids=edges[i].tolist(), rest_mm=float(initial_lengths[i] * 1000),
                                  current_mm=float(current_lengths[i] * 1000), strain_pct=float(strain[i] * 100),
                                  current_midpoint=vertices[edges[i]].mean(axis=0).tolist()) for i in worst],
                limits=['Strain is relative to an assembled synthetic rest mesh; fabric is uncalibrated.',
                        'Spatial bins summarize crossing locations; they do not identify a failure cause by themselves.'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--frame', type=int, default=141)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--cluster-mm', type=float, default=50.)
    args = parser.parse_args(argv)
    topology = json.loads((args.run / 'topology.json').read_text())
    source = args.run / 'frames' / f'frame-{args.frame:04d}.npz'
    with np.load(source) as data:
        result = diagnose(dict(data), topology, cluster_mm=args.cluster_mm)
    result.update(schema_version=1, frame=args.frame, source_frame_file=source.name)
    output = args.out or args.run / 'verification' / f'frame-{args.frame:04d}-diagnostic.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps(dict(output=str(output), frame=args.frame, pair_count=result['pair_count'],
                         strain_abs_p95_pct=result['strain_abs_p95_pct'], strain_abs_max_pct=result['strain_abs_max_pct'])))


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    main(argv)
