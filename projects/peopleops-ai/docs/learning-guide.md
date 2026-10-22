# Twelve-phase learning guide

The complete application is available to inspect. These exercises let you rebuild
one small idea at a time; application completion does not imply learner mastery.
Run commands from the project root. Each phase is an entry point for further
micro-steps, rather than a claim that one exercise covers every part of a phase.

## Phase 1 — Understand the business

**Business problem:** Maya needs help with payroll and HR must track the request until it is resolved.

**Visual:**

| Before | After |
| --- | --- |
| Maya sends a payroll question; no tracked state | HR-001 has status open and owner Payroll |

**Our task:** Display the initial request status.

**Code:**

```text
print("HR-001: ___")
```

**Explanation:** print() displays a message on your screen. Checking a request's status helps HR find work that still needs attention, like an open ServiceNow incident.

**How to verify:**

```sh
uv run pytest tests/test_data.py::test_seed_business_outcomes
```

Expected: 1 passed.

**Your turn:** What status belongs in the blank for a newly submitted request?

Source to inspect after attempting the exercise: `peopleops/seed.py`.

## Phase 2 — Set up the environment

**Business problem:** Two engineers need to run the same application with the same dependencies.

**Visual:**

| Before | After |
| --- | --- |
| Python packages differ across computers | An isolated .venv uses versions recorded in uv.lock |

**Our task:** Run the project setup and inspect the seeded metrics.

**Code:**

```text
# Run from the peopleops-ai directory
uv sync --frozen
uv run peopleops ___
```

**Explanation:** A virtual environment is a separate toolbox for one project, and uv sync installs its recorded tools. This keeps a change in another project from breaking the HR application.

**How to verify:**

```sh
uv run peopleops init
```

Expected: database path plus initialization status (already_initialized after first setup).

**Your turn:** Which command initializes the project's database?

Source to inspect after attempting the exercise: `pyproject.toml`.

## Phase 3 — Inspect fictional source data

**Business problem:** A Workday delivery includes missing fields, duplicate deliveries, and inconsistent dates.

**Visual:**

| Before | After |
| --- | --- |
| 22 raw rows, including blank name and invalid date | 16 accepted identities + 4 rejected rows + 2 duplicates |

**Our task:** Recognize an invalid record without silently inventing its missing information.

**Code:**

```text
def has_name(employee):
    return bool(employee.get("full_name", "").___())
```

**Explanation:** A dictionary stores labeled values, like the fields on a ServiceNow ticket, and strip() removes extra spaces. Validating required fields keeps incomplete employee records from entering headcount reports.

**How to verify:**

```sh
uv run pytest tests/test_data.py::test_seed_business_outcomes tests/test_data.py::test_bad_source_rows
```

Expected: 9 passed.

**Your turn:** Which string method removes surrounding spaces?

Source to inspect after attempting the exercise: `peopleops/fixtures/employees.json`.

## Phase 4 — Design database relationships

**Business problem:** Every HR request must belong to a real employee.

**Visual:**

| Before | After |
| --- | --- |
| HR-001 refers to EMP-001; an unknown employee might be mistyped | A foreign key permits EMP-001 and rejects an unknown employee ID |

**Our task:** Connect an HR request to its employee record.

**Code:**

```text
SELECT r.request_id, e.full_name
FROM hr_requests r
JOIN employees e ON r.employee_id = e.___;
```

**Explanation:** A primary key identifies one record, while a foreign key points to a record in another table. These links keep a payroll question attached to the correct employee, like a POS transaction linked to its store.

**How to verify:**

```sh
uv run pytest tests/test_data.py::test_foreign_keys_enforced
```

Expected: 1 passed.

**Your turn:** Which employee column completes this join?

Source to inspect after attempting the exercise: `peopleops/schema.sql`.

## Phase 5 — Calculate workforce metrics with SQL

**Business problem:** Management needs current headcount by department, with departures and future hires handled consistently.

**Visual:**

| Before | After |
| --- | --- |
| 16 validated employee records across four statuses | 14 current employees, grouped as 4 Engineering, 4 Operations, 4 People, 2 Sales |

**Our task:** Count employees currently active or on leave.

**Code:**

```text
SELECT COUNT(*) AS headcount
FROM employees
WHERE status IN ('active', '___');
```

**Explanation:** COUNT(*) counts matching rows and WHERE selects which rows qualify. A clear definition prevents management from counting departed employees or future hires as current headcount.

**How to verify:**

```sh
sqlite3 data/peopleops.db "SELECT COUNT(*) FROM employees WHERE status IN ('active','leave');"
```

Expected: 14 on a fresh demo database.

**Your turn:** Which second status belongs in current headcount?

Source to inspect after attempting the exercise: `sql/practice.sql`.

## Phase 6 — Build Python ETL

**Business problem:** Workday returns a padded, capitalized email that needs a consistent format.

**Visual:**

| Before | After |
| --- | --- |
|   JORDAN.LEE@fictional.example   | jordan.lee@fictional.example |

**Our task:** Clean a string before loading it into SQLite.

**Code:**

```text
def clean_email(value):
    return value.strip().___()
```

**Explanation:** def creates a reusable function, return sends its result back, and lower() makes text lowercase. Consistent email formatting makes employee matching reliable while invalid records remain visible in quarantine.

**How to verify:**

```sh
uv run pytest tests/test_data.py::test_seed_business_outcomes tests/test_data.py::test_replay_is_incremental_and_preserves_state
```

Expected: 2 passed.

**Your turn:** Which string method completes clean_email?

Source to inspect after attempting the exercise: `peopleops/pipeline.py`.

## Phase 7 — Add dbt and YAML quality tests

