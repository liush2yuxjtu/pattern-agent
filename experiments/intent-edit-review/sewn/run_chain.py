#!/usr/bin/env python3
"""Run sew-pattern-to-3d then verify-seaming on fresh, source-bound artifacts."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
import zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'services/dxf-preview'))
from converter.core import ConversionError, convert_dxf
from app import bundle

LABELS = {'baseline': '原型', '01_sleeve_length': '袖子加长20U', '02_body_length': '前后衣身缩短15U',
          '03_cuff_width': '袖口展开宽增加10U', '04_front_neck': '前领加深10U并联动领条'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def run(args):
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit('Use a new empty output directory; stale successes must never be reused.')
    out.mkdir(parents=True, exist_ok=True)
    manifest = {'format': 'intent-sewn-chain/1', 'verdict': 'BLOCKED', 'phases': [], 'cases': [],
                'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
                'units_assumption': args.units_assumption, 'source_spec_units': 'U, uncalibrated',
                'unit_note': 'Explicit numerical sewing assumption only; original YAML U and original DXF bytes remain unchanged. Not physical calibration.',
                'physical_fit': 'NOT_RUN', 'material_mechanics': 'NOT_RUN', 'production_cutting_approval': 'NOT_RUN',
                'source_files': {}}
    source_paths = [Path(__file__), REPO / 'services/dxf-preview/converter/core.py',
                    REPO / 'services/dxf-preview/converter/sewn.py', REPO / 'services/dxf-preview/converter/profile.json',
                    REPO / 'services/dxf-preview/converter/sewing_contract.json', REPO / 'services/dxf-preview/verification/seams.py',
                    REPO / 'services/dxf-preview/verification/geometry.py', REPO / 'services/dxf-preview/verify_connections.py']
    for name in ['sew-pattern-to-3d', 'verify-seaming', 'verify']:
        source_paths.append(REPO / '.agents/skills' / name / 'SKILL.md')
    for p in source_paths:
        manifest['source_files'][str(p.relative_to(REPO))] = sha(p.read_bytes())

    def event(phase, state):
        manifest['phases'].append({'phase': phase, 'state': state,
                                   'at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()})
        save(out / 'manifest.json', manifest)

    event('sew-pattern-to-3d', 'STARTED')
    for cid, label in LABELS.items():
        case = out / cid; case.mkdir()
        directory = REPO / 'patterns/fitted-tshirt' if cid == 'baseline' else REPO / 'experiments/intent-edit-benchmark/results' / cid
        dxf = directory / ('input.dxf' if cid == 'baseline' else 'output.dxf')
        spec = directory / ('input-spec.yaml' if cid == 'baseline' else 'new-spec.yaml')
        raw, spec_raw = dxf.read_bytes(), spec.read_bytes()
        row = {'id': cid, 'label': label, 'verdict': 'BLOCKED', 'source_dxf': str(dxf.relative_to(REPO)),
               'source_yaml': str(spec.relative_to(REPO)), 'source_dxf_sha256': sha(raw), 'source_yaml_sha256': sha(spec_raw),
               'units_assumption': args.units_assumption, 'profile': 'fitted-tshirt-v1'}
        manifest['cases'].append(row)
        (case / 'source-spec.yaml').write_bytes(spec_raw)
        start = time.monotonic()
        try:
            result = convert_dxf(raw, units=args.units_assumption, profile='fitted-tshirt-v1')
            archive = bundle(result, raw)
            (case / 'preview.zip').write_bytes(archive)
            files = case / 'files'; files.mkdir()
            with zipfile.ZipFile(io.BytesIO(archive)) as z:
                if z.testzip() is not None:
                    raise ValueError('Bundle CRC failure')
                for name in z.namelist():
                    if not (files / name).resolve().is_relative_to(files):
                        raise ValueError('Unsafe bundle path')
                z.extractall(files)
            if (files / 'model.glb').read_bytes() != result.glb or (files / 'original-input.dxf').read_bytes() != raw:
                raise ValueError('Bundle changed the generated GLB or source DXF')
            row.update(generation='GENERATED', model_sha256=sha(result.glb), model_bytes=len(result.glb),
                       vertices=result.report['vertices'], triangles=result.report['triangles'], mode=result.report['mode'],
                       max_vertex_edit_mm=result.report['pattern_revision']['max_vertex_edit_mm'])
        except ConversionError as error:
            unsupported = error.code in ['PROFILE_REQUIRED', 'UNITS_OR_SCALE', 'UNKNOWN_PROFILE', 'UNITS_REQUIRED']
            row.update(generation='REJECTED', verdict='BLOCKED' if unsupported else 'FAIL',
                       reason=str(error), error_code=error.code,
                       action='Needs an explicit supported profile and independently checked sewing contract; thresholds were not changed.' if unsupported else 'Actual assembly or strict exported geometry rejected.')
        except Exception as error:
            row.update(generation='ERROR', verdict='BLOCKED', reason=str(error), error_code='RUNTIME_OR_DELIVERY_ERROR')
            (case / 'runtime-error.log').write_text(traceback.format_exc())
        row['generation_seconds'] = round(time.monotonic() - start, 4)
        save(case / 'decision.json', row); save(out / 'manifest.json', manifest)
        print(json.dumps({'phase': 'sew-pattern-to-3d', 'id': cid, 'generation': row['generation'],
                          'error_code': row.get('error_code')}, ensure_ascii=False), flush=True)
    event('sew-pattern-to-3d', 'COMPLETED')

    event('verify-seaming', 'STARTED')
    for row in manifest['cases']:
        case = out / row['id']
        if row['generation'] != 'GENERATED':
            row['seaming'] = 'NOT_RUN_NO_ACCEPTED_MODEL'
            save(case / 'decision.json', row)
            continue
        command = [sys.executable, str(REPO / 'services/dxf-preview/verify_connections.py'),
                   '--dxf', str(REPO / row['source_dxf']), '--glb', str(case / 'files/model.glb'),
                   '--units', args.units_assumption, '--out', str(case / 'independent.json')]
        start = time.monotonic()
        result = subprocess.run(command, cwd=REPO, capture_output=True, text=True)
        (case / 'independent.log').write_text(result.stdout + result.stderr)
        row['independent_command'] = command; row['independent_exit_code'] = result.returncode
        row['verification_seconds'] = round(time.monotonic() - start, 4)
        if result.returncode in [0, 2] and (case / 'independent.json').exists():
            report = json.loads((case / 'independent.json').read_text())
            row['seaming'] = report['verdict']; row['verdict'] = report['verdict']
            checks = report.get('checks', {})
            row['measurements'] = {key: checks.get(key) for key in ['max_seam_gap_mm', 'max_3d_seam_length_error_mm', 'proper_self_intersections', 'topology']}
            row['seams'] = len(checks.get('seams', [])); row['failures'] = report.get('failures', [])
            if sha((case / 'files/model.glb').read_bytes()) != row['model_sha256']:
                raise ValueError('Model changed during independent verification')
        else:
            row.update(seaming='BLOCKED', verdict='BLOCKED', reason='Independent CLI could not finish; see raw log.')
        save(case / 'decision.json', row); save(out / 'manifest.json', manifest)
        print(json.dumps({'phase': 'verify-seaming', 'id': row['id'], 'verdict': row['verdict'],
                          'exit_code': result.returncode}, ensure_ascii=False), flush=True)
    event('verify-seaming', 'COMPLETED')
    verdicts = {row['verdict'] for row in manifest['cases']}
    manifest['verdict'] = 'FAIL' if 'FAIL' in verdicts else 'BLOCKED' if 'BLOCKED' in verdicts else 'PASS'
    manifest['summary'] = {key: sum(row['verdict'] == key for row in manifest['cases']) for key in ['PASS', 'FAIL', 'BLOCKED']}
    save(out / 'manifest.json', manifest)
    print(json.dumps({'verdict': manifest['verdict'], 'summary': manifest['summary'], 'output': str(out)}, ensure_ascii=False), flush=True)
    return 0 if manifest['verdict'] == 'PASS' else 2 if manifest['verdict'] == 'FAIL' else 3


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--units-assumption', choices=['mm', 'cm', 'inch'], required=True)
    raise SystemExit(run(parser.parse_args()))
