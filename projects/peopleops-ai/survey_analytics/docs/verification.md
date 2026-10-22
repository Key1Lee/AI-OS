# Local survey orchestrator verification — 2026-10-20

The current 5,000-employee dashboard and n8n collection workflow are documented
in [cohort verification](cohort-verification.md), dated 2026-10-21. The results
below retain the earlier small-fixture and load-test evidence.

Implemented as an additive synthetic lab in `survey_analytics/`. No real Qualtrics
or Samsara account is connected. No HR application source, shared provider config,
policy documents, employee fixtures, or learner exercises were edited.

## Executed checks

- `policy_assistant/.venv/bin/python -m pytest survey_analytics/tests -q --junitxml=survey_analytics/reports/tests.xml`
  from the PeopleOps project root: **16 passed**, zero failures/errors/skips;
  JUnit duration **0.544 seconds**. One existing Starlette TestClient/httpx
  deprecation warning. Tests were rerun after final API/pipeline formatting.
- `policy_assistant/.venv/bin/ruff check survey_analytics`: **all checks passed**.
  Initial lint findings were corrected before this final result.
- `docker compose up -d --wait` from the new directory: sidecar healthy using
  the existing Python 3.12 PeopleOps image and local Docker network.
- Imported `qualtrics-to-gold.json`, published workflow `qualtricsGold01`, and
  restarted the existing n8n container to register the new webhook. Existing
  named volumes and owner configuration were retained.
- Actual POST to `http://127.0.0.1:5680/webhook/qualtrics-gold-test`: HTTP 200,
  Gold ready, first run `replayed=false`. Saved as `reports/live-first-run.json`.
- Repeated actual webhook execution: same business results, `replayed=true`,
  unchanged table counts. Saved as `reports/live-replay.json`.
- `policy_assistant/.venv/bin/python -m survey_analytics.smoke`: **7 live checks
  passed** across n8n, the sidecar, and persistent SQLite; `reports/live-smoke.json`.
- Browser: opened the published workflow, fitted the canvas, selected the manual
  synthetic trigger, clicked Execute, and observed **Workflow executed successfully**
  and item counts along all seven connections. User-facing tab remains open.
  Screenshot: `docs/n8n-orchestrator.png` (captured at the existing narrow viewport).
- Original app regression smoke: `uv run python scripts/smoke.py` from
  `policy_assistant/`: **19 passed** after adding this workflow and restarting n8n.

## Durable evidence

Batch/source SHA-256:
`005a7ab5b5b05795356fb562386a0589607feecaf5a761084fbfb56fae743a88`.
Metric definition version: `survey-metrics-v1`.

| Table | Actual rows |
|---|---:|
| bronze_batches | 1 |
| bronze_responses | 14 |
| silver_responses | 12 |
| quarantine | 1 |
| gold_snapshots | 1 |

Actual Gold results: response rate 50%; completion rate 83.33%; engagement mean
3.9/5; engagement favorable 70%; CSAT 77.78%; eNPS +22.22 points; median duration
195 seconds. Question-specific denominators and quality counts are persisted in
the JSON, not filled by a language model. All department slices are withheld
because at least one group/question has fewer than five complete answers.

## Limits

This verifies a fixed, closed-cohort synthetic snapshot and real local n8n
execution. It does not verify actual Qualtrics API contracts, credentials, delayed
export polling, pagination, live survey mappings, incremental changes, a cloud
warehouse, production privacy, production access controls, hosted CI or load.
SQLite models medallion layers locally; no actual enterprise Gold warehouse was
configured. Existing 127-test enterprise evidence was not regenerated because
its implementation and fingerprint inputs were unchanged. Only the original
app's 19-check live smoke was rerun.

The inherited HR API/n8n/database/provider remain running, and the added
loopback-published survey sidecar remains available for the user's requested
inspection. Stop only that sidecar using `docker compose stop` in this directory.

## Production checklist follow-up — 2026-10-20

The user requested the n8n checklist, time tracking and MCP access. The UI saved
fixed estimated time savings of **10 minutes per production execution**. This
is a provisional 3-minute export + 3-minute cleanup + 4-minute metric-checking
assumption, not measured savings. Instance MCP was enabled and its workflow list
was verified to contain only the synthetic survey workflow; zero clients were
connected. No credentials were generated or copied. The authenticated endpoint
`/mcp-server/http` returned **401** to an unauthenticated POST.

