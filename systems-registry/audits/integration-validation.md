# Cross-system integration, failure and recovery validation — Step 5

Date: **2026-10-06, Asia/Seoul**. Scope: the latest Step 5 request, existing dependency graph and approved [remediation plan](remediation-plan.md). **Overall: PARTIALLY VERIFIED.** The executed AE adapter chain detects and recovers from the required failures; the independently installed Modeling path fails its prerequisite checks. This is a validation report, not a completed remediation or production-readiness claim.

Fresh execution evidence: [artifact directory](/Users/key/.codex/artifacts/aios-step5-20261006-225013). All profiles, injected faults, answers, SQL writes and provider responses used for validation are synthetic. No production deployment, live model call, real learner-profile repair, new system, dependency installation or product-code correction occurred during Step 5. Exactly the existing Modeling, Orchestration and Quality verifiers were reused, read-only. The only workspace artifact authored for Step 5 is this report.

**Step 4 preflight.** The [execution report](remediation-execution.md) records A-02/A-01/A-03/A-04 accepted, but A-05/A-07/A-06 still pending. That contradicts the request's premise that all of Step 4 was complete. Current A-05 code is present and fresh independent verification passes; this report does not silently rewrite the Step 4 handoff. A-07 still fails, and A-06 normal-path acceptance is stopped. Previous temporary Step 4 evidence/backup directories are unavailable; this run preserves new logs and synthetic state outside temporary storage. Current tests, rather than expired historical evidence, support the conclusions below.

| Remediation / prerequisite | Fresh evidence | Step 5 status |
| --- | --- | --- |
| A-02 original interview request boundary | Original API/boundary suite, included in 113 Toptal checks; bad Host/Origin/token rejected before state/provider effects, valid requests/idempotency preserved | VERIFIED |
| A-01 composed publication trust | AE current core hash equals the accepted Step 4 hash; 63 unit/native-contract/integration checks plus fresh native corruption/recovery probe | VERIFIED |
| A-03 assessment eligibility / rebuild tooling | Terminal tests included in the 113 checks; outage/fallback, recovery, authoritative failures, synthetic rebuild safety and noncrediting diagnostics pass | VERIFIED within code/tool scope; real historical profiles unverified |
| A-04 backfill invocation identity | Independent 40 tests, engine/schema probe and one focused production-build browser test | VERIFIED |
| A-05 presence relaxation | Current patch independently passes B5-1–B5-4 and 103 targeted tests; required→optional is explicit BREAKING | VERIFIED current behavior; Step 4 acceptance record remains incomplete |
| A-07 installed Modeling runtime | Direct pytest exit 126; isolated installed import and supported launcher import exit 1 | FAILED; affected installed path stopped |
| A-06 sampling restriction | Step 4 reports pending; prerequisite A-07 fails | BLOCKED; sampling execution/acceptance not attempted |
| Registry | `systems-registry/.venv/bin/python systems-registry/scripts/validate_registry.py` exits 0, 10 systems; relevant graph/path/ownership entries match inspected interfaces, including rebuild CLI | VERIFIED structural metadata, not executable health |

Required runtimes for the AE native adapter path did execute: Node/TypeScript Orchestration and sibling Python engines for Modeling, Quality, Observability and Toptal. AE supplies its existing source paths to those subprocesses. The normal Modeling installation is separately broken; successful AE execution cannot qualify it. Orchestration's focused browser server starts/stops; original/Quality API construction is exercised with TestClient. A live provider server and every project's standalone UI/API were not required for this offline adapter chain and were not certified.

## Baseline Test

Executed the default AE commerce fixture through all five genuine sibling adapters, with `seed=42`, explicit crash threshold 700 and an isolated profile. Probe: [ae_probe.py](/Users/key/.codex/artifacts/aios-step5-20261006-225013/ae_probe.py). Run ID: `79638507-cc12-4d95-9c4e-fc8744fc0f12`.

| Measurement | Healthy observed result |
| --- | --- |
| Source / loaded / materialized / validated / distinct orders | 1,000 each; zero duplicate extras |
| Revenue | **USD 53,945.00**, exact Decimal reconciliation with the pinned source |
| Native attempts | One SUCCESS; no hidden retry |
| Pipeline / Modeling / Quality | SUCCESS / PASS / PASS; native Quality gate OPEN |
| Publication / dashboard | ELIGIBLE / trusted=true |
| Observability | Native snapshot, six declared lineage edges, no incidents |
| Fixture SHA-256 | `ce5cc382fd6e9f3a8dfa73e387d39c8ef003fc58edd578f35f00effb56b6506c` |

