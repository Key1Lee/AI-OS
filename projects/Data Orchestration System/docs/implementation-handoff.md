# Orchestration Verification Agent handoff

## Contract source and objective

The user's original request is preserved in the chat attachment. Implement its FIRST
VERTICAL SLICE, with the beginner completion concepts taught through five bounded
e-commerce variations. Scope and criterion-to-evidence requirements are in
`docs/acceptance.md`. This handoff locates claims; it is not independent proof.

## Components and changed scope

All changes are new files within this formerly empty sibling project. No sibling
or shared AI-OS implementation was edited. Root inspection found unrelated in-progress
changes in other projects. Package identity is `data-orchestration-lab`; physical
root remains `Data Orchestration System`, matching the neighboring project's convention.

- `src/engine/{types,validation,graph,simulator}.ts`: typed, runtime-validated DAG,
  stable ordering, pure event stepping, explicit clock, eight states, retries,
  timeout errors, trigger rules, workers and pools, grounded explanations.
- `src/engine/{backfill,modeling,scenarios,schemas}.ts`: global backfill coordinator,
  partition planning/isolation, metadata-preserving Modeling envelope adapter,
  five authored scenarios, event/scenario JSON Schemas.
- `src/{App,main}.tsx`, `src/ui/`, `src/styles.css`: progressive stage/task/asset
  views, inspector, attempt timeline, backfill controls, rerun comparison, concept
  guide, beginner/advanced presentation, memory-only history and JSON downloads.
- `scripts/serve.mjs`: loopback static production serving. No mutation/API backend.
- `scripts/export-contracts.ts`, `contracts/`: generated schemas and examples.
- `tests/`: behavioral and integration invariants. `e2e/`: production browser flows.

## Implementation validation and expected independent work

Run `npm test`, `npm run build`, `npm run test:e2e` yourself. Attempt counterexamples
beyond the suite: DAG reorderings and diamonds, retry release/exhaustion, conditional
triggers and skip propagation, calendar boundaries, existing partition replacement,
global workers/resource pools, path duration, output reruns, event timestamps, malformed
inputs, repeatability, and UI explanation truth. Inspect system boundaries. Map every
acceptance criterion to direct evidence. Browser screenshots are available for UX
inspection, but they do not replace the verifier's own observations.

## Explicit implementation limits

No real SQL, real dataset loading, candidate scoring, hint policy, incident management,
monitoring, external app adapters, background scheduler, or durable session database.
Rerun counts are an authored replace/append simulation. The backfill example has its
own in-memory seeded partition registry. Model metadata is consumed through an envelope,
not a live connection. Schedule support is daily and limited to Asia/Seoul or UTC.
The successful-run duration bound assumes successful enabled tasks and unlimited
resources; actual traces expose contention/retry/failure. The asset view shows produced
data separately from the producer task, using the same declared dependency graph.

## Verification protocol

Exactly one tool-capable independent helper is authorized. Read parent
`architecture/verification.md` and this project's `AGENTS.md`. Inspect and run probes;
do not edit product code, product tests, or approved contracts. You may save independent
temporary probes and your evidence/report under `docs/verification-evidence/`.
Report STATUS: PASS | FAIL, TESTS EXECUTED, BLOCKING FAILURES, EXECUTION ERRORS,
ARCHITECTURAL VIOLATIONS, MISSING TESTS, UX FINDINGS, EVIDENCE, RECOMMENDED FIXES.
PASS only with no blocking correctness errors and supported required criteria. Send
defects to the main agent; use the same helper for re-verification after fixes.
