import test from 'node:test';
import assert from 'node:assert/strict';
import Ajv from 'ajv';
import { ecommerceWorkflow, executionEventSchema, EXAMPLE_PARTITIONS, planBackfill, simulateBackfill, TODAY } from '../src/engine';

test('Sep 27–29 produces exactly three historical runs today and preserves each partition key', () => {
  const workflow = ecommerceWorkflow(), plan = planBackfill('2026-09-27', '2026-09-29', TODAY, EXAMPLE_PARTITIONS);
  assert.deepEqual(plan.items.map(i => i.partition), ['2026-09-27', '2026-09-28', '2026-09-29']);
  const result = simulateBackfill(workflow, plan, { execution_id: 'fixture-stable' });
  assert.equal(result.runs.length, 3); assert.equal(result.partitions.length, 3);
  assert.ok(result.partitions.every(p => p.status === 'SUCCESS' && p.rows === 100));
  for (const run of result.runs) {
    assert.equal(run.clock_date, TODAY); assert.ok(run.events.every(e => e.partition === run.partition && e.occurred_at.startsWith(TODAY)));
    assert.equal(run.tasks.dashboard.status, 'SUCCESS');
  }
  assert.deepEqual(result, simulateBackfill(workflow, plan, { execution_id: 'fixture-stable' }), 'backfills must be deterministic');
});

test('one partition can fail without blocking neighboring dates; failed partitions remain replayable', () => {
  const workflow = ecommerceWorkflow(), plan = planBackfill('2026-09-27', '2026-09-29', TODAY, EXAMPLE_PARTITIONS);
  const result = simulateBackfill(workflow, plan, { execution_id: 'fixture-failed', fail_partition: '2026-09-28' });
  assert.deepEqual(result.partitions.map(p => p.status), ['SUCCESS', 'FAILED', 'SUCCESS']);
  const failed = result.runs.find(r => r.partition === '2026-09-28')!;
  assert.equal(failed.tasks.mart_revenue.status, 'FAILED'); assert.equal(failed.tasks.dashboard.status, 'BLOCKED');
  const retryPlan = planBackfill(plan.start, plan.end, TODAY, result.partitions);
  assert.deepEqual(retryPlan.items.map(i => i.action), ['SKIP', 'RUN', 'SKIP']);
  const original = structuredClone(result);
  const replay = simulateBackfill(workflow, retryPlan, { execution_id: 'fixture-replayed' });
  assert.equal(replay.partitions[1].status, 'SUCCESS');
  assert.equal(replay.runs[0].partition, failed.partition);
  assert.equal(replay.runs[0].workflow_id, failed.workflow_id);
  assert.notEqual(replay.runs[0].run_id, failed.run_id);
  const priorIds = new Set(result.runs.flatMap(run => run.events.map(event => event.event_id)));
  assert.ok(replay.runs.flatMap(run => run.events).every(event => !priorIds.has(event.event_id)));
  assert.deepEqual(result, original, 'replay must preserve the earlier history');
});

test('backfill identity is required and validated before the workflow is used', () => {
  const plan = planBackfill('2026-09-28', '2026-09-28', TODAY, []);
  let workflowReads = 0;
  const workflow = new Proxy(ecommerceWorkflow(), { get() { workflowReads++; throw new Error('workflow read before identity validation'); } });
  for (const options of [undefined, null, {}, { execution_id: undefined }, { execution_id: '' },
    { execution_id: ' ' }, { execution_id: 7 }, { execution_id: 'x'.repeat(161) }]) {
    assert.throws(() => Reflect.apply(simulateBackfill, undefined, [workflow, plan, options]), /Backfill (options|execution ID)/);
  }
  assert.equal(workflowReads, 0);
});

test('bounded backfill identities retain deterministic traces and valid event lengths', () => {
  const plan = planBackfill('2026-09-28', '2026-09-28', TODAY, []);
  const validate = new Ajv({ allErrors: true }).compile(executionEventSchema);
  for (const execution_id of ['x', 'x'.repeat(160)]) {
    const options = { execution_id }, workflow = ecommerceWorkflow();
    const result = simulateBackfill(workflow, plan, options);
    assert.equal(result.options.execution_id, execution_id);
    assert.equal(result.runs[0].run_id, `backfill:${execution_id}:2026-09-28`);
    assert.ok(result.runs[0].run_id.length <= 180);
    assert.deepEqual(result, simulateBackfill(workflow, plan, options));
    for (const event of result.runs[0].events) assert.equal(validate(event), true, JSON.stringify(validate.errors));
  }
});