Both SQLite tables were read back and compared with the complete independent source, not just totals. Evidence: [native results](/Users/key/.codex/artifacts/aios-step5-20261006-225013/ae-native-evidence.json), [probe log](/Users/key/.codex/artifacts/aios-step5-20261006-225013/ae-native-probe.log), and the run's `fixtures.json`, `baseline.sqlite`, `warehouse.sqlite`, `evidence.json`, `events.jsonl`, `openlineage.json` and `observability.sqlite` under `ae-profile/<run-id>/`.

This fixture's metric is gross completed-order USD revenue before refunds. It does not execute Semantic's separate net-revenue definition or Quality's independent net/refund fixture. Freshness is intentionally NOT_MEASURED. Staging/intermediate assets are declared aliases, and the dashboard is a declared consumer, not a live BI service.

## Cross-System Test Matrix

Selected actual runtime relationships first; optional artifact adapters are distinguished from deployed connections.

| Path | Execution selected | Status / practical limit |
| --- | --- | --- |
| AE → Orchestration → AE loader | Native scheduler determines failure/retry attempts; AE performs real partial SQLite commits and full retry | VERIFIED local execution |
| AE loaded data → Modeling → AE materialization | Native DuckDB query and exact-row oracle across complete key groups; AE persists certified output | VERIFIED adapter path; installed Modeling entrypoint FAILED |
| AE materialized rows → Quality | Native contracts, every row validated, complete key groups, duplicate/malformed/UNKNOWN rejection | VERIFIED |
| AE Modeling/Quality measurements → Observability | Genuine immutable snapshot import, measured failed test/execution, dashboard impact and recovery | VERIFIED local adapter chain |
| AE structured learner answers → Toptal | Genuine authoritative evaluator, strict fields, rejected wrong diagnosis, repair gate, guided CLI | VERIFIED bounded objective evaluation |
| Toptal → AI-OS provider transport / structured output | Injected SDK stubs exercise real central transport/parse contract; invalid structure and outage controls | VERIFIED offline; live inference quality/readiness unverified |
| AI-OS proposals → authorized tool → observed state | Real SQLite state with deterministic fake providers; failed claim, no-op mutation, verified durable recovery/repeat | VERIFIED controlled workflow |
| Serialized Modeling → Orchestration | Nine committed producer-schema-valid definitions, dependency conversion, rejection/recovery and schema-valid events | VERIFIED artifact compatibility; placeholder tasks execute no SQL |
| Serialized Modeling → Quality | Genuine native ContractDefinition with explicit synthetic input; strict converter/API and clean recovery | VERIFIED artifact compatibility; default fixture exporter FAILED |
| Serialized Quality → Observability TestResult | Genuine native contract validation; PASS/WARN/FAIL/UNKNOWN mapping and provenance | VERIFIED artifact compatibility; separate deployed wiring unverified |
| FDE → AI-OS / siblings | Registry/guidance references only; no registered executing dependency | NOT APPLICABLE as runtime integration; FDE local scenario tested |
| Modeling → Semantic in this ORDER path | No installed connection in registry; Semantic explicitly owns independent artifact contracts | NOT APPLICABLE to executed path; no connector invented |

## Order Data Trace

Canonical entity: **O0001**, customer **C001**, completed order, **USD 10.79**, ordered at `2026-10-02T00:00:00+00:00`. Its original row appears once in healthy raw/fact output, twice in the faulty raw/fact output and once after repair. [Order trace and lineage](/Users/key/.codex/artifacts/aios-step5-20261006-225013/ae-native-evidence.json) retains the rows and source hash.

| Boundary / owner | Input → output and state | Contract / observed validation | Failure behavior |
| --- | --- | --- | --- |
| Source / AE | Pinned fixture row → full independent 1,000-order reference in the run's `fixtures.json` | Fixed seed, explicit USD values and SHA-256 pin; source read agrees with original row | Changed fixture bytes reject, rather than replacing the oracle; covered by AE foundation checks |
| Orchestration / native engine; writes / AE | Declared transient crash → FAILED attempt + SUCCESS retry; actual writes to `orders_raw` | `orchestration-event-v1`; ordered attempts correlated to AE run/phase; measured warehouse counts recorded separately | First attempt commits 700; unsafe append retry leaves 1,700; safe upsert keeps 1,000 |
| Modeling / native engine; materialization / AE | Actual loaded occurrences + independent source → DuckDB `loaded_orders` projection → persisted `fct_orders` | `modeling-lab-v1` native build result, explicit order grain/key, exact rows/count/revenue; bounded key-complete batches ≤180 | Duplicate or wrong rows FAIL; duplicate occurrences remain visible; installed runtime separately fails |
| Quality / native engine | Persisted fact rows + declared schema/key/time → results/gate/events; stateless | `data-contract-v1`, `quality-bundle-v1`, `quality-gate-v1`, `quality-event-v1`; complete coverage in key-complete batches ≤200 | Duplicate/malformed/missing evidence prevents gate opening; wrong value with valid schema can pass its narrower checks |
| Revenue/publication / AE | Native Model receipt + actual fact rows + source + Quality receipt → exact gross revenue and trust labels in run evidence | AE `lab/contracts.py` and shared `publication_decision`; native certified rows must match persisted rows | Execution SUCCESS or Quality OPEN alone cannot establish trust; wrong exact rows block publication even with a correct total |
| Observability / native engine | Measured count/revenue/test/execution artifacts → per-run immutable metadata snapshots and declared dashboard lineage | `data-map-v1`; provenance says adapter-produced metadata, no dbt execution; cents remain exact | Measured fault opens fact incident and downstream impact; clean recovery resolves current incident while preserving pinned failure |
| Consumer / AE + native Toptal | Observed evidence → learner prediction/diagnosis → controlled repair → machine verification | `ae-lab-v1`; authoritative structured checks and explicit unassessed prose/transfer | Wrong diagnosis cannot trigger repair; incomplete/failed verification cannot restore VERIFIED |

