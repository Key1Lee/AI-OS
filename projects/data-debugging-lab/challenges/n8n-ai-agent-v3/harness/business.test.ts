import { BaseChatModel } from '@langchain/core/language_models/chat_models';
import { AIMessage, type BaseMessage } from '@langchain/core/messages';
import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';
import { createServer } from 'node:http';
import { mkdirSync, readFileSync, writeFileSync, appendFileSync } from 'node:fs';
import { join } from 'node:path';
import type { EngineRequest, EngineResponse, IExecuteFunctions } from 'n8n-workflow';
import { AgentV3 } from '../source/n8n/packages/@n8n/nodes-langchain/nodes/agents/Agent/V3/AgentV3.node';

type BusinessRequest = {
  request_id: string; employee_id: string; service: string;
  instruction: string; payload: Record<string, string>;
};
const requests: BusinessRequest[] = JSON.parse(readFileSync('/lab/fixtures/requests.json', 'utf8'));
const artifactDir = process.env.LAB_ARTIFACT_DIR!;
mkdirSync(artifactDir, { recursive: true });
function save(name: string, data: unknown) {
  writeFileSync(join(artifactDir, name), JSON.stringify(data, null, 2) + '\n');
}
function event(data: unknown) {
  appendFileSync(join(artifactDir, 'events.jsonl'), JSON.stringify(data) + '\n');
}
function snapshot(value: unknown) { return JSON.parse(JSON.stringify(value)); }
function decodeObservation(content: string): Record<string, unknown>[] {
  const parsed = JSON.parse(content);
  return Array.isArray(parsed) ? parsed : [parsed];
}

// A deterministic model boundary. Decisions depend on the actual messages received
// from n8n; no agent implementation, intermediate state, or tool history is mocked.
class RecordedBusinessModel extends BaseChatModel {
  serial = 0;
  promptAudit: Array<{ request_id: string; referenced_request_ids: unknown[] }> = [];
  constructor() { super({}); }
  _llmType() { return 'local-business-fixture'; }
  bindTools() { return this; }
  async _generate(messages: BaseMessage[]) {
    const human = messages.find((m) => m._getType() === 'human');
    const request: BusinessRequest = JSON.parse(String(human?.content));
    const observations = messages.filter((m) => m._getType() === 'tool').flatMap((m) => {
      try { return decodeObservation(String(m.content)); } catch { return []; }
    });
    const own = observations.filter((o) => o.request_id === request.request_id && o.ok === true);
    const references = [
      ...observations.map((o) => o.request_id),
      ...messages.flatMap((m) => m instanceof AIMessage ? m.tool_calls?.map((c) => c.args.request_id) ?? [] : []),
    ];
    this.promptAudit.push({ request_id: request.request_id, referenced_request_ids: references });
    const receipt = own.find((o) => o.operation === 'apply');
    const authorization = own.find((o) => o.operation === 'inspect');
    const message = receipt
      ? new AIMessage({ content: JSON.stringify({ request_id: request.request_id, status: 'complete', receipt: receipt.receipt }) })
      : new AIMessage({ content: '', tool_calls: [{
          name: request.service,
          args: {
            operation: authorization ? 'apply' : 'inspect',
            request_id: request.request_id, employee_id: request.employee_id,
            ...(authorization ? {
              authorization: authorization.authorization,
              idempotency_key: request.request_id + ':apply', payload: request.payload,
            } : {}),
          },
          id: request.request_id + ':call:' + (++this.serial), type: 'tool_call',
        }] });
    event({ kind: 'model', request_id: request.request_id,
      messages: messages.map((m) => ({ ...snapshot(m), message_type: m._getType() })),
      response: snapshot(message) });
    return { generations: [{ message, text: String(message.content) }] };
  }
}

