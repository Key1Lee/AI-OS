import { topologicalOrder } from './graph';
import { identifier, record } from './guards';
import { clockLabel, integer, timestamp, timeMinute, validateDate, validateWorkflow } from './validation';
import type { ExecutionEvent, ReadinessExplanation, RunOptions, SimulationRun, TaskDefinition, TaskExecution, TaskStatus, WorkflowDefinition } from './types';

export const TERMINAL = new Set<TaskStatus>(['SUCCESS', 'FAILED', 'BLOCKED', 'SKIPPED']);

export function createRun(workflow: WorkflowDefinition, options: RunOptions): SimulationRun {
  validateWorkflow(workflow); record(options, 'Run options'); validateDate(options.partition);
  if (options.clock_date !== undefined) validateDate(options.clock_date);
  if (options.start_minute !== undefined) integer(options.start_minute, 'Start minute', 0, 1439);
  if (options.max_concurrency !== undefined) integer(options.max_concurrency, 'Workers', 1, 8);
  if (options.run_id !== undefined && (typeof options.run_id !== 'string' || !options.run_id.length || options.run_id.length > 180)) throw new Error('Run ID requires 1–180 characters.');
  if (options.trigger !== undefined) record(options.trigger, 'Run trigger');
  const clockDate = options.clock_date ?? options.partition; validateDate(clockDate);
  const trigger = options.trigger ?? { kind: 'daily' };
  if (!['daily', 'manual', 'asset'].includes(trigger.kind)) throw new Error('Unknown run trigger.');
  if (trigger.kind === 'asset') {
    identifier(trigger.asset_id);
    if (!workflow.asset_triggers.includes(trigger.asset_id)) throw new Error('This asset update does not trigger the workflow.');
  }
  const now = options.start_minute ?? timeMinute(workflow.schedule.time);
  integer(now, 'Start minute', 0, 1439);
  const maxConcurrency = options.max_concurrency ?? 2; integer(maxConcurrency, 'Workers', 1, 8);
  const runId = options.run_id ?? `${workflow.id}:${options.partition}:${trigger.kind}:1`;
  if (typeof runId !== 'string' || !runId.length || runId.length > 180) throw new Error('Run ID requires 1–180 characters.');
  if (options.initial_outputs !== undefined) record(options.initial_outputs, 'Stored outputs');
  const outputs = structuredClone(options.initial_outputs ?? {});
  for (const [asset, partitions] of Object.entries(outputs)) {
    record(partitions, 'Stored asset partitions');
    if (!workflow.assets.some(a => a.id === asset)) throw new Error(`Unknown stored asset ${asset}.`);
    for (const [partition, rows] of Object.entries(partitions)) { validateDate(partition); integer(rows, 'Stored row count', 0, Number.MAX_SAFE_INTEGER); }
  }
  const tasks: Record<string, TaskExecution> = {};
  for (const task of workflow.tasks) tasks[task.id] = {
    task_id: task.id, status: 'WAITING', start_time: null, end_time: null, duration: null,
    execution_attempt: 0, error: null, next_retry_minute: null, attempts: [], blocked_by: [],
  };
  return { run_id: runId, workflow_id: workflow.id, partition: options.partition, clock_date: clockDate,
    now, timezone: workflow.schedule.timezone, trigger, max_concurrency: maxConcurrency,
    status: 'WAITING', activated: false, complete: false, start_time: null, end_time: null, tasks, events: [], outputs };
}

function transition(run: SimulationRun, workflow: WorkflowDefinition, definition: TaskDefinition, status: TaskStatus): void {
  const task = run.tasks[definition.id]; task.status = status;
  const event: ExecutionEvent = {
    contract_version: 'orchestration-event-v1', event_id: `${run.run_id}:${run.events.length + 1}`,
    run_id: run.run_id, workflow_id: workflow.id, task_id: task.task_id,
    asset_id: definition.outputs[0] ?? null, status, attempt: task.execution_attempt,
    occurred_at: timestamp(run.clock_date, run.now, run.timezone), start_time: task.start_time,
    end_time: task.end_time, duration: task.duration,
    error_type: task.error?.type ?? null, error_message: task.error?.message ?? null,
    partition: run.partition,
    upstream_state: Object.fromEntries(definition.dependencies.map(d => [d, run.tasks[d].status])),
  };
  run.events.push(event);
}

function dependencyStatus(run: SimulationRun, definition: TaskDefinition): 'ready' | 'waiting' | 'blocked' {
  const states = definition.dependencies.map(d => run.tasks[d].status);
  if (!states.length) return 'ready';
  if (definition.trigger_rule === 'all_done') return states.every(s => TERMINAL.has(s)) ? 'ready' : 'waiting';
  if (definition.trigger_rule === 'one_success') {
    if (states.includes('SUCCESS')) return 'ready';
    return states.every(s => TERMINAL.has(s)) ? 'blocked' : 'waiting';
  }
  if (states.some(s => TERMINAL.has(s) && s !== 'SUCCESS')) return 'blocked';
  return states.every(s => s === 'SUCCESS') ? 'ready' : 'waiting';
}

