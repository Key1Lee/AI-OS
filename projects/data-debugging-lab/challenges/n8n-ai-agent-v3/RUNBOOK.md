# Commands and evidence

Run all commands from `/Users/key/_AI-OS/projects/data-debugging-lab/challenges/n8n-ai-agent-v3`.

| Command | Purpose |
| --- | --- |
| `./scripts/lab setup` | Verify/retrieve the pinned source, build the image, frozen dependency install, compile prerequisites |
| `./scripts/lab versions` | Execute pinned Node and pnpm inside the offline runtime |
| `./scripts/lab unit` | Run eight original Agent V3 test files, one worker |
| `./scripts/lab run pair` | Execute and reconcile both business requests; current baseline exits 1 |
| `./scripts/lab run single-hr` | Independent HR control |
| `./scripts/lab run single-survey` | Independent survey control |
| `./scripts/lab build` | Regenerate compiled prerequisites after relevant source changes |
| `./scripts/lab shell` | Open an interactive shell in the same offline container |

`image` and `install` are also available separately. No `up`, external service, browser, model API key, SQL, or dbt command is required for this track. Do not run the parent track's scripts to control this one.

## Inspect a run

Every command prints its unique `evidence/<UTC>-<label>-<pid>/` directory. `command.txt`, `started.txt`, `finished.txt`, `output.log`, and `exit-code.txt` record what actually executed. Unit runs preserve fresh JUnit XML. Business runs also contain:

| Artifact under `artifacts/` | Evidence |
| --- | --- |
| `inputs.json`, `options.json` | Request identities and effective agent settings |
| `events.jsonl` | Ordered model inputs/responses, agent invocations, execution metadata, API audit |
| `agent-round-N.json` | Unchanged node outputs or outbound engine requests |
| `engine-response-N.json` | Actual mock results and unchanged metadata supplied on resume |
| `output.json` | Final node output, including intermediate steps |
| `api-calls.json`, `effects.json` | Attempted API operations versus committed effects |
| `prompt-audit.json` | Request identity references observed at the model boundary |
| `reconciliation.json` | Business assertions and execution error, if any |
| `failure.json` | Runtime exception details when execution raises |
| `junit.xml` | Test outcome |

Example inspection, substituting the directory printed by your run:

```bash
cat evidence/<your-run>/artifacts/inputs.json
cat evidence/<your-run>/artifacts/reconciliation.json
less evidence/<your-run>/artifacts/events.jsonl
```

Raw model messages retain LangChain serialization (`kwargs.content`, `kwargs.tool_calls`) plus `message_type`. Tool result content is JSON containing an array of result objects. Timestamps, temporary ports, tool-call IDs, and test durations are not deterministic assertions. Business identity, content, and effect checks are.

## Controlled configuration

`fixtures/requests.json` defines the synthetic business input. `harness/business.test.ts` contains the deterministic model, mock services, external execution adapter, and business reconciliation. `harness/vite.config.mts` extends upstream test settings without changing source. `harness/node_modules` links to the original package's installed dependencies.

The model uses the human request and actual tool-result messages it receives. It inspects authorization, requests an apply operation, then returns the actual receipt. It does not simulate a faulty agent or supply prebuilt agent history. The mock service independently validates employee identity, request/service scope, grant, payload, and idempotency key. It records all attempts and deduplicates committed actions per run. These local policies are fixture guarantees, not proof of n8n enterprise IAM or durable exactly-once delivery.

The adapter follows the upstream engine envelope: one response per requested action; original action retained; tool items under `data.ai_tool`; request metadata passed unchanged. The corresponding engine interfaces are in `packages/core/src/execution-engine/requests-response.ts` and the response assembly in `workflow-execute.ts`. This describes the harness boundary, not a diagnosis.

`LAB_BATCH_SIZE=<positive integer> ./scripts/lab run <scenario>` records an explicit batching configuration for an experiment you choose. State your prediction, control, and stopping rule before changing any setting. Do not interpret a changed outcome as a causal explanation on its own.

## Setup troubleshooting

- Docker unavailable: start Docker Desktop and retry the command. Other projects' containers are unrelated.
- Missing compiled package/module: retain the error and run `./scripts/lab build`. The public node imports compiled property metadata in addition to executable agent code.
- Missing packages: run `./scripts/lab install`, using the pinned container and frozen lockfile. Do not use host pnpm 11 or rewrite the lockfile.
- Current business assertion failure: expected baseline evidence. Read the recorded artifacts. Do not suppress assertions, alter the source pin, or upgrade dependencies as a setup workaround.
- Resource pressure: container limit is 4 GiB / 3 CPUs, Node heap 3 GiB, tests one worker, build concurrency two. No other container is stopped by these scripts.
- Checkout revision differs: setup stops and preserves it. Record your experimental revision; do not reset changes automatically.

All runs use disposable in-memory mock state. Containers remove themselves, publish no ports, mount only this track plus its pnpm cache, and have no external network during builds/tests. Image creation and dependency installation need network access. No host Docker socket or credential directory is mounted. There are no background services to stop. Durable recovery, crash restart, real provider behavior, and full workflow scheduling remain unverified.