**Business problem:** A transformation could accidentally duplicate employee IDs and inflate headcount.

**Visual:**

| Before | After |
| --- | --- |
| A staging table might contain the same employee twice | A unique test reports duplicate IDs as a failing check |

**Our task:** Declare the employee identifier's quality expectations.

**Code:**

```text
columns:
  - name: employee_id
    data_tests: [___, not_null]
```

**Explanation:** YAML records settings and test rules, while dbt runs SQL models and checks those rules against their output. Detecting bad data gives HR evidence of a defect even when a cleaning query could hide it.

**How to verify:**

```sh
uv run peopleops dbt
```

Expected: 6 models and 22 data tests pass; PASS=28.

**Your turn:** Which test detects duplicate employee IDs?

Source to inspect after attempting the exercise: `dbt/models/schema.yml`.

## Phase 8 — Use the FastAPI backend

**Business problem:** An employee submits a payroll question through a form and expects a tracked request.

**Visual:**

| Before | After |
| --- | --- |
| A JSON body contains a subject and description | POST /api/requests returns 201 and a request ID routed to Payroll |

**Our task:** Distinguish retrieving a request from submitting a new one.

**Code:**

```text
# Choose the HTTP method for creating a request.
method = "___"
# API requests also need a Bearer token and Idempotency-Key.
```

**Explanation:** GET retrieves information, POST submits information, and JSON packages labeled values for an API. FastAPI validates submissions so HR receives usable requests and the caller gets a clear response code.

**How to verify:**

```sh
uv run pytest tests/test_api.py::test_ticket_idempotency_and_conflict tests/test_api.py::test_ticket_validation_and_impersonation
```

Expected: 2 passed.

**Your turn:** Which HTTP method creates the HR request?

Source to inspect after attempting the exercise: `peopleops/app.py`.

## Phase 9 — Retrieve cited policy answers

**Business problem:** An employee asks when payroll is paid and needs an approved answer rather than a guess.

**Visual:**

| Before | After |
| --- | --- |
| When is payroll paid? | An exact passage from POL-001, with its title and version |

**Our task:** Require a source for an answer and escalate unsupported questions.

**Code:**

```text
result = answer_question(conn, question, "employee")
if not result["citations"]:
    action = "___"
```

**Explanation:** Retrieval ranks approved passages using sparse TF-IDF vectors, and this application quotes the selected text with a citation. This gives employees traceable answers while unsupported or sensitive questions go to a person.

**How to verify:**

```sh
uv run peopleops evaluate
```

Expected: 10 of 10 retrieval and safety cases pass.

**Your turn:** What should happen when no approved passage supports the answer?

Source to inspect after attempting the exercise: `peopleops/retrieval.py`.

## Phase 10 — Automate onboarding and notifications

**Business problem:** Workday delivers the same new hire twice, but HR needs one onboarding checklist.

**Visual:**

| Before | After |
| --- | --- |
| Two deliveries identify EMP-021 | One employee, three tasks, and one onboarding event |

**Our task:** Use a stable event key to prevent duplicate work.

**Code:**

```text
event_key = f"onboarding:{employee_id}"
# The database requires event_key to be ___.
```

**Explanation:** Idempotency means repeating an operation has the same business effect as doing it once, and an outbox keeps notification work in the database until delivery succeeds. This prevents duplicate onboarding tasks and lets HR recover from a messenger failure.

**How to verify:**

```sh
uv run pytest tests/test_data.py::test_new_hire_event_concurrent_replay tests/test_workflows_retrieval.py::test_slack_failure_retry_and_deduplicated_delivery
```

Expected: 2 passed.

**Your turn:** Which database constraint prevents two rows with the same event key?

Source to inspect after attempting the exercise: `peopleops/workflows.py`.

## Phase 11 — Enforce privacy and reliability

**Business problem:** Maya must not retrieve Jordan's confidential employee record.

**Visual:**

| Before | After |
| --- | --- |
| Maya requests /api/employees/EMP-002 | The server returns 403 and records a denied action |

**Our task:** Check ownership on the server before returning employee data.

**Code:**

```text
if user["role"] == "employee":
    allowed = user["employee_id"] == requested_employee_id
```

**Explanation:** A Bearer token identifies a caller, while authorization checks whether that caller may perform an action. Server-side ownership checks protect employee records even if someone bypasses the browser interface.

**How to verify:**

```sh
uv run pytest tests/test_api.py::test_employee_ownership tests/test_api.py::test_authentication_cannot_be_forged
```

Expected: 2 passed.

**Your turn:** Why is hiding Jordan's record in the browser insufficient protection?

Source to inspect after attempting the exercise: `tests/test_api.py`.

## Phase 12 — Practice recovery and the interview

**Business problem:** Workday becomes unavailable while employees still need HR support.

**Visual:**

| Before | After |
| --- | --- |
| Three simulated HTTP attempts return 503 | The run is marked failed, existing employee data is preserved, and readiness is degraded |

**Our task:** Use evidence to explain detection, impact, and recovery.

**Code:**

```text
# In a separate scenario database:
# PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops ingest --scenario unavailable
# Recovery:
# PEOPLEOPS_DATA_DIR=./data/drill uv run peopleops ingest --scenario ___
```

**Explanation:** Retries handle temporary failures, and a readiness signal shows whether the latest data path is healthy. Preserving the last successful dataset keeps HR working while an operator restores the source and checks freshness.

**How to verify:**

```sh
uv run pytest tests/test_api.py::test_failure_and_recovery_surface_readiness
```

Expected: 1 passed.

**Your turn:** Which scenario restores a healthy source after this failure?

Source to inspect after attempting the exercise: `docs/runbook.md`.
