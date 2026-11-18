#!/usr/bin/env python3
"""Exercise the actual self-contained HTML with Chromium and save review evidence."""
import argparse
import base64
import hashlib
import io
import json
import re
import shutil
import threading
import traceback
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / 'web/intent-edit-review/index.html'
FLAGS = ['--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pixels(page, selector):
    encoded = page.locator(selector).evaluate('(c)=>c.toDataURL("image/png").split(",")[1]')
    raw = base64.b64decode(encoded)
    im = Image.open(io.BytesIO(raw)).convert('RGB')
    background = Image.new('RGB', im.size, im.getpixel((0, 0)))
    mask = ImageChops.difference(im, background).convert('L').point(lambda x: 255 if x > 12 else 0)
    count = sum(mask.histogram()[128:])
    assert count > 1800, f'{selector} empty or nearly empty: {count} pixels'
    return {'sha256': digest(im.tobytes()), 'foreground_pixels': count, 'size': list(im.size)}


def ready(page, url):
    response = page.goto(url, wait_until='load')
    page.locator('body[data-ready="true"]').wait_for(timeout=40000)
    assert not page.locator('#fatal').is_visible()
    page.locator('canvas[data-ready="true"]').first.wait_for()
    return response


def select(page, entry):
    page.locator('#case-select').select_option(entry['id'])
    assert page.locator('body').get_attribute('data-selected-case') == entry['id']
    assert page.locator('#intent').input_value() == entry['intent']
    assert page.locator('#input-summary').inner_text() == '\n'.join(entry['input_summary_lines'])
    assert page.locator('#output-summary').inner_text() == '\n'.join(entry['summary_lines'])


def close(page, name):
    page.locator(f'[data-close="{name}-dialog"]').click()
    assert not page.locator(f'#{name}-dialog').is_visible()


def full_document(page, entry, side):
    page.locator(f'[data-document="{side}"]').click()
    assert page.locator('#document-dialog').is_visible()
    assert page.locator('#document-dialog .dialog-content').evaluate('(e)=>e.scrollTop===0'), 'new YAML opened at an old scroll position'
    actual = page.locator('#document-pre').text_content()
    raw = (ROOT / entry['files']['yaml']['path']).read_bytes()
    assert actual == raw.decode('utf-8'), f'{entry["id"]}: truncated or wrong YAML'
    assert digest(actual.encode('utf-8')) == entry['files']['yaml']['sha256']
    page.locator('#document-dialog .dialog-content').evaluate('(e)=>e.scrollTop=e.scrollHeight')
    assert page.locator('#document-dialog .dialog-content').evaluate('(e)=>e.scrollTop>0')
    page.keyboard.press('Escape')
    assert not page.locator('#document-dialog').is_visible()
    return {'bytes': len(raw), 'sha256': digest(raw), 'complete_text_and_scroll': True}


def download(page, entry, kind, side, target):
    record = entry['files'][kind]
    with page.expect_download() as captured:
        page.locator(f'[data-download="{kind}"][data-side="{side}"]').click()
    result = captured.value
    assert result.suggested_filename == record['name']
    saved = target / entry['id'] / result.suggested_filename
    saved.parent.mkdir(parents=True, exist_ok=True)
    result.save_as(saved)
    raw = saved.read_bytes()
    assert raw == (ROOT / record['path']).read_bytes(), f'{entry["id"]}/{kind}: download differs from original'
    assert digest(raw) == record['sha256']
    return {'id': entry['id'], 'kind': kind, 'bytes': len(raw), 'sha256': digest(raw)}


def no_overflow(page):
    state = page.evaluate('''()=>({viewport:innerWidth,width:document.documentElement.scrollWidth,
      dialogs:[...document.querySelectorAll('dialog[open]')].map(e=>({left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right}))})''')
    assert state['width'] <= state['viewport'], state
    for rect in state['dialogs']:
        assert rect['left'] >= 0 and rect['right'] <= state['viewport'], state
    return state


def interactions(page):
    page.locator('[aria-label="原型复位"]').click()
    page.locator('#input-model').scroll_into_view_if_needed()
    before = [pixels(page, '#' + side + '-model') for side in ['input', 'output']]
    r = page.locator('#input-model').bounding_box()
    page.mouse.move(r['x'] + r['width'] * .5, r['y'] + r['height'] * .5)
    page.mouse.down()
    page.mouse.move(r['x'] + r['width'] * .5 + 85, r['y'] + r['height'] * .5 + 12, steps=9)
    page.mouse.up()
    after = [pixels(page, '#' + side + '-model') for side in ['input', 'output']]
    for a, b in zip(before, after):
        assert a['sha256'] != b['sha256'], 'pointer drag did not change rendered pixels'
    states = page.locator('.model-canvas').evaluate_all('(cs)=>cs.map(c=>({...c.dataset}))')
    assert states[0]['yaw'] == states[1]['yaw'] and states[0]['pitch'] == states[1]['pitch']
    page.mouse.wheel(0, -160)
    zoomed = pixels(page, '#output-model')
    assert zoomed['sha256'] != after[1]['sha256']
    assert float(page.locator('#input-model').get_attribute('data-zoom')) > 1
    page.locator('#output-model').focus()
    page.keyboard.press('ArrowLeft')
    assert pixels(page, '#output-model')['sha256'] != zoomed['sha256']
    views = {}
    for label in ['改版正面', '改版背面', '改版复位']:
        page.locator(f'[aria-label="{label}"]').click()
        views[label] = pixels(page, '#output-model')['sha256']
    assert len(set(views.values())) == 3, 'front/back/reset use identical rendered view'
    return {'drag_changed_both_pixels': True, 'synchronized_camera': states, 'wheel_and_keyboard': True, 'views': views}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def run(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    raw = HTML.read_bytes()
    payload = json.loads(re.search(rb'<script id="app-data" type="application/json">(.*?)</script>', raw, re.S).group(1))
    report = {'html_sha256': digest(raw), 'html_bytes': len(raw), 'verdict': 'FAIL', 'errors': [], 'downloads': [], 'cases': [], 'responsive': []}
    server = None
    try:
        if args.base_url:
            url = args.base_url.rstrip('/') + '/'
        else:
            server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / 'web')))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f'http://127.0.0.1:{server.server_port}/intent-edit-review/'
        report['url'] = url
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=args.browser, headless=True, args=FLAGS)
            context = browser.new_context(viewport={'width': 1448, 'height': 1086}, device_scale_factor=1, accept_downloads=True)
            page = context.new_page()
            page.on('pageerror', lambda error: report['errors'].append(str(error)))
            page.on('console', lambda msg: report['errors'].append(msg.text) if msg.type == 'error' else None)
            requests, bad_responses = [], []
            page.on('request', lambda r: requests.append(r.url))
            page.on('response', lambda r: bad_responses.append({'url': r.url, 'status': r.status}) if r.status >= 400 else None)
            response = ready(page, url)
            report['document_sha256'] = digest(response.body())
            assert report['document_sha256'] == digest(raw), 'loaded document is not the candidate single HTML'
            assert page.title() == '原型与改版结果 一页对照'
            assert page.locator('#case-select option').count() == 4
            assert page.locator('#input-pattern .actual svg polyline').count() == 204
            assert page.locator('#input-pattern .actual svg text').count() == 27
            assert page.locator('#input-model').get_attribute('data-mode') == 'webgl'
            assert page.locator('#output-model').get_attribute('data-mode') == 'webgl'
            assert page.locator('#input-model').get_attribute('data-model-hash') == payload['baseline']['threeD']['artifact_sha256']
            no_overflow(page)
            page.screenshot(path=str(out / 'desktop-1448.png'), full_page=True)
            baseline_pixels = pixels(page, '#input-model')
            report['input_yaml'] = full_document(page, payload['baseline'], 'input')
            for kind in ['yaml', 'dxf']:
                report['downloads'].append(download(page, payload['baseline'], kind, 'input', out / 'downloads'))
            seen_svg, seen_pixels = set(), set()
            for entry in payload['cases']:
                select(page, entry)
                assert page.locator('#output-model').get_attribute('data-model-hash') == entry['threeD']['artifact_sha256']
                assert page.locator('#output-model').get_attribute('data-model-id') == entry['id']
                assert page.locator('#output-pattern .actual svg polyline').count() == 204
                assert page.locator('#output-pattern .actual svg text').count() == 27
                svg = page.locator('#output-pattern .actual').inner_html()
                pixel = pixels(page, '#output-model')
                assert pixels(page, '#input-model') == baseline_pixels, 'switching output changed the original view'
                assert digest(svg.encode()) not in seen_svg
                assert pixel['sha256'] not in seen_pixels, 'case switched metadata but retained prior pixels'
                seen_svg.add(digest(svg.encode())); seen_pixels.add(pixel['sha256'])
                record = {'id': entry['id'], 'svg_sha256': digest(svg.encode()), 'rendered': pixel, 'yaml': full_document(page, entry, 'output')}
                for kind in ['yaml', 'dxf']:
                    report['downloads'].append(download(page, entry, kind, 'output', out / 'downloads'))
                page.locator('#show-diff').click()
                rows = page.locator('#diff-content tbody tr')
                assert rows.count() == len(entry['changes'])
                for i, change in enumerate(entry['changes']):
                    expected = [change['name'], f"{change['before']:.6f}", f"{change['after']:.6f}", f"{change['after']-change['before']:.6f}"]
                    assert rows.nth(i).locator('td').all_text_contents() == expected
                if entry['id'] == '01_sleeve_length':
                    page.screenshot(path=str(out / 'diff-measurements.png'))
                for kind in ['spec_diff', 'geometry_patch']:
                    page.locator(f'[data-diff-tab="{kind}"]').click()
                    assert page.locator('#diff-content pre').text_content() == (ROOT / entry['files'][kind]['path']).read_text()
                    report['downloads'].append(download(page, entry, kind, 'output', out / 'downloads'))
                close(page, 'diff')
                report['cases'].append(record)
            page.screenshot(path=str(out / 'desktop-neck.png'), full_page=True)
            report['interactions'] = interactions(page)
            page.locator('#input-pattern').click()
            assert page.locator('#large-pattern svg polyline').count() == 204
            assert page.locator('#pattern-title').inner_text() == '输入二维纸样'
            page.keyboard.press('Escape')
            page.locator('#output-pattern').focus()
            page.keyboard.press('Enter')
            assert page.locator('#large-pattern svg text').count() == 27
            assert page.locator('#pattern-title').inner_text() == '输出二维纸样'
            page.screenshot(path=str(out / 'pattern-large.png'))
            close(page, 'pattern')
            page.locator('#show-source').click()
            source_text = page.locator('#source-detail').inner_text()
            for entry in [payload['baseline'], payload['cases'][-1]]:
                for sha in [entry['files']['dxf']['sha256'], entry['files']['yaml']['sha256'], entry['threeD']['artifact_sha256']]:
                    assert sha in source_text
            close(page, 'source')
            for width, height in [(1366, 900), (768, 1024), (375, 812), (320, 740)]:
                page.set_viewport_size({'width': width, 'height': height})
                select(page, payload['cases'][1])
                dimensions = no_overflow(page)
                a = page.locator('#input-stage').bounding_box(); b = page.locator('#output-stage').bounding_box()
                assert (b['y'] > a['y']) if width < 680 else (abs(a['y']-b['y']) < 1)
                pixels(page, '#output-model')
                if width in [375, 320]:
                    page.screenshot(path=str(out / f'mobile-{width}.png'), full_page=True)
                page.locator('[data-document="output"]').click()
                no_overflow(page)
                assert page.locator('#document-dialog .dialog-content').evaluate('(e)=>e.scrollTop===0')
                assert page.locator('#document-pre').text_content() == (ROOT / payload['cases'][1]['files']['yaml']['path']).read_text()
                if width == 375:
                    page.screenshot(path=str(out / 'mobile-yaml.png'))
                close(page, 'document')
                page.locator('#show-diff').click()
                no_overflow(page)
                close(page, 'diff')
                page.locator('#show-source').click()
                no_overflow(page)
                close(page, 'source')
                report['responsive'].append(dimensions)
            assert len(report['downloads']) == 18
            assert len(set(requests)) == 1, f'external or sibling resources loaded: {requests}'
            assert not bad_responses, bad_responses
            assert not report['errors'], report['errors']
            report['network'] = {'requests': requests, 'bad_responses': bad_responses}
            context.close(); browser.close()

            # A copied single file must work without adjacent assets. Respect the
            # managed browser's file-URL policy; do not disable security controls.
            isolated = out / 'isolated'; isolated.mkdir(exist_ok=True)
            saved_html = isolated / '原型与改版对照.html'; shutil.copyfile(HTML, saved_html)
            browser = playwright.chromium.launch(executable_path=args.browser, headless=True, args=FLAGS)
            context = browser.new_context(viewport={'width': 1448, 'height': 1086}, accept_downloads=True)
            page = context.new_page(); offline_errors, offline_requests = [], []
            page.on('pageerror', lambda e: offline_errors.append(str(e)))
            page.on('request', lambda r: offline_requests.append(r.url))
            isolated_server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(isolated)))
            threading.Thread(target=isolated_server.serve_forever, daemon=True).start()
            try:
                ready(page, f'http://127.0.0.1:{isolated_server.server_port}/{saved_html.name}')
            finally:
                isolated_server.shutdown(); isolated_server.server_close()
            context.set_offline(True)
            select(page, payload['cases'][2]); interactions(page)
            full_document(page, payload['cases'][2], 'output')
            downloaded = download(page, payload['cases'][2], 'dxf', 'output', out / 'offline-downloads')
            page.screenshot(path=str(out / 'offline-single-file.png'), full_page=True)
            assert len(offline_requests) == 1 and offline_requests[0].startswith('http://127.0.0.1:')
            assert not offline_errors, offline_errors
            assert len(list(isolated.iterdir())) == 1
            report['offline'] = {'isolated_files': 1, 'requests': offline_requests, 'errors': offline_errors, 'download': downloaded, 'sha256': digest(saved_html.read_bytes()),
                'scope': 'One real document from an isolated directory; HTTP server stopped and browser network disabled before case switch, rotation, full YAML and DXF download.',
                'direct_file_url': {'verdict': 'BLOCKED', 'reason': 'Observed net::ERR_BLOCKED_BY_ADMINISTRATOR; managed browser policy left intact.'}}
            context.close(); browser.close()

            # Genuine browser WebGL denial exercises the CPU triangle renderer.
            browser = playwright.chromium.launch(executable_path=args.browser, headless=True, args=['--disable-webgl'])
            context = browser.new_context(viewport={'width': 1366, 'height': 900})
            page = context.new_page(); software_errors = []
            page.on('pageerror', lambda e: software_errors.append(str(e)))
            ready(page, url)
            context.set_offline(True)
            assert page.locator('#input-model').get_attribute('data-mode') == 'software'
            software_before = pixels(page, '#output-model')
            select(page, payload['cases'][1])
            software_after = pixels(page, '#output-model')
            assert software_before['sha256'] != software_after['sha256']
            report['software'] = {'before': software_before, 'after': software_after, 'interaction': interactions(page), 'errors': software_errors}
            page.screenshot(path=str(out / 'software-fallback.png'), full_page=True)
            assert not software_errors, software_errors
            context.close(); browser.close()
        report['verdict'] = 'PASS'
    except Exception as error:
        report['failure'] = str(error)
        report['traceback'] = traceback.format_exc()
        raise
    finally:
        if server:
            server.shutdown(); server.server_close()
        (out / 'browser-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'verdict': report['verdict'], 'html_sha256': report['html_sha256'], 'cases': len(report['cases']), 'downloads': len(report['downloads']), 'report': str(out / 'browser-report.json'), 'failure': report.get('failure')}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'work/intent-edit-review/browser')
    parser.add_argument('--browser', default='/usr/bin/chromium')
    parser.add_argument('--base-url', help='Actual deployed route; local file/offline checks still run.')
    run(parser.parse_args())
