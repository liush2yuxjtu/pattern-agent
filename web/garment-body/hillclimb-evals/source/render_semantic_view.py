#!/usr/bin/env python3
"""Render actual skinned OBJ arm semantics in an existing orthographic guide camera.

Standalone CPU z-buffer; requires numpy and opencv-python. Does not fit or alter
geometry. --out is a PNG; sibling .json, .mask.png and .labels.png record provenance,
projection and visible labels (0 background, 1 other body, 2 L arm, 3 R arm).
This is supplemental generation control, not a grading oracle or collision test.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_obj(path):
    vertices, faces = [], []
    for line in Path(path).read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == 'v':
            vertices.append([float(x) for x in fields[1:4]])
        elif fields[0] == 'f':
            if len(fields) != 4:
                raise ValueError('Expected triangulated OBJ; polygon triangulation must match asset')
            face = []
            for token in fields[1:]:
                index = int(token.split('/')[0])
                face.append(index - 1 if index > 0 else len(vertices) + index)
            faces.append(face)
    v, f = np.asarray(vertices, float), np.asarray(faces, int)
    if v.ndim != 2 or v.shape[1] != 3 or f.ndim != 2 or f.shape[1] != 3:
        raise ValueError('Invalid triangular OBJ')
    if not np.isfinite(v).all() or f.min() < 0 or f.max() >= len(v):
        raise ValueError('Invalid OBJ coordinates or indices')
    return v, f


def projection(camera, view):
    spec = camera['views'][view]
    axis = spec['axis']
    if axis not in ('front', 'side', 'back'):
        raise ValueError('Only front, side, back orthographic axes are supported')
    width, height = int(camera['width']), int(camera['height'])
    scale = float(spec['px_per_cm'])
    cx, cy = map(float, spec['center_cm'])
    if width <= 0 or height <= 0 or not np.isfinite([scale, cx, cy]).all() or scale <= 0:
        raise ValueError('Invalid camera dimensions, center or scale')
    horizontal, depth = {'front': ([1, 0, 0], [0, 0, 1]),
                         'side': ([0, 0, 1], [1, 0, 0]),
                         'back': ([-1, 0, 0], [0, 0, -1])}[axis]
    matrix = np.array([[*(np.array(horizontal) * scale), width / 2 - scale * cx],
                       [0, -scale, 0, height / 2 + scale * cy]], float)
    return width, height, matrix, np.array(depth, float), axis


def semantic_faces(asset, v, f):
    body = np.asarray(asset['bodyVertexIds'], int)
    source_faces = np.asarray(asset['indices'], int).reshape(-1, 3)
    if len(v) == len(body):
        lookup = {int(source): compact for compact, source in enumerate(body)}
        expected = np.array([[lookup[int(i)] for i in face] for face in source_faces])
        vertex_ids = body
        mapping = 'compact OBJ vertex order equals bodyVertexIds order'
    elif len(v) == len(asset['vertices']) // 3:
        expected = source_faces
        vertex_ids = np.arange(len(v))
        mapping = 'full source vertex order'
    else:
        raise ValueError('OBJ vertex count matches neither compact body nor full source asset')
    if not np.array_equal(f, expected):
        raise ValueError('OBJ face order/indices do not exactly match asset topology and mapping')
    indices = np.asarray(asset['skinIndices'], int).reshape(-1, 4)[vertex_ids]
    weights = np.asarray(asset['skinWeights'], float).reshape(-1, 4)[vertex_ids]
    names = [bone['name'] for bone in asset['bones']]
    influence = []
    for side in ('L', 'R'):
        bones = [i for i, name in enumerate(names)
                 if name.startswith(('upperarm', 'lowerarm')) and name.endswith('.' + side)]
        if not bones:
            raise ValueError('Asset lacks upperarm/lowerarm bones for ' + side)
        influence.append((np.isin(indices, bones) * weights).sum(axis=1)[f].mean(axis=1))
    influence = np.array(influence)
    labels = np.ones(len(f), np.uint8)
    active = influence.max(axis=0) >= .25
    labels[active] = 2 + influence[:, active].argmax(axis=0)
    return labels, mapping


def render(asset_path, mesh_path, camera_path, view, out):
    asset = json.loads(Path(asset_path).read_text())
    camera = json.loads(Path(camera_path).read_text())
    v, f = read_obj(mesh_path)
    face_labels, mapping = semantic_faces(asset, v, f)
    width, height, matrix, depth_axis, axis = projection(camera, view)
    xy = np.column_stack((v, np.ones(len(v)))) @ matrix.T
    depth = v @ depth_axis
    z = np.full((height, width), -np.inf)
    labels = np.zeros((height, width), np.uint8)
    light = np.ones((height, width))
    for face, label in zip(f, face_labels):
        points = xy[face]
        x0, y0 = np.maximum(np.floor(points.min(axis=0)).astype(int), 0)
        x1, y1 = np.minimum(np.ceil(points.max(axis=0)).astype(int), [width - 1, height - 1])
        if x1 < x0 or y1 < y0:
            continue
        a, b, c = points
        den = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den) < 1e-10:
            continue
        yy, xx = np.mgrid[y0:y1+1, x0:x1+1] + .5
        u = ((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
        vv = ((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
        ww = 1-u-vv
        d = u*depth[face[0]]+vv*depth[face[1]]+ww*depth[face[2]]
        region = z[y0:y1+1, x0:x1+1]
        hit = (u >= -1e-9) & (vv >= -1e-9) & (ww >= -1e-9) & (d > region)
        region[hit] = d[hit]
        labels[y0:y1+1, x0:x1+1][hit] = label
        normal = np.cross(v[face[1]]-v[face[0]], v[face[2]]-v[face[0]])
        shade = .4 + .6 * abs(float(normal @ depth_axis)) / max(np.linalg.norm(normal), 1e-12)
        light[y0:y1+1, x0:x1+1][hit] = shade
    palette = np.array([[247, 250, 252], [188, 194, 203], [242, 139, 45], [41, 152, 218]])
    image = palette[labels].astype(float)
    image[labels > 0] *= light[labels > 0, None]
    image = np.clip(image, 0, 255).astype(np.uint8)
    out = Path(out)
    if out.suffix.lower() != '.png':
        raise ValueError('--out must be a PNG filename')
    inputs = {Path(p).resolve() for p in (asset_path, mesh_path, camera_path)}
    outputs = [out, out.with_suffix('.mask.png'), out.with_suffix('.labels.png'), out.with_suffix('.json')]
    if any(path.resolve() in inputs for path in outputs):
        raise ValueError('Output would overwrite input')
    out.parent.mkdir(parents=True, exist_ok=True)
    for path, data in [(out, image[:, :, ::-1]), (outputs[1], (labels > 0).astype(np.uint8)*255), (outputs[2], labels)]:
        if not cv2.imwrite(str(path), data):
            raise OSError('Failed writing ' + str(path))
    metadata = {'role': 'supplemental generation control; not grading oracle', 'view': view, 'axis': axis,
                'canvas': [width, height], 'camera_spec': camera['views'][view],
                'world_xyz1_to_pixel_xy': matrix.tolist(), 'depth_nearer_axis_xyz': depth_axis.tolist(),
                'screen_right_axis': {'front': '+X', 'side': '+Z', 'back': '-X'}[axis],
                'screen_up_axis': '+Y', 'side_parity': 'side horizontal +Z, nearer +X; horizontal reflection of conventional +X look-at/up+Y image' if axis == 'side' else None,
                'pixel_sampling': 'pixel centers x+0.5,y+0.5; opaque maximum-depth triangle z-buffer',
                'vertex_mapping': mapping, 'topology_verified': True, 'vertex_count': len(v), 'face_count': len(f),
                'labels': {'0': 'background', '1': 'torso/other body', '2': 'L upper/lower arm orange', '3': 'R upper/lower arm blue'},
                'face_label_rule': 'mean vertex upperarm/lowerarm weight >=0.25; strongest side wins; hands excluded',
                'visible_pixel_counts': {str(i): int((labels == i).sum()) for i in range(4)},
                'sources': {str(Path(p)): sha(p) for p in (asset_path, mesh_path, camera_path)},
                'script_sha256': sha(__file__), 'image_sha256': sha(out),
                'limitations': ['Requires exact source/compact topology and centimetres, Y up.', 'Face semantics use skin weights, not anatomical segmentation.', 'Visibility is triangle depth, not bone visibility; no cloth/collision inference.', 'Lighting differs from other renderers; camera is never auto-fit.']}
    outputs[3].write_text(json.dumps(metadata, indent=2)+'\n')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('asset', 'mesh', 'camera', 'view', 'out'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    result = render(args.asset, args.mesh, args.camera, args.view, args.out)
    print(json.dumps({'out': args.out, 'canvas': result['canvas'], 'axis': result['axis'],
                      'visible_pixel_counts': result['visible_pixel_counts']}))


if __name__ == '__main__':
    main()
