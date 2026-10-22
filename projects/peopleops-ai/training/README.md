# PeopleOps AI · Interview training lab

A local, fictional enterprise sandbox for an experienced analytics engineer
learning to write application code independently. This is inspired by the
People Analytics AI Engineer role, not affiliated with Samsara.

**Foundation is implemented; business exercises are intentionally unfinished.**
The health routes, database, synthetic sources, fixture explorer, provider
transport, UI shell, and telemetry work. RAG answers, secure record lookups,
analytics queries, and HR actions become functional as you complete Category B.
Their APIs return `501 exercise_pending` until then. No hidden answer key or
legacy solution is imported.

## Start the complete environment

Prerequisites: Docker Desktop running, Docker Compose v2+, and roughly 2 GB of
free disk for images. No API key is needed. From this checkout:

```sh
cd /Users/key/_AI-OS/projects/peopleops-ai/training
docker compose up --build -d --wait --wait-timeout 120
```

Open [Streamlit](http://127.0.0.1:8501), [backend API docs](http://127.0.0.1:8800/docs),
or [mock source docs](http://127.0.0.1:8801/docs). All published ports bind to
loopback. The seed job exits successfully; the other four services stay running.
Opening `../Start-Training.command` runs the same startup command on macOS.

```sh
docker compose ps -a
docker compose logs --tail 50 api ui seed
docker compose down
```

`down` retains the named PostgreSQL volume. Do not add `-v` unless you intend to
delete training data. Bootstrap loads a fixed dataset once and preserves changes
on later starts. No legacy SQLite files are read or changed.

## Set up your editor and tests

Install [uv](https://docs.astral.sh/uv/) if it is unavailable, then:

```sh
uv sync --frozen
uv run python --version
uv run pytest
LAB_DATABASE_TESTS=1 uv run pytest
```

The environment uses Python 3.12. `uv sync` can install that Python version.
Default pytest runs foundation tests and skips PostgreSQL tests unless explicitly
enabled. With the database running, the second command checks real foreign keys,
pgvector, and fixture counts. The exercise suite is deliberately excluded.

Without host Python, run foundation tests inside the built container:

```sh
docker compose exec api python -m pytest tests/foundation
docker compose exec -e LAB_DATABASE_TESTS=1 api python -m pytest tests/foundation
```

## Your first checkpoint

Start with [NEXT_TASK.md](../NEXT_TASK.md). It records the active Level 2 task,
the five questions to answer before coding, the assistance level, and completion
criteria. State and scores live in the six project-root Markdown records;
the UI's initial “not attempted” labels are static scaffolding.

Edit `exercises/e01_cleaning.py`, implementing only `normalize_employee`.
Maya's actual fixture has `"  Maya   Chen  "`, `" PERSON001@EXAMPLE.TEST "`,
and `" Active "`. Return `Maya Chen`, `person001@example.test`, and `active` in
an `EmployeeRecord`; preserve the original dictionary.

```sh
uv run pytest tests/exercises/test_e01_cleaning.py
```

Eight tests initially fail because the function is unfinished. That is the
starting checkpoint, not a broken installation. The full contract, examples,
and expected outputs are in [exercises](docs/exercises.md). After your attempt,
we run the tests, discuss your code, grade it out of 10, and discuss production
implications before moving on. Failed attempts do not trigger automatic solutions.

Exercise code is bind-mounted read-only into containers (editable on the host).
Restart the API after an edit: `docker compose restart api`. New dependencies,
UI, fixtures, or tests require `docker compose up --build -d --wait`.

## Evaluations and failure simulations

```sh
uv run python scripts/smoke.py
uv run python -m lab.evaluate --allow-blocked
uv run python -m lab.evaluate
```

The first evaluation command is foundation smoke. The strict command exits 1
while exercises are blocked or checks fail. Both save `reports/evaluation.json`
and report coverage. A blocked policy question cannot count as a correct answer.
The 36 cases cover supported questions, missing support, ambiguous intent,
injection attempts, employee/candidate privacy, authentication, and confirmation.

Examples of mock behavior:

```sh
curl 'http://127.0.0.1:8801/mock/workday?cursor=0&limit=25'
curl 'http://127.0.0.1:8801/mock/workday?scenario=schema_drift'
curl 'http://127.0.0.1:8801/mock/greenhouse?scenario=intermittent&attempt=1'
```

All sources support `normal`, `timeout`, `intermittent`, `unavailable`, `missing`,
`duplicate`, `schema_drift`, and `malformed`. Attempts 1–2 fail in intermittent
mode; attempt 3 succeeds. The explicit attempt parameter makes failures
reproducible without shared mutable fault counters.

## Reproducibility and source control

`fixtures/enterprise.json` is generated with seed 42 and a fixed 2026-10-01
business date. Operational timestamps use UTC. `uv.lock` pins Python packages;
`requirements.txt` exports their hashes for container installation. PostgreSQL
and Python container base images are pinned by digest.

```sh
uv run python -m lab.fixtures
uv run python scripts/build_curriculum.py
uv run python scripts/build_evaluations.py
```

The project lives in the existing AI-OS Git checkout; no nested repository or
automatic commit is created. The `training/` directory is self-contained and can
also be copied into a new Git repository. Ignore `.env`, `.venv`, and `reports`.
Do not copy the existing solved app into your exercise modules.

## Optional real provider

Default `LLM_PROVIDER=fake` uses no network and reports word estimates, not real
token usage. Hash embeddings are deterministic lexical vectors, not a semantic
embedding model. The provider probe demonstrates the transport only; E06 still
owns evidence selection and grounded answer validation.

To deliberately enable the optional OpenAI Responses transport, copy
`.env.example` to `.env`, set `LLM_PROVIDER=openai`, `ALLOW_EXTERNAL_LLM=true`,
your own `OPENAI_API_KEY`, and an `OPENAI_MODEL` available to your account.
Restart with `docker compose up -d --force-recreate api`. This sends selected
prompts/evidence externally and can incur charges. No real API call was used in
verification. Transport contract tests use `httpx.MockTransport`.

## Read in this order

- [Progress](../PROGRESS.md): implementation and learning status are separate.
- [Business context and data grains](docs/data.md)
- [Architecture and rejected alternatives](docs/architecture.md)
- [Exercise contracts and checkpoints](docs/exercises.md)
- [Security and confirmation contract](docs/security.md)
- [Operations and recovery](docs/operations.md)
- [Staff interview rubric](docs/interview.md)
- [Verification evidence](docs/verification.md)

The original completed simulation remains in the parent directory on port 8765.
Its tests and dependencies are separate. Use this training directory for the
new curriculum.
