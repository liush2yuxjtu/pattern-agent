#!/usr/bin/env python3
"""Independent position/topology fold inspector; standard library only.

Exit 0: this fold diagnostic PASS; 2: detected sharp edges; 3: invalid input.
This is not a cloth self-intersection, contact, material or physical-fit gate.
"""
import argparse
import gzip
import hashlib
import json
import math
import sys
import time
from pathlib import Path


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def uv_distance(p, a, b):
    vec = [b['x']-a['x'], b['y']-a['y']]
    delta = [p['x']-a['x'], p['y']-a['y']]
    t = max(0., min(1., dot(delta, vec)/(dot(vec, vec) or 1.)))
    return math.hypot(*(q-t*v for q, v in zip(delta, vec)))


def statistics(values):
    a = sorted(values)
    return {'count': len(a), 'p95': a[math.ceil(.95*len(a))-1] if a else None,
            'max': a[-1] if a else None}


def inspect(document, limit_deg=45., warning_deg=25., exclusion_mm=15.):
    document = document.get('geometry', document)
    if document.get('schema') != 'garment-body-wear-audit-input/2':
        raise ValueError('Expected declared schema: positions in metres, points2d in millimetres')
    if not (0 <= warning_deg <= limit_deg <= 180 and exclusion_mm >= 0):
        raise ValueError('Invalid declared limits')
    parts = []
    for p in document['garment']:
        part_id = p.get('partId', p.get('part', ''))
        if not part_id.startswith('sleeve'):
            continue
        positions, faces, uv = p['vertices'], p['triangles'], p['points2d']
        if not positions or not faces or len(positions) != len(uv):
            raise ValueError('Missing position/triangle/material-coordinate data')
        if not all(len(v) == 3 and all(math.isfinite(x) for x in v) for v in positions):
            raise ValueError('Nonfinite 3D position')
        if not all(math.isfinite(v[k]) for v in uv for k in ['x', 'y']):
            raise ValueError('Nonfinite material coordinate')
        seams = [e for e in p.get('boundary', []) if e['edge'].startswith('underarm')]
        if not seams:
            raise ValueError('Underarm semantics required; do not guess the excluded strip')
        if not all(0 <= e[k] < len(uv) for e in seams for k in ['a', 'b']):
            raise ValueError('Invalid underarm endpoint')
        normals, centers, invalid_faces, adjacent = [], [], [], {}
        for f, triangle in enumerate(faces):
            if len(triangle) != 3 or not all(isinstance(i, int) and 0 <= i < len(positions) for i in triangle):
                raise ValueError('Invalid triangle index')
            a, b, c = [positions[i] for i in triangle]
            n = cross(sub(b, a), sub(c, a))
            area2 = math.hypot(*n)
            normals.append([x/area2 for x in n] if math.isfinite(area2) and area2 > 1e-12 else None)
            centers.append([(a[k]+b[k]+c[k])/3 for k in range(3)])
            if not math.isfinite(area2) or area2 <= 1e-12:
                invalid_faces.append(f)
            for a, b in zip(triangle, triangle[1:]+triangle[:1]):
                key = tuple(sorted((a, b)))
                adjacent.setdefault(key, []).append((f, 1 if a < b else -1))
        edges, invalid_edges = [], []
        for (a, b), incidents in adjacent.items():
            if len(incidents) == 1:
                continue
            edge_id = f'{part_id}:{a}:{b}'
            fs = [f for f, _ in incidents]
            reason = 'non-manifold' if len(incidents) != 2 else 'inconsistent-winding' if incidents[0][1] == incidents[1][1] else 'degenerate-face' if any(normals[f] is None for f in fs) else None
            if reason:
                invalid_edges.append({'id': edge_id, 'reason': reason})
                continue
            n1, n2 = [normals[f] for f in fs]
            angle = math.degrees(math.atan2(math.hypot(*cross(n1, n2)), dot(n1, n2)))
            midpoint_uv = {k: (uv[a][k]+uv[b][k])/2 for k in ['x', 'y']}
            near = min(uv_distance(midpoint_uv, uv[s['a']], uv[s['b']]) for s in seams)
            if not math.isfinite(near):
                invalid_edges.append({'id': edge_id, 'reason': 'invalid-material-distance'})
                continue
            excluded = near < exclusion_mm
            classification = 'excluded' if excluded else 'sharp' if angle > limit_deg else 'warning' if angle > warning_deg else 'smooth'
            edges.append({'id': edge_id, 'a': a, 'b': b, 'faces': fs, 'angleDeg': angle,
                          'excluded': excluded, 'classification': classification,
                          'midpoint': [(positions[a][k]+positions[b][k])/2 for k in range(3)],
                          'midUv': midpoint_uv, 'endpointsUv': [uv[a], uv[b]],
                          'normals': [n1, n2], 'faceCenters': [centers[f] for f in fs],
                          'underarmDistanceMm': near,
                          'edgeLengthMm': math.dist(positions[a], positions[b])*1000})
        included = [e for e in edges if not e['excluded']]
        sharp = [e for e in included if e['classification'] == 'sharp']
        by_vertex = {}
        for e in sharp:
            for i in [e['a'], e['b']]:
                by_vertex.setdefault(i, []).append(e)
        seen, clusters = set(), []
        for e in sharp:
            if e['id'] in seen:
                continue
            pending, cluster = [e], []
            while pending:
                item = pending.pop()
                if item['id'] in seen:
                    continue
                seen.add(item['id']); cluster.append(item)
                for i in [item['a'], item['b']]:
                    pending.extend(x for x in by_vertex.get(i, []) if x['id'] not in seen)
            clusters.append({'edgeIds': [x['id'] for x in cluster], 'count': len(cluster),
                             'maxDeg': max(x['angleDeg'] for x in cluster),
                             'lengthMm': sum(x['edgeLengthMm'] for x in cluster)})
        parts.append({'partId': part_id, 'edges': edges, 'stats': statistics([e['angleDeg'] for e in included]),
                      'sharpCount': len(sharp), 'warningCount': sum(e['classification'] == 'warning' for e in included),
                      'excludedCount': len(edges)-len(included), 'invalidFaces': invalid_faces,
                      'invalidEdges': invalid_edges, 'clusters': clusters})
    if not parts:
        raise ValueError('No sleeves to inspect')
    included = [e for p in parts for e in p['edges'] if not e['excluded']]
    invalid = sum(len(p['invalidFaces'])+len(p['invalidEdges'])+(not p['stats']['count']) for p in parts)
    sharp = sum(p['sharpCount'] for p in parts)
    return {'schema': 'sleeve-crease-diagnostic/1', 'status': 'INVALID' if invalid else 'FAIL' if sharp else 'PASS',
            'scopeZh': '仅当前网格的袖片内部几何折角；材料、碰撞、自交与实物合体另验',
            'limits': {'limitDeg': limit_deg, 'warningDeg': warning_deg, 'underarmExclusionMm': exclusion_mm},
            'sharpCount': sharp, 'invalidCount': invalid,
            'peak': max(included, key=lambda e: e['angleDeg']) if included else None, 'parts': parts}


