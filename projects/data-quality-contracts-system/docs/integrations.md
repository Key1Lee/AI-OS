# Integration interfaces

All connections here are serialized, stateless local interfaces. Sibling runtimes
are unchanged. The five systems can operate independently; live wiring is deferred.

## Modeling → Quality

`POST /api/adapters/modeling` accepts `modeling-lab-v1` with explicit `fact_contract`
(grain, primary_key, columns, owner, semantic_meaning), plus optional `dataset_id`.
The existing Modeling scenario endpoint already exports `fact_contract`. Only its
desired contract is mapped: a ModelDefinition's observed DuckDB columns can be
nullable even when its designed contract says NOT NULL. Observed metadata is not
a new promise. Unsupported types are rejected, including naive TIMESTAMP, rather
than guessing timezone or precision. Keys and gross-vs-net semantics are preserved.
The generated Quality contract adds schema, key and required-value checks; it
does not invent the producer's business/FK rules. Those require an explicit policy.

## Orchestration → Quality

Call `POST /api/validate` with the contract, dataset map, explicit executed_at,
run_id, optional additional_rules and optional rule_ids. Rules are compiled from
the contract, not replaced by client-supplied result statuses. The response includes
`quality-gate-v1` publication eligibility. The caller owns execution order:

```text
build_fct_orders → validate → OPEN: publish_mart
                         ↘ BLOCKED: withhold
```

Missing results, UNKNOWN, duplicate evidence, stale input fingerprints and mismatched
target/rule/run/time cannot open a blocking gate. A selected single-rule request
is useful for diagnosis, but leaves the other required evidence missing and the
gate blocked. INFO/WARNING/CRITICAL is independent from a rule's blocking flag.

## Quality → Observability

`quality-event-v1` preserves deterministic FACT evidence, expected/actual, dataset,
rule, severity, counts, run/time/fingerprint. `POST /api/adapters/observability` maps
an event into the existing TestResult shape in `data-map-v1`:

| Quality | Observability |
|---|---|
| PASS | HEALTHY |
| WARN | WARNING |
| FAIL | FAILED |
| UNKNOWN | UNKNOWN |

The consumer maps dataset IDs to its own graph node IDs and stores provenance.
The quality app has no monitoring history, incident workflow, graph/lineage engine
or blast-radius analysis. Its fixed five-node picture is an authored learning flow;
the upstream stages are explicitly context, and only the fact is validated here.

## Toptal → Quality

`GET /api/scenarios` and `GET /api/scenarios/commerce-current-orders-v1` expose the
deterministic learning scenario. `POST .../validate` accepts named corruptions,
an explicit clock, run_id, additional_rules and optional selected rule IDs. It
returns evidence only: no score, grading rubric, hints, mastery or learner telemetry.
These lab endpoints expose educational facts openly; they are not an assessment
answer-security boundary. Toptal must own access, disclosure and scoring itself.

The first five corruptions are `duplicate`, `orphan`, `schema`, `stale`, `unpaid`.
Removing them restores the original fixture; no persistent data is modified.
Exports include all current rows and the input fingerprint. Sample evidence is
bounded to 8 rows and has protected 1-based `_row_number` pointers.

## Contract artifacts

`GET /api/contracts` and `/openapi.json`; `make contracts` regenerates checked-in
OpenAPI plus valid, duplicate, warning and missing-column bundle/event examples.
Money uses strings, integer columns are signed 64-bit, timestamps have explicit
timezones, and decimal constraints/thresholds are finite and bounded.
Reconciliation tolerance uses exact comparisons: absolute OR relative, inclusive;
a nonzero difference at a zero source total cannot pass relative tolerance.

The core clock is deterministic. The fixture's 2026-10-02 09:00 Asia/Seoul start
does not follow today's wall clock; stale mode advances it by three hours.
