# Remediation execution — Step 4

Date: **2026-10-05, Asia/Seoul**. Authoritative scope: [Step 3 plan](/Users/key/_AI-OS/systems-registry/audits/remediation-plan.md).

Execution order: A-02 → A-01 → A-03 → A-04 → A-05 → A-07 → A-06. Each batch is reproduced, changed, tested and recorded before moving to the next. This report is updated as work proceeds; pending rows are not acceptance claims.

Source backups and execution logs: `/var/folders/cl/91y0ht7x1kz__0vw0psz8b2h0000gn/T/aios-step4-kq43xm55`. Projects contain preexisting untracked work; rollback uses scoped snapshots, never a blanket Git reset/clean. Real learner records, cloud providers and production services are outside the executed checks.

| Batch | Finding | Current status |
| --- | --- | --- |
| 1 | A-02 original interview HTTP boundary | RESOLVED |
| 2 | A-01 AE publication trust | RESOLVED |
| 3 | A-03 lexical assessment credit | RESOLVED — policy/tool verified; real profiles remain legacy/unverified until separate apply |
| 4 | A-04 backfill execution identity | RESOLVED |
| 5 | A-05 presence compatibility | UNRESOLVED — pending its ordered batch |
| 6 | A-07 Modeling installation | UNRESOLVED — pending its ordered batch |
| 7 | A-06 SQL sampling | UNRESOLVED — pending its ordered batch |

## Batch 1 — A-02

**FINDING ID:** A-02 (P0).

**BEFORE:** Independently reproduced current-source hostile Host create/config/list/resume with 201/200/200/200, cross-origin form pause 200 with persisted PAUSED, zero provider calls. Existing original API baseline: **9 passed**.

**CHANGE:** Original-app loopback Host allowlist, strict same-Origin validation and per-process mutation token. Config exposes `request_token`; original static client sends `X-Interview-Token` and refreshes a stale connection without silently replaying a mutation. Original CSP, loopback launcher, dependencies and database schema preserved.

**FILES:** Toptal `app/main.py`, `app/models.py`, `app/static/app.js`, `tests/conftest.py`, `tests/test_api.py`, new `tests/test_interview_boundary.py`, and `docs/api.md`, all under `/Users/key/_AI-OS/projects/Toptal-Testing System/`.

**TESTS:** From Toptal root, with `PYTHONDONTWRITEBYTECODE=1` and `TOPTAL_TESTING_DB` redirected to temporary storage: `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_api.py tests/test_interview_boundary.py` → **50 passed**. `node --check app/static/app.js` → exit 0. The initial new-test run incorrectly treated database records as objects; assertions were corrected to the existing dictionary contract, then rerun. No product failure was hidden by that correction.

**RESULT:** PASS / RESOLVED. Independent latest-source HTTP verification passed 76 rejection controls, unchanged synthetic state/provider counts, authorized idempotency and restart token rotation. Real headless Chromium exercised the original static client: bootstrap/start/submit, pause/resume, process restart, stale-token rejection/config refresh with no automatic answer replay, explicit saved-answer retry with the same ID, end-module, induced evidence-sync failure/retry and Module 2 continuation. All nine browser mutations sent token and matching Origin; zero page errors. Four fake calls were expected and observed. Temporary server stopped.

**EVIDENCE:** `b1-baseline.log`, `b1-tests-final.log`, `b1.patch` and `b1-manifest.json` in the execution directory. Independent evidence: `/tmp/aios-step4-b1-independent.lmgdla/patched-http-results.json`, `browser-final/browser-results.json` and `browser-final/browser-final.png`. Initial browser-harness expectations were corrected for the legitimate continuation provider call and Playwright's full-header accessor; no product behavior was changed to satisfy the harness. All checks use synthetic DB/assessment content and fake providers.

**ROLLBACK:** Restore the six preexisting files from `b1-before/` and remove only the newly added boundary test after preserving any subsequent work. This requires keeping the original interview service stopped if its old unprotected behavior returns. No data migration.

**REMAINING RISK:** Local bootstrap tokens protect the browser request boundary; they are not remote multi-user authentication. Real browser attack delivery was not penetration-tested. No known B1 acceptance gap remains.

## Batch 2 — A-01

**FINDING ID:** A-01 (P0).

**BEFORE:** Fresh native reproduction retained 1,000 unique rows and Quality PASS, but revenue 53,946.00 versus pinned 53,945.00 produced Model FAIL while AE still recorded ELIGIBLE/trusted. The clean native control was ELIGIBLE/trusted.

**CHANGE:** One AE-owned phase publication decision now requires successful execution, Modeling PASS, Quality PASS/OPEN, complete expected/materialized/validated/distinct row coverage, no duplicates and exact pinned-source/materialized revenue. Missing/UNKNOWN/failed conditions block both output labels. Rejection reasons are retained; freshness stays NOT_MEASURED. Native engines, public result/event versions and historical evidence are preserved.

