#!/usr/bin/env python3
"""Build the self-contained WASM laboratory from pinned in-repo CC0/MIT assets.

ZIG and ESBUILD may point to local tool executables. No network at build/runtime.
Python dependency: numpy. The complete renderer, body, BVH and WASM are embedded.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT/'web/cloth-lab'
WORK = ROOT/'work/cloth-lab'


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
    assert len(v) <= 16000 and len(f) <= 30000 and len(nodes) <= 10000
    provenance = json.loads((ROOT/'web/human-studio/assets/provenance.json').read_text())
    return dict(positions=pack(v, '<f4'), normals=pack(normals, '<f4'), indices=pack(f, '<i4'),
                order=pack(order, '<i4'), nodes=base64.b64encode(b''.join(nodes)).decode(),
                vertices=len(v), triangles=len(f), nodeCount=len(nodes),
                heightMeters=float(np.ptp(v[:, 1])), sourceSha256=digest(source),
                source='web/human-studio/assets/human.json', provenance=provenance,
                collision='Full rendered triangle mesh, no radial or primitive proxy', license='CC0-1.0')


def build():
    WORK.mkdir(parents=True, exist_ok=True)
    zig = os.environ.get('ZIG') or shutil.which('zig')
    esbuild = os.environ.get('ESBUILD') or shutil.which('esbuild')
    if not zig or not esbuild:
        raise SystemExit('Set ZIG (tested 0.14.1) and ESBUILD (tested 0.25.12) to local tools.')
    subprocess.run([zig, 'cc', '-target', 'wasm32-freestanding', '-O3', '-nostdlib',
                    '-Wl,--no-entry', '-rdynamic', '-Wl,--initial-memory=16777216',
                    '-Wl,--max-memory=16777216', '-Wl,-z,stack-size=262144',
                    str(APP/'src/solver.c'), '-o', str(WORK/'solver.wasm')], check=True)
    subprocess.run([esbuild, str(APP/'src/app.js'), '--bundle', '--minify', '--format=iife',
                    '--legal-comments=inline', '--outfile='+str(WORK/'app.js')], check=True)
    body = make_body()
    wasm = (WORK/'solver.wasm').read_bytes()
    payload = dict(body=body, wasm=base64.b64encode(wasm).decode(),
                   wasmSha256=hashlib.sha256(wasm).hexdigest(),
                   sources={str(p.relative_to(ROOT)): digest(p) for p in [*sorted((APP/'src').iterdir()), Path(__file__)]},
                   renderer=json.loads((ROOT/'web/human-studio/vendor/provenance.json').read_text()))
    fingerprint = hashlib.sha256(json.dumps(dict(sources=payload['sources'], wasm=payload['wasmSha256'],
                                                  body=body['sourceSha256'], renderer=payload['renderer']['commit']),
                                            sort_keys=True).encode()).hexdigest()
    payload['buildFingerprint'] = fingerprint
    notices = (APP/'LICENSE.txt').read_text()+'\n\n'+(ROOT/'web/human-studio/vendor/THREE-LICENSE.txt').read_text()+'\n\n'+(ROOT/'web/human-studio/assets/MAKEHUMAN-CC0.txt').read_text()
    html = (APP/'src/template.html').read_text().replace('/*STYLE*/', (APP/'src/style.css').read_text())
    html = html.replace('/*PAYLOAD*/', json.dumps(payload, separators=(',', ':')))
    html = html.replace('/*APP*/', (WORK/'app.js').read_text()).replace('<!--NOTICES-->', '<!--\n'+notices.replace('--', '—')+'\n-->')
    html='\n'.join(line.rstrip() for line in html.splitlines())+'\n'
    (APP/'index.html').write_text(html)
    (APP/'build.json').write_text(json.dumps(dict(fingerprint=fingerprint, htmlSha256=digest(APP/'index.html'),
                                               htmlBytes=len(html.encode()), wasmSha256=payload['wasmSha256'],
                                               bodySourceSha256=body['sourceSha256'],
                                               vertices=body['vertices'], triangles=body['triangles'],
                                               tools=dict(zig=subprocess.check_output([zig, 'version'], text=True).strip(),
                                                          esbuild=subprocess.check_output([esbuild, '--version'], text=True).strip())), indent=2)+'\n')
    print((APP/'build.json').read_text())


if __name__ == '__main__':
    build()
