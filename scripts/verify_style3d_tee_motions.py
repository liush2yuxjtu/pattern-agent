#!/usr/bin/env python3
"""Verify the delivered Style3D report and media on a local or hosted Pages site."""
import argparse
from contextlib import contextmanager
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from verify_pages import new_api_context

CASE = 'style3d-tee-motions/'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


@contextmanager
def local_media_site(directory):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, *args):
            pass

        def do_GET(self):
            if not self.path.startswith('/pattern-agent/'):
                self.send_error(404)
                return
            self.path = self.path[len('/pattern-agent'):]
            requested = self.headers.get('Range')
            path = Path(self.translate_path(self.path))
            if not requested or path.suffix != '.mp4' or not path.is_file():
                super().do_GET()
                return
            size = path.stat().st_size
            bounds = re.fullmatch(r'bytes=(\d+)-(\d*)', requested)
            if not bounds or int(bounds[1]) >= size:
                self.send_error(416)
                return
            start = int(bounds[1])
            end = min(int(bounds[2] or size-1), size-1)
            if end < start:
                self.send_error(416)
                return
            length = end-start+1
            self.send_response(206)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.send_header('Content-Length', str(length))
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()
            with path.open('rb') as stream:
                stream.seek(start)
                try:
                    self.wfile.write(stream.read(length))
                except (BrokenPipeError, ConnectionResetError):
                    pass  # Chromium can cancel its previous range after a seek.

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/pattern-agent/'
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def verify(base, output, executable, expected_commit=None):
    base = base.rstrip('/') + '/'
    route = urljoin(base, CASE)
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=executable, headless=True)
        api = new_api_context(pw, base)
        try:
            page = browser.new_page(viewport={'width': 1440, 'height': 1100}, accept_downloads=True)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('response', lambda response: errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
            meta_response = api.get(urljoin(base, 'build.json'))
            assert meta_response.ok
            meta = meta_response.json()
            if expected_commit:
                assert meta['commit'] == expected_commit, (meta['commit'], expected_commit)
            assert page.goto(base).ok
            page.get_by_role('link', name='M 码 T 恤十项动作复验', exact=True).click()
            page.wait_for_url(route)
            assert page.locator('tbody tr').count() == 10
            assert all('→ 0' in row for row in page.locator('tbody tr').all_text_contents())
            assert page.locator('video').count() == 5
            media = []
            for video in page.locator('video').all():
                video.scroll_into_view_if_needed()
                media.append(video.evaluate("""async video => {
                    video.muted = true;
                    let timer;
                    try {
                        await Promise.race([video.play(), new Promise((_, reject) => {
                            timer = setTimeout(() => reject(new Error(`Playback timeout: ${video.currentSrc}`)), 12000);
                        })]);
                        return {source: video.currentSrc.split('/').pop(), seconds: video.duration, width: video.videoWidth};
                    } finally {
                        clearTimeout(timer);
                        video.pause();
                    }
                }"""))
            assert all(item['width'] > 0 and item['seconds'] > 5 for item in media), media
            assert abs(media[0]['seconds'] - 75.625) < 0.05, media[0]
            target = page.get_by_role('link', name='跳到坐下再起身', exact=True)
            timestamp = float(target.get_attribute('data-seek'))
            target.click()
            page.wait_for_function('time => Math.abs(document.querySelector("#retest-player").currentTime - time) < 0.2', arg=timestamp)
            page.locator('#retest-player').evaluate('video => { video.play().catch(console.error); }')
            page.wait_for_function('time => document.querySelector("#retest-player").currentTime > time + 0.35', arg=timestamp)
            page.locator('#retest-player').evaluate('video => video.pause()')
            for image in page.locator('.gallery img').all():
                assert image.evaluate('async img => { await img.decode(); return img.naturalWidth > 0; }')
            digests = {}
            for label in ('下载视频', '动作汇总 CSV', '逐帧 CSV', '678 条逐片数据 CSV'):
                link = page.get_by_role('link', name=label, exact=True)
                rel = CASE + link.get_attribute('href')
                with page.expect_download() as result:
                    link.click()
                download = result.value
                assert download.failure() is None
                digest = hashlib.sha256(Path(download.path()).read_bytes()).hexdigest()
                assert digest == meta['files'][rel], rel
                digests[rel] = digest
            page.evaluate('window.scrollTo(0, 0)')
            page.screenshot(path=str(output / 'desktop.png'))
            for name in ('retest', 'baseline', 'try-on', 'avatar'):
                assert page.goto(urljoin(route, f'{name}.html')).ok
                assert page.locator('h1').is_visible() and page.locator('table').count() > 0
                for image in page.locator('main img').all():
                    assert image.evaluate('async img => { await img.decode(); return img.naturalWidth > 0; }')
            page.set_viewport_size({'width':375, 'height':812})
            assert page.goto(route).ok
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert page.locator('#motions .scroll').evaluate('node => node.scrollWidth > node.clientWidth')
            page.screenshot(path=str(output / 'mobile.png'))
            missing = api.get(urljoin(route, 'media/no-such-motion.mp4'))
            assert missing.status == 404, (missing.status, missing.url)
            assert not errors, errors
            result = {'verdict':'PASS', 'commit':meta['commit'], 'url':route, 'reports':4,
                      'videos':media, 'seek_seconds':timestamp, 'downloads':digests, 'missing_asset_status':missing.status}
            (output / 'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
            print(json.dumps(result, ensure_ascii=False))
        finally:
            api.dispose()
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url')
    parser.add_argument('--directory', type=Path, default=Path('dist'))
    parser.add_argument('--output', type=Path, default=Path('work/verify-style3d-tee-motions'))
    parser.add_argument('--expected-commit')
    parser.add_argument('--browser', default=CHROME)
    args = parser.parse_args()
    if args.base_url:
        verify(args.base_url, args.output, args.browser, args.expected_commit)
    else:
        with local_media_site(args.directory.resolve()) as base:
            verify(base, args.output, args.browser, args.expected_commit)
