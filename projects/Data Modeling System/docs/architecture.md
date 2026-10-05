# Data Modeling & Transformation Lab — first slice

Architecture decision record, 2026-10-02. Project/package identity: `data-modeling-lab`.
The existing `Data Modeling Lab System` directory is the project root; it is not renamed.

## Current environment

This directory was empty. AI-OS is the parent Git repository and has unrelated changes;
this implementation is confined to this project. Node 24.18, npm 11.16, Python 3.13,
and uv are available. No dbt, DuckDB, SQLGlot, or FastAPI installation was found in
the active Python. Neighboring projects use React/TypeScript/Vite and Python/FastAPI.
Their public contract files were inspected read-only. No sibling imports or edits are needed.

## Proposed Data Modeling Lab architecture

One React app, one local FastAPI application, and a reusable Python engine. DuckDB
executes small deterministic fixtures in a new in-memory connection per operation.
SQLGlot inspects SQL; execution and dataset assertions establish correctness.
No cloud account, LLM account, database server, background orchestrator, or persistent
student database is required. A local launcher serves the built web app and API from
one origin. Vite proxies the API during development.

## Project boundary

Own grain declarations, key checks, joins, transformation differences, source-conformed
staging, an order fact, an inspectable semantic metric, and invariant-based evaluations.
The displayed graph is a **designed learning flow**, not a runtime lineage collector.
No incident management, source freshness monitoring, candidate scoring, assessment
policy, telemetry, or question selection belongs here.

## Dependencies

React, TypeScript, Vite, React Flow, and Lucide for the web app; FastAPI/Pydantic,
DuckDB, SQLGlot, and uvicorn for the engine/API. Pytest/httpx and Playwright provide
meaningful engine, API, and browser checks. Lock both Python and npm resolutions.
Do not generate dbt syntax in this slice. A future dbt adapter must inspect the chosen
project/version, compiled SQL, and metadata before translating into these contracts.

Primary implementation references: [DuckDB Python](https://duckdb.org/docs/stable/clients/python/overview),
[SQLGlot API](https://sqlglot.com/sqlglot.html), [FastAPI](https://fastapi.tiangolo.com/tutorial/).

## Data contracts

Pydantic contracts are provider-neutral and versioned `modeling-lab-v1`. OpenAPI and
an exported JSON Schema describe them. Definitions expose columns, explicit declared
grain (unknown until declared), keys, relationships, why a model exists, materialization,
transformation steps, metric definitions, and tests. Evaluation reports expose SQL
validity, schema/output/grain/key evidence, per-test status, warnings, and factual
explanations; there is no numerical assessment score. Money uses DECIMAL in SQL and
decimal strings in JSON. Actual cardinality is observed on fixture keys and explicitly
distinguished from an expected relationship and a general production guarantee.

## Visual learning model

Default beginner experience: a calm visual workspace with a source → staging → fact
→ metric story, source table samples, a grain declaration gate, and a join experiment.
Show grain, key, relationship, operation, and proof in the model inspector. Clickable
edges show before → operation → after → why, including changes in rows and columns.
Join Lab traces each left row to every matching right row and explains inflated sums
in actual dollars. A safe/broken toggle demonstrates a real transformation change.
Advanced mode reveals SQL and exact contracts using the same computed evidence.
Every status uses text/icon plus color. The learner can reset the local session.

## Deterministic evaluation model

Six source fixtures are human-inspectable: customers, order versions, items, payments,
products, and returns. Three completed orders total USD 225.00. A cancelled order is
excluded. Raw orders include an older O1 version; deterministic staging chooses the
latest version using explicit timestamp/source-version ordering and normalizes names,
timestamps, statuses, and cents. Staging has four orders; the fact has three completed
orders. Revenue means **gross completed-order revenue before returns**, not paid cash
or net revenue. A return fixture makes this distinction visible.

Joining the completed orders directly to items yields four rows and USD 325.00 when
summing order amounts: O1's USD 100.00 is repeated twice. Aggregating items to order
grain before the join yields three rows and USD 225.00. Cardinality, unmatched keys,
NULL join semantics, uniqueness, and expected versus actual rows are measured.

Learner SQL runs only as a single read-only query against known fixture/model tables.
External file/network access and extension auto-loading are disabled. Bound SQL size,
memory, time, and response size. The evaluator accepts semantically equivalent SQL,
not just an exact reference string. Exact expected rows, types, non-null keys,
uniqueness, completed-order filtering, and the metric result are separate checks.
The reference output is a checked-in oracle, not computed with learner SQL.

## First vertical slice

1. Load six e-commerce fixtures and show source schemas and rows.
2. Require a learner grain declaration before building an important model; unknown
   declarations stay visibly unknown and incorrect declarations receive evidence.
3. Show relationships and execute configurable LEFT/INNER join experiments.
4. Compute key cardinality, expected and actual rows, resulting grain evidence, and
   repeated order amounts; trace fanout visually and provide an aggregation repair.
5. Execute staging, display deduplication/renaming/casting differences, and build one
   completed-order fact with a declared key and grain.
6. Execute data assertions and independently compare expected output.
7. Define/evaluate one inspectable Revenue metric with explicit currency and filters.
8. Allow advanced SQL alternatives and preserve all invariant checks.
9. Produce grounded explanations and export designed-state/evaluation contracts.
10. Pass independent Modeling Verification Agent checks before completion.

## File structure

```text
apps/web/                         React UI, typed API client, browser checks
services/modeling-engine/src/
  data_modeling_lab/              contracts, fixtures, SQL guard, engine, API
scenarios/ecommerce/              fixture data, expected output, business definition
tests/                           engine and API correctness regressions
scripts/                         local launcher and contract export
docs/                            architecture, acceptance/verification, screenshots
pyproject.toml, uv.lock, Makefile
```

Use cohesive modules, not empty contract/adapter/microservice packages.

## Test strategy

Reconcile the hand-calculated USD 225.00 oracle and USD 325.00 broken result; prove
deterministic deduplication, row/key/null behavior, all join cardinality classes,
unmatched LEFT versus INNER behavior, aggregation repair, metric filtering, money
precision, contract rejection, alternate valid SQL, unsafe SQL rejection, bounded
execution, structured API errors, graph coherence, and no external project imports.
Playwright covers the complete learner journey, broken/repaired behavior, advanced
SQL evaluation, and a narrow viewport. Build/typecheck the production frontend.
Exactly one read-only verifier attempts to falsify claims independently and records
criterion-to-evidence, commands, gaps, and PASS/FAIL. Fix findings and reverify.

## Integration strategy

The future trainer consumes fixture/exercise requirements and `EvaluationResult`
through an API/SDK adapter; all scoring remains in the trainer. Observability may
consume exported `ModelDefinition`, `GrainDefinition`, `RelationshipDefinition`,
`ContractDefinition`, and `MetricDefinition` as designed state. A future consumer-owned
adapter maps these to its `GraphSnapshot`; no reverse dependency is introduced here.
Adapters for warehouses, lakehouse formats, dbt, or orchestration are future work.

## Later slices, deliberately pending

Intermediate/dimensional/customer-LTV/mart exercises and an expanded test authoring
experience come next. Then incremental updates, lookbacks, late data, backfills and
idempotency; then SCD2, snapshots and historical attribution; then integrations.
Other domains, warehouse-specific performance, model comparisons, and AI tutoring
remain outside this first release. The UI must not present pending labs as functional.
