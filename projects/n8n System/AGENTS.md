# Repository guidance

## Purpose and source of truth

Build reliable, deterministic lead-intake workflows. The existing process is
Northstar LeadOps Workflow 001. Read only the relevant files:

- Business behavior and open policy questions: `northstar-leadops/docs/process.md`
- Component and failure map: `northstar-leadops/docs/architecture.md`
- External-system boundaries: `northstar-leadops/docs/integrations.md`
- Input, AI, and response schemas: `northstar-leadops/contracts/`
- Executable exports: `northstar-leadops/workflows/`; local n8n mount:
  `n8n/workflows/`
- Database-owned state: `northstar-leadops/db/`
- Offline checks and synthetic cases: `northstar-leadops/scripts/` and
  `northstar-leadops/fixtures/`

## Working boundaries

Stay within this repository and its synthetic fixtures. Do not access another
project or connect to production accounts for architecture tests. Never commit
secrets, real lead data, credential exports, or local `.env` files. Use test
credentials only when an integration test is explicitly in scope.

Prefer static configuration, native n8n nodes, IF/Switch, and database
constraints before Code nodes. Use a small Code node when it is clearer. Use
bounded structured AI only for interpreting prose; AI never authorizes writes,
sets final scores, controls retries, or overrides validation. Do not add an
autonomous agent without a process requirement that needs dynamic planning.

For every external write, define duplicate-execution and ambiguous-outcome
behavior. Stop and identify unknown business policy before inventing a rule.
Keep n8n workflow copies synchronized when an export changes.

## Validation and completion

Run `node northstar-leadops/scripts/validate.mjs` and
`node northstar-leadops/scripts/test-behavior.mjs` after a workflow or contract
change. These are offline checks; report live integration coverage separately.

A change is done when its business outcome, input/output contract, failure and
replay behavior, side effects, evidence, and relevant tests agree. Update the
process document when behavior changes; update the architecture and integration
documents when implementation boundaries change.
