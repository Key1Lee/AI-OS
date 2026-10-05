import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import Ajv from 'ajv';
import { fileURLToPath } from 'node:url';

const directory = new URL('./', import.meta.url);
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
const requests = [];
const observed = { errors, externalRequests: requests, checks: [] };
page.on('pageerror', error => errors.push(error.message));
page.on('request', request => { if (!request.url().startsWith('http://127.0.0.1:8078') && !request.url().startsWith('blob:')) requests.push(request.url()); });
async function check(name, action) {
  try { await action(); observed.checks.push({ name, status: 'SUPPORTED' }); }
  catch (error) { observed.checks.push({ name, status: 'CONTRADICTED', error: error.message }); }
}
async function questionIsVisible(question) {
  const matches = await page.getByText(question, { exact: false }).all();
  for (const match of matches) if (await match.isVisible()) return true;
  return false;
}
try {
  await page.goto('http://127.0.0.1:8078/');
  await page.waitForLoadState('networkidle');
  await check('stage-first view hides full task graph', async () => {
    assert.equal(await page.getByLabel('Beginner pipeline overview').count(), 1);
    assert.equal(await page.getByLabel('Task dependency graph').count(), 0);
  });
  await check('all eight questions remain available in Backfill and Guide', async () => {
    for (const view of ['Backfill Lab', 'Learning guide']) {
      await page.getByRole('button', { name: view, exact: true }).click();
      for (const question of ['What runs?', 'When does it run?', 'What must finish first?', 'What happens if it fails?', 'Can it be retried?', 'Can it safely run twice?', 'How do I reprocess history?', 'What gets blocked downstream?']) assert.ok(await questionIsVisible(question), question);
    }
  });
  await page.getByRole('button', { name: 'Backfill Lab', exact: true }).click();
  await page.getByRole('button', { name: 'Run backfill', exact: true }).click();
  assert.match(await page.getByTestId('backfill-result').innerText(), /3 successful.*3 runs/);
  await page.screenshot({ path: fileURLToPath(new URL('independent-backfill.png', directory)), fullPage: true });
  const pending = page.waitForEvent('download');
  await page.getByRole('button', { name: /^Export (run|backfill) evidence$/ }).click();
  const download = await pending;
  const payload = JSON.parse(await readFile(await download.path(), 'utf8'));
  await writeFile(new URL('independent-backfill-export.json', directory), JSON.stringify(payload, null, 2));
  await check('active Backfill export includes the displayed historical runs and valid events', async () => {
    const found = [];
    function inspect(value) {
      if (!value || typeof value !== 'object') return;
      if (value.workflow_id && value.partition && value.tasks && value.events) found.push(value);
      for (const child of Object.values(value)) inspect(child);
    }
    inspect(payload);
    for (const partition of ['2026-09-27', '2026-09-28', '2026-09-29']) assert.ok(found.some(run => run.partition === partition && run.complete && run.clock_date === '2026-10-02'), `Export lacks completed displayed run for ${partition}; found ${found.map(run => `${run.partition}:${run.status}`).join(',')}`);
    const schema = JSON.parse(await readFile(new URL('../../contracts/execution-event.schema.json', import.meta.url), 'utf8'));
    const validate = new Ajv().compile(schema);
    for (const run of found) for (const event of run.events) assert.ok(validate(event), JSON.stringify(validate.errors));
    assert.equal(payload.source_workflow.tasks.length, 9);
    assert.deepEqual(payload.options, { workers: 2, partition_concurrency: 2 });
  });
  await check('accepted August partition is labeled with its actual calendar month', async () => {
    await page.getByLabel('Backfill start').fill('2026-08-01');
    await page.getByLabel('Backfill end').fill('2026-08-01');
    await page.getByRole('button', { name: 'Run backfill', exact: true }).click();
    const text = await page.getByTestId('partition-2026-08-01').innerText();
    observed.augustPartitionLabel = text;
    assert.match(text, /AUG/); assert.doesNotMatch(text, /OCT/);
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await check('narrow backfill controls and partition evidence fit without page overflow', async () => {
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, 'page overflow');
    assert.equal(await page.getByRole('button', { name: 'Run backfill', exact: true }).isVisible(), true, 'visible run control');
    assert.equal(await questionIsVisible('What runs?'), true, 'visible persistent question');
  });
  await page.screenshot({ path: fileURLToPath(new URL('independent-mobile-backfill.png', directory)), fullPage: true });
  await check('page runs without JS errors or external network resources', async () => { assert.deepEqual(errors, []); assert.deepEqual(requests, []); });
} finally {
  await writeFile(new URL('independent-browser-results.json', directory), JSON.stringify(observed, null, 2));
  await browser.close();
}
console.log(JSON.stringify(observed, null, 2));
if (observed.checks.some(check => check.status === 'CONTRADICTED')) process.exitCode = 1;
