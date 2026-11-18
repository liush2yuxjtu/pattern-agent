"""Reopen an actual saved HTML and read its heatmap colors from the draw buffer.

The WebGL hooks forward every original call unchanged. Only one requested
heatmap draw is read back at a time; the ARRAY_BUFFER binding is restored.
Expected RGB is calculated independently with NumPy from coordinates and UVs.
"""
import argparse
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

import numpy as np
from independent_fields import folds_reopen
from playwright.sync_api import sync_playwright


HOOK = r"""(() => {
  window.__captureHeatmap = false;
  for (const name of ['drawArrays', 'drawElements']) {
    const original = WebGL2RenderingContext.prototype[name];
    WebGL2RenderingContext.prototype[name] = function(...args) {
      const result = Reflect.apply(original, this, args);
      if (!window.__captureHeatmap) return result;
      const program = this.getParameter(this.CURRENT_PROGRAM);
      const location = this.getAttribLocation(program, 'color');
      if (location < 0 || !this.getVertexAttrib(location, this.VERTEX_ATTRIB_ARRAY_ENABLED)) return result;
      const buffer = this.getVertexAttrib(location, this.VERTEX_ATTRIB_ARRAY_BUFFER_BINDING);
      const previous = this.getParameter(this.ARRAY_BUFFER_BINDING);
      try {
        this.bindBuffer(this.ARRAY_BUFFER, buffer);
        const bytes = this.getBufferParameter(this.ARRAY_BUFFER, this.BUFFER_SIZE);
        if (bytes !== 3584 * 9 * 4) return result;
        const values = new Float32Array(bytes / 4);
        this.getBufferSubData(this.ARRAY_BUFFER, 0, values);
        window.__heatmapCapture = {values: Array.from(values), location,
          attributeSize: this.getVertexAttrib(location, this.VERTEX_ATTRIB_ARRAY_SIZE),
          attributeType: this.getVertexAttrib(location, this.VERTEX_ATTRIB_ARRAY_TYPE),
          webglVersion: this.getParameter(this.VERSION)};
        window.__captureHeatmap = false;
      } finally { this.bindBuffer(this.ARRAY_BUFFER, previous); }
      return result;
    };
  }
})();"""


def expected_colors(state, view):
    p = np.asarray(state['positions']).reshape(-1, 3)
    t = np.asarray(state['triangles']).reshape(-1, 3)
    uv = np.asarray(state['materialCoordinates']).reshape(-1, 3, 2)
    dm = np.stack((uv[:, 1] - uv[:, 0], uv[:, 2] - uv[:, 0]), axis=-1)
    ds = np.stack((p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]]), axis=-1)
    f = ds @ np.linalg.inv(dm)
    c = f.transpose(0, 2, 1) @ f
    stretch = np.sqrt(np.linalg.eigvalsh(c)[:, 1])
    green = (c - np.eye(2)) / 2
    e, nu = state['material']['E'], state['material']['nu']
    sigma = np.zeros_like(c)
    sigma[:, 0, 0] = e / (1 - nu ** 2) * (green[:, 0, 0] + nu * green[:, 1, 1])
    sigma[:, 1, 1] = e / (1 - nu ** 2) * (green[:, 1, 1] + nu * green[:, 0, 0])
    sigma[:, 0, 1] = sigma[:, 1, 0] = e / (1 + nu) * green[:, 0, 1]
    stress = np.maximum(0, np.linalg.eigvalsh(sigma)[:, 1]) / 1000
    if view in ['fold','curvature']:
        folds_reopen(state)
        field='triangleAngle_deg' if view=='fold' else 'triangleCurvature_per_m'
        scalar=np.abs(np.asarray(state['folding'][field]))/(60 if view=='fold' else 100)
    else:
        scalar = stress / 20 if view == 'stress' else (stretch - 1) / .2
    # Documented six-color ramp, sRGB to linear RGB before interpolation.
    colors = ['256bc2', '29b9a5', '92ce5f', 'f2ca4e', 'e77038', 'b62238']
    srgb = np.array([[int(h[i:i+2], 16) / 255 for i in (0, 2, 4)] for h in colors])
    linear = np.where(srgb <= .04045, srgb / 12.92, ((srgb + .055) / 1.055) ** 2.4)
    q = np.clip(scalar, 0, 1) * 5
    low = np.minimum(4, np.floor(q).astype(int))
    rgb = linear[low] + (linear[low + 1] - linear[low]) * (q - low)[:, None]
    return np.repeat(rgb, 3, axis=0).reshape(-1)


def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(args.html.parent)))
    Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/{args.html.name}'
    receipt = {'savedHTML_SHA256': hashlib.sha256(args.html.read_bytes()).hexdigest(), 'views': {}, 'errors': [],
               'scope': 'Actual downloaded HTML, coordinates independently recomputed, actual active draw attribute GPU readback; calibrated material accuracy NOT_RUN'}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=args.browser, headless=True, args=['--no-sandbox', '--enable-unsafe-swiftshader'])
            context = browser.new_context(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
            context.add_init_script(HOOK)
            page = context.new_page()
            page.on('pageerror', lambda e: receipt['errors'].append(str(e)))
            page.goto(url, wait_until='networkidle')
            page.wait_for_function('window.clothLab?.ready')
            context.set_offline(True)
            state = page.evaluate('clothLab.project()')
            assert state['simulation']['steps'] == 360
            for view in ['strain', 'stress', 'fold', 'curvature']:
                page.evaluate("""view=>{
                    window.__heatmapCapture=null;
                    window.__captureHeatmap=false;
                    document.querySelector(`[data-view="${view}"]`).addEventListener('click',
                      ()=>{window.__captureHeatmap=true;}, {capture:true,once:true});
                }""", view)
                page.get_by_role('button', name={'fold':'Fold · 折角','curvature':'Curvature · 曲率'}.get(view,view.capitalize()), exact=True).click()
                page.wait_for_function('window.__heatmapCapture !== null')
                gpu = page.evaluate('window.__heatmapCapture')
                actual = np.asarray(gpu.pop('values'), dtype=np.float32)
                expected = expected_colors(state, view)
                error = float(np.max(np.abs(actual - expected)))
                assert gpu['attributeSize'] == 3 and gpu['attributeType'] == 5126
                assert actual.shape == expected.shape and error < 2e-6
                assert len(np.unique(actual.reshape(-1, 9), axis=0)) > 10
                np.savez_compressed(args.output / (view + '-gpu-colors.npz'), actual=actual, expected=expected)
                page.screenshot(path=str(args.output / (view + '-gpu.png')), full_page=True)
                receipt['views'][view] = {**gpu, 'componentsCompared': len(actual), 'maxLinearRGBError': error, 'verdict': 'PASS'}
            browser.close()
        assert not receipt['errors']
        receipt['verdict'] = 'PASS'
    finally:
        server.shutdown()
        server.server_close()
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--html', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser', default='/usr/bin/chromium')
    run(parser.parse_args())
