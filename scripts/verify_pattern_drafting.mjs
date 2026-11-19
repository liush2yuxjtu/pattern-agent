import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, sep } from 'node:path';
import { pathToFileURL } from 'node:url';

const modulePath = process.env.PLAYWRIGHT_MODULE;
const { chromium } = await import(modulePath ? pathToFileURL(resolve(modulePath)).href : 'playwright-core');
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH,
  headless: true,
});
const web = resolve('web');
const prefix = '/pattern-agent/';
const server = process.argv[2] ? null : createServer(async (request, response) => {
  const pathname = new URL(request.url, 'http://localhost').pathname;
  if (!pathname.startsWith(prefix)) {
    response.writeHead(404).end();
    return;
  }
  const relative = pathname.slice(prefix.length) + (pathname.endsWith('/') ? 'index.html' : '');
  const file = resolve(web, relative);
  if (!file.startsWith(web + sep)) {
    response.writeHead(404).end();
    return;
  }
  try {
    const content = await readFile(file);
    response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' }).end(content);
  } catch {
    response.writeHead(404).end();
  }
});
if (server) await new Promise(ok => server.listen(0, '127.0.0.1', ok));
const base = process.argv[2] || `http://127.0.0.1:${server.address().port}${prefix}`;
const route = new URL('pattern-drafting/', base).href;

try {
  const page = await browser.newPage({ viewport: { width: 1250, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(base);
  await page.getByRole('navigation', { name: '主导航' }).getByRole('link', { name: '从白纸画纸样' }).click();
  assert.equal(page.url(), route);
  await page.getByRole('link', { name: '八款女式上衣逐笔工作台' }).click();
  const styles = page.locator('.work-styles label');
  assert.equal(await styles.count(), 8);
  const expected = [35, 35, 35, 35, 38, 39, 41, 38];
  for (const [i, count] of expected.entries()) {
    await styles.nth(i).click();
    const panel = page.locator('.work-panel:visible');
    assert.equal(await panel.locator('svg .work-layer').count(), count);
    const ink = () => panel.locator('.work-layer').evaluateAll(layers =>
      layers.filter(layer => getComputedStyle(layer).opacity === '1').length);
    assert.equal(await ink(), 0);
    const target = panel.locator('.work-pin:visible');
    for (let n = 1; n <= count; n++) {
      await target.click();
      assert.equal(await ink(), n);
    }
    assert.equal(await panel.getByRole('heading', { name: '纸样完成' }).isVisible(), true);
    await panel.locator('.work-state:visible .work-actions').getByText('撤回一笔').click();
    assert.equal(await ink(), count - 1);
    await target.click();
    await panel.getByText('清空本款').click();
    assert.equal(await ink(), 0);
  }
  await page.goto(new URL('womens-tops-pattern-workshop.html#shirt/slim/9', route).href);
  assert.equal(await page.getByRole('heading', { name: '二维纸样总览', exact: true }).isVisible(), true);
  assert.ok((await page.locator('[data-art] svg').textContent()).includes('袖衩包条'));
  await page.getByRole('button', { name: '算尺寸', exact: true }).click();
  assert.ok(page.url().endsWith('#shirt/slim/3'));
  await page.reload();
  assert.equal(await page.getByRole('heading', { name: '算尺寸', exact: true }).isVisible(), true);
  await page.setViewportSize({ width: 320, height: 840 });
  await page.goto(new URL('skirt-pattern-complete.html', route).href);
  assert.equal(await page.locator('[data-progress]').textContent(), '1／19');
  await page.getByRole('button', { name: '5 改成新款' }).click();
  await page.getByRole('button', { name: '转省放摆', exact: true }).click();
  const wing = await page.locator('[data-wing]').getAttribute('transform');
  assert.ok(wing.startsWith('rotate(-9.'));
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth === innerWidth));
  await page.goto(new URL('womens-tops-interactive-drafting.html', route).href);
  await page.locator('.work-pin:visible').click();
  assert.equal(await page.getByRole('heading', { name: '画中线', exact: true }).isVisible(), true);
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth === innerWidth));
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ verdict: 'PASS', base, styles: expected.length,
    draftingActions: expected.reduce((a, b) => a + b), undoAndReset: true,
    overviewAndDeepLink: true, skirtPivot: true, mobile: true, pageErrors: errors }));
} finally {
  await browser.close();
  if (server) server.close();
}