The final business value is explainable: a Decimal sum of the complete, exact source-equivalent `fct_orders` rowset after native modeling, with one occurrence of O0001 contributing USD 10.79. Lineage edges describe asset dependencies; they are not claimed as observed row-level lineage. No real Semantic service or BI consumer participated.

## Contract Results

| Producer | Consumer | Existing contract | Result / evidence |
| --- | --- | --- | --- |
| Native Orchestration | AE loader | `orchestration-event-v1`; AE OrchestrationAdapter protocol | VERIFIED — native retry and measured commits; 63 AE checks and native probe |
| Native Modeling | AE | `modeling-lab-v1`; ModelingAdapter protocol with native build receipts | VERIFIED on injected-source adapter — exact-row, wrong-amount and equal-total corruption controls; three independent native checks pass |
| Native Quality | AE | `data-contract-v1`, `quality-bundle-v1`, `quality-gate-v1`, `quality-event-v1` | VERIFIED — clean/duplicate/malformed/UNKNOWN/key-group contracts and outage/recovery |
| AE measurements | Native Observability | AE ObservabilityAdapter protocol plus existing `data-map-v1` import/result contracts | VERIFIED — native snapshot, schema, incident/impact, stable identity, immutable history and contradictory evidence rejection |
| AE authored questions/answers | Native Toptal | `training.models.Question/Evaluation`, `DeterministicReport`, `ae-lab-idempotency-objective-v1` | VERIFIED — structured positive/negative/strict-type/terminology-only controls and source provenance |
| Native Modeling definitions | Orchestration converter | Committed `docs/contracts.json`, `modeling-lab-v1` producer schema; `orchestration-scenario-v1` | VERIFIED offline — nine definitions, six sources, three placeholder tasks; malformed parents/version/duplicates/cycles reject, restored parent succeeds |
| Native Modeling designed contract | Quality converter/API | `ContractDefinition` serialized in `modeling-lab-v1` → `data-contract-v1` | VERIFIED with explicit synthetic native input; default fixture exporter fails; no default/deployed integration claim |
| Quality events | Observability TestResult | `quality-event-v1` → native `TestResult` | VERIFIED offline — all four statuses, provenance, invalid-status rejection and clean recovery |
| Quality comparator | Compatibility API consumer | Existing `contract-compatibility-v1` | VERIFIED — presence-relaxed BREAKING; nullable/non-nullable, policy, missing-column transition and API malformed/recovery controls |
| Toptal interviewer | AI-OS parsed provider transport | Existing `InterviewerDecision` Pydantic schema and central parsed-provider contract | VERIFIED offline — real central path with SDK stubs; malformed parsed result rejects |
| AI-OS | Workflow-owned handlers | `IntelligenceRequest`, `ToolDefinition`, `IntelligenceResult`, bounded argument schema and verifier callbacks | VERIFIED with actual synthetic SQLite state; model claim is not execution proof |

AE has explicit Python adapter Protocols, but their worker aggregates return `dict`; there is no separate strict versioned JSON schema for every aggregate receipt. Native envelopes and executed assertions protect the tested fields. This narrower contract limitation is recorded below rather than adding a new schema during validation.

## Retry/Idempotency Scenario

**VERIFIED.** Real isolated warehouse writes adapted the requested 700/1,000 scenario exactly:

| Phase | Attempt states | Warehouse rows after each attempt | Duplicate extras | Revenue / trust |
| --- | --- | --- | --- | --- |
| Healthy baseline | SUCCESS | 1,000 | 0 | USD 53,945.00 / trusted |
| Controlled append fault | FAILED → SUCCESS | **700 → 1,700** | 700 | USD 91,448.50 / BLOCKED, untrusted |
| Authored repair + recovery | FAILED → SUCCESS | **1,000 → 1,000** | 0 | USD 53,945.00 / trusted |
| Verification rerun and repeated verification | FAILED → SUCCESS | **1,000 → 1,000** each time | 0 | Exact source/fact equality and all eight recovery checks PASS |

