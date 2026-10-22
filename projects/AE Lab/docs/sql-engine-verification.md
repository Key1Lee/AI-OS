# SQL Step 2 validation evidence

Completed 2026-10-15 KST. This is implementation validation, not an independent
production/warehouse acceptance review.

- Full project suite: `uv run pytest -q` — **381 passed in 125.69s (0:02:05)**.
- Additional affected execution/privacy/SQL suite (before the final three patterns): **152 passed in 22.39s**.
- Bank validator: **PASS**, 120 executable problems,
  116 newly authored, 480 PostgreSQL fixture cases.
- 120 differently structured equivalent queries accepted.
- 29 authored broken queries distinguished from correct output.
- All candidate native Modeling keys/grain and Quality gates passed. Native
  Observability evidence was retained in isolated validation profiles.
- `node --check lab/web_assets/learning.js`, Python compileall and
  `git diff --check` passed.

The machine receipts in [sql-engine-validation.json](sql-engine-validation.json)
contain the current definition digests; they were reconciled against the catalog.
Reference solutions and hidden rows are not included in that document.

## Criteria and evidence

| Criterion | Evidence |
| --- | --- |
| Curriculum breadth | All existing SQL leaves have authored examples except deferred recursive patterns; authored availability matrix regenerated across 534 concepts. |
| Distribution/domains | 120 SQL/debug problems: L1 12, L2 27, L3 37, L4 29, L5 12, L6 3; all 15 requested business domains. |
| Executability/oracles | 480 real PostgreSQL runs, independent Python calculations, native output constraints, private digest checks and equivalent-query acceptance. |
| Meaningful edge cases | Hand-calculated no-record/NULL/zero lending states, DST repeated hour, leap day, text identifiers and required output ordering; large decimal money mutant passes sample but fails adversarial case; missing calendar-week/year comparisons and optional-cart eligibility have separate sentinels. |
| Reasoning gates | Join left/right grains, relationship and output grain; window partition/order/frame; logical duplicate identity; wrong declared grain cannot pass. |
| Modes | Debug diagnosis before repair, Review criteria, actual fixture EXPLAIN in Performance, hidden interview hints/diffs before completion. |
| Mastery | Existing multi-task/domain/spaced evidence requirements pass; equivalent queries do not earn named ROW_NUMBER evidence unless they use it. |
| Continuations | Finished commerce stage offers a new requirement through the same engine; no automatic continuation. |
| Existing behavior | Original retry/business tests and seven representatives remain; the project suite passes. |
| Browser loop | Isolated L3 seller exercise: observation → structured join/window declaration → separately written CASE/CTE query → 4/4 checks pass; SQL retained and six rubric dimensions shown separately. |
| First live session | Existing selector chose SQL-CTE-001 at L2 from zero learner evidence. Saved run 16372204-29e7-4331-879f-16d58e911c95 has no answers/attempts/hints; context, three sample tables and opening question displayed. |

Browser snapshots: [tested result](screenshots/sql-engine-browser.png) and
[untouched first session](screenshots/sql-first-session.png).
The first session's learner-safe snapshot is [sql-first-session.json](sql-first-session.json).

## Limits

Only PostgreSQL is executed. Vendor-specific dialect notes reference official
sources but do not certify cloud runtime behavior. Scale is hypothetical and
fixture EXPLAIN is not a billion-row benchmark. Business prose and performance
judgment require a named tutor review. Recursive SQL stays outside the bounded
runtime. No production changes, sibling writes, independent audit, or Step 3 work
were performed. This chat's active model could not be switched through the task.
