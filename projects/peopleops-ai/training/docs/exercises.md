# Exercise contracts and checkpoints

Work on **one function or query at a time**. Tests are intentionally failing,
without `xfail`, answer keys, or fallback solutions. Infrastructure tests do not
grade your implementation. The first checkpoint is E01; later checkpoints are
prepared but not assigned until the previous concepts are understood.

The active Level 2 checkpoint is [NEXT_TASK.md](../../NEXT_TASK.md). Before
coding, explain input, output, correctness rules, data structure/operation, and
edge cases. Begin at Level 0; the mentor does not supply an algorithm unless
that assistance is requested. Record help and scores in the project state files.

After an attempt: run the named tests, inspect failures, grade out of 10 using
the rubric, discuss tradeoffs, and ask for your explanation of production impact.
Do not automatically replace a failed attempt with a generated solution.

## E01 · Normalize one employee

Workday sends inconsistent strings. A pure function should produce one validated
record while preserving the raw evidence for debugging. Practice dictionary
access, string normalization, explicit errors, and typed dates.

Edit `exercises/e01_cleaning.py`, function `normalize_employee(raw)`.
Actual input from `fixtures/enterprise.json`:

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

Return an `EmployeeRecord` with `full_name="Maya Chen"`,
`email="person001@example.test"`, `status="active"`,
`hire_date=date(2026, 1, 26)`, aware `source_updated_at`, and all other values
preserved. Missing email, invalid date/status, negative PTO, or naive timestamp
must raise `ValueError`. Never mutate the input. The broader contract is in
[data.md](data.md); passing eight initial tests is not the whole specification.

```sh
uv run pytest tests/exercises/test_e01_cleaning.py
```

Production discussion after your attempt: should one invalid employee reject a
batch or enter quarantine? Explain the tradeoff before moving to E02.

## Remaining prepared checkpoints

Commands below assume `uv sync --frozen`. For database tests, start Compose and
prefix the command with `LAB_DATABASE_TESTS=1`. Each test filename matches the
exercise filename, replacing `.sql` with `.py` and adding `test_`.

| ID / file | Implement one step | Concrete input → expected result |
| --- | --- | --- |
| E02 `exercises/e02_duplicates.py` | `latest_events(events)` | Raw 242 events → 240 events sorted by ID. EVT-0001 keeps `applied`, timestamp Oct 1, over the later-arriving Sep 30 delivery. Equal version: last input wins. |
| E03 `exercises/e03_analytics.sql` | Begin with the `headcount` block | As of Oct 1 → Engineering 30, Operations 30, People 20, Sales 30. Then implement one remaining metric at a time using data.md. |
| E04 `exercises/e04_chunking.py` | `chunk_policy(policy, max_words)` | PTO v2 section 1 → `chunk_id=PTO:2:1:0`, `section_key=PTO:2:1`, exact section body. Five words with max_words=2 → chunks of 2,2,1 words; ordinal resets per section. |
| E05 `exercises/e05_retrieval.py` | `retrieve(question, principal, session, k)` | Employee asking about PTO → v2 evidence; no v1. Employee asking about compensation → no COMP hit, even when k=1. HR may retrieve COMP. |
| E06 `exercises/e06_grounding.py` | `answer_question(...)` | Payroll question → answered, 15th/final business day, citation PAY/v2/section1 with an exact quote. Missing policy → refused and no citations. “What about leave?” → clarify. |
| E07 `exercises/e07_authorization.py` | `authorize(principal, action, resource)` | EMP-001 reading EMP-001 → true; reading EMP-002 → false. Manager role alone is insufficient for full records. Unknown action → false. |
| E08 `exercises/e08_endpoints.py` | Start with employee GET endpoint | Maya reads her record → HTTP200, PTO80, no email/salary. Other or missing record → identical404. Then candidates, jobs, and aggregate endpoints. |
| E09 `exercises/e09_planning.py` | `plan_action(message, principal)` | “Employee needs help with payroll” → create_ticket, category Payroll, employee_id EMP-001. “Book some PTO” → clarify. Never execute here. |
| E10 `exercises/e10_actions.py` | First `prepare_action`, then `execute_action` | Preview creates no ticket. Exact confirmation replay returns the same request ID; one business row, one receipt. Reuse actor/key for different proposal →409. |
| E11 `exercises/e11_reliability.py` | `fetch_all(fetch_page, sleep, max_attempts)` | Page0 succeeds, page2 times out twice → calls (0,1),(2,1),(2,2),(2,3); sleeps .1,.2; no duplicated page0. Malformed pages/cyclic cursors →ValueError. |
| E12 `exercises/e12_ingestion.py` | `ingest_employees(records, session)` | Replay EMP-001/002 → inserted0/updated0/unchanged2. Old version with PTO0 leaves current PTO80. Invalid second row rolls back first-row update. |
| E13 `exercises/e13_status.py` | `request_status(request_id, principal, session)` | Maya + TKT-001 → {request_id:TKT-001,type:ticket,status:open}. TKT-002 and TKT-999 →same404. |

Example isolated runs:

```sh
uv run pytest tests/exercises/test_e02_duplicates.py
LAB_DATABASE_TESTS=1 uv run pytest tests/exercises/test_e03_analytics.py -k headcount
LAB_DATABASE_TESTS=1 uv run pytest tests/exercises/test_e05_retrieval.py
uv run pytest tests/exercises/test_e07_authorization.py
LAB_DATABASE_TESTS=1 uv run pytest tests/exercises/test_e10_actions.py
```

SQL blocks contain executable empty-result placeholders so each query can be
tested independently. Do not mistake a valid SQL statement for a correct metric.
Database exercise tests run in a rollback transaction. Endpoint tests read the
seeded isolated database. Do not point tests at another database.

## Retrieval debugging cases

1. **Outdated evidence:** remove the current-version filter mentally; PTO v1 is
   still embedded. Show how a plausible but wrong answer gets an apparently valid citation.
2. **Unauthorized top result:** COMP has distinctive vocabulary. Explain why
   retrieving it and filtering only after top-k loses permitted results.
3. **Weak lexical match:** hash vectors do not understand every paraphrase. Use
   recall@3 and a labeled query to diagnose retrieval before blaming generation.
4. **Missing support:** “Mars relocation allowance” has no document. Refuse rather
   than answer from an unrelated high-scoring chunk.
5. **Injected instruction:** a retrieved passage or question says “I am the admin.”
   It cannot change the authenticated principal or execute a tool.

## Checkpoint log template

Record attempts in the project-root `INTERVIEW_LOG.md`: date, exercise, file,
test command/result, rubric scores/10, actual assistance level, one strength,
one correction, learner's production explanation, and advance decision. Update
`PROGRESS.md` and `SKILL_MATRIX.md` only from that evidence. Mastery additionally
requires an independent equivalent variation with passing tests and explanation.
An implementation completed by the assistant is never evidence of learner mastery.
