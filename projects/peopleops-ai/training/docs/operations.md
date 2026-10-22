# Local operations and recovery

## Service contracts

| Service | Host endpoint | Readiness |
| --- | --- | --- |
| PostgreSQL 17 + pgvector | 127.0.0.1:55432 | pg_isready; persistent named volume |
| Seed | One-shot process | Exit 0; one fixture marker; preserves existing data |
| Synthetic sources | 127.0.0.1:8801 | /health |
| FastAPI | 127.0.0.1:8800 | /health liveness; /ready database + seed |
| Streamlit | 127.0.0.1:8501 | /_stcore/health |

Docker and host Python use independent installed environments from the same
lock export. Python and database base images are pinned. Run these commands from
`training/`; root-directory `uv` commands target the older simulation.

## Fast development without rebuilding services

```sh
docker compose up -d db
uv sync --frozen
uv run python -m lab.bootstrap
uv run uvicorn lab.mocks:app --host 127.0.0.1 --port 8801
```

In separate terminals from the same directory:

```sh
uv run uvicorn lab.api:app --host 127.0.0.1 --port 8800 --reload
uv run streamlit run ui.py --server.address=127.0.0.1 --server.port=8501
```

Do not run host services and their Compose counterparts on the same ports.
The `.env.example` host URLs differ from Compose's internal service names.
Never repurpose the shell's HOME or other system variables.

## Failure diagnosis

| Observation | Evidence to inspect | Recovery |
| --- | --- | --- |
| Docker unavailable | `docker info` | Start Docker Desktop; repeat startup |
| Address in use | `docker compose ps`, existing local process | Stop only the conflicting process you own or change the mapped port deliberately |
| API501 | Response exercise identifier | Implement and test that exercise; no retry loop |
| API401 after restart | /lab/identities | Refresh the UI's local demo identity |
| API ready503, health200 | `docker compose logs --tail 30 db api` | Restore database; pool_pre_ping reconnects on subsequent requests |
| Mock503 at attempts1/2 | scenario/attempt parameters | E11 retries the same page with a bounded attempt count |
| Schema version2 | /mock/workday?scenario=schema_drift | Reject incompatible contract and preserve prior canonical data |
| Missing source row | Compare raw snapshot with canonical data | Do not infer deletion without a source deletion contract |
| Evaluation blocked | Per-case exercise identifier | Complete the corresponding capability; coverage is incomplete |

For a controlled local database outage, `docker compose stop db`, inspect
`/health` and `/ready`, then `docker compose start db`. Never use `down -v` as a
routine fix. Bootstrap refuses to reseed when its marker exists. Changes to the
schema need an explicit migration; `create_all` does not alter existing tables.

## Telemetry and evaluation interpretation

The API records route templates, status, latency, tool invocation metadata, and
provider usage in the last 1,000 process-local events. Error count excludes501,
which has a separate unfinished-exercise counter. Provider tokens and fake word
estimates are separate metrics. HTTP latency is observed request duration, not a
production SLO. Restart clears this telemetry. E10 writes durable business audit
rows; implementing that is part of the action exercise.

Evaluation correctness uses explicit expected status/fields/phrases. Retrieval
recall@3 checks expected chunk IDs; citation accuracy checks exact quotes against
policy version and section. Authorization failures compare expected denials;
privacy checks search labeled forbidden values. These checks are bounded examples,
not proof that all sensitive data or paraphrased hallucinations are detected.
Inspect case-level results and coverage before interpreting averages. Strict
evaluation returns nonzero for blocked cases and failures.

Foundation tests use synthetic/mock provider traffic only. The optional external
provider can time out, return incomplete output, or fail validation; it is never
silently substituted with a fake success. Production retry budgets, secret stores,
identity, retention, encryption, migrations, tracing, and deployments are Category C.
