#!/usr/bin/env python3
"""Package CC0 MakeHuman geometry, native morph assets and anatomical rig.

Run after sparse-cloning makehumancommunity/makehuman into work/makehuman-upstream.
Only assets are redistributed; MakeHuman program logic is not included.
Measurement vertex IDs are factual landmarks on the CC0 mesh. Calibration,
skinning application and user interface are implemented independently.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / 'work/makehuman-upstream'
DEST = ROOT / 'web/human-studio/assets'
MEASURES = {
    'bust': ('bust-circ', 'Bust circumference', 72, 120),
    'waist': ('waist-circ', 'Waist circumference', 54, 108),
    'hips': ('hips-circ', 'Hip circumference', 80, 126),
    'shoulders': ('shoulder-dist', 'Shoulder breadth', 30, 46),
    'upperArm': ('upperarm-circ', 'Upper-arm circumference', 20, 40),
    'thigh': ('thigh-circ', 'Thigh circumference', 40, 76),
    'neck': ('neck-circ', 'Neck circumference', 28, 44),
    'upperArmLength': ('upperarm-length', 'Upper-arm length', 24, 38),
    'forearmLength': ('lowerarm-length', 'Forearm length', 18, 31),
    'thighLength': ('upperleg-height', 'Thigh length', 30, 52),
    'calf': ('calf-circ', 'Calf circumference', 28, 48),
}


def target(path):
    result = []
    for line in path.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        a = line.split()
        result.append([int(a[0]), *map(float, a[1:4])])
    return result


def build():
    data = UPSTREAM / 'makehuman/data'
    vertices, triangles, body = [], [], False
    for line in (data / '3dobjs/base.obj').read_text().splitlines():
        a = line.split()
        if not a:
            continue
        if a[0] == 'v':
            vertices.append(list(map(float, a[1:4])))
        elif a[0] == 'g':
            body = a[1] == 'body'
        elif a[0] == 'f' and body:
            ids = [int(v.split('/')[0]) - 1 for v in a[1:]]
            triangles += [[ids[0], ids[i], ids[i+1]] for i in range(1, len(ids)-1)]
    v = np.array(vertices, dtype=float)
    base_targets = [
        ('macrodetails/' + ethnicity + '-female-young.target', 1/3)
        for ethnicity in ['african', 'asian', 'caucasian']
    ] + [('macrodetails/universal-female-young-averagemuscle-averageweight.target', 1)]
    sources = ['3dobjs/base.obj', 'rigs/default.mhskel', 'rigs/default_weights.mhw']
    for rel, weight in base_targets:
        sources.append('targets/' + rel)
        for index, x, y, z in target(data / 'targets' / rel):
            v[index] += np.array([x, y, z]) * weight
    # MakeHuman asset coordinates are decimetres. Store actual centimetres.
    v *= 10
    reference = subprocess.check_output(['git', 'show', 'HEAD:makehuman/plugins/0_modeling_a_measurement.py'], cwd=UPSTREAM, text=True)
    rulers = {name: ast.literal_eval(ids) for name, ids in re.findall(r"self\.Measures\['measure/measure-([^']+)-decr\|incr'\]\s*=\s*(\[[^\]]+\])", reference)}
    controls = []
    for key, (native, label, minimum, maximum) in MEASURES.items():
        ids = rulers[native]
        if key == 'shoulders':
            # The upstream shoulder-dist ruler is one neck-to-shoulder segment.
            # This editor controls bilateral acromion breadth instead.
            point = v[ids[-1]].copy()
            point[0] *= -1
            mirror = int(np.argmin(np.linalg.norm(v-point, axis=1)))
            ids = [mirror, ids[-1]]
        if native.endswith('-circ') and ids[0] != ids[-1]:
            ids = ids + [ids[0]]
        morphs = {}
        for direction in ['incr', 'decr']:
            rel = 'targets/measure/measure-' + native + '-' + direction + '.target'
            sources.append(rel)
            morphs[direction] = [[i, round(x*10, 7), round(y*10, 7), round(z*10, 7)] for i, x, y, z in target(data / rel)]
        controls.append(dict(key=key, label=label, min=minimum, max=maximum,
                             path=ids, kind='circumference' if native.endswith('-circ') else 'landmark distance', **morphs))
    height_morphs = {}
    for direction, native in [('incr', 'maxheight'), ('decr', 'minheight')]:
        rel = 'targets/macrodetails/height/female-young-averagemuscle-averageweight-' + native + '.target'
        sources.append(rel)
        height_morphs[direction] = [[i, round(x*10, 7), round(y*10, 7), round(z*10, 7)] for i, x, y, z in target(data / rel)]
    controls.insert(0, dict(key='height', label='Standing height', min=145, max=195,
                           path=[], kind='standing height', **height_morphs))
    rig = json.loads((data / 'rigs/default.mhskel').read_text())
    weights = json.loads((data / 'rigs/default_weights.mhw').read_text())['weights']
    names = list(rig['bones'])
    influence = [[] for _ in vertices]
    for name, rows in weights.items():
        for index, weight in rows:
            influence[index].append((names.index(name), weight))
    skin_indices, skin_weights = [], []
    for rows in influence:
        rows = sorted(rows, key=lambda r: -r[1])[:4] or [(names.index('root'), 1)]
        total = sum(weight for _, weight in rows)
        skin_indices += [row[0] for row in rows] + [0] * (4-len(rows))
        skin_weights += [round(row[1]/total, 8) for row in rows] + [0] * (4-len(rows))
    used = np.unique(triangles)
    ymin, ymax = v[used, 1].min(), v[used, 1].max()
    def measure(ids):
        points = v[ids]
        return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())
    payload = dict(schema=1, name='MakeHuman adult female', unit='cm',
                   vertices=np.round(v, 6).reshape(-1).tolist(), indices=np.array(triangles).reshape(-1).tolist(),
                   bodyVertexIds=used.tolist(), skinIndices=skin_indices, skinWeights=skin_weights,
                   bones=[dict(name=n, **rig['bones'][n]) for n in names], joints=rig['joints'],
                   controls=controls, baseMeasurements={c['key']: float(ymax-ymin) if c['key']=='height' else measure(c['path']) for c in controls},
                   baseHeight=float(ymax-ymin), license='CC0-1.0',
                   measurementDefinition='Neutral-pose surface tape paths or named landmark distances on the model; not measurements of a photographed person.')
    DEST.mkdir(exist_ok=True, parents=True)
    (DEST / 'human.json').write_text(json.dumps(payload, separators=(',', ':')))
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=UPSTREAM, text=True).strip()
    provenance = dict(repository='https://github.com/makehumancommunity/makehuman', commit=commit,
                      asset_license='CC0-1.0', sources={rel: hashlib.sha256((data/rel).read_bytes()).hexdigest() for rel in sources},
                      measurements='Vertex landmark IDs compatible with MakeHuman ruler definitions; circumference paths closed explicitly. No MakeHuman application logic redistributed.',
                      adaptations=['Adult female macro-target blend', 'decimetres to centimetres', 'body faces only; helper geometry excluded', 'four largest normalized skin weights', 'quads triangulated'],
                      vertices=len(v), body_vertices=len(used), triangles=len(triangles), bones=len(names),
                      human_sha256=hashlib.sha256((DEST/'human.json').read_bytes()).hexdigest())
    (DEST / 'provenance.json').write_text(json.dumps(provenance, indent=2))
    print(json.dumps(dict(vertices=len(v), body_vertices=len(used), triangles=len(triangles), bones=len(names),
                          height=payload['baseHeight'], measurements=payload['baseMeasurements'], bytes=(DEST/'human.json').stat().st_size), indent=2))


if __name__ == '__main__':
    build()
