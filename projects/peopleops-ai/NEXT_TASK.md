# Current task · E01 employee normalization

> Learning checkpoint, preserved on 2026-10-19. The separate request to build a
> working policy assistant is implemented in `policy_assistant/`; it does not
> count as completing E01 or require an interview before using that application.

**Current phase:** Phase 1 — data engineering. Mode: LEARN. Assistance: Level 0.

**Current system status:** Foundation reverified on 2026-10-18: 30 passing tests,
healthy Compose services, passing live smoke. E01 has eight intentional failures
at its untouched starter. Business features remain incomplete; learner readiness
is unassessed.
Verification services are stopped after checks; this exercise runs without Docker.

**Today's business problem:** Workday sends Maya's name with extra spaces and
her email/status with inconsistent casing. Downstream HR code needs one valid,
consistent record while raw evidence remains available for debugging.

**Interview skill:** Translate a business contract into a small pure Python
function. Staff engineers must make correctness, invalid-data handling, and
state changes explicit before scaling a pipeline.

**File to modify:** `training/exercises/e01_cleaning.py`, relative to the
PeopleOps project root. Supporting contract: `training/lab/contracts.py`.

**My task:** Implement only this existing function; leave the rest of the
application and tests intact:

```python
def normalize_employee(raw: dict) -> EmployeeRecord:
    ...
```

## First respond with your reasoning — before coding

Identify these five things in your own words:

1. What is the input, including its shape and important field types?
2. What is the required output, including its type?
3. Which business rules determine whether that output is correct?
4. Which data structure or operations would you use, and why?
5. Which edge cases could break your approach?

No algorithm, pseudocode, or implementation is supplied at Level 0. Explain your
algorithm after identifying the contract. If that reasoning is incomplete, we
will clarify the requirement before you code; we will not automatically raise
the assistance level. Ask for a conceptual hint if you want Level 1 support.

## Actual fixture and expected output

Source: `training/fixtures/enterprise.json`, `raw_employees[0]`, seed 42.

```json
{
  "employee_id": "EMP-001",
  "full_name": "  Maya   Chen  ",
  "email": " PERSON001@EXAMPLE.TEST ",
  "department": "Engineering",
  "manager_id": null,
  "status": " Active ",
  "hire_date": "2026-01-26",
  "termination_date": null,
  "pto_hours": 80,
  "benefits_eligible": true,
  "source_updated_at": "2026-10-01T08:00:00+00:00"
}
```

Return an `EmployeeRecord` with name `Maya Chen`, email
`person001@example.test`, status `active`, hire date as `date(2026, 1, 26)`,
PTO 80, and a timezone-aware source timestamp. Preserve employee ID, department,
benefits eligibility, nullable manager, and nullable termination date. The
original input dictionary must be unchanged.

## Requirements and edge cases

- Normalize whitespace in the name; normalize email/status casing and surrounding
  whitespace. Preserve the other business values.
- Parse ISO dates/timestamps; source_updated_at must include timezone information.
- Return the declared model, not a hardcoded fixture or unrelated dictionary.
- Reject invalid/missing required values with ValueError. Initial negative tests
  cover missing email, invalid hire date, negative PTO, unsupported status, and
  naive source timestamp. Null manager and termination date are valid here.
- Retain the documented employee contract in `training/docs/data.md`; the
  initial eight tests are a starting check, not an exhaustive proof. Discuss
  any unclear temporal/business rule before inventing behavior.
- Do not mutate raw input or write to a database, file, or network.

The failure scenario is an invalid source record reaching normalization. The
function must reject it rather than silently inventing a valid employee.
Batch quarantine, deduplication, retry, and upsert behavior are later tasks.

**Verification:** No running Docker service is needed for this exercise.

```sh
cd /Users/key/_AI-OS/projects/peopleops-ai/training
uv run pytest tests/exercises/test_e01_cleaning.py
```

**Completion criteria:** Explain the five contract questions; independently
implement the function; pass all eight focused tests without weakening them;
explain how your function preserves raw input and handles invalid values.
We will score the attempt with INTERVIEW_LOG.md's six-category rubric and record
assistance. We will not advance until the reasoning is understood.

**Production implication / Staff follow-up:** If one employee update is invalid,
would you reject the entire batch or quarantine that row? Explain the data
integrity and operational tradeoff after your implementation.

Mastery requires an equivalent unseen variation solved independently, passing
its tests, and an explanation. No variation is assigned yet; first complete E01.
