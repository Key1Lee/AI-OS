import test from 'node:test';
import assert from 'node:assert/strict';
import { createRun, criticalPath, downstream, ecommerceWorkflow, readinessExpectation, scenarioContract, simulate, stepSimulation, TASK_STATES, TODAY, topologicalOrder, validateWorkflow, whyTask } from '../src/engine';
import type { SimulationRun, WorkflowDefinition } from '../src/engine';

const task = (workflow: WorkflowDefinition, id: string) => workflow.tasks.find(t => t.id === id)!;
function snapshots(workflow: WorkflowDefinition, workers = 2): SimulationRun[] {
  const result = [createRun(workflow, { partition: TODAY, max_concurrency: workers })];
  while (!result.at(-1)!.complete) {
    assert.ok(result.length < 1000, 'simulation must terminate');
    result.push(stepSimulation(result.at(-1)!, workflow));
  }
  return result;
}

test('healthy DAG has stable topological ordering and joins both staging dependencies', () => {
  const workflow = ecommerceWorkflow(), order = topologicalOrder(workflow), states = snapshots(workflow);
  for (const t of workflow.tasks) for (const d of t.dependencies) assert.ok(order.indexOf(d) < order.indexOf(t.id));
  assert.deepEqual(order, workflow.tasks.map(t => t.id));
  for (const state of states) {
    if (state.tasks.int_orders.status === 'RUNNING') {
      assert.equal(state.tasks.stg_orders.status, 'SUCCESS'); assert.equal(state.tasks.stg_customers.status, 'SUCCESS');
    }
    assert.ok(Object.values(state.tasks).every(t => TASK_STATES.includes(t.status)));
  }
  const result = states.at(-1)!;
  assert.equal(result.status, 'SUCCESS'); assert.equal(result.now, 374);
  assert.ok(Object.values(result.tasks).every(t => t.status === 'SUCCESS'));
  assert.equal(result.outputs.mart_revenue[TODAY], 100);
});

test('cycles, missing dependencies and duplicate tasks/dependencies are rejected before executing', () => {
  const cyclic = ecommerceWorkflow(); task(cyclic, 'extract_orders').dependencies = ['dashboard'];
  assert.throws(() => createRun(cyclic, { partition: TODAY }), /Cycle/);
  const missing = ecommerceWorkflow(); task(missing, 'int_orders').dependencies.push('not-a-task');
  assert.throws(() => topologicalOrder(missing), /Unknown dependency/);
  const duplicate = ecommerceWorkflow(); duplicate.tasks.push(structuredClone(duplicate.tasks[0]));
  assert.throws(() => topologicalOrder(duplicate), /unique/);
  const repeated = ecommerceWorkflow(); task(repeated, 'int_orders').dependencies.push('stg_orders');
  assert.throws(() => topologicalOrder(repeated), /Duplicate dependency/);
});

test('final customer failure blocks descendants without failing the independent orders branch', () => {
  const workflow = scenarioContract('customer-failure').workflow, run = simulate(workflow, { partition: TODAY });
  assert.equal(run.tasks.extract_customers.status, 'FAILED'); assert.equal(run.tasks.extract_customers.execution_attempt, 1);
  for (const id of ['stg_customers', 'int_orders', 'fct_orders', 'mart_revenue', 'dashboard']) {
    assert.equal(run.tasks[id].status, 'BLOCKED'); assert.equal(run.tasks[id].execution_attempt, 0);
  }
  for (const id of ['extract_orders', 'stg_orders', 'quality_check']) assert.equal(run.tasks[id].status, 'SUCCESS');
  assert.deepEqual(whyTask(run, workflow, 'int_orders').dependencies.map(d => [d.id, d.status]), [['stg_orders', 'SUCCESS'], ['stg_customers', 'BLOCKED']]);
  assert.match(whyTask(run, workflow, 'int_orders').detail, /never started/);
  assert.deepEqual(downstream(workflow, 'extract_customers'), ['stg_customers', 'int_orders', 'fct_orders', 'mart_revenue', 'dashboard']);
});

test('transient retry waits exactly five minutes, releases the worker and increments attempts', () => {
  const workflow = scenarioContract('transient').workflow, states = snapshots(workflow), run = states.at(-1)!;
  const attempts = run.tasks.extract_orders.attempts;
  assert.equal(attempts.length, 2); assert.equal(attempts[0].status, 'FAILED'); assert.equal(attempts[1].status, 'SUCCESS');
  assert.equal(attempts[1].start_minute - attempts[0].end_minute!, 5);
  assert.equal(run.tasks.extract_orders.execution_attempt, 2); assert.equal(run.now, 383);
  const retry = states.find(r => r.tasks.extract_orders.status === 'RETRYING')!;
  assert.ok(retry); assert.notEqual(retry.tasks.stg_orders.status, 'BLOCKED');
  assert.match(whyTask(retry, workflow, 'extract_orders').detail, /06:09 Asia\/Seoul, after 5 more virtual minutes/);
  assert.ok(states.some(r => r.tasks.extract_orders.status === 'RETRYING' && r.tasks.stg_customers.status === 'RUNNING'));
  assert.equal(run.events.filter(e => e.task_id === 'extract_orders' && e.status === 'FAILED').length, 1);
  assert.equal(run.events.filter(e => e.task_id === 'extract_orders' && e.status === 'RETRYING').length, 1);
});

