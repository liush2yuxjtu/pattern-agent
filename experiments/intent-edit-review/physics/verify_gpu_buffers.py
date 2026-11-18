#!/usr/bin/env python3
"""Independent GL color-VBO readback after actual WebGL2 cloth drawElements.

This observes the immutable reviewer HTML through a test-only preload hook.
Expected RGB is computed independently in NumPy from original recorded fields.
It never uses physicsReview.surface().colors or modifies viewer/data/geometry.
"""
import argparse
import base64
import gzip
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys
import threading
import time

import numpy as np
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.playwright_http import new_api_context

MODES = ['cloth', 'strain', 'stress', 'fold', 'contacts', 'seams']
FRAMES = [0, 30, 60]


def sha(raw): return hashlib.sha256(raw).hexdigest()
def unpack(value, width=1):
    a = np.frombuffer(base64.b64decode(value, validate=True), dtype='<f4').astype(float)
    return a.reshape(-1, width) if width > 1 else a


def bind_payload(raw_html, runs):
    match = re.search(rb'<script[^>]*id="physics-payload"[^>]*>(.*?)</script>', raw_html, re.S)
    assert match, 'No embedded actual physics payload'
    payload = json.loads(gzip.decompress(base64.b64decode(match[1], validate=True)))
    local = {}
    for run in runs:
        source_raw = (run/'input.json').read_bytes(); record_raw = (run/'trajectory.json').read_bytes()
        source, record = json.loads(source_raw), json.loads(record_raw)
        assert record['input_sha256'] == sha(source_raw), 'Original recording/input binding failed'
        local[source['case']] = dict(input=source, recording=record, run=str(run),
            input_sha256=sha(source_raw), recording_sha256=sha(record_raw),
            source_dxf_sha256=source['source_dxf_sha256'], source_spec_sha256=source['source_spec_sha256'])
    assert set(local) == {c['input']['case'] for c in payload['cases']}, 'Expected every embedded case'
    for c in payload['cases']:
        original = local[c['input']['case']]
        assert c['input'] == original['input'], 'Embedded physical input differs from original file data'
        assert c['audit']['input_sha256'] == original['input_sha256']
        assert c['audit']['recording_sha256'] == original['recording_sha256']
        original['source_files'] = {}
        for key, file in c['source_package']['files'].items():
            raw = base64.b64decode(file['base64'], validate=True)
            assert len(raw) == file['byte_length'] and sha(raw) == file['sha256']
            path = ROOT/file['path']
            assert path.read_bytes() == raw, 'Embedded source file differs from repository: '+key
            original['source_files'][key] = {k:v for k,v in file.items() if k != 'base64'}
        assert original['source_files']['yaml']['sha256'] == original['source_spec_sha256']
        assert original['source_files']['dxf']['sha256'] == original['source_dxf_sha256']
        packed, recording = c['recording'], original['recording']
        # Independent lossless byte-plane/XOR reconstruction, not the viewer's
        # decoder or builder helper. Check ALL actual arrays, not just samples.
        reconstructed = dict(packed); reconstructed['frames'] = [dict(f) for f in packed['frames']]
        for key, block in c['recording_blocks'].items():
            count, width = block['frames'], block['width']
            assert block['format'] == 'float32-xor-byteplanes/1' and count == len(recording['frames'])
            planes = np.frombuffer(base64.b64decode(block['base64'], validate=True), dtype=np.uint8).reshape(4, count, width)
            words = planes.transpose(1, 2, 0).copy().reshape(count, width*4).view('<u4')
            actual = np.bitwise_xor.accumulate(words, axis=0)
            for index in range(count):
                assert actual[index].tobytes() == base64.b64decode(recording['frames'][index][key]), 'Embedded recording array differs: '+key
                reconstructed['frames'][index][key] = recording['frames'][index][key]
        assert reconstructed == recording, 'Embedded recording metadata differs from original'
    return local, payload['viewer_sources']