export function runningCount(run: SimulationRun): number {
  return Object.values(run.tasks).filter(t => t.status === 'RUNNING').length;
}

// Used by the backfill coordinator in two passes: complete all partitions before
// assigning the shared worker budget. Callers operate on their own cloned state.
export function settleRun(run: SimulationRun, workflow: WorkflowDefinition, allowStarts = true, capacity = run.max_concurrency, poolCaps = workflow.pools): void {
  if (run.complete) return;
  if (!run.activated) {
    if (run.trigger.kind === 'daily' && run.now < timeMinute(workflow.schedule.time)) return;
    run.activated = true; run.status = 'RUNNING'; run.start_time = timestamp(run.clock_date, run.now, run.timezone);
  }
  const order = topologicalOrder(workflow);
  const byId = new Map(workflow.tasks.map(t => [t.id, t]));
  for (const id of order) {
    const task = run.tasks[id], definition = byId.get(id)!;
    if (task.status !== 'RUNNING') continue;
    const attempt = task.attempts.at(-1)!;
    const duration = Math.min(definition.duration_minutes, definition.timeout_minutes);
    task.duration = run.now - attempt.start_minute;
    if (run.now < attempt.start_minute + duration) continue;
    const outcome = definition.outcomes[Math.min(task.execution_attempt - 1, definition.outcomes.length - 1)];
    const error = definition.duration_minutes > definition.timeout_minutes
      ? { type: 'timeout' as const, message: `Exceeded ${definition.timeout_minutes} minute timeout.` }
      : outcome === 'success' ? null : { ...outcome };
    task.end_time = timestamp(run.clock_date, run.now, run.timezone); task.error = error;
    attempt.end_time = task.end_time; attempt.end_minute = run.now; attempt.duration = task.duration;
    attempt.error = error; attempt.status = error ? 'FAILED' : 'SUCCESS';
    if (!error) {
      for (const output of definition.outputs) {
        const stored = run.outputs[output] ??= {};
        const rows = definition.write_mode === 'append' ? (stored[run.partition] ?? 0) + definition.output_rows : definition.output_rows;
        if (!Number.isSafeInteger(rows)) throw new Error('Output count exceeds safe integer range.');
        stored[run.partition] = rows;
      }
      transition(run, workflow, definition, 'SUCCESS');
    } else {
      transition(run, workflow, definition, 'FAILED');
      if (task.execution_attempt < definition.retry_policy.max_attempts && definition.retry_policy.retryable_errors.includes(error.type)) {
        task.next_retry_minute = run.now + definition.retry_policy.delay_minutes;
        transition(run, workflow, definition, 'RETRYING');
      }
    }
  }
  // Topological traversal propagates terminal blocks without blocking retrying parents.
  for (const id of order) {
    const task = run.tasks[id], definition = byId.get(id)!;
    if (task.status === 'RETRYING' && run.now >= task.next_retry_minute!) {
      task.next_retry_minute = null; transition(run, workflow, definition, 'READY');
    }
    if (task.status !== 'WAITING') continue;
    if (!definition.enabled) { task.end_time = timestamp(run.clock_date, run.now, run.timezone); transition(run, workflow, definition, 'SKIPPED'); continue; }
    const readiness = dependencyStatus(run, definition);
    if (readiness === 'ready') transition(run, workflow, definition, 'READY');
    if (readiness === 'blocked') {
      task.blocked_by = definition.dependencies.filter(d => TERMINAL.has(run.tasks[d].status) && run.tasks[d].status !== 'SUCCESS');
      task.end_time = timestamp(run.clock_date, run.now, run.timezone); transition(run, workflow, definition, 'BLOCKED');
    }
  }
  if (allowStarts) {
    let workers = runningCount(run);
    for (const id of order) {
      const task = run.tasks[id], definition = byId.get(id)!;
      if (task.status !== 'READY' || workers >= Math.min(run.max_concurrency, capacity)) continue;
      const poolUsed = workflow.tasks.filter(d => d.resource_pool === definition.resource_pool && run.tasks[d.id].status === 'RUNNING').length;
      if (poolUsed >= poolCaps[definition.resource_pool]) continue;
      task.execution_attempt++; task.error = null; task.start_time = timestamp(run.clock_date, run.now, run.timezone);
      task.end_time = null; task.duration = 0;
      task.attempts.push({ attempt: task.execution_attempt, status: 'RUNNING', start_time: task.start_time,
        end_time: null, duration: null, start_minute: run.now, end_minute: null, error: null });
      transition(run, workflow, definition, 'RUNNING'); workers++;
    }
  }
  if (Object.values(run.tasks).every(t => TERMINAL.has(t.status))) {
    run.complete = true; run.status = Object.values(run.tasks).some(t => ['FAILED', 'BLOCKED'].includes(t.status)) ? 'FAILED' : 'SUCCESS';
    run.end_time = timestamp(run.clock_date, run.now, run.timezone);
  }
}

