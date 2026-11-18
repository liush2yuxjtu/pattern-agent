#!/usr/bin/env python3
"""Verify the actual standalone Node build, source inventory and frozen inputs.

Builds only to the requested evidence directory, never over the published HTML.
Pair this CLI/static boundary with verify_webgpu.py and all original suites.
"""
import argparse
import base64
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / 'web/cloth-lab'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def payload(html):
    match = re.search(r'<script id="payload" type="application/json">(.*?)</script>', html, re.S)
    assert match, 'Actual embedded payload is missing'
    return json.loads(match.group(1))


def wasm_sections(raw):
    """Parse the actual binary, retaining each complete section's raw bytes."""
    assert raw[:8] == b'\0asm\x01\0\0\0'

    def uleb(offset):
        value = shift = 0
        while True:
            assert offset < len(raw) and shift < 35, 'Invalid WASM section length'
            byte = raw[offset]
            offset += 1
            value |= (byte & 127) << shift
            if byte < 128:return value,offset
            shift += 7

    sections = []
    offset = 8
    while offset < len(raw):
        start = offset
        kind = raw[offset]
        size,body = uleb(offset+1)
        offset = body+size
        assert offset <= len(raw), 'Truncated WASM section'
        name = None
        if kind == 0:
            length,names = uleb(body)
            assert names+length <= offset
            name = raw[names:names+length].decode('utf-8')
        sections.append({'id':kind,'name':name,'raw':raw[start:offset]})
    return sections


def kernel_identity(actual, original):
    current,baseline = wasm_sections(actual),wasm_sections(original)
    live = [s['raw'] for s in current if s['id']]
    frozen = [s['raw'] for s in baseline if s['id']]
    assert live == frozen, 'Executable WASM sections changed from aa3f497'
    def custom(sections):
        result = {}
        for section in sections:
            if not section['id']:
                assert section['name'] not in result, 'Duplicate custom section'
                result[section['name']] = section['raw']
        return result
    new_custom,old_custom = custom(current),custom(baseline)
    assert new_custom.keys() <= old_custom.keys(), 'Unexpected new WASM custom section'
    removed = []
    for name,content in old_custom.items():
        if name in new_custom:
            assert new_custom[name] == content, f'Custom section changed: {name}'
        else:
            assert name.startswith('.debug_') or name in ['name','producers','target_features'], f'Unexpected custom section removed: {name}'
            removed.append({'name':name,'bytes':len(content),'sha256':sha(content)})
    return {'rawSha256':sha(actual), 'baselineRawSha256':sha(original),
            'nonCustomSha256':sha(b''.join(live)), 'nonCustomSectionsBitIdentical':True,
            'removedCustomSections':removed,
            'sections':[{'id':s['id'],'name':s['name'],'bytes':len(s['raw']),
                         'sha256':sha(s['raw'])} for s in current]}


class StandaloneHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.dependencies = []
        self.module_scripts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and attrs.get('type') == 'module':
            self.module_scripts.append(attrs)
        source = attrs.get('src') or attrs.get('poster')
        if tag == 'link' and attrs.get('rel') in ('stylesheet', 'modulepreload', 'preload'):
            source = attrs.get('href')
        if source and not source.startswith(('data:', 'blob:')):
            self.dependencies.append({'tag':tag, 'source':source})


