import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import { mkdirSync, readFileSync } from 'node:fs';
import Ajv from 'ajv';
import { executionEventSchema, scenarioSchema } from '../src/engine';

const validateEvent = new Ajv().compile(executionEventSchema), validateScenario = new Ajv().compile(scenarioSchema);
mkdirSync('docs/screenshots', { recursive: true });
async function finish(page: Page) {
  await page.getByRole('button', { name: 'Run simulation', exact: true }).click();
  await expect(page.getByText('Workflow complete', { exact: true })).toBeVisible({ timeout: 15000 });
}
async function download(page: Page, label: string) {
  const pending = page.waitForEvent('download'); await page.getByRole('button', { name: label, exact: true }).click();
  const result = await pending, path = await result.path();
  return JSON.parse(readFileSync(path!, 'utf8'));
}

test('stage-first success journey, task/asset inspection, timeline and valid evidence exports', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  await expect(page.getByLabel('Beginner pipeline overview')).toBeVisible();
  await expect(page.getByLabel('Task dependency graph')).toHaveCount(0);
  await expect(page.getByText('Scheduled for 06:00 · not yet eligible', { exact: true })).toBeVisible();
  await page.screenshot({ path: 'docs/screenshots/beginner-overview.png', fullPage: true });
  await finish(page); await expect(page.getByTestId('virtual-clock')).toHaveText('06:14');
  await page.getByRole('button', { name: 'Reveal 9 tasks' }).click();
  await page.getByTestId('task-int_orders').click();
  const inspector = page.getByTestId('task-inspector'); await expect(inspector.getByRole('heading', { name: 'int_orders', exact: true })).toBeVisible();
  await expect(inspector.getByText('Completed successfully', { exact: true })).toBeVisible();
  await expect(inspector.getByText('stg_customers', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Assets', exact: true }).click();
  await expect(page.getByTestId('task-fct_orders')).toContainText('created by fct_orders');
  await page.getByRole('button', { name: 'Tasks', exact: true }).click();
  await page.screenshot({ path: 'docs/screenshots/task-graph.png', fullPage: true });
  await page.getByRole('button', { name: 'Execution timeline', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Every attempt has a place.' })).toBeVisible();
  await expect(page.getByText('Dependency critical path · 14 min', { exact: true })).toBeVisible();
  await page.screenshot({ path: 'docs/screenshots/timeline.png', fullPage: true });
  await page.getByRole('button', { name: 'Advanced', exact: true }).click();
  const events = await download(page, 'Export execution events'); expect(events.length).toBeGreaterThan(20);
  for (const event of events) expect(validateEvent(event), JSON.stringify(validateEvent.errors)).toBe(true);
  const scenario = await download(page, 'Export scenario contract'); expect(validateScenario(scenario)).toBe(true);
  const evidence = await download(page, 'Export run evidence'); expect(evidence.run.tasks.dashboard.status).toBe('SUCCESS');
  expect(errors).toEqual([]);
});

test('failure is different from downstream blocking and configuration repair produces success', async ({ page }) => {
  await page.goto('/'); await page.getByLabel('Learning scenario').selectOption('customer-failure');
  await page.getByRole('button', { name: 'Run simulation', exact: true }).click();
  await expect(page.getByText('Workflow ended with a failure', { exact: true })).toBeVisible({ timeout: 15000 });
  await page.getByRole('button', { name: 'Reveal 9 tasks' }).click();
  await expect(page.getByTestId('task-extract_customers')).toContainText('FAILED');
  await expect(page.getByTestId('task-quality_check')).toContainText('SUCCESS');
  await expect(page.getByTestId('task-dashboard')).toContainText('BLOCKED');
  await page.getByTestId('task-int_orders').click();
  await expect(page.getByTestId('task-inspector')).toContainText('never started; it did not fail itself');
  await page.screenshot({ path: 'docs/screenshots/failure-propagation.png', fullPage: true });
  await page.getByRole('button', { name: 'Fix configuration & rerun' }).click();
  await expect(page.getByText('Workflow complete', { exact: true })).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId('task-dashboard')).toContainText('SUCCESS');
});

test('transient retry explains failed attempt, exact wait and later success', async ({ page }) => {
  await page.goto('/'); await page.getByLabel('Learning scenario').selectOption('transient'); await finish(page);
  await expect(page.getByTestId('virtual-clock')).toHaveText('06:23');
  const inspector = page.getByTestId('task-inspector');
  await expect(inspector).toContainText('Attempt 1 · FAILED'); await expect(inspector).toContainText('Attempt 2 · SUCCESS');
  await page.getByRole('button', { name: 'Advanced', exact: true }).click();
  const events = await download(page, 'Export execution events');
  const starts = events.filter((e: { task_id: string; status: string }) => e.task_id === 'extract_orders' && e.status === 'RUNNING');
  expect(starts.map((e: { occurred_at: string }) => e.occurred_at.slice(11, 16))).toEqual(['06:00', '06:09']);
});

test('same-input rerun compares safe replacement with duplicate accumulation', async ({ page }) => {
  for (const [scenario, count] of [['healthy', '100rows'], ['unsafe-rerun', '200rows']]) {
    await page.goto('/'); await page.getByLabel('Learning scenario').selectOption(scenario); await finish(page);
    await expect(page.getByTestId('first-row-count')).toHaveText('100rows');
    await page.getByRole('button', { name: 'Rerun same inputs' }).click();
    await expect(page.getByTestId('latest-row-count')).toHaveText(count, { timeout: 15000 });
  }
});

test('manual/data triggers are immediate and single worker reveals ready capacity waits', async ({ page }) => {
  await page.goto('/'); await page.getByLabel('Available workers').selectOption('1');
  await page.getByRole('button', { name: 'Step', exact: true }).click();
  await expect(page.getByTestId('virtual-clock')).toHaveText('06:00');
  await page.getByRole('button', { name: 'Reveal 9 tasks' }).click();
  await expect(page.getByTestId('task-extract_customers')).toContainText('READY');
  await page.getByTestId('task-extract_customers').click(); await expect(page.getByTestId('task-inspector')).toContainText('waiting for capacity');
  await page.getByLabel('Workflow trigger').selectOption('manual'); await page.getByRole('button', { name: 'Step', exact: true }).click();
  await expect(page.getByTestId('virtual-clock')).toHaveText('05:55');
  await page.getByLabel('Workflow trigger').selectOption('asset'); await page.getByRole('button', { name: 'Step', exact: true }).click();
  await expect(page.getByTestId('virtual-clock')).toHaveText('05:55');
});

test('backfill range, isolation, replay of failed date and explicit successful reprocessing', async ({ page }, testInfo) => {
  await page.goto('/'); await page.getByRole('button', { name: 'Backfill Lab', exact: true }).click();
  await expect(page.getByTestId('partition-2026-09-28')).toContainText('MISSING');
  await page.getByLabel('Fail Sep 28 only').check(); await page.getByRole('button', { name: 'Run backfill', exact: true }).click();
  await expect(page.getByTestId('partition-2026-09-27')).toContainText('SUCCESS');
  await expect(page.getByTestId('partition-2026-09-28')).toContainText('FAILED');
  await expect(page.getByTestId('partition-2026-09-29')).toContainText('SUCCESS');
  await expect(page.getByTestId('backfill-result')).toContainText('2 successful · 1 failed · 3 runs');
  const evidence = await download(page, 'Export backfill evidence');
  expect(evidence.contract_version).toBe('orchestration-backfill-session-v1');
  expect(evidence.plan.items.map((i: { partition: string }) => i.partition)).toEqual(['2026-09-27', '2026-09-28', '2026-09-29']);
  expect(evidence.runs).toHaveLength(3); expect(evidence.options.fail_partition).toBe('2026-09-28');
  expect(evidence.options.execution_id).toMatch(/^[0-9a-f-]{36}$/);
  expect(await download(page, 'Export backfill evidence')).toEqual(evidence);
  for (const run of evidence.runs) for (const event of run.events) expect(validateEvent(event)).toBe(true);
  await expect(page.getByText('Historical data date, today’s execution time.', { exact: false })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('backfill-partition-failure.png'), fullPage: true });
  await page.getByLabel('Fail Sep 28 only').uncheck(); await page.getByRole('button', { name: 'Run backfill', exact: true }).click();
  await expect(page.getByTestId('backfill-result')).toContainText('3 successful · 0 failed · 1 runs');
  const replay = await download(page, 'Export backfill evidence');
  expect(replay.options.execution_id).not.toBe(evidence.options.execution_id);
  const earlierIds = new Set(evidence.runs.flatMap((run: { events: { event_id: string }[] }) => run.events.map(event => event.event_id)));
  expect(replay.runs.flatMap((run: { events: { event_id: string }[] }) => run.events).every((event: { event_id: string }) => !earlierIds.has(event.event_id))).toBe(true);
  for (const run of replay.runs) for (const event of run.events) expect(validateEvent(event)).toBe(true);
  await page.getByLabel('Backfill end').fill('2026-10-01');
  await page.getByRole('button', { name: 'Run backfill', exact: true }).click();
  await expect(page.getByTestId('backfill-result')).toContainText('0 runs');
  await page.getByLabel('Existing partition policy').selectOption('replace');
  await page.getByRole('button', { name: 'Run backfill', exact: true }).click();
  await expect(page.getByTestId('backfill-result')).toContainText('5 runs');
  await expect(page.getByTestId('partition-2026-09-28')).toContainText('100 published rows');
  await page.getByRole('button', { name: 'Reset partitions', exact: true }).click();
  await page.getByRole('button', { name: 'Run backfill', exact: true }).click();
  const reset = await download(page, 'Export backfill evidence');
  expect(reset.options.execution_id).not.toBe(replay.options.execution_id);
  await page.reload(); await page.getByRole('button', { name: 'Backfill Lab', exact: true }).click();
  await page.getByRole('button', { name: 'Run backfill', exact: true }).click();
  const reloaded = await download(page, 'Export backfill evidence');
  expect(new Set([evidence.options.execution_id, replay.options.execution_id, reset.options.execution_id, reloaded.options.execution_id]).size).toBe(4);
  await page.getByLabel('Backfill start').fill('2026-10-01'); await page.getByLabel('Backfill end').fill('2026-09-27');
  await expect(page.getByRole('alert')).toContainText('start must be');
});

test('historical dates show their real month and year and export the displayed backfill', async ({ page }) => {
  await page.goto('/'); await page.getByRole('button', { name: 'Backfill Lab', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Export backfill evidence' })).toBeDisabled();
  await page.getByLabel('Backfill start').fill('2025-08-01'); await page.getByLabel('Backfill end').fill('2025-08-01');
  await page.getByRole('button', { name: 'Run backfill', exact: true }).click();
  await expect(page.getByTestId('partition-2025-08-01')).toContainText('AUG 2025');
  const evidence = await download(page, 'Export backfill evidence');
  expect(evidence.runs).toHaveLength(1); expect(evidence.runs[0].partition).toBe('2025-08-01');
  expect(evidence.runs[0].clock_date).toBe('2026-10-02'); expect(evidence.source_workflow.id).toBe('daily-ecommerce');
});

test('a long branch lengthens the critical path while evidence remains visible on narrow screens', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await page.goto('/');
  await page.getByLabel('Learning scenario').selectOption('long-branch'); await finish(page);
  await expect(page.getByTestId('virtual-clock')).toHaveText('06:19');
  await page.getByRole('button', { name: 'Tasks', exact: true }).click();
  await page.getByTestId('task-stg_customers').click(); await expect(page.getByTestId('task-inspector')).toContainText('stg_customers');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: 'docs/screenshots/mobile-task-details.png', fullPage: true });
  await page.getByRole('button', { name: 'Backfill Lab', exact: true }).click();
  await page.getByRole('button', { name: 'Run backfill', exact: true }).click();
  await expect(page.getByTestId('backfill-result')).toContainText('3 successful');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: 'docs/screenshots/mobile-backfill.png', fullPage: true });
});

test('loaded simulator executes offline and needs no external network resources', async ({ page, context }) => {
  const external: string[] = [];
  page.on('request', request => { if (!request.url().startsWith('http://127.0.0.1:8079') && !request.url().startsWith('blob:')) external.push(request.url()); });
  await page.goto('/'); await page.waitForLoadState('networkidle'); await context.setOffline(true);
  await finish(page); await expect(page.getByTestId('virtual-clock')).toHaveText('06:14');
  expect(external).toEqual([]);
});
