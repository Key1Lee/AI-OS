# Executed verification · 2026-10-19

## Local Qwen update · 2026-10-20

- `python3 -m py_dev check`: loaded **Qwen3-4B-Q4_K_M**, Q4_K_M GGUF,
  llama.cpp, 32,768 runtime context, 40,960 model context, Apple M1 Max Metal
  device detected, context shifting disabled, thinking toggle available.
- Mac `127.0.0.1:8080/health`: ready. Docker
  `host.docker.internal:8080/health`: **200**. Server remains bound to loopback.
- Host `uv run pytest`: **61 passed**, 1 Starlette deprecation warning,
  **1.99 seconds**. Includes five added local URL/structured-output checks.
  These tests use mocks and do not need the real model.
- `uv run python scripts/smoke.py` with real Qwen configured: **19 passed**.
  The live PTO chat returned the exact Requests passage from version 2 and
  `mode: LLM: qwen_local · embeddings: mock`.
- Host startup helper was exercised from a stopped runtime: it launched the
  existing AI-OS server command and returned `Started local Qwen`. Reuse was
  separately checked without replacing a running model.
- n8n Assistant UI: local OpenAI-compatible endpoint connection test succeeded;
  saved base URL and Qwen alias remained after reload. No API key was supplied.
  Sandbox and web search remain unset; no autonomous code-execution claim is made.
- PeopleOps browser: confirmed `Local Qwen connected`, submitted PTO through
  `/chat`, and observed the version 2 Requests citation. Screenshot: `chat-qwen.png`.
- Registry validation passed for 11 systems after recording the AI-OS runtime
  dependency. Launcher syntax and Compose configuration checks passed.
- Model and application services remain running for the user's self-hosted setup.
  The test DB is a separate disposable service.

The sections below retain the original mock-only implementation evidence.
The prior “no live model calls” statement describes that earlier run, not this
local-Qwen update. See [local Qwen configuration](local-qwen.md).

These are observed results, not expected counts. No paid model key was used.

| Check | Actual result |
| --- | --- |
| First PTO vertical slice, real PostgreSQL | **1 passed** before expanding the implementation |
| Final host `uv run pytest` | **56 passed**, 1 warning, 1.97 seconds |
| Final Docker `python -m pytest -o cache_dir=/tmp/pytest-cache` | **56 passed**, 1 warning, 1.60 seconds |
| `uv run python scripts/smoke.py` against running Compose | **19 passed**, including actual n8n webhook execution |
| Desktop browser | Connected generated employee token; submitted PTO question through `/chat`; received version 2; expanded exact citation |
| Mobile browser, 390px viewport | No horizontal document overflow; readable source; payroll question returned human handoff and “No ticket has been created” |
| Learner exercise preservation | SHA-256 comparison of **14 files**, **0 changed** |
| Registry validation | **Passed**, 11 systems |
| Compose configuration and Python compilation | **Passed** |
| Local secret exclusions | `.env` and `access-tokens.json` confirmed ignored by Git |

Host Python was **3.12.13**; container Python was **3.12.15**. Database was
**PostgreSQL 17.11**, extension **pgvector 0.8.7**. Runtime dependencies are locked
in `uv.lock` and hash-pinned in `requirements.txt`; n8n **2.43.7** and the database
image are pinned by digest in Compose.

The one pytest warning is Starlette's deprecation of its current httpx-based
TestClient path. It did not skip or fail tests. No live external LLM or embedding
service was exercised; the OpenAI-compatible request/response contract was tested
with `httpx.MockTransport`. Default word-hash vectors are explicitly mock vectors,
not proof of semantic-model quality.

## What the tests establish

- Versioned Markdown parsing, heading-aware bounded chunks, exact source text,
  idempotent replay, concurrent replay, immutable version conflict, and whole-batch
  rollback when a later document conflicts.
- PTO, benefits enrollment, parental leave, remote work, and payroll support.
- Token authentication; rejected role/region overrides; admin-only ingestion and
  both health routes; tenant isolation and role/region filtering.
- Authorization before top-k with a restricted perfect-match decoy at k=1;
  forbidden source IDs never reach the selector.
- Current-version citation, future-version exclusion, expired/withdrawn handling,
  and no fallback to an old public ACL after a current restriction.
- Abstention with absent or merely related evidence; personal balances,
  eligibility, coverage, salary, medical records, and payroll escalation before
  provider calls; obvious question/document prompt injection defenses.
- Fabricated and duplicate citation rejection; exact answer/source agreement;
  provider timeouts and invalid JSON; no model-authored free-text answer field.
- Vector dimension/finite-value validation, embedding-space isolation and
  reindexing; oversized streamed request rejection; safe validation errors.
- Live n8n status and structured-result forwarding, including unauthenticated
  webhook rejection, US/GB separation, HR-only evidence, and escalation.

## Reproduce

From the `policy_assistant/` directory after configuration:

```sh
docker compose up --build -d --wait
uv run python scripts/ingest.py
docker compose --profile test up -d test-db --wait
uv run pytest
docker compose run --rm \
  -e TEST_DATABASE_URL=postgresql://test:test-local-only@test-db:5432/peopleops_policy_test \
  api python -m pytest -o cache_dir=/tmp/pytest-cache
uv run python scripts/smoke.py
```

The host and container tests use the same dedicated test DB; run them sequentially.
The app database retains ingested policies and older embedding spaces. The smoke
script also proves identical re-ingestion does not create another document.

Earlier failures were fixed and rerun: a generic-word mismatch in the mock,
plural medical-record detection, request/open synonym handling, and a missing
workflow file in the first container image. The initial container result was
55 passes and one packaging failure; the corrected container result above is
the final evidence. No learner exercise was completed by these changes.

## Browser evidence

![Desktop chat with a current, expanded PTO citation](chat-desktop.png)

[Mobile chat screenshot](chat-mobile.png)

## Scope limits

These checks establish the fictional local slice. They are not a production
security audit, load test, live-provider quality evaluation, or real HR integration
test. The original SQLite and training application suites were not rerun because
their implementation files were not changed. Their historical results remain in
their own verification documents.

Local application and test services are stopped after verification; named policy
and n8n volumes are retained. Use the launcher or setup commands to restart.

## Additive Qualtrics test orchestrator — 2026-10-20

The current local stack is running for the user's inspection. A separate
`../survey_analytics` service and published n8n workflow `qualtricsGold01` now
demonstrate synthetic survey data flowing through durable Bronze, Silver and
Gold SQLite layers. The original HR workflow and its execution-saving settings
were preserved. After the n8n import/restart, `uv run python scripts/smoke.py`
was actually rerun: **19 passed**. The new lab also passed 16 temporary-database
tests and 7 real webhook/persistence smoke checks. Full evidence, metric
definitions and limitations are in
[survey orchestrator verification](../../survey_analytics/docs/verification.md).
No real Qualtrics or Samsara integration is claimed.