def check_artifact(html_path, manifest_path, frozen_payload, report):
    raw = html_path.read_bytes()
    html = raw.decode()
    manifest = json.loads(manifest_path.read_text())
    packed = payload(html)
    parser = StandaloneHTML()
    parser.feed(html)
    assert not parser.dependencies and not parser.module_scripts, vars(parser)
    assert not re.search(r'@import\s+[\'"u]', html), 'External CSS import'
    assert manifest['format'] == 'standalone-html'
    assert manifest['releaseStripDebug'] is True
    assert manifest['solver']['source'] == 'web/cloth-lab/src/solver.c'
    assert '-Wl,--strip-debug' in manifest['solver']['flags']
    assert '-Wl,--initial-memory=16777216' in manifest['solver']['flags']
    assert '-Wl,--max-memory=16777216' in manifest['solver']['flags']
    assert manifest['htmlSha256'] == sha(raw)
    assert manifest['htmlBytes'] == len(raw)
    wasm = base64.b64decode(packed['wasm'], validate=True)
    assert wasm.startswith(b'\0asm\x01\0\0\0')
    assert sha(wasm) == manifest['wasmSha256'] == packed['wasmSha256']
    report['kernelIdentity'] = kernel_identity(wasm,base64.b64decode(frozen_payload['wasm'],validate=True))
    assert packed['body'] == frozen_payload['body'], 'Actual body/BVH bytes changed'
    assert manifest['bodySourceSha256'] == packed['body']['sourceSha256']
    assert manifest['fingerprint'] == packed['buildFingerprint']
    assert packed['sources'] == manifest['sources']
    assert manifest['bundle']['format'] == 'iife'
    assert manifest['bundle']['entryPoint'] == 'web/cloth-lab/src/app.js'
    source_modules = set(manifest['bundle']['sourceModules'])
    assert len(source_modules) >= 8, source_modules
    assert {'web/cloth-lab/src/app.js', 'web/cloth-lab/src/rendering.js'} <= source_modules
    actual_sources = {str(p.relative_to(ROOT)) for p in (APP/'src').rglob('*') if p.is_file()}
    assert actual_sources <= set(manifest['sources']), sorted(actual_sources-set(manifest['sources']))
    assert source_modules <= set(manifest['sources'])
    assert set(manifest['bundle']['inputs']) <= set(manifest['sources'])
    for name, expected in manifest['sources'].items():
        path = ROOT/name
        assert path.is_file() and sha(path.read_bytes()) == expected, name
    assert (APP/'src/app.js').stat().st_size < 8000, 'Entry point still contains monolithic application logic'
    report.update(htmlSha256=sha(raw), htmlBytes=len(raw), wasmSha256=sha(wasm),
                  fingerprint=manifest['fingerprint'], moduleCount=len(source_modules),
                  sourceCount=len(manifest['sources']), sourceModules=sorted(source_modules))
    return manifest


