# Enterprise HR reference — run, inspect, verify

The latest [interactive engineering layer](testing-layer-guide.md) adds timed
stage/source/rule inspectors, SQLite runtime records, switchable failures and
actual backend test buttons to this same portal. Current execution evidence is
in [testing-layer-verification.md](testing-layer-verification.md).

The new `app.main` entrypoint implements the supplied enterprise master prompt
inside the existing `policy_assistant` package. It uses SQLite, mock Slack and
Workday, governed JSONL policies, deterministic routing/search and exact source
answers. It needs no Docker, Qwen server, paid key, or hosted database.

The earlier `app.api` entrypoint still serves the pgvector/n8n/Qwen policy app on
8810. This enterprise reference serves on **8811**, with an independent SQLite
file. The learner-owned exercises remain separate. No code-completion milestone
is evidence of learner mastery.

## Exact setup commands

From this checkout:

```sh
cd /Users/key/_AI-OS/projects/peopleops-ai/policy_assistant
uv sync --frozen
uv run python -m ingestion.run_pipeline
uv run uvicorn app.main:app --host 127.0.0.1 --port 8811 --no-access-log
```

Open <http://127.0.0.1:8811/>. The portal's explicitly fictional identity selector
lets you compare US/UK applicability, department groups, HR delegation and denials.
Answers show the source, correlation ID, component trace and requirement IDs.
`../Start-Enterprise-HR.command` runs the same application. Stop it with Control-C.

The requested standard Python workflow is also supported (Python **3.12**):

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m ingestion.run_pipeline
uvicorn app.main:app --host 127.0.0.1 --port 8811 --no-access-log
```

In a second terminal after installing dependencies:

```sh
pytest -v
python -m evals.run_evaluations
```

Or use `make verify` to run static checks, tests/coverage, evaluations and release
gates together. `make run`, `make ingest`, `make test`, and `make evaluate` are
shortcuts. `uv sync --frozen` uses the checked-in lock; pip resolves the stated
dependency ranges. The application uses only SQLite in this mode despite the
preserved pgvector adapter libraries being installed in the same package.

The mock settings are in `config/app.yaml` and use `HR_` environment overrides;
for example `HR_DATABASE_PATH`, `HR_AS_OF_DATE`, `HR_DEMO_MODE` and
`HR_SLACK_SIGNING_SECRET`. The demo's date is deliberately **2026-10-20** for
reproducibility. Balances are labeled synthetic and show their actual source date.
Set `HR_DEMO_MODE=false` to disable public fixture identities and demo credentials;
real SSO is an integration interface, not an implemented login system.

## Three core requests

```sh
curl -sS http://127.0.0.1:8811/ask \
  -H 'Authorization: Bearer demo-employee-us' \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is the parental leave policy?"}'

curl -sS http://127.0.0.1:8811/ask \
  -H 'Authorization: Bearer demo-employee-us' \
  -H 'Content-Type: application/json' \
  -d '{"question":"How many PTO days do I have remaining?"}'

curl -sS http://127.0.0.1:8811/ask \
  -H 'Authorization: Bearer demo-employee-us' \
  -H 'Content-Type: application/json' \
  -d '{"question":"Show me the PTO balance of EMP200."}'
```

The expected behaviors are: a **US policy citation**, exactly **12.5 days as of
2026-10-20**, and a **generic denial before any Workday method is called**.
These tokens are intentionally public synthetic credentials; never use them in
a real HR service. Other fixture tokens and grants are in `mock_data/employees.json`.

Run the same requests through the actual signed mock Slack HTTP endpoint:

```sh
uv run python scripts/demo_enterprise.py 'What is the parental leave policy?'
uv run python scripts/demo_enterprise.py 'How many PTO days do I have remaining?'
uv run python scripts/demo_enterprise.py 'Show me the PTO balance of EMP200.'
```

The simulator signs exact bytes, adds timestamp/HMAC headers and supplies a
separate mock enterprise bearer session. A signed Slack user ID alone is
insufficient. This is a mock enterprise-session binding, not an invented claim
about Slack OAuth or proprietary Workday APIs. Signature verification follows
[Slack's official HMAC instructions](https://docs.slack.dev/authentication/verifying-requests-from-slack/).
Responses are returned over HTTP; no real Slack messages are sent.

## Contracts and component inspection

Read [the elementary function tour](enterprise-functions.md) for a short explanation
of each core function and why the major test layers exist.

`POST /ask` and `/chat` accept only `{question}` plus a bearer session.
`POST /slack/events` accepts the supplied signed event envelope. Successful
business handling uses HTTP 200 with `answered`, `denied`, `abstained`, `clarify`,
`escalated`, `refused` or `unavailable`; authentication/permissions/input/rate/storage
errors use 401/403/422/429/503. Oversized bodies use 413 and event conflicts 409.

`POST /admin/ingest` needs `policy:ingest`; it reads only the configured local
registry/source paths, not paths supplied in HTTP. `/health`,
`/admin/observability` and `/admin/audit/{request_id}` need `audit:read`.
`/live` is public process liveness only. `/openapi.json` exposes the machine-readable
API schema; the portal works with no CDN-based documentation assets.

```sh
curl -sS http://127.0.0.1:8811/admin/observability \
  -H 'Authorization: Bearer demo-admin'
