# Implementation verification evidence

Run date: **2026-10-18**, local macOS arm64. This records implementation checks,
not an independent review or learner assessment.

## Verified

| Check | Observed result |
| --- | --- |
| Runtime | Host Python3.12.13; container Python3.12.15; PostgreSQL17.11; pgvector0.8.7; base images pinned |
| Compose startup | Database, mocks, API, and UI became healthy; seed exited0 |
| PostgreSQL | Real pgvector extension, 120 employees, 240 canonical events, 16 policy versions, 60 tickets |
| Vector storage | Stored policy vector round-tripped; self cosine distance approximately0 |
| Database constraints | Orphan ticket and duplicate employee email rejected |
| Foundation suite | `LAB_DATABASE_TESTS=1 uv run pytest`: **30 passed** |
| Container suite | Same30 foundation tests passed inside the non-root API container |
| Default/registry command | **27 passed,3 skipped** when database tests are not enabled |
| Existing demo | Root `uv run pytest`: **60 passed**; no legacy business code changed |
| Live smoke | Health/readiness, identity authentication, fixture counts, pagination, intermittent503, schema2 drift, and actual HTTP timeout passed |
| Learner baseline | Explicit PostgreSQL-enabled exercise suite: **62 intentionally failing tests**; eight are E01. No working solutions supplied |
| Evaluation | **36 scenarios: 4 passed, 32 blocked, 0 executed failures**; coverage11.1% |
| Strict evaluation | Exited1 as intended because32 scenarios are blocked |
| Controlled DB outage | /health200, /ready503, fixture explorer200; after database restart, /ready200 |
| No accidental HR actions | After UI/API/evaluation checks:60 tickets,0 PTO requests,0 action receipts |
| Browser | Overview,120-row data table, policy pending state, payroll preview pending state, operations, and fake provider probe inspected |
| Registry | Registry validation passed for11 systems |

The four executable evaluation cases check authentication/input validation.
They do **not** establish RAG accuracy, record authorization, citation quality,
or action safety. Retrieval and citation metrics are null until those cases
execute. The first learner implementation remains pending and ungraded.

## Limits and resolved setup issues

- The initial Compose build tried to export the same image from four parallel
  build targets. Fixed by making only the API service build the shared image.
- The initial editable install occurred before package files existed. Reinstalled
  the local package and set the explicit test import path; foundation tests pass.
- Starlette emits one deprecation warning for its HTTPX TestClient path. Tests
  pass with the locked HTTPX version. Migrating the client is a later dependency
  transition, not a reason to hide the warning.
- Browser QA used the app's default narrow viewport. No desktop-size layout or
  load/performance benchmark is claimed.
- Rebuilding the running UI produced temporary WebSocket/health connection logs;
  after reload the final exercise catalog rendered successfully. Screenshot:
  `screenshots/checkpoint.jpg`; focused first checkpoint: `screenshots/first-exercise.jpg`.
- Container tests emitted a pytest cache permission warning because `/app` is
  owned by root while the service runs as an unprivileged user. The tests passed;
  use `-o cache_dir=/tmp/peopleops-pytest-cache` if you want a writable test cache.
- No real OpenAI API call, external HR connection, production deployment, or
  paid model was used. The optional adapter has a mocked wire-contract test.
- Local health does not mean Category B business features are implemented.

The original SQLite/dbt source was unchanged. Its unit suite was rerun for
isolation; previous dbt evidence remains in `../../docs/verification.md`.
Owned preview containers are stopped after verification; the named volume is
retained. Use the README startup command to resume.
