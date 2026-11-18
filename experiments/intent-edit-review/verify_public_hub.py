#!/usr/bin/env python3
"""Check published center navigation against exact public source revision bytes.

Local verify_hub.py additionally audits all repository resource paths. This driver
binds the deployed browser responses to that already audited public revision.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import traceback
from urllib.request import urlopen
from playwright.sync_api import sync_playwright

SITE = 'https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/'
RAW = 'https://raw.githubusercontent.com/liush2yuxjtu/pattern-agent/'
README_PATH = 'experiments/intent-edit-review/README.md'
README_URL = 'https://github.com/liush2yuxjtu/pattern-agent/blob/main/' + README_PATH


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(args):
    if not re.fullmatch(r'[0-9a-f]{40}', args.source_revision):
        raise ValueError('Supply a full immutable public source commit SHA')
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    report = {'verdict': 'FAIL', 'source_revision': args.source_revision,
              'errors': [], 'bad_responses': [], 'round_trips': [], 'viewports': []}
    try:
        def source(path):
            with urlopen(RAW + args.source_revision + '/' + path, timeout=30) as response:
                return response.read()
        expected = {route: sha(source('web/intent-edit-review/' + suffix)) for route, suffix in
                    [('hub', 'experiment/index.html'), ('demo', 'index.html'),
                     ('docs', 'docs/index.html'), ('sewn', 'sewn/index.html')]}
        readme_sha = sha(source(README_PATH))
        report.update({'expected_html_sha256': expected, 'readme_sha256': readme_sha})
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.browser,
                args=['--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
            with browser:
                context = browser.new_context(viewport={'width': 1448, 'height': 1000})
                page = context.new_page()
                def observe(target):
                    target.on('pageerror', lambda error: report['errors'].append(str(error)))
                    target.on('console', lambda msg: report['errors'].append(msg.text) if msg.type == 'error' else None)
                    target.on('response', lambda response: report['bad_responses'].append(
                        {'url': response.url, 'status': response.status}) if response.status >= 400 else None)
                observe(page)
                def is_hub(target):
                    assert target.url == SITE + 'experiment/'
                    assert target.locator('meta[name="experiment-readme-sha256"]').get_attribute('content') == readme_sha
                    assert target.locator('[data-readme]').get_attribute('href') == README_URL
                response = page.goto(SITE + 'experiment/', wait_until='load')
                assert response.status == 200 and sha(response.body()) == expected['hub']
                is_hub(page)
                for width in [1448, 768, 375, 320]:
                    page.set_viewport_size({'width': width, 'height': 900})
                    page.evaluate('scrollTo(0,0)')
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    page.screenshot(path=str(out / f'public-hub-{width}.png'))
                    page.locator('nav a').last.click()
                    assert page.evaluate('Boolean(location.hash)')
                    report['viewports'].append({'width': width, 'overflow': False, 'toc_clicked': True})
                page.set_viewport_size({'width': 1448, 'height': 1000})
                for route in ['demo', 'docs', 'sewn']:
                    page.goto(SITE + 'experiment/', wait_until='load')
                    with page.expect_navigation(wait_until='load') as navigation:
                        page.locator(f'[data-route="{route}"]').click()
                    response = navigation.value
                    actual_sha = sha(response.body())
                    assert response.status == 200 and actual_sha == expected[route], route
                    if route == 'demo':
                        page.locator('body[data-ready="true"]').wait_for(timeout=30000)
                        assert page.locator('#case-select option').count() == 4
                        assert page.locator('canvas[data-ready="true"]').count() == 2
                        link = page.locator('[data-experiment-center]')
                        link.scroll_into_view_if_needed()
                        page.screenshot(path=str(out / 'public-comparison-footer.png'))
                        with context.expect_page() as opened:
                            link.click()
                        popup = opened.value; observe(popup); popup.wait_for_load_state('load')
                        is_hub(popup); popup.close(); page.go_back(wait_until='load')
                        returned = 'clicked actual footer; new tab returned to hub'
                    else:
                        if route == 'docs':
                            assert page.locator('article section.level1').count() == 4
                        else:
                            assert 'BLOCKED' in page.locator('.scope').inner_text()
                            assert page.locator('iframe').count() == 2
                        page.locator('[data-experiment-center]').click()
                        page.wait_for_load_state('load'); returned = 'clicked actual header return link'
                    is_hub(page)
                    report['round_trips'].append({'route': route, 'actual_html_sha256': actual_sha, 'return': returned})
                assert not report['errors'] and not report['bad_responses']
        report['verdict'] = 'PASS'
    except Exception as error:
        report.update({'failure': str(error), 'traceback': traceback.format_exc()})
        raise
    finally:
        (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({k: report.get(k) for k in ['verdict', 'source_revision', 'failure']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-revision', required=True)
    parser.add_argument('--browser', default='/usr/bin/chromium')
    parser.add_argument('--output', required=True, type=Path)
    verify(parser.parse_args())
