#!/usr/bin/env python3
"""Pack the unchanged MakeHuman triangle mesh and deterministic collision BVH.

This build-time geometry helper is called by web/cloth-lab/build.js. It requires
NumPy (web/cloth-lab/requirements-build.txt), never a browser Python runtime.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import sys

try:
    import numpy as np
except ImportError:
    raise SystemExit('cloth-lab: Body preparation requires NumPy. Install it with '
                     'python -m pip install -r web/cloth-lab/requirements-build.txt')

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pack(array, dtype):
    return base64.b64encode(np.array(array, dtype=dtype).tobytes()).decode()


def make_body():
    source = ROOT/'web/human-studio/assets/human.json'
    data = json.loads(source.read_text())
    full = np.array(data['vertices']).reshape(-1, 3)/100
    f = np.array(data['indices']).reshape(-1, 3)
    used = np.unique(f)
    remap = np.full(len(full), -1)
    remap[used] = np.arange(len(used))
    v = full[used]
    v[:, 1] -= v[:, 1].min()  # Ground the actual asset; no shape scaling.
    f = remap[f]
    triangles = v[f]
    normals = np.zeros_like(v)
    crosses = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
    for j in range(3):
        np.add.at(normals, f[:, j], crosses)
    normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
    centers = triangles.mean(axis=1)
    nodes, order = [], []

    def recurse(ids):
        idx = len(nodes)
        nodes.append(None)
        lo = triangles[ids].min(axis=(0, 1))
        hi = triangles[ids].max(axis=(0, 1))
        if len(ids) <= 8:
            start = len(order)
            order.extend(ids.tolist())
            children = (-1, -1, start, len(ids))
        else:
            axis = np.argmax(np.ptp(centers[ids], axis=0))
            ids = ids[np.argsort(centers[ids, axis], kind='stable')]
            mid = len(ids)//2
            children = (recurse(ids[:mid]), recurse(ids[mid:]), 0, 0)
        nodes[idx] = struct.pack('<6f4i', *lo, *hi, *children)
        return idx

    recurse(np.arange(len(f)))
    if len(v) > 16000 or len(f) > 30000 or len(nodes) > 10000:
        raise ValueError('MakeHuman mesh exceeds the fixed WASM body allocation')
    provenance = json.loads((ROOT/'web/human-studio/assets/provenance.json').read_text())
    return dict(positions=pack(v, '<f4'), normals=pack(normals, '<f4'), indices=pack(f, '<i4'),
                order=pack(order, '<i4'), nodes=base64.b64encode(b''.join(nodes)).decode(),
                vertices=len(v), triangles=len(f), nodeCount=len(nodes),
                heightMeters=float(np.ptp(v[:, 1])), sourceSha256=digest(source),
                source='web/human-studio/assets/human.json', provenance=provenance,
                collision='Full rendered triangle mesh, no radial or primitive proxy', license='CC0-1.0')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='Write packed body JSON here (default: stdout)')
    args = parser.parse_args()
    body = json.dumps(make_body(), separators=(',', ':'))+'\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(body, encoding='utf-8')
    else:
        sys.stdout.write(body)


if __name__ == '__main__':
    main()
