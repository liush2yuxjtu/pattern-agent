#!/usr/bin/env python3
"""Independently exercise the actual single HTML with WebGL unavailable.

The browser control returns null only for WebGL canvas contexts. SVG projection,
OrbitControls, all saved float32 arrays, CAD sources and OBJ exports remain real.
This checks presentation; it never changes numerical garment acceptance.
"""
import argparse
import base64
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import time
import traceback
import xml.etree.ElementTree as ET

import numpy as np
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.playwright_http import new_api_context

ARRAYS = ('positions', 'previous', 'fields', 'contacts', 'folds')
NO_WEBGL = """const original=HTMLCanvasElement.prototype.getContext;
window.__blockedWebGLCalls=0;
HTMLCanvasElement.prototype.getContext=function(kind,...args){
 if(/^(webgl2?|experimental-webgl)$/i.test(kind)){window.__blockedWebGLCalls++;return null;}
 return original.call(this,kind,...args);
};"""
STATE_HASHES = """async()=>{
 const state=physicsReview.state(),hashes={};
 for(const key of ['positions','previous','fields','contacts','folds']){
  const raw=new Float32Array(state[key]);
  const digest=new Uint8Array(await crypto.subtle.digest('SHA-256',raw.buffer));
  hashes[key]=Array.from(digest,b=>b.toString(16).padStart(2,'0')).join('');
 }
 return {hashes,clock:state.clock,info:physicsReview.info()};
}"""
SVG_SIGNATURE = """async()=>{
 const svg=document.querySelector('#canvas-host>svg[data-renderer-backend="svg"]');
 const paths=Array.from(svg.querySelectorAll('path'));
 const hash=async text=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),b=>b.toString(16).padStart(2,'0')).join('');
 return {geometry:await hash(paths.map(p=>p.getAttribute('d')).join('|')),
  styles:await hash(paths.map(p=>p.getAttribute('style')).join('|')),paths:paths.length,
  renderer:physicsReview.renderer()};
}"""


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unpack(raw, width=1):
    values = np.frombuffer(base64.b64decode(raw), dtype='<f4').astype(float)
    return values.reshape(-1, width) if width > 1 else values


def seek(page, frame):
    page.locator('#timeline').evaluate("""(el,index)=>{
      el.value=index;el.dispatchEvent(new Event('input',{bubbles:true}));
    }""", frame)


def next_svg(page, before):
    page.wait_for_function('n=>physicsReview.renderer().svgRenderCount>n', arg=before, timeout=30000)


def idle_svg(page):
    deadline = time.monotonic() + 30
    last, stable = None, 0
    while time.monotonic() < deadline:
        value = page.evaluate('physicsReview.renderer().svgRenderCount')
        stable = stable + 1 if value == last else 0
        if stable >= 3:
            return value
        last = value
        page.wait_for_timeout(150)
    raise AssertionError('Static SVG did not stop repainting after camera damping settled')


def expect_colors(page, source, frame, mode):
    """Recompute the real vertex-color buffer from the original saved fields."""
    actual = page.evaluate('physicsReview.surface()')
    faces = np.asarray(source['triangles'])
    assert actual['triangles'] == source['triangles'], 'No source triangle may be removed'
    fields = unpack(frame['fields'], 8)
    if mode == 'contacts':
        expected = np.where(unpack(frame['contacts'])[:, None] > 0, [.83, .28, .16], [.56, .69, .59])
    else:
        palette = np.array([[.16, .29, .65], [.20, .65, .68], [.85, .91, .78], [.94, .65, .25], [.76, .20, .18]])
        if mode == 'strain':
            value = (fields[:, 0] + .1) / .6
        elif mode == 'stress':
            value = (fields[:, 3] + 20000) / 120000
        elif mode == 'fold':
            value = (unpack(frame['folds'], 2)[:, 0] + 180) / 360
        else:
            value = None
        colors = np.tile([.53, .71, .58], (len(faces), 1))
        if value is not None:
            t = np.clip(value, 0, 1) * 4
            k = np.minimum(3, np.floor(t).astype(int))
            f = t - k
            colors = palette[k] * (1 - f[:, None]) + palette[k + 1] * f[:, None]
        expected, counts = np.zeros((len(source['positions']), 3)), np.zeros(len(source['positions']))
        for j in range(3):
            np.add.at(expected, faces[:, j], colors)
            np.add.at(counts, faces[:, j], 1)
        expected /= np.maximum(counts[:, None], 1)
    observed = np.asarray(actual['colors']).reshape(-1, 3)
    error = float(np.max(np.abs(observed - expected)))
    assert error < 2e-6, (mode, error)
    return {'max_vertex_color_error': error, 'color_sha256': sha(np.asarray(observed, dtype='<f4').tobytes())}


