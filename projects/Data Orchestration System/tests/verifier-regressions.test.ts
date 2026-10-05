import test from 'node:test';
import assert from 'node:assert/strict';
import { createRun, criticalPath, ecommerceWorkflow, planBackfill, scenarioContract, simulate, simulateBackfill, stepSimulation, TODAY, topologicalOrder, whyTask } from '../src/engine';
import type { OutputStore, WorkflowDefinition } from '../src/engine';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { Timeline } from '../src/ui/components';

function twoTasks(): WorkflowDefinition {
  const workflow = ecommerceWorkflow();
  workflow.tasks = workflow.tasks.slice(0, 2);
  workflow.tasks[0].id = 'A'; workflow.tasks[1].id = 'B';
  workflow.assets = workflow.assets.filter(a => ['source.orders', 'source.customers', 'raw_orders', 'raw_customers'].includes(a.id));
  workflow.assets.find(a => a.id === 'raw_orders')!.producer_task_id = 'A';
  workflow.assets.find(a => a.id === 'raw_customers')!.producer_task_id = 'B';
  return workflow;
}

test('verifier: malformed top-level/nested output stores fail at createRun', () => {
  const workflow = ecommerceWorkflow();
  for (const value of [7, [], null, 'rows', { mart_revenue: 7 }, { mart_revenue: null }, { mart_revenue: [] }, { mart_revenue: new Date() }]) {
    assert.throws(() => createRun(workflow, { partition: TODAY, initial_outputs: value as unknown as OutputStore }), /plain object/);
  }
});

test('verifier: a string dependency matching a valid single-character ID is rejected before execution', () => {
  const workflow = twoTasks(); workflow.tasks[1].dependencies = 'A' as unknown as string[];
  assert.throws(() => topologicalOrder(workflow), /Dependencies on B must be an array/);
  assert.throws(() => createRun(workflow, { partition: TODAY }), /Dependencies on B must be an array/);
});

test('verifier: explicit successful-partition replacement rejects an append workflow', () => {
  const plan = planBackfill('2026-09-30', '2026-09-30', TODAY, [{ partition: '2026-09-30', status: 'SUCCESS', rows: 100 }], 'replace');
  assert.throws(() => simulateBackfill(scenarioContract('unsafe-rerun').workflow, plan, { execution_id: 'verifier-unsafe' }), /requires replacement writes/);
  const safe = simulateBackfill(ecommerceWorkflow(), plan, { execution_id: 'verifier-safe' });
  assert.equal(safe.partitions[0].rows, 100);
});

test('verifier: retry delay guarantees eligibility, not start, when another task occupies the worker', () => {
  const workflow = twoTasks(), a = workflow.tasks[0], b = workflow.tasks[1];
  a.duration_minutes = 1; a.retry_policy.delay_minutes = 1; a.outcomes = [{ type: 'transient', message: 'Temporary failure' }, 'success'];
  b.duration_minutes = 10; b.timeout_minutes = 10;
  let run = createRun(workflow, { partition: TODAY, max_concurrency: 1 });
  run = stepSimulation(run, workflow); run = stepSimulation(run, workflow);
  assert.equal(run.now, 361); assert.equal(run.tasks.A.status, 'RETRYING'); assert.equal(run.tasks.B.status, 'RUNNING');
  const explanation = whyTask(run, workflow, 'A');
  assert.match(explanation.detail, /eligible at 06:02/); assert.match(explanation.detail, /free worker and resource slot/);
  const completed = simulate(workflow, { partition: TODAY, max_concurrency: 1 });
  assert.equal(completed.tasks.A.attempts[1].start_minute, 371);
  const timeline = renderToStaticMarkup(createElement(Timeline, { workflow, run: completed, onSelect: () => {} }));
  assert.match(timeline, /Between attempts: 1m retry delay \+ 9m waiting for capacity/);
  assert.match(timeline, /including retry delay and any wait for capacity/);
});

