# Engineering lab operational readiness

The baseline assessment in `enterprise-readiness.md` still applies. This is a
fictional local teaching app; no real enterprise deployment or integration was
performed. The added lab implements the following bounded controls:

- Demo-mode guard and explicit `lab:run` permission, separate from an HR role.
- Fixed suite names, no arbitrary command/path/body overrides and no shell.
- One active process group, a configured deadline, isolated SQLite/coverage/reports
  and child environments without provider keys or arbitrary Python paths.
- Tenant-bound report access, safe parsed counts/metrics and no HTTP access to
  raw process output. Parameter text is omitted from failed IDs in web reports.
- A 40-folder report limit, current-source labels and source-stability checks
  during pytest and job execution.
- Per-request failure injection; authorization remains active and source tables
  are not mutated by scenario selection.
- SQLite identity authority and receipt context checks so cached responses cannot
  restore revoked grants or removed policy access.

Coverage is reported with its scope: the complete regression suite covers the
application and ingestion together, while a unit-only job covers only the work
executed by that directory. The initial proposed **unit-only 85%** target is not
claimed as achieved; its observed coverage is recorded in the verification report.
The configured CI gate continues to enforce **85% combined statement/branch
coverage across the full regression suite**. Increasing isolated unit coverage
without duplicating integration tests remains an engineering improvement.

Remaining work for a real deployment includes organizational authentication,
approved delegation and retention, secret management, database encryption and
least privilege, TLS, policy-owner validation, queues/distributed coordination,
representative load/semantic/security evaluation and an authorized rollout.
Never expose the public synthetic persona selector to real employee data.

The in-process runner is for trusted local source only. A production test service
needs a separate sandbox/worker identity, resource quotas, signed immutable source
artifacts, controlled report retention, distributed job leases and operator
approval policies. The local runner is not an arbitrary-code sandbox.

Source-stage timings, attempts, safe failure codes and aggregate index freshness
are implemented. Availability/error-budget SLOs and production alert thresholds
remain proposals in the baseline assessment. Raw questions, credentials, employee
IDs and record contents remain outside the runtime audit allowlist. Local pytest
diagnostics contain synthetic fixtures and stay in operator-owned report folders.

If a job hangs, its deadline terminates the owned POSIX process group. Stop the
local app to close its active worker. Preserve the relevant safe job ID and
reports, reproduce in a temporary database, fix the source and rerun the full
suite. Move old report folders to an archive before hitting the bounded report
limit; no automatic destructive cleanup is performed.

The migration is additive. A pre-layer SQLite backup is retained under
`data/backups/pre-testing-layer-20261020.sqlite3`; these private runtime files are
ignored by Git. Unchanged seed digests preserve mock database edits; deliberately
changed seed files replace only their corresponding synthetic table atomically.
Restore compatible code with its database copy after preserving current state.
Do not undo a policy revocation by using an old public index. The existing
PostgreSQL/n8n volumes and Qwen runtime are outside this migration.
