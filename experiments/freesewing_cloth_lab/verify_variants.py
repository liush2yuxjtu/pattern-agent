"""Drive an edited upstream pattern and physically simulate the resulting mesh."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from independent import run as audit

ROOT = Path(__file__).resolve().parents[2]


def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    result = {'url': args.url, 'checks': {}, 'errors': []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox', '--enable-unsafe-swiftshader'])
        page = browser.new_page(viewport={'width': 1440, 'height': 1150})
        page.on('pageerror', lambda error: result['errors'].append(str(error)))
        response = page.goto(args.url, wait_until='networkidle')
        result['htmlSHA256'] = hashlib.sha256(response.body()).hexdigest()
        page.wait_for_function('window.clothLab?.ready')
        baseline = page.evaluate('clothLab.project().materialCoordinates')
        page.get_by_label('Skirt length in millimetres', exact=True).focus()
        page.keyboard.press('End')
        page.get_by_label('FreeSewing circle ratio percent', exact=True).focus()
        page.keyboard.press('End')
        page.get_by_label('Material assumption').select_option('linen')
        profile = page.evaluate('clothLab.project().freesewing')
        result['checks']['realEditedPattern'] = profile['length_mm'] == 650 and profile['settings']['options']['circleRatio'] == .6
        result['checks']['materialCoordinatesChange'] = page.evaluate('clothLab.project().materialCoordinates') != baseline
        page.evaluate('clothLab.step(120)')
        own = page.evaluate('clothLab.verify()')
        state = page.evaluate('clothLab.project()')
        with gzip.open(args.output / 'edited-state.json.gz', 'wt') as file:
            json.dump(state, file)
        result['independent'] = audit(state, ROOT, negative=False)
        result['checks']['editedPhysicalState'] = own['verdict'] == result['independent']['verdict'] == 'PASS'
        result['performance'] = state['simulation']
        page.screenshot(path=str(args.output / 'edited-fabric.png'), full_page=True)
        page.get_by_role('button', name='Fold · 折角', exact=True).click()
        page.screenshot(path=str(args.output / 'edited-fold.png'), full_page=True)
        result['checks']['consoleHealthy'] = not result['errors']
        browser.close()
    result['verdict'] = 'PASS' if all(result['checks'].values()) else 'FAIL'
    (args.output / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'verdict': result['verdict'], 'checks': result['checks'], 'bodyIntersections': result['independent']['body_triangle_intersections'], 'selfIntersections': result['independent']['cloth_self_intersections']}, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    result = run(parser.parse_args())
    raise SystemExit(0 if result['verdict'] == 'PASS' else 2)
