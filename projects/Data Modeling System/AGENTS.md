# Data Modeling Lab project guidance

This is the independent `data-modeling-lab` project. Follow the parent AI-OS boundaries.
Read `docs/architecture.md` for the approved first slice and deferred scope.

- Deterministic execution and assertions are the truth engine. Never use AI to certify SQL.
- Learner grain declarations must stay explicit; do not relabel inferred grain as fact.
- Currency is decimal, and metric business definitions must be inspectable.
- No imports from sibling projects, scoring policy, incident management, or cloud requirements.
- Keep exactly one independent Modeling Verification Agent. It may inspect/run checks
  and create temporary probes, but must not edit product code, tests, or contracts.
- Required checks: `uv run pytest`, `npm --prefix apps/web run build`, and
  `npm --prefix apps/web run test:e2e`. `make check` runs them in order.
- Use `uv sync --extra dev` and `npm --prefix apps/web ci` to reproduce dependencies.
- Start locally with `uv run python scripts/run.py`. Bind to loopback by default.
