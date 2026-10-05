import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

async function main() {
const payload = JSON.parse(readFileSync(0, 'utf8'));
const { simulate } = await import(pathToFileURL(resolve(payload.project, 'src/engine/index.ts')).href);
const task = {
  id: 'orders_load', name: 'Orders load', purpose: 'Execute the supplied local loader; retry a declared injected transient crash',
  stage: 'ingest', dependencies: [], trigger: 'workflow', trigger_rule: 'all_success',
  duration_minutes: 1, timeout_minutes: 5,
  retry_policy: { max_attempts: 2, delay_minutes: 1, retryable_errors: ['transient'] },
  inputs: ['source.orders'], outputs: ['orders_raw'], idempotent: 'unknown',
  outcomes: payload.fail_after_rows === null ? ['success'] :
    [{ type: 'transient', message: `Injected crash after ${payload.fail_after_rows} committed rows` }, 'success'],
  enabled: true, resource_pool: 'warehouse', write_mode: 'replace', output_rows: 1000,
};
const workflow = {
  id: 'ae_lab_orders', name: 'AE Lab order load', purpose: 'Native retry eligibility; Lab owns actual database writes',
  tasks: [task], assets: [{ id: 'source.orders', name: 'Orders', producer_task_id: null },
    { id: 'orders_raw', name: 'Loaded orders', producer_task_id: 'orders_load' }],
  schedule: { frequency: 'daily', time: '06:00', timezone: 'Asia/Seoul' },
  asset_triggers: ['source.orders'], pools: { warehouse: 1 }, expected_ready_time: '07:00',
};
const run = simulate(workflow, { run_id: payload.run_id, partition: '2026-10-02',
  clock_date: '2026-10-03', start_minute: 360, trigger: { kind: 'manual' }, max_concurrency: 1 });
process.stdout.write(JSON.stringify({ status: run.status, attempts: run.tasks.orders_load.attempts,
  events: run.events, native_run: run, provenance: 'Native orchestration simulator; output counts are declared, actual rows measured by Lab' }));
}
main().catch(error => { process.stderr.write(String(error)); process.exitCode = 1; });
