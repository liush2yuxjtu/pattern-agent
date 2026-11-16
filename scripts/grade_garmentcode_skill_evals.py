"""Independent artifact grading, following skill-creator grading.json schema."""
import hashlib
import json
import math
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
from verify_garmentcode_preview import read_glb



def grade(case, configuration):
    run = case / configuration
    outputs = run / 'outputs'
    expectations = json.loads((case / 'eval_metadata.json').read_text())['assertions']
    checks = []

    def check(index, action):
        try:
            evidence = action()
            checks.append({'text': expectations[index], 'passed': True, 'evidence': evidence})
        except Exception as error:
            checks.append({'text': expectations[index], 'passed': False,
                           'evidence': f'{type(error).__name__}: {error}'})

    manifests = list(outputs.rglob('manifest.json'))

    def model():
        mode = 'simulate' if case.name == 'cpu-physical-simulation' else 'existing'
        selected = [(path, json.loads(path.read_text())) for path in manifests]
        selected = [(path, m) for path, m in selected if m.get('mode') == mode]
        assert len(selected) == 1, f'Expected one {mode} manifest, got {len(selected)}'
        path, manifest = selected[0]
        return path.parent, manifest

    if case.name == 'cpu-physical-simulation':
        def execution():
            _, m = model(); s = m['simulation']
            assert s['executed'] and s['device'] == 'cpu' and s['frames'] > 11 and s['error'] is None
            return f"CPU executed {s['frames']} frames; error={s['error']}; snapshot fix={s.get('cpu_static_check_snapshot_fix')}"
        def geometry():
            folder, _ = model()
            a, fa = read_glb((folder / 'garment-initial.glb').read_bytes())
            b, fb = read_glb((folder / 'garment.glb').read_bytes())
            assert fa == fb and len(a) == len(b)
            displacement = max(math.dist(x, y) for x, y in zip(a, b))
            assert displacement > .01
            return f'Independent GLB decoder: {len(a)} vertices, {len(fa)//3} triangles, same topology; max displacement {displacement}m'
        def provenance():
            _, m = model()
            assert m['input']['sha256'] == '048aac4e8b90ffcda38f2b928eebe6354c48a4528ed7f31a885ce38e38ccf88e'
            assert m['garmentcode_commit'] == 'd449629979028123a5c4dc9e732a2ec19b7fce31'
            return 'Actual official-fixture hash and pinned upstream commit match'
        def separated():
            _, m = model(); s = m['simulation']; r = m['release']
            assert r['upstream_threshold_check'] in ('PASS', 'FAIL')
            for counter, field in [('self_intersections', 'strict_zero_self_intersections'), ('body_intersections', 'strict_zero_body_intersections')]:
                expected = 'PASS' if not s['error'] and s['static'] and s[counter] == 0 else 'FAIL'
                assert r[field] == expected, (field, r[field], expected)
            return json.dumps(r, ensure_ascii=False)
        def unrun():
            _, m = model()
            assert m['release']['physical_fit'] == m['release']['independent_full_geometry_audit'] == 'NOT_RUN'
            return 'Both independent full audit and physical fit explicitly NOT_RUN'
        def label():
            folder, m = model(); s = m['simulation']
            assert '通过质量检查' not in m['preview_label']
            if s['self_intersections'] or s['body_intersections']:
                assert '未通过' in m['preview_label']
            assert m['preview_label'] in (folder / 'preview.html').read_text()
            return m['preview_label']
        actions = [execution, geometry, provenance, separated, unrun, label]
    elif case.name == 'existing-mesh-only':
        def export():
            folder, m = model()
            assert (folder / 'preview.html').is_file()
            vertices, _ = read_glb((folder / 'garment.glb').read_bytes())
            assert vertices
            return 'Real standalone export produced valid GLB and offline HTML'
        def geometry():
            folder, _ = model()
            a, fa = read_glb((REPO / 'web/garmentcode-preview/garment.glb').read_bytes())
            b, fb = read_glb((folder / 'garment.glb').read_bytes())
            assert a == b and fa == fb, 'Export changed input positions, meter scale or topology'
            return f'All {len(a)} positions and {len(fa)} indices match actual meter-unit input'
        def provenance():
            _, m = model()
            source = REPO / 'web/garmentcode-preview/garment.glb'
            assert m['input']['sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
            assert m['mode'] == 'existing' and not m['simulation']['executed'] and not m['mesh_generated_this_run']
            return 'Actual existing input SHA; generated_this_run=false and simulation.executed=false'
        def label():
            folder, m = model()
            assert m['preview_label'].startswith('已有') and '未重新生成或仿真' in m['preview_label']
            assert m['release']['physical_fit'] == 'NOT_RUN'
            assert m['preview_label'] in (folder / 'preview.html').read_text()
            return m['preview_label']
        actions = [export, geometry, provenance, label]
    else:
        def rejected():
            log = (outputs / 'command.log').read_text()
            assert 'Random-body sample requires' in log
            return 'Real CLI diagnostic rejects random-body input'
        def needed():
            log = (outputs / 'command.log').read_text()
            assert '--body-mesh' in log and 'refusing neutral-body substitution' in log
            return 'CLI names matching --body-mesh and refuses neutral substitution'
        def no_output():
            found = list(outputs.rglob('*.glb')) + list(outputs.rglob('*_sim.obj'))
            assert not found, found
            return 'No GLB or simulated OBJ exists under this rejected request'
        actions = [rejected, needed, no_output]
    for i, action in enumerate(actions):
        check(i, action)
    passed = sum(item['passed'] for item in checks)
    result = {'expectations': checks, 'summary': {'passed': passed, 'failed': len(checks)-passed,
              'total': len(checks), 'pass_rate': passed/len(checks)},
              'eval_feedback': {'overall': 'Real geometry and explicit scope are checked. Single-run cases do not establish statistical superiority.'}}
    (run / 'grading.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result['summary']


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    for case in sorted((args.workspace / 'iteration-1').iterdir()):
        if case.is_dir() and (case / 'eval_metadata.json').exists():
            for config in ['with_skill', 'old_skill']:
                print(case.name, config, grade(case, config))
