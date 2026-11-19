"""Compare cold readiness and long tasks during real Run drape playback."""
import argparse
import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from browser_launch import chromium_args


def percentile(values, ratio):
    values = sorted(values)
    return values[min(len(values) - 1, int(len(values) * ratio))] if values else 0


def sample(browser, url, screenshot):
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    try:
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
        page.add_init_script('''window.tasks=[];
            new PerformanceObserver(list=>{
                for(const e of list.getEntries()) tasks.push([e.startTime,e.duration]);
            }).observe({type:'longtask',buffered:true});''')
        response = page.goto(url, wait_until='commit')
        page.wait_for_function('window.clothLab?.ready', timeout=90000)
        ready_ms = page.evaluate('performance.now()')
        page.locator('#back').click()
        page.evaluate('clothLab.gpuComplete()')
        page.screenshot(path=str(screenshot))
        start_steps = page.evaluate('clothLab.stats().steps')
        page.locator('#run').click()
        start_ms = page.evaluate('performance.now()')
        page.wait_for_function(
            'target=>clothLab.stats().steps>=target',
            arg=start_steps + 24, polling=100, timeout=30000,
        )
        page.locator('#run').click()
        end_ms, steps = page.evaluate('[performance.now(),clothLab.stats().steps]')
        page.wait_for_timeout(150)
        tasks = page.evaluate('tasks')
        active = [duration for start, duration in tasks if start_ms <= start <= end_ms]
        return {
            'url': url, 'sha256': hashlib.sha256(response.body()).hexdigest(),
            'ready_ms': ready_ms, 'playback_ms': end_ms - start_ms,
            'steps': steps - start_steps, 'long_task_p95_ms': percentile(active, .95),
            'longest_task_ms': max(active, default=0), 'long_tasks': tasks,
            'backend': page.evaluate('clothLab.renderBackend()'), 'errors': errors,
            'paused': page.locator('#run').inner_text() == 'Run drape',
            'covered': page.evaluate('clothLab.coverageCheck().verdict') == 'PASS',
        }
    finally:
        page.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        with pw.chromium.launch(executable_path='/usr/bin/chromium', args=chromium_args()) as browser:
            before = sample(browser, args.baseline, args.output / 'before.png')
        with pw.chromium.launch(executable_path='/usr/bin/chromium', args=chromium_args()) as browser:
            after = sample(browser, args.url, args.output / 'after.png')
            page = browser.new_page()
            page.goto(args.url, wait_until='commit')
            page.wait_for_function('window.clothLab?.ready', timeout=90000)
            exact = page.evaluate('''()=>{
                const extract=()=>{
                    const q=clothLab.project();
                    return JSON.stringify([q.positions,q.previous,q.inverseMass,
                        q.contactPressure, q.support.normalCorrection_m,
                        q.support.frictionCorrection_m,q.support.stepStart_m,
                        q.support.previousAtStart_m,q.simulation.steps]);
                };
                const boot=extract();
                clothLab.reset();
                clothLab.step(120);
                return extract()===boot;
            }''')
    checks = {
        'first_drape_at_least_twice_as_fast': after['ready_ms'] <= .5 * before['ready_ms'],
        'playback_long_tasks_at_least_halved': after['long_task_p95_ms'] <= .5 * before['long_task_p95_ms'],
        'playback_completes_and_pauses': after['steps'] >= 24 and after['paused'],
        'default_checkpoint_matches_fresh_simulation': exact,
        'coverage_and_console': after['covered'] and not after['errors'],
    }
    data = {'verdict': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks, 'before': before, 'after': after}
    (args.output / 'receipt.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({**checks, 'verdict': data['verdict']}, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == '__main__':
    raise SystemExit(main())