test('retry exhaustion is terminal; deterministic errors never get automatic retries', () => {
  const temporary = ecommerceWorkflow(); task(temporary, 'extract_orders').outcomes = [{ type: 'transient', message: 'API still unavailable' }];
  const run = simulate(temporary, { partition: TODAY });
  assert.equal(run.tasks.extract_orders.execution_attempt, 3); assert.equal(run.tasks.extract_orders.status, 'FAILED');
  assert.equal(run.tasks.dashboard.status, 'BLOCKED');
  const deterministic = ecommerceWorkflow(); task(deterministic, 'extract_orders').outcomes = [{ type: 'deterministic', message: 'Invalid SQL' }];
  assert.equal(simulate(deterministic, { partition: TODAY }).tasks.extract_orders.execution_attempt, 1);
});

test('timeouts use FAILED with timeout evidence; equal-to-limit duration succeeds', () => {
  const workflow = ecommerceWorkflow(), definition = task(workflow, 'stg_customers');
  definition.duration_minutes = 47; definition.timeout_minutes = 5; definition.retry_policy.max_attempts = 2;
  const states = snapshots(workflow), run = states.at(-1)!;
  assert.ok(states.some(r => r.tasks.stg_customers.status === 'RUNNING'));
  assert.equal(run.tasks.stg_customers.status, 'FAILED'); assert.equal(run.tasks.stg_customers.error!.type, 'timeout');
  assert.ok(run.tasks.stg_customers.attempts.every(a => a.duration === 5));
  definition.duration_minutes = 5;
  assert.equal(simulate(workflow, { partition: TODAY }).tasks.stg_customers.status, 'SUCCESS');
});

test('daily scheduling is separate from readiness and uses explicit Asia/Seoul timestamps', () => {
  const workflow = ecommerceWorkflow(), early = createRun(workflow, { partition: TODAY, start_minute: 355 });
  assert.equal(early.activated, false); assert.equal(early.events.length, 0);
  assert.match(whyTask(early, workflow, 'extract_orders').detail, /06:00 Asia\/Seoul/);
  const started = stepSimulation(early, workflow);
  assert.equal(started.now, 360); assert.equal(started.tasks.extract_orders.status, 'RUNNING');
  assert.equal(started.tasks.int_orders.status, 'WAITING');
  assert.equal(started.tasks.extract_orders.start_time, '2026-10-02T06:00:00+09:00');
  const manual = stepSimulation(createRun(workflow, { partition: TODAY, start_minute: 355, trigger: { kind: 'manual' } }), workflow);
  assert.equal(manual.now, 355);
});

test('a declared asset event triggers the same workflow; unrelated assets cannot', () => {
  const workflow = ecommerceWorkflow();
  const run = simulate(workflow, { partition: TODAY, start_minute: 355, trigger: { kind: 'asset', asset_id: 'source.orders' } });
  assert.equal(run.tasks.extract_orders.start_time, '2026-10-02T05:55:00+09:00');
  assert.equal(run.status, 'SUCCESS');
  assert.throws(() => createRun(workflow, { partition: TODAY, trigger: { kind: 'asset', asset_id: 'mart_revenue' } }), /does not trigger/);
});

test('worker and pool constraints leave eligible tasks READY and never overcommit', () => {
  const workflow = ecommerceWorkflow();
  for (const workers of [1, 2, 4]) {
    for (const state of snapshots(workflow, workers)) assert.ok(Object.values(state.tasks).filter(t => t.status === 'RUNNING').length <= workers);
  }
  const serial = snapshots(workflow, 1); assert.equal(serial.at(-1)!.now, 381);
  assert.equal(serial[1].tasks.extract_customers.status, 'READY');
  assert.match(whyTask(serial[1], workflow, 'extract_customers').detail, /worker/);
  workflow.pools.api = 1;
  for (const state of snapshots(workflow, 4)) assert.ok(workflow.tasks.filter(t => t.resource_pool === 'api' && state.tasks[t.id].status === 'RUNNING').length <= 1);
});

