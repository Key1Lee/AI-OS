# Current responsibility map — 2026-10-02

Phase 0 completed before implementation. The four siblings were inspected directly;
their directories differ from the names in the brief. No sibling files are changed.

| System / inspected evidence | Existing overlap | Keep here | Quality interface / avoid duplication |
|---|---|---|---|
| Modeling: `../Data Modeling System/services/modeling-engine/src/data_modeling_lab/{contracts,engine}.py`, `scenarios/ecommerce/fixture.json`, README | `ContractDefinition`, declared grain/keys/columns; deterministic uniqueness, null, schema, relationship, accepted-value and business assertions; golden-output evaluation | Model design, transformations, join/grain teaching, exercise-specific golden assertions and gross Revenue semantics | Consume `modeling-lab-v1` declared ModelDefinition as designed state; map types explicitly. Do not copy SQL evaluator, golden oracle or redefine its metric. Reusable quality policies belong here for future consumers. |
| Orchestration: `../Data Orchestration System/src/engine/{modeling,scenarios,types}.ts`, README | Authored `quality_check` task and `quality_result` asset; runtime validation of workflows; model-envelope adapter | Task dependencies, timing, retries, schedules, backfills, execution truth | Call validation between build and publish; obey gate result. The current quality task is a simulation, not an executing quality engine. Do not duplicate scheduling or task state. |
| Observability: `../Data Observability System/src/data_system_map/contracts.py`, `adapters/dbt.py`, AGENTS | Recorded `TestResult`, dbt manifest/run-result/freshness ingestion, provenance, schema differences, graph health/incidents | Artifact ingestion, monitoring, trends, lineage, investigation and blast radius | Emit `quality-event-v1`; offer a mapping into its existing TestResult shape. This project's flow is a fixed teaching sequence, not a lineage engine. No second artifact/incident service. |
| Toptal: `../Toptal-Testing System/trainer/data_map/{contracts,service}.py`, `docs/dbt_lab.md`, AGENTS | Deterministic graders, SQL result comparison, competency schemas, recorded-test inspection; dbt runner deferred | Scoring, hint/reveal policy, attempts, telemetry, mastery, assessment | Expose scenario and validation endpoints without answers/rubrics/scoring. Toptal decides what the learner sees. Do not import trainer internals or write learner records. |

## Shared contracts and semantics

No common quality service or shared QualityRule/ValidationResult contract exists.
The existing public envelopes are `modeling-lab-v1`, `orchestration-event-v1`,
`orchestration-scenario-v1`, and `data-map-v1`. Preserve those names and status
vocabularies at their boundaries; normalize through explicit consumer adapters.
No source migration is needed for this slice. Future replacements of embedded
generic assertions should use these interfaces and separately prove preservation.

All systems use e-commerce concepts (customers, orders, order_items, payments,
products, returns), but their fixtures and metrics are not identical. Modeling's
Revenue is gross completed-order USD revenue, before returns. This lab's contract
explicitly uses current-order net USD revenue after refunded returns. The new
10-order fixture is a separately versioned scenario, not a shared oracle.

```text
MODELING       declares intended row meaning, schema and key
ORCHESTRATION  builds datasets and calls validation before publication
QUALITY        verifies declared assumptions and decides the quality gate
OBSERVABILITY  consumes facts to investigate time, upstream causes and impact
TOPTAL         assesses whether the learner can diagnose the evidence
```

Sibling runtimes remain independently runnable. Interfaces are implemented and
tested locally; live wiring into sibling applications is a future consumer change.
