# Data System Map — implementation architecture

Build date: 2026-10-02, Asia/Seoul. Authorization: the user's Data System Map
specification, especially FIRST VERTICAL SLICE and its verification contract.

## Current architecture and invariants

The existing application is React/TypeScript/Vite with FastAPI on loopback port
8001, a separate DuckDB subprocess harness, SQLAlchemy/Alembic and SQLite training
records. The older FDE browser app and terminal trainer remain separate.
Independent baseline: **101 Python tests passed**. This directory is not a Git
repository. No dbt artifact adapter or graph engine currently exists.

Preserve the SQL API, editor, exercise versions, learner databases, launchers and
four canonical assessment registers. This feature adds separate metadata and
investigation records. Demonstration/test runs are never learner mastery evidence.

## Target boundaries and data flow

`dbt artifact JSON → dbt adapter → provider-neutral contracts → immutable SQLite
snapshot → deterministic graph query → visibility policy → React graph/details`

- `data_system_map/`: reusable deterministic engine, normalized contracts, dbt
  adapter, adjacency traversal, snapshot repository and evidence explanations.
  It imports no trainer code and executes no uploaded SQL, Jinja or Python.
- `trainer/data_map/`: authored scenario, candidate actions, persisted telemetry,
  visibility policy and deterministic assessment rubric. It consumes normalized
  engine contracts; it imports no dbt adapter implementation.
- `apps/api/data_map.py`: composition and stable `/api/map` HTTP contracts using
  the existing local token/origin boundary. Graph storage and assessment storage
  are separate SQLite profiles; existing training schemas are not migrated.
- `apps/web/src/data-map/`: reusable React view, available through trainer
  navigation and a standalone `/map` page. Small focused graphs use accessible
  HTML nodes and SVG edges rather than a new graph dependency.
- Explanations in this slice are deterministic and source-linked. An AI reasoning
  provider remains optional/later; no credential, repository or data value is sent
  to a model. AI unavailability does not affect the map.

## Normalized contracts

Versioned contracts represent systems/snapshots, nodes, columns, declared
dependency edges, executions, tests, incident observations and provenance.
Unknown grain, key, nullable, owner, schema or runtime fields remain null.
Every conclusion has FACT, INFERENCE or AI_HYPOTHESIS classification. Declared
metadata is identified as declared; a passing build does not prove data quality.

Snapshots are content-addressed and immutable. Nodes and edges have normalized
adjacency storage. Import is atomic; malformed optional artifacts cannot replace
the prior graph. Missing dependencies, conflicting metadata and cycles are
preserved as issues rather than fabricated relationships or silently resolved.

dbt normalization uses manifest `nodes`, `sources`, `exposures`, `metrics` and
`depends_on.nodes`; run results identify executed nodes/tests by `unique_id`.
Catalog and freshness are optional. Resource classification from naming is
explicitly inferred. SQL is displayed on explicit inspection, never executed.
Column lineage and SQL AST analysis are not claimed in this first slice.

## First vertical slice and beginner experience

1. Load a small commerce demonstration through the same dbt ingestion contract.
2. Default to five major stages; expand one stage or a chosen model's neighbors.
3. Select a node to inspect declared schema, grain, inputs/outputs, tests and SQL.
4. Interpret build status separately from test and freshness evidence.
5. Show the observed failure, relevant upstream path and downstream business
   outputs. Establish an earliest suspicious node only with comparable evidence;
   otherwise explicitly say it cannot yet be established.
6. Start a persisted learning or assessment investigation. Capture explicit
   inspections, questions/hypotheses, diagnosis, fix proposal and verification
   plan. Score only objective facts and observable actions; prose quality remains
   unassessed. Reviewing recorded tests is not represented as executing dbt.

The commerce sample is original synthetic data. A trusted generator executes its
transforms and checks in DuckDB and exports demonstrative dbt-shaped metadata.
It does not claim that dbt ran or that any production system was inspected.
The bug changes order grain in an intermediate join, propagates duplicates to a
fact model and inflates a revenue mart.

Assessment policy is authoritative on the server. An active assessment restricts
all map graph, incident, query and explanation endpoints globally; changing
a request's mode cannot reveal the answer. Requested node/tests/schema inspection
may reveal legitimate diagnostic evidence, but never an automatic first-bad-node
label, solution or unsolicited hint. Ending the assessment and learning is an
explicit audited transition. Prior learning exposure disqualifies independence.
Local machine owners can inspect project files; those files are not a secrecy
boundary against the owner.

## Risks and limits

- Artifact versions and partial runs: validate supported shapes, retain artifact
  identities/timestamps, distinguish unknown/unexecuted/skipped from healthy.
- Conflicts and stale results: surface disagreement and provenance; correlation
  or a changed SQL file is not causation.
- Cycles/large graphs: bounded traversal/path enumeration, explicit truncation,
  no full DAG by default, stable node ordering, 14-resource display limits that
  preserve the selected focus or observed failure.
- Storage/import errors: preserve previous snapshots, sanitize errors and bound
  uploaded JSON sizes; no arbitrary server file path or network ingestion.
- Security: metadata-only import, no artifact execution, escaped React output,
  local origin/token checks, conservative secret redaction, no live model calls.

Later stages are SQLGlot/SQLFluff analysis, column lineage, natural-language
queries, further adapters, production runtime connections and model reasoning.
Direct/transitive traversal and affected-output analysis are included now because
the initial incident workflow needs them.

## Files and test plan

Add the engine, trainer integration, API router, reusable UI, original fixture
generator/artifacts, Python contract/golden/integration/regression tests, browser
smoke tests and feature documentation. Modify only API composition, navigation,
the standalone entry, build checks and additive README/configuration.

Self-test parsing, schema/provenance, cycles/branches/disconnected nodes, paths,
impact, uncertainty, atomic failed imports, snapshot/session restart, request
idempotency, assessment leak routes, security, old trainer regression, typecheck,
production build and actual browser interactions. The single Verification Agent
then independently attempts to falsify these contracts; fix blocking findings
and return to the same agent until PASS or a genuine limitation is documented.