test('SKIPPED propagation and all_done/one_success trigger rules are explicit', () => {
  const disabled = ecommerceWorkflow(); task(disabled, 'extract_customers').enabled = false;
  const skipped = simulate(disabled, { partition: TODAY });
  assert.equal(skipped.tasks.extract_customers.status, 'SKIPPED'); assert.equal(skipped.tasks.int_orders.status, 'BLOCKED');
  const cleanup = scenarioContract('customer-failure').workflow; task(cleanup, 'stg_customers').trigger_rule = 'all_done';
  assert.equal(simulate(cleanup, { partition: TODAY }).tasks.stg_customers.status, 'SUCCESS');
  const one = scenarioContract('customer-failure').workflow; task(one, 'int_orders').trigger_rule = 'one_success';
  assert.equal(simulate(one, { partition: TODAY }).tasks.int_orders.status, 'SUCCESS');
  const allFailed = scenarioContract('customer-failure').workflow;
  task(allFailed, 'extract_orders').outcomes = [{ type: 'deterministic', message: 'No orders' }];
  task(allFailed, 'int_orders').trigger_rule = 'one_success';
  assert.equal(simulate(allFailed, { partition: TODAY }).tasks.int_orders.status, 'BLOCKED');
});

test('same-input reruns preserve 100 rows with replace and accumulate 200 with append', () => {
  for (const [scenario, expected] of [['healthy', 100], ['unsafe-rerun', 200]] as const) {
    const workflow = scenarioContract(scenario).workflow, first = simulate(workflow, { partition: TODAY, run_id: 'first' });
    const second = simulate(workflow, { partition: TODAY, run_id: 'second', initial_outputs: first.outputs });
    assert.equal(first.outputs.mart_revenue[TODAY], 100); assert.equal(second.outputs.mart_revenue[TODAY], expected);
    assert.equal(first.outputs.mart_revenue[TODAY], 100, 'rerun must not mutate earlier evidence');
  }
  const unknown = ecommerceWorkflow(); task(unknown, 'mart_revenue').idempotent = 'unknown'; validateWorkflow(unknown);
});

test('critical path is duration-weighted and shortening the other branch cannot speed it up', () => {
  const normal = criticalPath(ecommerceWorkflow()); assert.equal(normal.minutes, 14);
  const long = scenarioContract('long-branch').workflow, path = criticalPath(long);
  assert.equal(path.minutes, 19); assert.ok(path.tasks.includes('stg_customers'));
  task(long, 'stg_orders').duration_minutes = 1;
  assert.equal(criticalPath(long).minutes, 19);
});

test('one-success joins use the first nominally successful parent in the duration bound', () => {
  const workflow = scenarioContract('long-branch').workflow;
  task(workflow, 'int_orders').trigger_rule = 'one_success';
  workflow.pools.warehouse = 8;
  assert.equal(criticalPath(workflow).minutes, 14);
  assert.equal(simulate(workflow, { partition: TODAY, max_concurrency: 8 }).now, 374);
});

test('simulation and event ordering are repeatable and do not mutate the supplied definition', () => {
  const workflow = scenarioContract('transient').workflow, before = structuredClone(workflow);
  const options = { partition: TODAY, start_minute: 355, run_id: 'repeatable' };
  assert.deepEqual(simulate(workflow, options), simulate(workflow, options)); assert.deepEqual(workflow, before);
  const run = createRun(workflow, options), old = structuredClone(run); stepSimulation(run, workflow); assert.deepEqual(run, old);
  const completed = simulate(workflow, options); assert.deepEqual(stepSimulation(completed, workflow), completed);
});

test('invalid dates, policies, capacities, outcomes and prototype IDs fail before execution', () => {
  const workflow = ecommerceWorkflow();
  for (const date of ['2026-02-30', '2026-13-01', 'not-a-date']) assert.throws(() => createRun(workflow, { partition: date }), /Invalid partition/);
  for (const workers of [0, -1, 2.5, 9, NaN]) assert.throws(() => createRun(workflow, { partition: TODAY, max_concurrency: workers }), /Workers/);
  const invalid = ecommerceWorkflow(); task(invalid, 'extract_orders').retry_policy.max_attempts = 0;
  assert.throws(() => validateWorkflow(invalid), /Max attempts/);
  const pool = ecommerceWorkflow(); task(pool, 'extract_orders').resource_pool = 'missing_pool'; assert.throws(() => validateWorkflow(pool), /Unknown resource/);
  const unsafePool = ecommerceWorkflow(); task(unsafePool, 'extract_orders').resource_pool = 'toString'; assert.throws(() => validateWorkflow(unsafePool), /safe, unique identifiers/);
  const proto = ecommerceWorkflow(); proto.assets[0].id = '__proto__'; assert.throws(() => validateWorkflow(proto));
  const label = ecommerceWorkflow(); task(label, 'mart_revenue').write_mode = 'append'; assert.throws(() => validateWorkflow(label), /idempotency/);
  const outcome = ecommerceWorkflow(); task(outcome, 'extract_orders').outcomes = []; assert.throws(() => validateWorkflow(outcome), /outcomes/);
});

test('expectation is an execution fact with measurable delay and unavailable readiness', () => {
  const workflow = ecommerceWorkflow(); workflow.expected_ready_time = '06:10';
  const run = simulate(workflow, { partition: TODAY });
  assert.deepEqual(readinessExpectation(run, workflow), { expected: 370, actual: 374, delay_minutes: 4 });
  assert.equal(readinessExpectation(createRun(workflow, { partition: TODAY }), workflow).actual, null);
});
