export const TASK_STATES = ['WAITING', 'READY', 'RUNNING', 'SUCCESS', 'FAILED', 'RETRYING', 'BLOCKED', 'SKIPPED'] as const;
export type TaskStatus = typeof TASK_STATES[number];
export type ErrorType = 'transient' | 'deterministic' | 'timeout';
export type Stage = 'ingest' | 'staging' | 'transform' | 'mart' | 'dashboard';
export type TriggerRule = 'all_success' | 'all_done' | 'one_success';
export type Timezone = 'Asia/Seoul' | 'UTC';
export interface RetryPolicy { max_attempts: number; delay_minutes: number; retryable_errors: ErrorType[] }
export interface TaskError { type: ErrorType; message: string }
export interface TaskDefinition {
  id: string; name: string; purpose: string; stage: Stage;
  dependencies: string[]; trigger: 'workflow'; trigger_rule: TriggerRule;
  duration_minutes: number; timeout_minutes: number; retry_policy: RetryPolicy;
  inputs: string[]; outputs: string[]; idempotent: boolean | 'unknown';
  outcomes: ('success' | TaskError)[]; enabled: boolean; resource_pool: string;
  write_mode: 'replace' | 'append'; output_rows: number;
}
export interface AssetDefinition {
  id: string; name: string; producer_task_id: string | null;
  model_reference?: { id: string; grain: unknown; materialization: unknown };
}
export interface WorkflowDefinition {
  id: string; name: string; purpose: string; tasks: TaskDefinition[]; assets: AssetDefinition[];
  schedule: { frequency: 'daily'; time: string; timezone: Timezone };
  asset_triggers: string[]; pools: Record<string, number>; expected_ready_time: string;
}
export type RunTrigger = { kind: 'daily' } | { kind: 'manual' } | { kind: 'asset'; asset_id: string };
export type OutputStore = Record<string, Record<string, number>>;
export interface RunOptions {
  partition: string; clock_date?: string; start_minute?: number; run_id?: string;
  trigger?: RunTrigger; max_concurrency?: number; initial_outputs?: OutputStore;
}
export interface Attempt {
  attempt: number; status: 'RUNNING' | 'SUCCESS' | 'FAILED';
  start_time: string; end_time: string | null; duration: number | null;
  start_minute: number; end_minute: number | null; error: TaskError | null;
}
export interface TaskExecution {
  task_id: string; status: TaskStatus; start_time: string | null; end_time: string | null;
  duration: number | null; execution_attempt: number; error: TaskError | null;
  next_retry_minute: number | null; attempts: Attempt[]; blocked_by: string[];
}
export interface ExecutionEvent {
  contract_version: 'orchestration-event-v1'; event_id: string; run_id: string;
  workflow_id: string; task_id: string; asset_id: string | null; status: TaskStatus;
  attempt: number; occurred_at: string; start_time: string | null; end_time: string | null;
  duration: number | null; error_type: ErrorType | null; error_message: string | null;
  partition: string; upstream_state: Record<string, TaskStatus>;
}
export interface SimulationRun {
  run_id: string; workflow_id: string; partition: string; clock_date: string; now: number;
  timezone: Timezone; trigger: RunTrigger; max_concurrency: number;
  status: 'WAITING' | 'RUNNING' | 'SUCCESS' | 'FAILED'; activated: boolean; complete: boolean;
  start_time: string | null; end_time: string | null;
  tasks: Record<string, TaskExecution>; events: ExecutionEvent[]; outputs: OutputStore;
}
export interface ScenarioContract {
  contract_version: 'orchestration-scenario-v1'; id: string; title: string; brief: string;
  workflow: WorkflowDefinition; default_partition: string; evidence_task_ids: string[];
  learner_questions: string[];
}
export interface ReadinessExplanation {
  title: string; detail: string; waiting_for: string[];
  dependencies: { id: string; status: TaskStatus; satisfied: boolean }[];
}
export interface OrchestratorAdapter {
  vendor: 'Airflow' | 'Dagster' | 'Prefect' | 'dbt jobs';
  normalize(source: unknown): WorkflowDefinition;
}
export const AIRFLOW_CONCEPTS = {
  Workflow: 'DAG', Task: 'Task', Dependency: 'upstream / downstream',
  'Historical processing': 'backfill', Retry: 'retry policy', Schedule: 'timetable / schedule',
  'Data dependency': 'asset',
} as const;
