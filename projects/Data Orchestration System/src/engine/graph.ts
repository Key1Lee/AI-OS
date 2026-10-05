import type { WorkflowDefinition } from './types';
import { identifier, identifiers, record } from './guards';

export function topologicalOrder(workflow: WorkflowDefinition): string[] {
  record(workflow, 'Workflow');
  const tasks = workflow.tasks;
  if (!Array.isArray(tasks)) throw new Error('Workflow tasks must be an array.');
  if (!tasks.length || tasks.length > 100) throw new Error('A workflow needs 1–100 tasks.');
  for (const task of tasks) {
    record(task, 'Task'); identifier(task.id); identifiers(task.dependencies, `Dependencies on ${task.id}`);
  }
  const byId = new Map(tasks.map(t => [t.id, t]));
  if (byId.size !== tasks.length) throw new Error('Task IDs must be unique.');
  const indegrees = new Map(tasks.map(t => [t.id, t.dependencies.length]));
  const children = new Map(tasks.map(t => [t.id, [] as string[]]));
  for (const task of tasks) {
    if (new Set(task.dependencies).size !== task.dependencies.length) throw new Error(`Duplicate dependency on ${task.id}.`);
    for (const parent of task.dependencies) {
      if (!byId.has(parent)) throw new Error(`Unknown dependency ${parent} on ${task.id}.`);
      children.get(parent)!.push(task.id);
    }
  }
  // Always choose the first eligible task in definition order, including after a merge.
  const order: string[] = [];
  const used = new Set<string>();
  while (order.length < tasks.length) {
    const next = tasks.find(t => !used.has(t.id) && indegrees.get(t.id) === 0);
    if (!next) throw new Error('Cycle detected: dependencies must form a DAG.');
    used.add(next.id); order.push(next.id);
    for (const child of children.get(next.id)!) indegrees.set(child, indegrees.get(child)! - 1);
  }
  return order;
}

export function downstream(workflow: WorkflowDefinition, taskId: string): string[] {
  if (!workflow.tasks.some(t => t.id === taskId)) throw new Error(`Unknown task ${taskId}.`);
  const affected = new Set([taskId]);
  return topologicalOrder(workflow).filter(id => {
    if (id === taskId) return false;
    if (workflow.tasks.find(t => t.id === id)!.dependencies.some(d => affected.has(d))) {
      affected.add(id); return true;
    }
    return false;
  });
}

export function criticalPath(workflow: WorkflowDefinition): { tasks: string[]; minutes: number } {
  // Nominal execution assumes enabled attempts succeed. Skip/block reachability
  // still follows the real trigger rules: a skipped parent cannot satisfy an OR
  // join, and skipping is immediate rather than inheriting upstream duration.
  const best = new Map<string, { tasks: string[]; minutes: number; can_succeed: boolean }>();
  let longest = { tasks: [] as string[], minutes: 0 };
  for (const id of topologicalOrder(workflow)) {
    const task = workflow.tasks.find(t => t.id === id)!;
    const parents = task.dependencies.map(p => best.get(p)!);
    const canSucceed = task.enabled && (!parents.length || task.trigger_rule === 'all_done'
      || (task.trigger_rule === 'one_success' ? parents.some(p => p.can_succeed) : parents.every(p => p.can_succeed)));
    const candidates = task.trigger_rule === 'one_success' ? parents.filter(p => p.can_succeed) : parents;
    const parent = task.trigger_rule === 'one_success' && candidates.length
      ? candidates.reduce((a, b) => b.minutes < a.minutes ? b : a)
      : candidates.reduce((a, b) => b.minutes > a.minutes ? b : a, { tasks: [] as string[], minutes: 0, can_succeed: true });
    const result = canSucceed
      ? { tasks: [...parent.tasks, id], minutes: parent.minutes + task.duration_minutes, can_succeed: true }
      : { tasks: [] as string[], minutes: 0, can_succeed: false };
    best.set(id, result);
    if (result.minutes > longest.minutes) longest = { tasks: result.tasks, minutes: result.minutes };
  }
  return longest;
}
