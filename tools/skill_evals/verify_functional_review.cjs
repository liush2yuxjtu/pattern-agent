// Drive the actual adapted Anthropic static viewer; no route mocks or API calls.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

function argumentsFromCLI() {
  const result = {};
  for (let i = 2; i < process.argv.length; i += 2) {
    const key = process.argv[i];
    if (!['--url', '--out', '--expected-runs'].includes(key) || !process.argv[i + 1]) throw Error('Use --url URL --out DIR [--expected-runs N]');
    result[key.slice(2)] = process.argv[i + 1];
  }
  if (!result.url || !result.out) throw Error('--url and --out required');
  if (result['expected-runs'] !== undefined && (!Number.isInteger(Number(result['expected-runs'])) || Number(result['expected-runs']) < 1)) throw Error('Invalid expected run count');
  return result;
}

(async () => {
  const args = argumentsFromCLI();
  const out = path.resolve(args.out);
  fs.mkdirSync(out, { recursive: true });
  let browser;
  const requests = [], errors = [], checks = [];
  function requireCheck(condition, detail) {
    checks.push({ detail, passed: Boolean(condition) });
    if (!condition) throw Error(detail);
  }
  try {
    browser = await chromium.launch({ executablePath: process.env.CHROMIUM_BIN || '/usr/bin/chromium', headless: true, args: ['--no-sandbox'] });
    const context = await browser.newContext({ viewport: { width: 1280, height: 920 }, acceptDownloads: true });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => requests.push({ method: request.method(), url: request.url() }));
    const response = await page.goto(args.url, { waitUntil: 'networkidle' });
    requireCheck(response.status() === 200, 'Actual review URL responds HTTP 200');
    await page.locator('#progress').waitFor();
    const progress = await page.locator('#progress').innerText();
    const match = progress.match(/^1 of (\d+)$/);
    requireCheck(Boolean(match), 'First actual run is displayed');
    const count = Number(match[1]);
    if (args['expected-runs']) requireCheck(count === Number(args['expected-runs']), 'Expected run count matches');
    requireCheck(await page.locator('#outputs-body .output-file').count() > 0, 'At least one real output is rendered');
    requireCheck((await page.locator('#config-badge').innerText()).match(/with skill|new skill/i) !== null, 'With-skill candidate precedes its baseline');
    await page.locator('#grades-section .grades-toggle').click();
    requireCheck(await page.locator('#grades-content').evaluate(element => element.classList.contains('open')), 'Formal grades disclosure opens');
    requireCheck(await page.locator('#grades-content .assertion-item').count() > 0, 'Formal assertion evidence is rendered');
    await page.screenshot({ path: path.join(out, 'desktop.png'), fullPage: false });
    const feedback = 'Browser verification fixture — local feedback persists; not a human acceptance decision.';
    await page.locator('#feedback').fill(feedback);
    await page.locator('#feedback-status').filter({ hasText: 'Saved in this browser' }).waitFor();
    await page.reload({ waitUntil: 'networkidle' });
    requireCheck(await page.locator('#feedback').inputValue() === feedback, 'Feedback survives a real page reload');
    if (count > 1) {
      await page.locator('#next-btn').click();
      requireCheck(await page.locator('#progress').innerText() === `2 of ${count}`, 'Next navigates to another output');
      await page.locator('#prev-btn').click();
      requireCheck(await page.locator('#feedback').inputValue() === feedback, 'Feedback survives run navigation');
    }
    await page.locator('[onclick="switchView(\'benchmark\')"]').click();
    requireCheck(await page.locator('#panel-benchmark').evaluate(element => element.classList.contains('active')), 'Benchmark tab opens');
    requireCheck(await page.locator('#benchmark-content').innerText().then(text => text.includes('Benchmark Results')), 'Quantitative benchmark renders');
    await page.screenshot({ path: path.join(out, 'benchmark.png'), fullPage: false });
    await page.locator('[onclick="switchView(\'outputs\')"]').click();
    const downloading = page.waitForEvent('download');
    await page.locator('#done-btn').click();
    const download = await downloading;
    requireCheck(download.suggestedFilename() === 'feedback.json', 'Submit starts a real feedback.json download');
    const feedbackPath = path.join(out, 'feedback-fixture.json');
    await download.saveAs(feedbackPath);
    const saved = JSON.parse(fs.readFileSync(feedbackPath, 'utf8'));
    requireCheck(saved.status === 'complete' && saved.reviews.length === count && saved.reviews[0].feedback === feedback, 'Downloaded feedback reopens with every run and entered text');
    await page.locator('#done-overlay button').click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(out, 'mobile.png'), fullPage: false });
    requireCheck(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Mobile document has no horizontal overflow');
    requireCheck(requests.every(request => request.method === 'GET' && !new URL(request.url).pathname.includes('/api/')), 'No POST or feedback API request was sent');
    requireCheck(errors.length === 0, 'No page JavaScript errors');
    const report = { verdict: 'PASS', scope: 'actual static review UI and downloaded feedback; fixture feedback is not human approval', url: args.url, runs: count, checks, requests, page_errors: errors };
    fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify({ verdict: report.verdict, runs: count, checks: checks.length, output: out }));
  } catch (error) {
    fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify({ verdict: 'FAIL', error: String(error), checks, requests, page_errors: errors }, null, 2));
    throw error;
  } finally {
    if (browser) await browser.close();
  }
})();
