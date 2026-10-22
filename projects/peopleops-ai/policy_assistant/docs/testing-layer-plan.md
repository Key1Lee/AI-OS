# Additive interactive testing layer · 2026-10-20

Source: the verified `app.main` SQLite enterprise reference. Target: the same
application with a timed execution inspector, applied YAML rules, SQLite-backed
identity/PTO, safe failure simulations, and an actual backend test runner.

Implementation phases:

1. Add typed business/routing/security configuration and expand the local schema
   with mock identity/Workday tables. Seed idempotently from the existing fixtures.
2. Instrument actual authorization/source/validation work and expose safe response
   diagnostics. Keep legacy trace names, identity rules and exact source facts.
3. Add demo-only failure simulation and permission-protected, allowlisted test
   subprocesses. Each job gets isolated reports, coverage and runtime data.
4. Extend the existing portal, tests, traceability and docs; execute the tests,
   evaluations, real dashboard jobs and browser scenarios before reporting results.

Invariants: the existing n8n/Qwen/pgvector entrypoint, learner exercises, employee
grants, approved document versions, source balances and audit minimization are
preserved. No production or enterprise connection is introduced. Existing EMP200
hours and EMP300 days remain boundary fixtures; the new prompt's other balances
are examples. EMP100 remains exactly 12.5 days as of 2026-10-20.

Schema strategy: additive tables in the enterprise SQLite file, no old table
deletions. Take a SQLite backup before starting the changed app on existing data.
JSON remains the reproducible seed; unchanged seed digests do not overwrite edits
to the mock database. Tests use temporary databases. Recovery: stop the owned
preview, retain the new file, and use the prior code with its pre-layer backup.
The preserved PostgreSQL and n8n volumes require no migration.

Mock assumptions: only explicit lab permissions can run tests; the public persona
selector is a local teaching feature. Failure controls never change identity or
grant access. Subprocess commands are server-owned, serial and time bounded, with
no arbitrary command/path input or raw subprocess logs returned over HTTP.
Production SSO, queues, distributed rate limiting and deployment remain separate.
