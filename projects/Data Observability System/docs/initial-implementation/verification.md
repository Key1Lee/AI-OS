# Data System Map verification

Date: 2026-10-02, Asia/Seoul. Scope: the requested **first vertical slice**,
plus deterministic dependency impact needed by its incident workflow. This is
implementation verification, not evidence of the learner's engineering mastery.

## Baseline and preservation

The single independent Verification Agent established 101 passing Python tests
before feature edits. Existing SQL, FDE and terminal workflows, exercise versions,
canonical learner registers and learner database schemas are preserved. This
directory is not a Git repository; no Git diff or commit is claimed.

## Self-check evidence

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest -q --tb=short` | 146 passed, 20.14 seconds on the final candidate |
| `make lint` | Python compilation, TypeScript typecheck and launcher shell syntax passed |
| `npm --prefix apps/web run build` | Production build passed; map is a separate lazy-loaded chunk |
| `make check-map-demo` | Executed DuckDB generator reproduces the checked-in artifacts |
| `npm --prefix apps/web run test:e2e` | 11 passed, 24.6 seconds; six map flows and all five original SQL flows |

The Python suite includes original golden branches, cycles and disconnected
components; exact dependencies and paths; bounded path enumeration; schema and
artifact provenance; unknown metadata; test association versus data flow; partial
run/compile/freshness handling; conflict reporting; immutable snapshots and restart;
assessment hiding across every implemented access path; persisted actions/drafts;
idempotent submission; optimistic revision conflicts; storage isolation; redaction;
atomic import rejection; authorized bounded chunked uploads; no-rubric rejection;
and import-boundary assertions.

The browser suite covers the original five SQL workflows and map overview,
assessment before exposure, recorded failure/test inspection, notes and hypothesis
reload, explicit assessment-to-learning transition, saved notes before transition,
evidence-supported learning suspicion, an eight-check investigation with zero
claimed test executions, persisted result, artifact upload, unknown schema/grain,
inert SQL text, narrow light layout, keyboard stage selection and conflicting tabs.
All test and generator runs use temporary or synthetic data; no learner evidence
is created. Screenshots are in `docs/screenshots/map-*.png`.

One existing Starlette/httpx deprecation warning remains. Vite's advisory about
the existing Monaco editor chunk remains; the map does not load Monaco or add a
dependency. These are non-blocking build advisories, not failures.

## Independent falsification and repairs

Exactly one helper was created and used solely for verification. Its initial
backend verdict was FAIL, with concrete independently reproduced defects:

1. List/object resource types and layer values caused uncontrolled errors.
2. Primary-key and observation strings bypassed secret filtering.
3. A focused graph with 20 parents omitted the selected mart after truncation.
4. Failed compile/unknown-operation results disappeared from incident discovery.
5. Execution-only incidents omitted their error evidence.
6. A source column key leaked through its provenance pointer on re-verification.
7. Saving in one tab erased another tab's earlier unsynced notes. Browser copies
   now use per-tab storage, with revision-aware explicit recovery.

Root self-review also reproduced secret-shaped draft selection strings being
persisted. Selection and request identities now reject recognized secret patterns
before storage; ordinary freeform notes are redacted through their existing contract.
Three more regressions reproduced invalid manifest/run/freshness timestamps being
accepted, which could crash date rendering. The adapter now rejects malformed or
unsupported timestamp representations before committing an import. Browser-safe
calendar ISO timestamps and unknown values are supported; the prior snapshot remains
intact after a rejected import.

Regression tests first reproduced the failures, then passed after fixes. Strict
type validation now precedes membership checks. Recognized secrets are removed
from normalized values, and sensitive measurements become unknown rather than
falsely comparable. Secret-bearing provenance keys are rejected atomically.
Bounded display views reserve the selected node; failed executions stay visible
with independent provenance. Guidance does not assume every failure involves a
join. Upload authorization now precedes reading, with an explicit streamed limit.
These regressions live in `tests/regression/test_data_map_verification.py`.

Final whole-feature independent verdict: **PASS**, from the same single
Verification Agent. Its exact [JSON report](verification-agent.json) records the
checks and evidence. It independently ran the full 143-test suite before the
timestamp-only change, the final 45-test engine/API/regression subset afterward,
all 11 browser cases, lint/build/generator checks, and separate adversarial
recovery, secret, timestamp and assessment probes. No blocking findings remain
within this first-slice scope.

The latest local process was restarted on the final backend. Read-only smoke
checks returned health 200, 12 SQL exercises, the five-stage overview with no
default model DAG, and no active investigation in the learner profile. The map is
available at `http://127.0.0.1:8001/map` while that local process runs.

## Explicit later work and limits

Column lineage, SQLGlot/SQLFluff, natural-language translation, AI model reasoning,
additional observability adapters and live connections remain later slices.
The adapter validates supported resource fields, not full dbt JSON Schema.
Synthetic exports do not claim a dbt CLI run. Imported systems have no automatic
authored grade. Investigation scores do not evaluate freeform fix validity,
root-cause proof, explanation quality or an executed repair. No five-minute human
onboarding study, production metadata, external model calls or deployment was
performed. Recognized secret filtering is not a comprehensive PII detector.