Added a published error handler (`qualtricsGoldError01`) with Error Trigger →
local notification HTTP node. The event schema accepts only the two synthetic
workflow IDs, bounded execution IDs and fixed node names; it rejects error
messages, stacks, arbitrary nodes and HR workflow events. It commits deduplicated
events to SQLite and exposes the local `/notifications` inbox. No external
messages, email, Slack or desktop push notifications are sent.

Initial expected-versus-observed discrepancy: an intentional workflow failure
did not produce a notification. The n8n log explicitly reported that the error
workflow was inactive and could not execute. Publishing that handler, restarting
n8n and repeating the otherwise unchanged probe produced the expected event.
This establishes the missing publication as the cause. A separate startup check
also encountered a transient connection close during restart; readiness polling
now handles that transport exception within its bounded startup wait.

Actual final results:

- **18 pytest tests passed** (16 existing + two notification/export-boundary tests),
  with the same existing Starlette/httpx deprecation warning.
- Ruff: **all checks passed**.
- Actual intentionally failed execution **71** ran the error handler and delivered
  a local notification at **2026-10-20T13:05:03.191398+00:00**. Evidence:
  `reports/checklist-smoke.json`. No external messages were sent.
- The normal published webhook was rerun afterwards: **7 live checks passed**,
  with unchanged Bronze/Silver/Gold rows and all seven expected metric values.
- The original PeopleOps app smoke was rerun after the final n8n restart:
  **19 passed** (`uv run python scripts/smoke.py` in `policy_assistant`).
- `reports/workflow-checklist-export.json` proves the main workflow remains active
  with `timeSavedPerExecution=10`, `timeSavedMode=fixed`, `availableInMCP=true` and
  `errorWorkflow=qualtricsGoldError01`.
- `docs/mcp-enabled.png` shows the actual MCP workflow list. A newly opened
  workflow tab hit the browser's blocked internal error page during restart;
  it was not bypassed. Subsequent settings validation used the official local n8n
  CLI and real HTTP execution instead. The existing MCP settings tab remains open.

This verifies configuration, normal execution and notification delivery. It does
not verify an authenticated MCP client handshake, actual manual time savings,
external notifications, or production release readiness.

## Fake account and 500-request test — 2026-10-20

Implemented a public fake account/token gate on all four mock source routes:
account, export creation, export status, and export download. The layer endpoints
and test webhook retain their existing local demo behavior. The three n8n source
HTTP nodes now send the fake `X-API-TOKEN` header; existing n8n time tracking,
MCP availability and error-handler configuration are retained in the generated JSON.

Actual command, from the PeopleOps project root:

```sh
policy_assistant/.venv/bin/python -m survey_analytics.load_test --requests 500 --concurrency 20
```

The load phase began at **2026-10-20T13:09:08.390425+00:00** and sent exactly
**500 real HTTP GET requests**, using 20 in-flight slots and keep-alive, to the
local mock export download route. Five setup/auth controls were additional and
excluded from the 500-request count and timing.

| Measurement | Actual result |
|---|---:|
| HTTP 200 responses | 500 / 500 |
| Exact fixture payload hashes validated | 500 / 500 |
| Failures | 0 |
| Elapsed load phase | 1.554 seconds |
| Throughput | 321.75 requests/second |
| HTTP latency p50 / p95 / p99 | 47.719 / 145.036 / 210.045 ms |
| Maximum HTTP latency | 399.314 ms |
| Missing / incorrect fake token | 401 / 401 |
| Correct fake token account control | 200 |
| Row deliveries validated | 7,500 (500 × the same 15-row fixture) |

Latency begins after acquiring a concurrency slot and ends when the HTTP
response body is read. Percentiles use linear interpolation. Throughput includes
the complete timed load phase and payload validation. There are no automatic
retries. Report: `reports/load-test.json`; a separate actual HTTP sample is in
`reports/mock-export-sample.json`. No live Qualtrics request was made.

After the final code changes, **21 tests passed** (same existing Starlette warning),
Ruff passed, the real n8n-to-Gold smoke passed **7 checks**, and the preserved HR
app smoke passed **19 checks** after the n8n restart. The Gold table row counts
remain 1 batch, 14 Bronze versions, 12 Silver rows, one quarantine, one snapshot.

The 500 requests were reads of one fixed synthetic snapshot. They are not 500
new responses, 500 simultaneous connections, or 500 n8n workflow executions.
This does not establish production capacity, sustained-load behavior, real vendor
compatibility, token security, throttling, delayed exports or live account access.
