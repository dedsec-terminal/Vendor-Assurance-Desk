const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const packagePath = process.env.PLAYWRIGHT_MODULE || 'playwright';
const { chromium } = require(packagePath);

(async () => {
  const browser = await chromium.launch({headless: true});
  const page = await browser.newPage({viewport: {width: 1440, height: 1050}, deviceScaleFactor: 1});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {if (message.type() === 'error') errors.push(message.text());});
  const base = process.env.LAB_URL || 'http://127.0.0.1:8765';
  await page.goto(base);
  await page.waitForFunction(() => document.querySelector('#load-status').textContent.includes('Loaded') || document.querySelector('#metric-retest').textContent.trim() === '2/2');
  assert.equal(await page.locator('#metric-open-gaps').innerText(), '3');
  assert.equal(await page.locator('#metric-retest').innerText(), '2/2');
  assert.match(await page.locator('#overview-approval').innerText(), /pending/i);
  const output = path.resolve(__dirname, '../output');
  await page.screenshot({path: path.join(output, 'dashboard_desktop.png'), fullPage: true});
  for (const name of ['evidence', 'controls', 'findings', 'decision', 'results']) {
    await page.locator(`button[data-view="${name}"]`).click();
    assert.equal(await page.locator(`#view-${name}`).isVisible(), true);
  }
  await page.screenshot({path: path.join(output, 'results_desktop.png'), fullPage: true});
  await page.locator('button[data-view="controls"]').click();
  assert.match(await page.locator('#view-controls').innerText(), /NIST CSF 2.0/);
  assert.match(await page.locator('#view-controls').innerText(), /ISO/);
  await page.screenshot({path:path.join(output,'controls_desktop.png'),fullPage:true});
  await page.locator('button[data-view="findings"]').click();
  const retest = page.locator('#view-findings button').filter({hasText: /retest/i}).first();
  await retest.click();
  assert.match(await page.locator('#finding-board').innerText(), /Ready for review/);
  assert.match(await page.locator('#finding-board').innerText(), /Open/);
  await page.locator('#presentation-toggle').click();
  assert.equal(await page.locator('#presentation-toggle').getAttribute('aria-pressed'), 'true');
  await page.locator('#presentation-toggle').click();
  await page.setViewportSize({width: 390, height: 844});
  await page.locator('button[data-view="overview"]').click();
  await page.screenshot({path: path.join(output, 'dashboard_mobile.png'), fullPage: true});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true, 'Mobile horizontal overflow');
  for (const route of ['/output/assessment.json', '/output/results.json', '/output/risk_register.csv', '/output/decision_memo.md']) {
    const response = await page.request.get(base + route);
    assert.equal(response.status(), 200, route);
  }
  assert.equal((await page.request.get(base + '/case-study/data.json')).status(), 404);
  assert.equal((await page.request.get(base + '/platform/.local/credentials.json')).status(), 404);
  assert.deepEqual(errors, []);
  fs.writeFileSync(path.join(output, 'browser_validation.json'), JSON.stringify({passed:true, views:6, responsive:true, console_errors:errors, downloads:4, private_paths_denied:2}, null, 2));
  await browser.close();
  console.log('Browser checks passed: 6 views, mobile layout, retest statuses, downloads and private-path isolation.');
})().catch(error => {console.error(error); process.exit(1);});
