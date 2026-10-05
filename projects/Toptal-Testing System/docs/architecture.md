# Architecture

The Analytics Engineering trainer is an additional application in this project.

```text
React + TypeScript + Monaco (bundled locally)
  -> FastAPI /api (loopback, same origin)
  -> training service + pure scoring/selection functions
  -> SQLAlchemy repository / SQLite + Alembic
  -> isolated, time-limited DuckDB worker
```

`apps/web` owns interaction. `apps/api` owns HTTP validation and the local origin
boundary. `trainer/schemas` owns validated content and requests.
`trainer/exercises` loads a data-driven bank. `trainer/execution` owns the SQL
worker and result comparator. `trainer/services` coordinates durable attempts.
`trainer/repositories` owns transactions. `trainer/mastery` and
`trainer/adaptive` implement explainable policies without an LLM.

Exercise versions are immutable: a content hash detects a changed file with the
same version. Attempts reference the exact stored version, even after a new
version is seeded. Drafts persist before execution. Submissions persist before
grading. Completion, result, mistakes, mastery and events commit atomically.
Request IDs prevent duplicate submission credit. Revision success is assisted
practice evidence when earlier attempts failed, used hints, or saw a solution.

SQLite is the initial store. SQLAlchemy models and repository methods keep SQL
out of endpoints and scoring. A future PostgreSQL adapter still needs migration
and concurrency verification; portability is a boundary, not a tested claim.

## Security contract

SQL execution receives fixtures and query text only, never an application DB
connection. A fresh worker and in-memory DuckDB are created per case. Only a
single SELECT is accepted. External access, extension autoload/install, spills,
and configuration changes are disabled; threads, memory, output and time are
bounded. Credentials are removed from worker environment. On macOS a Seatbelt
profile additionally denies network and filesystem access outside runtime files
and a temporary worker directory. Execution fails closed if that sandbox is
unavailable. Other OS support requires an equivalent sandbox before execution.
This is a single-user local trainer, not a public arbitrary-code service.

HTTP mutation requests require the locally issued CSRF token and matching origin
when an Origin header exists. Host validation blocks DNS rebinding. Hidden cases,
expected outputs and solutions are excluded from public exercise responses.
The local source tree itself is not an answer-key security boundary.

