import { createRun, runningCount, settleRun } from './simulator';
import { integer, validateDate, validateWorkflow } from './validation';
import type { SimulationRun, WorkflowDefinition } from './types';
import { record } from './guards';

export interface PartitionRecord { partition: string; status: 'SUCCESS' | 'FAILED' | 'MISSING'; rows: number | null }
export interface BackfillItem { partition: string; action: 'RUN' | 'SKIP'; reason: string; existing: PartitionRecord | null }
export interface BackfillPlan { start: string; end: string; today: string; mode: 'missing' | 'replace'; items: BackfillItem[] }
export interface BackfillResult {
  source_workflow: WorkflowDefinition;
  options: { execution_id: string; workers: number; partition_concurrency: number; fail_partition?: string };
  plan: BackfillPlan; runs: SimulationRun[]; partitions: PartitionRecord[];
  peak_workers: number; peak_partitions: number; total_minutes: number;
}

export const EXAMPLE_PARTITIONS: PartitionRecord[] = [
  ...['2026-09-27', '2026-09-28', '2026-09-29'].map(partition => ({ partition, status: 'MISSING' as const, rows: null })),
  { partition: '2026-09-30', status: 'SUCCESS', rows: 100 },
  { partition: '2026-10-01', status: 'SUCCESS', rows: 100 },
  { partition: '2026-10-02', status: 'SUCCESS', rows: 100 },
];

export function planBackfill(start: string, end: string, today: string, existing: PartitionRecord[], mode: 'missing' | 'replace' = 'missing'): BackfillPlan {
  [start, end, today].forEach(validateDate);
  if (start > end) throw new Error('Backfill start must be on or before the end.');
  if (end >= today) throw new Error('Backfill targets historical dates before today.');
  if (!['missing', 'replace'].includes(mode)) throw new Error('Unknown replacement mode.');
  const days = (Date.parse(`${end}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`)) / 86400000 + 1;
  integer(days, 'Backfill days', 1, 31);
  const records = new Map<string, PartitionRecord>();
  if (!Array.isArray(existing)) throw new Error('Existing partitions must be an array.');
  for (const record of existing) {
    validateDate(record.partition);
    if (records.has(record.partition)) throw new Error('Partition records must be unique.');
    if (!['SUCCESS', 'FAILED', 'MISSING'].includes(record.status)) throw new Error('Invalid partition status.');
    if (record.rows !== null) integer(record.rows, 'Partition rows', 0, Number.MAX_SAFE_INTEGER);
    records.set(record.partition, record);
  }
  const items: BackfillItem[] = [];
  for (let day = 0; day < days; day++) {
    const partition = new Date(Date.parse(`${start}T00:00:00Z`) + day * 86400000).toISOString().slice(0, 10);
    const record = records.get(partition) ?? null;
    const skip = mode === 'missing' && record?.status === 'SUCCESS';
    items.push({ partition, action: skip ? 'SKIP' : 'RUN', existing: record ? structuredClone(record) : null,
      reason: skip ? 'Already successful; keep existing output.' : record?.status === 'SUCCESS'
        ? 'Explicit replacement of successful output.' : record?.status === 'FAILED' ? 'Reprocess a failed partition.' : 'Fill a missing partition.' });
  }
  return { start, end, today, mode, items };
}