test('automatic retries keep one partition execution identity and increment attempts', () => {
  const workflow = ecommerceWorkflow();
  const task = workflow.tasks[0];
  task.outcomes = [{ type: 'transient', message: 'synthetic retry' }, 'success'];
  task.retry_policy.max_attempts = 2;
  const result = simulateBackfill(workflow, planBackfill('2026-09-28', '2026-09-28', TODAY, []), { execution_id: 'automatic-retry' });
  assert.equal(result.runs.length, 1);
  const run = result.runs[0];
  assert.equal(run.status, 'SUCCESS');
  assert.deepEqual(run.tasks[task.id].attempts.map(attempt => attempt.attempt), [1, 2]);
  assert.ok(run.events.every(event => event.run_id === run.run_id));
});

test('successful partitions are kept by default and reprocessed only under explicit replacement policy', () => {
  const workflow = ecommerceWorkflow();
  const keep = planBackfill('2026-09-30', '2026-10-01', TODAY, EXAMPLE_PARTITIONS);
  assert.ok(keep.items.every(i => i.action === 'SKIP'));
  const skipped = simulateBackfill(workflow, keep, { execution_id: 'fixture-keep' });
  assert.equal(skipped.runs.length, 0); assert.equal(skipped.total_minutes, 0); assert.equal(skipped.peak_workers, 0);
  assert.ok(skipped.partitions.every(p => p.rows === 100));
  const replace = planBackfill('2026-09-30', '2026-10-01', TODAY, EXAMPLE_PARTITIONS, 'replace');
  const rerun = simulateBackfill(workflow, replace, { execution_id: 'fixture-replace' });
  assert.equal(rerun.runs.length, 2); assert.ok(rerun.partitions.every(p => p.rows === 100));
});

test('worker budget and resource pools are GLOBAL across concurrent partitions', () => {
  const workflow = ecommerceWorkflow(); workflow.pools.api = 1; workflow.pools.warehouse = 1;
  const plan = planBackfill('2026-09-27', '2026-09-29', TODAY, EXAMPLE_PARTITIONS);
  for (const workers of [1, 2, 4]) {
    const result = simulateBackfill(workflow, plan, { execution_id: 'fixture-workers', workers, partition_concurrency: 3 });
    assert.ok(result.peak_workers <= workers); assert.ok(result.peak_partitions <= 3);
    const attempts = result.runs.flatMap(run => workflow.tasks.flatMap(task => run.tasks[task.id].attempts.map(a => ({ ...a, pool: task.resource_pool }))));
    for (let minute = 360; minute <= 360 + result.total_minutes; minute++) {
      const running = attempts.filter(a => a.start_minute <= minute && a.end_minute! > minute);
      assert.ok(running.length <= workers, `global workers at ${minute}`);
      for (const [pool, limit] of Object.entries(workflow.pools)) assert.ok(running.filter(a => a.pool === pool).length <= limit, `${pool} at ${minute}`);
    }
  }
});

test('partition concurrency one prevents overlap even with excess worker capacity', () => {
  const result = simulateBackfill(ecommerceWorkflow(), planBackfill('2026-09-27', '2026-09-29', TODAY, EXAMPLE_PARTITIONS), { execution_id: 'fixture-serial', workers: 4, partition_concurrency: 1 });
  assert.equal(result.peak_partitions, 1); assert.equal(result.total_minutes, 42);
  for (let i = 1; i < result.runs.length; i++) assert.ok(result.runs[i].start_time! >= result.runs[i - 1].end_time!);
});

test('invalid dates/ranges, future dates, duplicate records, forged plans and invalid capacities are rejected', () => {
  assert.throws(() => planBackfill('2026-09-29', '2026-09-27', TODAY, []), /start/);
  assert.throws(() => planBackfill('2026-09-29', TODAY, TODAY, []), /historical/);
  assert.throws(() => planBackfill('2026-08-01', '2026-09-29', TODAY, []), /Backfill days/);
  assert.throws(() => planBackfill('2026-02-30', '2026-09-29', TODAY, []), /Invalid/);
  assert.throws(() => planBackfill('2026-09-27', '2026-09-29', TODAY, [EXAMPLE_PARTITIONS[0], EXAMPLE_PARTITIONS[0]]), /unique/);
  const plan = planBackfill('2026-09-27', '2026-09-29', TODAY, EXAMPLE_PARTITIONS);
  const forged = structuredClone(plan); forged.items[0].action = 'SKIP';
  assert.throws(() => simulateBackfill(ecommerceWorkflow(), forged, { execution_id: 'fixture-forged' }), /inconsistent/);
  assert.throws(() => simulateBackfill(ecommerceWorkflow(), plan, { execution_id: 'fixture-workers-invalid', workers: 0 }), /workers/);
  assert.throws(() => simulateBackfill(ecommerceWorkflow(), plan, { execution_id: 'fixture-concurrency-invalid', partition_concurrency: 9 }), /Concurrent/);
  assert.throws(() => simulateBackfill(ecommerceWorkflow(), plan, { execution_id: 'fixture-failure-invalid', fail_partition: '2026-10-01' }), /target/);
});