export function nextEventMinute(run: SimulationRun, workflow: WorkflowDefinition): number {
  const candidates: number[] = [];
  if (!run.activated && run.trigger.kind === 'daily') candidates.push(timeMinute(workflow.schedule.time));
  for (const definition of workflow.tasks) {
    const task = run.tasks[definition.id];
    if (task.status === 'RUNNING') candidates.push(task.attempts.at(-1)!.start_minute + Math.min(definition.duration_minutes, definition.timeout_minutes));
    if (task.status === 'RETRYING') candidates.push(task.next_retry_minute!);
  }
  const future = candidates.filter(t => t > run.now);
  if (!future.length) throw new Error('No future event: the workflow cannot make progress.');
  return Math.min(...future);
}

export function stepSimulation(current: SimulationRun, workflow: WorkflowDefinition): SimulationRun {
  if (current.workflow_id !== workflow.id) throw new Error('Run/workflow mismatch.');
  if (current.complete) return structuredClone(current);
  const run = structuredClone(current), before = run.events.length;
  settleRun(run, workflow);
  if (!run.complete && run.events.length === before) {
    run.now = nextEventMinute(run, workflow); settleRun(run, workflow);
  }
  return run;
}

export function simulate(workflow: WorkflowDefinition, options: RunOptions): SimulationRun {
  let run = createRun(workflow, options);
  for (let step = 0; step < 5000 && !run.complete; step++) run = stepSimulation(run, workflow);
  if (!run.complete) throw new Error('Simulation exceeded the bounded event limit.');
  return run;
}

export function whyTask(run: SimulationRun, workflow: WorkflowDefinition, taskId: string): ReadinessExplanation {
  const definition = workflow.tasks.find(t => t.id === taskId);
  if (!definition) throw new Error(`Unknown task ${taskId}.`);
  const task = run.tasks[taskId];
  const dependencies = definition.dependencies.map(id => ({ id, status: run.tasks[id].status,
    satisfied: definition.trigger_rule === 'all_done' ? TERMINAL.has(run.tasks[id].status) : run.tasks[id].status === 'SUCCESS' }));
  const waitingFor = dependencies.filter(d => !d.satisfied && (definition.trigger_rule !== 'one_success' || !TERMINAL.has(d.status))).map(d => d.id);
  const explain = (title: string, detail: string, waiting_for = waitingFor) => ({ title, detail, waiting_for, dependencies });
  if (!run.activated) return explain('Waiting for the workflow trigger', run.trigger.kind === 'daily'
    ? `The daily schedule opens at ${workflow.schedule.time} ${workflow.schedule.timezone}. Being scheduled does not satisfy dependencies.`
    : 'The explicit trigger is accepted. Step or run the simulation to begin.');
  if (task.status === 'BLOCKED') return explain('Blocked by an upstream result', `${task.blocked_by.join(', ')} did not succeed. This task has never started; it did not fail itself.`, task.blocked_by);
  if (task.status === 'RETRYING') return explain('Waiting before another attempt', `Attempt ${task.execution_attempt} failed: ${task.error?.message} The next attempt becomes eligible at ${clockLabel(task.next_retry_minute!)} ${run.timezone}, after ${task.next_retry_minute! - run.now} more virtual minutes. It still needs a free worker and resource slot.`, []);
  if (task.status === 'FAILED') return explain('This task failed', `${task.error?.message} ${task.error?.type === 'deterministic' ? 'Repeating the same input cannot repair this error. Fix the task before rerunning.' : 'The retry policy has no eligible attempts left.'}`, []);
  if (task.status === 'READY') return explain('Dependencies satisfied; waiting for capacity', `A worker and a slot in the ${definition.resource_pool} pool are required. Ready is different from running.`, []);
  if (task.status === 'RUNNING') return explain('Executing now', `Attempt ${task.execution_attempt} occupies one worker. A slow task is still running until its timeout is exceeded.`, []);
  if (task.status === 'SUCCESS') return explain('Completed successfully', `Attempt ${task.execution_attempt} completed and produced ${definition.outputs.join(', ') || 'no data asset'}.`, []);
  if (task.status === 'SKIPPED') return explain('Intentionally skipped', 'This task is disabled in this workflow. All-success dependents require a successful result, even when a parent is skipped.', []);
  return explain('Waiting for dependencies', `${definition.trigger_rule === 'one_success' ? 'At least one parent must succeed.' : definition.trigger_rule === 'all_done' ? 'Every parent must reach a terminal state.' : 'Every parent must succeed.'} Still waiting for ${waitingFor.join(', ')}.`);
}

export function readinessExpectation(run: SimulationRun, workflow: WorkflowDefinition) {
  const dashboard = workflow.tasks.find(t => t.stage === 'dashboard');
  const actual = dashboard ? run.tasks[dashboard.id].attempts.at(-1)?.end_minute ?? null : null;
  const ready = dashboard ? run.tasks[dashboard.id].status === 'SUCCESS' : false;
  const expected = timeMinute(workflow.expected_ready_time);
  return { expected, actual: ready ? actual : null, delay_minutes: ready && actual !== null ? Math.max(0, actual - expected) : null };
}
