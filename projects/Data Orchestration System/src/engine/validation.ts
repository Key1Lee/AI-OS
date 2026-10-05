import { topologicalOrder } from './graph';
import type { Timezone, WorkflowDefinition } from './types';
import { identifier, identifiers, jsonValue, record, textField } from './guards';
export { identifier } from './guards';

export function validateDate(value: string): void {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)
    || !Number.isFinite(Date.parse(`${value}T00:00:00Z`))
    || new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) !== value) {
    throw new Error(`Invalid partition date: ${value}. Use YYYY-MM-DD.`);
  }
}
export function integer(value: number, name: string, min = 1, max = 10000): void {
  if (!Number.isInteger(value) || value < min || value > max) throw new Error(`${name} must be an integer from ${min} to ${max}.`);
}
export function timeMinute(time: string): number {
  if (typeof time !== 'string' || !/^([01]\d|2[0-3]):[0-5]\d$/.test(time)) throw new Error('Time must be HH:MM (24-hour).');
  return Number(time.slice(0, 2)) * 60 + Number(time.slice(3));
}
export function timestamp(date: string, minute: number, timezone: Timezone): string {
  const offset = timezone === 'Asia/Seoul' ? '+09:00' : 'Z';
  // Generate local virtual time independently of the host clock/timezone.
  return new Date(Date.parse(`${date}T00:00:00Z`) + minute * 60000).toISOString().replace(/\.000Z$/, offset);
}
export function clockLabel(minute: number): string {
  const dayMinute = minute % 1440;
  return `${String(Math.floor(dayMinute / 60)).padStart(2, '0')}:${String(dayMinute % 60).padStart(2, '0')}`;
}

export function validateWorkflow(workflow: WorkflowDefinition): void {
  record(workflow, 'Workflow');
  if (!Array.isArray(workflow.tasks) || !Array.isArray(workflow.assets)) throw new Error('Workflow requires task and asset arrays.');
  identifier(workflow.id); textField(workflow.name, 'Workflow name'); textField(workflow.purpose, 'Workflow purpose', true);
  record(workflow.schedule, 'Schedule');
  if (workflow.schedule.frequency !== 'daily' || !['Asia/Seoul', 'UTC'].includes(workflow.schedule.timezone)) throw new Error('Supported schedule: daily, Asia/Seoul or UTC.');
  timeMinute(workflow.schedule.time); timeMinute(workflow.expected_ready_time);
  topologicalOrder(workflow);
  record(workflow.pools, 'Resource pools');
  if (!Object.keys(workflow.pools).length) throw new Error('At least one resource pool is required.');
  for (const [name, count] of Object.entries(workflow.pools)) { identifier(name); integer(count, `Pool ${name}`, 1, 8); }
  for (const asset of workflow.assets) {
    record(asset, 'Asset'); identifier(asset.id); textField(asset.name, 'Asset name');
    if (asset.producer_task_id !== null) identifier(asset.producer_task_id);
    if (asset.model_reference !== undefined) {
      record(asset.model_reference, 'Model reference'); identifier(asset.model_reference.id);
      if (!jsonValue(asset.model_reference.grain) || !jsonValue(asset.model_reference.materialization)) throw new Error('Model metadata must be JSON data.');
    }
  }
  const assets = new Map(workflow.assets.map(a => [a.id, a]));
  if (assets.size !== workflow.assets.length) throw new Error('Asset IDs must be unique.');
  const tasks = new Map(workflow.tasks.map(t => [t.id, t]));
  for (const task of workflow.tasks) {
    identifier(task.id);
    textField(task.name, 'Task name'); textField(task.purpose, 'Task purpose');
    if (!['ingest', 'staging', 'transform', 'mart', 'dashboard'].includes(task.stage)) throw new Error('Task stage is invalid.');
    if (task.trigger !== 'workflow' || !['all_success', 'all_done', 'one_success'].includes(task.trigger_rule)) throw new Error(`Invalid trigger rule on ${task.id}.`);
    integer(task.duration_minutes, 'Task duration'); integer(task.timeout_minutes, 'Timeout');
    record(task.retry_policy, 'Retry policy');
    integer(task.retry_policy.max_attempts, 'Max attempts', 1, 10);
    integer(task.retry_policy.delay_minutes, 'Retry delay', 1, 1000);
    if (!Array.isArray(task.retry_policy.retryable_errors) || new Set(task.retry_policy.retryable_errors).size !== task.retry_policy.retryable_errors.length || task.retry_policy.retryable_errors.some(e => !['transient', 'timeout'].includes(e))) throw new Error('Only unique transient/timeout errors are automatically retryable.');
    if (typeof task.enabled !== 'boolean' || ![true, false, 'unknown'].includes(task.idempotent)) throw new Error('Task enabled/idempotent flags are invalid.');
    if (!['replace', 'append'].includes(task.write_mode) || (task.write_mode === 'append' && task.idempotent === true)) throw new Error('Append cannot claim idempotency for this repeated-payload scenario.');
    integer(task.output_rows, 'Output rows', 0, 1000000);
    identifier(task.resource_pool);
    if (!Object.hasOwn(workflow.pools, task.resource_pool)) throw new Error(`Unknown resource pool on ${task.id}.`);
    if (!Array.isArray(task.outcomes) || !task.outcomes.length || task.outcomes.length > 10) throw new Error('Provide 1–10 authored outcomes.');
    for (const outcome of task.outcomes) {
      if (outcome === 'success') continue;
      record(outcome, 'Authored failure outcome');
      if (!['transient', 'deterministic', 'timeout'].includes(outcome.type) || typeof outcome.message !== 'string' || !outcome.message.trim()) throw new Error('Invalid authored failure outcome.');
    }
    identifiers(task.inputs, 'Task input assets'); identifiers(task.outputs, 'Task output assets', true);
    for (const input of task.inputs) if (!assets.has(input)) throw new Error(`Unknown input asset ${input}.`);
    for (const output of task.outputs) {
      if (assets.get(output)?.producer_task_id !== task.id) throw new Error(`Output ${output} must name ${task.id} as its producer.`);
    }
  }
  for (const asset of workflow.assets) {
    identifier(asset.id);
    if (!asset.id || !asset.name) throw new Error('Asset identity required.');
    if (asset.producer_task_id !== null && !tasks.get(asset.producer_task_id)?.outputs.includes(asset.id)) throw new Error(`Unknown/inconsistent producer on ${asset.id}.`);
  }
  identifiers(workflow.asset_triggers, 'Asset triggers', true);
  if (workflow.asset_triggers.some(a => !assets.has(a) || assets.get(a)!.producer_task_id !== null)) throw new Error('Asset triggers must refer to external source assets.');
}
