# Implementation handoff — 2026-10-03

## Objective and controlling scope

Build the smallest excellent standalone Data Quality & Contracts slice from the
user's `product-brief.md`; audit siblings before implementation; use exactly one
independent verification agent; completion only after that verifier passes.
The twenty vertical-slice requirements and acceptance matrix are implemented.
Small deterministic freshness/volume/reconciliation and compatibility fundamentals
are included to teach the requested completion concepts and five failure scenarios.
No sibling files or shared AI-OS implementation are changed. The pre-existing empty
`Data Quality System` directory is preserved; the requested preferred directory is
`projects/data-quality-contracts-system`.

## System audit / final responsibility map

See `system-audit.md` for exact inspected paths and overlaps. Existing Modeling
assertions remain exercise-local proof. Orchestration's quality task remains authored
execution context. Observability ingests recorded artifact facts. Toptal retains
its grader, scoring and disclosure. Quality owns reusable expectations, schema/key/
business validation, results, severity, compatibility and publication eligibility.
No source extraction/migration was needed. Serialized adapters prevent duplication.

## Architecture and affected components

Strict Pydantic domain → pure deterministic engine → ValidationBundle / QualityGate /
QualityEvents → stateless FastAPI → visual React lab. Optional dbt adapter and real
DuckDB execution; GX design only. `architecture.md` contains the flow diagram.
Implementation: `src/quality_system`, fixture JSON, `web/src`, scripts, dbt_lab,
tests, contract exports, project docs, dependency lockfiles and Makefile.

Input clocks and decimal semantics are explicit. Empty row assertions are UNKNOWN;
schema metadata and actual values are checked; key uniqueness is separate from
semantic-grain meaning; missing/stale/mismatched gate evidence withholds publication.
Decimal comparisons use fresh contexts and exact threshold ratios. INTEGER is
signed 64-bit. Samples protect generated row pointers. Generated IDs are bounded.

## First scenario / expected evidence

Commerce current-orders v1 has six source concepts and ten prebuilt fact rows.
Net USD revenue = captured 555.00 − refunded 5.00 = warehouse 550.00.

| Input | Counts | Gate / evidence |
|---|---|---|
| valid | 18 PASS | OPEN / eligible |
| duplicate 1007 | 16 PASS, 2 FAIL | 11 rows / 10 IDs; two affected rows, one extra; 620.00 warehouse; withheld |
| orphan C999 | 17 PASS, 1 FAIL | One orphan; withheld |
| remove ordered_at | 15 PASS, 1 FAIL, 2 UNKNOWN | Schema contradiction; missing dependent evidence; withheld |
| advance clock 3 hours | 17 PASS, 1 FAIL | 210-minute arrival age against 120-minute limit; withheld |
| completed unpaid | 17 PASS, 1 FAIL | One business invariant violation; withheld |
| optional-description gap | 17 PASS, 1 WARN | Nonblocking; eligible |
| repair / fresh rerun | 18 PASS | OPEN / eligible |

The browser shows contract → prediction → validation → factual samples → controlled
corruption → consequence → repair → verify. Five quality levels and seven teaching
stages; no learner scoring or claims of earned mastery. Unit vs data-test examples
are separately labeled. The upstream flow is authored context, not certified lineage.

## Checks observed before full handoff

- 94 pytest checks passed, plus production TypeScript/Vite build.
- 8 Playwright journeys passed: complete break/repair/export, five failures, warning/
  UNKNOWN, custom-rule blocking, compatibility policies, seven stages/test types/
  family, all views on mobile, local assets/no browser exceptions.
- Real dbt Core 1.12.5 / dbt-duckdb 1.11.0: valid build of 26 resources succeeds;
  duplicate, unpaid, missing schema column and intentionally wrong unit logic produce
  the expected failures. Current summaries/logs in `docs/test-results/`.
- Same independent verifier's core round 3: all 118 edge probes supported; originals
  and corrective regressions in `docs/verification-evidence/` and project tests.

Provider adapters honestly report unsupported mappings and recorded-evidence
differences. The real optional dbt check is required to be rerun after macro changes.
Final evidence may update counts as regressions are added. Final acceptance belongs
to the independent verifier, not this handoff's test claims.

## Known scope limits / next integration

Live sibling applications are not wired together. The existing consumer-owned
adapters should call the local API/serialized contracts and preserve scenario IDs
and semantic definitions. Modeling supplies designed state; Orchestration builds
and obeys the gate; Quality emits facts; Observability investigates; Toptal assesses.
No schedule, lineage/incident service, Toptal policy, transformations, ML detection,
AI chatbot, streaming or enterprise catalog is implemented. No production work.

## Verification request

Independently inspect current files, run the affected checks and edge probes, and
map evidence to each row in acceptance.md. Include adapter/schema behavior, UI
claims, unknown/fail-closed policies and boundary preservation. Do not edit product
code/tests/contracts. Return STATUS: PASS or FAIL and the user's required categories;
write your own dated report/evidence. A failing result returns to implementation
with reproduction, correction, regression, rerun and reverification by this agent.
