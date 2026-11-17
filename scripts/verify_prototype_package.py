#!/usr/bin/env python3
"""Verify the real prototype-package reference UI and downloaded source artifacts."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import runpy
from urllib.parse import urljoin
import zipfile

from playwright.sync_api import sync_playwright
from verify_pages import local_site

ROOT = Path(__file__).resolve().parents[1]
ROUTE = 'prototype-package/'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_source():
    root = ROOT / 'web/prototype-package/package'
    spec = json.loads((root / 'prototype-spec.json').read_text())
    verifier = runpy.run_path(str(root / 'verify_baseline.py'))
    baseline = verifier['verify'](spec, root)
    manifest = json.loads((root / 'SHA256.json').read_text())
    for name, expected in manifest.items():
        assert digest((root / name).read_bytes()) == expected, name
    design = json.loads((root / 'design-spec.json').read_text())
    assert digest((root / design['prototype']['snapshot_file']).read_bytes()) == design['prototype']['snapshot_sha256']
    assert not design['program']['operations']
    assert design['units']['source_drawing_mm_per_unit'] is None
    for item in json.loads((root / 'examples/index.json').read_text()):
        intent = json.loads((root / item['intent']).read_text())
        patch = json.loads((root / item['expected_spec_patch']).read_text())
        assert intent['reference_only'] and intent['execution_status'] == 'NOT_RUN'
        assert patch['example_only'] and not patch['executable']
        if intent['visual_ref']:
            assert (root / item['intent']).parent.joinpath(intent['visual_ref']).is_file()
    return {'source_and_bindings': baseline, 'manifest_files_checked': len(manifest), 'examples_reference_only': 3}


def verify(base, output, expected_commit=None, browser='/usr/bin/chromium'):
    base = base.rstrip('/') + '/'
    output.mkdir(parents=True, exist_ok=True)
    checks, downloads, errors, bad, failures = [], [], [], [], []
    with sync_playwright() as pw:
        engine = pw.chromium.launch(executable_path=browser, headless=True)
        try:
            context = engine.new_context(viewport={'width': 1440, 'height': 1080}, accept_downloads=True)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
            page.on('requestfailed', lambda req: failures.append({'url': req.url, 'error': req.failure}) if req.failure != 'net::ERR_ABORTED' else None)
            page.on('response', lambda res: bad.append({'url': res.url, 'status': res.status}) if res.status >= 400 else None)
            metadata_response = context.request.get(urljoin(base, 'build.json'))
            assert metadata_response.status == 200
            metadata = metadata_response.json()
            if expected_commit:
                assert metadata['commit'] == expected_commit, (metadata['commit'], expected_commit)
            assert page.goto(urljoin(base, ROUTE), wait_until='networkidle').status == 200
            assert page.title() == 'Pattern Agent · 原型包与设计意图'
            assert page.locator('h1').inner_text().replace('\n', '') == '原型包准备与使用示例'
            page.wait_for_function('document.querySelector("#example-panel").dataset.example === "01-sleeve-length"')
            assert page.locator('.prototype-paper img').evaluate('(img) => img.complete && img.naturalWidth > 0')
            checks.append('correct new route, source preview pixels and loaded real example JSON')
            page.screenshot(path=str(output / 'desktop.png'))
            page.locator('#open-prototype').click()
            assert page.locator('#prototype-dialog').is_visible()
            page.keyboard.press('Escape')
            assert not page.locator('#prototype-dialog').is_visible()
            checks.append('source preview modal opens and closes by keyboard')

            for frame_id, count in [('build-flow', 6), ('use-flow', 10)]:
                frame = page.locator('#' + frame_id)
                frame.scroll_into_view_if_needed()
                inner = page.frame_locator('#' + frame_id)
                inner.locator('svg .node').first.wait_for()
                assert inner.locator('svg .node').count() == count
                page.wait_for_function('(id) => {const f=document.getElementById(id),r=f.contentDocument.querySelector("[data-flow]");return r&&f.getBoundingClientRect().height>=r.getBoundingClientRect().height}', arg=frame_id)
                assert frame.bounding_box()['height'] > 400
                assert not inner.locator('svg .node').evaluate_all("groups => groups.some(g=>[...g.querySelectorAll('text')].some(t=>{const r=t.getBBox(),b=g.querySelector('path').getBBox();return r.x+r.width>b.x+b.width-5}))")
                frame.screenshot(path=str(output / (frame_id + '.png')))
            checks.append('two rendered workflow diagrams, readable labels and automatic frame heights')

            page.locator('button[data-example="02-front-neckline"]').click()
            page.wait_for_function('document.querySelector("#example-panel").dataset.example === "02-front-neckline"')
            assert '加深1厘米' in page.locator('#example-title').inner_text()
            assert page.locator('#intent-image').get_attribute('src').endswith('02-front-neckline/intent.png')
            page.locator('.spec-details summary').click()
            assert page.locator('#example-patch').is_visible()
            assert json.loads(page.locator('#example-patch').inner_text())['planned_operations'][0]['op'] == 'ADJUST_NECKLINE'
            page.locator('button[data-example="03-movement-goal"]').click()
            page.wait_for_function('document.querySelector("#example-panel").dataset.example === "03-movement-goal"')
            assert page.locator('#movement-note').is_visible()
            assert not page.locator('#intent-figure').is_visible()
            assert json.loads(page.locator('#example-patch').inner_text())['planned_operations'] == []
            page.locator('button[data-example="03-movement-goal"]').press('ArrowLeft')
            page.wait_for_function('document.querySelector("#example-panel").dataset.example === "02-front-neckline"')
            assert page.locator('#tab-neckline').evaluate('(button) => button === document.activeElement')
            page.screenshot(path=str(output / 'example.png'), full_page=True)
            checks.append('pointer and keyboard change cases; ambiguous goal retains an empty operation list')

            for link in page.locator('.package-file-list a').all():
                href = link.get_attribute('href')
                key = ROUTE + href
                with page.expect_download() as event:
                    link.click()
                download = event.value
                assert download.failure() is None, download.failure()
                target = output / download.suggested_filename
                download.save_as(target)
                data = target.read_bytes()
                assert digest(data) == metadata['files'][key], key
                downloads.append({'path': key, 'sha256': digest(data), 'bytes': len(data)})
            archive = output / 'fitted-tshirt-prototype-package-v0.2.zip'
            with zipfile.ZipFile(archive) as z:
                assert z.testzip() is None
                archived_manifest = json.loads(z.read('prototype-package/SHA256.json'))
                for name, expected in archived_manifest.items():
                    assert digest(z.read('prototype-package/' + name)) == expected, name
                root_spec = json.loads(z.read('prototype-package/design-spec.json'))
                assert not root_spec['program']['operations']
                geometry_bytes = z.read('prototype-package/prototype-spec.json')
                assert digest(geometry_bytes) == root_spec['prototype']['snapshot_sha256']
                source = json.loads(z.read('prototype-package/baseline-source-manifest.json'))
                for item in source['files']:
                    assert digest(z.read('prototype-package/source/' + item['name'])) == item['sha256']
            checks.append('five actual downloads match build hashes; complete archive and original file hashes verified')

            for width in [375, 320]:
                page.set_viewport_size({'width': width, 'height': 900})
                page.goto(urljoin(base, ROUTE), wait_until='networkidle')
                page.wait_for_function('document.querySelector("#example-panel").dataset.example === "01-sleeve-length"')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                for frame_id in ['build-flow', 'use-flow']:
                    page.locator('#' + frame_id).scroll_into_view_if_needed()
                    page.frame_locator('#' + frame_id).locator('svg .node').first.wait_for()
                    page.wait_for_function('(id)=>{const f=document.getElementById(id),r=f.contentDocument.querySelector("[data-flow]");return f.getBoundingClientRect().height>=r.getBoundingClientRect().height}', arg=frame_id)
                page.locator('button[data-example="03-movement-goal"]').click()
                page.wait_for_function('document.querySelector("#example-panel").dataset.example === "03-movement-goal"')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(output / f'mobile-{width}.png'), full_page=True)
            checks.append('375px and 320px mobile with reflowing workflows and real case changes')
            page.locator('.spec-details summary').click()
            assert '"planned_operations": []' in page.locator('#example-patch').inner_text()
            checks.append('spec disclosure presents the actual selected reference file')
            assert not errors, errors
            assert not bad, bad
            assert not failures, failures
            # Probe after the error collection assertions: a nonexistent package must be a real 404.
            missing = context.request.get(urljoin(base, ROUTE + 'downloads/no-such-package.zip'))
            assert missing.status == 404
            checks.append('missing archive returns 404')
        finally:
            engine.close()
    report = {'verdict': 'PASS', 'claim': 'new prototype reference route, diagrams, examples and source downloads only',
              'base_url': base, 'route': ROUTE, 'commit': metadata['commit'], 'checks': checks,
              'downloads': downloads, 'errors': errors, 'http_errors': bad, 'failed_requests': failures,
              'semantic_compiler': 'NOT_IMPLEMENTED', 'edited_dxf': 'NOT_GENERATED', 'new_3d_preview': 'NOT_GENERATED',
              'browser': 'local Playwright Chromium; ego-browser unavailable in the Cloud environment'}
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url')
    parser.add_argument('--output', type=Path, default=ROOT / 'work/verify-prototype-package')
    parser.add_argument('--expected-commit')
    parser.add_argument('--browser', default='/usr/bin/chromium')
    args = parser.parse_args()
    if args.base_url:
        verify(args.base_url, args.output, args.expected_commit, args.browser)
    else:
        source = check_source()
        print(json.dumps(source, ensure_ascii=False, indent=2))
        with local_site(ROOT / 'dist') as base_url:
            verify(base_url, args.output, args.expected_commit, args.browser)
