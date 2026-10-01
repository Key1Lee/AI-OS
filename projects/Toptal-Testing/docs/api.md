# Local API contract

All paths below use `/api`. Fetch `/config` for the per-process local request
token, then send it as `X-Trainer-Token` on mutations. Browser mutations must
have matching Origin; accepted hosts are localhost and 127.0.0.1. No CORS grant
is needed. Restarting changes the token; refresh the browser to reconnect.

| Endpoint | Behavior |
|---|---|
| GET `/health`, `/config` | Runtime status and local request configuration, no credentials. |
| GET `/dashboard` | Actual stats, active draft, competencies, mistakes, due reviews, history and recommendation. |
| GET `/exercises`, `/exercises/{id}` | Public prompts, schemas and visible fixture only. |
| POST `/attempts` | Start with mode, optional exercise/competency/difficulty and timer; default resumes current work. |
| GET `/attempts/{id}` | Frozen version, saved text, assistance, interactions, pending submission and result. |
| PUT `/attempts/{id}/draft` | Optimistic revision check; stale writes return 409. |
| POST `/attempts/{id}/run` | Save query, execute public fixture and return candidate output without completing the attempt. |
| POST `/attempts/{id}/submit` | Persist request ID and text before hidden tests; atomic result/progress commit. |
| POST `/attempts/{id}/revise` | New linked attempt against the old frozen version; retains assistance. |
| POST `/attempts/{id}/hints`, `/solution` | Audited hints or explicit solution exposure. Completed evidence remains frozen. |
| POST `/attempts/{id}/clarifications` | Frozen-rule response and durable question; no independence penalty. |
| POST `/attempts/{id}/pause`, `/resume` | Preserve drafts; only one active primary challenge. |
| GET `/competencies`, `/competencies/{id}`, `/mistakes`, `/reviews`, `/history` | Evidence views; no fabricated scores. |

Invalid inputs return 422; missing resources 404; transitions/revision/request-ID
conflicts 409; local origin/token failures 403; unavailable execution/storage
503. Infrastructure failures preserve submissions and do not change mastery.
An in-flight request uses a bounded execution lease; the same saved body and ID
can safely retry after interruption. A changed body requires a new request ID.
Failed requests cannot reopen completed or inactive attempts. A superseded
worker cannot change the state or evidence owned by a newer recovery request.

Persistence tables: `competencies`, `exercise_versions`, `sessions`, `attempts`,
`attempt_submissions`, `test_runs`, `interactions`, `mastery`, `mistakes`, `events`
and Alembic's version register. Exercise definitions and evidence projections use
validated JSON; identities, references and uniqueness constraints are relational.
SQLite WAL and serialized short write transactions support this local single-user
contract. Grading is outside DB write transactions; PostgreSQL/distributed
multi-user operation has not been verified.