test('nested workflow shapes and null optional run values are never silently accepted', () => {
  for (const field of ['assets', 'pools', 'schedule'] as const) {
    const workflow = ecommerceWorkflow(); (workflow as unknown as Record<string, unknown>)[field] = 7;
    assert.throws(() => createRun(workflow, { partition: TODAY }));
  }
  for (const field of ['inputs', 'outputs', 'retry_policy', 'outcomes'] as const) {
    const workflow = ecommerceWorkflow(); (workflow.tasks[0] as unknown as Record<string, unknown>)[field] = 7;
    assert.throws(() => createRun(workflow, { partition: TODAY }));
  }
  for (const field of ['trigger', 'start_minute', 'clock_date', 'max_concurrency', 'run_id']) {
    assert.throws(() => createRun(ecommerceWorkflow(), { partition: TODAY, [field]: null }));
  }
});

test('verifier: coercible resource-pool arrays cannot bypass a shared pool limit', () => {
  const workflow = ecommerceWorkflow(); workflow.pools.api = 1;
  for (const task of workflow.tasks.filter(t => t.stage === 'ingest')) task.resource_pool = ['api'] as unknown as string;
  assert.throws(() => createRun(workflow, { partition: TODAY }), /safe, unique identifiers/);
});

test('partition failure injection works for a workflow without a mart task', () => {
  const workflow = twoTasks();
  const result = simulateBackfill(workflow, planBackfill('2026-09-27', '2026-09-29', TODAY, []), { execution_id: 'verifier-partition-fail', fail_partition: '2026-09-28' });
  assert.deepEqual(result.partitions.map(p => p.status), ['SUCCESS', 'FAILED', 'SUCCESS']);
});

test('verifier: critical path cannot use a skipped input as the successful side of an OR join', () => {
  const workflow = ecommerceWorkflow();
  workflow.tasks.find(t => t.id === 'stg_customers')!.enabled = false;
  workflow.tasks.find(t => t.id === 'int_orders')!.trigger_rule = 'one_success';
  workflow.pools = { api: 8, warehouse: 8, reporting: 8 };
  const run = simulate(workflow, { partition: TODAY, max_concurrency: 8 });
  assert.equal(run.status, 'SUCCESS'); assert.equal(run.now, 374);
  assert.equal(criticalPath(workflow).minutes, 14);
});

test('verifier: OR-join critical path excludes a transitively blocked parent', () => {
  const workflow = ecommerceWorkflow(), base = workflow.tasks[0];
  workflow.tasks = ['A', 'B', 'C', 'D'].map(id => ({ ...structuredClone(base), id, name: id, outputs: [id], inputs: [], dependencies: [], duration_minutes: 1 }));
  workflow.tasks[0].enabled = false;
  workflow.tasks[1].dependencies = ['A'];
  workflow.tasks[2].duration_minutes = 3;
  workflow.tasks[3].duration_minutes = 5; workflow.tasks[3].dependencies = ['B', 'C']; workflow.tasks[3].trigger_rule = 'one_success';
  workflow.assets = workflow.tasks.map(t => ({ id: t.id, name: t.id, producer_task_id: t.id })); workflow.asset_triggers = [];
  workflow.pools.api = 8;
  const run = simulate(workflow, { partition: TODAY, max_concurrency: 8 });
  assert.equal(run.tasks.B.status, 'BLOCKED'); assert.equal(run.tasks.D.attempts[0].start_minute, 363);
  assert.deepEqual(criticalPath(workflow), { tasks: ['C', 'D'], minutes: 8 }); assert.equal(run.now, 368);
});

test('verifier: an immediately skipped task never inherits its upstream runtime in the bound', () => {
  const workflow = ecommerceWorkflow(), base = workflow.tasks[0];
  workflow.tasks = ['A', 'B', 'C'].map(id => ({ ...structuredClone(base), id, name: id, outputs: [id], inputs: [], dependencies: [], duration_minutes: 1 }));
  workflow.tasks[0].duration_minutes = 10;
  workflow.tasks[1].enabled = false; workflow.tasks[1].dependencies = ['A'];
  workflow.tasks[2].dependencies = ['B']; workflow.tasks[2].trigger_rule = 'all_done';
  workflow.assets = workflow.tasks.map(t => ({ id: t.id, name: t.id, producer_task_id: t.id })); workflow.asset_triggers = [];
  workflow.pools.api = 8;
  const run = simulate(workflow, { partition: TODAY, max_concurrency: 8 });
  assert.equal(run.tasks.C.attempts[0].start_minute, 360);
  assert.deepEqual(criticalPath(workflow), { tasks: ['A'], minutes: 10 }); assert.equal(run.now, 370);
});