The 1,700 state is the intentional unsafe control, not the accepted repaired final state. Repair atomically removes the old duplicates, enforces the existing order key and applies upsert. Whole rowsets are checked, not just `COUNT(DISTINCT)`. Native scheduler attempts and five-minute virtual retry delay remain visible. Original fault receipt and snapshot remain unchanged; canonical events are unique and run-correlated.

Backfill identity independently passes zero event-ID overlap for a new recovery invocation, identical same-ID trace reproduction, unchanged earlier payloads and the focused repeat-export/reset/reload browser case. Automatic task retry retains one run identity. Orchestration's simulation alone is not proof of durable SQL writes; the AE probe supplies that proof.

## Silent Corruption Scenario

**DETECTED / VERIFIED** for the executed cases, with actual native engines and persisted warehouse output:

| Case with pipeline SUCCESS | Narrow Quality | Native Modeling / composed publication | Recovery |
| --- | --- | --- | --- |
| 700 duplicate logical orders after retry | FAIL, closed gate | FAIL / BLOCKED, dashboard untrusted; fact incident impacts dashboard | Exact 1,000 rows and expected metric; repeat safe |
| Unique 1,000 rows; O0001 amount increased USD 1.00 | PASS / OPEN | Exact-row Model FAIL / BLOCKED; USD 53,946.00 fails source reconciliation | Clean native upsert restores USD 53,945.00 and resolves incident; clean rerun passes |
| O0001 +USD 1.00, O0002 −USD 1.00; correct aggregate total | PASS / OPEN | Exact-row Model FAIL / BLOCKED even though USD 53,945.00 matches | Full source row equality restored; clean rerun passes |
| Equal-total substitution after native certification | PASS / OPEN; native Model receipt PASS | Existing native integration test mutates two persisted fact values by ±17 cents; composed publication rejects `materialized_output_matches_model` | Detection test passed in current AE suite; no new product fix |

Quality does not claim to be the exact business-value oracle for every schema-valid row. The cross-system composed decision detects the narrower-gate blind spots. Evidence: native JSON, probe log and `tests/integration/test_pipeline.py` cases in the 63-check log.

## Boundary Failure Scenario

Forced the **actual Quality subprocess dependency unavailable** by setting `AE_LAB_QUALITY_PYTHON` to a nonexistent artifact-local executable for one re-verification, then restored the environment.

- The native bridge raises an actionable `AdapterError`; no PASS, fallback gate or restored VERIFIED result is fabricated.
- Previously VERIFIED AE state is suspended to **REMEDIATED** before the fresh check. Persisted verification remains **RUNNING**, with empty checks, when the exception exits; it is not a passing receipt.
- Raw and fact rows remain exactly unchanged under safe writes. The old pinned Observability snapshot and an unrelated synthetic profile remain unchanged.
- Restoring the dependency and re-verifying produces VERIFIED/PASS with all eight checks true and no residual data corruption.

**State safety and recovery: VERIFIED. Durable outage diagnosis/telemetry: PARTIALLY VERIFIED.** The initiating process gets the precise dependency error, but this exception path leaves RUNNING rather than persisting a terminal failure/error receipt. It aborts before importing a new Quality-failure incident; the previous successful snapshot remains historical evidence, not a new outage signal. This limitation is recorded, not broadly repaired.

Additional malformed-boundary controls: Quality API rejects optional primary key, unsupported version and extra fields with 422, then accepts the restored valid request; Observability rejects invalid TestResult status and contradictory measurements, then validates clean evidence; Orchestration rejects missing-parent/invalid/cyclic artifacts, then executes the restored dependency graph. These artifact and virtual failures are distinct from the real unavailable executable above.

## AI False-Success Scenario

**VERIFIED** through real `IntelligenceService`/`ModelRouter`, authorized workflow handlers and artifact-local SQLite, using deterministic provider stubs and no live API:

| Control | Actual observed state | Service result |
| --- | --- | --- |
| Model says “completed successfully,” requested 1,000 rows never written | 700 rows | **rejected**, deterministic=false; one provider call, no alternate-provider retry |
| Same text without workflow verifier | 700 rows | **proposed**, never verified |
| Explicitly authorized mutating handler reports completion but performs no write | 700 rows | **uncertain**, tool `verification_failed`, deterministic=false; no continuation/replay/fallback |
| Correct synthetic handler + tool and workflow state verifiers | 1,000 rows | **verified**, deterministic=true |
| Same request repeated after successful mutation | 1,000 rows; one saved mutation receipt | **verified**, stable idempotency key and no duplicate logical state |

