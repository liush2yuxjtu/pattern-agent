"""Independent mesh-based sleeve and cloth acceptance checks.

Run in Blender Python, e.g.:
  blender -b --python verification/geometry.py -- --frames evidence/frames \
    --topology evidence/topology.json --out evidence/verification

This module never reads a scene's configured success flags. All geometric results
come from exported evaluated vertices, triangles, marked loops, and arm paths.
Distances are metres; EPS is fixed at 1 micrometre. Cloth self-intersection
excludes triangles sharing a vertex. Tangential contacts within EPS are allowed.
The checks sample saved frames; they do not certify all continuous solver time.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

EPS = 1e-6
SEAM_LIMIT_M = 0.002


def _mesh_info(vertices, triangles):
    edge_faces = {}
    parent = list(range(len(vertices)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for f, tri in enumerate(triangles):
        for a, b in zip(tri, np.roll(tri, -1)):
            a, b = int(a), int(b)
            ra, rb = root(a), root(b)
            if ra != rb:
                parent[ra] = rb
            edge_faces.setdefault(tuple(sorted((a, b))), []).append((f, a, b))
    boundary = [e for e, fs in edge_faces.items() if len(fs) == 1]
    nonmanifold = sum(len(fs) > 2 for fs in edge_faces.values())
    conflicts = sum(len(fs) == 2 and fs[0][1:] == fs[1][1:] for fs in edge_faces.values())
    boundary_adj = {}
    for a, b in boundary:
        boundary_adj.setdefault(a, []).append(b)
        boundary_adj.setdefault(b, []).append(a)
    bad_boundary = sum(len(n) != 2 for n in boundary_adj.values())
    remaining = set(boundary_adj)
    loops = 0
    while remaining:
        loops += 1
        stack = [remaining.pop()]
        while stack:
            for j in boundary_adj[stack.pop()]:
                if j in remaining:
                    remaining.remove(j)
                    stack.append(j)
    used = set(int(i) for i in triangles.ravel())
    components = len({root(i) for i in used})
    tri_v = vertices[triangles]
    cross = np.cross(tri_v[:, 1] - tri_v[:, 0], tri_v[:, 2] - tri_v[:, 0])
    degenerate = int(np.sum(np.linalg.norm(cross, axis=1) <= EPS * EPS))
    volumes = {}
    for tri, vol in zip(triangles, np.einsum('ij,ij->i', tri_v[:, 0], np.cross(tri_v[:, 1], tri_v[:, 2])) / 6):
        r = root(int(tri[0]))
        volumes[r] = volumes.get(r, 0.0) + float(vol)
    return dict(edge_faces=edge_faces, boundary_edges=boundary, boundary_loops=loops,
                boundary_branch_vertices=bad_boundary, nonmanifold_edges=nonmanifold,
                winding_conflicts=conflicts, components=components,
                degenerate_triangles=degenerate, component_signed_volumes=list(volumes.values()))


def _segment_triangle(p, q, tri, epsilon=EPS):
    """Return segment parameter for a nonparallel hit, including boundary hits."""
    direction = q - p
    edge1, edge2 = tri[1] - tri[0], tri[2] - tri[0]
    h = np.cross(direction, edge2)
    det = float(np.dot(edge1, h))
    scale = max(np.linalg.norm(direction) * np.linalg.norm(edge1) * np.linalg.norm(edge2), 1e-30)
    if abs(det) <= 1e-12 * scale:
        return None
    inv = 1.0 / det
    s = p - tri[0]
    u = float(inv * np.dot(s, h))
    bary_eps = epsilon / max(np.linalg.norm(edge1), np.linalg.norm(edge2), epsilon)
    if u < -bary_eps or u > 1 + bary_eps:
        return None
    z = np.cross(s, edge1)
    v = float(inv * np.dot(direction, z))
    if v < -bary_eps or u + v > 1 + bary_eps:
        return None
    t = float(inv * np.dot(edge2, z))
    t_eps = epsilon / max(np.linalg.norm(direction), epsilon)
    return min(1., max(0., t)) if -t_eps <= t <= 1 + t_eps else None


def _dedup_hits(hits):
    found = []
    for h in sorted(hits, key=lambda h: h['distance_m']):
        if found and abs(h['distance_m'] - found[-1]['distance_m']) <= 5 * EPS:
            if h['direction'] != found[-1]['direction']:
                found[-1]['direction'] = 0
        else:
            found.append(h.copy())
    return found


def _path_hits(path, triangles, outward_axis=None):
    hits = []
    offset = 0.
    for p, q in zip(path[:-1], path[1:]):
        seg_length = float(np.linalg.norm(q - p))
        if seg_length <= EPS:
            continue
        for face_i, tri in enumerate(triangles):
            t = _segment_triangle(p, q, tri)
            if t is None:
                continue
            normal = np.cross(tri[1] - tri[0], tri[2] - tri[0])
            if outward_axis is not None and np.dot(normal, outward_axis) < 0:
                normal = -normal
            dot = float(np.dot(q - p, normal))
            direction = 1 if dot > 1e-12 else -1 if dot < -1e-12 else 0
            hits.append(dict(distance_m=offset + t * seg_length,
                             direction=direction, triangle=face_i))
        offset += seg_length
    return _dedup_hits(hits)


def _cap(loop_vertices):
    centre = loop_vertices.mean(axis=0)
    return np.array([[centre, a, b] for a, b in zip(loop_vertices, np.roll(loop_vertices, -1, axis=0))])


def _point_on_path(path, distance):
    for p, q in zip(path[:-1], path[1:]):
        length = np.linalg.norm(q - p)
        if distance <= length:
            return p + (q - p) * distance / max(length, 1e-30)
        distance -= length
    return path[-1]


def _winding(points, triangles):
    result = []
    for point in points:
        a, b, c = (triangles[:, j] - point for j in range(3))
        la, lb, lc = (np.linalg.norm(v, axis=1) for v in (a, b, c))
        numerator = np.einsum('ij,ij->i', a, np.cross(b, c))
        denominator = (la * lb * lc + np.einsum('ij,ij->i', a, b) * lc
                       + np.einsum('ij,ij->i', b, c) * la
                       + np.einsum('ij,ij->i', c, a) * lb)
        result.append(float(np.sum(2 * np.arctan2(numerator, denominator)) / (4 * np.pi)))
    return np.array(result)


def _orient_cap_from_sleeve(vertices, loop, edge_faces):
    centre = vertices[loop].mean(axis=0)
    result = []
    for a, b in zip(loop, np.roll(loop, -1)):
        entries = edge_faces.get(tuple(sorted((int(a), int(b)))), [])
        if len(entries) != 1:
            raise ValueError('marked cap edge is not one sleeve-boundary edge')
        _, start, end = entries[0]
        result.append([centre, vertices[end], vertices[start]])
    return np.asarray(result)


def _area2(poly):
    if len(poly) < 3:
        return 0.
    return abs(sum(float(np.cross(poly[(i + 1) % len(poly)] - poly[i], poly[(i + 2) % len(poly)] - poly[i]))
                   for i in range(len(poly))))


def _coplanar_overlap(a, b, normal):
    """Convex polygon clipping; area, rather than touching edges, is a collision."""
    drop = int(np.argmax(np.abs(normal)))
    a, b = np.delete(a, drop, axis=1), np.delete(b, drop, axis=1)
    orient = np.cross(b[1] - b[0], b[2] - b[0])
    if abs(orient) <= EPS * EPS:
        return False
    sign = 1. if orient > 0 else -1.
    poly = list(a)
    for c, d in zip(b, np.roll(b, -1, axis=0)):
        if not poly:
            return False
        out = []
        for p, q in zip(poly, poly[1:] + poly[:1]):
            dp = sign * float(np.cross(d - c, p - c))
            dq = sign * float(np.cross(d - c, q - c))
            inp, inq = dp >= -EPS * EPS, dq >= -EPS * EPS
            if inp:
                out.append(p)
            if inp != inq:
                out.append(p + (q - p) * dp / (dp - dq))
        poly = out
    if len(poly) < 3:
        return False
    origin = poly[0]
    area = abs(sum(float(np.cross(poly[i] - origin, poly[i + 1] - origin)) for i in range(1, len(poly) - 1))) / 2
    return area > EPS * EPS


def _plane_slice(tri, distances):
    points = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        di, dj = distances[i], distances[j]
        if abs(di) <= EPS:
            points.append(tri[i])
        if (di < -EPS and dj > EPS) or (di > EPS and dj < -EPS):
            points.append(tri[i] + (tri[j] - tri[i]) * di / (di - dj))
    return points


def _tri_intersects(a, b, coplanar_is_collision=True):
    """Proper crossing or coplanar area overlap, ignoring EPS-scale contact."""
    na = np.cross(a[1] - a[0], a[2] - a[0])
    nb = np.cross(b[1] - b[0], b[2] - b[0])
    la, lb = np.linalg.norm(na), np.linalg.norm(nb)
    if min(la, lb) <= EPS * EPS:
        return False
    na, nb = na / la, nb / lb
    da, db = (a - b[0]) @ nb, (b - a[0]) @ na
    if ((np.min(da) > EPS or np.max(da) < -EPS) or
            (np.min(db) > EPS or np.max(db) < -EPS)):
        return False
    axis = np.cross(na, nb)
    if np.linalg.norm(axis) <= 1e-8:
        return bool(coplanar_is_collision and np.max(np.abs(da)) <= EPS * 1e-4 and _coplanar_overlap(a, b, na))
    if not (np.min(da) < -EPS and np.max(da) > EPS and np.min(db) < -EPS and np.max(db) > EPS):
        return False
    sa, sb = _plane_slice(a, da), _plane_slice(b, db)
    if len(sa) < 2 or len(sb) < 2:
        return False
    axis /= np.linalg.norm(axis)
    ia, ib = np.asarray(sa) @ axis, np.asarray(sb) @ axis
    return min(np.max(ia), np.max(ib)) - max(np.min(ia), np.min(ib)) > EPS


def _bvh(vertices, triangles, epsilon=EPS):
    return BVHTree.FromPolygons(vertices.tolist(), triangles.tolist(), all_triangles=True, epsilon=epsilon)



def _ray_parity(tree, point, direction):
    origin = Vector(point.tolist())
    direction = Vector(direction)
    direction.normalize()
    crossings = 0
    for _ in range(128):
        location, normal, face_i, distance = tree.ray_cast(origin, direction)
        if location is None:
            return crossings % 2 == 1
        crossings += 1
        origin = location + direction * (4 * EPS)
    raise ValueError('body parity ray exceeded the supported 128 intersections')


def _contains_points(vertices, triangles, points):
    """Global parity classification, with winding confirmation for ray disagreement.

    Nearest face normals alone are ambiguous at concave edges/vertices. Nearest
    distance is used only for penetration depth and the EPS contact allowance.
    """
    tree = _bvh(vertices, triangles, epsilon=0.)
    directions = ((1., .37139, .61803), (.281, 1., .437), (.513, .327, 1.))
    inside = []
    ambiguous = 0
    for point in points:
        nearest, normal, face_i, distance = tree.find_nearest(Vector(point.tolist()))
        if nearest is None:
            raise ValueError('body nearest-surface query failed')
        if distance <= EPS:
            inside.append((False, float(distance)))
            continue
        votes = [_ray_parity(tree, point, direction) for direction in directions]
        if all(v == votes[0] for v in votes):
            contained = votes[0]
        else:
            ambiguous += 1
            winding = abs(float(_winding(np.array([point]), vertices[triangles])[0]))
            if abs(winding - .5) <= 1e-4:
                raise ValueError('body sample has ambiguous parity and winding containment')
            contained = winding > .5
        inside.append((bool(contained), float(distance)))
    return inside, ambiguous

def _intersection_pairs(vertices_a, tris_a, vertices_b=None, tris_b=None):
    same = vertices_b is None
    if same:
        vertices_b, tris_b = vertices_a, tris_a
    bvh_a, bvh_b = _bvh(vertices_a, tris_a), _bvh(vertices_b, tris_b)
    candidates = bvh_a.overlap(bvh_b)
    a, b = vertices_a[tris_a], vertices_b[tris_b]
    found = []
    for i, j in candidates:
        if same and (i >= j or set(map(int, tris_a[i])) & set(map(int, tris_b[j]))):
            continue
        if _tri_intersects(a[i], b[j], coplanar_is_collision=same):
            found.append([int(i), int(j)])
    return found


def _sleeve_check(vertices, triangles, topology, side, path, whole_info):
    result = dict(pass_=False, errors=[])
    try:
        armhole = np.asarray(topology['armholes'][side], dtype=int)
        cuff = np.asarray(topology['cuffs'][side], dtype=int)
        sleeve_ids = np.asarray(topology['sleeve_triangles'][side], dtype=int)
        for name, loop in (('armhole', armhole), ('cuff', cuff)):
            if loop.ndim != 1 or len(loop) < 3 or len(set(map(int, loop))) != len(loop):
                raise ValueError(name + ' loop must have at least 3 distinct ordered vertices')
            if np.min(loop) < 0 or np.max(loop) >= len(vertices):
                raise ValueError(name + ' loop index out of range')
        if len(sleeve_ids) < 2 or np.min(sleeve_ids) < 0 or np.max(sleeve_ids) >= len(triangles):
            raise ValueError('sleeve triangle indices missing or out of range')
        sleeve_tris = triangles[sleeve_ids]
        info = _mesh_info(vertices, sleeve_tris)
        wanted_boundary = {tuple(sorted((int(a), int(b)))) for loop in (armhole, cuff) for a, b in zip(loop, np.roll(loop, -1))}
        if set(info['boundary_edges']) != wanted_boundary:
            result['errors'].append('sleeve boundary does not equal the two marked loops')
        if info['components'] != 1 or info['nonmanifold_edges'] or info['winding_conflicts'] or info['degenerate_triangles']:
            result['errors'].append('sleeve is disconnected, nonmanifold, inconsistently oriented, or degenerate')
        attached = all(len(whole_info['edge_faces'].get(tuple(sorted((int(a), int(b)))), [])) == 2
                       for a, b in zip(armhole, np.roll(armhole, -1)))
        cuff_open = all(len(whole_info['edge_faces'].get(tuple(sorted((int(a), int(b)))), [])) == 1
                        for a, b in zip(cuff, np.roll(cuff, -1)))
        if not attached:
            result['errors'].append('armhole is not attached to garment faces on both sides')
        if not cuff_open:
            result['errors'].append('cuff is not an actual open garment boundary')
        if path.ndim != 2 or path.shape[1] != 3 or len(path) < 2 or not np.isfinite(path).all():
            raise ValueError('arm path must be finite Px3, P>=2')
        axis = vertices[cuff].mean(axis=0) - vertices[armhole].mean(axis=0)
        if np.linalg.norm(axis) <= EPS:
            raise ValueError('armhole and cuff centres coincide')
        axis /= np.linalg.norm(axis)
        arm_axis = path[-1] - path[0]
        arm_axis /= max(np.linalg.norm(arm_axis), 1e-30)
        result['arm_axis_to_sleeve_axis_deg'] = float(np.degrees(np.arccos(np.clip(np.dot(axis, arm_axis), -1., 1.))))
        result['cuff_min_vertex_radius_mm'] = float(np.linalg.norm(vertices[cuff] - vertices[cuff].mean(axis=0), axis=1).min() * 1000)
        a_cap, c_cap = _cap(vertices[armhole]), _cap(vertices[cuff])
        a_hits, c_hits = _path_hits(path, a_cap, axis), _path_hits(path, c_cap, axis)
        wall_hits = _path_hits(path, vertices[sleeve_tris])
        own_crossing = (len(a_hits) == 1 and len(c_hits) == 1 and a_hits[0]['direction'] == 1
                        and c_hits[0]['direction'] == 1 and a_hits[0]['distance_m'] + EPS < c_hits[0]['distance_m'])
        other = 'R' if side == 'L' else 'L'
        other_hits = []
        for name in ('armholes', 'cuffs'):
            if other in topology.get(name, {}):
                loop = np.asarray(topology[name][other], dtype=int)
                other_hits.extend(_path_hits(path, _cap(vertices[loop])))
        result.update(armhole_crossings=len(a_hits), cuff_crossings=len(c_hits),
                      armhole_hits=a_hits, cuff_hits=c_hits, sleeve_wall_crossings=len(wall_hits),
                      wrong_side_crossings=len(other_hits), armhole_attached=attached, cuff_is_open=cuff_open,
                      interior_winding_min=None, interior_winding_max=None)
        if not own_crossing:
            result['errors'].append('path does not cross armhole then cuff once in the outward direction')
        if wall_hits:
            result['errors'].append('arm path intersects sleeve cloth surface')
        if other_hits:
            result['errors'].append('arm path traverses a contralateral marked loop')
        if own_crossing:
            # Samples include every interior segment midpoint and 15 evenly spaced
            # positions; wall crossings above guard unsampled excursions as well.
            start, end = a_hits[0]['distance_m'], c_hits[0]['distance_m']
            result['entry_to_exit_path_length_mm'] = float((end - start) * 1000)
            result['cuff_center_to_arm_path_mm'] = float(np.linalg.norm(vertices[cuff].mean(axis=0) - _point_on_path(path, end)) * 1000)
            sample_distances = list(np.linspace(start + .01 * (end - start), end - .01 * (end - start), 15))
            accumulated = 0.
            for p, q in zip(path[:-1], path[1:]):
                length = float(np.linalg.norm(q - p))
                mid = accumulated + length / 2
                if start + EPS < mid < end - EPS:
                    sample_distances.append(mid)
                accumulated += length
            shell = np.concatenate([vertices[sleeve_tris],
                                    _orient_cap_from_sleeve(vertices, armhole, info['edge_faces']),
                                    _orient_cap_from_sleeve(vertices, cuff, info['edge_faces'])])
            wind = np.abs(_winding(np.array([_point_on_path(path, d) for d in sample_distances]), shell))
            result['interior_winding_min'], result['interior_winding_max'] = float(wind.min()), float(wind.max())
            if not np.all(np.abs(wind - 1.) <= 1e-4):
                result['errors'].append('arm path does not remain inside the closed corresponding sleeve volume')
        result['pass_'] = not result['errors']
    except (KeyError, ValueError, IndexError, TypeError) as exc:
        result['errors'].append(str(exc))
    result['pass'] = result.pop('pass_')
    return result


def analyze_frame(arrays, topology, rest_vertices=None):
    """Measure one evaluated frame. Invalid input fails closed as JSON metrics."""
    result = dict(schema_version=1, epsilon_m=EPS, seam_limit_m=SEAM_LIMIT_M,
                  arm_entry_pass=False, cloth_sim_pass=False, errors=[])
    try:
        v = np.asarray(arrays['cloth_vertices'], dtype=float)
        t = np.asarray(arrays['cloth_triangles'], dtype=int)
        bv = np.asarray(arrays['body_vertices'], dtype=float)
        bt = np.asarray(arrays['body_triangles'], dtype=int)
        for name, verts, tris in (('cloth', v, t), ('body', bv, bt)):
            if verts.ndim != 2 or verts.shape[1] != 3 or len(verts) < 4 or not np.isfinite(verts).all():
                raise ValueError(name + ' vertices must be finite Nx3')
            if tris.ndim != 2 or tris.shape[1] != 3 or len(tris) < 4 or np.min(tris) < 0 or np.max(tris) >= len(verts):
                raise ValueError(name + ' triangles invalid')
        rest = np.asarray(rest_vertices if rest_vertices is not None else arrays.get('rest_vertices', topology.get('rest_vertices')), dtype=float)
        if rest.shape != v.shape or not np.isfinite(rest).all():
            raise ValueError('matching finite rest_vertices required for strain audit')
        cloth_info, body_info = _mesh_info(v, t), _mesh_info(bv, bt)
        for label, info in (('cloth', cloth_info), ('body', body_info)):
            result[label + '_topology'] = {k: val for k, val in info.items() if k not in ('edge_faces', 'boundary_edges')}
        cloth_valid = (cloth_info['nonmanifold_edges'] == 0 and cloth_info['winding_conflicts'] == 0
                       and cloth_info['boundary_branch_vertices'] == 0 and cloth_info['degenerate_triangles'] == 0
                       and cloth_info['components'] == int(topology.get('expected_components', 1)))
        if 'expected_openings' in topology:
            cloth_valid = cloth_valid and cloth_info['boundary_loops'] == int(topology['expected_openings'])
        body_valid = (not body_info['boundary_edges'] and body_info['nonmanifold_edges'] == 0
                      and body_info['winding_conflicts'] == 0 and body_info['degenerate_triangles'] == 0
                      and all(vol > EPS ** 3 for vol in body_info['component_signed_volumes']))
        result['body_topology_pass'] = bool(body_valid)
        body_self_pairs = _intersection_pairs(bv, bt)
        result['body_self_intersection_pairs'] = len(body_self_pairs)
        result['body_self_intersection_examples'] = body_self_pairs[:20]
        result['body_embedding_pass'] = not body_self_pairs
        body_valid = body_valid and not body_self_pairs
        result['cloth_structure_pass'], result['body_mesh_valid'] = bool(cloth_valid), bool(body_valid)
        if not cloth_valid:
            result['errors'].append('garment topology is invalid or does not match declared component/opening counts')
        if not body_valid:
            result['errors'].append('body must be closed, consistently outward oriented, and free of proper triangle self-intersection')
        sides = {side: _sleeve_check(v, t, topology, side, np.asarray(arrays['path_' + side], dtype=float), cloth_info)
                 for side in ('L', 'R')}
        result['sleeves'] = sides
        result['arm_entry_pass'] = bool(cloth_valid and all(x['pass'] for x in sides.values()))
        pairs = np.asarray(topology.get('seam_pairs', []), dtype=int)
        if pairs.ndim != 2 or pairs.shape[1] != 2 or len(pairs) == 0 or np.min(pairs) < 0 or np.max(pairs) >= len(v):
            raise ValueError('nonempty valid seam_pairs required')
        gaps = np.linalg.norm(v[pairs[:, 0]] - v[pairs[:, 1]], axis=1)
        result['seam_pair_count'] = len(pairs)
        result['welded_seam_pair_count'] = int(np.sum(pairs[:, 0] == pairs[:, 1]))
        result['seam_mode'] = 'welded_shared_vertices' if np.all(pairs[:, 0] == pairs[:, 1]) else 'vertex_pairs'
        result['seam_max_gap_mm'] = float(gaps.max() * 1000)
        result['seam_pass'] = bool(gaps.max() < SEAM_LIMIT_M)
        edges = np.array(list(cloth_info['edge_faces']), dtype=int)
        rest_lengths = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
        if np.any(rest_lengths <= EPS):
            raise ValueError('rest mesh has an edge of length <= epsilon')
        strain = np.linalg.norm(v[edges[:, 0]] - v[edges[:, 1]], axis=1) / rest_lengths - 1
        result['strain_abs_p95_pct'] = float(np.quantile(np.abs(strain), .95) * 100)
        result['strain_abs_max_pct'] = float(np.abs(strain).max() * 100)
        result['strain_extension_max_pct'] = float(strain.max() * 100)
        self_pairs = _intersection_pairs(v, t)
        body_pairs = _intersection_pairs(v, t, bv, bt)
        result['self_intersection_pairs'] = len(self_pairs)
        result['self_intersection_examples'] = self_pairs[:20]
        result['cloth_body_intersection_pairs'] = len(body_pairs)
        result['cloth_body_intersection_examples'] = body_pairs[:20]
        # Vertex + face-centre samples also detect enclosed garment geometry
        # which triangle/triangle intersection alone would miss. Global parity
        # avoids ambiguous nearest-face signs at concave shoulder edges.
        samples = np.concatenate([v, v[t].mean(axis=1)])
        inside, ambiguous = _contains_points(bv, bt, samples)
        depths = [distance for contained, distance in inside if contained]
        max_inside = max(depths, default=0.)
        count_inside = len(depths)
        result['body_sample_count'] = len(samples)
        result['body_inside_sample_count'] = count_inside
        result['body_containment_method'] = 'three_ray_parity_with_winding_confirmation'
        result['body_parity_disagreements'] = ambiguous
        result['body_penetration_max_mm'] = max_inside * 1000
        result['finite_pass'] = bool(np.isfinite(strain).all())
        result['cloth_sim_pass'] = bool(result['arm_entry_pass'] and cloth_valid and body_valid
                                         and result['seam_pass'] and not self_pairs and not body_pairs
                                         and not count_inside and result['finite_pass'])
    except (KeyError, ValueError, IndexError, TypeError) as exc:
        result['errors'].append(str(exc))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', required=True)
    parser.add_argument('--topology', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--start-frame', type=int, default=None, help='Optional inclusive subset for independent parallel verification')
    parser.add_argument('--end-frame', type=int, default=None, help='Optional inclusive subset for independent parallel verification')
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    topology = json.loads(Path(args.topology).read_text())
    files = sorted(Path(args.frames).glob('*.npz'))
    if args.start_frame is not None or args.end_frame is not None:
        files = [p for p in files if (args.start_frame is None or int(p.stem.rsplit('-', 1)[-1]) >= args.start_frame)
                 and (args.end_frame is None or int(p.stem.rsplit('-', 1)[-1]) <= args.end_frame)]
    rows = []
    previous = None
    # A parallel subset must retain the true preceding-frame motion rather
    # than treating its first selected frame as the start of the experiment.
    if files:
        first_number = int(files[0].stem.rsplit('-', 1)[-1])
        preceding = files[0].with_name(f'frame-{first_number - 1:04d}.npz')
        if first_number > 1 and preceding.exists():
            with np.load(preceding) as data:
                previous = data['cloth_vertices'].copy()
    for file in files:
        with np.load(file) as data:
            arrays = dict(data)
        row = analyze_frame(arrays, topology)
        row['frame_file'] = file.name
        row['frame'] = int(arrays['frame']) if 'frame' in arrays else int(file.stem.rsplit('-', 1)[-1])
        row['motion_rms_mm'] = (float(np.sqrt(np.mean(np.sum((arrays['cloth_vertices'] - previous) ** 2, axis=1))) * 1000)
                                if previous is not None else 0.)
        previous = arrays['cloth_vertices']
        rows.append(row)
        print(json.dumps({k: row.get(k) for k in ('frame', 'arm_entry_pass', 'cloth_sim_pass', 'seam_max_gap_mm',
                                                 'self_intersection_pairs', 'cloth_body_intersection_pairs', 'body_inside_sample_count')}), flush=True)
    report = dict(schema_version=1, frame_count=len(rows), all_arm_entry_pass=bool(rows) and all(r['arm_entry_pass'] for r in rows),
                  all_cloth_sim_pass=bool(rows) and all(r['cloth_sim_pass'] for r in rows), frames=rows,
                  limitations=['Saved-frame discrete geometry, not a continuous-time collision certificate.',
                               'Arm paths are skeletal centreline paths; full arm volume is separately covered by the cloth/body check.',
                               'Welded shared-vertex seams establish assembly closure, not a simulated sewing process or seam strength.',
                               'Strain is relative to the supplied assembled rest mesh; it is not calibrated fabric comfort.',
                               'Inside samples use three-ray global parity, winding confirmation on disagreement, and EPS-scale contact allowance.'])
    (out / 'verification.json').write_text(json.dumps(report, indent=2))
    columns = ['frame', 'frame_file', 'arm_entry_pass', 'cloth_sim_pass', 'seam_max_gap_mm', 'self_intersection_pairs',
               'cloth_body_intersection_pairs', 'body_self_intersection_pairs', 'body_inside_sample_count', 'body_penetration_max_mm',
               'strain_abs_p95_pct', 'strain_abs_max_pct', 'motion_rms_mm']
    with (out / 'per-frame.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    return 0 if report['all_cloth_sim_pass'] else 2


if __name__ == '__main__':
    tail = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    sys.exit(main(tail))
