# Provider adapters and current dbt functionality

The core validator is provider neutral and runs without dbt or Great Expectations.
References were checked on 2026-10-02. Installed runtime evidence is separate from
documentation: `docs/test-results/dbt.json` records dbt Core 1.12.5 / dbt-duckdb 1.11.0.

dbt's [data-test documentation](https://docs.getdbt.com/docs/build/data-tests)
distinguishes built-in generic tests, custom generic tests and singular SQL assertions.
The exporter uses `data_tests` and explicit `arguments`, supported by
[current property syntax](https://docs.getdbt.com/reference/resource-properties/data-tests).
The optional lab runs uniqueness, not-null, accepted-values and relationships on
models, plus source tests, custom key/completeness/relationship/value macros and
a singular completed-is-paid assertion. The [model contract](https://docs.getdbt.com/docs/mesh/govern/model-contracts)
is enforced on the produced fact's columns/types. A native
[unit test](https://docs.getdbt.com/docs/build/unit-tests) supplies two controlled
inputs to a separate tiny example; it is not a dataset quality assertion.

## Scope and conformance

`dbt_export` returns YAML, required macro names and explicit unsupported rule IDs.
Copy the macros from `dbt_lab/macros/quality_rules.sql`; do not pretend that a
standard dbt `unique` test also enforces NULL policy. Thresholds beyond the macro's
18 decimal places and mixed/non-string categories are unsupported rather than
silently rounded/coerced. Freshness, volume, reconciliation and business/consistency
rules use core validation except for the separately authored singular paid test.

`dbt_result` normalizes a single explicitly bound recorded test result, not a whole
manifest/artifact-ingestion service. That service already belongs to Observability.
Missing, skipped, error, unbound, malformed or contradictory evidence is UNKNOWN.
Recorded PASS/WARN/FAIL describes dbt's result; no new query was run by the mapper.
Its failures can count duplicate groups or aggregate rows, so the domain's
`failed_rows`, `total_rows` and failure rate remain unknown. Empty dbt row predicates
may PASS; the core deliberately returns UNKNOWN. The core gate is computed from
its own current validation bundle and includes volume/schema/arrival evidence.
Never substitute a partial set of provider records for the full gate contract.

The local dbt verifier uses temporary copies and databases. Positive artifacts are
copied to ignored `dbt_lab/target/`; checked-in summaries/logs prove all five cases.
It disables anonymous usage telemetry and needs no cloud warehouse or credentials.
The initial Python build needed a trusted CA bundle for a dbt binary dependency;
`make check-dbt` passes the installed certifi bundle without disabling verification.

## Great Expectations

`gx_design` maps eligible column checks to optional GX class/argument designs.
It does not import, install or execute GX. NULL, mostly, grouping and failure-count
semantics must be conformance-tested before a consumer uses GX evidence for gates.
The endpoint explicitly reports `executed: false`; unsupported kinds are visible.