The handler's unique keys and saved SQLite receipt provide durable idempotency; the shared runtime does not invent a persistent store for the workflow. Existing Intelligence tests also pass post-commit exception, failed read after mutation, complete-batch argument/authority rejection, and native provider continuation controls. `DecisionService` tests preserve deterministic denial over probabilistic judgment.

Evidence: [disk-state probe](/Users/key/.codex/artifacts/aios-step5-20261006-225013/ai_false_success_probe.py), [result JSON](/Users/key/.codex/artifacts/aios-step5-20261006-225013/ai-false-success-evidence.json), `ai-false-success.log`, `ai-synthetic-state.sqlite`; 18 Intelligence and 12 Decision tests pass. This qualifies the bounded tool/verification mechanism, not the factual quality or availability of a live model.

## AE Lab Result

**VERIFIED for the authored technical scenario and repaired native adapter path.** Six current CLI cases pass, including the nine-step ORIENT→PREDICT→RUN→OBSERVE→DIAGNOSE→FIX→VERIFY→RECALL→CONNECT journey and interruption/resume. Before RUN, output contains neither the predicted fault count nor repair answer. Wrong diagnosis is rejected and cannot authorize repair. Actual measurements become available for observation; supplied synthetic diagnosis permits the authored repair; fresh machine checks establish recovery.

Reset creates a new isolated exercise while retaining earlier evidence. Local objective labels remain bounded and assistance-qualified; this does not establish real learner understanding, prose evaluation or transfer. The fresh probe additionally checks incorrect diagnosis, fault preservation, incident resolution, repeated safe rerun and unrelated-profile isolation. `ae-guided-cli.log`: **6 passed**. `ae-step4-contracts.log`: **63 passed**, including genuine native contract tests.

## FDE Lab Result

**VERIFIED for the existing synthetic customer scenario; runtime sibling integration NOT APPLICABLE.** `python3 -m unittest discover -s tests -v`: **27 passed**. The executed engine/CLI/exercise cases establish:

- Ambiguous opening and DISCOVERY; one requested evidence topic releases at a time. Locked evidence rejects without altering state.
- Private instructor-field canaries never appear in start/diagram/evidence/progress/graph/log/component views. An explicitly requested solution is a separate recorded action.
- Framing and requirements submissions remain pending tutor review; they cannot unlock prototype execution. Current reviewed framing, requirements, metric contract and design are required before build.
- One complete discovery/design/executable-test/incident/recovery/measurement sequence passes. SQL mutations/replays and a changed-after-test artifact are checked before simulated deployment.
- Failure injection preserves original learner SQL, and reset archives synthetic work. No automatic keyword mastery, real tutor assessment or real deployment is inferred.

Evidence: `fde-tests.log`, especially `test_public_views_never_project_private_fields`, `test_locked_requested_artifact_reveals_nothing`, `test_stage_gates_prevent_phase_skips`, `test_complete_discovery_code_incident_measurement_loop` and exercise replay cases. FDE's registry/integration guidance is reference-only; no AI-OS or sibling executor connection was manufactured for this validation.

## Toptal Result

**VERIFIED within original request safety, terminal policy, structured provider boundary and objective SQL evaluation scope.** All checks use temporary databases and fake provider/SDK responses.

- Original API/security and terminal policy tests: **113 passed**. Bad request boundaries preserve state; accepted start/submit/restart/retry retain idempotency. Required provider outage preserves the answer/pauses; optional outage produces diagnostic practice without assessed credit or success spacing. Synthetic rebuild preview/apply/backups/rollback controls pass; real historical profiles remain untouched.
- Parsed provider transport, native SQL runner and exercise contracts: **41 passed**. Original exercises execute deterministic visible/hidden cases; unsafe SQL cannot write/read files/network. Public exercise contracts exclude hidden cases, expected rows and reference answers. Authoritative deterministic failure overrides a model PASS, with malformed structure rejected.
- Three focused real SQL-trainer API workflows: **3 passed, 9 deselected**. Correct submission is evaluated, duplicate submission and restart preserve one result, wrong SQL gets feedback without hidden row disclosure, corrected revision cannot earn independent credit, infrastructure failure saves the submission without mastery.
- AE→Toptal native contracts additionally prove exact authored fields are evaluated, terminology-only prose is not objective proof, strict row types apply and a missing evaluator runtime fails explicitly.

Evidence: `toptal-step4.log`, `toptal-objective-transport.log`, `toptal-workflow.log`, AE contract log. Deprecation warnings are retained. Live model reasoning quality, official hiring acceptance and any actual learner's mastery are unverified.

## Recovery Results

