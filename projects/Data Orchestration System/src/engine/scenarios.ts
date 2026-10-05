import type { ScenarioContract, TaskDefinition, WorkflowDefinition } from './types';

export const TODAY = '2026-10-02';
export const LEARNING_QUESTIONS = [
  'What runs?', 'When does it run?', 'What must finish first?', 'What happens if it fails?',
  'Can it be retried?', 'Can it safely run twice?', 'How do I reprocess history?', 'What gets blocked downstream?',
];

function task(id: string, stage: TaskDefinition['stage'], parents: string[], minutes: number, inputs: string[], output: string, purpose: string): TaskDefinition {
  return { id, name: id, stage, dependencies: parents, purpose, trigger: 'workflow', trigger_rule: 'all_success',
    duration_minutes: minutes, timeout_minutes: 10,
    retry_policy: { max_attempts: 3, delay_minutes: 5, retryable_errors: ['transient', 'timeout'] },
    inputs, outputs: [output], idempotent: true, outcomes: ['success'], enabled: true,
    resource_pool: stage === 'ingest' ? 'api' : stage === 'dashboard' ? 'reporting' : 'warehouse',
    write_mode: 'replace', output_rows: 100 };
}
export function ecommerceWorkflow(): WorkflowDefinition {
  const tasks = [
    task('extract_orders', 'ingest', [], 4, ['source.orders'], 'raw_orders', 'Bring today’s order data into the pipeline.'),
    task('extract_customers', 'ingest', [], 3, ['source.customers'], 'raw_customers', 'Bring customer data into the pipeline independently of orders.'),
    task('stg_orders', 'staging', ['extract_orders'], 2, ['raw_orders'], 'stg_orders', 'Run the declared orders staging model.'),
    task('stg_customers', 'staging', ['extract_customers'], 2, ['raw_customers'], 'stg_customers', 'Run the declared customer staging model.'),
    task('int_orders', 'transform', ['stg_orders', 'stg_customers'], 3, ['stg_orders', 'stg_customers'], 'int_orders', 'Wait for both staging models, then run the declared intermediate model.'),
    task('quality_check', 'transform', ['stg_orders'], 2, ['stg_orders'], 'quality_result', 'Execute the supplied order quality check before the fact is published.'),
    task('fct_orders', 'transform', ['int_orders', 'quality_check'], 2, ['int_orders', 'quality_result'], 'fct_orders', 'Publish the declared order fact only after the model and quality check finish.'),
    task('mart_revenue', 'mart', ['fct_orders'], 2, ['fct_orders'], 'mart_revenue', 'Publish the declared revenue mart for this partition.'),
    task('dashboard', 'dashboard', ['mart_revenue'], 1, ['mart_revenue'], 'revenue_dashboard', 'Refresh the executive dashboard from the published mart.'),
  ];
  return { id: 'daily-ecommerce', name: 'Daily e-commerce pipeline',
    purpose: 'Make a revenue dashboard ready from two independent source feeds.', tasks,
    assets: [{ id: 'source.orders', name: 'Orders source', producer_task_id: null },
      { id: 'source.customers', name: 'Customers source', producer_task_id: null },
      ...tasks.map(t => ({ id: t.outputs[0], name: t.outputs[0], producer_task_id: t.id }))],
    schedule: { frequency: 'daily', time: '06:00', timezone: 'Asia/Seoul' },
    asset_triggers: ['source.orders'], pools: { api: 2, warehouse: 2, reporting: 1 }, expected_ready_time: '07:00' };
}

export const SCENARIO_INFO = [
  { id: 'healthy', title: '01 · A successful day', short: 'Follow the happy path', description: 'Two source feeds meet before the fact, mart, and dashboard can run.' },
  { id: 'customer-failure', title: '02 · Break a dependency', short: 'Failed is different from blocked', description: 'Customer extraction has a deterministic configuration error. The orders branch can still succeed.' },
  { id: 'transient', title: '03 · Try again, safely', short: 'A temporary API timeout', description: 'The first orders request times out. A five-minute delay precedes a successful second attempt.' },
  { id: 'unsafe-rerun', title: '04 · Run it twice', short: '100 rows → 200 rows', description: 'The mart appends the same authored 100-row payload each time. Compare two runs.' },
  { id: 'long-branch', title: '05 · Find the critical path', short: 'One branch sets the pace', description: 'Customer staging takes eight minutes. A faster orders branch cannot shorten that dependency chain.' },
] as const;
export type ScenarioId = typeof SCENARIO_INFO[number]['id'];

export function scenarioContract(id: ScenarioId): ScenarioContract {
  const info = SCENARIO_INFO.find(s => s.id === id);
  if (!info) throw new Error(`Unknown scenario: ${id}.`);
  const workflow = ecommerceWorkflow();
  const find = (taskId: string) => workflow.tasks.find(t => t.id === taskId)!;
  if (id === 'customer-failure') find('extract_customers').outcomes = [{ type: 'deterministic', message: 'Customer source configuration is invalid. Fix it before rerunning.' }];
  if (id === 'transient') find('extract_orders').outcomes = [{ type: 'transient', message: 'Orders API request timed out temporarily.' }, 'success'];
  if (id === 'unsafe-rerun') { find('mart_revenue').write_mode = 'append'; find('mart_revenue').idempotent = false; }
  if (id === 'long-branch') find('stg_customers').duration_minutes = 8;
  return { contract_version: 'orchestration-scenario-v1', id: `ecommerce-${id}-v1`, title: info.title,
    brief: info.description, workflow, default_partition: TODAY,
    evidence_task_ids: ['dashboard', 'mart_revenue', 'fct_orders', 'int_orders', 'extract_customers', 'extract_orders'],
    learner_questions: LEARNING_QUESTIONS };
}
