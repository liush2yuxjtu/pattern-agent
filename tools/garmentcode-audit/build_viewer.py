#!/usr/bin/env python3
"""Build one offline HTML from actual raw OBJ, checkpoints, and audit reports."""
import argparse
import base64
import importlib.util
import json
import html
import hashlib
import gzip
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location('mesh_audit', Path(__file__).with_name('audit.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    root = audit.ROOT
    published = root / 'web/garmentcode-preview'
    body_v, body_f = audit.read_obj(workspace / 'GarmentCode/assets/bodies/mean_all.obj', 1.)
    initial_v, faces = audit.read_obj(published / 'demo/mesh_boxmesh.obj', .01)
    final_v, final_f = audit.read_obj(published / 'demo/mesh_sim.obj', .01)
    if not np.array_equal(faces, final_f):
        raise ValueError('initial and final topology differ')

    def flat(values):
        array = np.asarray(values)
        return np.round(array, 8).reshape(-1).tolist() if array.dtype.kind == 'f' else array.reshape(-1).tolist()

    old = json.loads((workspace / 'old-independent-audit-v3.json').read_text())
    runs = [{'id': 'archived', 'label': '旧版 / 精确复现', 'frames': ['saved_final'],
        'positions': [flat(final_v)], 'audits': old['frames'],
        'settings': {'substeps': 10, 'iterations': 1, 'contact_radius_cm': .1},
        'run_status': '已重新运行 232 帧；与旧 OBJ 坐标完全一致'}]
    for folder, report_name, label in [
        ('run-refined', 'refined-independent-audit.json', '候选 A / 20 子步 × 2 迭代'),
        ('run-contact', 'contact-independent-audit.json', '候选 B / 接触半径 0.2 cm'),
        ('run-fixed-recorder', 'fixed-independent-audit.json', '基线 / 300 帧完整记录')]:
        path = workspace / folder
        if not (path / 'checkpoints.npz').is_file() or not (workspace / report_name).is_file():
            continue
        archive = np.load(path / 'checkpoints.npz', allow_pickle=False)
        report = json.loads((workspace / report_name).read_text())
        metadata = json.loads((path / 'run.json').read_text())
        if not np.array_equal(archive['faces'], faces):
            raise ValueError('candidate no longer uses the common topology')
        if np.max(np.abs(archive['body_vertices_m'] - body_v)) > 1e-6:
            raise ValueError('candidate body differs from the displayed collider')
        if archive['frame_ids'].tolist() != [row['frame'] for row in report['frames']]:
            raise ValueError('audit/checkpoint frame identities differ')
        runs.append({'id': folder, 'label': label,
            'sequence_sha256': audit.sha256(path / 'checkpoints.npz'),
            'audit_sha256': audit.sha256(workspace / report_name),
            'frames': archive['frame_ids'].tolist(), 'positions': [flat(v) for v in archive['positions_m']],
            'audits': report['frames'], 'settings': metadata,
            'run_status': '前两候选的最低帧数被上游重置，未达请求的 300 帧；修复后的基线另列' if folder != 'run-fixed-recorder' else '修复最低帧数保护后，实际运行并记录 300 帧'})
    data = {'name': '官方 8 片短袖示例', 'label': '保存状态回放 · 成衣 FAIL',
        'source': 'GarmentCode 固定版本 + 配套 mean_all 人体；不是 Golden Garment 或用户扫描',
        'initial': {'vertices': flat(initial_v), 'faces': flat(faces)},
        'final': {'vertices': flat(final_v), 'faces': flat(faces)},
        'body': {'vertices': flat(body_v), 'faces': flat(body_f)}, 'runs': runs,
        'bodyAudit': {'numpy_pairs': old['body_self_face_pairs_numpy'],
            'cgal_pairs': old['body_self_face_pairs_cgal'], 'validity': old['body_validity']},
        'provenance': {'pattern_sha256': audit.sha256(published / 'example-shirt_specification.json'),
            'body_sha256': audit.sha256(workspace / 'GarmentCode/assets/bodies/mean_all.obj'),
            'archived_mesh_sha256': audit.sha256(published / 'demo/mesh_sim.obj'),
            'units': 'metres', 'rounding_for_display_m': 1e-8,
            'collision_audit': 'full precision saved arrays; rendering rounds to 1e-8 m'}}
    data['provenance']['implementation'] = {name: audit.sha256(Path(__file__).with_name(name)) for name in ['audit.py', 'build_viewer.py', 'viewer-fragment.html', 'shell.html']}
    data['revision'] = 'sha256:' + hashlib.sha256(json.dumps({'provenance':data['provenance'],
        'runs': [{k:v for k,v in r.items() if k in ['id','sequence_sha256','audit_sha256','settings']} for r in runs]}, sort_keys=True).encode()).hexdigest()
    data['provenance']['revision'] = data['revision']
    fragment = Path(__file__).with_name('viewer-fragment.html').read_text()
    payload = base64.b64encode(gzip.compress(json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode(), mtime=0)).decode()
    fragment = fragment.replace('__MESH_DATA__', payload)
    pattern_svg = (published / 'demo/garment_pattern.svg').read_bytes()
    pattern_data = base64.b64encode(pattern_svg).decode()
    shell = Path(__file__).with_name('shell.html').read_text()
    result = shell.replace('__VIEWER__', fragment).replace('__PATTERN_DATA__', pattern_data)
    result = result.replace('__GPL_LICENSE__', html.escape(Path(__file__).with_name('LICENSE-GPL-3.txt').read_text()))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(result)
    print(json.dumps({'html': str(args.out), 'bytes': args.out.stat().st_size, 'runs': len(runs),
                      'sha256': audit.sha256(args.out)}))


if __name__ == '__main__':
    main()
