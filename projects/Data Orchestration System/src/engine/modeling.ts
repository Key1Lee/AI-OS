import { validateWorkflow } from './validation';
import { ecommerceWorkflow } from './scenarios';
import type { Stage, WorkflowDefinition } from './types';

// Only the Modeling project's existing public fields are read. Grain and
// materialization remain opaque source metadata, never orchestration semantics.
export interface ModelingDefinition {
  id: string; name: string; layer: 'source' | 'staging' | 'intermediate' | 'fact' | 'dimension' | 'mart' | 'metric' | 'output';
  why: string; parents: string[]; grain: unknown; materialization: unknown;
}
export interface ModelingEnvelope { contract_version: 'modeling-lab-v1'; models: ModelingDefinition[] }

export function workflowFromModels(envelope: ModelingEnvelope): WorkflowDefinition {
  if (envelope?.contract_version !== 'modeling-lab-v1' || !Array.isArray(envelope.models) || !envelope.models.length) throw new Error('Expected a modeling-lab-v1 model envelope.');
  const models = new Map(envelope.models.map(m => [m.id, m]));
  if (models.size !== envelope.models.length) throw new Error('Model IDs must be unique.');
  const stages: Record<string, Stage> = { staging: 'staging', intermediate: 'transform', fact: 'transform', dimension: 'transform', mart: 'mart', metric: 'mart', output: 'dashboard' };
  for (const model of envelope.models) {
    if (!model.id || !model.name || !model.why || !['source', ...Object.keys(stages)].includes(model.layer) || !Array.isArray(model.parents)) throw new Error('Invalid model definition.');
    for (const parent of model.parents) if (!models.has(parent)) throw new Error(`Unknown model parent ${parent}.`);
    if (model.layer === 'source' && model.parents.length) throw new Error('Source models must be external roots in this adapter.');
  }
  const defaults = ecommerceWorkflow(), template = defaults.tasks[0];
  const workflow: WorkflowDefinition = { ...defaults, id: 'imported-models', name: 'Imported modeling dependencies',
    purpose: 'Execute supplied model definitions without redefining their meaning.',
    tasks: envelope.models.filter(m => m.layer !== 'source').map(model => ({ ...structuredClone(template),
      id: `build_${model.id}`, name: `build_${model.name}`, purpose: model.why, stage: stages[model.layer],
      dependencies: model.parents.filter(p => models.get(p)!.layer !== 'source').map(p => `build_${p}`),
      inputs: [...model.parents], outputs: [model.id], duration_minutes: 1, resource_pool: 'warehouse', idempotent: 'unknown' })),
    assets: envelope.models.map(model => ({ id: model.id, name: model.name, producer_task_id: model.layer === 'source' ? null : `build_${model.id}`,
      model_reference: { id: model.id, grain: structuredClone(model.grain), materialization: structuredClone(model.materialization) } })),
    asset_triggers: envelope.models.filter(m => m.layer === 'source').map(m => m.id) };
  validateWorkflow(workflow); return workflow;
}
