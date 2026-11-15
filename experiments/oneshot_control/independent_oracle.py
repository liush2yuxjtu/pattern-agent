"""Independent static triangle-mesh oracle for the one-shot control experiment.

Implementation independence: NumPy/SciPy only. This file does not import or call
legacy verification code, Blender, mathutils, or BVHTree. Triangle intersection
uses bounding spheres/cKDTree, AABBs, and the separating-axis theorem (two face
normals plus nine edge-cross-edge axes). Coplanar area uses a separate 2D convex
intersection construction. Volume membership uses signed solid angles.

This is an independently implemented numerical check, not formal mathematical
proof and not a cloth physics/fit validator. Units are metres. Shared-vertex
triangle pairs are excluded only for a mesh's self-intersection check. Proper
noncoplanar intersections must straddle both planes by more than epsilon_m;
edge/point contacts are excluded. Exactly coplanar positive-area overlap counts.

  python independent_oracle.py --self-test --out SELF_TEST.json
  python independent_oracle.py --old-run RUN --out OLD_AUDIT.json
  python independent_oracle.py --npz CONTROL.npz --out CONTROL_AUDIT.json

Analytic tests always run before any old-scene or control comparison.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.spatial import cKDTree

EPSILON_M = 1e-6


def _mesh(vertices, triangles):
    vertices = np.asarray(vertices, dtype=np.float64)
    raw = np.asarray(triangles)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise ValueError('vertices must be a finite Nx3 array')
    if raw.ndim != 2 or raw.shape[1] != 3 or not np.issubdtype(raw.dtype, np.integer):
        raise ValueError('triangles must be an integer Mx3 array')
    triangles = raw.astype(np.int64, copy=False)
    if not len(triangles) or triangles.min() < 0 or triangles.max() >= len(vertices):
        raise ValueError('triangle indices missing or out of range')
    return vertices, triangles


def _cross2(a, b):
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def _inside2(point, triangle, numerical=1e-12):
    sides = _cross2(np.roll(triangle, -1, axis=0) - triangle, point - triangle)
    return bool(np.all(sides >= -numerical) or np.all(sides <= numerical))


def _coplanar_area(a, b, normal):
    """Area of the convex hull of contained vertices and edge intersections.

    This construction is separate from the 3D SAT predicate and does not use
    polygon clipping from the legacy implementation.
    """
    drop = int(np.argmax(np.abs(normal)))
    a, b = np.delete(a, drop, axis=1), np.delete(b, drop, axis=1)
    points = [p for p in a if _inside2(p, b)] + [p for p in b if _inside2(p, a)]
    for p, q in zip(a, np.roll(a, -1, axis=0)):
        r = q - p
        for c, d in zip(b, np.roll(b, -1, axis=0)):
            s = d - c
            determinant = float(_cross2(r, s))
            if abs(determinant) <= 1e-14 * max(np.linalg.norm(r) * np.linalg.norm(s), 1e-30):
                continue
            u = float(_cross2(c - p, s) / determinant)
            v = float(_cross2(c - p, r) / determinant)
            if -1e-12 <= u <= 1 + 1e-12 and -1e-12 <= v <= 1 + 1e-12:
                points.append(p + u * r)
    if len(points) < 3:
        return 0.
    ordered = sorted(set((float(p[0]), float(p[1])) for p in points))
    if len(ordered) < 3:
        return 0.
    lower, upper = [], []
    for point in ordered:
        point = np.asarray(point)
        while len(lower) >= 2 and _cross2(lower[-1] - lower[-2], point - lower[-1]) <= 1e-16:
            lower.pop()
        lower.append(point)
    for point in reversed(ordered):
        point = np.asarray(point)
        while len(upper) >= 2 and _cross2(upper[-1] - upper[-2], point - upper[-1]) <= 1e-16:
            upper.pop()
        upper.append(point)
    hull = np.asarray(lower[:-1] + upper[:-1])
    if len(hull) < 3:
        return 0.
    return abs(float(np.sum(_cross2(hull, np.roll(hull, -1, axis=0))))) / 2


def _sat_pairs(a, b, epsilon_m):
    """Vectorized SAT on paired triangle arrays, with explicit contact rules."""
    edges_a = np.roll(a, -1, axis=1) - a
    edges_b = np.roll(b, -1, axis=1) - b
    normal_a = np.cross(edges_a[:, 0], edges_a[:, 1])
    normal_b = np.cross(edges_b[:, 0], edges_b[:, 1])
    length_a = np.linalg.norm(normal_a, axis=1)
    length_b = np.linalg.norm(normal_b, axis=1)
    valid = (length_a > epsilon_m ** 2) & (length_b > epsilon_m ** 2)
    unit_a = normal_a / np.maximum(length_a[:, None], 1e-300)
    unit_b = normal_b / np.maximum(length_b[:, None], 1e-300)
    signed_b = np.einsum('pvd,pd->pv', b - a[:, :1], unit_a)
    signed_a = np.einsum('pvd,pd->pv', a - b[:, :1], unit_b)
    parallel = np.linalg.norm(np.cross(unit_a, unit_b), axis=1) <= 1e-10
    numerical_m = max(epsilon_m * 1e-4, 1e-12)
    coplanar = valid & parallel & (np.max(np.abs(signed_a), axis=1) <= numerical_m)
    strict_crossing = (valid & ~parallel
                       & (signed_a.min(axis=1) < -epsilon_m) & (signed_a.max(axis=1) > epsilon_m)
                       & (signed_b.min(axis=1) < -epsilon_m) & (signed_b.max(axis=1) > epsilon_m))
    result = np.zeros(len(a), dtype=bool)
    indices = np.flatnonzero(strict_crossing)
    if len(indices):
        aa, bb = a[indices], b[indices]
        edge_axes = np.cross(edges_a[indices, :, None, :], edges_b[indices, None, :, :]).reshape(-1, 9, 3)
        axes = np.concatenate([normal_a[indices, None], normal_b[indices, None], edge_axes], axis=1)
        lengths = np.linalg.norm(axes, axis=2)
        usable = lengths > 1e-14
        axes = axes / np.maximum(lengths[..., None], 1e-300)
        pa = np.einsum('pvd,pad->pav', aa, axes)
        pb = np.einsum('pvd,pad->pav', bb, axes)
        minimum_a, maximum_a = pa.min(axis=2), pa.max(axis=2)
        minimum_b, maximum_b = pb.min(axis=2), pb.max(axis=2)
        overlap = np.minimum(maximum_a, maximum_b) - np.maximum(minimum_a, minimum_b)
        separated = usable & (overlap < -numerical_m)
        # Face normals have zero span in their own triangle and cannot require
        # positive interval width. Other usable axes reject point/edge-only contact.
        nonflat = usable & ((maximum_a - minimum_a) > numerical_m) & ((maximum_b - minimum_b) > numerical_m)
        contact_only = nonflat & (overlap <= numerical_m)
        result[indices] = ~np.any(separated | contact_only, axis=1)
    for index in np.flatnonzero(coplanar):
        result[index] = _coplanar_area(a[index], b[index], unit_a[index]) > epsilon_m ** 2
    return result


def intersect_pairs(vertices, triangles, other_vertices=None, other_triangles=None, epsilon_m=EPSILON_M):
    """Return sorted [triangle_i, triangle_j] proper-intersection pairs.

    Bounding-sphere radii are bucketed by powers of two before cKDTree queries;
    every possible sphere overlap is included. Actual radii/AABBs reject loose
    candidates, and the independent SAT predicate decides the remaining pairs.
    """
    vertices, triangles = _mesh(vertices, triangles)
    same = other_vertices is None and other_triangles is None
    if (other_vertices is None) != (other_triangles is None):
        raise ValueError('other_vertices and other_triangles must be supplied together')
    if same:
        other_vertices, other_triangles = vertices, triangles
    else:
        other_vertices, other_triangles = _mesh(other_vertices, other_triangles)
    if epsilon_m <= 0:
        raise ValueError('epsilon_m must be positive')
    a, b = vertices[triangles], other_vertices[other_triangles]
    centres_a, centres_b = a.mean(axis=1), b.mean(axis=1)
    radii_a = np.linalg.norm(a - centres_a[:, None], axis=2).max(axis=1)
    radii_b = np.linalg.norm(b - centres_b[:, None], axis=2).max(axis=1)
    lower_a, upper_a, lower_b, upper_b = a.min(axis=1), a.max(axis=1), b.min(axis=1), b.max(axis=1)
    buckets = np.floor(np.log2(np.maximum(radii_b, epsilon_m))).astype(int)
    found = []
    for bucket in np.unique(buckets):
        group = np.flatnonzero(buckets == bucket)
        tree = cKDTree(centres_b[group])
        neighbours = tree.query_ball_point(centres_a, radii_a + radii_b[group].max() + epsilon_m)
        left, right = [], []
        for i, local_indices in enumerate(neighbours):
            if not local_indices:
                continue
            js = group[np.asarray(local_indices, dtype=int)]
            if same:
                js = js[js > i]
            if not len(js):
                continue
            sphere = np.linalg.norm(centres_b[js] - centres_a[i], axis=1) <= radii_a[i] + radii_b[js] + epsilon_m
            boxes = np.all(np.maximum(lower_a[i], lower_b[js]) <= np.minimum(upper_a[i], upper_b[js]) + epsilon_m, axis=1)
            js = js[sphere & boxes]
            if same and len(js):
                shares_vertex = np.any(triangles[i, :, None] == other_triangles[js, None, :], axis=(1, 2))
                js = js[~shares_vertex]
            if len(js):
                left.extend([i] * len(js))
                right.extend(js.tolist())
        left, right = np.asarray(left, dtype=int), np.asarray(right, dtype=int)
        for start in range(0, len(left), 2048):
            ii, jj = left[start:start + 2048], right[start:start + 2048]
            mask = _sat_pairs(a[ii], b[jj], epsilon_m)
            found.extend([[int(i), int(j)] for i, j in zip(ii[mask], jj[mask])])
    return sorted(found)


def mesh_audit(vertices, triangles):
    """Report edge connectivity, boundary cycles, orientation and degeneracy."""
    vertices, triangles = _mesh(vertices, triangles)
    edges = np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]])
    sorted_edges = np.sort(edges, axis=1)
    unique, inverse, counts = np.unique(sorted_edges, axis=0, return_inverse=True, return_counts=True)
    directions = np.where(edges[:, 0] < edges[:, 1], 1, -1)
    orientation = np.bincount(inverse, weights=directions, minlength=len(unique))
    parents = list(range(len(vertices)))

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for a, b in unique:
        ra, rb = root(int(a)), root(int(b))
        if ra != rb:
            parents[ra] = rb
    used = np.unique(triangles)
    components = len({root(int(i)) for i in used})
    boundary = unique[counts == 1]
    graph = defaultdict(list)
    for a, b in boundary:
        graph[int(a)].append(int(b)); graph[int(b)].append(int(a))
    unseen, cycles, boundary_components = set(graph), 0, 0
    while unseen:
        stack, component = [unseen.pop()], []
        while stack:
            i = stack.pop(); component.append(i)
            for j in graph[i]:
                if j in unseen:
                    unseen.remove(j); stack.append(j)
        boundary_components += 1
        cycles += int(all(len(graph[i]) == 2 for i in component))
    tri = vertices[triangles]
    double_area = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    volume_terms = np.einsum('ij,ij->i', tri[:, 0], np.cross(tri[:, 1], tri[:, 2])) / 6
    volumes = defaultdict(float)
    for face, value in zip(triangles, volume_terms):
        volumes[root(int(face[0]))] += float(value)
    nonmanifold = int(np.sum(counts > 2))
    winding_conflicts = int(np.sum((counts == 2) & (orientation != 0)))
    degenerate = int(np.sum(double_area <= EPSILON_M ** 2))
    duplicate_faces = len(triangles) - len(np.unique(np.sort(triangles, axis=1), axis=0))
    closed = not len(boundary) and not nonmanifold and not winding_conflicts and not degenerate
    euler = int(len(used) - len(unique) + len(triangles))
    return dict(vertex_count=len(vertices), used_vertex_count=len(used), orphan_vertices=len(vertices) - len(used),
                triangle_count=len(triangles), edge_count=len(unique), connected_components=components,
                boundary_edges=len(boundary), boundary_components=boundary_components, boundary_cycles=cycles,
                boundary_branch_vertices=sum(len(value) != 2 for value in graph.values()),
                nonmanifold_edges=nonmanifold, winding_conflicts=winding_conflicts,
                degenerate_triangles=degenerate, duplicate_faces=int(duplicate_faces), euler_characteristic=euler,
                closed_oriented_edge_manifold=bool(closed),
                component_signed_volumes_m3=list(volumes.values()),
                outward_closed_components=bool(closed and all(v > EPSILON_M ** 3 for v in volumes.values())),
                limits='Edge-manifold/connectivity audit; self-intersection requires intersect_pairs separately.')


def winding_numbers(vertices, triangles, points):
    """Vectorized signed solid-angle winding; bounded batches avoid huge arrays."""
    vertices, triangles = _mesh(vertices, triangles)
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError('points must be finite Px3')
    tri = vertices[triangles]
    values = []
    for start in range(0, len(points), 16):
        delta = tri[None] - points[start:start + 16, None, None]
        a, b, c = delta[:, :, 0], delta[:, :, 1], delta[:, :, 2]
        na, nb, nc = np.linalg.norm(a, axis=2), np.linalg.norm(b, axis=2), np.linalg.norm(c, axis=2)
        triple = np.einsum('pfi,pfi->pf', a, np.cross(b, c))
        denominator = (na * nb * nc + np.einsum('pfi,pfi->pf', a, b) * nc
                       + np.einsum('pfi,pfi->pf', b, c) * na + np.einsum('pfi,pfi->pf', c, a) * nb)
        values.extend((np.sum(2 * np.arctan2(triple, denominator), axis=1) / (4 * np.pi)).tolist())
    return np.asarray(values)


def point_inside_mesh(vertices, triangles, points):
    """Strict interior membership by |winding|>0.5; boundary samples are excluded.

    Callers should first establish a closed, oriented, non-self-crossing body and
    choose claimed skeletal samples away from its surface. Returned membership
    supplies the path/body correspondence check missing from the legacy gate.
    """
    return np.abs(winding_numbers(vertices, triangles, points)) > .5000001


def _cube():
    vertices = np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]], dtype=float)
    triangles = np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
    return vertices, triangles


def analytic_tests():
    """Known geometry first; no legacy result is consulted to set expectations."""
    a = np.array([[0.,0,0],[1.,0,0],[0.,1,0]])
    cases = [
        ('parallel_disjoint', a, a + [0,0,1], False),
        ('noncoplanar_crossing', a, np.array([[.25,-.1,-1],[.25,-.1,1],[.25,.8,0]]), True),
        ('noncoplanar_edge_contact', a, np.array([[0.,0,0],[1.,0,0],[0.,-1,1]]), False),
        ('noncoplanar_point_contact_with_plane_straddling', a, np.array([[.5,.5,-1],[.5,.5,1],[.5,2.5,1]]), False),
        ('coplanar_positive_area', a, np.array([[.1,.1,0],[.8,.1,0],[.1,.8,0]]), True),
        ('coplanar_edge_contact', a, np.array([[0.,0,0],[1.,0,0],[0.,-1,0]]), False),
        ('coplanar_point_contact', a, a + [1,0,0], False),
        ('sub_epsilon_parallel_gap', a, a + [0,0,EPSILON_M/2], False),
        ('in_plane_disjoint', a, a + [2,0,0], False)]
    rows = []
    for name, aa, bb, expected in cases:
        vertices = np.concatenate([aa, bb]); triangles = np.array([[0,1,2],[3,4,5]])
        observed = bool(intersect_pairs(vertices, triangles))
        passed = observed == expected
        rows.append(dict(name=name, expected_intersection=expected, observed_intersection=observed, passed=passed))
        if not passed:
            raise AssertionError(f'{name}: expected {expected}, got {observed}')
    # Separate meshes may reuse numeric vertex IDs; those are not adjacency.
    one = np.array([[0,1,2]])
    for name, bb, expected in (
            ('cross_mesh_noncoplanar_positive', cases[1][2], True),
            ('cross_mesh_coplanar_positive', cases[4][2], True),
            ('cross_mesh_disjoint_negative', a + [0,0,1], False)):
        observed = bool(intersect_pairs(a, one, bb, one))
        assert observed == expected, name
        rows.append(dict(name=name, expected_intersection=expected, observed_intersection=observed, passed=True))
    shared_v = np.array([[-1.,-1,0],[1.,-1,0],[0.,1,0],[.5,0,-1],[.5,0,1]])
    assert intersect_pairs(shared_v, np.array([[0,1,2],[0,3,4]])) == []
    rows.append(dict(name='shared_vertex_exclusion', passed=True))
    v, t = _cube(); audit = mesh_audit(v,t)
    assert audit['connected_components'] == 1 and audit['boundary_cycles'] == 0 and audit['outward_closed_components']
    assert abs(audit['component_signed_volumes_m3'][0] - 8.) < 1e-12
    rows.append(dict(name='closed_cube_connectivity_orientation_volume', passed=True))
    tube = mesh_audit(v,t[4:]); assert tube['boundary_cycles'] == 2 and tube['boundary_branch_vertices'] == 0
    rows.append(dict(name='open_square_tube_two_boundary_cycles', passed=True))
    inside = point_inside_mesh(v,t,np.array([[0.,0,0],[.8,-.8,.8],[2,0,0],[0,0,2]]))
    assert inside.tolist() == [True,True,False,False]
    rows.append(dict(name='independent_solid_angle_interior_exterior', passed=True))
    assert not point_inside_mesh(v,t,np.array([[2.,0,0],[3,0,0]])).any()
    rows.append(dict(name='claimed_path_outside_armless_cube_rejected', passed=True))
    crossing = cases[1][2]
    first = bool(intersect_pairs(np.concatenate([a,crossing]),np.array([[0,1,2],[3,4,5]])))
    reverse = bool(intersect_pairs(np.concatenate([a,crossing]),np.array([[2,1,0],[5,4,3]])))
    assert first and reverse
    rows.append(dict(name='intersection_invariant_to_face_winding', passed=True))
    return dict(test_count=len(rows), all_passed=True, tests=rows,
                epsilon_m=EPSILON_M, phase='analytic_before_legacy_comparison')


def audit_old(run, frame_numbers):
    saved = json.loads((run/'verification/verification.json').read_text())
    legacy = {int(row['frame']):row for row in saved['frames']}
    rows = []
    for frame in frame_numbers:
        source = run/'frames'/f'frame-{frame:04d}.npz'
        with np.load(source) as data:
            cv,ct,bv,bt = [data[key] for key in ('cloth_vertices','cloth_triangles','body_vertices','body_triangles')]
            paths = {side:data['path_'+side].copy() for side in ('L','R')}
        started = time.monotonic()
        pair_kinds = {
            'garment_self':(intersect_pairs(cv,ct),'self_intersection_pairs','self_intersection_examples'),
            'garment_body':(intersect_pairs(cv,ct,bv,bt),'cloth_body_intersection_pairs','cloth_body_intersection_examples'),
            'body_self':(intersect_pairs(bv,bt),'body_self_intersection_pairs','body_self_intersection_examples')}
        comparisons = {}
        for name,(pairs,count_key,example_key) in pair_kinds.items():
            current = set(map(tuple,pairs)); examples = set(map(tuple,legacy[frame].get(example_key,[])))
            comparisons[name] = dict(independent_count=len(pairs), legacy_count=legacy[frame][count_key],
                                     count_difference=len(pairs)-legacy[frame][count_key], pairs=pairs,
                                     saved_legacy_example_count=len(examples),
                                     saved_legacy_examples_missing_from_independent=sorted(examples-current),
                                     full_legacy_pair_set_available=False)
        path_audit = {}
        for side,path in paths.items():
            w = winding_numbers(bv,bt,path)
            path_audit[side] = dict(sample_count=len(path), interior_count=int(np.sum(np.abs(w)>.5000001)),
                                    winding_numbers=w.tolist(), strictly_inside_mask=(np.abs(w)>.5000001).tolist(),
                                    note='Full exported path includes deliberate end extensions; only claimed internal-bone samples should be required inside.')
        row = dict(frame=frame,source_npz_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                   garment_mesh=mesh_audit(cv,ct),body_mesh=mesh_audit(bv,bt),
                   comparisons=comparisons, exported_path_membership=path_audit,
                   elapsed_seconds=time.monotonic()-started)
        rows.append(row)
        print(json.dumps(dict(frame=frame,counts={k:[v['independent_count'],v['legacy_count']] for k,v in comparisons.items()},
                              elapsed_seconds=row['elapsed_seconds'])),flush=True)
    return dict(frame_count=len(rows),frames=rows,
                comparison_limit='Saved legacy report contains counts and at most20 example pairs, not complete pair sets.',
                independence='Independent SAT/cKDTree/solid-angle implementation; no imported legacy geometry or BVH. Not formal proof.')


def audit_npz(source):
    with np.load(source) as data:
        arrays = dict(data)
    cv,ct,bv,bt = [arrays[key] for key in ('cloth_vertices','cloth_triangles','body_vertices','body_triangles')]
    paths = {}
    for side in ('L','R'):
        for key in ('claimed_internal_path_'+side,'path_'+side):
            if key in arrays:
                w = winding_numbers(bv,bt,arrays[key])
                paths[key] = dict(points=np.asarray(arrays[key]).tolist(),winding_numbers=w.tolist(),
                                  inside=(np.abs(w)>.5000001).tolist(),all_inside=bool(np.all(np.abs(w)>.5000001)))
    return dict(source_file=source.name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                garment_mesh=mesh_audit(cv,ct),body_mesh=mesh_audit(bv,bt),
                garment_self_pairs=intersect_pairs(cv,ct),body_self_pairs=intersect_pairs(bv,bt),
                garment_body_pairs=intersect_pairs(cv,ct,bv,bt),path_body_correspondence=paths,
                limits=['Static geometry only; no cloth simulation or physical fit is established.',
                        'Require only explicitly claimed internal skeletal samples inside body; arbitrary path extensions can be outside.'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--old-run',type=Path)
    parser.add_argument('--frames',nargs='+',type=int,default=[1,66,81,141,153,241])
    parser.add_argument('--npz',type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args = parser.parse_args(argv)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    tests = analytic_tests()
    receipt = dict(schema_version=1,implementation='independent_oracle_numpy_scipy_sat_v1',
                   source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),analytic_tests=tests)
    # Persist analytic evidence before any legacy/control comparison is entered.
    args.out.with_name(args.out.stem+'-analytic-first.json').write_text(json.dumps(receipt,indent=2))
    if args.old_run:
        receipt['old_scene_audit'] = audit_old(args.old_run,args.frames)
    if args.npz:
        receipt['control_audit'] = audit_npz(args.npz)
    args.out.write_text(json.dumps(receipt,indent=2,allow_nan=False))
    print(json.dumps(dict(output=str(args.out),analytic_tests=tests['test_count'],all_analytic_passed=tests['all_passed'])))


if __name__ == '__main__':
    main()
