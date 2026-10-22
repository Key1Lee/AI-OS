# Samsara People Analytics — Demo

A working Next.js + native n8n employee-survey demonstration. **All data is
fabricated. These are not Samsara's actual engagement results.** No API key,
Qualtrics account, paid service or cloud hosting is required. The assistant uses
the existing local **Qwen3-4B-Q4_K_M** runtime; analytics remain deterministic.

## Synthetic population

The demo has **5,000 eligible employees per year**, split as follows for each of
2024, 2025 and 2026 YTD. This allocation is illustrative, not actual Samsara staffing.

| Department | Eligible employees | Share |
| --- | ---: | ---: |
| Human Resources | 250 | 5% |
| Marketing | 500 | 10% |
| Engineering & Product | 2,000 | 40% |
| Sales | 1,250 | 25% |
| Customer Success & Support | 1,000 | 20% |
| **Total** | **5,000** | **100%** |

Fixed seeds produce realistic variation in participation and correlated survey
answers, plus missing, invalid, incomplete and duplicate records. Annual headcounts
stay constant in this scenario; three years represent 15,000 eligible survey
opportunities, not a claim of 15,000 distinct employees. Scores continue to give
valid respondents equal weight. The 2026 cutoff remains October 21, 2026.

The assistant uses Qwen to understand natural phrasing, possessives and department
shorthand. Try “What was Engineering’s survey score?”, “Which department scored
highest in 2026?” or “What questions were employees asked?” Omitted years mean all
three available years; latest means 2026 YTD. Explicit dropdown filters take
precedence. Unknown departments and questions outside the approved data are declined.

The mock-export request uses a bounded 8 MB JSON limit for the expanded source.
The golden reference covers all 217 combinations: 7 nonempty year subsets × 31
nonempty department subsets. Original 180-eligible fixtures and evidence are
preserved under `evidence/archive/180-eligible/`; they describe the earlier demo.

## Run

The existing Mac model server must be running on `127.0.0.1:8080`. Check
`curl http://127.0.0.1:8080/health`. If stopped, run `python3 -m py_dev serve`
from the AI-OS root in a separate terminal. The container reaches that same local
server at `host.docker.internal:8080`; no model download or API key is needed.
The app refuses incomplete Qwen output or an unavailable model, with no hidden
chat fallback. The initial verified dashboard remains available without Qwen.
See [local Qwen architecture](docs/local-qwen.md).

Requires Docker with Compose. From this directory:

```sh
docker compose up --build
```

