# Data Quality & Contracts System

Follow the parent AI-OS boundary rules. Read `docs/system-audit.md`,
`docs/architecture.md` and `docs/acceptance.md` before changing domain behavior.

- Deterministic input data, exact decimal money, explicit timezone-aware clocks.
- Preserve UNKNOWN; blocking missing or unknown evidence withholds publication.
- Modeling owns design/transformations; Orchestration execution; Observability
  monitoring/investigation; Toptal disclosure/scoring. No sibling imports.
- Exactly one independent Data Quality Verification Agent audits and falsifies.
  Reuse it; it may save probes/evidence, but not edit product code/tests/contracts.
- Required checks: `uv run pytest`, `npm --prefix web run build`,
  `npm --prefix web run test:e2e` (`make check`). dbt check: `make check-dbt`.
- Setup: `uv sync --extra dev`, `npm --prefix web ci`.
- Run: `uv run python scripts/run.py`, loopback port 8082 by default.
- Keep project logic, fixtures, dependencies and evidence in this project.
