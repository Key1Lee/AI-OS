# Phase 1 independent verification

**Outcome: VERIFIED** for the bounded `ORCH-IDEMPOTENCY-001` vertical slice.
Verified on 2026-10-03 against the current project files. This is completed-change
verification under the [shared verification contract](../../../architecture/verification.md), not an architecture audit
or a certification of broad learner mastery.

The contract source is the user's Phase 1 request: discover and reuse the five
existing systems, define explicit Lab interfaces, execute the reproducible
1,000 → 1,700 → 1,000 scenario, expose native failure evidence, gate remediation
on diagnosis, prove recovery and retry safety, and provide the nine-step learning
sequence with diagrams and compact concept documentation. Scope remains this
single local CLI scenario; later families and production deployment are absent.

## Executed evidence

The verifier inspected the inventory, architecture, five workers, coordinator,
warehouse, state store, learning CLI, event exports, ADRs and project tests.
The verifier changed only this report and independent probes/evidence under
`docs/verification-probes/`; implementation and product tests were left to the
implementers.

| Check | Observed result | Saved evidence |
|---|---|---|
| `uv run pytest -q` | **46 passed in 37.18s** across unit, native contract, integration and CLI E2E layers | [pytest output](verification-probes/pytest.txt) |
| `uv run python docs/verification-probes/independent_phase1.py` | **18 checks passed**, using real native runtimes and temporary Lab state | [probe source](verification-probes/independent_phase1.py), [results](verification-probes/independent-results.json) |
| `uv run python docs/verification-probes/resume_after_adapter_error.py` | **6 checks passed** for interruption, guided resume and stale acceptance prevention | [probe source](verification-probes/resume_after_adapter_error.py), [results](verification-probes/resume-results.json) |
| Current Git status versus discovery transcript baseline | All **232** recorded baseline entries remain; additions are this Lab and an unrelated untracked `FDE Lab` directory | [discovery baseline](phase0-workspace-baseline.txt) |
| Native probe source/config comparison | **398** files across the five siblings have identical SHA-256 values before and after native probes | [native probe results](verification-probes/independent-results.json) |

Successful pipeline results in the independent probes came from the real sibling
engines. The resume probe injects explicit `AdapterError` exceptions at selected
availability boundaries; it delegates every successful modeling result to the
native engine and resumes the rest through all native adapters. It does not
substitute successful engine responses.

## Criterion-to-evidence map