| Fault | Detection / recovery actually executed | Final state | Status |
| --- | --- | --- | --- |
| Partial write + append retry | Native fail/retry, Model/Quality FAIL, incident; supported diagnosis then existing safe repair | Exact 1,000 raw/fact rows, correct metric, gate/trust restored; verification repeated safely | VERIFIED |
| Wrong amount with unique keys | Native exact-row FAIL while Quality OPEN; clean upsert and clean rerun | Correct rowset/revenue; incident clears; prior corrupt phase retained | VERIFIED |
| Offsetting wrong rows with unchanged sum | Exact-row FAIL and composed publication BLOCKED; clean upsert and rerun | Exact source equality, not just total equality | VERIFIED |
| Quality executable unavailable | Explicit bridge error; prior acceptance suspended; environment restored then re-verified | No changed/corrupt data, unrelated profile preserved; fresh VERIFIED/PASS | VERIFIED safety/recovery; PARTIALLY VERIFIED durable outage telemetry |
| Backfill failed invocation | New identity replay plus same-ID deterministic control | Zero overlapping IDs, immutable historical payloads | VERIFIED |
| Malformed optional artifacts/API input | Explicit schema/version/dependency rejection; restore valid input | Valid converter/API/graph succeeds; invalid status does not survive validation | VERIFIED offline |
| AI claim/no-op mutation | Deterministic actual-state rejection; correct handler and repeated same-request verification | 1,000 logical rows, one durable receipt | VERIFIED with provider stubs |
| FDE local prototype/replay incident | Existing engine/exercise tests observe, diagnose and repair synthetic fixture | Passing replay checks; original SQL retained; deployment remains simulated | VERIFIED local scenario |
| Modeling installed path | Failed prerequisites; no environment or code repair in Step 5 | Still unavailable; dependent normal-path sampling check stopped | FAILED / BLOCKED |

## Observability Evidence

For the actual AE data incident, [native results](/Users/key/.codex/artifacts/aios-step5-20261006-225013/ae-native-evidence.json) and per-run snapshots/events answer:

| Engineer's question | Observed evidence |
| --- | --- |
| What failed? | Native Model exact-row assertions and Quality order-key uniqueness; 700 duplicate extras and USD 37,503.50 excess revenue |
| When? | Canonical timezone-aware event timestamps on the reproducible logical scenario timeline; no claim of measured real execution duration |
| Where / which run? | `orders_raw`/`fct_orders`, run `79638507-cc12-4d95-9c4e-fc8744fc0f12`, named baseline/fault/recovery/rerun phases |
| Which component? | Failed native loader attempt/retry in scheduler trace; Model and Quality evidence; incident node `model.ae_lab.fct_orders` |
| Impact? | Declared downstream `executive_dashboard`, potential corrupt revenue USD 91,448.50; publication withheld |
| Retried? | FAILED→SUCCESS attempt sequence and `RUN_RETRIED` metadata record committed-row counts |
| Recovered? | Current incident list clears; `INCIDENT_RESOLVED` correlates native identity and original opening event/key; recovery/rerun row/metric evidence passes |
| Is history retained? | Pinned original fault snapshot and phase equal pre-recovery copies; historical failed test still records 700 extras |

The initial accepted/repeated trace contains 28 unique canonical events, including one incident opening/resolution pair and four retry observations; later boundary/recovery events remain in saved run evidence. Six declared lineage edges connect source through fact/revenue to dashboard. Native Observability retains artifact provenance and exact USD cents. Root cause is not automatically proved by dependency impact: the separate structured diagnosis supplies authored causal evidence. Freshness, row-level lineage, dbt execution and live BI are outside this scope.

For the dependency outage, the command sees an explicit missing-runtime error, but no new incident is persisted and verification remains RUNNING after exception. An engineer can identify the failing dependency from retained command evidence; saved state alone is less diagnostic. That distinction prevents an inflated observability claim.

## Failed/Blocked Paths

1. **FAILED — A-07 installed Modeling.** The current pytest script and editable mapping retain the deleted `Data Modeling Lab System` root. Fresh direct launcher exit 126, isolated `-I -B` import exit 1 and supported nonmutating launcher import exit 1. Evidence: [runtime results](/Users/key/.codex/artifacts/aios-step5-20261006-225013/modeling/runtime-38cvx2r0/runtime-results.json) and its three logs. Installed API serving, owning full suite/build/browser and SQL sampling acceptance were stopped. AE's three native Modeling contracts pass through its preexisting source-path adapter; that is not installed-runtime repair.
2. **BLOCKED — A-06 normal-path sampling rejection.** Step 4 never accepted this planned guard, and A-07 fails its prerequisite. No sampling acceptance was claimed, no alternate bootstrap created and no guard implemented in Step 5.
3. **FAILED invocation — default Modeling fixture exporter.** Quality verifier's genuine default-export attempt reports `ModuleNotFoundError: modeling_fixtures`; [retained log](/Users/key/.codex/artifacts/aios-step5-20261006-225013/quality/modeling-export.log). The successful converter test uses explicit synthetic native contract input. This corroborates A-07 rather than proving a new business-data defect.
4. **PARTIALLY VERIFIED — durable dependency-outage diagnosis.** Safe suspension/recovery pass, but saved terminal failure receipt/new outage incident is absent; RUNNING remains after the exception.
5. **NOT APPLICABLE — live FDE sibling wiring / Semantic stage in AE chain.** Current systems define reference/artifact boundaries, not these executing connections. No missing implementation was added or scored as a failed configured pipeline.
6. **Unverified limits.** Live provider behavior, production readiness, full unrelated UI suites, optional dbt, actual historical learner credit and enterprise telemetry were not tested. Old Step 4 temporary backup/evidence directories are absent; do not rely on them for rollback or present them as currently accessible.

