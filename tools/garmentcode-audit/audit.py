#!/usr/bin/env python3
"""Audit saved GarmentCode surfaces with CGAL and a separate NumPy oracle.

No solver or preview measurement code is imported. OBJ vertex IDs are preserved.
All geometry passed to predicates is in metres. A pass applies only to the
supplied discrete surfaces, never continuous collision, material, or real fit.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ORACLE_PATH = ROOT / 'experiments/oneshot_control/independent_oracle_v2.py'
spec = importlib.util.spec_from_file_location('independent_geometry', ORACLE_PATH)
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_obj(path, scale):
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('scale must be finite and positive')
    vertices, faces = [], []
    for line in Path(path).read_text().splitlines():
        if line.startswith('v '):
            values = line.split()[1:]
            if len(values) != 3:
                raise ValueError('only unweighted three-coordinate vertices are supported')
            vertices.append(list(map(float, values)))
        elif line.startswith('f '):
            values = line.split()[1:]
            if len(values) != 3:
                raise ValueError('triangular OBJ required; triangulation would change source faces')
            indices = [int(value.split('/')[0]) for value in values]
            if min(indices) <= 0:
                raise ValueError('only positive OBJ indices are supported')
            faces.append([i - 1 for i in indices])
    v, f = np.asarray(vertices, dtype=float) * scale, np.asarray(faces, dtype=np.int64)
    oracle._mesh(v, f)
    return v, f


def cgal_pairs(vertices, faces):
    from CGAL.CGAL_Polyhedron_3 import Polyhedron_3
    from CGAL.CGAL_Polygon_mesh_processing import self_intersections
    topology = oracle.mesh_audit(vertices, faces)
    if any(topology[key] for key in ('nonmanifold_edges', 'winding_conflicts', 'degenerate_triangles', 'duplicate_faces')):
        raise ValueError('CGAL surface contract requires a nondegenerate oriented edge manifold')
    with tempfile.TemporaryDirectory(prefix='garment-audit-') as temp:
        path = Path(temp) / 'surface.off'
        with path.open('w') as stream:
            stream.write(f'OFF\n{len(vertices)} {len(faces)} 0\n')
            np.savetxt(stream, vertices, fmt='%.17g')
            np.savetxt(stream, np.column_stack([np.full(len(faces), 3), faces]), fmt='%d')
        mesh = Polyhedron_3(str(path))
        if mesh.size_of_facets() != len(faces) or mesh.size_of_vertices() != len(vertices):
            raise ValueError('CGAL did not preserve the input mesh')
        for index, face in enumerate(mesh.facets()):
            face.set_id(index)
        pairs = []
        self_intersections(mesh, pairs)
        # SWIG Facet_pair supports [0]/[1], but its sequence fallback wraps
        # later indices instead of raising IndexError. Never iterate/unpack it.
        return sorted([sorted([int(pair[0].id()), int(pair[1].id())]) for pair in pairs])


def audit_surface(vertices, faces, body_v=None, body_f=None, body_mesh=None, body_volume_valid=True):
    topology = oracle.mesh_audit(vertices, faces)
    sat = oracle.intersect_pairs(vertices, faces)
    exact = cgal_pairs(vertices, faces)
    body_pairs = oracle.intersect_pairs(vertices, faces, body_v, body_f) if body_v is not None else None
    interior = None
    if body_v is not None and body_volume_valid:
        import trimesh
        collider = body_mesh if body_mesh is not None else trimesh.Trimesh(vertices=body_v, faces=body_f, process=False)
        if not collider.is_watertight or not collider.is_winding_consistent:
            raise ValueError('interior test requires a closed consistently oriented body')
        inside_ids = np.flatnonzero(collider.contains(vertices))
        if len(inside_ids):
            _, distances, _ = trimesh.proximity.closest_point(collider, vertices[inside_ids])
            interior = inside_ids[distances > oracle.EPSILON_M].tolist()
        else:
            interior = []
    return {'topology': topology, 'numpy_self_face_pairs': sat,
        'cgal_self_face_pairs': exact,
        'self_predicates_agree': sat == exact,
        'body_face_pairs': body_pairs,
        'strict_inside_vertex_ids': interior,
        'interior_verdict': 'NOT_RUN' if body_v is None else ('UNKNOWN_INVALID_BODY' if not body_volume_valid else ('FAIL' if interior else 'PASS_SAVED_VERTICES')),
        'collision_verdict': 'FAIL' if sat or exact or body_pairs or interior else ('UNKNOWN_BODY_VOLUME' if not body_volume_valid else ('PASS_DISCRETE_SURFACE' if body_pairs is not None else 'BODY_NOT_RUN')),
        'self_pair_centres_m': [((vertices[faces[a]].mean(0) + vertices[faces[b]].mean(0)) / 2).tolist() for a, b in sorted(set(map(tuple, sat + exact)))]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh', type=Path)
    parser.add_argument('--body', type=Path)
    parser.add_argument('--mesh-scale', type=float, default=.01)
    parser.add_argument('--body-scale', type=float, default=1.)
    parser.add_argument('--sequence', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if bool(args.sequence) == bool(args.mesh):
        parser.error('choose exactly one of --mesh and --sequence')
    if args.mesh and not args.body:
        parser.error('--mesh requires the actual --body collider')
    if args.out.exists():
        parser.error('report already exists; retain earlier results')
    start = time.perf_counter()
    analytic = oracle.analytic_tests()
    report = {'schema_version': 1, 'checker_sha256': sha256(__file__),
        'numpy_oracle_sha256': sha256(ORACLE_PATH), 'analytic_controls': analytic,
        'numpy_epsilon_m': oracle.EPSILON_M,
        'scope': 'Saved, supplied discrete surfaces only; no clearance or continuous-time guarantee',
        'material_stress': 'NOT_VALIDATED', 'physical_fit': 'NOT_RUN', 'frames': []}
    if args.sequence:
        archive = np.load(args.sequence, allow_pickle=False)
        positions, faces = archive['positions_m'], archive['faces']
        body_v, body_f = archive['body_vertices_m'], archive['body_faces']
        frame_ids = archive['frame_ids']
        if len(frame_ids) != len(positions) or len(np.unique(frame_ids)) != len(frame_ids):
            raise ValueError('frame IDs must uniquely match checkpoint arrays')
        report['source'] = {'sequence_sha256': sha256(args.sequence)}
    else:
        v, faces = read_obj(args.mesh, args.mesh_scale)
        body_v, body_f = read_obj(args.body, args.body_scale)
        positions, frame_ids = [v], ['saved_final']
        report['source'] = {'mesh_sha256': sha256(args.mesh), 'body_sha256': sha256(args.body),
                            'mesh_scale_to_m': args.mesh_scale, 'body_scale_to_m': args.body_scale}
    report['body_topology'] = oracle.mesh_audit(body_v, body_f)
    report['body_self_face_pairs_cgal'] = cgal_pairs(body_v, body_f)
    report['body_self_face_pairs_numpy'] = oracle.intersect_pairs(body_v, body_f)
    body_valid = not report['body_self_face_pairs_cgal'] and not report['body_self_face_pairs_numpy'] and report['body_topology']['closed_oriented_edge_manifold']
    report['body_volume_valid'] = bool(body_valid)
    report['body_validity'] = 'PASS' if body_valid else 'FAIL'
    import trimesh
    collider = trimesh.Trimesh(vertices=body_v, faces=body_f, process=False)
    for frame, v in zip(frame_ids, positions):
        result = audit_surface(v, faces, body_v, body_f, collider, body_valid)
        result['frame'] = frame.item() if hasattr(frame, 'item') else frame
        report['frames'].append(result)
        print(json.dumps({'frame': result['frame'], 'numpy_self_pairs': len(result['numpy_self_face_pairs']),
              'cgal_self_pairs': len(result['cgal_self_face_pairs']), 'body_pairs': len(result['body_face_pairs']),
              'inside_vertices': None if result['strict_inside_vertex_ids'] is None else len(result['strict_inside_vertex_ids'])}), flush=True)
    report['verdict'] = 'PASS_DISCRETE_SURFACES' if body_valid and all(r['collision_verdict'] == 'PASS_DISCRETE_SURFACE' for r in report['frames']) else 'FAIL'
    report['wall_seconds'] = time.perf_counter() - start
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'report': str(args.out), 'verdict': report['verdict']}))
    return 0 if report['verdict'] == 'PASS_DISCRETE_SURFACES' else 2


if __name__ == '__main__':
    raise SystemExit(main())
