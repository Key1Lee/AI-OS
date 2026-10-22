# Elementary engineering glossary

Each entry says what the concept does and why HR needs it.

| Name | What it does | Business purpose |
| --- | --- | --- |
| `print()` | Displays text | Inspect the result of a small exercise |
| `def` / `return` | Define a function / send its result back | Reuse the same cleaning rule consistently |
| Dictionary `{}` | Stores labeled values | Represent one employee or HR request |
| List `[]` | Stores an ordered collection | Process a source delivery of employee records |
| `for` | Repeats an action for each item | Validate every employee rather than one sample |
| `if` | Chooses an action when a condition is true | Reject an invalid status |
| `try` / `except` | Attempts work / handles a specified failure | Quarantine an invalid date while processing other rows |
| `raise` | Signals a failure | Prevent invalid data from being treated as successful |
| `.get()` on a dictionary | Reads a labeled value with an optional default | Handle missing source fields deliberately |
| `.strip()` / `.lower()` | Remove outer spaces / lowercase text | Normalize an email before matching |
| `bool()` | Converts a value to true/false | Check whether a required name is present |
| `datetime.strptime()` | Parses text using a stated date format | Turn a source date into a consistent calendar date |
| `httpx.Client.get()` | Requests information through an HTTP client | Practice fetching Workday with timeouts and retries |
| `requests.get()` | The analogous GET helper in the Requests library | Understand familiar API examples; this app uses HTTPX |
| `sqlite3.connect()` | Opens a database connection | Read and write the local filing cabinet |
| `.execute()` / `.executemany()` | Run SQL once / for many parameter sets | Store records safely with bound values |
| Commit / rollback | Make a transaction durable / undo it | Save the hire and tasks together or preserve the old state |
| `SELECT` / `WHERE` | Choose fields / select qualifying rows | Inspect the employees included in a metric |
| `COUNT(*)` | Count matching records | Calculate headcount or unresolved workload |
| `GROUP BY` / `HAVING` | Form groups / filter grouped results | Compare departments and find suspicious duplicate groups |
| `JOIN` / `LEFT JOIN` | Match related records / retain unmatched left records | Link tickets to employees and include people with no tasks |
| CTE / `WITH` | Name an intermediate query result | Explain a metric in readable stages |
| `COALESCE()` | Substitute a value for NULL | Show zero tasks for someone with no assignments |
| `CASE WHEN` | Choose a value under a condition | Count completed tasks separately |
| `ROW_NUMBER()` | Assign an ordered row number within each group | Find each employee's latest request |
| Window `SUM() OVER` | Calculate a running total without collapsing every row | Reconstruct monthly changes in workforce |
| `ON CONFLICT ... DO UPDATE` | Update an existing key instead of inserting a duplicate | Load a newer employee version incrementally |
| Primary key / foreign key | Identify a row / link to another row | Keep every request tied to a real employee |
| `unique` / `not_null` | Detect duplicate keys / missing values | Catch defects that could distort HR metrics |
| JSON / YAML | Exchange labeled data / express readable configuration | Submit API requests and declare dbt test rules |
| `GET` / `POST` / `PATCH` | Retrieve / submit / change part of a resource | Read policies, create requests, and update status |
| Authentication / authorization | Identify the caller / check permitted actions | Distinguish Maya from HR and protect Jordan's record |
| `pytest` / `assert` | Run tests / check an expected outcome | Detect regressions before demonstrating the application |
| TF-IDF / cosine similarity | Weight distinctive words / compare vector direction | Rank relevant policy passages without cloud services |
| Embedding | A numeric representation of content | A future neural index could match broader paraphrases |
| RAG / LLM | Retrieve context then generate / a language model | A future summarizer could explain authorized evidence |
| Idempotency / outbox | Safe replay / durable pending events | Prevent duplicate tasks and recover notification failures |
| Audit / telemetry | Record actions / measure runtime signals | Investigate denied access, failures, and slow requests |

## Project function map

| Function | Responsibility |
| --- | --- |
| `bootstrap()` | Initialize schema, examples, and demo identities once |
| `source_records()` / `MockWorkday.fetch()` | Generate a selected source scenario / fetch its simulated pages |
| `parse_date()` / `clean_employee()` | Normalize a date / validate one employee dictionary |
| `ingest()` | Fetch, validate, deduplicate, version-check, load, and record outcomes |
| `connect()` / `audit()` / `rows()` | Manage a transaction / record an action / return query dictionaries |
| `metrics()` / `freshness()` / `quality_checks()` | Compute business totals / assess age / detect invariant violations |
| `operations()` | Assemble operational evidence for the dashboard |
| `route_request()` | Assign a team or select human triage |
| `visible_policies()` / `answer_question()` | Filter policy access / retrieve a cited passage or escalate |
| `onboard()` / `enqueue()` | Create unique tasks / persist a unique pending event |
| `queue_reminders()` / `deliver()` | Queue overdue identifiers / retry mock delivery |
| `create_app()` | Assemble API routes, identity checks, startup, and UI serving |
| `evaluate()` / `main()` | Check retrieval regression cases / run the chosen CLI command |