def expected_colors(source, recording, index, mode):
    frame = recording['frames'][index]; faces = np.asarray(source['triangles'], int); nv = len(source['positions'])
    if mode == 'contacts':
        return np.where(unpack(frame['contacts'])[:, None] > 0, [.83, .28, .16], [.56, .69, .59])
    fields = unpack(frame['fields'], 8)
    if mode == 'strain': t = (fields[:, 0]+.1)/.6
    elif mode == 'stress': t = (fields[:, 3]+20000)/120000
    elif mode == 'fold': t = (unpack(frame['folds'], 2)[:, 0]+180)/360
    else: t = None
    if t is None: per_face = np.tile([.53, .71, .58], (len(faces), 1))
    else:
        assert np.isfinite(t).all(), 'Recorded field contains nonfinite values'
        palette = np.array([[.16,.29,.65],[.20,.65,.68],[.85,.91,.78],[.94,.65,.25],[.76,.20,.18]])
        per_face = np.column_stack([np.interp(np.clip(t, 0, 1), np.linspace(0, 1, 5), palette[:, channel]) for channel in range(3)])
    indices = faces.ravel(); counts = np.bincount(indices, minlength=nv)
    return np.column_stack([np.bincount(indices, weights=np.repeat(per_face[:, channel], 3), minlength=nv) for channel in range(3)])/np.maximum(counts[:, None], 1)


