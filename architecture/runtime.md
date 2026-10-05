# AI-OS local runtime

## Boundaries

```text
AI-OS shared defaults
  -> selected provider/model profile
  -> optional project configuration
  -> task profile
  -> per-run override
  -> Py.Dev runtime
  -> model router / provider adapter / model
  -> deterministic validation and run trace
```

The runtime owns configuration resolution, local startup checks, context
planning, model invocation, and non-secret traces. Project applications own
business rules, durable project state, authorization, and their own workflow
steps. Toptal's provider consumers now delegate transport, credentials, budgets
and metadata to AI-OS while retaining domain interfaces. Other projects can adopt
[the shared intelligence contracts](../docs/ai-os/intelligence-plane.md).

## Configuration inheritance

Global defaults are in [`config/defaults.toml`](../config/defaults.toml).
Provider profiles live in `config/providers/`. TOML uses the Python standard
library; no configuration framework or YAML dependency is required. The
resolver merges nested settings in this exact order:

1. global defaults
2. selected provider profile
3. `projects/<name>/aios.toml`, if it exists
4. the named task profile
5. environment and explicit per-run settings (explicit arguments win)

The final provider is determined before its provider profile is applied. A
project without `aios.toml` inherits defaults. Toptal-Testing's small
[`aios.toml`](<../projects/Toptal-Testing System/aios.toml>) changes only its output
preference and defines four task profiles. Northstar has no project runtime
file and inherits the global configuration unchanged.

To override one project setting, add only that table and field to its
`aios.toml`. For example:

```toml
inherits = ["global"]
[project]
name = "MyProject"
[generation]
max_output_tokens = 4096
```

Do not copy the complete defaults file. Invalid providers, reasoning names,
tiers, output limits, project names, and weakened least-privilege policy fail
before invocation. A run may request tools, but only a workflow can authorize
them; the shared runtime currently has no tool executor and rejects nonempty
tool requests. `IntelligenceService` separately coordinates bounded native
OpenAI/Claude proposals through explicitly authorized workflow-owned handlers.

## Local Qwen startup

The provider profile defaults to `qwen_local`. It discovers one Qwen GGUF in
`~/.local/share/ai-os/models`, or uses an explicit `AIOS_QWEN_GGUF_PATH` /
per-run `model_path`. It discovers `llama-server` on `PATH` or in common local
install locations. No machine-specific path is committed to configuration.

`python3 -m py_dev serve` starts a loopback server at the provider endpoint
with the configured default context, one parallel slot, and
`--no-context-shift`. `python3 -m py_dev check` checks the GGUF header,
quantization and native context metadata, binary/version and devices,
`/health`, `/v1/models`, `/props`, loaded model
identity and path, current context, template capabilities, and a synthetic
reasoning-budget probe. The runtime refuses to send work when these checks
fail. To select a different installed model, set `AIOS_QWEN_GGUF_PATH` and
restart the server with that file. `QWEN_MODEL` and `QWEN_BASE_URL` remain
supported environment overrides.

`llama.cpp` is the inference runtime. Qwen is the model. GGUF is the file
format; quantization is read from the GGUF header. A Metal device and
the active server's GPU-layer argument are detected when available. The
runtime refuses to claim GPU offload or a reasoning feature from an
unverified flag alone.

## Context policy

The global policy has tiers of 16,384 (`small`), 32,768 (`standard`), 65,536
(`large`), and 131,072 (`very_large`) tokens. These are policy choices, not
claims that a model or server can handle all tiers. The runtime chooses the
smallest tier that fits its prompt estimate, configured output allowance,
verified reasoning allowance, and safety margin. An explicit tier is honored
only if it fits. The ceiling is the minimum of the configured maximum, model
metadata context, and running server context. A request for 65,536 or 131,072
therefore fails against a server running at 32,768, with a diagnostic that
explains how to change the runtime safely.

System instructions, the active task, project-supplied critical state, session
messages, and supplied relevant retrieval results are all included in the
estimate. The shared runtime does not silently drop or summarize any of them.
If the request cannot fit, it rejects the run. Projects may supply a retrieval
component that selects relevant documents first; no index or retrieval engine
is implied by the `retrieval.enabled` default. Actual prompt/output token
counts are taken from the provider response when available and added to the
trace. Token estimation is conservative but is not a tokenizer guarantee; the
local server must run with context shifting disabled.

## Reasoning policy

`none`, `low`, `medium`, `high`, and `xhigh` are AI-OS semantic profiles. The
default is `medium`. Configured Qwen starting budgets are 0, 1,024, 4,096,
8,192, and 16,384 tokens, respectively. They do not represent OpenAI's
proprietary reasoning effort. The runtime checks the active Qwen chat template
for `enable_thinking` and `reasoning_effort` support, and tests whether the
server actually enforces a zero-token reasoning budget. When verified, it
sends the configured budget. Otherwise, it uses the supported thinking on/off
control and traces `reasoning_method=thinking_toggle` with
`reasoning_budget_enforced=false`. Higher semantic profiles do not grant tools
or filesystem permissions.

**Context size and reasoning effort are separate.** Context is the amount of
information available in one active request. Reasoning controls model
thinking where supported. Neither stores durable memory. `SessionState`
contains temporary conversation history; project-owned stores hold durable
facts, decisions, assessment evidence, and artifacts. Toptal-Testing already
stores weakness and evaluation records in its structured project data rather
than relying on Qwen conversation context.

## Runs, verification, and traces

The existing `python3 -m py_dev run` command accepts project, task, and
per-run overrides without editing global or project files:

```sh
python3 -m py_dev check --project Toptal-Testing
python3 -m py_dev run --project Toptal-Testing --task rapid_recall \
  --reasoning none --max-output 64 < prompt.txt
```

Use `--brain`, `--model`, `--context`, `--reasoning`, `--max-output`,
`--tool`, or `--no-verification` for a single run. Hard workflow validation
remains active even when optional verification is disabled. A workflow can
supply an optional verifier; a failed result can trigger a cloud specialist
only when central `external_escalation.enabled`, provider allow flags, and the
cloud-call budget all permit it. The default is false. A task's label alone
never triggers escalation.

Run traces default to `~/.config/py-dev/run-traces.jsonl` (override with
`AIOS_TRACE_FILE`). They record project, task, provider and exact model,
context tier, estimated and actual token counts when available, reasoning
profile and effective method, tool-call count, verification result, latency,
escalation decision, and error class. They omit prompts, project-state
contents, retrieved text, response bodies, and API keys. The model router
also records per-attempt audit metadata as described in
[model-router.md](model-router.md).

## Current limits

- Toptal uses shared provider transport; the other listed applications have not
  all adopted intelligence calls. Project persistent stores remain authoritative.
- Retrieval indexing and conversation summarization remain integration points.
  Bounded tools exist through `IntelligenceService`; the legacy runtime CLI
  grants no repository/shell authority. Context overflow fails
  explicitly.
- The local reasoning budget is used only when a live capability probe
  verifies it. Otherwise the on/off thinking control is used, and the budget
  value is advisory in configuration and tracing.
- Cloud provider context limits and reasoning mappings require their own
  model-specific capability profiles before strict cross-provider enforcement.

The local server checks follow the official
[llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).