**FILES:** AE `lab/core.py`, `tests/unit/test_foundations.py`, `tests/contract/test_native_execution.py`, `tests/integration/test_pipeline.py`, `docs/architecture.md`, under `/Users/key/_AI-OS/projects/AE Lab/`.

**TESTS:** From AE root: `PYTHONDONTWRITEBYTECODE=1 uv run --frozen pytest -q -p no:cacheprovider tests/unit/test_foundations.py tests/contract/test_native_execution.py tests/contract/test_quality.py tests/contract/test_observability.py tests/integration/test_pipeline.py` → **55 passed in 40.94s** after the materialized binding correction (initial suite: 53 passed). Tests cover missing/unknown evidence, wrong amount, wrong rows with unchanged total, passing Quality, direct phase publication, recovery/rerun, isolated profiles and historical snapshots.

**RESULT:** PASS / RESOLVED. Independently authored native probes executed by the root verified clean/fault/recovery/rerun for wrong-amount and offsetting-row faults, each before Verify; Quality remained PASS in both corrupt cases but publication was blocked. Isolated profiles, source pin and historical snapshots were preserved. A supplemental native challenge proved a materialization substitution with equal total could still be trusted under the initial patch. That specific condition was corrected by comparing persisted rows with native certified output; the unchanged probe now records BLOCKED/untrusted with `materialized_output_matches_model`. No native engine changes were needed. After a transient account-credit interruption, the independent verifier resumed and returned VERIFIED on matching final source hashes, its 25-case negative decision matrix, native probes and the 55-test suite. Root executed its native probes unchanged after the initial sandbox restriction.

**EVIDENCE:** `b2-baseline.log`, `b2-baseline-profiles/native_summary.json`, `b2-tests.log`, `b2-tests-final.log`, `b2.patch` and `b2-manifest.json` in the execution directory. Independent probes/logs/JSON: `/tmp/aios-b2-verifier.LTXCr6/`; final core SHA256 `6a64c72c6f6844e8e6a205934a57ac258755d5d99dd2ffc883ea4f94b0a0e85c`. Initial sandbox IPC and temporary noncanonical phase names were harness/environment failures, corrected before normal execution. No native verdict was mocked in publication integration controls.

**ROLLBACK:** Restore only five files from `b2-before/`, preserving subsequent work and all profiles/snapshots. Withhold output-trust claims if the old predicate returns; no persisted format migration.

**REMAINING RISK:** Saved historical trust labels are not retroactively certified by this change. This synthetic exercise does not certify freshness or production readiness.

## Batch 3 — A-03

**FINDING ID:** A-03 (P1), RESOLVED within the approved policy/tool scope.

**BEFORE:** Current-source synthetic lexical contradiction received diagnostic PASS, independent success 1, mastery 0.12. Root independently reproduced failure-streak clearing and acceptance of a caller-supplied 30-day review. Baseline terminal suite: 26 passed.

**CHANGE:** One metadata-derived eligibility rule distinguishes complete reasoning assessment from lexical/missing/unknown practice, with genuine authoritative deterministic failures retained and no confidence cutoff. Store, family/assessed-attempt counts, normal/recovery scheduling and summaries share it. Practice retains raw evaluation/exposure but grants no assessed success, negative lexical judgment, mastery/streak effects or success spacing. The store caps caller-supplied spacing. Pre-policy aggregates display LEGACY/unverified. Explicit-path rebuild defaults to noninitializing read-only preview, requires reviewed source digest for apply, holds a writer lock through projection/consistent SQLite backup/atomic derived update, and appends an owned correction receipt. Raw attempts/evaluation/schedule history remain unchanged. No real learner profile was inspected or applied.

**FILES:** Under `/Users/key/_AI-OS/projects/Toptal-Testing System/`: `training/mastery.py`, `training/persistence.py`, `training/application.py`, `training/scheduling.py`; `tests/training/test_mastery.py`, `test_persistence.py`, `test_evaluators.py`, `test_scheduling.py`, `test_acceptance.py`; `README.md`; new `scripts/rebuild_training_credit.py`. Registry: `/Users/key/_AI-OS/systems-registry/registry/toptal-testing.yaml` adds the actual CLI and executed terminal validation command.

**TESTS:** With original-app import DB redirected to temporary storage and bytecode/cache disabled, `.venv/bin/python -m pytest -q -p no:cacheprovider tests/training` → 63 passed, one preexisting Starlette/httpx warning. Root independent 16-case metadata/assistance/cold/transfer matrix, nine-attempt mixed-history rebuild with secondary calibration, and CLI help/missing-path/missing-digest controls all exited 0. Registry validator exited 0. The initial expanded test run had five WAL-precondition fixture failures; fixtures were quiesced without weakening the preview guard. Root's initial rebuild harness encountered the same intended WAL refusal, then passed with stopped synthetic writers. In-progress receipt ownership was corrected against the existing NOT NULL session contract before acceptance.