def source_tools(page, out):
    package = page.evaluate('physicsReview.sources()')
    files = package['files']
    page.locator('#view-2d').click()
    assert page.locator('#pattern-2d').is_visible()
    assert page.locator('#canvas-host>svg[data-renderer-backend="svg"]').is_hidden()
    original = ET.fromstring(package['twoD']['svg'])
    ns = '{http://www.w3.org/2000/svg}'
    for tag in ['polyline', 'text']:
        expected, observed = original.findall(ns + tag), page.locator('#pattern-svg-host svg ' + tag)
        assert observed.count() == len(expected)
        for i, node in enumerate(expected):
            assert (observed.nth(i).get_attribute('points') if tag == 'polyline' else observed.nth(i).text_content()) == (node.get('points') if tag == 'polyline' else ''.join(node.itertext()))
    svg = page.locator('#pattern-svg-host svg')
    original_box = svg.get_attribute('viewBox')
    page.locator('#pattern-zoom-in').click()
    assert svg.get_attribute('viewBox') != original_box
    page.locator('#pattern-reset').click()
    assert svg.get_attribute('viewBox') == original_box
    page.locator('#open-spec').click()
    assert page.locator('#spec-dialog').evaluate('(el)=>el.open')
    yaml_raw = base64.b64decode(files['yaml']['base64'])
    assert page.locator('#spec-content').text_content().encode('utf8') == yaml_raw
    page.keyboard.press('Escape')
    assert page.evaluate('document.activeElement.id') == 'open-spec'
    buttons = {'yaml': 'download-spec', 'dxf': 'download-dxf', 'spec_diff': 'download-spec-diff', 'geometry_patch': 'download-geometry-patch'}
    for kind, record in files.items():
        expected = (ROOT / record['path']).read_bytes()
        assert expected == base64.b64decode(record['base64']) and sha(expected) == record['sha256']
        with page.expect_download() as pending:
            page.locator('#' + buttons[kind]).click()
        saved = out / record['name']
        pending.value.save_as(saved)
        assert saved.read_bytes() == expected
    page.screenshot(path=str(out / 'actual-2d.png'))
    page.locator('#view-3d').click()
    return {'files': {k: f['sha256'] for k, f in files.items()}, 'yaml_bytes': len(yaml_raw), 'lines': len(original.findall(ns + 'polyline')), 'texts': len(original.findall(ns + 'text'))}


def check_obj(page, out, source, frame):
    with page.expect_download() as pending:
        page.locator('#download-obj').click()
    path = out / 'actual-final.obj'
    pending.value.save_as(path)
    rows = path.read_text().splitlines()
    vertices = np.array([[float(x) for x in row.split()[1:]] for row in rows if row.startswith('v ')])
    faces = [[int(x) - 1 for x in row.split()[1:]] for row in rows if row.startswith('f ')]
    assert np.array_equal(vertices, unpack(frame['positions'], 3))
    assert faces == source['triangles']
    return {'sha256': sha(path.read_bytes()), 'vertices': len(vertices), 'triangles': len(faces)}


