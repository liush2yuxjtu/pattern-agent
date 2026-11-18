const fs = require('fs'), path = require('path');

exports.verifyFeedback = async function(page, {manifest, base, url, out, check}) {
  await page.locator('#pr-after').click();
  await page.waitForFunction(() => document.querySelector('#pr-feedback-version').textContent.includes('当前候选'));
  const expectations = manifest.grades.final.expectations;
  check('Actual grader assertions and their evidence are shown, not a synthetic score',
    await page.locator('#pr-expectations>li').count() === expectations.length &&
    (await page.locator('#pr-expectations>li').allTextContents()).every((text, i) => text.includes(expectations[i].evidence)));
  check('Grader self-critique is available', await page.locator('#pr-eval-critique>li').count() === manifest.grades.final.eval_feedback.suggestions.length);
  check('New candidate is not silently human accepted', await page.locator('#pr-human-acceptance').inputValue() === 'not_reviewed');
  const firstExport = page.waitForEvent('download'); await page.locator('#pr-export-feedback').click();
  const draftPath = path.join(out, 'draft-feedback.json'); await (await firstExport).saveAs(draftPath);
  check('Empty feedback export remains an unfinished review', JSON.parse(fs.readFileSync(draftPath)).status === 'in_progress');
  const beforeText = '自动化测试：基线反馈，不代表人工验收。';
  const modelText = '自动化测试：仍需修正握衣动作 <img src=x>，不代表人工验收。';
  await page.locator('#pr-before').click(); await page.locator('#pr-human-feedback').fill(beforeText);
  await page.locator('#pr-after').click();
  check('Before feedback cannot leak into candidate feedback', await page.locator('#pr-human-feedback').inputValue() === '');
  await page.locator('#pr-human-feedback').fill(modelText);
  await page.locator('#pr-human-acceptance').selectOption('accepted');
  check('Explicit human acceptance never rewrites the independent failure grade', (await page.locator('#pr-assertion-version').innerText()).includes(manifest.grades.final.overall_verdict));
  await page.locator('#pr-human-acceptance').selectOption('needs_changes');
  await page.reload({waitUntil:'networkidle'});
  await page.waitForFunction(value => document.querySelector('#pr-human-feedback')?.value === value, modelText);
  check('Candidate text and explicit decision survive real reload', await page.locator('#pr-human-acceptance').inputValue() === 'needs_changes');
  check('Review text is text, not injected markup', await page.locator('#pr-human-review img').count() === 0);
  const exportWait = page.waitForEvent('download'); await page.locator('#pr-export-feedback').click();
  const file = path.join(out, 'feedback.json'); await (await exportWait).saveAs(file);
  const saved = JSON.parse(fs.readFileSync(file)); const latest = saved.reviews.find(r => r.version === 'model');
  const previous = saved.reviews.find(r => r.version === 'baseline');
  check('Downloaded feedback uses creator review fields with separate original/candidate records',
    saved.status === 'complete' && latest.feedback === modelText && previous.feedback === beforeText &&
    saved.reviews.every(r => typeof r.run_id === 'string' && Number.isFinite(Date.parse(r.timestamp))));
  check('Human feedback binds exact original, state, mesh and camera',
    latest.source_fingerprints.reference_sha256 === manifest.files['reference/original-product.jpg'] &&
    latest.source_fingerprints.state_sha256 === manifest.files['model/final-state.json'] &&
    latest.source_fingerprints.posed_obj_sha256 === manifest.files['model/posed.obj'] &&
    latest.source_fingerprints.camera_sha256 === manifest.files['model/camera.json']);
  check('Human review does not overwrite independent automatic FAIL',
    (await page.locator('#pr-assertion-version').innerText()).includes(manifest.grades.final.overall_verdict));
  await page.locator('#pr-human-review').scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(out,'human-review.png')});

  const changed = structuredClone(manifest); changed.files['model/final-state.json'] = 'a'.repeat(64);
  const isolated = await page.context().newPage();
  try {
    await isolated.route(new URL('manifest.json',base).href,r => r.fulfill({json:changed}));
    await isolated.goto(url,{waitUntil:'networkidle'});
    await isolated.waitForFunction(() => document.querySelector('#pr-feedback-version')?.textContent.includes('aaaaaaaaaaaa'));
    check('Deliberately changed model fingerprint cannot inherit previous human acceptance',
      await isolated.locator('#pr-human-feedback').inputValue() === '' && await isolated.locator('#pr-human-acceptance').inputValue() === 'not_reviewed');
  } finally {await isolated.close();}

  const key = 'pattern-agent:human-review:v1:' + latest.run_id;
  const stored = await page.evaluate(key => localStorage.getItem(key),key);
  await page.evaluate(key => localStorage.setItem(key,'broken-json'),key);
  await page.reload({waitUntil:'networkidle'});
  await page.waitForFunction(() => document.querySelector('#pr-feedback-version')?.textContent.includes('当前候选'));
  check('Corrupt stored feedback safely becomes unreviewed', await page.locator('#pr-human-feedback').inputValue() === '' && await page.locator('#pr-human-acceptance').inputValue() === 'not_reviewed');
  await page.evaluate(({key,stored})=>localStorage.setItem(key,stored),{key,stored});
  await page.reload({waitUntil:'networkidle'});
  await page.waitForFunction(value => document.querySelector('#pr-human-feedback')?.value === value,modelText);
};