export function simulateBackfill(workflow: WorkflowDefinition, plan: BackfillPlan, options: { execution_id: string; workers?: number; partition_concurrency?: number; fail_partition?: string }): BackfillResult {
  record(options, 'Backfill options');
  if (typeof options.execution_id !== 'string' || !options.execution_id.trim() || options.execution_id.length > 160) throw new Error('Backfill execution ID requires 1–160 nonblank characters.');
  validateWorkflow(workflow); record(plan, 'Backfill plan');
  if (!Array.isArray(plan.items)) throw new Error('Backfill plan items must be an array.');
  // Recompute the plan to reject a mutated/forged plan at the execution boundary.
  const canonical = planBackfill(plan.start, plan.end, plan.today, plan.items.flatMap(i => i.existing ? [i.existing] : []), plan.mode);
  if (JSON.stringify(canonical) !== JSON.stringify(plan)) throw new Error('Backfill plan is inconsistent.');
  if (plan.mode === 'replace' && plan.items.some(i => i.action === 'RUN') && workflow.tasks.some(t => t.enabled && t.outputs.length && t.write_mode === 'append')) {
    throw new Error('Partition replacement requires replacement writes. This workflow appends and can duplicate rows; choose a replacement workflow.');
  }
  if (options.workers !== undefined) integer(options.workers, 'Backfill workers', 1, 8);
  if (options.partition_concurrency !== undefined) integer(options.partition_concurrency, 'Concurrent partitions', 1, 8);
  const workers = options.workers ?? 2, parallel = options.partition_concurrency ?? 2;
  integer(workers, 'Backfill workers', 1, 8); integer(parallel, 'Concurrent partitions', 1, 8);
  if (options.fail_partition !== undefined && !plan.items.some(i => i.partition === options.fail_partition && i.action === 'RUN')) throw new Error('Failure injection must target a partition that will run.');
  const queue = plan.items.filter(i => i.action === 'RUN');
  const runs: SimulationRun[] = [], active: { run: SimulationRun; workflow: WorkflowDefinition }[] = [];
  let next = 0, now = 360, peakWorkers = 0, peakPartitions = 0;
  for (let tick = 0; tick < 100000; tick++, now++) {
    // Complete all due work before reassigning any global worker/pool slot.
    for (const entry of active) { entry.run.now = now; settleRun(entry.run, entry.workflow, false); }
    for (let i = active.length - 1; i >= 0; i--) if (active[i].run.complete) active.splice(i, 1);
    while (active.length < parallel && next < queue.length) {
      const item = queue[next++], partitionWorkflow = structuredClone(workflow);
      if (item.partition === options.fail_partition) (partitionWorkflow.tasks.find(t => t.stage === 'mart') ?? partitionWorkflow.tasks.at(-1)!).outcomes = [{ type: 'deterministic', message: 'Authored failure for this partition only.' }];
      const outputs = Object.fromEntries(workflow.assets.filter(a => a.producer_task_id !== null).map(a => [a.id, item.existing?.rows !== null && item.existing?.rows !== undefined ? { [item.partition]: item.existing.rows } : {}]));
      const run = createRun(partitionWorkflow, { partition: item.partition, clock_date: plan.today, start_minute: 360,
        trigger: { kind: 'manual' }, run_id: `backfill:${options.execution_id}:${item.partition}`, max_concurrency: workers, initial_outputs: outputs });
      run.now = now; runs.push(run); active.push({ run, workflow: partitionWorkflow });
      settleRun(run, partitionWorkflow, false);
    }
    peakPartitions = Math.max(peakPartitions, active.length);
    for (const entry of active) {
      const others = active.filter(a => a !== entry);
      const occupied = others.reduce((sum, a) => sum + runningCount(a.run), 0);
      const pools = Object.fromEntries(Object.entries(workflow.pools).map(([pool, limit]) => [pool, limit - others.reduce((sum, a) => sum + a.workflow.tasks.filter(t => t.resource_pool === pool && a.run.tasks[t.id].status === 'RUNNING').length, 0)]));
      settleRun(entry.run, entry.workflow, true, workers - occupied, pools);
    }
    peakWorkers = Math.max(peakWorkers, active.reduce((sum, a) => sum + runningCount(a.run), 0));
    if (next === queue.length && active.every(a => a.run.complete)) {
      const partitions = plan.items.map(item => {
        if (item.action === 'SKIP') return structuredClone(item.existing!);
        const run = runs.find(r => r.partition === item.partition)!;
        const mart = workflow.tasks.find(t => t.stage === 'mart') ?? workflow.tasks.at(-1)!;
        return { partition: item.partition, status: run.status === 'SUCCESS' ? 'SUCCESS' as const : 'FAILED' as const,
          rows: run.outputs[mart.outputs[0]]?.[item.partition] ?? null };
      });
      return { source_workflow: structuredClone(workflow), options: { execution_id: options.execution_id, workers, partition_concurrency: parallel, ...(options.fail_partition ? { fail_partition: options.fail_partition } : {}) },
        plan: structuredClone(plan), runs, partitions, peak_workers: peakWorkers, peak_partitions: peakPartitions, total_minutes: now - 360 };
    }
  }
  throw new Error('Backfill exceeded the bounded virtual clock.');
}
