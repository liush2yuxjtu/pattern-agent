#!/usr/bin/env python3
"""Verify the rendered handbook, responsive navigation and real demo link."""
import argparse
import hashlib
import json
import threading
import traceback
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / 'web/intent-edit-review/docs/index.html'
DEMO = REPO / 'web/intent-edit-review/index.html'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def run(args):
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    report = {'verdict': 'FAIL', 'docs_sha256': sha(DOCS.read_bytes()), 'demo_sha256': sha(DEMO.read_bytes()),
              'page_errors': [], 'bad_responses': [], 'viewports': []}
    server = None
    try:
        if args.base_url:
            url = args.base_url.rstrip('/') + '/'
        else:
            server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(REPO / 'web')))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f'http://127.0.0.1:{server.server_port}/intent-edit-review/docs/'
        report['url'] = url
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.browser, args=['--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
            page = browser.new_page(viewport={'width': 1448, 'height': 1000})
            page.on('pageerror', lambda e: report['page_errors'].append(str(e)))
            page.on('console', lambda m: report['page_errors'].append(m.text) if m.type == 'error' else None)
            page.on('response', lambda r: report['bad_responses'].append({'url': r.url, 'status': r.status}) if r.status >= 400 else None)
            response = page.goto(url, wait_until='load')
            assert response.status == 200 and sha(response.body()) == report['docs_sha256']
            assert page.title() == '原型与改版对照｜项目文档'
            assert page.locator('article section.level1').count() == 4
            assert page.locator('article').inner_text().count('geometry-patch.json') >= 2
            assert 'NOT_RUN' in page.locator('article').inner_text()
            assert page.locator('a[data-source]').get_attribute('href') == 'https://github.com/liush2yuxjtu/pattern-agent/tree/main/experiments/intent-edit-review/'
            anchors = page.locator('nav a').evaluate_all('(links)=>links.map(a=>a.getAttribute("href"))')
            assert len(anchors) >= 20
            for href in anchors:
                assert href.startswith('#') and page.locator('[id="' + href[1:] + '"]').count() == 1, href
            report['anchors_checked'] = len(anchors)
            for width, height in [(1448, 1000), (375, 812), (320, 740)]:
                page.set_viewport_size({'width': width, 'height': height})
                page.evaluate('scrollTo(0,0)')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), f'overflow at {width}'
                page.screenshot(path=str(out / f'docs-{width}.png'))
                for anchor in ['guide', 'architecture', 'data-audit', 'release']:
                    page.locator(f'nav a[href="#{anchor}"]').click()
                    assert page.evaluate('location.hash') == '#' + anchor
                    assert page.locator('#' + anchor + ' h1').is_visible()
                    if width == 1448 and anchor in ['data-audit', 'release']:
                        page.screenshot(path=str(out / f'docs-{anchor}-1448.png'))
                report['viewports'].append({'width': width, 'height': height, 'overflow': False, 'toc_navigation': 'PASS'})
            page.set_viewport_size({'width': 1448, 'height': 1000})
            page.evaluate('scrollTo(0,0)')
            with page.expect_navigation(wait_until='load') as navigation:
                page.locator('a[data-demo]').click()
            demo_response = navigation.value
            assert sha(demo_response.body()) == report['demo_sha256']
            assert '/intent-edit-review/' in page.url and '/docs/' not in page.url
            page.locator('body[data-ready="true"]').wait_for(timeout=30000)
            assert page.locator('#case-select option').count() == 4
            assert page.locator('canvas[data-ready="true"]').count() == 2
            report['demo_link'] = {'url': page.url, 'sha256': sha(demo_response.body()), 'real_viewer_ready': True}
            page.screenshot(path=str(out / 'demo-from-docs.png'), full_page=True)
            page.go_back(wait_until='load')
            assert page.title() == '原型与改版对照｜项目文档'
            assert not report['page_errors'] and not report['bad_responses']
            browser.close()
        report['verdict'] = 'PASS'
    except Exception as e:
        report['failure'] = str(e); report['traceback'] = traceback.format_exc()
        raise
    finally:
        if server:
            server.shutdown(); server.server_close()
        (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({k: report.get(k) for k in ['verdict', 'docs_sha256', 'anchors_checked', 'failure']}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=REPO / 'work/intent-edit-review/docs-browser')
    parser.add_argument('--base-url', help='Actual published docs URL.')
    parser.add_argument('--browser', default='/usr/bin/chromium')
    run(parser.parse_args())
