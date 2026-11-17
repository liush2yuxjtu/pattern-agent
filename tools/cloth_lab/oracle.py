#!/usr/bin/env python3
"""Independent NumPy + trimesh reopener. Never imports the JS/C runtime solver.

Required: numpy, scipy, trimesh, rtree. Body sign is independently ray-tested on
the exact exported closed body. Tensor math is independently recomputed in f64.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]


def tensors(positions, uv, faces, material):
    triangles, flat = positions[faces], uv[faces]
    dm = np.stack((flat[:, 1]-flat[:, 0], flat[:, 2]-flat[:, 0]), axis=-1)
    ds = np.stack((triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0]), axis=-1)
    F = ds @ np.linalg.inv(dm)
    C = np.swapaxes(F, 1, 2) @ F
    green = (C-np.eye(2))*.5
    eu, ev, g, nu = (material[k] for k in ['Eu', 'Ev', 'G', 'nu'])
    den = 1-nu*nu*ev/eu
    q11, q22, q12 = eu/den, ev/den, nu*ev/den
    S = np.empty_like(green)
    S[:, 0, 0] = q11*green[:, 0, 0]+q12*green[:, 1, 1]
    S[:, 1, 1] = q12*green[:, 0, 0]+q22*green[:, 1, 1]
    S[:, 0, 1] = S[:, 1, 0] = 2*g*green[:, 0, 1]
    J = np.sqrt(np.maximum(np.linalg.det(C), 1e-16))
    sigma = F @ S @ np.swapaxes(F, 1, 2)/J[:, None, None]
    # Project onto an orthonormal tangent frame; exclude the zero normal stress.
    tangent, _ = np.linalg.qr(F)
    principal = np.linalg.eigvalsh(np.swapaxes(tangent, 1, 2) @ sigma @ tangent)
    eigen = np.linalg.eigvalsh(C)
    return np.column_stack((np.sqrt(np.maximum(eigen[:, 1], 0))-1,
                            np.sqrt(C[:, 0, 0])-1, np.sqrt(C[:, 1, 1])-1,
                            principal[:, 1],
                            np.sqrt(principal[:, 0]**2+principal[:, 1]**2-principal[:, 0]*principal[:, 1]),
                            green[:, 0, 0], green[:, 1, 1], green[:, 0, 1]))


def seam_audit(data, uv):
    n, m = data['grid']
    k = (n+1)*(m+1)
    lengths = []
    for p in range(2):
        boundary = uv[p*k+np.arange(m+1)*(n+1)]
        lengths.append(np.linalg.norm(np.diff(boundary, axis=0), axis=1).sum()*1000)
    mismatch = abs(lengths[0]-lengths[1])
    missing, reversed_pairing = False, False
    for name in ['S1', 'S2']:
        pairs = [s for s in data['seams'] if s['name'] == name]
        missing |= sum(s['active'] for s in pairs) != m+1
        ay = np.array([uv[s['a'], 0] for s in pairs])
        by = np.array([uv[s['b'], 0] for s in pairs])
        reversed_pairing |= np.any(np.diff(ay)*np.diff(by) <= 0)
    return dict(lengthsMm=lengths, mismatchMm=float(mismatch), missing=bool(missing), reversed=bool(reversed_pairing))


def segment_hits(mesh, starts, ends):
    direction = ends-starts
    lengths = np.linalg.norm(direction, axis=1)
    valid = lengths > 1e-9
    starts, direction, lengths = starts[valid], direction[valid], lengths[valid]
    direction /= lengths[:, None]
    locations, rays, _ = mesh.ray.intersects_location(starts, direction, multiple_hits=True)
    if not len(rays):
        return 0
    distances = np.einsum('ij,ij->i', locations-starts[rays], direction[rays])
    return int(np.sum((distances > 1e-6) & (distances < lengths[rays]-1e-6)))


def verify(data, body_source=None, intersections=True):
    x = np.array(data['positions'], dtype=float).reshape(-1, 3)
    uv = np.array(data['restUV'], dtype=float).reshape(-1, 2)
    faces = np.array(data['triangles'], dtype=int).reshape(-1, 3)
    assert np.isfinite(x).all() and faces.min() >= 0 and faces.max() < len(x)
    n, m = data['grid'];k=(n+1)*(m+1)
    assert x.shape == (2*k, 3) and faces.shape == (4*n*m, 3)
    params = data['parameters']
    # Reconstruct the flat pattern independently from its dimensional contract.
    expected = []
    for p in range(2):
        for j in range(m+1):
            w = params['topMm']+(params['bottomMm']-params['topMm'])*j/m
            for i in range(n+1):
                expected.append([j/m*params['lengthsMm'][p]/1000, (i/n-.5)*w/1000])
    assert np.max(abs(uv-np.array(expected))) < 1e-7, 'Flat pattern does not match dimensions'
    seam = seam_audit(data, uv)
    assert seam['mismatchMm'] < 1, seam
    assert not seam['missing'] and not seam['reversed'], seam
    pairs = np.array([[s['a'], s['b']] for s in data['seams'] if s['active']])
    max_gap = np.linalg.norm(x[pairs[:, 0]]-x[pairs[:, 1]], axis=1).max()*1000
    assert max_gap <= 2, f'Seam closure gap {max_gap} mm'
    actual = np.array(data['triangleFields']).reshape(-1, 8)
    expected_fields = tensors(x, uv, faces, data['material'])
    field_errors = np.max(abs(actual-expected_fields), axis=0)
    assert np.allclose(actual, expected_fields, rtol=3e-4, atol=np.array([2e-5,2e-5,2e-5,.15,.15,2e-5,2e-5,2e-5])), field_errors
    b = data['body']
    bv = np.array(b['positions']).reshape(-1, 3)
    bf = np.array(b['triangles']).reshape(-1, 3)
    if body_source:
        raw = body_source.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == b['sourceSha256']
        source = json.loads(raw)
        original = np.array(source['vertices']).reshape(-1, 3)*.01
        ids = np.array(source['indices']).reshape(-1, 3)
        used = np.unique(ids);expected_body=original[used].copy()
        expected_body[:, 1] -= expected_body[:, 1].min()
        remap=np.full(len(original),-1);remap[used]=np.arange(len(used))
        assert np.array_equal(remap[ids], bf), 'Body topology was substituted'
        assert np.max(abs(expected_body-bv)) < 1e-7, 'Body mesh was substituted'
    bv[:, 0] += b['offsetX']
    body = trimesh.Trimesh(bv, bf, process=False)
    assert body.is_watertight and body.is_winding_consistent, 'Body sign requires a closed oriented mesh'
    cloth = trimesh.Trimesh(x, faces, process=False)
    edges = cloth.edges_unique
    samples = np.concatenate([x, (x[edges[:, 0]]+x[edges[:, 1]])*.5, x[faces].mean(axis=1)])
    # trimesh sign is positive inside, opposite to the runtime convention.
    signed = trimesh.proximity.signed_distance(body, samples)
    inside = body.contains(samples)
    max_penetration = max(0, signed.max())*1000
    assert max_penetration <= .2, f'Actual body penetration {max_penetration} mm'
    assert not np.any(inside & (signed > .0002)), 'Independent ray parity found interior samples'
    hits = reverse_hits = 0
    if intersections:
        hits = segment_hits(body, x[edges[:, 0]], x[edges[:, 1]])
        be = body.edges_unique
        a, z = bv[be[:, 0]], bv[be[:, 1]]
        keep = np.all(np.minimum(a, z) <= x.max(axis=0)+1e-5, axis=1) & np.all(np.maximum(a, z) >= x.min(axis=0)-1e-5, axis=1)
        reverse_hits = segment_hits(cloth, a[keep], z[keep])
        assert hits == 0 and reverse_hits == 0, f'Actual mesh intersections: cloth edges {hits}, body edges {reverse_hits}'
    return dict(verdict='PASS', vertices=len(x), triangles=len(faces), bodyVertices=len(bv), bodyTriangles=len(bf),
                seam=seam, maxSeamGapMm=float(max_gap), maxBodyPenetrationMm=float(max_penetration),
                minBodyClearanceMm=float(-signed.max()*1000), sampledPoints=len(samples),
                insideSamples=int(inside.sum()), clothEdgeBodyHits=hits, bodyEdgeClothHits=reverse_hits,
                maxTensorFieldAbsoluteErrors=field_errors.tolist(),
                maxPrincipalStrainPercent=float(expected_fields[:, 0].max()*100),
                maxPrincipalCauchyKPa=float(expected_fields[:, 3].max()/1000),
                scope='Discrete mesh collision and stated synthetic constitutive model. Self-collision and physical fit NOT_RUN.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--body-source', type=Path, default=ROOT/'web/human-studio/assets/human.json')
    args=parser.parse_args()
    result=verify(json.loads(args.project.read_text()), args.body_source)
    text=json.dumps(result, indent=2)
    if args.output: args.output.write_text(text+'\n')
    print(text)
