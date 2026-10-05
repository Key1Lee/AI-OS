import { TASK_STATES } from './types';

const id = { type: 'string', minLength: 1, maxLength: 200 };
const date = { type: 'string', pattern: '^\\d{4}-\\d{2}-\\d{2}$' };
const nullableTime = { anyOf: [{ type: 'string', pattern: '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(Z|\\+09:00)$' }, { type: 'null' }] };
const error = { type: 'object', additionalProperties: false, required: ['type', 'message'], properties: { type: { enum: ['transient', 'deterministic', 'timeout'] }, message: { type: 'string', minLength: 1 } } };
const task = {
  type: 'object', additionalProperties: false,
  required: ['id', 'name', 'purpose', 'stage', 'dependencies', 'trigger', 'trigger_rule', 'duration_minutes', 'timeout_minutes', 'retry_policy', 'inputs', 'outputs', 'idempotent', 'outcomes', 'enabled', 'resource_pool', 'write_mode', 'output_rows'],
  properties: {
    id, name: id, purpose: { type: 'string', minLength: 1 }, stage: { enum: ['ingest', 'staging', 'transform', 'mart', 'dashboard'] },
    dependencies: { type: 'array', uniqueItems: true, items: id }, trigger: { const: 'workflow' }, trigger_rule: { enum: ['all_success', 'all_done', 'one_success'] },
    duration_minutes: { type: 'integer', minimum: 1, maximum: 10000 }, timeout_minutes: { type: 'integer', minimum: 1, maximum: 10000 },
    retry_policy: { type: 'object', additionalProperties: false, required: ['max_attempts', 'delay_minutes', 'retryable_errors'], properties: {
      max_attempts: { type: 'integer', minimum: 1, maximum: 10 }, delay_minutes: { type: 'integer', minimum: 1, maximum: 1000 },
      retryable_errors: { type: 'array', uniqueItems: true, items: { enum: ['transient', 'timeout'] } } } },
    inputs: { type: 'array', items: id }, outputs: { type: 'array', uniqueItems: true, items: id },
    idempotent: { enum: [true, false, 'unknown'] }, outcomes: { type: 'array', minItems: 1, maxItems: 10, items: { anyOf: [{ const: 'success' }, error] } },
    enabled: { type: 'boolean' }, resource_pool: id, write_mode: { enum: ['replace', 'append'] }, output_rows: { type: 'integer', minimum: 0, maximum: 1000000 },
  },
};
export const workflowSchema = {
  type: 'object', additionalProperties: false, required: ['id', 'name', 'purpose', 'tasks', 'assets', 'schedule', 'asset_triggers', 'pools', 'expected_ready_time'],
  properties: {
    id, name: id, purpose: { type: 'string' }, tasks: { type: 'array', minItems: 1, maxItems: 100, items: task },
    assets: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['id', 'name', 'producer_task_id'], properties: {
      id, name: id, producer_task_id: { anyOf: [id, { type: 'null' }] },
      model_reference: { type: 'object', required: ['id', 'grain', 'materialization'], additionalProperties: false, properties: { id, grain: {}, materialization: {} } },
    } } },
    schedule: { type: 'object', additionalProperties: false, required: ['frequency', 'time', 'timezone'], properties: {
      frequency: { const: 'daily' }, time: { type: 'string', pattern: '^([01]\\d|2[0-3]):[0-5]\\d$' }, timezone: { enum: ['Asia/Seoul', 'UTC'] },
    } },
    asset_triggers: { type: 'array', uniqueItems: true, items: id }, pools: { type: 'object', minProperties: 1, additionalProperties: { type: 'integer', minimum: 1, maximum: 8 } },
    expected_ready_time: { type: 'string', pattern: '^([01]\\d|2[0-3]):[0-5]\\d$' },
  },
};
export const executionEventSchema = {
  $schema: 'http://json-schema.org/draft-07/schema#', $id: 'urn:data-orchestration-lab:execution-event:v1',
  title: 'ExecutionEvent', type: 'object', additionalProperties: false,
  required: ['contract_version', 'event_id', 'run_id', 'workflow_id', 'task_id', 'asset_id', 'status', 'attempt', 'occurred_at', 'start_time', 'end_time', 'duration', 'error_type', 'error_message', 'partition', 'upstream_state'],
  properties: {
    contract_version: { const: 'orchestration-event-v1' }, event_id: id, run_id: id, workflow_id: id, task_id: id,
    asset_id: { anyOf: [id, { type: 'null' }] }, status: { enum: TASK_STATES }, attempt: { type: 'integer', minimum: 0, maximum: 10 },
    occurred_at: { ...nullableTime, anyOf: [nullableTime.anyOf[0]] }, start_time: nullableTime, end_time: nullableTime,
    duration: { anyOf: [{ type: 'integer', minimum: 0 }, { type: 'null' }] }, error_type: { enum: ['transient', 'deterministic', 'timeout', null] },
    error_message: { type: ['string', 'null'] }, partition: date, upstream_state: { type: 'object', additionalProperties: { enum: TASK_STATES } },
  },
};
export const scenarioSchema = {
  $schema: 'http://json-schema.org/draft-07/schema#', $id: 'urn:data-orchestration-lab:scenario:v1', title: 'OrchestrationScenario',
  type: 'object', additionalProperties: false, required: ['contract_version', 'id', 'title', 'brief', 'workflow', 'default_partition', 'evidence_task_ids', 'learner_questions'],
  properties: { contract_version: { const: 'orchestration-scenario-v1' }, id, title: id, brief: { type: 'string', minLength: 1 },
    workflow: workflowSchema, default_partition: date, evidence_task_ids: { type: 'array', uniqueItems: true, items: id },
    learner_questions: { type: 'array', minItems: 1, items: { type: 'string', minLength: 1 } } },
};