async function runBusiness(selected: BusinessRequest[]) {
  const effects: Record<string, unknown>[] = [];
  const apiCalls: Record<string, unknown>[] = [];
  const committed = new Map<string, Record<string, unknown>>();
  const server = createServer(async (req, res) => {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const input = JSON.parse(Buffer.concat(chunks).toString());
    const principal = req.headers['x-employee-id'];
    const expected = requests.find((r) => r.request_id === input.request_id);
    const authorized = !!expected && principal === expected.employee_id &&
      input.employee_id === expected.employee_id && req.url === '/' + expected.service;
    let output: Record<string, unknown>;
    let status = 200;
    if (!authorized) {
      status = 403;
      output = { ok: false, request_id: input.request_id, error: 'authorization_denied' };
    } else if (input.operation === 'inspect') {
      output = { ok: true, operation: 'inspect', request_id: input.request_id,
        employee_id: expected.employee_id, authorization: 'local-grant:' + input.request_id };
    } else if (input.operation === 'apply' &&
      input.authorization === 'local-grant:' + input.request_id &&
      input.idempotency_key === input.request_id + ':apply' &&
      JSON.stringify(input.payload) === JSON.stringify(expected.payload)) {
      const prior = committed.get(input.idempotency_key);
      output = prior ?? { ok: true, operation: 'apply', request_id: input.request_id,
        employee_id: expected.employee_id, receipt: 'receipt:' + input.request_id };
      if (!prior) {
        committed.set(input.idempotency_key, output);
        effects.push({ service: expected.service, ...input, receipt: output.receipt });
      }
    } else {
      status = 422;
      output = { ok: false, request_id: input.request_id, error: 'invalid_operation_or_grant' };
    }
    const audit = { principal, path: req.url, input, status, output };
    apiCalls.push(audit); event({ kind: 'mock_api', ...audit });
    res.writeHead(status, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(output));
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('No local mock address');
  const url = 'http://127.0.0.1:' + address.port;
  const model = new RecordedBusinessModel();
  const tools = ['hr_service', 'survey_service'].map((name) => new DynamicStructuredTool({
    name, description: 'Inspect authorization, then apply the requested local synthetic service action.',
    schema: z.object({ operation: z.enum(['inspect', 'apply']), request_id: z.string(),
      employee_id: z.string(), authorization: z.string().optional(),
      idempotency_key: z.string().optional(), payload: z.record(z.string()).optional() }),
    func: async () => { throw new Error('Tools must be scheduled through the engine boundary'); },
  }));
  const node = { id: 'business-agent', name: 'Employee Service Agent',
    type: '@n8n/n8n-nodes-langchain.agent', typeVersion: 3, position: [0, 0], parameters: {} };
  const options = { batchSize: Number(process.env.LAB_BATCH_SIZE ?? 2), maxIterations: 5,
    returnIntermediateSteps: true, enableStreaming: false, autoSaveHighlightedData: false,
    passthroughBinaryImages: false,
    systemMessage: 'Process each independent request. Inspect its authorization, apply exactly one action, and return its receipt.' };
  const context = {
    getInputData: () => selected.map((json) => ({ json })),
    getNode: () => node, getWorkflow: () => ({ id: 'local-business', name: 'Local synthetic services' }),
    getExecutionId: () => 'local-' + (process.env.LAB_SCENARIO ?? 'pair'),
    getExecuteData: () => ({}), getExecutionCancelSignal: () => new AbortController().signal,
    getParentCallbackManager: () => undefined,
    getNodeParameter: (key: string, i: number, fallback?: unknown) => {
      if (key === 'text') return JSON.stringify(selected[i]);
      if (key === 'promptType') return 'define';
      if (key === 'hasOutputParser' || key === 'needsFallback') return false;
      if (key === 'options') return { ...options };
      if (key === 'options.batching.batchSize') return options.batchSize;
      if (key === 'options.batching.delayBetweenBatches') return 0;
      if (key.startsWith('options.')) return options[key.slice(8) as keyof typeof options] ?? fallback;
      return fallback;
    },
    getInputConnectionData: async (kind: string) => kind === 'ai_languageModel' ? model : kind === 'ai_tool' ? tools : undefined,
    getParentNodes: () => tools.map((tool) => ({ name: tool.name })),
    continueOnFail: () => false, isStreaming: () => false,
    setMetadata: (metadata: unknown) => event({ kind: 'execution_metadata', metadata }),
    logger: Object.fromEntries(['debug', 'info', 'warn', 'error'].map((level) =>
      [level, (...args: unknown[]) => event({ kind: 'log', level, args })])),
    customData: { set: () => {} },
  } as unknown as IExecuteFunctions;
  let response: EngineResponse | undefined;
  let result: unknown;
  try {
    for (let round = 0; round < 8; round++) {
      event({ kind: 'agent_invocation', round, response: snapshot(response ?? null) });
      result = await AgentV3.prototype.execute.call(context, response);
      save('agent-round-' + round + '.json', result);
      if (Array.isArray(result)) break;
      const request = result as EngineRequest;
      if (!request.actions) throw new Error('Unexpected agent protocol');
      const actionResponses = [];
      for (const action of request.actions) {
        const index = Number(action.metadata?.itemIndex);
        const principal = selected[index]?.employee_id ?? 'unknown';
        const started = Date.now();
        const reply = await fetch(url + '/' + action.nodeName, { method: 'POST',
          headers: { 'Content-Type': 'application/json', 'x-employee-id': principal },
          body: JSON.stringify(action.input) });
        const output = await reply.json();
        actionResponses.push({ action, data: { data: { ai_tool: [[{ json: output }]] },
          startTime: started, executionTime: Date.now() - started, executionIndex: round, source: [] } });
      }
      // Match the engine's request/response protocol; pass metadata through unchanged.
      response = { actionResponses, metadata: request.metadata };
      save('engine-response-' + round + '.json', response);
    }
    save('output.json', result);
    save('effects.json', effects); save('api-calls.json', apiCalls);
    save('inputs.json', selected); save('options.json', options);
    return { result, effects, apiCalls, promptAudit: model.promptAudit };
  } catch (error) {
    const failure = error instanceof Error ? { name: error.name, message: error.message, stack: error.stack } : { message: String(error) };
    save('failure.json', failure);
    return { result, effects, apiCalls, promptAudit: model.promptAudit, failure };
  } finally {
    save('effects.json', effects); save('api-calls.json', apiCalls);
    save('inputs.json', selected); save('options.json', options);
    save('prompt-audit.json', model.promptAudit);
    await new Promise<void>((resolve, reject) => server.close((err) => err ? reject(err) : resolve()));
  }
}

test('record and reconcile the independent employee-service business contract', async () => {
  const scenario = process.env.LAB_SCENARIO ?? 'pair';
  const selected = scenario === 'single-hr' ? requests.slice(0, 1)
    : scenario === 'single-survey' ? requests.slice(1) : requests;
  const { result, effects, apiCalls, promptAudit, failure } = await runBusiness(selected);
  const outputs = Array.isArray(result) ? result[0] : [];
  const checks = selected.map((request, index) => {
    const item = outputs.find((o: { pairedItem?: { item: number } }) => o.pairedItem?.item === index);
    let completion;
    try { completion = JSON.parse(item?.json?.output); } catch { completion = undefined; }
    const steps = item?.json?.intermediateSteps ?? [];
    const ownEffects = effects.filter((e) => e.request_id === request.request_id);
    return { request_id: request.request_id,
      complete: completion?.request_id === request.request_id && completion?.status === 'complete',
      action_consistent: ownEffects.length === 1 && completion?.receipt === ownEffects[0]?.receipt,
      history_complete: steps.filter((s: { observation?: string }) => {
        try { return decodeObservation(s.observation ?? '{}').every((o) => o.request_id === request.request_id); } catch { return false; }
      }).length === 2,
      history_isolated: steps.every((s: { observation?: string }) => {
        try { return decodeObservation(s.observation ?? '{}').every((o) => o.request_id === request.request_id); } catch { return false; }
      }),
      prompt_isolated: promptAudit.filter((p) => p.request_id === request.request_id)
        .every((p) => p.referenced_request_ids.every((id) => id === request.request_id)),
      exactly_one_effect: ownEffects.length === 1,
    };
  });
  const summary = { scenario, requests: selected.length, outputs: outputs.length,
    checks, authorization_denials: apiCalls.filter((c) => c.status !== 200).length,
    execution_error: failure?.message ?? null,
    all_contracts_met: !failure && outputs.length === selected.length &&
      apiCalls.every((c) => c.status === 200) && checks.every((c) =>
        c.complete && c.action_consistent && c.history_complete && c.history_isolated && c.prompt_isolated && c.exactly_one_effect) };
  save('reconciliation.json', summary);
  expect(summary.all_contracts_met, 'Business contract not satisfied; inspect the recorded evidence').toBe(true);
});
