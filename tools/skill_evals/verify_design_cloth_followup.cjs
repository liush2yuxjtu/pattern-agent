const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { readFile } = require('node:fs/promises');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright-core');

const root = path.resolve(__dirname, '../..');
const route = '/pattern-agent/design-cloth/';
const names = ['eval.html', 'boat-followup.html'];
const digest = body => createHash('sha256').update(body).digest('hex');

async function main() {
  const pages = new Map(await Promise.all(names.map(async name => [
    name, await readFile(path.join(root, 'web/design-cloth', name)),
  ])));
  const liveUrl = process.argv[2];
  const server = http.createServer((req, res) => {
    const body = req.url.startsWith(route) && pages.get(req.url.slice(route.length));
    if (!body) {
      res.writeHead(404).end();
      return;
    }
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }).end(body);
  });

  try {
    if (!liveUrl) {
      await new Promise((resolve, reject) => {
        server.once('error', reject);
        server.listen(0, '127.0.0.1', resolve);
      });
    }
    const base = liveUrl || `http://127.0.0.1:${server.address().port}${route}`;
    const browser = await chromium.launch({
      executablePath: process.env.PATTERN_EVAL_CHROME || undefined,
      headless: true,
    });
    try {
      const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      const original = await page.goto(new URL(names[0], base).href);
      assert.equal(original.status(), 200);
      assert.equal(digest(await original.body()), digest(pages.get(names[0])));

      const navigation = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/boat-followup.html'));
      await page.getByRole('link', { name: 'Boat CLO 3D 跟进评测 · 37、38' }).click();
      const followup = await navigation;
      assert.equal(followup.status(), 200);
      assert.equal(digest(await followup.body()), digest(pages.get(names[1])));

      const prompts = [];
      for (let index = 0; index < 4; index++) {
        assert.equal(await page.locator('#progress').innerText(), `${index + 1} of 4`);
        const prompt = await page.locator('#prompt-text').innerText();
        assert.match(prompt, /EOZ3024D6RYM|FUA2519L2MM/);
        prompts.push(prompt);
        assert.match(await page.locator('#outputs-body').innerText(), /Boat/);
        if (index < 3) await page.locator('#next-btn').click();
      }
      assert.equal(new Set(prompts).size, 2);
      await page.locator('#prev-btn').click();
      await page.locator('#grades-section .grades-toggle').click();
      assert.match(await page.locator('#grades-content').innerText(), /Boat 参数/);

      await page.getByRole('button', { name: 'Benchmark', exact: true }).click();
      assert.match(await page.locator('#benchmark-content').innerText(), /100%/);
      await page.setViewportSize({ width: 390, height: 844 });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), 390);
      const missing = await page.request.get(new URL('nonexistent-followup.html', base).href);
      assert.equal(missing.status(), 404);
      assert.deepEqual(errors, []);
      console.log(JSON.stringify({
        base, verdict: 'PASS', sha256: digest(pages.get(names[1])),
        runs: 4, distinctPrompts: 2, grades: true, benchmark: true, mobileWidth: 390, missing: 404,
      }));
    } finally {
      await browser.close();
    }
  } finally {
    if (server.listening) await new Promise(resolve => server.close(resolve));
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
