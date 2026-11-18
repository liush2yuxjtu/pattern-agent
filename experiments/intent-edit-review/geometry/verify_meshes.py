"""Numerical self-check for the source-bound static review meshes.

An independent delivery audit must still read the HTML artifacts and reconstruct
their geometry contract without treating this builder as the oracle.
"""
from pathlib import Path
from copy import deepcopy
import argparse
import hashlib
import json
import sys

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(REPO / 'services/dxf-preview'))
from converter.core import parse_dxf

IDS = ['baseline', '01_sleeve_length', '02_body_length', '03_cuff_width', '04_front_neck']
EXPECTED = {'01_sleeve_length': {'袖片'}, '02_body_length': {'前片', '后片'},
            '03_cuff_width': {'袖片'}, '04_front_neck': {'前片', '领条'}}


def digest(data): return hashlib.sha256(data).hexdigest()


def signature(panel):
    return {key: panel[key] for key in ['positions', 'triangles', 'uv', 'normals']}


def cuff_measure(model):
    panel = next(p for p in model['panels'] if p['id'] == 'sleeve_b')
    cfg = panel['construction']['source_config']; pose = model['pose']
    center = np.array(pose['sleeve_root_center_U']) + cfg['axis_length_U'] * np.array(pose['sleeve_axis'])
    vertices = np.array(panel['positions'])
    ids = [i for i, source in enumerate(panel['binding']['boundary_sources']) if '袖片袖口横线' in source['curve']]
    radii = np.linalg.norm(vertices[ids] - center, axis=1)
    return {'axis_length_U': cfg['axis_length_U'], 'cuff_center_U': center.tolist(), 'cuff_radius_U': float(radii.mean()),
            'cuff_radius_spread_U': float(np.ptp(radii)), 'source_width_U': cfg['cuff_width_U']}


