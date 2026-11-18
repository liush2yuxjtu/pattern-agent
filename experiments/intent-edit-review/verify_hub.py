#!/usr/bin/env python3
"""Verify the README-centered experiment hub and actual related-page round trips."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import threading
import traceback
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit
from playwright.sync_api import sync_playwright
from gallery_checks import canvas_pixels, drive_gallery

REPO = Path(__file__).resolve().parents[2]
PROJECT = REPO / 'experiments/intent-edit-review'
README_URL = 'https://github.com/liush2yuxjtu/pattern-agent/blob/main/experiments/intent-edit-review/README.md'
ONLINE_HUB = 'https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/experiment/'


def sha(raw): return hashlib.sha256(raw).hexdigest()


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args): pass


def run(args):
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    report = {'verdict': 'FAIL', 'readme_sha256': sha((PROJECT / 'README.md').read_bytes()),
              'hub_sha256': sha((REPO / 'web/intent-edit-review/experiment/index.html').read_bytes()),
              'errors': [], 'bad_responses': [], 'round_trips': [], 'viewports': []}
    server = None
    try:
        if args.base_url: url = args.base_url.rstrip('/') + '/'
        else:
            server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(REPO / 'web')))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f'http://127.0.0.1:{server.server_port}/intent-edit-review/experiment/'
        report['url'] = url
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.browser, args=['--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
            context = browser.new_context(viewport={'width': 1448, 'height': 1000})
            page = context.new_page()
            page.on('pageerror', lambda e: report['errors'].append(str(e)))
            page.on('console', lambda m: report['errors'].append(m.text) if m.type == 'error' else None)
            page.on('response', lambda r: report['bad_responses'].append({'url': r.url[:160], 'status': r.status}) if r.status >= 400 else None)
            response = page.goto(url, wait_until='load')
            assert response.status == 200 and sha(response.body()) == report['hub_sha256']
            assert page.locator('meta[name="experiment-readme-sha256"]').get_attribute('content') == report['readme_sha256']
            source_data = json.loads(re.search(r'<script[^>]*id="app-data"[^>]*>(.*?)</script>',
                (REPO / 'web/intent-edit-review/index.html').read_text(), re.S)[1])
            assert json.loads(page.locator('#gallery-data').text_content()) == source_data
            report['gallery'] = drive_gallery(page, out / 'gallery', source_data)
            page.locator('[data-view="readme"]').click()
            assert page.locator('#readme-title').inner_text() == '实验说明'
            assert page.locator('[data-readme]').get_attribute('href') == README_URL
            assert 'BLOCKED' in page.locator('#experiment-content').inner_text()
            repo_links = []
            for href in page.locator('#experiment-content a').evaluate_all('(as)=>as.map(a=>a.href)'):
                parsed = urlsplit(href); parts = unquote(parsed.path).strip('/').split('/', 4)
                if parsed.netloc == 'github.com' and len(parts) == 5 and parts[:2] == ['liush2yuxjtu', 'pattern-agent'] and parts[2] in ['blob', 'tree'] and parts[3] == 'main':
                    target = (REPO / parts[4]).resolve(); assert target.is_relative_to(REPO) and target.exists(), href
                    assert target.is_dir() == (parts[2] == 'tree'), href
                    repo_links.append(parts[4])
            required = {'patterns/fitted-tshirt/input-spec.yaml', 'patterns/fitted-tshirt/input.dxf',
                        'experiments/intent-edit-benchmark/README.md', 'experiments/intent-edit-review/sewn/README.md',
                        'docs/verification/intent-edit-benchmark-20261117',
                        'docs/verification/intent-edit-review-20261118/README.md',
                        'docs/verification/intent-sewn-chain-20261118/README.md'}
            assert required <= set(repo_links)
            report['repo_links_checked'] = len(repo_links)
            anchors = page.locator('nav[aria-label="实验总览目录"] a').evaluate_all('(as)=>as.map(a=>a.getAttribute("href"))')
            for href in anchors:
                assert href.startswith('#') and page.locator('[id="' + unquote(href[1:]) + '"]').count() == 1
            report['toc_links_checked'] = len(anchors)
            for width, height in [(1448, 1000), (768, 1000), (375, 850), (320, 740)]:
                page.set_viewport_size({'width': width, 'height': height}); page.evaluate('scrollTo(0,0)')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), width
                page.screenshot(path=str(out / f'hub-{width}.png'))
                heading = page.get_by_role('heading', name='四个改版案例', exact=True)
                heading.evaluate('(el)=>scrollTo(0,el.getBoundingClientRect().top+scrollY-20)')
                page.screenshot(path=str(out / f'hub-cases-{width}.png'))
                page.locator('nav[aria-label="实验总览目录"] a').last.click(); assert page.evaluate('Boolean(location.hash)')
                report['viewports'].append({'width': width, 'overflow': False, 'toc_click': True})
            page.set_viewport_size({'width': 1448, 'height': 1000})
            for route in ['demo', 'docs', 'sewn']:
                page.goto(url, wait_until='load')
                page.locator('[data-view="readme"]').click()
                with page.expect_navigation(wait_until='load') as entered:
                    page.locator(f'[data-route="{route}"]').click()
                target_url = page.url
                target_sha = sha(entered.value.body())
                if route == 'demo':
                    page.locator('body[data-ready="true"]').wait_for(timeout=30000)
                    assert page.locator('#case-select option').count() == 4
                    assert page.locator('canvas[data-ready="true"]').count() == 2
                    link = page.locator('[data-experiment-center]'); assert link.get_attribute('href') == ONLINE_HUB
                    link.scroll_into_view_if_needed(); page.screenshot(path=str(out / 'comparison-footer.png'))
                    if args.base_url:
                        with context.expect_page() as opened: link.click()
                        popup = opened.value; popup.wait_for_load_state('load')
                        assert popup.url == url
                        assert popup.locator('meta[name="experiment-readme-sha256"]').get_attribute('content') == report['readme_sha256']
                        popup.close(); returned = 'actual online footer popup'
                    else: returned = 'online footer URL checked; local browser Back verified'
                    page.go_back(wait_until='load')
                else:
                    if route == 'docs': assert page.locator('article section.level1').count() == 4
                    else:
                        assert 'BLOCKED' in page.locator('.scope').inner_text()
                        assert page.locator('iframe').count() == 2
                    page.locator('[data-experiment-center]').click(); page.wait_for_load_state('load')
                    assert page.locator('meta[name="experiment-readme-sha256"]').get_attribute('content') == report['readme_sha256']
                    returned = 'actual return-to-center link'
                assert page.title() == '纸样设计意图实验｜案例库'
                report['round_trips'].append({'route': route, 'target_url': target_url, 'return': returned,
                    'target_sha256': target_sha})
            assert not report['errors'] and not report['bad_responses']
            software = browser.new_context(viewport={'width': 1280, 'height': 900})
            software.add_init_script("""const original=HTMLCanvasElement.prototype.getContext;
                HTMLCanvasElement.prototype.getContext=function(kind,...args){
                    return /webgl/i.test(kind)?null:original.call(this,kind,...args);
                };""")
            fallback = software.new_page(); fallback.goto(url, wait_until='load')
            fallback.on('pageerror', lambda error: report['errors'].append(str(error)))
            fallback.locator('body[data-gallery-ready="true"]').wait_for(timeout=30000)
            assert fallback.locator('.case-media canvas[data-mode="software"]').count() == 5
            canvas = fallback.locator('.case-card[data-case-id="baseline"] canvas')
            before = canvas_pixels(canvas); canvas.focus(); fallback.keyboard.press('ArrowRight')
            after = canvas_pixels(canvas); assert before['sha256'] != after['sha256']
            fallback.screenshot(path=str(out / 'gallery-software.png'))
            report['software_gallery'] = {'models': 5, 'before': before, 'after': after}
            software.close()
            offline = browser.new_context(offline=True, viewport={'width': 375, 'height': 850})
            isolated = offline.new_page(); requests = []
            isolated.on('pageerror', lambda error: report['errors'].append(str(error)))
            isolated.on('request', lambda request: requests.append(request.url))
            isolated.set_content((REPO / 'web/intent-edit-review/experiment/index.html').read_text(), wait_until='load')
            isolated.locator('body[data-gallery-ready="true"]').wait_for(timeout=30000)
            isolated.locator('[data-filter="sewn"]').click(); assert isolated.locator('.case-card:visible').count() == 2
            isolated.locator('[data-open-case="03_cuff_width"]').click()
            with isolated.expect_download() as saved:
                isolated.locator('[data-case-file="dxf"]').click()
            saved.value.save_as(out / 'offline-cuff.dxf')
            expected = next(e for e in source_data['cases'] if e['id'] == '03_cuff_width')['files']['dxf']['sha256']
            assert sha((out / 'offline-cuff.dxf').read_bytes()) == expected and not requests
            report['offline_gallery'] = {'requests': requests, 'actual_dxf_sha256': expected,
                'scope': 'Exact self-contained HTML loaded with networking disabled; direct file URL policy not bypassed.'}
            offline.close()
            assert not report['errors'] and not report['bad_responses']
            browser.close()
        report['verdict'] = 'PASS'
    except Exception as error:
        report['failure'] = str(error); report['traceback'] = traceback.format_exc(); raise
    finally:
        if server: server.shutdown(); server.server_close()
        (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({k: report.get(k) for k in ['verdict', 'repo_links_checked', 'toc_links_checked', 'failure']}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--base-url'); p.add_argument('--browser', default='/usr/bin/chromium'); run(p.parse_args())