def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    html_raw = args.html.read_bytes()
    receipt = {'verdict': 'FAIL', 'html_sha256': sha(html_raw), 'verifier_sha256': sha(Path(__file__).read_bytes()), 'backend': 'svg', 'scope': 'Actual CPU projection, sources, saved arrays and export; numerical garment acceptance is unchanged.', 'cases': [], 'page_errors': [], 'console_errors': []}

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(args.html.parent)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/{args.html.name}'
    receipt['url'] = url
    try:
        with sync_playwright() as p:
            api = new_api_context(p, url)
            response = api.get(url, timeout=90000)
            assert response.status == 200 and sha(response.body()) == receipt['html_sha256']
            api.dispose()
            browser = p.chromium.launch(executable_path=args.browser, args=['--no-sandbox'])
            context = browser.new_context(viewport={'width': 1440, 'height': 1080}, accept_downloads=True)
            context.add_init_script(NO_WEBGL)
            page = context.new_page()
            page.on('pageerror', lambda error: receipt['page_errors'].append(str(error)))
            page.on('console', lambda message: receipt['console_errors'].append(message.text) if message.type == 'error' else None)
            page.goto(url, wait_until='load')
            page.wait_for_function('window.physicsReview && physicsReview.renderer().backend==="svg" && physicsReview.renderer().svgFaces>100', timeout=90000)
            assert page.evaluate('window.__blockedWebGLCalls') > 0
            receipt['viewer_sources'] = page.evaluate('physicsReview.info().viewerSources')
            assert receipt['viewer_sources'] == {name: sha((Path(__file__).parent / name).read_bytes()) for name in ['viewer.mjs', 'viewer.css', 'viewer.template.html', 'recording-codec.mjs']}

            for directory in args.run:
                source_raw, recording_raw = (directory / 'input.json').read_bytes(), (directory / 'trajectory.json').read_bytes()
                source, recording = json.loads(source_raw), json.loads(recording_raw)
                case = source['case']
                out = args.output / case
                out.mkdir(exist_ok=True)
                page.locator('#case').select_option(case)
                assert page.evaluate('physicsReview.info().case') == case
                renderer = page.evaluate('physicsReview.renderer()')
                assert renderer['backend'] == 'svg' and renderer['gpu'] is False
                assert all(renderer[key] is None for key in ['calls', 'triangles', 'geometries'])
                assert renderer['sourceTriangles'] == len(source['triangles'])
                assert 'CPU' in page.locator('#renderer-status').inner_text()
                idle = idle_svg(page)
                page.wait_for_timeout(400)
                assert page.evaluate('physicsReview.renderer().svgRenderCount') == idle, 'No per-RAF redraw of static SVG'
                result = {'case': case, 'input_sha256': sha(source_raw), 'recording_sha256': sha(recording_raw), 'static_svg_no_repaint': True, 'frames': [], 'modes': {}}

                initial = page.evaluate(SVG_SIGNATURE)
                assert initial['paths'] > 100 and initial['renderer']['svgFaces'] > 1000
                box = page.locator('#canvas-host>svg[data-renderer-backend="svg"]').bounding_box()
                x, y = box['x'] + box['width'] * .55, box['y'] + box['height'] * .5
                page.mouse.move(x, y)
                page.mouse.down()
                page.mouse.move(x + 85, y + 25, steps=5)
                page.mouse.up()
                idle_svg(page)
                rotated = page.evaluate(SVG_SIGNATURE)
                assert rotated['geometry'] != initial['geometry'], 'Real OrbitControls rotation must reproject SVG'
                page.mouse.wheel(0, -220)
                idle_svg(page)
                zoomed = page.evaluate(SVG_SIGNATURE)
                assert zoomed['geometry'] != rotated['geometry'], 'Real wheel zoom must reproject SVG'
                page.locator('#reset-camera').click()
                idle_svg(page)
                page.screenshot(path=str(out / 'actual-svg-3d.png'))
                result['camera'] = {'rotation': True, 'zoom': True}

                before = page.evaluate('physicsReview.renderer().svgRenderCount')
                page.locator('#body').uncheck()
                next_svg(page, before)
                hidden = page.evaluate('physicsReview.renderer().svgFaces')
                assert hidden < initial['renderer']['svgFaces'], 'Actual body triangles must be present and toggleable'
                for mode in ['cloth', 'strain', 'stress', 'fold', 'contacts', 'seams']:
                    before = page.evaluate('physicsReview.renderer().svgRenderCount')
                    page.locator(f'[data-mode="{mode}"]').click()
                    next_svg(page, before)
                    result['modes'][mode] = {**expect_colors(page, source, recording['frames'][0], mode), **page.evaluate(SVG_SIGNATURE)}
                assert len({v['styles'] for v in result['modes'].values()}) >= 3
                page.locator('[data-mode="strain"]').click()
                idle_svg(page)
                first_svg = page.evaluate(SVG_SIGNATURE)
                for index, frame in enumerate(recording['frames']):
                    seek(page, index)
                    observed = page.evaluate(STATE_HASHES)
                    assert observed['info']['index'] == index and observed['info']['integrationCallsDuringReplay'] == 0
                    assert observed['clock'] == frame['time']
                    expected = {key: sha(base64.b64decode(frame[key])) for key in ARRAYS}
                    assert observed['hashes'] == expected, (case, index, 'Actual saved float32 arrays changed')
                    result['frames'].append({'frame': index, 'clock': frame['time'], 'array_sha256': observed['hashes']})
                assert len(result['frames']) == 61
                idle_svg(page)
                last_svg = page.evaluate(SVG_SIGNATURE)
                result['final_colors'] = expect_colors(page, source, recording['frames'][-1], 'strain')
                assert result['final_colors']['color_sha256'] != result['modes']['strain']['color_sha256']
                assert last_svg['geometry'] != first_svg['geometry'] and last_svg['styles'] != first_svg['styles']
                page.screenshot(path=str(out / 'actual-svg-final-strain.png'))
                result['obj'] = check_obj(page, out, source, recording['frames'][-1])

                selected = page.evaluate('physicsReview.info().selectedFace')
                for vertex in range(0, len(source['positions']), max(1, len(source['positions']) // 24)):
                    point = page.evaluate('(i)=>physicsReview.projectPoint(i)', vertex)
                    if box['x'] + 10 < point['x'] < box['x'] + box['width'] - 10 and box['y'] + 10 < point['y'] < box['y'] + box['height'] - 10:
                        page.mouse.click(point['x'], point['y'])
                        if page.evaluate('physicsReview.info().selectedFace') != selected:
                            break
                assert page.evaluate('physicsReview.info().selectedFace') != selected, 'Actual raycast face selection on SVG'
                assert page.locator('#uv-preview polygon').count() == 1
                result['actual_face_selection'] = page.evaluate('physicsReview.info().selectedFace')
                result['sources'] = source_tools(page, out)
                page.locator('#body').check()
                receipt['cases'].append(result)

            page.set_viewport_size({'width': 375, 'height': 900})
            page.locator('#view-2d').click()
            page.evaluate('scrollTo(0,0)')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(args.output / 'mobile-2d.png'))
            page.locator('#open-spec').click()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(args.output / 'mobile-full-yaml.png'))
            page.keyboard.press('Escape')
            assert not receipt['page_errors'] and not receipt['console_errors']
            browser.close()
        assert sha(args.html.read_bytes()) == receipt['html_sha256'], 'Candidate changed during verification'
        receipt['verdict'] = 'PASS'
    except Exception as error:
        receipt['failure'] = str(error)
        receipt['traceback'] = traceback.format_exc()
        raise
    finally:
        server.shutdown()
        server.server_close()
        (args.output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({k: receipt.get(k) for k in ['verdict', 'html_sha256', 'failure']}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html', type=Path, required=True)
    parser.add_argument('--run', type=Path, action='append', required=True, help='Original actual run directory; repeat for both supported cases')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser', default='/usr/bin/chromium')
    run(parser.parse_args())
