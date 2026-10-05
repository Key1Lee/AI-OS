import test from 'node:test';
import assert from 'node:assert/strict';
import Ajv from 'ajv';
import { renderToStaticMarkup } from 'react-dom/server';
import { Timeline } from '../../src/ui/components';
import { createRun, criticalPath, ecommerceWorkflow, executionEventSchema, planBackfill, scenarioContract, simulate, simulateBackfill, stepSimulation, TASK_STATES, TODAY, topologicalOrder, validateWorkflow, whyTask, workflowFromModels } from '../../src/engine/index';
import type { SimulationRun, TaskDefinition, WorkflowDefinition } from '../../src/engine/index';

function dag(spec: Array<{ id: string; dependencies?: string[]; duration?: number; rule?: TaskDefinition['trigger_rule']; outcomes?: TaskDefinition['outcomes']; enabled?: boolean; retryDelay?: number; attempts?: number; pool?: string }>): WorkflowDefinition {
  const defaults = ecommerceWorkflow();
  return { ...defaults, id: 'independent-probe', assets: [], asset_triggers: [], pools: { shared: 8, separate: 8 },
    tasks: spec.map(s => ({ ...structuredClone(defaults.tasks[0]), id: s.id, name: s.id, purpose: 'Independent behavioral probe', stage: 'transform',
      dependencies: s.dependencies ?? [], inputs: [], outputs: [], duration_minutes: s.duration ?? 1, timeout_minutes: 10000,
      trigger_rule: s.rule ?? 'all_success', outcomes: s.outcomes ?? ['success'], enabled: s.enabled ?? true, resource_pool: s.pool ?? 'shared',
      retry_policy: { max_attempts: s.attempts ?? 2, delay_minutes: s.retryDelay ?? 2, retryable_errors: ['transient', 'timeout'] } })) };
}
function trace(workflow: WorkflowDefinition, options = {}) {
  const states = [createRun(workflow, { partition: TODAY, ...options })];
  while (!states.at(-1)!.complete) {
    assert.ok(states.length < 2500, 'must terminate');
    const previous = structuredClone(states.at(-1)!);
    states.push(stepSimulation(states.at(-1)!, workflow));
    assert.deepEqual(states.at(-2), previous, 'stepping cannot mutate prior evidence');
  }
  return states;
}
const temporary = { type: 'transient' as const, message: 'Independent temporary failure' };
const bad = { type: 'deterministic' as const, message: 'Independent permanent failure' };

