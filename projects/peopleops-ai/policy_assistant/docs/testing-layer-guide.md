# Interactive engineering lab

This layer extends the existing PeopleOps enterprise app on **8811**. It adds
measured execution stages, safe source/rule inspection, request-scoped fault
injection and real backend test jobs. All employees, grants and HR facts are
synthetic. It uses no paid API and does not connect to actual Slack or Workday.

## Start the application

On this Mac, run `../Start-Enterprise-HR.command`, or:

```sh
cd /Users/key/_AI-OS/projects/peopleops-ai/policy_assistant
uv sync --frozen
uv run python -m ingestion.run_pipeline
uv run uvicorn app.main:app --host 127.0.0.1 --port 8811 --no-access-log
```

Open **http://127.0.0.1:8811/**. The startup loads synthetic identity/PTO fixtures
into SQLite and ingests the governed policies. The older n8n/Qwen/pgvector app
continues to use `app.api` on 8810; it is independent of this deterministic lab.

The requested standard Python workflow works from the project directory with
Python **3.12**:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m ingestion.run_pipeline
uvicorn app.main:app --host 127.0.0.1 --port 8811 --reload --no-access-log
# In another activated terminal:
pytest -v
python -m evals.run_evaluations
```

On Windows the corresponding environment steps are `py -3.12 -m venv .venv`
and `.venv\Scripts\Activate.ps1` in PowerShell. Windows execution was not verified;
the tested local subprocess-group cleanup targets macOS/Linux. `make verify`
runs the locked environment's static checks, full pytest/coverage and evaluations.

## Use the seven dashboard pieces

1. **Employee simulator:** choose a fictional persona. The server reads their
   session and permissions from SQLite. Changing persona immediately clears
   the prior conversation, returned data and test results.
2. **Chat:** submit a question or choose one of the three core workflow examples.
   Answers and policy citations come from real backend requests.
3. **Execution trace:** inspect measured stage status and elapsed milliseconds.
   Denied requests show skipped tool/retrieval stages. A replay shows a receipt
   lookup, the original factual result and no new protected source read.
4. **Data sources:** compare the identity service, authorized policy index and
   Workday mock. Returned facts are shown only for the selected authorized
   request; a denial does not reveal another employee's balance or existence.
5. **Business rules:** see the actual matched rule ID, outcome, requirement IDs
   and source YAML file. Routing patterns and evidence/freshness parameters are
   executable configuration; they are not front-end explanation guesses.
6. **Test runner:** choose **Demo policy administrator** to receive the fixture's
   explicit `lab:run` permission. Run unit, integration, security or all evaluations.
   The last option first runs the complete pytest suite, including end-to-end
   and performance cases, then runs the independent evaluations and release gates.
7. **Results:** inspect actual JUnit pass/fail/skipped counts, failed function IDs,
   combined coverage, metric numerators/denominators, latency and traceability.
   Partial-suite coverage is labeled separately from a full release run. Historical
   reports are marked when their source fingerprint no longer matches.

The failure selector exercises real paths: request-scoped Workday 503, timeout,
missing/stale/malformed/wrong-owner records, rate limiting/retry exhaustion,
intermittent recovery and a slow source; missing/conflicting/expired policy
evidence; omitted authentication; invalid Slack HMAC; and duplicate requests.
The first two security cases go to the actual protected HTTP endpoints with
deliberately invalid credentials/signature. No simulated success values are
created in JavaScript. Fault settings never change an employee's permissions.

## API examples and actual expected behavior

```sh
curl -sS http://127.0.0.1:8811/ask \
  -H 'Authorization: Bearer demo-employee-us' -H 'Content-Type: application/json' \
  -d '{"question":"How many PTO days do I have remaining?"}'

curl -sS http://127.0.0.1:8811/ask \
  -H 'Authorization: Bearer demo-employee-us' -H 'Content-Type: application/json' \
  -d '{"question":"What is our parental leave policy?"}'

