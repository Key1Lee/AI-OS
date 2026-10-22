# People Insights AI

**Employee Experience Reporting Assistant** — a small, runnable FastAPI and pandas
application for a hypothetical Samsara People Analytics use case. An HR manager
asks a question, receives department aggregates, compares departments, changes
metrics in a follow-up and downloads the displayed report as CSV.

The application uses the **1,470-record synthetic IBM HR sample**, not Samsara
employee data and not a genuine Qualtrics export. Job satisfaction and work-life
balance are sample proxies, not official Qualtrics EX25 measures. No paid model
or LLM arithmetic is used. The existing PeopleOps survey application is separate.

## Run locally

Use Python 3.11 or newer; this build was run with Python 3.12. From this directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_data.py
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8813 --reload
```

Open [People Insights AI](http://127.0.0.1:8813/). The **Direct API** route works
without n8n. After initial setup, `./start.sh` runs the same app without reload.
Stop the process with Ctrl+C. No Docker, database or cloud infrastructure is
required for this application. Use one process/worker because the demo session
store is in memory. Restarting clears conversations, reports and optional imports.

The verified CSV is included in the ZIP. Downloading again is optional when
offline; startup checks its SHA-256 and record count. A failed download reports
the error and never substitutes generated records. If the CSV is absent or
corrupted, health and report requests return an explicit unavailable response.

Source attribution: [original Kaggle dataset](https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset),
[user-specified public mirror](https://github.com/IamVasil/IBM-HR-Analytics-Employee-Attrition-Performance),
and [pinned CSV](https://raw.githubusercontent.com/IamVasil/IBM-HR-Analytics-Employee-Attrition-Performance/38fe9d45a87c0f0683ae46d5e9a1036f71423143/WA_Fn-UseC_-HR-Employee-Attrition.csv).
Commit: `38fe9d45a87c0f0683ae46d5e9a1036f71423143`.
SHA-256: `a5c31e38bd7fafc9bc333884eb181b06b41b8e5e488e8f7ccb27199fb3be7659`.
The sample contains no survey period, so the app supplies none.

## Try the demonstration

Use the default **HR manager · all departments** identity, Direct API or n8n:

1. **Give me the Sales happiness report.** Shows 446 employees, job satisfaction
   **61.4% favorable** and work-life balance **73.5% favorable**; n = 446 for each.
2. **Compare it with Research & Development.** Retains the two metrics; R&D has
   961 employees, **61.9%** favorable job satisfaction and **69.3%** favorable
   work-life balance. The report explains the displayed percentage-point gaps.
3. **What about attrition?** Keeps both departments; Sales **20.6%**, R&D **13.8%**.
4. **Can you download this report?** Offers the same aggregate report's CSV.
   Click **Download aggregate CSV**; no individual records are exported.
5. **Show me the Qualtrics engagement score.** Explains that genuine Qualtrics
   data is not connected and IBM proxies cannot supply official EX25 scores.

For clarification, start a new conversation and type **Give me an employee
happiness report.** Choose a department, then a metric or **Both**. The assistant
asks one question at a time. A direct **Show me Sales job satisfaction** request
needs no extra question. **What about Human Resources?** retains the prior metric.
Unsupported departments, metrics, personal records, SQL and historical trends
produce safe messages instead of invented scores.

The deterministic parser supports these patterns and common aliases (HR, R&D,
work-life, WLB). It is not an open-ended language model; unrecognized words prompt
clarification. Every completed report explicitly names its source.

## Scoring definitions

| Metric | Formula | Extra output |
|---|---|---|
| Job satisfaction | Valid 1–4 answers ≥ 3 / valid answers × 100 | Mean on 1–4 scale |
| Work-life balance | Valid 1–4 answers ≥ 3 / valid answers × 100 | Mean on 1–4 scale |
| Observed attrition | Yes / valid Yes-or-No indicators × 100 | Sample indicator, not prediction |
| Employees working overtime | Yes / valid Yes-or-No indicators × 100 | Descriptive sample percentage |

Percentages use one decimal; means use two. Null answers are excluded separately
for each metric. Invalid non-null values, unknown departments and duplicate
employee identifiers reject ingestion. Counts below five suppress the group or
question result, including its numerator/denominator. No overall aggregate is
published that could be used to subtract a suppressed department.

## API and demo authorization

Interactive schemas are at [API docs](http://127.0.0.1:8813/docs).
All analytics endpoints require an `X-Demo-Key`. The server maps these deliberate,
public fixtures to an identity; a user-supplied role is rejected:

| Public demo key | Server scope |
|---|---|
| `demo-hr-manager` | Three IBM departments |
| `demo-sales-manager` | Sales only |
| `demo-admin` | Three departments and synthetic import |

This is a mocked authorization demonstration, **not production authentication**.
The browser identity selector makes that explicit. Sessions and download access
are bound to the resolved identity. Sessions expire after 30 minutes of inactivity;
CSV receipts expire 30 minutes after generation. Each store is bounded to 256
entries. Downloaded CSVs contain only displayed department statistics.

| Endpoint | Purpose |
|---|---|
| `GET /health` | Data readiness; 503 if unavailable |
| `GET /api/departments` | Current identity's supported departments |
| `GET /api/metrics` | Metric definitions |
| `GET /api/sources` | IBM/import availability |
| `POST /api/chat` | Deterministic stateful chat |
| `POST /api/chat/route` | Same direct chat or fixed configured n8n relay |
| `POST /api/report` | Validated structured aggregate request |
| `GET /api/reports/{report_id}/csv` | Principal-bound aggregate export |
| `POST /api/admin/qualtrics` | Optional synthetic aggregate import |

```sh
curl http://127.0.0.1:8813/health
curl http://127.0.0.1:8813/api/departments -H 'X-Demo-Key: demo-hr-manager'
curl -X POST http://127.0.0.1:8813/api/chat \
  -H 'Content-Type: application/json' -H 'X-Demo-Key: demo-hr-manager' \
  -d '{"session_id":"demo-session-001","message":"Show Sales job satisfaction"}'
