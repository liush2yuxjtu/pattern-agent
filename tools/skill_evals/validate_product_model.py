#!/usr/bin/env python3
"""Independent product-case model integrity gate, never a real-person fit oracle.

Reconstructs authored neutral morphs and tape measurements, checks saved OBJ,
then independently decodes the actual rigged GLB and its posed surface. Does
not import the browser renderer, its calibration solver or case fitting code.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
from PIL import Image


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def obj(path):
    vertices, faces = [], []
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            vertices.append([float(v) for v in line.split()[1:4]])
        elif line.startswith('f '):
            faces.append([int(v.split('/')[0])-1 for v in line.split()[1:]])
    return np.asarray(vertices), np.asarray(faces)


def frame(head, tail):
    y = tail-head
    y /= np.linalg.norm(y)
    x = np.cross(y, [0, 0, 1])
    if np.linalg.norm(x) < 1e-8:
        x = np.cross(y, [0, 1, 0])
    x /= np.linalg.norm(x)
    return np.column_stack((x, y, np.cross(x, y)))


def euler_xyz(angles):
    x, y, z = np.deg2rad(angles)
    a, b, c, d, e, f = np.cos(x), np.sin(x), np.cos(y), np.sin(y), np.cos(z), np.sin(z)
    return np.array([[c*e, -c*f, d], [a*f+b*e*d, a*e-b*f*d, -b*c], [b*f-a*e*d, b*e+a*f*d, a*c]])


def validate(workspace, repo, require_render_provenance=True):
    workspace, repo = Path(workspace), Path(repo)
    model = workspace/'model'
    asset_path = repo/'web/human-studio/assets/human.json'
    audit = module('product_state_audit', repo/'.agents/skills/garment-body-six-view/scripts/inspect_human_state.py')
    glb = module('product_glb_audit', repo/'scripts/verify_human_studio_geometry.py')
    state = json.loads((model/'final-state.json').read_text())
    asset_bytes = asset_path.read_bytes()
    state_report = audit.audit(state, asset_bytes, digest(asset_path), require_match=True)
    asset = json.loads(asset_bytes)
    rest = np.asarray(asset['vertices'], dtype=float).reshape(-1, 3)
    for control, weight in zip(asset['controls'], state['morphWeights']):
        for index, x, y, z in control['incr' if weight >= 0 else 'decr']:
            rest[index] += abs(weight)*np.array([x, y, z])
    ids = np.asarray(asset['bodyVertexIds'])
    rest[:, 1] -= rest[ids, 1].min()
    neutral, neutral_faces = obj(model/'final-neutral.obj')
    posed, posed_faces = obj(model/'final-posed.obj')
    require(neutral.shape == posed.shape == (len(ids), 3), 'Wrong surface vertex count')
    require(np.isfinite(neutral).all() and np.isfinite(posed).all(), 'Nonfinite OBJ vertex')
    id_map = {int(old): new for new, old in enumerate(ids)}
    expected_faces = np.array([id_map[int(v)] for v in asset['indices']]).reshape(-1, 3)
    require(np.array_equal(neutral_faces, expected_faces) and np.array_equal(posed_faces, expected_faces), 'OBJ topology differs from actual asset')
    neutral_delta = float(np.max(np.abs(neutral-rest[ids])))
    require(neutral_delta < 1e-5, 'Neutral OBJ disagrees with authored morph reconstruction')
    g, binary = glb.load_glb(model/'final-posed.glb')
    parent = {child: i for i, node in enumerate(g['nodes']) for child in node.get('children', [])}
    skin_index, skin_node = next((i, node) for i, node in enumerate(g['nodes']) if 'skin' in node)
    primitive = g['meshes'][skin_node['mesh']]['primitives'][0]
    attrs, skin = primitive['attributes'], g['skins'][skin_node['skin']]
    require(len(skin['joints']) == len(asset['bones']) == 163, 'Incorrect anatomical bone count')
    positions = glb.read_accessor(g, binary, attrs['POSITION'])
    require(positions.shape == rest.shape, 'GLB does not contain the authored rest buffer')
    glb_rest_delta = float(np.max(np.abs(positions-rest)))
    require(glb_rest_delta < 2e-5, 'GLB rest mesh differs from state morphs')
    require([g['nodes'][i]['name'] for i in skin['joints']] == [b['name'] for b in asset['bones']], 'GLB skin bone identity/order mismatch')
    heads = {b['name']: rest[asset['joints'][b['head']]].mean(axis=0) for b in asset['bones']}
    frames = {b['name']: frame(heads[b['name']], rest[asset['joints'][b['tail']]].mean(axis=0)) for b in asset['bones']}
    bone_error = 0.0
    for b, node_index in zip(asset['bones'], skin['joints']):
        name, parent_name = b['name'], b['parent']
        basis = frames[parent_name].T if parent_name in frames else np.eye(3)
        matrix = glb.local_matrix(g['nodes'][node_index])
        expected_rotation = basis @ frames[name] @ euler_xyz(state['poseDegrees'].get(name, [0, 0, 0]))
        expected_translation = basis @ (heads[name]-heads[parent_name]) if parent_name in frames else heads[name]
        bone_error = max(bone_error, float(np.max(abs(matrix[:3, :3]-expected_rotation))), float(np.max(abs(matrix[:3, 3]-expected_translation))))
    require(bone_error < 1e-6, 'Actual GLB bone transforms do not match saved joint angles')
    worlds = {}
    def world(i):
        if i not in worlds:
            local = glb.local_matrix(g['nodes'][i])
            worlds[i] = world(parent[i]) @ local if i in parent else local
        return worlds[i]
    joint_indices = glb.read_accessor(g, binary, attrs['JOINTS_0']).astype(int)
    weights = glb.read_accessor(g, binary, attrs['WEIGHTS_0'])
    require(np.max(abs(weights.sum(axis=1)-1)) < 1e-5, 'GLB skin weights not normalized')
    inverse = glb.read_accessor(g, binary, skin['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    transforms = np.array([world(i) for i in skin['joints']]) @ inverse
    homogeneous = np.column_stack((positions, np.ones(len(positions))))
    result = np.zeros((len(positions), 4))
    for slot in range(4):
        result += np.einsum('nij,nj->ni', transforms[joint_indices[:, slot]], homogeneous)*weights[:, slot, None]
    posed_delta_m = float(np.max(np.abs(result[ids, :3]-posed*.01)))
    require(np.isfinite(result).all() and posed_delta_m < .00002, 'Skinned GLB in metres disagrees with posed OBJ in cm')
    metrics = json.loads((model/'fit/metrics.json').read_text())
    gate = json.loads((model/'fit/input-hashes.json').read_text())
    require(metrics['protocol']['reference_image_sha256'] == gate['reference_image_sha256'], 'Metrics reference hashes disagree with frozen input gate')
    require(metrics['protocol']['frozen_mask_sha256'] == gate['frozen_mask_sha256'], 'Metrics mask hashes disagree with frozen input gate')
    iou_errors = {}
    for view in ('front', 'side', 'back'):
        with Image.open(model/'fit'/(view+'-reference-mask.png')) as image:
            mask = np.array(image.convert('L'))
        require(hashlib.sha256(mask.tobytes()).hexdigest() == gate['frozen_mask_sha256'][view], 'Changed frozen reference mask: '+view)
        reference = mask > 0
        for phase in ('initial', 'final'):
            with Image.open(model/'fit'/(view+'-'+phase+'-mask.png')) as image:
                projected = np.array(image.convert('L')) > 0
            require(reference.shape == projected.shape and reference.any() and projected.any(), 'Invalid comparison mask: '+view)
            intersection, union = np.count_nonzero(reference & projected), np.count_nonzero(reference | projected)
            values = {'iou': intersection/union, 'dice': 2*intersection/(reference.sum()+projected.sum())}
            reported = metrics[view][phase]['full_clothed_envelope_comparison']
            error = max(abs(float(value)-reported[key]) for key, value in values.items())
            require(error < 1e-10, 'Saved IoU/Dice differ from actual frozen masks: '+view+' '+phase)
            iou_errors[view+'_'+phase] = error
    depth = np.load(model/'final-renders/rawdepth.npy', allow_pickle=False)
    with Image.open(model/'final-renders/depth-valid.png') as image:
        valid = np.array(image.convert('L')) > 0
    require(depth.ndim == 2 and depth.shape == valid.shape and valid.any() and np.isfinite(depth[valid]).all(), 'Invalid numerical depth or empty depth validity mask')
    if require_render_provenance:
        provenance = json.loads((model/'render-provenance.json').read_text())
        require(provenance['generation'] == 'generation-2', 'Render provenance generation mismatch')
        for field, name in [('final_state_sha256', 'final-state.json'), ('final_posed_obj_sha256', 'final-posed.obj'), ('camera_sha256', 'camera.json')]:
            require(provenance[field] == digest(model/name), 'Stale render source: '+name)
        renders = model/'final-renders'
        declared = provenance['render_sha256']
        require(all(view+'.png' in declared for view in ('front','side','back','closeup','pose','depth')), 'Six render hashes required')
        require(set(declared) == {str(p.relative_to(renders)) for p in renders.rglob('*') if p.is_file()}, 'Render provenance file set mismatch')
        for name, sha in declared.items():
            path = (renders/name).resolve()
            require(renders.resolve() in path.parents and digest(path) == sha, 'Changed render artifact: '+name)
    return dict(verdict='PASS', scope='Independent model/file/pose integrity, not photograph recovery or cloth physics', asset_sha256=digest(asset_path), state=state_report, neutral_obj_max_delta_cm=neutral_delta, glb_rest_max_delta_cm=glb_rest_delta, glb_bone_transform_max_delta=bone_error, glb_vs_posed_obj_max_delta_m=posed_delta_m, render_provenance_checked=require_render_provenance, frozen_mask_iou_dice_max_error=max(iou_errors.values()), finite_depth_valid_pixels=int(valid.sum()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--skip-render-provenance', action='store_true')
    args = parser.parse_args()
    print(json.dumps(validate(args.workspace, args.repo, not args.skip_render_provenance), indent=2))