## New Findings

**No new P0/P1 defect was established.** A-07 and the unaccepted A-06 are already known remediation items. The validated current A-05 behavior is stronger than its unfinished Step 4 acceptance record.

| Validation finding | Evidence / consequence | Deferred disposition |
| --- | --- | --- |
| Step 4 handoff incomplete | Report still lists three pending items; current A-05 now verified, A-07 fails, A-06 blocked | Reconcile accepted evidence and close existing remediation before overall acceptance |
| Dependency outage leaves RUNNING | Fresh actual missing-Quality-runtime probe leaves REMEDIATED/RUNNING and an actionable process error, with safe state | Reliability/diagnostic limitation for later scoped work; no tiny Step 4 regression causality demonstrated |
| AE aggregate receipt schema is weaker than native envelopes | Adapter Protocols return `dict`; worker aggregate JSON has no independent strict schema/version | Contract coverage limitation; tested native fields and publication invariants pass; no new schema invented |
| Historical evidence retention gap | Prior Step 4 temporary logs/backups absent during this validation | New evidence stored in artifact directory with hashes and synthetic databases; old rollback artifacts cannot be certified |
| No connected Semantic/FDE runtime stage | Registry, FDE integration docs and Semantic AGENTS explicitly distinguish references/artifacts | Intended scope limitation, not a proposed new system/connection |

No product fix, registry mutation or broad cleanup was made. Native scopes and intentional UNKNOWN states were preserved. Model/Orchestration/Quality independent preservation records show 19/92/18 scoped source/setup/test/contract files unchanged respectively. [Root source manifest](/Users/key/.codex/artifacts/aios-step5-20261006-225013/root-sources.json) records current critical hashes; AE core matches the accepted Step 4 hash.

## Verification Matrix

| Critical path / requirement | Final status | Executed evidence / reason |
| --- | --- | --- |
| Recorded P0 corrections still effective | VERIFIED | Toptal boundary tests; AE native correctness/trust controls |
| Accepted P1 terminal/backfill behavior | VERIFIED within stated scope | Terminal synthetic live/recovery/rebuild suite; backfill native/schema/browser controls |
| Current presence compatibility correction | VERIFIED | Independent B5 criteria, API 422→valid recovery, 103 checks |
| Healthy native AE baseline | VERIFIED | 1,000 complete rows, USD 53,945.00, PASS native receipts, open gate, trusted output |
| ORDER provenance | VERIFIED at authored asset/row/metric scope | Pinned source O0001→actual raw/fact rows→known total→declared dashboard, retained native lineage |
| Partial write + retry after repair | VERIFIED | Real 700→1,700 unsafe control; corrected 1,000→1,000, exact equality and safe repeat |
| Silent analytical corruption detection | VERIFIED / DETECTED | Duplicates, wrong amount, equal-total row errors and changed materialization |
| Dependency failure isolation and recovery | VERIFIED | Missing native executable abort, acceptance suspension, no unrelated mutation, restored dependency PASS |
| Dependency-outage persistent diagnosis | PARTIALLY VERIFIED | Explicit process error; saved RUNNING/no new incident limits unattended diagnosis |
| AI false success / no-op tool mutation | VERIFIED | SQLite evidence: rejected/uncertain, never verified; correct recovery/repeat succeeds |
| AE technical failure learning journey | VERIFIED bounded objective scope | Six CLI cases; no pre-run solution, diagnosis gate, real repair and verification |
| FDE ambiguity/discovery/design/disclosure/recovery | VERIFIED synthetic scenario | 27 engine/CLI/exercise cases; no live sibling integration |
| Toptal evaluation/disclosure/durability | VERIFIED tested surfaces | 113 + 41 + 3 current targeted cases; live assessment quality unverified |
| Registered metadata | VERIFIED structural scope | Validator passes 10; paths/graph/CLI consistent; lifecycle health stays UNKNOWN |
| Installed Modeling runtime/startup | FAILED | Fresh unsupported old-path launch and missing installed module |
| Sampling guard normal-path acceptance | BLOCKED | Existing unresolved guard and failed installed-runtime prerequisite |
| Optional artifact boundaries | VERIFIED offline | Strict native producer/consumer conversion and malformed-input recovery |
| Live FDE/Semantic chain stages | NOT APPLICABLE | Not configured runtime edges; intentionally not invented |

