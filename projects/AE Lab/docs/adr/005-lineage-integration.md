# ADR-005: Supported observability artifact integration

Status: accepted for Phase 1.

**Context.** The existing observability facade imports dbt-shaped metadata and
results. It has no generic event ingestion API. The Lab needs real incident and
impact behavior without claiming to have executed dbt.

**Decision.** Translate measured row counts, duplicate counts, metric values and
native execution/quality status into supported manifest/run-results shapes.
Mark the adapter producer and explicitly state that no dbt command executed.
Use a Lab-owned observability SQLite database and pin historic snapshot IDs.

**Alternatives.** Modify the sibling API; implement another incident engine;
launch dbt solely to obtain artifact filenames.

**Tradeoffs.** The native engine can derive incidents and downstream impact
through its existing contract. Lineage is declared architecture, rather than
observed row movement. Staging/intermediate aliases teach the path but are not
separate materialized transformations in this slice.

**Consequences.** Evidence preserves producer and measurement basis. Source,
fact and revenue observations are attributed independently. Native root-cause
uncertainty remains visible; learner diagnosis is separately assessed. A future
direct event adapter or real multi-model execution needs its own integration decision.
