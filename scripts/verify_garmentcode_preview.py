#!/usr/bin/env python3
"""Verify the published GarmentCode viewer and downloads independently of its generator.

This verifies a static preview surface, not physical fit or zero intersections.
No NumPy, trimesh, Warp or GPU is required by the geometry reader.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import struct
from urllib.parse import urljoin
import zipfile

from playwright.sync_api import sync_playwright
from verify_pages import local_site

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'garmentcode-preview/'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_glb(data):
    """Decode the actual GLB buffers and reject invalid mesh geometry."""
    magic, version, size = struct.unpack_from('<4sII', data)
    assert magic == b'glTF' and version == 2 and size == len(data), 'Invalid GLB header'
    pos, document, binary = 12, None, None
    while pos < len(data):
        length, kind = struct.unpack_from('<II', data, pos)
        payload = data[pos + 8:pos + 8 + length]
        assert len(payload) == length, 'Truncated GLB chunk'
        if kind == 0x4e4f534a:
            document = json.loads(payload)
        elif kind == 0x004e4942:
            binary = payload
        pos += 8 + length
    assert pos == len(data) and document and binary, 'Missing GLB chunks'

    def values(index):
        a = document['accessors'][index]
        view = document['bufferViews'][a['bufferView']]
        types = {5121: ('B', 1), 5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
        code, size = types[a['componentType']]
        dim = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
        start = view.get('byteOffset', 0) + a.get('byteOffset', 0)
        stride = view.get('byteStride', size * dim)
        assert a['count'] > 0 and stride >= size * dim
        assert start + (a['count'] - 1) * stride + size * dim <= len(binary), 'Accessor outside buffer'
        return [struct.unpack_from('<' + code * dim, binary, start + i * stride) for i in range(a['count'])]

    meshes = document['meshes']
    assert len(meshes) == 1 and len(meshes[0]['primitives']) == 1, 'Expected one garment mesh'
    prim = meshes[0]['primitives'][0]
    assert prim.get('mode', 4) == 4, 'Expected triangle primitive'
    vertices = values(prim['attributes']['POSITION'])
    indices = [x[0] for x in values(prim['indices'])]
    assert len(indices) % 3 == 0
    assert all(len(v) == 3 and all(math.isfinite(x) for x in v) for v in vertices), 'Non-finite vertex'
    assert all(0 <= i < len(vertices) for i in indices), 'Index out of bounds'
    for a, b, c in zip(indices[::3], indices[1::3], indices[2::3]):
        assert len({a, b, c}) == 3, 'Repeated face index'
        u = [vertices[b][k] - vertices[a][k] for k in range(3)]
        v = [vertices[c][k] - vertices[a][k] for k in range(3)]
        cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        assert sum(x*x for x in cross) > 1e-20, 'Degenerate triangle'
    return vertices, indices


def verify(base, output, expected_commit=None, executable='/usr/bin/chromium'):
    base = base.rstrip('/') + '/'
    url = urljoin(base, PREFIX)
    output.mkdir(parents=True, exist_ok=True)
    errors, failed, bad = [], [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=executable, headless=True,
            args=['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            context = browser.new_context(viewport={'width': 1200, 'height': 1000}, accept_downloads=True)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
            page.on('requestfailed', lambda req: failed.append({'url': req.url, 'failure': req.failure}) if req.failure != 'net::ERR_ABORTED' else None)
            page.on('response', lambda res: bad.append({'url': res.url, 'status': res.status}) if res.status >= 400 else None)
            response = page.goto(url, wait_until='networkidle', timeout=60000)
            assert response.status == 200 and page.title() == 'Pattern Agent · GarmentCode 三维预览'
            root = page.locator('#garment-preview')
            page.wait_for_selector('#garment-preview[data-rendered="true"]', timeout=30000)
            assert root.get_attribute('data-mode') == 'final'
            assert '研究预览' in page.locator('[data-role=status]').inner_text()
            assert '零自穿透' in page.locator('.preview-context').inner_text()
            metadata_response = context.request.get(urljoin(base, 'build.json'))
            assert metadata_response.status == 200
            metadata = metadata_response.json()
            if expected_commit:
                assert metadata['commit'] == expected_commit, (metadata['commit'], expected_commit)
            html = response.body()
            assert digest(html) == metadata['files'][PREFIX + 'index.html'], 'Deployed page is not this build'
            records = []
            for link in page.locator('[data-download]').all():
                href = link.get_attribute('href')
                with page.expect_download() as event:
                    link.click()
                download = event.value
                assert download.failure() is None, download.failure()
                target = output / download.suggested_filename
                download.save_as(target)
                data = target.read_bytes()
                assert digest(data) == metadata['files'][PREFIX + href], href
                records.append({'file': target.name, 'sha256': digest(data), 'bytes': len(data)})
            assert len(records) == 4
            vertices, indices = read_glb((output / 'garment.glb').read_bytes())
            assert len(vertices) == 3569 and len(indices) // 3 == 6958
            initial_response = context.request.get(urljoin(url, 'garment-initial.glb'))
            assert initial_response.status == 200
            assert digest(initial_response.body()) == metadata['files'][PREFIX + 'garment-initial.glb']
            initial, initial_indices = read_glb(initial_response.body())
            assert indices == initial_indices
            displacement = max(math.dist(a, b) for a, b in zip(vertices, initial))
            assert displacement > .01, 'Final mesh is not meaningfully deformed'
            pattern = json.loads((output / 'example-shirt_specification.json').read_text())
            assert len(pattern['pattern']['panels']) == 8
            assert digest((output / 'example-shirt_specification.json').read_bytes()) == '048aac4e8b90ffcda38f2b928eebe6354c48a4528ed7f31a885ce38e38ccf88e'
            with zipfile.ZipFile(io.BytesIO((output / 'garmentcode-preview.skill').read_bytes())) as archive:
                assert archive.testzip() is None
                assert 'garmentcode-preview/SKILL.md' in archive.namelist()
                assert 'garmentcode-preview/scripts/garment_preview.py' in archive.namelist()
            simulation_response = context.request.get(urljoin(url, 'simulation-result.json'))
            assert simulation_response.status == 200
            simulation = simulation_response.json()
            assert simulation['simulation']['frames'] == 232
            assert simulation['release']['strict_zero_self_intersections'] == 'FAIL'
            assert simulation['release']['physical_fit'] == 'NOT_RUN'

            canvas = page.locator('canvas')
            def pixels():
                page.wait_for_timeout(120)
                return digest(canvas.screenshot())
            before = pixels()
            page.locator('[data-role=wire]').check()
            wire = pixels()
            assert before != wire, 'Wireframe did not change rendered pixels'
            page.locator('[data-role=body]').uncheck()
            hidden = pixels()
            assert hidden != wire, 'Body toggle did not change rendered pixels'
            page.locator('[data-role=initial]').click()
            page.wait_for_selector('#garment-preview[data-mode="initial"]')
            assert root.get_attribute('data-mode') == 'initial'
            assert '未物理仿真' in page.locator('[data-role=status]').inner_text()
            initial_pixels = pixels()
            assert initial_pixels != hidden
            page.locator('[data-role=final]').click()
            page.wait_for_selector('#garment-preview[data-mode="final"]')
            assert root.get_attribute('data-mode') == 'final'
            before = pixels()
            box = canvas.bounding_box()
            page.mouse.move(box['x']+box['width']*.5, box['y']+box['height']*.5)
            page.mouse.down()
            page.mouse.move(box['x']+box['width']*.7, box['y']+box['height']*.6, steps=8)
            page.mouse.up()
            rotated = pixels()
            assert rotated != before, 'Pointer drag did not rotate model'
            page.mouse.wheel(0, -220)
            zoomed = pixels()
            assert zoomed != rotated, 'Wheel did not zoom model'
            page.locator('[data-role=front]').click()
            front = pixels()
            page.locator('[data-role=back]').click()
            assert front != pixels(), 'Front/back views are identical'
            page.locator('[data-role=body]').check()
            page.locator('[data-role=wire]').uncheck()
            page.locator('[data-role=front]').click()
            page.screenshot(path=str(output / 'desktop.png'), full_page=True)
            page.set_viewport_size({'width': 375, 'height': 812})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile overflow'
            page.locator('[data-role=wire]').check()
            page.screenshot(path=str(output / 'mobile.png'), full_page=True)
            assert not errors and not failed and not bad, {'errors': errors, 'failed': failed, 'http': bad}
            # Reopen the exact downloaded HTML without network access.
            offline = browser.new_context(offline=True, viewport={'width': 900, 'height': 800})
            offline_page = offline.new_page()
            offline_errors = []
            offline_page.on('pageerror', lambda error: offline_errors.append(str(error)))
            offline_page.set_content((output / 'offline-preview.html').read_text())
            offline_page.wait_for_selector('#garment-preview[data-rendered="true"]')
            assert not offline_errors
            offline_page.locator('[data-role=wire]').check()
            offline_page.screenshot(path=str(output / 'offline.png'))
            offline.close()
            # Adjacent edge case: no WebGL still gives a visible image and downloads.
            fallback = browser.new_context()
            fallback.add_init_script("const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...rest){return type==='webgl'?null:original.call(this,type,...rest);};")
            fallback_page = fallback.new_page()
            fallback_page.goto(url, wait_until='networkidle')
            img = fallback_page.locator('img.fallback-image')
            assert img.count() == 1 and img.evaluate('(n)=>n.complete && n.naturalWidth>0')
            assert '静态预览' in fallback_page.locator('[data-role=status]').inner_text()
            fallback.close()
            missing = context.request.get(urljoin(url, 'no-such-model.glb'))
            assert missing.status == 404, 'Missing model should not return an HTML fallback'
            report = {'verdict': 'PASS', 'claim': 'Viewer and downloads work; not a garment-release approval',
                'url': url, 'commit': metadata['commit'], 'source_sha256': metadata['source_sha256'],
                'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'downloads': records,
                'geometry': {'vertices': len(vertices), 'triangles': len(indices)//3,
                             'max_vertex_displacement_m': displacement, 'decoder': 'independent stdlib GLB reader'},
                'checks': ['actual WebGL pixels', 'wireframe', 'body visibility', 'initial/final switch',
                           'real pointer rotation', 'wheel zoom', 'front/back', 'four downloaded file hashes',
                           'offline downloaded HTML reopen', '375px mobile', 'WebGL-disabled image fallback',
                           'missing model returns 404'],
                'errors': errors, 'failed_requests': failed, 'asset_http_errors': bad,
                'strict_geometry_release': 'FAIL', 'physical_fit': 'NOT_RUN'}
            (output / 'browser-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return report
        finally:
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url')
    parser.add_argument('--directory', type=Path, default=ROOT/'dist')
    parser.add_argument('--output', type=Path, default=ROOT/'work/verify-garmentcode-preview')
    parser.add_argument('--expected-commit')
    parser.add_argument('--browser', default='/usr/bin/chromium')
    args = parser.parse_args()
    if args.base_url:
        verify(args.base_url, args.output, args.expected_commit, args.browser)
    else:
        with local_site(args.directory) as base:
            verify(base, args.output, args.expected_commit, args.browser)