curl -sS http://127.0.0.1:8811/ask \
  -H 'Authorization: Bearer demo-employee-us' -H 'Content-Type: application/json' \
  -d '{"question":"Show me EMP200 PTO balance."}'

curl -sS http://127.0.0.1:8811/lab/ask \
  -H 'Authorization: Bearer demo-employee-us' -H 'Content-Type: application/json' \
  -d '{"question":"What is my PTO balance?","scenario":"unavailable"}'

curl -sS http://127.0.0.1:8811/admin/test-runs \
  -H 'Authorization: Bearer demo-admin' -H 'Content-Type: application/json' \
  -d '{"suite":"unit"}'
# Substitute the returned job_id:
curl -sS http://127.0.0.1:8811/admin/test-runs/JOB_ID \
  -H 'Authorization: Bearer demo-admin'
```

Verified core responses are exact **12.5 days as of 2026-10-20**, an approved US
parental-leave excerpt with `HR-PARENTAL-US` version `1.0`, and a generic denial
with no protected Workday call. These tokens are public, synthetic teaching
sessions. Never reuse them for real records.

## Rules, data and report contracts

- `config/business_rules.yaml`: proposed exact-source, freshness, evidence,
  conflict and private-review rules. The stricter of the app and business source-age
  limits applies. Evidence coverage is an explicit configurable threshold.
- `config/routing_rules.yaml`: seven intent contracts, ordered matching patterns
  and the fallback. An optional `IntentRouter` adapter returns the same typed
  `Route`; authorization remains outside that adapter.
- `config/security_policies.yaml`: fixed deny-by-default invariants, permission
  names, scoped access, receipt revalidation and lab operator permission.
  The client cannot supply or modify rules.
- SQLite `mock_employees` and `mock_workday`: actual runtime source records.
  JSON is a seed snapshot. Unchanged seed digests preserve database edits;
  an intentionally changed fixture snapshot replaces that mock table atomically.
  Policy ingestion does not reset employee or Workday records.
- `reports/lab/<job-id>/`: isolated state, JUnit, coverage, test manifest and
  optional evaluation/release/traceability artifacts. Raw process output remains
  local and is never returned by the HTTP API. Failed parameter text is omitted
  from web reports; function IDs remain visible.

Jobs accept only `unit`, `integration`, `security` or `evaluations`; command,
environment and output paths are server-owned. One process group runs at a time,
with a default 120-second deadline and 40 retained job folders before new jobs
are refused. Move old job folders to a local archive if that limit is reached.
Provider keys and arbitrary Python paths are removed from child environments.
Coverage and test manifests cannot overwrite the canonical `reports/` files.

Disable the teaching layer with `HR_LAB_ENABLED=false`. `HR_DEMO_MODE=false`
also disables the synthetic identity sessions; it does not install real SSO.
These values must be exported as environment variables or set in `config/app.yaml`;
the enterprise app does not auto-load the older service's `.env`.

## Where the implementation lives

```text
app/
  main.py                 authenticated API, simulation and test job routes
  rules.py                typed YAML governance
  diagnostics.py          measured, content-free stages
  enterprise_data.py      idempotent SQLite seed
  identity.py             SQLite session authority and identity adapter
  orchestrator.py         actual authorized source execution
  test_runner.py          bounded subprocess jobs and artifact parser
  lab_worker.py           fixed pytest/evaluation commands
  enterprise_static/      existing portal extended with the lab dashboard
config/                   app, business, routing and security YAML
requirements/             15 BRD requirements, 23 acceptance/traceability rows
tests/                    unit, integration, security, end_to_end, performance
evals/                    independent labeled evaluation layers
reports/                  executed local artifacts; ignored runtime files
.github/workflows/ci.yaml  standalone CI; AI-OS also has its root path-scoped CI
```

Read [architecture and trust boundaries](architecture.md), [test plan](test_plan.md),
[actual verification](testing-layer-verification.md), [operational readiness](operational_readiness.md)
and [elementary function explanations](enterprise-functions.md).