curl -X POST http://127.0.0.1:8813/api/report \
  -H 'Content-Type: application/json' -H 'X-Demo-Key: demo-hr-manager' \
  -d '{"department":"Sales","metrics":["job_satisfaction","work_life_balance","attrition"]}'
```

A completed response has `status: "report"`, `report`, and measured `elapsed_ms`.
`report` includes `source`, `metrics`, `departments`, `summary`, `limitations`,
`report_id` and `csv_url`. Each metric has its value, valid denominator, numerator,
optional mean, formula and publication status. Chat also includes `message`,
`options` and `context`. Clarifications/unsupported replies have `report: null`.
Actual complete request-sequence responses are in `evidence/live-checks.json`.

Missing/unknown identity: 401. Unauthorized structured department: 403. Unknown or
expired receipt: 404. Invalid schema or import: 422. Missing IBM data: 503.
Chat authorization denials return `status: "error"` without scores. No arbitrary
file path, SQL, provider URL or role is accepted as part of a chat/report request.

## Connect n8n

```text
Browser → /api/chat/route → n8n webhook → /api/chat
        ← structured response ← n8n Respond to Webhook
```

The UI serves from FastAPI. In **n8n workflow** mode it sends the same chat body
and demo identity through a same-origin relay; the browser needs no CORS bypass.
The HTTP node forwards to `/api/chat`, not `/api/chat/route`, avoiding recursion.
Python owns validation, authorization, state, scoring, summaries and exports.

1. Start this backend on port 8813.
2. In local n8n, import `n8n/people_insights_workflow.json` from the workflow menu.
3. Set **Python chat and report API → URL** to your backend. Native n8n on the same
   Mac: `http://127.0.0.1:8813/api/chat`. For the user's existing macOS Docker n8n:
   `http://host.docker.internal:8813/api/chat`. The second JSON
   `people_insights_workflow.macos-existing-n8n.json` already has that URL.
   No new Docker service is required. Linux containers need an explicitly approved
   host gateway/network arrangement; the Mac address is not universal.
4. Publish/activate the workflow. Its production webhook path is
   `/webhook/people-insights-chat`. Set `N8N_WEBHOOK_URL` in `.env` to the correct
   local n8n port (5680 on this Mac). Restart FastAPI after an environment change.
5. Choose **n8n workflow** in the UI and ask for a Sales report.

Regenerate a native workflow with another backend URL if needed:

```sh
python scripts/build_workflow.py --backend-url http://127.0.0.1:8813/api/chat
```

Test the published webhook directly:

```sh
curl -X POST http://127.0.0.1:5680/webhook/people-insights-chat \
  -H 'Content-Type: application/json' -H 'X-Demo-Key: demo-hr-manager' \
  -d '{"session_id":"n8n-demo-001","message":"Show Sales job satisfaction"}'
```

The workflow has four functional nodes plus one explanatory note. Its HTTP node
has a ten-second timeout; success returns the backend JSON, and failure returns
a safe message with no scores. There are no automatic retries of stateful turns.
The relay times out after 15 seconds. It never silently replays through the direct
route; select Direct API explicitly, and start a new conversation after an
uncertain timeout. Node execution payload saving is disabled. No time-saved
estimate, MCP access or paid provider is configured for this new workflow.

Troubleshooting: webhook 404 usually means the workflow is unpublished or the
production path/port is wrong. A safe backend error can indicate a missing demo
header, unavailable data or a wrong HTTP node URL. Check `/health` on the Mac,
then test the backend from the n8n environment. `localhost` inside a container is
that container. A 502 from the UI relay means n8n was unreachable or returned an
invalid reply; Direct API remains available. Do not disable TLS or expose raw HR
data to work around a connection issue.

## Optional Qualtrics-format import

This project's runtime is **synthetic only**. The extension demonstrates the
schema and source isolation for future authorized aggregate imports. It does
not verify source authenticity or connect to a real account. It accepts supplied
percentages, never silently recomputes them as IBM scores or calls them EX25.