test('independent reversed diamond has stable ready-node definition priority and waits for slow parent', () => {
  const workflow = dag([{ id: 'D', dependencies: ['B', 'C'], duration: 5 }, { id: 'C', dependencies: ['A'], duration: 2 }, { id: 'B', dependencies: ['A'], duration: 8 }, { id: 'A', duration: 2 }]);
  assert.deepEqual(topologicalOrder(workflow), ['A', 'C', 'B', 'D']);
  const run = simulate(workflow, { partition: TODAY, max_concurrency: 8 });
  assert.equal(run.tasks.D.attempts[0].start_minute, 370);
  assert.equal(run.now, 375);
  assert.deepEqual(criticalPath(workflow), { tasks: ['A', 'B', 'D'], minutes: 15 });
  workflow.tasks.find(t => t.id === 'C')!.duration_minutes = 1;
  assert.equal(criticalPath(workflow).minutes, 15);
});
test('independent self-cycle, distant cycle, duplicate edge, unknown edge and duplicate task reject', () => {
  for (const workflow of [dag([{ id: 'A', dependencies: ['A'] }]), dag([{ id: 'A', dependencies: ['C'] }, { id: 'B', dependencies: ['A'] }, { id: 'C', dependencies: ['B'] }]), dag([{ id: 'A' }, { id: 'B', dependencies: ['A', 'A'] }]), dag([{ id: 'A', dependencies: ['B'] }]), dag([{ id: 'A' }, { id: 'A' }])]) {
    assert.throws(() => createRun(workflow, { partition: TODAY }));
  }
});
test('all_success stays WAITING during retry, becomes BLOCKED only after exhausted failure', () => {
  const workflow = dag([{ id: 'A', duration: 1, outcomes: [temporary] }, { id: 'B', dependencies: ['A'] }, { id: 'C', duration: 9 }]);
  const states = trace(workflow);
  for (const r of states.filter(r => r.tasks.A.status === 'RETRYING')) assert.equal(r.tasks.B.status, 'WAITING');
  const end = states.at(-1)!;
  assert.equal(end.tasks.A.status, 'FAILED'); assert.equal(end.tasks.A.execution_attempt, 2);
  assert.equal(end.tasks.B.status, 'BLOCKED'); assert.equal(end.tasks.B.execution_attempt, 0);
  assert.equal(end.tasks.C.status, 'SUCCESS');
  assert.match(whyTask(end, workflow, 'B').detail, /never started/);
});
test('all_done joins wait for a retrying and failed parent to both become terminal', () => {
  const workflow = dag([{ id: 'A', outcomes: [temporary, 'success'], duration: 2 }, { id: 'B', outcomes: [bad], duration: 1 }, { id: 'C', dependencies: ['A', 'B'], rule: 'all_done' }]);
  const run = simulate(workflow, { partition: TODAY, max_concurrency: 8 });
  assert.equal(run.tasks.C.attempts[0].start_minute, 366); assert.equal(run.tasks.C.status, 'SUCCESS');
  assert.equal(run.status, 'FAILED');
});
test('one_success starts at first success despite long running other parent', () => {
  const workflow = dag([{ id: 'A', duration: 1 }, { id: 'B', duration: 10 }, { id: 'C', dependencies: ['A', 'B'], rule: 'one_success', duration: 3 }]);
  const states = trace(workflow, { max_concurrency: 8 });
  assert.ok(states.some(r => r.tasks.C.status === 'RUNNING' && r.tasks.B.status === 'RUNNING'));
  assert.equal(states.at(-1)!.tasks.C.attempts[0].start_minute, 361);
  assert.equal(criticalPath(workflow).minutes, 10, 'long independent running task still bounds whole workflow');
});
test('skipped/failed parents block one_success but all_done runs; no ninth state appears', () => {
  const workflow = dag([{ id: 'A', enabled: false }, { id: 'B', outcomes: [bad] }, { id: 'C', dependencies: ['A', 'B'], rule: 'one_success' }, { id: 'D', dependencies: ['C'], rule: 'all_done' }]);
  const states = trace(workflow), end = states.at(-1)!;
  assert.equal(end.tasks.A.status, 'SKIPPED'); assert.equal(end.tasks.C.status, 'BLOCKED'); assert.equal(end.tasks.D.status, 'SUCCESS');
  assert.ok(states.every(r => Object.values(r.tasks).every(t => TASK_STATES.includes(t.status))));
});
test('retry release lets another task run; delay is an eligibility boundary under contention', () => {
  const workflow = dag([{ id: 'A', duration: 1, outcomes: [temporary, 'success'], retryDelay: 1 }, { id: 'B', duration: 10 }]);
  const states = trace(workflow, { max_concurrency: 1 }), pending = states.find(r => r.tasks.A.status === 'RETRYING')!, end = states.at(-1)!;
  assert.equal(pending.now, 361); assert.equal(pending.tasks.B.status, 'RUNNING');
  assert.ok(states.some(r => r.now === 362 && r.tasks.A.status === 'READY' && r.tasks.B.status === 'RUNNING'));
  assert.equal(end.tasks.A.attempts[1].start_minute, 371);
  const explanation = whyTask(pending, workflow, 'A').detail;
  assert.match(explanation, /eligible/i, 'must not promise a start while the only worker is occupied');
  assert.doesNotMatch(explanation, /Next attempt starts at/);
});
test('timeline names policy delay and capacity waiting truthfully for occupied retry worker', () => {
  const workflow = dag([{ id: 'A', duration: 1, outcomes: [temporary, 'success'], retryDelay: 1 }, { id: 'B', duration: 10 }]);
  const run = simulate(workflow, { partition: TODAY, max_concurrency: 1 });
  const html = renderToStaticMarkup(Timeline({ workflow, run, onSelect: () => {} }));
  assert.match(html, /1m retry delay \+ 9m waiting for capacity/);
  assert.match(html, /wait between attempts/);
});
test('timeout retry never magically succeeds when authored duration still exceeds timeout', () => {
  const workflow = dag([{ id: 'A', duration: 47, outcomes: ['success'], attempts: 3 }]); workflow.tasks[0].timeout_minutes = 5;
  const end = simulate(workflow, { partition: TODAY });
  assert.equal(end.tasks.A.execution_attempt, 3); assert.equal(end.tasks.A.status, 'FAILED');
  assert.deepEqual(end.tasks.A.attempts.map(a => a.duration), [5, 5, 5]);
  assert.deepEqual(end.tasks.A.attempts.map(a => a.start_minute), [360, 367, 374]);
});
test('UTC midnight crossing and historical partition preserve logical date and timestamp offset', () => {
  const workflow = dag([{ id: 'A', duration: 3 }]); workflow.schedule = { frequency: 'daily', time: '23:59', timezone: 'UTC' };
  const run = simulate(workflow, { partition: '2024-02-29', clock_date: TODAY, start_minute: 1438 });
  assert.equal(run.tasks.A.start_time, '2026-10-02T23:59:00Z');
  assert.equal(run.tasks.A.end_time, '2026-10-03T00:02:00Z');
  assert.ok(run.events.every(e => e.partition === '2024-02-29'));
  assert.equal(createRun(workflow, { partition: TODAY, start_minute: 1438 }).activated, false);
});
test('source asset event does not erase task dependencies or daily gate semantics', () => {
  const workflow = ecommerceWorkflow();
  const run = stepSimulation(createRun(workflow, { partition: TODAY, start_minute: 0, trigger: { kind: 'asset', asset_id: 'source.orders' } }), workflow);
  assert.equal(run.tasks.extract_orders.status, 'RUNNING'); assert.equal(run.tasks.stg_orders.status, 'WAITING');
  for (const asset_id of ['raw_orders', 'source.customers', 'missing']) assert.throws(() => createRun(workflow, { partition: TODAY, trigger: { kind: 'asset', asset_id } }));
});
test('reruns preserve other partitions, input stores and earlier traces for both write modes', () => {
  for (const [scenario, rows] of [['healthy', 100], ['unsafe-rerun', 200]] as const) {
    const workflow = scenarioContract(scenario).workflow, first = simulate(workflow, { partition: '2026-09-28' });
    const saved = structuredClone(first);
    const current = simulate(workflow, { partition: TODAY, initial_outputs: first.outputs });
    const rerun = simulate(workflow, { partition: TODAY, initial_outputs: current.outputs });
    assert.equal(rerun.outputs.mart_revenue[TODAY], rows); assert.equal(rerun.outputs.mart_revenue['2026-09-28'], 100);
    assert.deepEqual(first, saved); assert.equal(current.outputs.mart_revenue[TODAY], 100);
  }
});
test('calendar backfills handle month/year/leap boundaries and exact 31-day range bound', () => {
  assert.deepEqual(planBackfill('2024-02-28', '2024-03-01', TODAY, []).items.map(i => i.partition), ['2024-02-28', '2024-02-29', '2024-03-01']);
  assert.deepEqual(planBackfill('2025-12-31', '2026-01-01', TODAY, []).items.map(i => i.partition), ['2025-12-31', '2026-01-01']);
  assert.equal(planBackfill('2026-08-01', '2026-08-31', TODAY, []).items.length, 31);
  assert.throws(() => planBackfill('2026-08-01', '2026-09-01', TODAY, []));
});
test('append behavior cannot silently turn explicit successful replacement into 200 rows', () => {
  const workflow = scenarioContract('unsafe-rerun').workflow;
  const plan = planBackfill('2026-09-30', '2026-09-30', TODAY, [{ partition: '2026-09-30', status: 'SUCCESS', rows: 100 }], 'replace');
  let result;
  try { result = simulateBackfill(workflow, plan); } catch (e) { assert.match((e as Error).message, /append|replace|replacement/i); return; }
  assert.equal(result.partitions[0].rows, 100, 'explicit replacement must replace or reject append incompatibility');
});
test('31 backfill dates with retries obey independent interval sweep global budgets', () => {
  const workflow = ecommerceWorkflow(); workflow.tasks[0].outcomes = [temporary, 'success']; workflow.pools.api = 1; workflow.pools.warehouse = 1;
  for (const workers of [1, 2, 4]) {
    const result = simulateBackfill(workflow, planBackfill('2026-08-01', '2026-08-31', TODAY, []), { workers, partition_concurrency: 3 });
    const attempts = result.runs.flatMap(r => workflow.tasks.flatMap(t => r.tasks[t.id].attempts.map(a => ({ start: a.start_minute, end: a.end_minute!, pool: t.resource_pool }))));
    const instants = [...new Set(attempts.flatMap(a => [a.start, a.end]))].sort((a, b) => a - b);
    for (const instant of instants) {
      const active = attempts.filter(a => a.start <= instant && instant < a.end);
      assert.ok(active.length <= workers, `global workers at ${instant}`);
      for (const [pool, budget] of Object.entries(workflow.pools)) assert.ok(active.filter(a => a.pool === pool).length <= budget, `pool ${pool} at ${instant}`);
      const partitions = result.runs.filter(r => r.tasks.extract_orders.attempts[0].start_minute <= instant && instant < r.now);
      assert.ok(partitions.length <= 3, `partition limit at ${instant}`);
    }
    assert.equal(result.partitions.length, 31); assert.ok(result.partitions.every(p => p.status === 'SUCCESS'));
  }
});
test('backfill result contains exact replay definition/options including partition-specific failure', () => {
  const workflow = ecommerceWorkflow();
  const result = simulateBackfill(workflow, planBackfill('2026-09-27', '2026-09-29', TODAY, []), { workers: 3, partition_concurrency: 2, fail_partition: '2026-09-28' });
  const exported = JSON.parse(JSON.stringify(result));
  assert.deepEqual(exported.source_workflow, workflow);
  const replayed = simulateBackfill(exported.source_workflow, exported.plan, exported.options);
  assert.deepEqual(replayed, exported);
  assert.deepEqual(exported.partitions.map((p: any) => p.status), ['SUCCESS', 'FAILED', 'SUCCESS']);
});
test('runtime boundary rejects primitive and nested non-record output stores before execution', () => {
  const workflow = ecommerceWorkflow();
  for (const initial_outputs of [7, 'text', [], { mart_revenue: 7 }, { mart_revenue: null }, { mart_revenue: [] }]) {
    assert.throws(() => createRun(workflow, { partition: TODAY, initial_outputs } as any), `invalid output store ${JSON.stringify(initial_outputs)}`);
  }
});
test('runtime boundary rejects string-valued dependencies even with matching one-letter ID', () => {
  const workflow = dag([{ id: 'A' }, { id: 'B', dependencies: ['A'] }]);
  (workflow.tasks[1] as any).dependencies = 'A';
  assert.throws(() => validateWorkflow(workflow)); assert.throws(() => createRun(workflow, { partition: TODAY }));
});
test('accepted custom engine events satisfy the exported consumer schema', () => {
  const validate = new Ajv().compile(executionEventSchema);
  for (const workflow of [dag([{ id: 'A', enabled: false }, { id: 'B', dependencies: ['A'] }]), dag([{ id: 'A', outcomes: [temporary, 'success'] }, { id: 'B', dependencies: ['A'], rule: 'all_done' }])]) {
    for (const event of simulate(workflow, { partition: TODAY }).events) assert.ok(validate(event), JSON.stringify(validate.errors));
  }
});
test('model adapter preserves metadata objects without shared references and infers no SQL semantics', () => {
  const envelope = { contract_version: 'modeling-lab-v1' as const, models: [
    { id: 'source', name: 'External source', why: 'Available data', layer: 'source' as const, parents: [], grain: { keys: ['id'] }, materialization: { type: 'table', sql: 'opaque' } },
    { id: 'model', name: 'Model', why: 'Declared model', layer: 'staging' as const, parents: ['source'], grain: { keys: ['id'] }, materialization: { type: 'incremental', unique_key: 'id' } },
    { id: 'output', name: 'Output', why: 'Publish declared output', layer: 'output' as const, parents: ['model'], grain: { keys: ['id'] }, materialization: { type: 'view' } },
  ] };
  const before = structuredClone(envelope), workflow = workflowFromModels(envelope);
  assert.deepEqual(workflow.tasks.find(t => t.id === 'build_output')!.dependencies, ['build_model']);
  assert.deepEqual(workflow.assets[1].model_reference!.materialization, envelope.models[1].materialization);
  (workflow.assets[1].model_reference!.grain as any).keys.push('probe');
  assert.deepEqual(envelope, before);
  assert.equal(workflow.tasks[0].idempotent, 'unknown');
});
test('critical path excludes a skipped parent from nominal one-success candidates', () => {
  const workflow = ecommerceWorkflow();
  workflow.tasks.find(t => t.id === 'stg_customers')!.enabled = false;
  workflow.tasks.find(t => t.id === 'int_orders')!.trigger_rule = 'one_success';
  for (const pool of Object.keys(workflow.pools)) workflow.pools[pool] = 8;
  const run = simulate(workflow, { partition: TODAY, max_concurrency: 8 });
  assert.equal(run.status, 'SUCCESS'); assert.equal(run.now - 360, 14);
  assert.equal(run.tasks.int_orders.attempts[0].start_minute, 366);
  assert.equal(criticalPath(workflow).minutes, 14);
});
test('critical path excludes a transitively blocked parent from one-success candidates', () => {
  const workflow = dag([{ id: 'A', enabled: false }, { id: 'B', dependencies: ['A'] }, { id: 'C', duration: 3 }, { id: 'D', dependencies: ['B', 'C'], rule: 'one_success', duration: 5 }]);
  const run = simulate(workflow, { partition: TODAY, max_concurrency: 8 });
  assert.equal(run.tasks.B.status, 'BLOCKED'); assert.equal(run.now - 360, 8);
  assert.deepEqual(criticalPath(workflow), { tasks: ['C', 'D'], minutes: 8 });
});
test('critical path skips inherited latency when all-done follows an immediately disabled task', () => {
  const workflow = dag([{ id: 'A', duration: 10 }, { id: 'B', dependencies: ['A'], enabled: false }, { id: 'C', dependencies: ['B'], rule: 'all_done' }]);
  const run = simulate(workflow, { partition: TODAY, max_concurrency: 8 });
  assert.equal(run.tasks.C.attempts[0].start_minute, 360); assert.equal(run.now - 360, 10);
  assert.deepEqual(criticalPath(workflow), { tasks: ['A'], minutes: 10 });
});
test('array-valued resource pools cannot exploit key coercion to exceed one shared pool slot', () => {
  const workflow = ecommerceWorkflow(); workflow.pools.api = 1;
  (workflow.tasks[0] as any).resource_pool = ['api'];
  (workflow.tasks[1] as any).resource_pool = ['api'];
  assert.throws(() => validateWorkflow(workflow));
  assert.throws(() => createRun(workflow, { partition: TODAY, max_concurrency: 4 }));
});
