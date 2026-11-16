#!/usr/bin/env python3
"""Exercise newly generated self-contained skill previews in real Chromium."""
import argparse
import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def verify(previews, output, executable):
    output.mkdir(parents=True, exist_ok=True)
    reports = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=executable, headless=True,
            args=['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader',
                  '--enable-unsafe-swiftshader'])
        try:
            for index, path in enumerate(previews):
                context = browser.new_context(offline=True, viewport={'width': 1100, 'height': 850})
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
                # The managed Chromium policy blocks file:// navigation. Render the
                # exact saved HTML bytes in an offline context, as the project
                # publication verifier does; do not change browser policy flags.
                page.set_content(path.read_text(), wait_until='load')
                page.wait_for_selector('#garment-preview[data-rendered="true"]')
                assert page.title() == 'GarmentCode 三维预览'
                canvas = page.locator('canvas')
                def pixels():
                    page.wait_for_timeout(150)
                    return hashlib.sha256(canvas.screenshot()).hexdigest()
                original = pixels()
                page.locator('[data-role=wire]').check()
                wire = pixels()
                assert original != wire, 'Wireframe did not change actual canvas pixels'
                box = canvas.bounding_box()
                page.mouse.move(box['x'] + box['width']*.45, box['y'] + box['height']*.5)
                page.mouse.down()
                page.mouse.move(box['x'] + box['width']*.7, box['y'] + box['height']*.6, steps=8)
                page.mouse.up()
                rotated = pixels()
                assert rotated != wire, 'Pointer drag did not rotate actual model'
                page.mouse.wheel(0, -160)
                assert pixels() != rotated, 'Wheel did not zoom actual model'
                if page.locator('[data-role=initial]').is_enabled():
                    page.locator('[data-role=initial]').click()
                    page.wait_for_selector('#garment-preview[data-mode="initial"]')
                    assert '未物理仿真' in page.locator('[data-role=status]').inner_text()
                    page.locator('[data-role=final]').click()
                    page.wait_for_selector('#garment-preview[data-mode="final"]')
                status = page.locator('[data-role=status]').inner_text()
                page.screenshot(path=str(output / f'preview-{index}-desktop.png'), full_page=True)
                page.set_viewport_size({'width': 375, 'height': 812})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile overflow'
                page.screenshot(path=str(output / f'preview-{index}-mobile.png'), full_page=True)
                assert not errors, errors
                reports.append({'preview': str(path), 'verdict': 'PASS', 'status': status,
                    'checks': ['real WebGL canvas', 'wireframe pixels', 'pointer rotation pixels',
                               'wheel zoom pixels', 'initial/final where available', 'saved HTML bytes rendered offline',
                               '375px layout', 'no JS/console errors'],
                    'browser_routing': 'Browser plugin unavailable; ego-browser command missing on Linux; existing Playwright/Chromium used',
                    'native_file_url_navigation': 'BLOCKED_BY_ADMINISTRATOR; not bypassed or claimed verified',
                    'physical_fit': 'NOT_RUN'})
                context.close()
        finally:
            browser.close()
    (output / 'browser-report.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='append', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser', default='/usr/bin/chromium')
    args = parser.parse_args()
    verify(args.preview, args.output, args.browser)
