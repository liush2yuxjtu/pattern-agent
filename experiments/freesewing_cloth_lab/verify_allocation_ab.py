"""Compare actual fixed-step coordinates against an unchanged baseline HTML.

The baseline is a real prior artifact, not a second implementation or fixture.
Performance is recorded; coordinate and previous-position equality is required.
"""
import argparse
from functools import partial
import gzip
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
import time

import numpy as np
from playwright.sync_api import sync_playwright


def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(args.baseline_html.parent)))
    Thread(target=server.serve_forever, daemon=True).start()
    baseline = f'http://127.0.0.1:{server.server_port}/{args.baseline_html.name}'
    states, result = {}, {'cases': {}}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox', '--enable-unsafe-swiftshader'])
            for name, url in [('baseline', baseline), ('optimized', args.url)]:
                page = browser.new_page(viewport={'width': 1440, 'height': 1100})
                response = page.goto(url, wait_until='networkidle')
                page.wait_for_function('window.clothLab?.ready')
                page.evaluate('clothLab.reset()')
                start = time.perf_counter()
                page.evaluate('(n)=>clothLab.step(n)', args.steps)
                state = page.evaluate('clothLab.project()')
                states[name] = state
                with gzip.open(args.output / (name + '.json.gz'), 'wt') as file:
                    json.dump(state, file)
                result['cases'][name] = {'htmlSHA256': hashlib.sha256(response.body()).hexdigest(), 'wallSeconds': time.perf_counter() - start, 'stats': state['simulation']}
                page.close()
            browser.close()
        result['equal'] = {key: np.array_equal(states['baseline'][key], states['optimized'][key]) for key in ['positions', 'previous', 'materialCoordinates']}
        result['maxCoordinateDifference_m'] = float(np.max(np.abs(np.asarray(states['baseline']['positions']) - states['optimized']['positions'])))
        result['verdict'] = 'PASS' if all(result['equal'].values()) else 'FAIL'
        (args.output / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
        return result
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--baseline-html', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--steps', type=int, default=120)
    result = run(parser.parse_args())
    raise SystemExit(0 if result['verdict'] == 'PASS' else 2)
