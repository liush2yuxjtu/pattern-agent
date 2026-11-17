#!/usr/bin/env python3
"""Independent NumPy audit of downloaded centimetre OBJ and skinned GLB.

Does not import the browser's calibration or skinning implementation.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np


def load_glb(path):
    raw = path.read_bytes()
    magic, version, length = struct.unpack_from('<III', raw)
    assert magic == 0x46546c67 and version == 2 and length == len(raw)
    chunks, offset = {}, 12
    while offset < len(raw):
        count, kind = struct.unpack_from('<II', raw, offset)
        chunks[kind] = raw[offset+8:offset+8+count]
        offset += count+8
    return json.loads(chunks[0x4e4f534a]), chunks[0x004e4942]


def read_accessor(gltf, binary, index):
    spec = gltf['accessors'][index]
    view = gltf['bufferViews'][spec['bufferView']]
    dtype = {5121: np.uint8, 5123: '<u2', 5125: '<u4', 5126: '<f4'}[spec['componentType']]
    width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[spec['type']]
    result = np.frombuffer(binary, dtype=dtype, count=spec['count']*width,
                           offset=view.get('byteOffset', 0)+spec.get('byteOffset', 0)).reshape(-1, width)
    if spec.get('normalized'):
        result = result.astype(float) / np.iinfo(dtype).max
    return result


def local_matrix(node):
    if 'matrix' in node:
        return np.array(node['matrix']).reshape(4, 4).T
    x, y, z, w = node.get('rotation', [0, 0, 0, 1])
    rotation = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                         [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                         [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    matrix = np.eye(4)
    matrix[:3, :3] = rotation @ np.diag(node.get('scale', [1, 1, 1]))
    matrix[:3, 3] = node.get('translation', [0, 0, 0])
    return matrix


def verify(directory, asset_path):
    geometry = json.loads((directory/'export-geometry.json').read_text())
    snapshot = json.loads((directory/'human-model.json').read_text())
    asset = json.loads(asset_path.read_text())
    rest = np.array(geometry['rest']).reshape(-1, 3)
    posed = np.array(geometry['posed'])
    measurements = {}
    for control in asset['controls']:
        if control['key'] == 'height':
            value = np.ptp(rest[asset['bodyVertexIds'], 1])
        else:
            value = np.linalg.norm(np.diff(rest[control['path']], axis=0), axis=1).sum()
        measurements[control['key']] = float(value)
    cm_error = max(abs(value-snapshot['dimensions'][key]) for key, value in measurements.items())
    reported_error = max(abs(value-snapshot['measuredNeutral'][key]) for key, value in measurements.items())
    assert cm_error < .2 and reported_error < .001, (cm_error, reported_error)
    obj = (directory/'human-posed-cm.obj').read_text().splitlines()
    obj_vertices = np.array([list(map(float, line.split()[1:4])) for line in obj if line.startswith('v ')])
    obj_error = float(np.abs(obj_vertices-posed).max())
    assert obj_error < 1e-5
    gltf, binary = load_glb(directory/'human-rigged.glb')
    parent = {child: index for index, node in enumerate(gltf['nodes']) for child in node.get('children', [])}
    world_cache = {}
    def world(index):
        if index not in world_cache:
            node = local_matrix(gltf['nodes'][index])
            world_cache[index] = world(parent[index]) @ node if index in parent else node
        return world_cache[index]
    skin_node = next(node for node in gltf['nodes'] if 'skin' in node)
    primitive = gltf['meshes'][skin_node['mesh']]['primitives'][0]
    attributes = primitive['attributes']
    positions = read_accessor(gltf, binary, attributes['POSITION'])
    indices = read_accessor(gltf, binary, attributes['JOINTS_0']).astype(int)
    weights = read_accessor(gltf, binary, attributes['WEIGHTS_0'])
    skin = gltf['skins'][skin_node['skin']]
    inverse = read_accessor(gltf, binary, skin['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    transforms = np.array([world(index) for index in skin['joints']]) @ inverse
    homogeneous = np.column_stack((positions, np.ones(len(positions))))
    result = np.zeros((len(positions), 4))
    for slot in range(4):
        result += np.einsum('nij,nj->ni', transforms[indices[:, slot]], homogeneous) * weights[:, slot, None]
    glb_body = result[geometry['bodyVertexIds'], :3]
    glb_error_m = float(np.abs(glb_body-posed*.01).max())
    assert glb_error_m < .00002, glb_error_m
    assert len(skin['joints']) == 163
    assert np.max(np.abs(weights.sum(axis=1)-1)) < 1e-5
    report = dict(verdict='PASS', scope='Independent decoded file geometry, centimetre tape paths and linear blend skinning; no anatomical recovery claim',
                  measurements_cm=measurements, max_target_error_cm=cm_error,
                  max_reported_measurement_error_cm=reported_error, max_obj_error_cm=obj_error,
                  max_glb_world_error_metres=glb_error_m, rig_joints=len(skin['joints']),
                  surface_vertices=len(posed), triangles=len(geometry['indices'])//3)
    (directory/'independent-geometry.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--asset', type=Path, default=Path(__file__).resolve().parents[1]/'web/human-studio/assets/human.json')
    args = parser.parse_args()
    verify(args.output, args.asset)
