# PeopleOps AI progress

Updated: 2026-10-20. The latest enterprise master prompt is implemented in
`policy_assistant/` as the standalone SQLite `app.main` reference. It does not
advance or replace the learner-owned curriculum or the earlier pgvector app.

## Enterprise HR reference · 2026-10-20

### Interactive testing layer · latest

- Added timed execution stages, actual source/rule inspection, executable YAML
  rules, SQLite identity/PTO, request-scoped faults and permission-gated real
  subprocess jobs to the existing portal on 8811.
- Final regression: **127 passed**, **94.01% full combined coverage**; independent
  evaluations **105/105**, configured gates **13/13**, traceability gaps **0**.
- All four browser test buttons executed: unit **52/52**, integration **49/49**,
  security **10/10**, full verification **127/127 + 105/105**. Unit-only coverage
  is **53.83%**, below the proposed unit-only 85% target; full-suite coverage is
  reported separately. Preserved pgvector regressions: **61 passed** this turn.
- Current setup/evidence: `policy_assistant/docs/testing-layer-guide.md` and
  `policy_assistant/docs/testing-layer-verification.md`. Learner exercises and
  interview scores remain unchanged. Earlier results below are historical.

- Implemented HR-001–HR-015 with BRD, exact criteria, access matrix, code/test/evaluation
  traceability, synthetic identities/PTO, signed mock Slack, governed ingestion,
  deterministic RAG, scoped record reads, redacted audit, portal and CI gates.
- Executed: **84 tests passed**, **92.34% combined statement/branch coverage**,
  **105/105 evaluation cases passed**, **13/13 demonstration gates passed**.
  All 15 requirements have mapped tests and evaluations; no traceability gaps
  were reported. Preserved pgvector policy regressions: **61 passed**.
- Live HTTP verified exact self PTO (12.5 days, 2026-10-20), cited parental policy,
  and cross-employee denial with zero protected calls. Browser checks covered
  US/UK policies, citations, denial, component traces and mobile layout.
- Start with `Start-Enterprise-HR.command` on 8811. The owned verification
  preview is stopped after QA; the earlier n8n/Qwen/policy services are preserved.
- Evidence and limits: `policy_assistant/docs/enterprise-verification.md`.
  This is a fictional local candidate; real enterprise integration and production
  approval remain open. No learner exercise, answer or assessment score changed.

## Local model connection · 2026-10-20

User requested the installed Qwen as provider. The working policy app now uses
Qwen3-4B-Q4_K_M via the Mac's existing AI-OS runtime; the n8n Assistant model is
also connected and reload-verified. Embeddings remain mock. Host tests: 61 passed;
live n8n/Qwen checks: 19 passed. Model and app services are running. The interview
remains at Question 1 with no submitted answer or score.

## Principal Engineer interview · 2026-10-20

User requested an oral interview about the working system, one question at a
time. Session PI-001 is in INTERVIEW_LOG.md. Question 1 covers the end-to-end
PTO request flow; answer and score are pending. Services are running; the n8n
editor owner setup has been completed by the user; its model connection is configured. E01 remains a separate pending
coding checkpoint, with no learner mastery inferred from the completed app.

## Working application · 2026-10-19

- Delivered the FastAPI/Pydantic/PostgreSQL/pgvector policy slice, versioned
  Markdown ingestion, server identity and pre-retrieval ACLs, citations,
  abstention/escalation, admin endpoints, n8n workflow, and minimal chat UI.
- Python suite: **56 passed** on both host and Docker with real PostgreSQL and mock providers.
- Live Docker/n8n checks: **19 passed**. Browser checks confirmed identity
  connection, the current PTO citation, and payroll escalation on mobile.
- Setup, function explanations, provider configuration, and final verification
  evidence are in `policy_assistant/README.md` and `policy_assistant/docs/`.
- This is assistant-authored application work, not learner mastery. The prior
  E01 assignment and all exercise implementations remain unchanged.

## Previous learning checkpoint

The following 2026-10-18 state remains the current **learning** checkpoint.

## Current session · L2-001

- Current phase: **Phase 1, data engineering**. Mode: **LEARN**, following a
  bounded BUILD step to initialize the state records.
- Current task: **E01 normalize_employee**, assistance **Level 0**.
- Next interaction: learner identifies input, output, correctness rule, intended
  data structure/operations, and edge cases before writing code.
- Current verification: existing Compose stack started without rebuilding;
  four services healthy, seed exit 0; foundation **30 passed**; live smoke passed.
- E01 baseline: **8 intentional failures**, each at PendingExercise. No learner
  implementation, score, or mastery is inferred from this result.
- Evaluation recheck: **4 passed, 32 blocked, 0 executed failures** (11.1% coverage).
  RAG, record authorization, and action safety are not established by these passes.
- Infrastructure blockers: none observed. Learning checkpoint: awaiting the
  learner's reasoning and implementation; do not advance to E02.
- Application/exercise source preserved. This session changes guidance and state,
  not business logic or the working environment's design.
