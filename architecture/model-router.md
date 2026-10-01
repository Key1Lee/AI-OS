# Py.Dev model boundary

## Existing architecture and scope

Before this implementation, the shared AI-OS layer had no executable Py.Dev
harness, model router, or provider contract. It now has a shared model boundary
and a thin runtime for inherited configuration and validated local runs.
Toptal-Testing owns an independent Qwen/OpenAI evaluator,
OpenAI interviewer, deterministic rubric, evidence store, and tests. Northstar
owns n8n workflows, schemas, and offline validation. These project contracts
remain unchanged. Existing project applications have not been migrated.

## Runtime path

```text
Py.Dev workflow (owns state, tools, permissions, and business rules)
  -> ModelRouter (selection, cloud gates, fallback, budget, audit)
  -> one provider adapter (Qwen local / OpenAI / Claude)
  -> ModelResponse
  -> schema validation and workflow's deterministic validator
  -> workflow decision
```

`ModelRequest` carries messages, system instructions, task type, context, tool
permissions, schema, reasoning level, timeout, metadata, selection, and task
constraints. `ModelResponse` carries content, parsed output, actual provider and
model, latency, token counts when available, finish/validation status, routing
decision, fallback, degraded state, error, and optional review. Provider
adapters cannot call tools or grant filesystem authority. The caller supplies
deterministic validation and controls all side effects.

The conservative capability registry is in `py_dev/capabilities.py`. It marks
tool calling and images unsupported until a workflow-owned tool loop and
adapter contract exist. Context window sizes are unknown rather than guessed.
The router rejects a request that *requires* an unsupported capability.

## Configuration

Set environment variables in the process that runs Py.Dev. Keep API keys in
the environment or a credential manager; do not commit them.

```sh
export DEFAULT_BRAIN=qwen
export QWEN_ENABLED=true
export QWEN_BASE_URL=http://127.0.0.1:8080/v1
export QWEN_MODEL='your-loaded-Qwen-model-alias'
export QWEN_QUANTIZATION=Q4_K_M

# Explicit paid access. Both ENABLED and ALLOW flags are required.
export OPENAI_ENABLED=false
export ALLOW_OPENAI=false
export OPENAI_MODEL='your-configured-openai-model'
export CLAUDE_ENABLED=false
export ALLOW_CLAUDE=false
export CLAUDE_MODEL='your-configured-claude-model'

# Automatic cloud routing and fallback stay off until explicitly enabled.
export ALLOW_CLOUD_ESCALATION=false
export CLOUD_CALL_BUDGET=0
```

Qwen is the model; llama.cpp is the local GGUF inference runtime. The installed
model in this workspace uses `Q4_K_M`; set the environment variable to match
your loaded file when using `ModelRouter` directly. Start a local `llama-server` bound to loopback with
the selected Qwen GGUF file, then set `QWEN_MODEL` to its served model ID or
alias. The adapter accepts only a loopback HTTP URL and uses
`/v1/chat/completions`. `QWEN_QUANTIZATION` is audit metadata, not a check of
the file's actual quantization. The local server and model file are not managed
by this package.

OpenAI uses the optional `openai` Python SDK, `OPENAI_API_KEY`, and the
configured Responses API model. Claude uses the optional `anthropic` Python
SDK, `ANTHROPIC_API_KEY`, and the configured Messages API model. Install those
SDKs only when enabling the corresponding provider. No current model name is
embedded in the router.

`CLOUD_CALL_BUDGET` is a daily UTC cap on attempted cloud calls. It is reserved
atomically before the API request and is not refunded after a failed request,
because that request may have incurred cost. When settings come from the
environment, the shared ledger defaults to
`~/.config/py-dev/cloud-budget.json`; override with `CLOUD_BUDGET_FILE` if
needed. A direct `ModelSettings(...)` instance without `cloud_budget_file`
uses an in-memory cap for that router instance. Budgeting counts calls, not
provider currency charges or tokens.

The default audit file for environment settings is
`~/.config/py-dev/model-audit.jsonl`; override with `MODEL_AUDIT_FILE`. Each
attempt records safe identifiers, provider/model, routing mode/reason,
fallback, runtime/quantization, UTC request time, status, latency, and
validation status. Prompts, context, arbitrary metadata, API keys, and response
bodies are not logged. If audit recording fails, execution reports degraded
operation and does not make another provider call.
Direct `ModelSettings(...)` construction should supply an audit sink or file;
without one, events go to the application's `py_dev.model_audit` logger.

