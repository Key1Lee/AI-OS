# Failure recovery runbook

Use the UI's **System health** screen as HR, or the commands below. For a
disposable drill, prefix each CLI command with the same
`PEOPLEOPS_DATA_DIR=./data/drill` setting so it uses a separate database.
No scenario contacts a real enterprise API or sends messages.

## Workday unavailable

**Expected versus observed:** Healthy ingestion returns source rows; this
scenario returns 503 on three attempts and records `source_unavailable`.

```sh
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops ingest --scenario unavailable
# Expected: failed, source_unavailable, attempts=3; exit 1
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops ops
# Inspect the failed run and the last successful run.
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops ingest --scenario normal
# Expected: success; existing rows are unchanged on replay.
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops quality
# Expected: all checks pass; exit 0
```

Before → after: three failed HTTP attempts → failed run plus the last good
employee dataset. Recovery restores the source, then checks a successful run,
freshness, and unchanged employee counts rather than merely restarting a process.

`transient` instead fails twice and succeeds on attempt three. `malformed`
returns an invalid response shape and fails with `source_contract_invalid`.

## Stale data

```sh
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops ingest --scenario stale
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops quality
# Expected: freshness fails; quality exits 1.
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops ingest --scenario normal
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops quality
```

Before → after: source timestamps four days old → freshness alert while newer
employee versions remain protected. Investigate the source publication time
and the last successful sync separately; a recent fetch alone does not prove
the source is current.

## Duplicate source records and new hires

```sh
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops ingest --scenario duplicate
# Expected: extra duplicate rows; zero changes if baseline is already present.
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops ingest --scenario new_hire
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops ingest --scenario new_hire
# First: one changed identity. Second: zero changed identities.
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops notify
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops notify
# Second delivery produces zero messages.
```

Before → after: two new-hire deliveries → one employee, three tasks, one event.
Check the employee/kind and event-key uniqueness constraints before treating
duplicate delivery as an incident requiring manual data deletion.

## Slack unavailable

Run this before delivering the newly queued EMP-021 event, or queue reminders
first if the event has already been delivered.

```sh
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops remind
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops notify --failures 1500
# All eligible events fail three attempts each, remain retryable; exit 1.
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops notify
# Pending/failed events are delivered once each; exit 0.
```

Before → after: undelivered outbox events → failed status with attempt counts
→ successful local receipts after recovery. If no event is pending, a delivery
failure injection has no work to affect; inspect the outbox before rerunning.

## Missing policy documents

In the UI, use **Simulate missing policies**, then ask the policy assistant
when payroll is paid. It should cite nothing and recommend an HR request.
Use **Restore policies**, repeat the question, and inspect the POL-001 citation.

Before → after: an empty authorized knowledge base → safe escalation.
Check document availability and permissions before changing retrieval ranking;
an inaccessible policy is not evidence that the search algorithm is broken.

## Growing volume

```sh
PEOPLEOPS_DATA_DIR=./data/scale uv run peopleops ingest --scenario growth
PEOPLEOPS_DATA_DIR=./data/scale uv run peopleops ops
PEOPLEOPS_DATA_DIR=./data/scale uv run peopleops dbt
```

Before → after: 22 baseline source rows → 5,001 source rows and 4,995 accepted
identities. Compare duration and quality outcomes; this bounded local run
does not establish production throughput or concurrency capacity.

## SQL and dbt failures

```sh
uv run peopleops dbt debug
uv run peopleops dbt
```

Inspect `dbt/logs/dbt.log` and `dbt/target/run_results.json`. The application
database is `data/peopleops.db`; the generated snapshot is `data/analytics.db`.
An old snapshot can be rebuilt without deleting employee or ticket state.
The source profile paths are injected by the CLI, so use that command instead
of relying on a global `~/.dbt/profiles.yml`.

## Startup and access

If port 8765 is occupied, use `uv run peopleops serve --port 8766` and open
that printed address. If a role receives 403, verify its authenticated
identity and the permission matrix before changing access checks. A 401 needs
a valid Bearer token; a 422 needs corrected input, not a new database.

## One scheduled-job concept

```sh
PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops tick
```

This executes one ordered run; it does not create a recurring job. In an
Airflow-style DAG, ingestion would precede quality checks, which gate reminder
creation and delivery. Retries belong around individual tasks, and backfills
need explicit date and idempotency contracts rather than a blind loop over
the current-state workflow.