# Substitute the request_id from an actual response:
curl -sS http://127.0.0.1:8811/admin/audit/REQUEST_ID \
  -H 'Authorization: Bearer demo-admin'
```

A response's `trace` identifies the component path; `requirement_ids` links to
the BRD and tests. Audit events record the chosen workflow, authorization decision,
source status, attempts and timings, without questions, balances, identifiers or
credentials. Console audit messages are JSON. Index freshness is exposed in the
admin metrics. Stored request receipts contain the authorized synthetic response
for up to 24 hours, with no raw question; they are not the redacted audit log.

## Ingestion and version changes

`mock_data/registry.jsonl` is the independent approval inventory.
`mock_data/documents/policies.jsonl` contains 22 policy source records and one
malformed example. The pipeline checks metadata and content digests, rejects
seven invalid/lifecycle/injection sources, and indexes 16 approved versions.
Current retrieval still filters roles, country, groups, classification and dates.
An index entry never overrides those checks or makes source instructions trusted.

Identical reprocessing yields 16 `unchanged` records. Changes need a new governed
version and digest. The `test_current_versions` test demonstrates a 2.2 update and
a subsequent restricted 2.3 version with no fallback to the old public version.
Removed inventory membership denies old indexed content. Chunk-size changes
replace derived chunks transactionally without creating duplicate documents.
Oversized files, malformed records and unsupported content fail or quarantine
with safe reason codes; the entire run rolls back if immutable authority changes.

## Evaluation and CI

The independently authored labels live in four JSONL datasets:
42 routing, 19 retrieval, 26 answer and 18 security cases (**105** total).
The pytest cases exercise isolated functions, integrations, security and signed
Slack end-to-end behavior. Their coverage scope is the new runtime and shared
guards/chunking helpers; the old policy API is a separate regression target.

`reports/evaluation.json` includes numerators, denominators, failed-case IDs,
Recall@5, Precision@5, MRR, coverage, citation validity, exact PTO correctness,
observed exposure counts, appropriate abstention and labeled accepted facts.
`extractive_support` means exact source-backed output, not a comprehensive semantic
groundedness score. The optional LLM judge is separate and cannot grant access or
overrule hard release/security gates:

```sh
# Optional, uses an already running local Qwen server; not needed by CI:
uv run python -m evals.run_evaluations --judge-qwen
```

Ranking experiments use TF-IDF versus overlap and 120 versus 600 character chunks.
The report records their actual effects on retrieval quality and context volume;
do not infer a universal best configuration from this small corpus.
Latency p50/p95/p99 comes from 40 measured in-process HTTP requests, with 16
additional concurrent requests. Actual simulated faults include 503, timeout,
missing/stale/wrong-owner/malformed records, 429/retry exhaustion, conflicts,
duplicates and authentication failures.

Release gates require current passing tests and matching source fingerprints;
stale coverage alone cannot certify changed code. Rerun `pytest` after changing
implementation, labels, fixtures or configuration. Reports are reproducible ignored
runtime artifacts; summarized observed results are in `docs/enterprise-verification.md`.

The project workflow `.github/workflows/ci.yaml` supports a standalone checkout.
The AI-OS checkout also has a path-scoped root workflow at
`/Users/key/_AI-OS/.github/workflows/peopleops-enterprise.yaml`. Both install locked
dependencies, perform static checks, run the test layers, enforce evaluation and
coverage/traceability gates, and upload reports. No cloud credentials or model
network access are required. These workflows are configured; GitHub execution is
not claimed until they actually run on GitHub.

## Required artifacts and remaining decisions

- `requirements/`: BRD, exact criteria, access matrix, traceability CSV,
  assumptions and stakeholder decision log.
- `app/`, `ingestion/`, `mock_data/`, `evals/`, `tests/`: working source and fixtures.
- `docs/enterprise-architecture.md`: diagrams, contracts and trust boundaries.
- `docs/enterprise-readiness.md`: implemented controls, proposed SLOs, gaps,
  alerts, incident handling and rollback.
- `reports/`: actual coverage, JUnit, traceability, evaluation, release and live
  response artifacts. `requirements/traceability.csv` maps every requirement
  to actual code/test functions; the report flags both untested requirements
  and tests without requirements.

Terraform is intentionally omitted because this request needs no cloud resources.
This is an operational local reference, with production identity, queueing,
retention, encryption, real adapter contracts and stakeholder approvals still open.