def run(args):
    started = time.perf_counter(); args.output.mkdir(parents=True, exist_ok=True)
    hook = Path(__file__).with_name('gpu_buffer_observer.js')
    receipt = dict(verdict='RUNNING', expected_html_sha256=args.expected_html_sha256,
        script_sha256=sha(Path(__file__).read_bytes()), observer_sha256=sha(hook.read_bytes()),
        checks=[],
        scope='Actual GL color-attribute buffer contents after real drawElements. Software SwiftShader context, not hardware-GPU certification or fragment-output colorimetry.',
        source_mutation='No viewer, app, geometry, expected-data or HTML edits.', page_errors=[], console_errors=[])
    def save(): (args.output/'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    save()
    try:
        raw_html = args.html.read_bytes(); original_hash = sha(raw_html)
        receipt.update(html_sha256=original_hash, html_bytes=len(raw_html))
        assert re.fullmatch('[0-9a-f]{64}', args.expected_html_sha256), 'Expected SHA256 must be explicit lowercase hex'
        assert original_hash == args.expected_html_sha256, 'Immutable final HTML digest differs'
        local, viewer_sources = bind_payload(raw_html, args.run)
        for name, digest in viewer_sources.items():
            assert sha(Path(__file__).with_name(name).read_bytes()) == digest, 'Viewer source digest differs from frozen HTML: '+name
        receipt.update(viewer_sources=viewer_sources,
            cases=[{k:v for k,v in c.items() if k not in ['input','recording']} for c in local.values()])
        save()
    except Exception as error:
        receipt.update(verdict='FAIL', failure=str(error), seconds=time.perf_counter()-started)
        save(); raise
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k): super().__init__(*a, directory=str(args.html.parent), **k)
        def log_message(self, *a): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/{args.html.name}'; receipt['url'] = url
    try:
        with sync_playwright() as p:
            api = new_api_context(p, url)
            served = api.get(url, timeout=90000)
            assert served.status == 200 and sha(served.body()) == original_hash, 'HTTP response is not identical HTML'
            api.dispose()
            browser = p.chromium.launch(executable_path=args.browser, headless=True,
                args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
            context = browser.new_context(viewport={'width':1440,'height':1080})
            page = context.new_page(); page.add_init_script(path=str(hook))
            page.on('pageerror', lambda e: receipt['page_errors'].append(str(e)))
            page.on('console', lambda m: receipt['console_errors'].append(m.text) if m.type == 'error' else None)
            response = page.goto(url, wait_until='load', timeout=90000)
            assert response.status == 200
            page.wait_for_function('Boolean(window.physicsReview && window.__gpuBufferAudit)', timeout=90000)
            assert not page.evaluate('window.__gpuBufferAudit.unsupported || null')
            for case_id, original in local.items():
                source, recording = original['input'], original['recording']
                page.locator('#case').select_option(case_id)
                for index in FRAMES:
                    page.locator('#timeline').evaluate('(e, index) => {e.value=String(index);e.dispatchEvent(new Event("input", {bubbles:true}));}', index)
                    for mode in MODES:
                        page.locator(f'[data-mode="{mode}"]').click()
                        info = page.evaluate('physicsReview.info()')
                        assert info['case'] == case_id and info['index'] == index and info['mode'] == mode and not info['playing']
                        assert info['sourceDXF'] == original['source_dxf_sha256'] and info['sourceSpec'] == original['source_spec_sha256']
                        token = f'{case_id}:{index}:{mode}'
                        after = page.evaluate('(v) => window.__gpuBufferAudit.arm(v)',
                            dict(nv=len(source['positions']), nt=len(source['triangles']), case=case_id, frame=index, mode=mode, token=token))
                        page.wait_for_function('(token) => window.__gpuBufferAudit.read()?.token===token', arg=token, timeout=15000)
                        actual = page.evaluate('window.__gpuBufferAudit.read()')
                        assert 'error' not in actual, actual
                        assert actual['sequence'] > after and actual['afterSequence'] == after, 'Stale draw snapshot'
                        assert actual['array_buffer_restored'] and not actual['context_info']['context_lost']
                        assert 'SwiftShader' in (actual['context_info']['unmasked_renderer'] or ''), 'Expected explicit software context identity'
                        raw = base64.b64decode(actual.pop('color_float32_base64'), validate=True)
                        colors = np.frombuffer(raw, dtype='<f4').astype(float).reshape(-1, 3)
                        expected = expected_colors(source, recording, index, mode)
                        assert colors.shape == expected.shape
                        error = float(np.max(abs(colors-expected)))
                        assert error <= 2e-6, f'Actual GL buffer RGB mismatch {token}: {error}'
                        name = f'{case_id}-frame{index}-{mode}'
                        (args.output/(name+'.color.f32')).write_bytes(raw)
                        actual.update(max_rgb_error=error, color_buffer_sha256=sha(raw), original_frame_fields_sha256=sha(base64.b64decode(recording['frames'][index]['fields'])))
                        if index == 60:
                            image = args.output/(name+'.png'); page.screenshot(path=str(image), full_page=True)
                            actual['screenshot'] = image.name; actual['screenshot_sha256'] = sha(image.read_bytes())
                        receipt['checks'].append(actual); save()
                        print(json.dumps(dict(case=case_id, frame=index, mode=mode, draw_sequence=actual['sequence'], max_rgb_error=error)), flush=True)
            assert len(receipt['checks']) == len(local)*len(FRAMES)*len(MODES) == 36
            assert not page.evaluate('window.__gpuBufferAudit.errors'), 'Observer reported actual GL read failures'
            assert not receipt['page_errors'] and not receipt['console_errors'], 'Actual page/console errors'
            browser.close()
        assert sha(args.html.read_bytes()) == original_hash, 'HTML bytes changed during verification'
        receipt['verdict'] = 'PASS'
    except Exception as error:
        receipt['verdict'] = 'FAIL'; receipt['failure'] = str(error); raise
    finally:
        server.shutdown(); server.server_close(); receipt['seconds'] = time.perf_counter()-started
        receipt['cleanup'] = 'Owned local HTTP server/browser context closed.'; save()
    print(json.dumps(dict(verdict=receipt['verdict'], actual_gl_buffer_checks=len(receipt['checks']), html_sha256=original_hash)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html', type=Path, default=ROOT/'web/intent-edit-review/physics/index.html')
    parser.add_argument('--expected-html-sha256', required=True, help='Frozen candidate SHA256, supplied independently of file read')
    parser.add_argument('--run', type=Path, action='append')
    parser.add_argument('--output', type=Path, default=ROOT/'work/intent-physics/gpu-buffer37')
    parser.add_argument('--browser', default='/usr/bin/chromium')
    options = parser.parse_args()
    if options.run is None: options.run = [ROOT/'work/intent-physics/baseline-run37', ROOT/'work/intent-physics/cuff-run37']
    run(options)
