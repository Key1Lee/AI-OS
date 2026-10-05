# SQL release verification — 2026-10-01

## Authorized scope and outcome

The controlling request is the user's pasted application specification, especially
**FIRST EXECUTION**: deliver a reliable Phase 1 SQL training loop with at least ten
original problems before expanding to other domains. Project `AGENTS.md`, the
README and the adopted AI-OS verification/review guidance also apply.

**Phase 1: VERIFIED on this macOS host.** This is the first working release of the
larger product, not completion of every roadmap phase. Several Phase 2 mechanisms
are included: deterministic selection, conservative mastery, mistake recurrence,
transfer retests, persisted review dates and evidence dashboards.

Implementation, verification and review were separate procedural passes by the
same Codex agent. No independent human or second-agent review is claimed.

## Baseline and boundaries

- This directory is not a Git repository; no commit or diff-based provenance is
  claimed. The changed scope is the new `apps/`, `trainer/`, `curriculum/`,
  `exercise_bank/sql/`, `migrations/`, `tests/ae/`, `tests/regression/`, new launcher,
  development scripts and documentation, plus additive README/environment/ignore
  configuration.
- Before implementation, the existing suite passed **37 tests** with one
  Starlette/httpx deprecation warning. Those checks remain present and passing.
- Existing `app/` and `training/` behavior, launchers, database profiles and four
  canonical assessment registers were preserved. No learner answer, score or
  mastery was fabricated or imported from existing work.
- New operational evidence lives in `data/ae-trainer.db`. Test profiles and
  screenshot attempts are separate temporary data, never learner evidence.
- No production deployment, external message, background automation or live
  reasoning-provider call was performed.

## Acceptance evidence

| Required behavior | Observed evidence | Outcome |
|---|---|---|
| Launch app and load bank | Executed `./Start-AE-Trainer.command`; Uvicorn started on loopback port 8001, browser assets loaded, `/api/health` returned service `senior-ae-trainer`, SQL available and 12 exercises. | Supported |
| Continue Training presents one appropriate problem | Browser smoke follows dashboard to an adaptive SQL attempt; backend primary-attempt and prerequisite/filter regressions pass. | Supported |
| User edits SQL, Runs DuckDB and sees candidate output | Browser smoke types into Monaco's SQL editor and verifies query output; execution integration uses actual isolated DuckDB processes. | Supported |
| Submit executes hidden tests and gives useful feedback | Browser smoke submits correct SQL and sees 4/4 categories; failure smoke exposes category feedback and revision without hidden input disclosure. | Supported |
| At least ten original problems spanning requested SQL concepts | Twelve versioned JSON contracts cover joins/cardinality, aggregation, windows, deduplication, dates, retention and NULLs. Each has one public fixture plus three hidden fixtures. All **48 reference-solution cases** execute correctly. | Supported |
| Persist attempts, submissions and mastery; survive restart | Integration reopens the same temporary database, verifies frozen results and saved drafts, and safely retries a request ID. Browser reload verifies durable results. | Supported |
| Recommend next exercise based on evidence | Browser smoke verifies the next recommendation; deterministic tests cover stable ordering, configured factors, readiness, prerequisites and transfer after failure. | Supported |
| Handle errors without losing work | Tests cover syntax errors, resource limits, stale draft writes, interrupted/infrastructure grading, pending submission recovery and request-body conflicts. SQL that never executes creates no evidence about unobserved concepts. | Supported |
| Preserve historical versions and prevent mastery gaming | Integration tests preserve prior attempt snapshots across a new version and reject same-version content changes. Hints, solution exposure, external help, retries and repeated questions cannot award independent credit. | Supported |
| Isolate submitted SQL from application files and network | Actual OS sandbox probes deny reading a file outside the worker directory and deny sockets. SQL probes deny DDL, multiple statements, attachment, export, external reads and extension/config changes. | Supported |
| Focused usable UI | Browser tests verify desktop solving, light theme, 390px layout, autosave and two-tab conflict recovery. Dashboard and solving screenshots were visually inspected. | Supported |

## Checks run

| Command/check | Result |
|---|---|
| `make test` (`.venv/bin/python -m pytest -q`) | **101 passed**, 17.87s; one existing Starlette/httpx deprecation warning. Includes the original 37 and 64 new checks. |
| `.venv/bin/python -m pytest -q tests/regression/test_ae_no_unobserved_gaps.py` | **1 passed**, after the final execution-error feedback wording change. |
| `make test-e2e` | **5 passed**, 11.9s, actual Chromium browser and isolated local API/profile. |
| `make lint` | Python compilation, TypeScript type checking and launcher zsh syntax all passed. |
| `npm --prefix apps/web run build` | Production client built successfully; Monaco's editor chunk receives Vite's size advisory and is loaded only when solving. |
| `.venv/bin/python -m pip check` | No broken requirements found. |
| `./Start-AE-Trainer.command` and local HTTP checks | Successful startup and browser load; real profile remained at 0 attempts, 0 tested competencies and 0 mistakes during validation. |

The 48 reference contracts are included in the Python execution tests, rather than
an additional learner-success count. Browser checks exercise success, hidden-test
failure/revision, strict interview clarification/hint rules, narrow/light layout
and stale-tab recovery. They use a temporary profile on port 8123.

## Engineering review and corrections

Review traced the execution boundary, result comparison, storage identity,
submission/idempotency transitions, version freezing, mastery evidence and draft
recovery. Confirmed defects were returned to implementation and regression-tested:

- Stale tabs could recover a local draft over newer server text; conflict state
  now blocks saving/running until the user explicitly loads and restores a copy.
- Output value comparison could accept a formatted string for a required DATE;
  published type families are now checked, and aware timestamps compare instants.
- Duplicate-heavy result matching could exceed recursion depth; iterative
  matching handles the supported 1,000-row limit and overlapping float matches.
- Resuming/filtering could select the wrong primary draft; active/grading priority
  and explicit filter semantics now preserve one primary challenge.
- A profile override could point at another application's SQLite file; a read-only
  identity check now rejects it before persistent PRAGMA or migration changes.
- A syntax-only failure could imply gaps in joins, grain or NULL reasoning; only
  SQL execution receives evidence when no case produces a usable result.
- Older failed submissions could reopen completed or inactive attempts, and a
  late failing worker could reset a successful lease retry. Attempt guards and
  lease ownership now preserve completed evidence and reject stale work. Four
  regressions reproduced these defects before the fix and pass after it.

No unresolved blocking finding remained within the inspected Phase 1 scope.
This statement covers the known changed files and tests, not a general security
certification or an external review.

## Remaining scope and practical limits

Actual dbt and Python labs, reasoning-domain exercises/provider integration,
mixed interview rounds, frozen requirement changes, take-home workspaces,
generated performance datasets and the 75–120 curated bank remain future phases.
The UI labels them as planned. Explanation quality is stored but unassessed;
SQL correctness is determined by execution alone.

Execution isolation was tested on macOS with `sandbox-exec`; other hosts fail
closed until an equivalent sandbox is implemented. PostgreSQL replacement,
distributed multi-user operation and other browser/OS combinations are unverified.
Review scheduling stores due dates; it creates no background notifications.
Local answer-key files are not a secrecy boundary against the machine owner.

Use the [implementation plan](implementation_plan.md) for later phases, the
[API contract](api.md) for integration and the [README](../README.md) to launch.