def read_document(path):
    payload = path.read_bytes()
    raw = gzip.decompress(payload) if path.suffix == '.gz' else payload
    return json.loads(raw), hashlib.sha256(payload).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--trace', type=Path)
    args = parser.parse_args()
    start = time.perf_counter_ns()
    try:
        doc, digest = read_document(args.input)
        result = inspect(doc)
        result['source'] = {'file': args.input.name, 'sha256': digest}
        code = 3 if result['status'] == 'INVALID' else 2 if result['status'] == 'FAIL' else 0
    except (KeyError, ValueError, TypeError, IndexError, OSError, gzip.BadGzipFile) as error:
        result, code = {'status': 'INVALID', 'reason': str(error)}, 3
    elapsed_us = (time.perf_counter_ns()-start)/1000
    result['performance'] = {'elapsedMs': elapsed_us/1000, 'kind': 'actual-input-read-and-inspection',
                             'notSimulationHistory': True}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    if args.trace:
        args.trace.parent.mkdir(parents=True, exist_ok=True)
        args.trace.write_text(json.dumps({'traceEvents': [{'name': 'independent-crease-inspection', 'cat': 'geometry',
            'ph': 'X', 'pid': 1, 'tid': 1, 'ts': 0, 'dur': elapsed_us,
            'args': {'status': result['status'], 'input': args.input.name, 'sharpCount': result.get('sharpCount')}}]}))
    print(json.dumps({'status': result['status'], 'sharpCount': result.get('sharpCount'),
                      'maxDeg': (result.get('peak') or {}).get('angleDeg'), 'elapsedMs': elapsed_us/1000}))
    return code


if __name__ == '__main__':
    sys.exit(main())
