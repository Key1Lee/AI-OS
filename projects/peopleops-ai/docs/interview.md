# Hiring-manager rehearsal

This is a fictional engineering exercise, not a description of Samsara's
systems or its interview evaluation criteria. Use the application to support
your explanation with something you can run and inspect.

## A 90-second walkthrough

“I built a local PeopleOps application around three business needs: dependable
workforce metrics, accountable HR support, and traceable policy answers.
The source is a simulated Workday API; Python normalizes records, quarantines
invalid rows, and updates employees only when the source version is newer.
SQLite enforces relationships, while separate dbt models test the analytics
snapshot. FastAPI checks identity and record ownership before serving data.
Policy retrieval filters permissions first and returns exact approved passages
with citations, escalating when it has no support. Onboarding uses unique task
keys and a transactional outbox so repeated source events do not duplicate
work. I can demonstrate a failed source, a stale delivery, and notification
recovery with preserved business state and audit evidence.”

## A five-minute demo

1. Open Overview as HR. Define headcount and the inclusive 30-day window.
2. Switch to Maya. Submit “Payroll help” and explain its Payroll routing.
3. Show that Jordan's record returns 403 using `scripts/demo_api.py`.
4. Ask when payroll is paid. Open the cited source and explain extractive output.
5. As HR, simulate a new hire twice. Show three tasks and one event for EMP-021.
6. Simulate Workday unavailable. Explain retries, preserved employee state,
   and readiness degradation; restore the healthy scenario.
7. Run pytest and dbt. Distinguish automated program evidence from your own
   understanding and from any unproven production claim.

## Practice defending decisions

| Prompt | Evidence and judgment to include |
| --- | --- |
| Why SQLite? | No server setup, real transactions and relationships; move to PostgreSQL when concurrency, access control, or operating needs justify it |
| Why simple retrieval first? | Inspectable citations, no external data flow, ten regression cases; lexical matching misses paraphrases, so measure a broader labeled set before adding neural embeddings |
| Why no live LLM? | Exact extraction makes support testable; generation adds flexibility but requires grounding checks, refusal evaluations, cost/latency budgets, and data-handling decisions |
| How do duplicates behave? | Source version selection, employee UPSERT, unique task keys, event keys, and request idempotency keys solve different replay boundaries |
| How is access enforced? | A token maps to a server-stored role and employee ID; each data path checks permissions, and retrieval filters documents before ranking |
| What breaks first at scale? | Write contention and operational coupling merit measurement; the local 5,001-row run proves one bounded test, not a throughput guarantee |
| How would you add Airflow? | Map explicit stage dependencies, distinguish retryable failures from invalid data, define backfill dates and replay guarantees, and keep quality gates visible |
| What is missing for production? | Enterprise SSO, team-scoped HR cases, encryption/retention, migrations, backups, distributed delivery guarantees, richer employment history, and operating ownership |

## Business impact without invented results

Before → after: repetitive policy questions without sources → a cited answer
or tracked escalation. Measure answer usefulness, correct escalation, time to
first response, and repeated contacts on a real authorized evaluation set.

Before → after: onboarding managed by manually copied checklists → stable
employee/task keys with retryable notifications. Measure overdue tasks,
duplicate task rates, failed deliveries, and time to operational recovery.

Before → after: inconsistent definitions of workforce totals → an explicit
status/date contract and tested reconciliation. Measure source freshness,
rejected-row rates, reconciliation failures, and stakeholder agreement on
definitions; do not claim cost savings or ticket deflection without evidence.

## Self-assessment rubric

| Score | Evidence |
| --- | --- |
| 0–3 | Can name components but cannot trace a request or explain the output |
| 4–7 | Can run the happy path; needs help with privacy or failure recovery |
| 8–9 | Can explain keys, versions, permissions, citations, and recover a failure |
| 10 | Can reproduce checks, identify practical limits, and defend a measured next step |

No mastery score has been awarded. Self-reviewed checkmarks in the UI record
your study progress only.
