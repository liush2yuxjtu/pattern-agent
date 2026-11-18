#!/usr/bin/env python3
"""Third skill: real preview pixels, exact downloads, and independent download reopen."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import traceback
import zipfile
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[3]
FLAGS = ['--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pixel(canvas):
    raw = base64.b64decode(canvas.evaluate('(c)=>c.toDataURL().split(",")[1]'))
    im = Image.open(io.BytesIO(raw)).convert('RGB')
    difference = ImageChops.difference(im, Image.new('RGB', im.size, im.getpixel((0, 0)))).convert('L')
    n = sum(difference.point(lambda x: 255 if x > 12 else 0).histogram()[128:])
    assert n > 8000, ('Empty model view', n)
    return {'sha256': sha(im.tobytes()), 'foreground_pixels': n, 'size': list(im.size)}


def view(page, cid):
    frame = page.frame(url=re.compile('/' + cid + r'/files/preview\.html$'))
    assert frame, ('Missing actual preview frame', cid)
    frame.locator('#canvas[data-ready="true"]').wait_for(timeout=40000)
    return frame


def drive(page, frame):
    canvas = frame.locator('#canvas'); canvas.scroll_into_view_if_needed()
    before = pixel(canvas); box = canvas.bounding_box()
    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    page.mouse.down(); page.mouse.move(box['x'] + box['width'] / 2 + 75, box['y'] + box['height'] / 2 + 10, steps=9); page.mouse.up()
    dragged = pixel(canvas); assert dragged['sha256'] != before['sha256']
    page.mouse.wheel(0, -120); zoomed = pixel(canvas); assert zoomed['sha256'] != dragged['sha256']
    canvas.focus(); page.keyboard.press('ArrowRight'); keyed = pixel(canvas); assert keyed['sha256'] != zoomed['sha256']
    frame.locator('#wireframe').check(); wired = pixel(canvas); assert wired['sha256'] != keyed['sha256']
    frame.locator('#wireframe').uncheck(); frame.locator('#reset').click()
    reset = pixel(canvas); assert reset['sha256'] == before['sha256']
    frame.evaluate('scrollTo(0,0)')
    return {'initial': before, 'drag': dragged, 'zoom': zoomed, 'keyboard': keyed, 'wireframe': wired, 'reset': reset}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def run(args):
    source = args.directory.resolve(); out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((source / 'manifest.json').read_text())
    report = {'verdict': 'FAIL', 'phase': 'verify', 'workflow_verdict': manifest['verdict'],
              'catalog_sha256': sha((source / 'index.html').read_bytes()), 'cases': [], 'page_errors': [], 'bad_responses': []}
    server = None
    try:
        if args.base_url:
            url = args.base_url.rstrip('/') + '/'
        else:
            server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(source)))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f'http://127.0.0.1:{server.server_port}/'
        report['url'] = url
        accepted = [r for r in manifest['cases'] if r['verdict'] == 'PASS']
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=args.browser, args=FLAGS)
            context = browser.new_context(viewport={'width': 1448, 'height': 1100}, accept_downloads=True)
            page = context.new_page()
            page.on('pageerror', lambda e: report['page_errors'].append(str(e)))
            page.on('console', lambda m: report['page_errors'].append(m.text) if m.type == 'error' else None)
            page.on('response', lambda r: report['bad_responses'].append({'url': r.url[:150], 'status': r.status}) if r.status >= 400 else None)
            response = page.goto(url, wait_until='load')
            assert sha(response.body()) == report['catalog_sha256']
            assert 'BLOCKED' in page.locator('.scope').inner_text()
            assert page.locator('iframe').count() == len(accepted)
            for entry in manifest['cases']:
                row = page.locator(f'[data-result="{entry["id"]}"]')
                assert row.locator('.status').inner_text() == entry['verdict']
                if entry['verdict'] != 'PASS':
                    assert not (source / entry['id'] / 'files/model.glb').exists()
                    assert row.locator('a[href$="model.glb"]').count() == 0
                    assert '新的明确配置' in row.inner_text()
            for entry in accepted:
                cid = entry['id']; frame = view(page, cid); panel = page.locator(f'.panel[data-case="{cid}"]')
                assert int(frame.locator('#canvas').get_attribute('data-triangles')) == entry['triangles']
                embedded = re.findall(r'data:model/gltf-binary;base64,([A-Za-z0-9+/=]+)', frame.content())
                assert len(embedded) == 1 and sha(base64.b64decode(embedded[0])) == entry['model_sha256']
                paths = out / cid; paths.mkdir(exist_ok=True)
                record = {'id': cid, 'model_sha256': entry['model_sha256'], 'interactions': drive(page, frame)}
                panel.locator('summary').click()
                cells = panel.locator('tbody tr'); actual = json.loads((source / cid / 'independent.json').read_text())
                assert cells.count() == len(actual['checks']['seams']) == 15
                for i, seam in enumerate(actual['checks']['seams']):
                    assert cells.nth(i).locator('td').all_text_contents() == [seam['name'], f'{seam["processed_residual_mm"]:.6f}', f'{seam["length_error_mm"]:.6f}', f'{seam["max_gap_mm"]:.6f}']
                panel.locator('summary').click()
                for name in ['files/model.glb', 'delivery.zip']:
                    with page.expect_download() as downloaded:
                        panel.locator(f'a[href="{cid}/{name}"]').click()
                    target = paths / Path(name).name; downloaded.value.save_as(target)
                    assert target.read_bytes() == (source / cid / name).read_bytes()
                with zipfile.ZipFile(paths / 'delivery.zip') as z:
                    assert z.testzip() is None
                    assert sha(z.read('files/model.glb')) == entry['model_sha256']
                    assert sha(z.read('files/original-input.dxf')) == entry['source_dxf_sha256']
                    assert sha(z.read('source-spec.yaml')) == entry['source_yaml_sha256']
                    assert json.loads(z.read('independent.json'))['verdict'] == 'PASS'
                command = [sys.executable, str(REPO / 'services/dxf-preview/verify_connections.py'), '--dxf',
                           str(source / cid / 'source-input.dxf'), '--glb', str(paths / 'model.glb'),
                           '--units', entry['units_assumption'], '--out', str(paths / 'downloaded-independent.json')]
                checked = subprocess.run(command, capture_output=True, text=True)
                (paths / 'downloaded-independent.log').write_text(checked.stdout + checked.stderr)
                assert checked.returncode == 0, checked.stdout + checked.stderr
                record['downloaded_glb_independent'] = json.loads((paths / 'downloaded-independent.json').read_text())['verdict']
                frame.evaluate('scrollTo(0,0)'); page.locator(f'iframe[data-case="{cid}"]').screenshot(path=str(paths / 'actual-preview.png'))
                report['cases'].append(record)
            page.evaluate('scrollTo(0,0)'); page.screenshot(path=str(out / 'catalog-desktop.png'))
            for width in [375, 320]:
                page.set_viewport_size({'width': width, 'height': 850})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), width
                for entry in accepted:
                    pixel(view(page, entry['id']).locator('#canvas'))
                page.evaluate('scrollTo(0,0)'); page.screenshot(path=str(out / f'catalog-{width}.png'))
            assert not report['page_errors'] and not report['bad_responses']
            assert len({c['interactions']['initial']['sha256'] for c in report['cases']}) == len(accepted)
            context.close(); browser.close()

            browser = pw.chromium.launch(executable_path=args.browser, args=FLAGS)
            touch = browser.new_context(viewport={'width': 375, 'height': 900}, has_touch=True, is_mobile=True)
            pg = touch.new_page(); pg.goto(url, wait_until='load'); cdp = touch.new_cdp_session(pg)
            for entry in accepted:
                canvas = view(pg, entry['id']).locator('#canvas'); canvas.scroll_into_view_if_needed()
                before = pixel(canvas); box = canvas.bounding_box(); x = box['x'] + box['width'] / 2; y = box['y'] + box['height'] / 2
                cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y, 'id': 1}]})
                for step in range(1, 7):
                    cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x + step * 8, 'y': y + 5, 'id': 1}]})
                cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
                after = pixel(canvas); assert after['sha256'] != before['sha256']
                next(c for c in report['cases'] if c['id'] == entry['id'])['real_touch'] = {'before': before, 'after': after}
            pg.screenshot(path=str(out / 'touch-mobile.png')); touch.close(); browser.close()

            browser = pw.chromium.launch(executable_path=args.browser, args=FLAGS)
            offline = browser.new_context(offline=True, viewport={'width': 1000, 'height': 1000})
            for entry in accepted:
                pg = offline.new_page(); requests = []
                pg.on('request', lambda r: requests.append(r.url.split(':', 1)[0]))
                pg.set_content((source / entry['id'] / 'files/preview.html').read_text(), wait_until='load')
                pg.locator('#canvas[data-ready="true"]').wait_for(timeout=30000)
                initial = pixel(pg.locator('#canvas')); pg.locator('#wireframe').check()
                assert pixel(pg.locator('#canvas'))['sha256'] != initial['sha256']
                assert all(scheme == 'data' for scheme in requests), requests
                pg.screenshot(path=str(out / entry['id'] / 'offline-preview.png'))
                report['cases'][next(i for i, row in enumerate(report['cases']) if row['id'] == entry['id'])]['offline'] = {'requests': requests, 'pixels': initial, 'scope': 'Exact self-contained preview HTML loaded with networking disabled; not a managed file-URL bypass.'}
                pg.close()
            offline.close(); browser.close()

            browser = pw.chromium.launch(executable_path=args.browser, args=['--disable-webgl'])
            page = browser.new_page(viewport={'width': 1200, 'height': 1000}, accept_downloads=True)
            page.goto(url, wait_until='load')
            for entry in accepted:
                frame = page.frame(url=re.compile('/' + entry['id'] + r'/files/preview\.html$'))
                frame.locator('#error').filter(has_text='兼容查看器').wait_for()
                with page.expect_download() as downloaded:
                    page.locator(f'.panel[data-case="{entry["id"]}"] a[href$="model.glb"]').click()
                dest = out / entry['id'] / 'no-webgl-model.glb'; downloaded.value.save_as(dest)
                assert sha(dest.read_bytes()) == entry['model_sha256']
            page.screenshot(path=str(out / 'no-webgl.png'))
            browser.close()
        report['verdict'] = 'PASS'
        report['scope'] = 'Delivery accurately exposes accepted/blocked cases; accepted models and saved downloads independently pass. Whole five-case sewing workflow remains BLOCKED.'
    except Exception as error:
        report['failure'] = str(error); report['traceback'] = traceback.format_exc()
        raise
    finally:
        if server:
            server.shutdown(); server.server_close()
        (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({key: report.get(key) for key in ['verdict', 'workflow_verdict', 'failure']}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path, default=REPO / 'web/intent-edit-review/sewn')
    p.add_argument('--output', type=Path, required=True); p.add_argument('--browser', default='/usr/bin/chromium')
    p.add_argument('--base-url'); run(p.parse_args())