**RESULT:** PASS / RESOLVED. New writes/fallback/recovery provide zero lexical success effects; recognized low-confidence reasoning remains eligible; objective failures remain authoritative. Preview creates no files or directories, unsupported/stale/active-WAL cases refuse safely, unknown legacy evidence supplies no invented credit, post-UPDATE receipt failure rolls back the entire correction, backup restores exact logical source, repeated apply is a no-op. Old assessment times are retained.

**EVIDENCE:** `b3-baseline-results.json`, `b3-baseline-tests.log`, `b3-first-expanded-tests.log`, `b3-final-tests.log`, `b3.patch`, `b3-before-manifest.json`, `b3-independent-live-final.log`, `b3-independent-rebuild-final.log`, `b3-cli-independent.log`, `b3-registry-validation.log` and registry scoped snapshot in the execution directory.

**ROLLBACK:** Restore the ten preexisting project files from `b3-before/`, remove only the new CLI, and restore registry metadata from `b3-registry-before/`, preserving later work. For any separately selected profile apply, stop its writers and restore the tool's consistent SQLite backup; never reverse arithmetic or delete raw history. Only synthetic profiles were applied here.

**REMAINING RISK:** Existing real profiles may retain legacy credit and influence adaptation until their separately reviewed rebuild. They were not read or certified. Preview requires a quiescent/copied schema-2 profile without WAL; cap is 10,000 rows per evidence table and 64 MiB including committed WAL for apply. Unreconstructable identity/time/mode blocks apply. Raw unknown reasoning remains unassessed even after aggregates are rebuilt.

## Batch 4 — A-04

**FINDING ID:** A-04 (P1).

**BEFORE:** Fresh failed→successful backfill reproduction reused 25 event IDs, including two conflicting payloads. Baseline project tests: 37 passed.

**CHANGE:** `simulateBackfill` requires a validated caller-owned `options.execution_id` of 1–160 nonblank characters before reading workflow inputs. Partition run IDs include this identity and exports retain it. The browser generates one UUID per new invocation; repeated export retains the result's original identity. Same-ID/identical-input replay stays deterministic; automatic task retries retain their run and increment attempts. Engine randomness, ordinary simulator API, schemas and historical exports are unchanged.

**FILES:** Under `/Users/key/_AI-OS/projects/Data Orchestration System/`: `src/engine/backfill.ts`, `src/ui/BackfillLab.tsx`, `tests/backfill.test.ts`, `tests/verifier-regressions.test.ts`, focused backfill case in `e2e/learning.spec.ts`, `README.md`.

**TESTS:** `npm test` → 40 passed; `npm run build` → exit 0; `npm run test:e2e -- --grep 'backfill range'` → one focused browser case passed, including repeat export, recovery, reset and reload. From AE: `PYTHONDONTWRITEBYTECODE=1 uv run --frozen pytest -q -p no:cacheprovider tests/contract/test_native_execution.py -k orchestration` → 1 passed, 3 deselected. Focused test screenshots now use the temporary test output path, preserving dated audit evidence.

**RESULT:** PASS / RESOLVED. Independent read-only Orchestration verifier returned VERIFIED: zero recovery overlaps; frozen earlier payloads unchanged; deterministic replay; retry attempts 1→2 with existing delay; 12 invalid inputs rejected; maximum run/event lengths 180/183; 218 engine events schema-valid; three worker/pool scenarios preserved. Its separate production-build browser probe covered five invocations, stable repeat export, reset/reload, 268 unique/schema-valid events, no page errors or external requests. Exactly six planned files changed, with 84 other sampled files and AE worker preserved.

**EVIDENCE:** `b4-baseline-tests.log`, `b4-baseline-collision.log`, `b4-tests.log`, `b4-build.log`, `b4-e2e.log`, `b4-ae-consumer.log`, `b4.patch` and `b4-manifest.json` in the execution directory. Independent engine/browser/baseline/preservation JSON and source hashes: `/tmp/orchestration-b4-independent.ZlCNE9/`.

**ROLLBACK:** Restore six files from `b4-before/` together, preserving later work and exports. Legacy identity collisions return on rollback; do not merge/deduplicate separate backfills by those IDs. No data migration.

**REMAINING RISK:** Callers must supply a fresh identity for new invocations and must not reuse an identity with changed input. The required source API intentionally rejects historical callers without an explicit identity. Focused browser coverage does not certify unrelated UI flows.
