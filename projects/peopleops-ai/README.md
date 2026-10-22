# PeopleOps AI Engineering Lab

> **People Insights AI:** [Conversational IBM sample reporting app, setup and evidence](people-insights-ai/README.md).
> Open [the local chatbot](http://127.0.0.1:8813/) for department reports, comparisons
> and aggregate CSV downloads. It uses its own Python environment and supports
> direct FastAPI or local n8n execution. The survey dashboard and training remain separate.

> **Enterprise HR reference:** [BRD, standalone setup, exact PTO, governed RAG, evaluations and CI](policy_assistant/docs/enterprise-guide.md).
> Launch `Start-Enterprise-HR.command`, or run `make verify` in `policy_assistant/`.

> **Working policy assistant:** [Setup, API examples, n8n, and test results](policy_assistant/README.md).
> Launch `Start-Policy-Assistant.command` for the completed Python 3.12,
> FastAPI, PostgreSQL/pgvector, and chat application. The training exercises below
> remain unchanged and separately assessed.

> **New primary learning environment:** [ASTRA interview training lab](training/README.md)
> uses Python 3.12, PostgreSQL/pgvector, FastAPI, SQLAlchemy, Streamlit, and Docker
> Compose. Its business logic remains learner exercises. See [PROGRESS.md](PROGRESS.md)
> or launch `Start-Training.command`. The guide below describes the preserved
> original SQLite simulation.

A complete local HR simulation for practicing ingestion, SQL, APIs, policy
retrieval, privacy, and failure recovery. All employees and policies are
fictional; Workday and Slack use local mocks. This is independent of Samsara
and makes no claim about its internal systems.

## Run it

```sh
cd /Users/key/_AI-OS/projects/peopleops-ai
uv sync --frozen
uv run peopleops init
uv run peopleops serve
```

Open [the application](http://127.0.0.1:8765/) or [interactive API docs](http://127.0.0.1:8765/docs).
The app serves on loopback. Stop it with Control-C. On macOS you can also open
`Start-PeopleOps.command`; it uses the same commands.

`uv sync` installs the recorded dependencies into this project's `.venv`.
`init` creates tables, loads fictional data, and generates local demo tokens;
repeating it preserves existing work. `serve` runs the FastAPI service.
Python 3.11–3.13 is supported; this checkout was tested with Python 3.13.

If uv is unavailable, the standard Python alternative is:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e . pytest 'dbt-core>=1.10,<1.11' 'dbt-sqlite>=1.10,<1.11'
.venv/bin/peopleops init
.venv/bin/peopleops serve
```

The alternative resolves versions at install time; `uv sync --frozen` uses
the checked-in lockfile. No database server, API key, cloud account, Airflow
installation, or frontend build is needed.

## Explore

| Screen | What to do |
| --- | --- |
| Overview | Inspect headcount, hires, departures, request workload, and onboarding |
| HR requests | Submit a payroll question, inspect routing, and resolve it as HR |
| People & onboarding | Browse validated records, simulate a hire, and complete tasks |
| Policy assistant | Ask when payroll is paid and inspect its cited policy |
| System health | Simulate failures, inspect quarantines, retry notifications, and read audit events |
| Learning path | Work through 12 small lessons with starter exercises and exact checks |

Use the **Demo identity** selector to act as Maya, Jordan, HR, or an analyst.
The employee roles see their own records and requests; the analyst gets
aggregate metrics and public policies; HR operates the demo. Demo role
switching deliberately exposes generated demo credentials on loopback.
These credentials are for fictional data and are not production login.

To exercise API authentication without copying a token into shell history:

```sh
uv run python scripts/demo_api.py
```

This retrieves the local Maya demo identity, submits a fictional payroll
request, replays it with the same idempotency key, and prints only outcomes.

## Check the application

```sh
uv run pytest
uv run peopleops quality
uv run peopleops evaluate
uv run peopleops dbt
sqlite3 -header -column data/peopleops.db < sql/practice.sql
```

On a fresh database the expected results are 60 pytest tests, eight passing
SQL/freshness checks, ten passing policy evaluation cases, and six dbt models
plus 22 data tests (`PASS=28`). See [verification evidence](docs/verification.md)
for the actual run and environment, including dependency warnings.

## Fresh demo expectations

| Source input | Result |
| --- | --- |
| 20 fictional employee records + 2 duplicate deliveries | 16 accepted identities, 4 invalid rows, 2 duplicates |
| 16 accepted employee identities | 14 current employees, 1 departure, 1 prehire |
| Hire/departure dates in the last 30 days | 5 new hires, 1 departure |
| 6 HR requests | 5 unresolved, 1 resolved |
| 15 onboarding tasks | 1 complete, 6.7% completion |
| 8 policies | 6 company policies, 2 HR-only policies |

Dates shift from the fixture anchor to the current Asia/Seoul calendar date
when the source is read. `PEOPLEOPS_AS_OF=2026-10-17` pins a lesson date;
freshness still uses the real UTC clock, so old pinned dates intentionally
become stale. Dates in requests and operational logs use real UTC timestamps.
Interactions change these initial totals; they are not a reset contract.

## Files to follow

```text
peopleops/fixtures/ → integrations.py → validation.py → pipeline.py
                                                    ↓
schema.sql ← db.py ← SQLite peopleops.db → dbt/ → analytics.db
                         ↓
              analytics.py + app.py → web/
                         ↓
         retrieval.py + routing.py + workflows.py
                         ↓
            audit_logs + http_observations + tests/
```

The live UI uses direct SQL over the application database. dbt builds a
separate analytics snapshot for transformation/testing practice; run it again
after source changes. The UI does not silently present an old dbt snapshot
as current data.

- [Architecture, contracts, permissions, and trade-offs](docs/architecture.md)
- [12-phase learning guide](docs/learning-guide.md)
- [SQL and Python glossary](docs/glossary.md)
- [Failure recovery runbook](docs/runbook.md)
- [Interview rehearsal](docs/interview.md)
- [Progress and verification](docs/verification.md)

## Boundaries

The policy assistant uses sparse TF-IDF retrieval and exact approved passages.
Its score is text similarity, not the probability an answer is correct; there
is no live LLM or neural embedding service. The guide explains where those
components would fit and how to evaluate them.

`uv run peopleops tick` demonstrates ordered jobs and quality gates in one
process. It does not install or claim a running Airflow scheduler. `notify`
and `remind` simulate Slack and never send real messages. There is no live
Greenhouse integration; a future recruiting feed would need its own contract.

SQLite, generated Bearer tokens, and unrestricted HR demo access are appropriate
for this local exercise. The database and raw/quarantine records contain
fictional sensitive fields and are not encrypted. Production identity,
encryption, retention, team-scoped HR case permissions, and deployment are
separate engineering work. `PEOPLEOPS_DEMO_MODE=0` disables public identity
switching; API use then requires an existing token from the local credentials
file and the browser demo is disabled.

The SQLite dbt adapter currently pairs with dbt-core 1.10, which reports a
deprecation warning. This version is isolated to the learning project;
upgrade the adapter/core together before choosing a production stack.