## Routing and overrides

- `auto` selects Qwen for general work. Coding, implementation, debugging, code
  review, and SQL prefer OpenAI. Architecture critique, requirements review,
  document analysis, and second opinion prefer Claude. Automatic cloud use
  requires the provider flags, a remaining budget, and
  `ALLOW_CLOUD_ESCALATION=true`; otherwise the local policy applies.
- `brain=qwen|openai|claude` is a per-task manual override. It wins over workflow
  and task defaults, subject to privacy, offline, enabled-provider, budget, and
  capability gates.
- Private or offline requests are local-only, including fallback and review.
- Provider failure or invalid model output tries the configured eligible
  fallback order. The response reports the originally selected provider and
  actual provider. No eligible provider returns an explicit degraded response.
- A domain validator failure stops the workflow; another model cannot override
  a deterministic authorization or invariant failure.

Set `PY_DEV_POLICY_FILE=/absolute/path/policy.json` to change task preferences,
workflow overrides, or fallback order without editing routing code. Example:

```json
{
  "task_preferences": {"coding": "openai", "architecture_critique": "claude"},
  "workflow_overrides": {"offline-interview-trainer": "qwen_local", "architecture-audit": "claude"},
  "fallback_order": {"qwen_local": ["openai", "claude"]}
}
```

### CLI

From the AI-OS root, `python3 -m py_dev status --brain auto` shows the resolved
provider, model, and Qwen runtime/quantization. For a one-task
override, pass `--brain qwen`, `--brain openai`, or `--brain claude` to `status`
or `run`. `run` reads the prompt from standard input:

```sh
python3 -m py_dev status --brain qwen
python3 -m py_dev run --brain qwen --task-type general < prompt.txt
python3 -m py_dev run --brain auto --task-type coding --workflow repo-implementation < prompt.txt
```

`--private` and `--offline` impose local-only routing. `--review-with claude`
requests a separate, budgeted second opinion. Review is never automatic; a
failed review remains visible without replacing a valid primary response.
The projectless legacy `run --brain auto --task-type ...` form keeps the
original task/workflow routing policy. Runs with `--project` or `--task` use
the inherited AI-OS runtime configuration described in [runtime.md](runtime.md).

### Workflow integration

```python
from py_dev import ModelRequest, ModelRouter, ModelSettings

def validate_business_rules(request, response):
    # Run workflow-owned checks. Raise if a permission, schema, or invariant fails.
    ...

router = ModelRouter(ModelSettings.from_env(), validator=validate_business_rules)
result = router.run(ModelRequest(
    messages=({"role": "user", "content": "Analyze the supplied task"},),
    task_id="task-123",
    workflow="my-workflow",
    task_type="general",
    brain="auto",
))
if result.degraded:
    # Use a workflow-owned deterministic fallback, or report unavailability.
    ...
```

Structured output supports a fail-closed subset of JSON Schema: object root,
properties, required, additionalProperties, arrays/items, primitive types,
enum, and basic length and numeric bounds. Unsupported keywords raise before
invocation. Model output is parsed and validated locally even when an adapter
requests JSON mode or schema-constrained output. Domain-specific invariants
belong in the supplied validator.

## Current limits

- The shared runtime resolves configuration and invokes models, but a full
  workflow engine, durable memory implementation, and tool router do not exist
  in this repository. Toptal-Testing and Northstar retain their own runtimes.
- No tool calls, image inputs, provider-managed conversation state, or
  capability discovery are implemented. Context limits and exact model
  capabilities need configuration or measurement before hard enforcement.
- The daily call cap is not a monetary spend ceiling. Provider billing and
  token prices are not queried. A workflow needing a financial ceiling must
  add a separate billing-aware policy.
- No live Qwen, OpenAI, or Claude invocation is part of the automated tests.

The adapter API choices follow the official
[llama.cpp server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md),
[OpenAI Responses](https://developers.openai.com/api/docs/guides/structured-outputs),
and [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create)
documentation. Runtime behavior still depends on the installed server, SDK,
and configured model versions.