### Executed command ledger

All commands ran from their owning root. Bytecode/cache disabled for Python checks. `EVIDENCE` below is shorthand for `/Users/key/.codex/artifacts/aios-step5-20261006-225013`; it is not an additional runtime setting. Detailed agent argv/environment records are in `quality/commands.json`, `orchestration/verification-result.json` and Modeling's `runtime-results.json`.

| Owner | Command / selected scope | Actual result / log |
| --- | --- | --- |
| Registry | `systems-registry/.venv/bin/python systems-registry/scripts/validate_registry.py` | Exit 0, 10 systems; `registry.log` |
| AE | `uv run --frozen --no-sync pytest -q -p no:cacheprovider tests/unit/test_foundations.py tests/contract/test_native_execution.py tests/contract/test_quality.py tests/contract/test_observability.py tests/contract/test_testing.py tests/integration/test_pipeline.py` | 63 passed; `ae-step4-contracts.log` |
| AE | `uv run --frozen --no-sync python - < EVIDENCE/ae_probe.py` | Exit 0, native baseline/fault/repair/repeat/outage/silent-corruption assertions; `ae-native-probe.log` |
| AE | `uv run --frozen --no-sync pytest -q -p no:cacheprovider tests/e2e/test_cli.py` | 6 passed; `ae-guided-cli.log` |
| Toptal | `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_api.py tests/test_interview_boundary.py tests/training` with temporary original-app import DB | 113 passed; `toptal-step4.log` |
| Toptal | `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_openai_service.py tests/ae/test_execution.py tests/ae/test_contracts.py` with temporary audit/provider/original-app paths | 41 passed; `toptal-objective-transport.log` |
| Toptal | `.venv/bin/python -m pytest -q -p no:cacheprovider tests/ae/test_workflow.py -k 'offline_vertical_loop or failure_feedback or infrastructure_failure'` with temporary import/trainer DB paths | 3 passed, 9 deselected; `toptal-workflow.log` |
| FDE | `python3 -m unittest discover -s tests -v` | 27 passed; `fde-tests.log` |
| AI-OS | `python3 -m unittest discover -s tests -p 'test_intelligence.py' -v` | 18 passed; `ai-intelligence-tests.log` |
| AI-OS | `python3 -m unittest discover -s tests -p 'test_decisions.py' -v` | 12 passed; `ai-decision-tests.log` |
| AI-OS | `python3 - < EVIDENCE/ai_false_success_probe.py` | Exit 0, disk-state rejection/recovery/idempotency assertions; `ai-false-success.log` |
| Quality | `uv run --offline --frozen --no-sync python -B -m pytest -q -p no:cacheprovider tests/test_contracts_and_adapters.py tests/test_engine.py` | 103 passed; `quality/pytest.log` |
| Quality | Independent API/comparator/native contract probe | Exit 0; `quality/verification.json` and `commands.json`; default exporter failure retained separately |
| Orchestration | `npm test` | 40 passed; `orchestration/npm-test.log` |
| Orchestration | `node --import ./node_modules/tsx/dist/loader.mjs EVIDENCE/orchestration/runtime-contract-probe.mts` | Exit 0, 182 schema-valid events; runtime-contract result/log |
| Orchestration | `npm run build -- --outDir EVIDENCE/orchestration/browser-build/dist` | Exit 0; `orchestration/build.log` |
| Orchestration | `npm run test:e2e -- --config EVIDENCE/orchestration/playwright.config.mjs --grep 'backfill range'` | 1 passed; `orchestration/browser-test.log`; focused server stopped |
| Modeling | Direct launcher, isolated import, supported no-sync launcher import | Exit 126/1/1; three failure logs and exact argv in `modeling/runtime-38cvx2r0/runtime-results.json` |
| Modeling → AE | Three current native Modeling contract cases with default interpreter/adapter, no interpreter/root override | 3 passed; `modeling/runtime-38cvx2r0/ae-native-modeling-contracts.log` |

Passing counts describe executed selections; overlapping contracts were intentionally independently rechecked and are not summed into an ecosystem score. No whole-workspace suite was run.

**Step 6 handoff:** ready for a scoped remediation/acceptance decision, **not unconditional ecosystem sign-off**. One recommendation: complete the existing **A-07 → A-06** sequence, reconcile its Step 4 acceptance evidence, then rerun the currently blocked installed Modeling and sampling paths before accepting the ecosystem.
