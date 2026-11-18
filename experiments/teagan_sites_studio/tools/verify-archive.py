"""Rebuild and exercise the restored studio without mutating frozen source assets."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--browser', action='store_true')
args = parser.parse_args()
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
steps = []
report = {'status': 'FAIL', 'sourceCommit': '5fd4986222886d1e4aaa5944122eaaec397c9a2a',
          'scope': 'Restored local source, build, existing assertions and optional actual Chromium interactions',
          'browserTransport': 'LOCAL exact-byte route.fulfill; not a fresh production deployment test',
          'browserFallback': 'ego-browser not installed; use repository Playwright scripts and installed Chromium',
          'physicalFit': 'NOT_RUN', 'materialCalibration': 'NOT_CALIBRATED', 'steps': steps}

def run(name, command, cwd):
    start = time.monotonic()
    with (out / (name + '.log')).open('w') as log:
        result = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
    steps.append({'name': name, 'command': command, 'cwd': str(cwd),
                  'exitCode': result.returncode, 'seconds': round(time.monotonic() - start, 2),
                  'log': name + '.log'})
    print(name + ': ' + ('PASS' if result.returncode == 0 else 'FAIL'), flush=True)
    if result.returncode:
        raise RuntimeError(name + ' failed; read ' + str(out / (name + '.log')))

try:
    run('source', [sys.executable, str(ROOT / 'tools/verify-source.py')], ROOT)
    assert (ROOT / 'app/node_modules/esbuild').exists(), 'Run npm ci in app first.'
    with tempfile.TemporaryDirectory(prefix='teagan-archive-') as temp:
        app = Path(temp) / 'app'
        shutil.copytree(ROOT / 'app', app, ignore=shutil.ignore_patterns('node_modules', '__pycache__'))
        (app / 'node_modules').symlink_to((ROOT / 'app/node_modules').resolve(), target_is_directory=True)
        run('build', ['npm', 'run', 'build'], app)
        manifest = json.loads((ROOT / 'SOURCE-MANIFEST.json').read_text())
        mismatch = [item['path'] for item in manifest['files']
                    if hashlib.sha256((app / item['path']).read_bytes()).hexdigest() != item['sha256']]
        assert not mismatch, 'Rebuild changed archived bytes: ' + repr(mismatch)
        report['rebuildAllSourceHashesMatch'] = True
        run('core', ['npm', 'run', 'verify'], app)
        run('expert', ['npm', 'run', 'verify:expert'], app)
        shutil.copy2(app / 'dist/verification/expert-report.json', out / 'expert-report.json')
        run('state-model', ['node', 'scripts/verify-studio-state.mjs', str(out / 'state-model.json')], app)
        fixture = Path(temp) / 'angle-fixtures.json'
        run('fold-angles', ['node', 'scripts/verify-crease-angles.mjs', str(fixture)], app)
        run('fold-independent', [sys.executable, str(ROOT / 'tools/verify-fold-independent.py'),
                                 '--app', str(app), '--fixtures', str(fixture),
                                 '--out', str(out / 'fold-independent.json')], app)
        if args.browser:
            for suite in ['state', 'views']:
                run('browser-' + suite, [sys.executable, str(ROOT / 'tools/run-browser.py'),
                    '--app', str(app), '--suite', suite, '--out', str(out / ('browser-' + suite))], app)
        else:
            report['browserStatus'] = 'SKIP: --browser not supplied'
        report['status'] = 'PASS'
finally:
    (out / 'receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