def neck_center(model):
    panel = next(p for p in model['panels'] if p['id'] == 'front')
    uv = np.array(panel['uv'])[:panel['binding']['boundary_vertex_count']]
    ids = [i for i, src in enumerate(panel['binding']['boundary_sources']) if '领口' in src['curve'] and abs(uv[i, 0]) < 1e-6]
    if len(ids) != 1: raise ValueError('Expected one source-bound front neckline center')
    return np.array(panel['positions'][ids[0]])


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--models', type=Path, default=ROOT)
    p.add_argument('--output', type=Path, required=True); args = p.parse_args()
    manifest = json.loads((args.models / 'manifest.json').read_text())
    models = {key: json.loads((args.models / (key + '.mesh.json')).read_text()) for key in IDS}
    base = models['baseline']; report = {'verdict': 'PASS', 'scope': 'Numeric self-check; independent HTML/source audit separate.', 'cases': []}
    for entry in manifest['models']:
        data = (args.models / entry['file']).read_bytes()
        assert digest(data) == entry['sha256'] and len(data) == entry['byte_length']
    for key, model in models.items():
        assert model['pose'] == base['pose'] and model['units'] == 'U'
        assert model['physical_fit'] == model['cloth_simulation'] == model['sewing_validation'] == 'NOT_RUN'
        assert model['source_unit_calibration']['状态'] == '未标定'
        dxf = (REPO / model['source_dxf']).read_bytes(); spec = (REPO / model['source_spec']).read_bytes()
        assert digest(dxf) == model['source_dxf_sha256'] and digest(spec) == model['source_spec_sha256']
        curves, _ = parse_dxf(dxf); parts = []
        for before, panel in zip(base['panels'], model['panels'], strict=True):
            v = np.array(panel['positions']); f = np.array(panel['triangles']); n = np.array(panel['normals']); uv = np.array(panel['uv'])
            assert np.isfinite(v).all() and np.isfinite(uv).all() and np.isfinite(n).all()
            assert f.min() >= 0 and f.max() < len(v)
            area = np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1) / 2
            assert area.min() > 1e-9
            assert np.max(np.abs(np.linalg.norm(n, axis=1) - 1)) < 1e-6
            changed = signature(before) != signature(panel)
            if key != 'baseline': assert changed == (panel['source_piece'] in EXPECTED[key]), (key, panel['id'], changed)
            nb = panel['binding']['boundary_vertex_count']; bindings = panel['binding']['boundary_sources']
            assert len(bindings) == nb
            errors = []
            for point, source in zip(uv[:nb], bindings, strict=True):
                actual = curves[source['polyline_index']][source['vertex_index']] - panel['binding']['dxf_layout_origin_U']
                errors.append(float(np.max(np.abs(point - actual))))
            assert max(errors) < 1e-6
            parts.append({'panel': panel['id'], 'source_piece': panel['source_piece'], 'vertices': len(v), 'triangles': len(f),
                          'min_triangle_area_U2': float(area.min()), 'max_source_binding_error_U': max(errors), 'changed_vs_base': changed})
        report['cases'].append({'id': key, 'panels': parts})
    report['unique_models'] = len({entry['sha256'] for entry in manifest['models']}); assert report['unique_models'] == 5
    original = cuff_measure(base); longer = cuff_measure(models['01_sleeve_length']); wider = cuff_measure(models['03_cuff_width'])
    assert abs(longer['axis_length_U'] - original['axis_length_U'] - 20) < 1e-6
    assert abs(wider['axis_length_U'] - original['axis_length_U']) < 1e-6
    assert abs(longer['cuff_radius_U'] - original['cuff_radius_U']) < 1e-6
    assert abs(wider['cuff_radius_U'] - original['cuff_radius_U'] - 10 / (2 * np.pi)) < 1e-6
    for label in ['front', 'back']:
        old = next(p for p in base['panels'] if p['id'] == label)
        new = next(p for p in models['02_body_length']['panels'] if p['id'] == label)
        indices = [i for i, ref in enumerate(old['binding']['boundary_sources']) if '下摆' in ref['curve']]
        # Arc fractions along a changed side legitimately differ, while the
        # original DXF polyline/vertex identities and ordering must not.
        source_id = lambda item: (item['curve'], item['polyline_index'], item['vertex_index'])
        assert list(map(source_id, old['binding']['boundary_sources'])) == list(map(source_id, new['binding']['boundary_sources']))
        differences = np.array(new['positions'])[indices] - np.array(old['positions'])[indices]
        assert np.max(np.abs(differences[:, 1] - 15)) < 1e-6
    neck_delta = neck_center(models['04_front_neck']) - neck_center(base)
    assert np.max(np.abs(neck_delta - [0, -10, 0])) < 1e-6
    old_band = next(p for p in base['panels'] if p['id'] == 'band')
    new_band = next(p for p in models['04_front_neck']['panels'] if p['id'] == 'band')
    old_ring = old_band['construction']['source_config']['neck_ring_length_U']
    new_ring = new_band['construction']['source_config']['neck_ring_length_U']
    assert new_ring > old_ring
    # Adjacent failure controls exercise the actual source/model binding boundary.
    import build_meshes as builder
    baseline = yaml.safe_load((REPO / 'patterns/fitted-tshirt/input-spec.yaml').read_bytes())
    polylines, _ = parse_dxf((REPO / 'patterns/fitted-tshirt/input.dxf').read_bytes())
    bindings = builder.source_map(baseline, polylines)
    bad = [curve.copy() for curve in polylines]; bad[0][0, 0] += 1
    try: builder.get_sources(baseline, bad, bindings)
    except ValueError: mismatch_rejected = True
    else: raise AssertionError('Changed actual DXF with stale YAML was accepted')
    report.update({'same_pose': True, 'mesh_response': {'baseline_sleeve': original, 'longer_sleeve': longer, 'wider_cuff': wider,
                    'front_neck_center_delta_U': neck_delta.tolist(), 'band_ring_lengths_U': [old_ring, new_ring], 'body_hem_rise_U': 15},
                   'mismatched_actual_dxf_rejected': mismatch_rejected,
                   'physical_fit': 'NOT_RUN', 'cloth_simulation': 'NOT_RUN', 'sewing_validation': 'NOT_RUN'})
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'verdict': report['verdict'], 'unique_models': report['unique_models'], 'mesh_response': report['mesh_response']}, ensure_ascii=False))


if __name__ == '__main__': main()
