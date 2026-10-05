# ADR-001: Canonical Lab event contract

Status: accepted for Phase 1.

**Context.** Native systems expose different result and telemetry shapes. The
learner needs one correlated sequence without losing native provenance.

**Decision.** Use the frozen `ae-lab-v1` Event dataclass with event identity,
logical timestamp, run/scenario, system, asset, type, status, metadata and upstream
assets. Retain native evidence alongside the envelope. Export JSONL and a small
OpenLineage-style parent run/job/dataset projection.

**Alternatives.** Consume five incompatible event streams directly; mandate a
collector or vendor SDK before one scenario works.

**Tradeoffs.** The envelope provides understandable correlation while preserving
system-specific detail in metadata. Logical timestamps reproduce the exercise;
they are not live service timing measurements. The projection is not a tested
claim of complete OpenLineage conformance.

**Consequences.** New event semantics require contract evolution. Adapter
results must identify provenance, and actual measurements must be distinguished
from authored scenario facts and declared simulator output counts.
Native incident openings and resolutions carry correlated incident identity and
opening-event references; a healthy baseline is not an incident resolution.

**Field mapping.** The exported parent-run shape follows the canonical
Run/Job/Dataset model and wire fields documented by the
[OpenLineage API](https://openlineage.io/apidocs/openapi/) and
[object model](https://openlineage.io/docs/spec/object-model/).

| Lab field | OpenLineage-style field |
|---|---|
| `timestamp` | `eventTime` |
| UUID `run_id` | `run.runId`, stable across observations |
| `scenario_id` | `job.name` within namespace `ae-lab` |
| `upstream_assets` | `inputs` dataset namespace/name pairs |
| `asset` | `outputs` dataset namespace/name pair |
| Run start / completion / internal observation | `START` / `COMPLETE` / `OTHER` |

Lab event identity and rich native evidence remain in the canonical JSONL export.
The projection uses a placeholder producer URI and no external collector; a
production producer identity and schema conformance checks are deferred.
