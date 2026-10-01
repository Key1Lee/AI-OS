# Data System Map API and contracts

Local base: `/api/map`. Normalized contract: `data-map-v1`; investigation rubric:
`map-investigation-v1`. The engine is independently reusable through
`DataSystemService` and `Graph`; trainer policy is composed at the HTTP boundary.
No uploaded SQL, Jinja or Python is executed. No model or warehouse is contacted.

## Import and exploration

| Method | Path under `/api/map` | Result |
| --- | --- | --- |
| GET | `/systems` | Saved systems and current snapshot identities |
| POST | `/systems/import` | Atomic normalization and immutable snapshot |
| GET | `/systems/{system_id}/graph` | Stage overview, or focused models |
| GET | `/systems/{system_id}/search?q=term` | Names, descriptions and columns, at most 100 matches |
| GET | `/systems/{system_id}/nodes/{node_id}` | Node, direct neighbors, schema, recorded evidence |
| GET | `/systems/{system_id}/nodes/{node_id}/schema` | Declared/catalog-reported columns and unknown fields |
| GET | `/systems/{system_id}/nodes/{node_id}/tests` | Associated definitions/results; `executed_now=false` |
| GET | `/systems/{system_id}/nodes/{node_id}/sql` | Raw/compiled SQL as text; `executed=false` |
| GET | `/systems/{system_id}/nodes/{node_id}/upstream` | Direct parents and other transitive ancestors |
| GET | `/systems/{system_id}/nodes/{node_id}/downstream` | Direct children and other transitive descendants |
| GET | `/systems/{system_id}/nodes/{node_id}/impact` | Direct, transitive and business-output consumers |
| GET | `/systems/{system_id}/nodes/{node_id}/columns/{column}/lineage` | Explicit `unavailable`, with no fabricated mappings |
| GET | `/systems/{system_id}/incidents` | Recorded model/source execution or associated test failures |
| GET | `/systems/{system_id}/incidents/{node_id}` | Bounded failure view, failed tests and execution evidence |
| POST | `/debug/investigate` | Same incident contract; body `system_id`, `node_id` |
| GET | `/systems/{system_id}/explain` | Deterministic metadata tour; blocked during assessment |
| POST | `/systems/{system_id}/query` | Explicit deterministic graph operation |

Import body contains `system_id`, `name`, `manifest`, and optional `run_results`,
`catalog`, `freshness` objects. This release validates the **resource subset** of
manifest v7–v12, or reports an unknown schema when no version is supplied; it
does not claim full dbt JSON Schema validation. Schema YAML must first be compiled
into artifact declarations by the user's dbt workflow. Unsupported resources,
unresolved dependencies, invocation mismatches, cycles and conflicting types are
reported. Optional artifacts are all part of one atomic import. The authored
`commerce-demo` identity cannot be replaced. An active assessment blocks imports.
Timestamp fields accept calendar ISO representations (date, or `T` time with
seconds and optional fraction/`Z`/minute UTC offset), or unknown. Invalid timestamps
are rejected before storage so imported execution evidence cannot break date rendering.

`graph?level=overview` is the default and has stage summaries with no model DAG.
`level=models&focus=node_id` returns the chosen node and its immediate neighbors;
`level=models&layer=staging` expands one stage. Display views have a 14-resource
limit, preserve the focus, filter edges to visible endpoints and report truncation.
Engine traversal remains complete; `all_paths` bounds depth to 64, results to 32,
and expansions to 10,000 with explicit truncation. Tests use separate association
edges and do not become data-flow dependencies.

Query operations: `get_node`, `upstream`, `downstream`, `direct_parents`,
`direct_children`, `impact`, `affected_outputs`, `failed_path`, `changed_nodes`,
`shortest_path`, `all_paths`, `column_lineage`. Use `node_id`, except path operations
use `start` and `end`. Column lineage additionally needs `column`. Natural language
translation and `/analysis/sql` are later features.

## Investigation policy and persistence

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/investigations/current` | Single active investigation or null |
| GET | `/investigations/history` | Durable prior investigations and results |
| POST | `/investigations` | Start/resume with `system_id`, `mode` |
| GET | `/investigations/{id}` | Public scenario, saved draft, ordered actions, telemetry |
| PUT | `/investigations/{id}/draft` | Save answer fields plus optimistic `revision` |
| POST | `/investigations/{id}/hypotheses` | Record candidate `text` as unvalidated inference |
| POST | `/investigations/{id}/submit` | Immutable diagnosis with idempotent `request_id` |
| POST | `/investigations/{id}/end` | End, optionally `learn=true` after assessment |

Answer fields are `observed_failure`, `suspected_origin`, `grain`,
`affected_outputs`, `fix_proposal`, `verification_plan`, `notes`. Grain choices:
`one_row_per_order`, `one_row_per_item`, `unknown`, or an empty draft selection.
Only the original commerce scenario has an authored assessment/rubric. Imported
systems support persisted exploration and drafts; submission returns 409 because
there is no authored grading contract.

Browser draft and hypothesis copies are isolated per tab and survive that tab's
reload. A changed server revision shows the saved draft with an explicit restoration
option for the unsynced copy. Save diagnosis draft writes durable profile storage;
ending or changing mode saves the tab's notes first and stops on a revision conflict.
Unsubmitted browser text is not a replacement for a saved profile draft.

The server freezes the session snapshot and enforces active-assessment visibility
on every incident/query/explanation route. A request parameter cannot enable hints.
Explicit node inspection may retrieve that node's reported measurements without
automatic origin labels. Repeated exposure, including previous learning, prevents
independent credit. Completed results contain only scoped authored answer/action
checks. Root-cause proof, fix validity, prose quality and actual repair verification
are unassessed. `tests_executed=0` and `verification_performed=false` are explicit.
No canonical competency or mastery register is modified.

## Evidence and failures

Facts carry artifact filename, JSON pointer, artifact hash and available timestamp.
Naming-based stage assignment is `INFERENCE`. Declared dependencies are facts
about metadata, not proof of row movement. Compilation failures remain failures;
successful compile is unknown build health. A successful build cannot override a
failed associated test. Multi-target test associations remain ambiguous.

Incident `evidence` contains failed test results; `execution_evidence` contains
failed executions, including operation and error. Learning may report an earliest
observed anomaly only with comparable upstream checks and no known incomplete
lineage. It always leaves `first_bad_node=null`, explains uncertainty and does
not claim a proved cause. Recent changes compare imported snapshots; Git changes
are unavailable in this repository.

Mutation requests require the current token from `/api/config` in
`X-Trainer-Token`, and same-origin requests. Authorization precedes upload reading.
Map mutation bodies are limited to 8 MiB, including chunked requests. Unknown
fields/types produce generic 422 validation errors without reflecting uploaded
secrets. Malformed artifact errors are sanitized; conflicts are 409, missing
resources 404, unavailable storage 503. Recognized secret patterns are redacted
before persistence; sensitive measurement values become unknown to avoid false
comparisons. Secret-bearing resource identities/provenance keys are rejected.
This is conservative pattern filtering, not a comprehensive PII detector; only
authorized, sanitized metadata should be imported.
