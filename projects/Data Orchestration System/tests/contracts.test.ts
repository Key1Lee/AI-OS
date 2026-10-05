import test from 'node:test';
import assert from 'node:assert/strict';
import Ajv from 'ajv';
import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { executionEventSchema, scenarioSchema, scenarioContract, SCENARIO_INFO, simulate, TODAY, validateWorkflow, workflowFromModels } from '../src/engine';

const ajv = new Ajv({ allErrors: true }), validateEvent = ajv.compile(executionEventSchema), validateScenario = ajv.compile(scenarioSchema);
test('every scenario and every transition satisfy independently compiled integration schemas', () => {
  for (const info of SCENARIO_INFO) {
    const scenario = scenarioContract(info.id);
    assert.equal(validateScenario(scenario), true, JSON.stringify(validateScenario.errors));
    const result = simulate(scenario.workflow, { partition: TODAY });
    assert.equal(new Set(result.events.map(e => e.event_id)).size, result.events.length);
    for (const event of result.events) assert.equal(validateEvent(event), true, JSON.stringify(validateEvent.errors));
    for (const event of result.events.filter(e => ['FAILED', 'RETRYING'].includes(e.status))) {
      assert.ok(event.error_type); assert.ok(event.error_message); assert.ok(event.start_time && event.end_time); assert.ok(event.duration! > 0);
    }
    assert.ok(scenario.evidence_task_ids.every(id => scenario.workflow.tasks.some(t => t.id === id)));
  }
});
test('malformed contract versions, states and assessment-policy extensions fail schema validation', () => {
  const scenario = scenarioContract('healthy'), result = simulate(scenario.workflow, { partition: TODAY });
  assert.equal(validateEvent({ ...result.events[0], status: 'TIMEOUT' }), false);
  assert.equal(validateEvent({ ...result.events[0], contract_version: 'wrong' }), false);
  const incomplete = { ...result.events[0] } as Record<string, unknown>; delete incomplete.upstream_state;
  assert.equal(validateEvent(incomplete), false);
  assert.equal(validateScenario({ ...scenario, scoring: { points: 10 } }), false);
  assert.equal(validateScenario({ ...scenario, hints: ['Read the API error'] }), false);
});
test('Modeling adapter uses existing parents and preserves opaque grain/materialization metadata', () => {
  const grain = { declared: 'one row per order', classification: 'declared', status: 'pass' };
  const envelope = { contract_version: 'modeling-lab-v1' as const, models: [
    { id: 'orders', name: 'orders', layer: 'source' as const, why: 'Source records', parents: [], grain, materialization: 'external' },
    { id: 'stg_orders', name: 'stg_orders', layer: 'staging' as const, why: 'Conformed orders', parents: ['orders'], grain, materialization: 'view' },
    { id: 'fct_orders', name: 'fct_orders', layer: 'fact' as const, why: 'Order fact', parents: ['stg_orders'], grain, materialization: { type: 'incremental', owned_by: 'Modeling' } },
  ] };
  const before = structuredClone(envelope), workflow = workflowFromModels(envelope);
  validateWorkflow(workflow); assert.equal(workflow.tasks.length, 2);
  assert.deepEqual(workflow.tasks[1].dependencies, ['build_stg_orders']);
  assert.equal(workflow.tasks[1].idempotent, 'unknown');
  assert.deepEqual(workflow.assets[2].model_reference!.grain, grain);
  assert.deepEqual(workflow.assets[2].model_reference!.materialization, envelope.models[2].materialization);
  assert.deepEqual(envelope, before);
  assert.equal(simulate(workflow, { partition: TODAY }).status, 'SUCCESS');
});
test('Modeling adapter rejects unknown model parents and model cycles', () => {
  const base = { id: 'model', name: 'model', layer: 'fact' as const, why: 'Declared fact', parents: ['missing'], grain: null, materialization: 'table' };
  assert.throws(() => workflowFromModels({ contract_version: 'modeling-lab-v1', models: [base] }), /Unknown model parent/);
  assert.throws(() => workflowFromModels({ contract_version: 'modeling-lab-v1', models: [{ ...base, parents: ['model'] }] }), /Cycle/);
  assert.throws(() => workflowFromModels({ contract_version: 'modeling-lab-v1', models: [{ ...base, layer: 'source', parents: ['model'] }] }), /external roots/);
});
test('truth engine uses no wall clock, randomness, sibling imports or orchestration vendors', () => {
  const files = readdirSync(resolve('src/engine')).filter(f => f.endsWith('.ts'));
  for (const file of files) {
    const text = readFileSync(resolve('src/engine', file), 'utf8');
    assert.doesNotMatch(text, /Date\.now\(|new Date\(\)|Math\.random\(|setInterval\(|setTimeout\(/, file);
    assert.doesNotMatch(text, /from\s+['"].*(?:Data Modeling|Data Observability|Toptal|airflow|dagster|prefect|openai)/i, file);
  }
  assert.equal(executionEventSchema.properties.status.enum.includes('FAILED'), true);
});
