# Data Pipeline & Orchestration Lab — first slice

Decision date: 2026-10-02 (Asia/Seoul). Package/repository identity:
`data-orchestration-lab`. The empty `Data Orchestration System` workspace is already
a sibling project; implementation stays here. Other projects and AI-OS shared files
are preserved, including their unrelated in-progress changes.

## Architecture inspection and ownership

Inspected AI-OS `AGENTS.md`, `README.md`, runtime/model-router guidance, testing,
verification, and the neighboring Modeling, Observability, and Toptal contracts.
The Modeling project was renamed to `Data Modeling System` during that read-only
inspection; it remains an independent source. No shared runtime change is needed.

Modeling owns the desired data: grain, SQL, joins, materialization semantics, metrics,
and assertions. This lab owns when tasks execute and their execution evidence.
Observability consumes events and owns health, investigation, anomalies, and incidents.
Toptal consumes scenario/evidence contracts and owns hints, scoring, progress, and
candidate telemetry. The lab has no dependencies on any of those implementations.

## One local application, one reusable truth engine

`src/engine/` is pure, browser-independent TypeScript. A React/Vite application calls
it directly; no API server, database, account, LLM, or production orchestrator is
necessary. A small Node static server serves the built app on loopback. Fonts and
all assets are bundled, so simulation works offline after installation/build.
Session history is in browser memory; JSON export is the durable handoff.

An explicit virtual date, clock, partition, run ID, and failure sequence determine
the result. Topological order is stable. A discrete event step completes due attempts,
resolves dependencies to a fixed point, then assigns workers. Retrying tasks release
workers. Deterministic errors do not qualify for automatic retries. A timeout is an
error type on FAILED, not a ninth beginner task state. One-success and all-done rules
are supported and remain inspectable in advanced mode.

Daily schedules use an explicitly supported timezone (Asia/Seoul or UTC). They make
the workflow eligible, independently of task dependency readiness. Manual and declared
asset-update triggers use the same dependency/worker engine. No live scheduling daemon
is claimed. A backfill replays selected logical dates **today**, respects successful
partitions unless replacement is requested, and shares a global worker budget across
concurrent partitions. It does not execute in the historical date's wall clock.

The longest weighted dependency path is a theoretical lower bound with unlimited
resources and no retries. The actual attempt timeline includes contention, retry
delays, and failure. They are labeled separately to avoid teaching a false equivalence.
For conditional rules, the bound follows nominal reachability: skipped tasks finish
immediately without success; their all-success descendants block; one-success joins
choose only successful candidates, and all-done joins wait for terminal parents.
The idempotency experiment uses an authored 100-row payload with replace/append
semantics. It teaches execution safety, not a replacement for Modeling's SQL engine.

## Presentation

Default: Source → Ingest → Staging → Transform → Mart → Dashboard. Reveal nine actual
tasks only on request. Every state has text and a symbol, not color alone. A persistent
question strip and task inspector cover what runs, when, dependencies, failure,
retries, rerun safety, history, and downstream blocking. Pipeline, asset, and timeline
views share the same run snapshots; advanced mode reveals definitions/event payloads.
Five small authored variations cover success/failure, transient retries, unsafe reruns,
three missing partitions, and a long branch. No assessment score is produced.

## Contracts and future adapters

Versioned JSON Schemas describe execution events and Toptal scenarios; exports include
the source workflow, attempts, upstream states, partition, and timestamps. Modeling
definitions are consumed as an envelope of `modeling-lab-v1` ModelDefinitions: `parents`
become execution dependencies; grain/materialization metadata remains opaque.
No modeling semantics are inferred or rewritten. A vendor adapter port and concept
mapping are the entire MVP adapter surface: no Airflow, Dagster, Prefect, or dbt jobs
integration is implemented.

## Checks and deliberate limits

Node tests cover behavioral invariants and contract validation; browser tests exercise
the learner journey, mobile layout, exported evidence, and production serving.
An independent tool-capable verifier follows AI-OS verification guidance and attempts
to falsify every criterion in `docs/acceptance.md`. Only that verifier makes the
independent acceptance decision; defects return to the main implementation agent.

Not included: production scheduling, distributed execution, cloud deployment, SQL
execution, runtime observability, assessment/hint policy, persistent progress, generic
workflow authoring, cron/weekly/hourly schedules, incremental-model logic, or full
orchestrator integrations. Late data/lookbacks are explained through a bounded
historical-partition example, with transformation ownership delegated to Modeling.