Select **Demo administrator**, expand the import panel and use
`data/qualtrics_template.csv`. It is explicitly marked as a synthetic example.
After import, ask **Show Qualtrics engagement for Sales**. IBM remains the default
unless Qualtrics was explicitly selected in the conversation. Switch back with
**Show IBM Sales job satisfaction**. The result always labels the source.

Required exact headers: `Department,SurveyName,SurveyPeriod,Metric,Score,RespondentCount,ScoringMethodology`.
Metric keys: the four IBM names or `engagement`; percentages must be finite 0–100,
respondent counts nonnegative integers. Supply a documented methodology and period;
the app does not invent either. One survey/period per CSV, no duplicate
department-metric rows, 200 KB/500-row limits. Groups with fewer than five
respondents are withheld. Employee totals are not inferred from question counts.

API import requires `X-Demo-Key: demo-admin` and JSON containing `csv_text`,
`synthetic_demo: true` and `authorized_aggregate: true`. Only one in-memory
Qualtrics-format survey is retained; each valid import replaces the previous one.
Any failed validation preserves the previous import. Different sources are never
merged. No individual data columns are accepted. CSV formula prefixes in provided
descriptions are neutralized on report export.

Future real data requires verified identity, department authorization, approved
survey definitions, credentials, retention rules, a protected import process,
privacy review and appropriate deployment controls. Workday and actual Qualtrics
adapters can replace the source behind these governed aggregate contracts. They
are not implemented or represented as connected in this local demo.

## Tests and measured behavior

```sh
pytest -q --junitxml=evidence/tests.xml
python scripts/smoke.py
# With the configured local n8n workflow running:
python scripts/smoke.py --n8n
```

The automated suite covers independently counted source metrics, nulls and
denominators, malformed ingestion, privacy suppression, one-question clarification,
context and identity isolation, comparison, follow-ups, unsupported requests,
authorization, CSV exports, n8n-compatible responses, relay failure and optional
import validation. It uses local fixtures/sample data and no paid keys.

Actual run evidence and timing samples are in `evidence/tests.xml` and
`evidence/live-checks.json`; the dated scope and browser checks are in
[VERIFICATION.md](VERIFICATION.md). The live script exercises all five required
scenarios in both modes and makes 20 sequential report requests per mode. It
records HTTP p50/p95/max, not a production capacity benchmark. **Business time
savings have not been measured.**

## Core functions in elementary language

| Function | What it does |
|---|---|
| `validate_data()` | Checks the required columns, identifiers and allowed values. Missing metric answers remain missing. |
| `load_data()` | Reads and fingerprints the pinned IBM CSV. It reports a problem rather than inventing replacement records. |
| `calculate_metric()` | Counts valid answers and calculates their percentage. It withholds small samples. |
| `build_report()` | Filters the data to the requested departments and calls the scoring functions. It returns aggregate rows and source information. |
| `describe_report()` | Turns calculated results into short sentences. It describes differences without claiming causes. |
| `report_csv()` | Writes only the displayed aggregate rows to CSV. It never exports employee identifiers. |
| `SessionStore.get()` | Finds a conversation belonging to the current demo identity. Old sessions expire. |
| `unrecognized_words()` | Spots terms the small parser does not understand. This prevents silently using an old department for an unknown request. |
| `handle_chat()` | Remembers selections and asks for one missing detail at a time. Once the request is clear, it calls the same reporting code as the structured API. |
| `principal()` | Looks up a fixed demo identity on the server. The request cannot grant itself a role. |
| `create_app()` | Connects the local data, session memory, report endpoints and frontend. Each app instance has separate state. |
| `save_report()` | Checks department scope before filtering and stores a temporary export receipt. Another identity cannot download it. |
| `route_chat()` | Sends the same request directly or through the configured n8n webhook. A failed relay produces a visible error. |
| `parse_qualtrics()` | Validates a provided department-score CSV. It retains the supplied survey and scoring definitions. |
| `provided_report()` | Displays imported scores without calculating missing ones. It clearly distinguishes that source from IBM. |
| `scripts/download_data.main()` | Downloads the pinned sample and verifies it before replacing the local CSV. |
| `scripts/build_workflow.workflow()` | Creates importable n8n nodes and connections. The workflow relays requests instead of duplicating analytics rules. |
| `scripts/smoke.demonstrate()` | Runs the five required conversations against the running app. It checks reports and an actual CSV download. |
| `scripts/smoke.benchmark()` | Times sequential local HTTP requests. It does not estimate labor savings. |

## Explain it in a Staff AI Engineer interview

**Business:** HR managers repeatedly need the same departmental reports. This
demo automates their preparation through a conversation and consistent exports;
an actual business time-savings study is still needed.

**Analytics engineering:** The backend validates the source, keeps explicit
metric definitions and independent denominators, applies department scope before
filtering, suppresses small groups and returns traceable aggregates.

**AI engineering:** A bounded intent parser remembers conversation context and
asks for missing parameters. Python calculates every value; n8n coordinates the
request/response path. There is no need for a vector database or a language model
to do arithmetic. Future natural-language adapters must preserve these contracts.

This is not Samsara's actual architecture, staffing, survey data or production
security. The complete source ZIP is generated with `python scripts/package.py`.
