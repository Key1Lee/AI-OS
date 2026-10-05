# Analytics Engineering trainer implementation

Authorized by the user's complete application request (2026-10-01).
The first execution milestone is Phase 1, followed by the sequenced roadmap.

## Baseline and preservation

Inspection on 2026-10-01: this directory is not a Git repository. Existing systems
are `app/` (FastAPI interviewer, port 8000) and `training/` (terminal trainer).
Baseline `.venv/bin/python -m pytest -q`: **37 passed**, one Starlette deprecation
warning. The four canonical assessment registers contain no concluded learner
demonstrations and an active FDE assessment. They are not imported as Analytics
Engineering performance. Existing launchers, APIs, expectations, and evidence
remain intact. No existing learner database is migrated or reset.

## Sequence and acceptance

1. Phase 0: public research, contracts, competency/exercise schema, scoring,
   selection, security and persistence design.
2. Phase 1: separate local FastAPI service (8001), React/TypeScript/Monaco UI,
   versioned original SQL bank (at least ten exercises), isolated DuckDB worker,
   Run/Submit, hidden tests, feedback, persistent attempts, progress and next
   recommendation. Verify actual SQL, failure paths, restart and browser flow.
3. Phase 2: deterministic adaptive factors, conservative mastery, mistake
   recurrence, transfer/review queue, explainable competency dashboard.
4. Phase 3: actual isolated dbt builds and incremental/replay lab contracts.
5. Phase 4: reasoning domains and validated configurable evaluator interface.
6. Phase 5: strict mixed interviews and frozen follow-ups.
7. Phase 6: multi-stage take-home workspaces and requirement changes.
8. Phase 7: expand the curated bank toward 75–120 after subsystem validation.
9. Phase 8: review correctness, safety, persistence, curriculum and UX.

Phase 1 must work offline after setup, without an API key. Tests use temporary
databases; browser smoke evidence uses a separate temporary profile. Generated
work and smoke results never establish learner mastery. Verification and review
are separate passes after implementation; defects return to implementation.

## Reversible decisions

Use Vite for a static React/TypeScript client instead of Next.js: this local tool
has no SSR requirement and a single FastAPI process can serve bundled assets and
API offline. SQLAlchemy isolates data access; Alembic versions the new database.
Use a new launcher and `data/ae-trainer.db`. Rollback means stop the new service;
the existing apps continue to use their original launchers and databases.

## Delivered milestone — 2026-10-01

Phase 0 documentation and research are complete. Phase 1 is implemented and
verified on the local macOS host: 12 original SQL exercises, 48 executed fixture
contracts, the complete browser training loop, durable attempts, versioned
history, isolated execution and safe failure/recovery paths. Phase 2's selector,
mastery, mistake and review mechanisms are also present and tested. Strict SQL
practice includes clarifications and assistance auditing.

Verification: 101 Python tests and five browser smoke checks pass, alongside
type checking, compilation, production build and dependency consistency. The
actual launcher was exercised with a clean profile. See
[verification and engineering review](verification.md) for criterion evidence,
resolved defects and limitations.

Phases 3–7 remain planned. Their menu entries explain that status; no dbt build,
reasoning-provider evaluation, mixed interview, take-home project or full bank
expansion is claimed. Phase 8 has been applied to this release's scope and must
repeat as those capabilities are added.