| Required criterion / applicable contract | What must be proven | Evidence observed | Assessment |
|---|---|---|---|
| Existing systems discovered before implementation | Five responsibilities, entrypoints, native interfaces, dependencies, storage and risks are identified | [System inventory](system-inventory.md) covers all five; current workers use those inspected interfaces | Supported |
| Canonical interfaces and scenario registry | Stable scenario ID, deterministic contract and explicit adapter/event/state interfaces exist | `lab/scenarios.py` contains one frozen definition; `lab/contracts.py` defines five protocols, legal states and validated `ae-lab-v1` events | Supported |
| Adapters reuse all five systems | Native retry, SQL assertions, quality gates, incidents/impact and evaluation enforcement run | Native contract tests and both independent execution probes invoke sibling runtimes; workers import the original SDKs instead of copying their engines | Supported |
| Preserve bounded systems | Lab writes and state stay inside its profile; sibling sources/interfaces and canonical learner records are preserved | Workers contain consumer glue; observability DB paths target the selected Lab profile; Python bridges disable bytecode writes; baseline comparison and 398 unchanged sibling source/config digests corroborate isolation | Supported, with baseline limits below |
| Synthetic commerce dataset works | Seeded orders and related tables are reproducible, contain 1,000 stable order keys, and retain exact cents | Unit fixtures and independent arithmetic probes reproduce seed 42 revenue **53,945.00**; custom seed 7 native integration yields **53,955.00**; modified pinned fixture is rejected | Supported |
| Vertical slice works and failure is reproducible | A real 700-row committed write survives a crash, then native retry appends the full source | Independent default scenario observes attempt warehouse counts **700, 1,700**, pipeline `SUCCESS`, 700 extra duplicate IDs and revenue **91,448.50**; configured 37-row fault also passes integration checks | Supported |
| Modeling/quality detect corruption without hidden deduplication | All actual fact rows remain visible; duplicate keys cannot escape native input limits | Native modeling reports `FAIL` while preserving 1,003 rows in the adversarial boundary probe; quality covers all 1,003 rows and reports three extra duplicates; 181-row modeling and 201-row quality key groups fail closed rather than split | Supported |
| Observability captures failure and business impact | Native incident, failed test/execution, measured revenue and downstream dashboard evidence exist | Native observability contracts show failed fact evidence, duplicate failures, six lineage edges and `executive_dashboard` impact; faulty publication is blocked and dashboard revenue is marked untrusted | Supported |
| Learner can diagnose it | Evidence precedes diagnosis; unsupported answers cannot authorize repair | CLI E2E observes fault evidence before diagnosis; wrong structured diagnosis and prose-only keyword answers fail; `fix` rejects them; native Toptal authoritative enforcement evaluates accepted structured fields | Supported for authored fields |
| Remediation succeeds | Historical duplicates are repaired and subsequent writes update or insert by a stable key | Real recovery returns exactly 1,000 complete raw and fact rows equal to the independent source, unique key installed, native model/quality `PASS`, revenue **53,945.00**, empty current incident list and trusted publication | Supported |
| Regression proves safety | Repeating a recovered load, including another committed partial attempt and retry, does not change data | All eight machine criteria pass; both rerun attempts remain at 1,000 rows; complete row equality is asserted. Compensating +1/-1 cent row corruption preserves total/count but makes rerun stability fail and cannot award mastery | Supported |
| Explicit resumable state | Legal state transitions persist; interruptions cannot silently count as recovery or retain stale acceptance | Unit transition checks reject jumps; interrupted fault resumes to exactly 1,700 rather than another append; interrupted recovery cannot verify early; actual `learn --resume` finishes FIX → VERIFY → RECALL → CONNECT; interrupted new verification suspends prior mastery | Supported |
| Exact educational sequence and assistance boundaries | ORIENT → PREDICT → RUN → OBSERVE → DIAGNOSE → FIX → VERIFY → RECALL → CONNECT; no early answer | E2E asserts all nine headings in order, with no 1,700/upsert disclosure before RUN; wrong prediction still permits observation. Automated assistance cannot award local `MASTERED`; reset retains history | Supported |
| Canonical telemetry and lineage semantics | Event identity/correlation/order and upstream metadata are inspectable; incidents have actual lifecycles | Unique correlated event IDs and increasing logical timestamps are asserted; baseline emits no invented incident resolution; recovery resolution references its opened event; repeated verification retains one parent completion event; parent OpenLineage-style START/OTHER/COMPLETE mapping is tested | Supported for documented projection |
| Architecture diagram exists | Scenario can emit healthy, failed, downstream-impact and recovery Mermaid views; lineage walks backward from the dashboard | `lab.telemetry` produces all three views per saved run and upstream asset slices; CLI lineage and documentation include the source-to-dashboard path with a quality branch | Supported |
| Documentation explains why | Compact concept page and explicit architecture decisions explain cause, signal, fix and limits | [Idempotency](concepts/idempotency.md) contains WHAT/WHY/WHERE/FAILURE/SIGNAL/FIX/INTERVIEW/RECALL; five ADRs record events, boundaries, warehouse, states and declared lineage | Supported |

## Findings corrected and independently rechecked

The verifier found three material defects during implementation: a healthy
baseline emitted `INCIDENT_RESOLVED` without an opened incident; a failed new
verification could retain `VERIFIED` and permit `MASTERED`; and guided resume
after an interrupted repair tried VERIFY before recovery existed. Implementers
corrected these. Final probes establish correlated incident resolution, suspended
stale acceptance, rejected recall after failure, and successful guided recovery
resume. No material finding remains open within the Phase 1 contract.

## Evidence limits and handoff

- The discovery baseline was reconstructed from the initial tool transcript;
  discovery-time content hashes were not captured. Git flags cannot prove earlier
  byte-level preservation inside already modified/untracked sibling files.
  The independent before/after native probes do establish byte-level preservation
  of the 398 source/config files during verification. Existing unrelated changes
  remain visible and were not restored or attributed to this task.
- Orchestration is native deterministic simulation; the Lab performs the actual
  durable writes. Native model SQL is real. Staging/intermediate lineage nodes
  are declared conceptual aliases, and the dashboard is a declared consumer.
- Observability imports honestly labeled adapter-produced dbt-shaped metadata;
  no dbt command, generic collector or live BI refresh is claimed. Freshness is
  `NOT_MEASURED`. Complete OpenLineage conformance is outside this projection.
- Exact structured answers and local recall are tested. Free-text reasoning,
  unseen-scenario transfer and canonical Toptal mastery are unassessed. Guided,
  repeated and automated exposure remain explicitly qualified.
- Results apply to the installed native runtimes and one local user. General
  joins/window functions, source-version conflicts, distributed/concurrent
  writers, packaging across machines and later scenario families remain deferred.

The implemented Phase 1 slice can be demonstrated and used for the requested
focused learning exercise. A later scenario requires its own approved contract
and checks; this result does not establish acceptance for later phases.