- All six state records are initialized; all 14 exercise files match their
  pre-session hashes. Verification containers are stopped after checks, with
  the PostgreSQL volume retained. E01 tests need no running Docker services.

## Authoritative state records

- [Current task](NEXT_TASK.md): one assignment and its pre-code questions.
- [Skill matrix](SKILL_MATRIX.md): nine areas; all currently unassessed.
- [Interview log](INTERVIEW_LOG.md): exact rubric, assistance ladder, attempts.
- [Decisions](DECISIONS.md): architecture, alternatives, security/chaos gaps.
- [Failure log](FAILURE_LOG.md): observed failures, evidence and prevention.

The setup results below are historical implementation milestones unless the
current session explicitly rechecks them. They are not learner assessment.

## Category A: implemented foundation

- [x] Independent Python 3.12 environment and locked dependencies in `training/`.
- [x] Docker Compose, PostgreSQL 17 + pgvector, FastAPI/Pydantic, SQLAlchemy, Streamlit.
- [x] Normalized models, foreign keys, transaction-bound session plumbing.
- [x] Reproducible synthetic data: 120 employees, 24 jobs, 240 recruiting events,
  16 policy versions across 15 policies, 60 tickets, 60 onboarding tasks.
- [x] Mock Workday, Greenhouse, policy, Slack, and ticket HTTP source interfaces.
- [x] Pagination, delayed responses, intermittent outages, duplicates, missing
  records, malformed payloads, and schema drift fixtures.
- [x] Offline fake provider and deterministic hash embeddings; optional real
  provider transport is opt-in and tested without external calls.
- [x] Minimal UI, health/readiness, local identity simulator, fixture explorer.
- [x] Bounded latency/error/tool/usage telemetry and durable audit schema.
- [x] 13 exercise modules, signatures, examples, expected outputs, failing tests.
- [x] 36-case evaluation harness with blocked/failed/passed and coverage reporting.
- [x] Architecture, data contracts, security protocol, operations, interview rubric.
- [x] Existing completed demo preserved; all 60 legacy unit tests pass.
- [x] Final foundation checks:30 tests passed on host and in the container;
  four running services healthy, seed exit0, outage/recovery and browser verified.
- [x] Strict evaluation baseline:4 passed,32 blocked,0 executed failures;
  62 exercise tests fail intentionally. Registry validation passed.

## Phase status

| Phase | Infrastructure status | Learner capability status |
| --- | --- | --- |
| 0 Foundation | Implemented and locally verified; training/docs/verification.md | Ready to begin |
| 1 Data engineering | Models, data, exercise scaffolds ready | E01/E02/E03 pending |
| 2 Policy RAG | Versioned sections, vector storage, provider transport ready | E04/E05/E06 pending |
| 3 Secure tools | Authentication transport and typed contracts ready | E07/E08 pending |
| 4 Agent automation | Proposal/receipt models, confirmation UI, contracts ready | E09/E10/E13 pending |
| 5 Reliability | Fault-injectable source, DB outage handling, tests ready | E11/E12 pending |
| 6 Evaluation | Harness and 36 scenarios ready | Business coverage blocked until exercises are implemented |
| 7 Interview | Question sequence and scoring rubric ready | Not conducted |

## Category B: learner assessment

Current checkpoint: **E01 normalize_employee** in
`training/exercises/e01_cleaning.py`.

No learner attempt has been submitted. Score: **not assessed**. Understanding:
**not assessed**. Later exercises are prepared, not assigned or mastered.
Do not automatically solve a failed attempt. After an attempt, run the focused
tests, grade using the Level 2 rubric, record assistance, explain issues, and
discuss production implications. Mastery additionally requires an equivalent
independent variation and explanation.

## Level 2 requirements staged for later milestones

- Shared orchestration interfaces and authorized evidence before prompts: transport
  exists; actual E05/E06 orchestration remains learner work.
- Tenant isolation, malicious-document cases, and salary/access negative cases:
  pending Phase 2/3 design and tests; current training schema is single-tenant.
- Server-validated confirmation, payload integrity, expiry, replay, and durable
  redacted action audit: pending E10; models/UI alone do not satisfy this.
- Complete named, isolated fault profiles with logs, recovery expectations,
  regression tests and RCA packets: incremental work at the relevant milestone.
- Staff design reviews: after significant learner milestones, not assigned now.

These gaps are explicit in DECISIONS.md. The Level 2 directive says to stop once
the foundation works and the first independent exercise is ready. No broad
feature implementation or additional fault scenario was introduced this session.

## Category C: designed extensions

SSO, narrower authorization, semantic embeddings, schema migrations, outbox,
CI/CD, concurrency, scaling, performance, and multi-agent tradeoffs are prompts
in `training/docs/interview.md`. They are not implemented or deployed.

## Separation from the original demo

The older SQLite application is an assistant-written reference, not evidence
of learner mastery. Its state and dependencies are unchanged. The new training
path does not import its completed business logic.