def run(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = {'startedAtUnix':time.time(), 'baselineRef':args.baseline_ref, 'checks':{}, 'commands':[]}

    def command(argv, name, *, cwd=ROOT, expected=0):
        result = subprocess.run([str(x) for x in argv], cwd=cwd, capture_output=True, text=True)
        (out/(name+'.stdout.log')).write_text(result.stdout)
        (out/(name+'.stderr.log')).write_text(result.stderr)
        report['commands'].append({'argv':[str(x) for x in argv], 'cwd':str(cwd), 'exitCode':result.returncode})
        assert (result.returncode == 0 if expected == 0 else result.returncode != 0), (name,result.returncode,result.stderr[-2000:])
        return result

    try:
        baseline_html = subprocess.check_output(['git','show',f'{args.baseline_ref}:web/cloth-lab/index.html'], cwd=ROOT).decode()
        frozen = payload(baseline_html)
        for name in ['web/cloth-lab/src/solver.c', 'web/cloth-lab/src/avatar-fit.json', 'web/human-studio/assets/human.json']:
            original = subprocess.check_output(['git','show',f'{args.baseline_ref}:{name}'], cwd=ROOT)
            assert (ROOT/name).read_bytes() == original, name
        report['checks']['frozenSolverAvatarProfileAndSourceBodyExact'] = True
        command([args.node, APP/'build.js','--help'], 'help')
        command([args.node, APP/'build.js','--unknown-option'], 'unknown-option', expected=1)
        command([args.node, APP/'build.js','--out'], 'missing-out', expected=1)
        manifests = []
        for name in ['first', 'second']:
            directory = out/name
            directory.mkdir(exist_ok=True)
            target = directory/'custom.html'
            command([args.node, APP/'build.js','--out',target,'--work-dir',directory/'work'], 'build-'+name)
            artifact = {}
            manifests.append(check_artifact(target,directory/'custom.build.json',frozen,artifact))
            report[name] = artifact
        assert (out/'first/custom.html').read_bytes() == (out/'second/custom.html').read_bytes()
        assert manifests[0] == manifests[1]
        report['checks']['repeatableIndependentCustomOutputsAndManifest'] = True
        report['checks']['singleInlineIIFEAndRealWASMBodyNoExternalDependencies'] = True
        report['checks']['recursiveSourcesAndActualBundleInputsAreHashed'] = True
        legacy = out/'legacy.html'
        command([args.python, ROOT/'scripts/build_cloth_lab.py','--out',legacy,'--work-dir',out/'legacy-work'], 'legacy-python')
        assert legacy.read_bytes() == (out/'first/custom.html').read_bytes()
        assert json.loads((out/'legacy.build.json').read_text()) == manifests[0]
        report['checks']['legacyPythonForwardsTheSameCLIAndBuild'] = True

        # Mutate only an isolated copy, including a nested, unimported source.
        # Source inventory must bind that file, and stale body fit must reject
        # before replacing an existing output. No shared product files change.
        with tempfile.TemporaryDirectory(prefix='cloth-build-contract-') as tmp:
            fixture = Path(tmp)
            for name in manifests[0]['sources']:
                target = fixture/name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT/name, target)
            cli = fixture/'web/cloth-lab/build.js'
            assert cli.is_file()
            fit_path = fixture/'web/cloth-lab/src/avatar-fit.json'
            original_fit = fit_path.read_bytes()
            fit = json.loads(original_fit)
            fit['sourceBodySha256'] = '0'*64
            fit_path.write_text(json.dumps(fit))
            rejected = fixture/'keep.html'
            rejected.write_text('existing artifact must survive')
            failed = command([args.node,cli,'--out',rejected,'--work-dir',fixture/'build-work'], 'stale-fit',cwd=fixture,expected=1)
            assert re.search(r'stale|source.body|body.hash',failed.stdout+failed.stderr,re.I), failed.stderr
            assert rejected.read_text() == 'existing artifact must survive'
            fit_path.write_bytes(original_fit)
            report['checks']['staleFitRejectedAndExistingArtifactPreserved'] = True
            command([args.node,cli,'--out',fixture/'portable.html','--work-dir',fixture/'build-work'], 'cross-root',cwd=fixture)
            assert (fixture/'portable.html').read_bytes() == (out/'first/custom.html').read_bytes(), 'Same sources in a different checkout changed standalone bytes'
            portable = json.loads((fixture/'portable.build.json').read_text())
            assert portable == manifests[0]
            save(out/'cross-root.build.json',portable)
            report['checks']['differentSourceRootProducesIdenticalStandaloneBytesAndManifest'] = True
            nested = fixture/'web/cloth-lab/src/verify-fixture/nested.txt'
            nested.parent.mkdir(parents=True)
            nested.write_text('source inventory negative control\n')
            command([args.node,cli,'--out',fixture/'nested.html','--work-dir',fixture/'build-work'], 'nested-source',cwd=fixture)
            changed = json.loads((fixture/'nested.build.json').read_text())
            assert changed['sources']['web/cloth-lab/src/verify-fixture/nested.txt'] == sha(nested.read_bytes())
            assert changed['fingerprint'] != manifests[0]['fingerprint']
            assert changed['wasmSha256'] == manifests[0]['wasmSha256']
        report['checks']['nestedSourceChangesFingerprintWithoutChangingKernel'] = True
        report['verdict'] = 'PASS'
    except Exception as error:
        report['verdict'] = 'FAIL'
        report['error'] = str(error)
        raise
    finally:
        report['finishedAtUnix'] = time.time()
        save(out/'receipt.json', report)
    print(json.dumps({'verdict':report['verdict'], 'checks':report['checks']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline-ref', default='aa3f497')
    parser.add_argument('--node', default=os.environ.get('NODE','node'))
    parser.add_argument('--python', default=os.environ.get('PYTHON','python'))
    run(parser.parse_args())
