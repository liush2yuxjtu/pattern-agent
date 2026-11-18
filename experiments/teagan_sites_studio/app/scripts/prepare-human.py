"""Reproducibly extract MakeHuman's CC0 body, retaining its source and license."""
from pathlib import Path
import hashlib, json

root = Path(__file__).resolve().parents[1] / 'dist/models'
raw = (root / 'makehuman-base.obj').read_bytes()
vertices, faces, joints = [], [], {}
group = ''
for line in raw.decode().splitlines():
    s = line.split()
    if not s:
        continue
    if s[0] == 'v':
        vertices.append(list(map(float, s[1:4])))
    elif s[0] == 'g':
        group = s[1]
    elif s[0] == 'f':
        ids = [int(x.split('/')[0]) - 1 for x in s[1:]]
        if group == 'body':
            faces.append(ids)
        elif group.startswith('joint-'):
            joints.setdefault(group[6:], set()).update(ids)
used = sorted({i for face in faces for i in face})
remap = {v: i for i, v in enumerate(used)}
triangles = [[remap[f[0]], remap[f[i]], remap[f[i+1]]]
             for f in faces for i in range(1, len(f)-1)]
# Exact horizontal mesh section at the chest; only the central torso loop is used.
segments = []
chest_y = 4.1
for face in faces:
    cuts = []
    for i, a in enumerate(face):
        p, q = vertices[a], vertices[face[(i+1) % len(face)]]
        if (p[1] <= chest_y < q[1]) or (q[1] <= chest_y < p[1]):
            t = (chest_y-p[1])/(q[1]-p[1])
            cuts.append([p[k]+t*(q[k]-p[k]) for k in range(3)])
    if len(cuts) == 2 and max(abs(p[0]) for p in cuts) < 1.6:
        segments.append(cuts)
length = sum(sum((a[k]-b[k])**2 for k in range(3))**.5 for a,b in segments)
revision = '3c701a8e52f09e69922e8b598d23be2d7dfc49e3'
model = {
    'schema': 'cc0-human-mesh/1', 'name': 'MakeHuman hm08 base body',
    'license': 'CC0-1.0', 'revision': revision,
    'sourceUrl': f'https://github.com/makehumancommunity/makehuman/blob/{revision}/makehuman/data/3dobjs/base.obj',
    'sourceSha256': hashlib.sha256(raw).hexdigest(),
    'processing': 'Body group only; fan triangulation of original quads. No MakeHuman application code is included.',
    'vertices': [vertices[i] for i in used], 'triangles': triangles,
    'joints': {name: [sum(vertices[i][k] for i in ids)/len(ids) for k in range(3)] for name,ids in joints.items()},
    'chestSection': {'y': chest_y, 'circumferenceSourceUnits': length, 'segments': segments},
    'bodyBounds': {'min': [min(vertices[i][k] for i in used) for k in range(3)],
                   'max': [max(vertices[i][k] for i in used) for k in range(3)]},
}
(root / 'makehuman-body.json').write_text(json.dumps(model,separators=(',',':')))
print(f'CC0 body: {len(used)} vertices, {len(triangles)} triangles; chest section {length:.9f} source units.')
