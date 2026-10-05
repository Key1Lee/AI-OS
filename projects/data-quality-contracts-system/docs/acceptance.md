# Acceptance and independent verification

The user brief is controlling. The main agent implements; exactly one independent
Data Quality Verification Agent inspects and falsifies without editing product code.

| Criterion | Required evidence |
|---|---|
| Phase 0 / boundaries | Inspected sibling paths, overlap map; no sibling imports or modifications; no scoring, scheduler or incident/lineage engine |
| Provider neutral contract | DataContract, QualityRule, ValidationResult, QualityEvent and gate schemas; strict requests; deterministic serialized exports |
| Valid scenario | Six source concepts plus 10-row fct_orders; explicit net USD semantics; every baseline check PASS |
| Core predicates | Unique incl. NULL/composite keys and duplicates; not-null thresholds; accepted values; required/optional relationship policies; business invariant |
| Schema / grain | Missing column, wrong type, nullable metadata, actual bad values; declared grain supported by unique non-null keys, no inferred semantic claim |
| Controlled failures | Duplicate gives 11 rows / 10 IDs; orphan; missing ordered_at; stale time; completed unpaid; reset/fix restores PASS |
| Gate / status | PASS/WARN/FAIL/UNKNOWN; severity separate from blocking; warn can continue; missing/unknown/stale evidence cannot approve a blocking gate |
| Extended fundamentals | Deterministic freshness, volume, exact reconciliation tolerances and policy-based structural compatibility with edge cases |
| Beginner UX | Visible contract/purpose, predictions, checks, affected rows, consequences, five quality levels, builder, seven progressive concept stages, repair and export |
| Integration contracts | Modeling-v1 mapping; stateless validation API for Toptal; orchestration gate envelope; quality-event-v1 and existing Observability TestResult mapping |
| Optional providers | Tested dbt export/result mapping + executed local dbt lab including unit vs data tests; optional GX mapping without runtime dependency |
| Reproducibility | Engine/API tests, production frontend build, browser journeys including mobile, independent edge probes and recorded evidence |

Required commands: `uv run pytest`, `npm --prefix web run build`,
`npm --prefix web run test:e2e`; optional provider check
`uv run --extra dbt python scripts/check_dbt.py`.
Independent verification reports supported/contradicted/unproven evidence for the
criteria above. Completion requires STATUS: PASS with no blocking correctness gaps.