Open [the application](http://localhost:3000) and [n8n](http://localhost:5678).
Startup imports and publishes the included workflow automatically into an isolated
n8n volume. Allow the JavaScript runner to register before the first question.
The dashboard can load before n8n finishes starting; retry a question if necessary.

The n8n editor may offer first-run local owner-account setup. This is only needed
to use the editor, not the published webhook or application. Complete it yourself
with local demo credentials if desired. No external n8n account is required.

Ask the default three-year question or use the example buttons. Year and
department filters execute the same real n8n pipeline and update the answer,
KPIs, charts, annual table and verification receipt together. Chat answers include
actual n8n execution IDs and Markdown source excerpts. Export CSV downloads the
current verified annual and department metrics with a synthetic-data label and source checksum.

```sh
curl -X POST http://localhost:5678/webhook/samsara-survey \
  -H 'Content-Type: application/json' \
  --data '{"question":"What was everyone’s company survey score at Samsara over the last three years?"}'
```

The browser uses `http://localhost:3000/api/chat`; the web service forwards to
`http://n8n:5678/webhook/samsara-survey`; n8n uses `http://web:3000/api/...` internally.
There are no browser-only localhost addresses in internal workflow HTTP nodes.
Exposed ports bind to 127.0.0.1. To select alternative host ports:

```sh
WEB_PORT=3010 N8N_PORT=5679 docker compose up --build
```

Stop these services with `docker compose down`. The n8n volume is preserved.

## Open the workflow in n8n

After local owner setup, open the **Samsara People Analytics — Synthetic Demo**
workflow. It is imported and published during startup. To manually import into
another local instance, use the editor's workflow menu → Import from File →
`n8n/qualtrics-survey-demo.json`, then publish it. Keep the Compose service names
or update all internal backend URLs consistently.

- Published URL: `http://localhost:5678/webhook/samsara-survey`.
- Test URL: `http://localhost:5678/webhook-test/samsara-survey`.
- The test URL only works while “Listen for test event”/Execute workflow is active
  in the editor. The app always calls the published URL.
- The fixed workflow ID is project-local: `samsaraSurveyDemo2026`.
- Restart imports changed checked-in workflow JSON before starting n8n. Editor
  edits survive restarts when that source JSON is unchanged. Export desired editor
  edits before changing the source workflow. Other n8n instances are untouched.

## Checks and fixture regeneration

Node 20.9+ (Node 24 used here) and Python 3.10+ are required for host development:

```sh
npm --prefix web ci
python3 scripts/verify.py
python3 -m unittest discover -s tests -p '*_test.py' -v
npm --prefix web test
npm --prefix web run lint
npm --prefix web run typecheck
npm --prefix web run build
python3 scripts/integration.py
```

The last command needs both Compose services running. It tests all five example
questions against independent Python results, chat/dashboard agreement, direct
webhooks, rejected inputs, missing data, changed source snapshots and filtering.
It saves actual receipts in `evidence/integration.json`. Unit tests cover all 217
filter combinations, intentionally altered scores, corrupt references, unavailable
references, unequal department weighting, duplicate revisions and unavailable n8n.

`python3 scripts/checks.py` runs and records the six host checks above in one
command. For the bounded live failure drill, run `python3 scripts/failure_probes.py`.
It temporarily corrupts/removes the reference only in this demo's web container,
restores the exact tracked fixture, stops/restarts only this project's n8n, and
confirms recovery. Do not run it while presenting the demo. Results are saved in
`evidence/failure-probes.json`. Read-only node-execution proof can be captured with
`docker compose exec -T n8n node /demo/inspect-executions.cjs`.

Regenerate fictional source data and its independent golden reference explicitly:

```sh
python3 scripts/seed_data.py
python3 scripts/verify.py --write
npm --prefix web run workflow
docker compose up --build -d
docker compose restart n8n
```

The seed is fixed. Never regenerate the reference merely to hide a failed metric.
After workflow changes, regenerate the workflow and restart n8n.

For hot-reload development, keep Docker n8n running and start Next on a spare port:
`npm --prefix web run dev -- --port 3001`. For a fully host-based web-to-n8n path,
set `N8N_WEBHOOK_URL=http://localhost:5678/webhook/samsara-survey` (the default).
The workflow still calls the Compose web service; rebuild it when backend logic
changes so both web instances use the same implementation and fixtures.

## API contract

All endpoints use JSON and `Cache-Control: no-store`. Error envelopes contain
`error` and `validation.status`; errors never claim a verified report.

| Endpoint | Request | Response |
| --- | --- | --- |
| `GET /api/mock-qualtrics/responses` | None | Full fictional `responses`, `headcount`, `sourceChecksum`, `synthetic` |
| `POST /api/metrics` | `{snapshot:{responses,headcount}, plan:{years,departments,metric}}` | `{report, validation, plan, source}`; 409 with `report:null` for reconciliation failures |
| `POST /api/assistant/interpret` | `{question, filters?}` | Local Qwen interpretation, validated plan, retrieval query and model receipt |
| `POST /api/assistant/answer` | `{question,interpretation,metrics,references}` | Revalidated report, Qwen-selected evidence and deterministic answer text |
| `POST /api/rag/search` | `{question}` | `{references:[{document,excerpt,relevance}], numericalSource:false}` |
| `GET /api/report` | Optional comma-separated `years`, `departments` query parameters | Dashboard-ready verified report and receipt |
| `POST /api/chat` | `{question, filters?:{years,departments}}` | Verified report plus `answer`, `references`, `orchestration:{mode,executionId,workflowId}`, actual `ai` model receipts |

`report` contains annual, department and pooled metrics, selected-period trend,
and quality counts. `validation` contains PASS/FAIL/NOT VERIFIED, checksum,
retrieved/used counts, every comparison, timestamp and an explanatory message.
Missing or malformed independent reference withholds the report. There is no
hidden fallback if n8n is down. `/api/report` initializes the dashboard directly
and truthfully makes no n8n-execution claim.

## Files and definitions

- `web/src/lib/metrics.ts`: TypeScript metric engine.
- `scripts/verify.py`: independent Python calculator and 217-scope golden generation.
- `web/src/lib/verification.ts`: source/field comparisons and numerical gate.
- `knowledge/`: survey questions, custom definition, quality rules and privacy.
- `n8n/qualtrics-survey-demo.json`: executable native workflow with error branches.
- `docs/workflow.mmd`: Mermaid architecture source.
- `docs/architecture.md`: elementary walkthrough and exact metric contract.
- `docs/requirements.md`: business problem, success criteria and exclusions.
- `docs/verification.md`: observed validation and remaining limitations.

The custom **Demo Company Engagement Score** averages the three 1–5 answers,
subtracts one and multiplies by 25 for each valid respondent; then it averages
respondents equally. The pooled score weights responses across years equally.
Headcount totals 5,000 eligible survey opportunities per year across five departments. 2026 ends
October 21 in UTC; 2024 and 2025 are full years. No statistical or causal claims
are made. This is an aggregate local sandbox, not a production HR product.

Implementation references: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation),
[n8n Server CLI import/publish](https://docs.n8n.io/hosting/cli-commands/).
