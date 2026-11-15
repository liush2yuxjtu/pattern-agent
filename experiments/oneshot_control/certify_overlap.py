"""Reproduce positive-area overlap witnesses without legacy verification code.

The independent oracle supplies candidate pairs only. This file separately
solves a 2D linear program for a disk strictly inside both coplanar triangles,
then checks barycentric membership of the resulting 3D point. This is numerical
corroboration, not formal proof. No geometry or threshold is modified.

When saved alongside independent_oracle.py:
  python certify_overlap.py --npz CASE/arrays.npz --out witnesses.json --sample-count 54
  python certify_overlap.py --npz CASE/arrays.npz --out pair.json --pair 2236 2258

Use --oracle SOURCE.py if the oracle is elsewhere. Units are metres.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linprog


def cross2(a, b):
    return float(a[0] * b[1] - a[1] * b[0])


def witness_for_pair(vertices, triangles, pair, epsilon_m=1e-6):
    i, j = pair
    a, b = vertices[triangles[i]], vertices[triangles[j]]
    normal_a = np.cross(a[1] - a[0], a[2] - a[0])
    normal_b = np.cross(b[1] - b[0], b[2] - b[0])
    normal_a /= np.linalg.norm(normal_a)
    normal_b /= np.linalg.norm(normal_b)
    plane_separation = float(max(np.max(np.abs((b - a[0]) @ normal_a)),
                                 np.max(np.abs((a - b[0]) @ normal_b))))
    sine_angle = float(np.linalg.norm(np.cross(normal_a, normal_b)))
    report = dict(pair=[int(i), int(j)], vertex_indices=[triangles[i].tolist(), triangles[j].tolist()],
                  triangle_coordinates_m=[a.tolist(), b.tolist()],
                  shared_vertices=sorted(set(map(int, triangles[i])) & set(map(int, triangles[j]))),
                  plane_separation_m=plane_separation, sine_normal_angle=sine_angle,
                  positive_area_confirmed=False)
    if sine_angle > 1e-10 or plane_separation > max(epsilon_m * 1e-4, 1e-12):
        report['reason'] = 'not a coplanar candidate; this witness method does not apply'
        return report
    drop = int(np.argmax(np.abs(normal_a)))
    keep = [k for k in range(3) if k != drop]
    aa, bb = a[:, keep], b[:, keep]
    inequalities, bounds = [], []
    for triangle in (aa, bb):
        orientation = 1. if cross2(triangle[1] - triangle[0], triangle[2] - triangle[0]) > 0 else -1.
        for start, end in zip(triangle, np.roll(triangle, -1, axis=0)):
            edge = end - start
            inward = orientation * np.array([-edge[1], edge[0]])
            inward /= np.linalg.norm(inward)
            # n.(point-start)>=radius, with n normalized, places an entire
            # disk of this radius in the half-plane for this triangle edge.
            inequalities.append([-inward[0], -inward[1], 1.])
            bounds.append(-float(np.dot(inward, start)))
    solved = linprog([0., 0., -1.], A_ub=inequalities, b_ub=bounds,
                     bounds=[(None, None), (None, None), (0., None)], method='highs',
                     options={'primal_feasibility_tolerance': 1e-9, 'dual_feasibility_tolerance': 1e-9})
    report['lp_success'] = bool(solved.success)
    if not solved.success:
        report['reason'] = str(solved.message)
        return report
    point2 = solved.x[:2]
    point3 = np.zeros(3)
    point3[keep] = point2
    point3[drop] = a[0, drop] - np.dot(normal_a[keep], point2 - a[0, keep]) / normal_a[drop]

    def barycentric(triangle):
        denominator = cross2(triangle[1] - triangle[0], triangle[2] - triangle[0])
        return [cross2(triangle[1] - point2, triangle[2] - point2) / denominator,
                cross2(triangle[2] - point2, triangle[0] - point2) / denominator,
                cross2(triangle[0] - point2, triangle[1] - point2) / denominator]

    weights_a, weights_b = barycentric(aa), barycentric(bb)
    radius = float(solved.x[2])
    minimum_slack = float(np.min(np.asarray(bounds) - np.asarray(inequalities) @ solved.x))
    reconstructed_a, reconstructed_b = np.asarray(weights_a) @ a, np.asarray(weights_b) @ b
    residual = float(max(np.linalg.norm(reconstructed_a - point3), np.linalg.norm(reconstructed_b - point3)))
    positive = bool(radius > 1e-10 and min(weights_a + weights_b) > 1e-10
                    and residual < 1e-9 and minimum_slack >= -1e-9)
    report.update(witness_point_m=point3.tolist(), interior_disk_radius_m=radius,
                  barycentric_a=weights_a, barycentric_b=weights_b,
                  reconstruction_residual_m=residual, lp_minimum_constraint_slack_m=minimum_slack,
                  positive_area_confirmed=positive, disk_radius_exceeds_epsilon=bool(radius > epsilon_m))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--npz', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--oracle', type=Path, default=Path(__file__).resolve().with_name('independent_oracle.py'))
    parser.add_argument('--sample-count', type=int, default=10)
    parser.add_argument('--pair', nargs=2, type=int, action='append')
    parser.add_argument('--epsilon-m', type=float, default=1e-6)
    args = parser.parse_args(argv)
    spec = importlib.util.spec_from_file_location('independent_candidate_oracle', args.oracle)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    with np.load(args.npz) as data:
        vertices, triangles = data['cloth_vertices'], data['cloth_triangles']
    candidates = oracle.intersect_pairs(vertices, triangles, epsilon_m=args.epsilon_m)
    selected = args.pair or candidates[:max(0, args.sample_count)]
    reports = [witness_for_pair(vertices, triangles, pair, epsilon_m=args.epsilon_m) for pair in selected]
    result = dict(schema_version=1, input_sha256=hashlib.sha256(args.npz.read_bytes()).hexdigest(),
                  oracle_sha256=hashlib.sha256(args.oracle.read_bytes()).hexdigest(),
                  reproducer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  epsilon_m=args.epsilon_m, candidate_pair_count=len(candidates), witness_count=len(reports),
                  positive_area_witness_count=sum(r['positive_area_confirmed'] for r in reports), witnesses=reports,
                  method='Independent LP disk interior witness plus barycentric reconstruction, separate from oracle polygon-area calculation.',
                  limits='Numerical corroboration, not formal proof; no Blender/BVH/legacy imports.')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k != 'witnesses'}))
    return 0 if reports and all(r['positive_area_confirmed'] for r in reports) else 2


if __name__ == '__main__':
    raise SystemExit(main())
