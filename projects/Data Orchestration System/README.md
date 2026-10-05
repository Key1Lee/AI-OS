# Data Pipeline & Orchestration Lab

An independent visual lab for **when, why, and in what order analytical work runs**.
Project/package identity: `data-orchestration-lab`. Its root is the existing
`Data Orchestration System` sibling directory in AI-OS.

## Run locally

Requires Node 22.12+ and npm. From this directory:

```sh
npm ci
npm run build
npm start
```

Open [the lab](http://127.0.0.1:8078). Use `npm run dev` for development, or
`node scripts/serve.mjs --port 8080` to choose another production port.
No cloud account, AI account, sibling application, database, or real orchestrator
is needed. Assets and fonts are local; simulation works offline after the app loads.

Session runs/output state live in browser memory. **Export run evidence** downloads
the source scenario, current run, and completed history. Reloading clears the session.
In Backfill Lab the button exports the displayed backfill's source workflow, explicit
worker/failure options, plan, partition runs/events, and results instead.

Each new backfill invocation has a caller-owned `options.execution_id` (a nonblank
string of 1–160 characters). The browser creates a UUID when Run is pressed;
exporting that result preserves its ID. Partition run IDs are
`backfill:${execution_id}:${partition}`. Replaying a failed partition starts a new
invocation with a new ID; automatic task retries remain in the same run and
increment attempts. Identical explicit inputs and the same execution ID reproduce
the same trace. Historical exports retain their original identities; do not reuse
an ID for changed inputs. This required `simulateBackfill` argument changes the
source API; the existing event and export contract versions are retained.

## Your first experiment

1. Begin with Source → Ingest → Staging → Transform → Mart → Dashboard.
2. Predict which tasks can start together. Run or step through a successful day.
3. Reveal nine tasks. Click `int_orders`: both staging dependencies must succeed.
4. Choose **Break a dependency**. Customer extraction fails; the independent orders
   branch still completes. Click the blocked task to see why it never started.
5. Fix configuration and rerun. Then choose **Try again, safely**: attempt one times
   out temporarily, its worker is released, and attempt two begins after five minutes.
6. Choose **Run it twice**, then **Rerun same inputs**. The mart grows 100 → 200 rows.
   The successful-day scenario uses replacement and gives 100 → 100 instead.
7. Open **Backfill Lab**. Preview Sep 27–29, run the range, fail Sep 28 independently,
   and rerun the failed partition while keeping successful dates. Try explicit
   reprocessing and compare global workers with partition concurrency.
8. Choose **Find the critical path** and open the timeline. Customer staging lengthens
   the successful dependency bound from 14 to 19 minutes. The actual timeline also
   reveals worker/pool contention and retry delays.

Daily eligibility opens at **06:00 Asia/Seoul** on the explicit virtual date
**Oct 2, 2026**. Manual and declared orders-asset update triggers can begin at 05:55.
This is a virtual learning schedule, not a background production scheduler.
Historical partition keys remain historical; backfill execution timestamps are today.

## Engine and contracts

The browser-independent entrypoint is `src/engine/index.ts`. A consumer can use it
through TypeScript/tsx without React:

```ts
import { scenarioContract, createRun, stepSimulation, simulate } from './src/engine';
const scenario = scenarioContract('transient');
const result = simulate(scenario.workflow, {
  partition: '2026-10-02', clock_date: '2026-10-02',
  start_minute: 355, run_id: 'consumer-explicit-run-1', max_concurrency: 2,
});
// Or createRun(...), then stepSimulation(...) to inspect every event instant.
```

All truth is deterministic: the supplied DAG, duration/outcome sequences, run options,
resource budgets, and stored outputs determine the result. No randomness, wall clock,
or AI sets states. Eight task states are used; timeout is a FAILED error type.
Trigger rules support all-success, all-done, and one-success. Resource pool budgets
are shared across backfill partitions. Retry delay releases workers.

`npm run contracts` regenerates checked-in schemas and examples under `contracts/`:

- `orchestration-event-v1`: task transitions, run/workflow/task/asset identity,
  attempts, occurred/start/end times, attempt duration in minutes, errors, logical
  partition, and upstream states. Attempt failures remain recorded even after success.
- `orchestration-scenario-v1`: authored workflow, repeatable failures, partition,
  learner questions, and evidence task IDs. No score, rubric, hint policy, or telemetry.
- `workflowFromModels`: consumes a `modeling-lab-v1` envelope of existing Modeling
  ModelDefinitions (`models` array). `parents` become dependencies; declared grain and
  materialization are copied as opaque metadata. It executes authored placeholder
  tasks, not SQL or Modeling transformations. Source models remain external assets.

Advanced mode reveals definitions, attempts, payloads, and separate event/scenario
exports. A future consumer should validate JSON against the supplied schemas and
then use the engine's domain validation. Real Observability and Toptal connections
are future consumer-owned adapters; the contracts are implemented and tested here.

## Boundaries

Modeling defines the desired data. Orchestration executes work. Observability reads
execution facts to investigate health and failures. Toptal assesses learner reasoning.
The lab imports no sibling code and has no SQL evaluator, assessment engine, monitoring
service, or incident workflow. Rerun row counts use a clearly authored 100-row payload.
Late data/lookbacks are explained by choosing historical partitions, not implementing
incremental-model transformations. Vendor-neutral adapter types and Airflow concept
mapping exist; Airflow, Dagster, Prefect, and dbt jobs integrations do not run yet.

## Checks

```sh
npm test
npm run build
npm run test:e2e
```

`npm run check` runs all three. Browser checks use the production build on loopback
port 8079; run `npx playwright install chromium` if the browser is unavailable.
Engine/contract checks include dependencies, cycles, all trigger rules, retry exhaustion,
timeouts, schedules/assets, rerun safety, deterministic traces, partitions, global
worker/pool limits, critical path, Modeling metadata, and schema validation. Browser
checks cover the learning flow, repair/retry, exports, reruns, backfills, mobile, and
execution offline. Screenshots are under `docs/screenshots/`.

See [architecture](docs/architecture.md), [acceptance criteria](docs/acceptance.md),
and [implementation handoff](docs/implementation-handoff.md). Exactly one independent
Orchestration Verification Agent challenged the implementation and issued
**[PASS](docs/verification-agent.md)** after corrective work. Final evidence covers
37 project tests, the production build, 9 browser journeys, 24 independent probes,
and 6 independent browser check groups, with no blocking correctness errors.

This is the first vertical slice. Generic workflow authoring, persistent learning
progress, cron/hourly/weekly schedules, production scheduling, real external integrations,
distributed executors, Kafka, Kubernetes, and cloud deployment remain outside it.

Explicit successful-partition replacement requires replacement writes. An authored
append workflow is rejected for that operation so reprocessing cannot silently double
the output while claiming replacement. Retry-delay timestamps indicate eligibility;
worker and resource availability can delay the actual next attempt.
