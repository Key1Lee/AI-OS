# PeopleOps AI

The user's 2026-10-19 implementation request authorizes the completed policy
assistant in `policy_assistant/`, separate from the interview curriculum. Read
`policy_assistant/AGENTS.md` for that application's checks. The learning-only
protocol below applies to `training/`, not to maintenance of the working app.

The 2026-10-20 enterprise master prompt additionally authorizes the standalone
SQLite `app.main` reference, scoped synthetic PTO reads, governed RAG, requirements,
evaluations and CI in that same package. Its default check is `make verify`.

The new ASTRA interview training environment is in `training/`; read its local
AGENTS.md before editing. Category B functions there must remain learner-owned.
The rules below describe the preserved original simulation. Never copy its
completed business logic into the training exercises.

## Stateful Level 2 learning sessions

At the beginning of each PeopleOps learning session, inspect the current source
and these project-root records: `PROGRESS.md`, `SKILL_MATRIX.md`,
`INTERVIEW_LOG.md`, `DECISIONS.md`, `FAILURE_LOG.md`, and `NEXT_TASK.md`.
Repository evidence is authoritative. Verify relevant behavior before claiming
it works; distinguish current test results from historical evidence.

Use BUILD for infrastructure only, LEARN for one learner implementation, DEBUG
for one isolated investigation, and INTERVIEW for scored questions without
unsolicited hints. Follow `training/AGENTS.md` for the session protocol. Do not
rebuild functioning components or overwrite learner code. The current task is
the one in `NEXT_TASK.md`, until learner evidence justifies advancement.

## Original simulation boundary

This independent project is a fictional local learning simulation. Keep all
business code, data, credentials, examples, and test evidence here.

- Never connect real Workday, Greenhouse, Slack, or employee data.
- Bind the demo server to loopback. Demo identity switching is deliberately
  public in demo mode; it is not production identity management.
- Preserve server-side role and ownership checks and policy filtering before retrieval.
- Keep policy answers extractive and cited; do not imply a live LLM is running.
- Preserve transactional onboarding/outbox idempotency and quarantine evidence.
- Run `uv run pytest` and `uv run peopleops dbt` for relevant changes.
- Keep learner assessment separate from implementation completion.
