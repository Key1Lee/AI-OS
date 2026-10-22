# People Insights AI — executed evidence, 21 October 2026

## Delivered scope

One local Python/FastAPI process serves the HTML/CSS/JavaScript chatbot, loads
the pinned IBM CSV with pandas, calculates four metrics, remembers scoped
conversation context, produces comparisons and exports aggregate CSV reports.
Direct execution and a real local n8n relay both use the same Python functions.
An optional administrator import demonstrates separately labeled synthetic
Qualtrics-format aggregates. No real Samsara, Workday or Qualtrics data is used.

## Executed commands and results

From `peopleops-ai/people-insights-ai`:

```sh
.venv/bin/python scripts/download_data.py
.venv/bin/python -m pytest -q --junitxml=evidence/tests.xml
.venv/bin/python scripts/smoke.py --n8n
../policy_assistant/.venv/bin/ruff check app scripts tests
./start.sh
.venv/bin/python scripts/package.py
```

- Download and validation **passed**: 1,470 rows and 1,470 unique employee IDs.
  Sales 446, Research & Development 961, Human Resources 63. The pinned source
  SHA-256 is `a5c31e38bd7fafc9bc333884eb181b06b41b8e5e488e8f7ccb27199fb3be7659`.
  The first download attempt used the host Python's incomplete certificate store
  and failed verification. The successful downloader uses httpx's certificate
  bundle; certificate verification was not disabled and no data was substituted.
- **44 pytest tests passed**, one Starlette TestClient/httpx deprecation warning.
  Full result: `evidence/tests.xml`.
- Ruff and the frontend JavaScript syntax check **passed**.
- Native `./start.sh` launched the app on **127.0.0.1:8813**; health returned 200
  with `synthetic_only: true` and `dataset_rows: 1470`.
- n8n workflow **peopleInsightsAI01** was imported and published into the user's
  existing local runner. That runner was restarted for publication. The HTTP
  node uses `http://host.docker.internal:8813/api/chat` and was actually exercised.
  The portable native-n8n JSON instead uses `127.0.0.1:8813/api/chat`.
- **All five required scenarios passed in each mode**, Direct API and actual n8n,
  including comparison context, metric replacement, same-report CSV receipt and
  refusal to fabricate a Qualtrics score. CSV downloads contained two department
  rows for observed attrition and no employee identifiers.
- The real n8n failure branch **passed**: an invalid demo identity caused backend
  rejection and the webhook returned a safe error with no scores.
- A malformed n8n response and an unreachable relay were tested with deterministic
  mocks; both return 502 and never automatically replay a stateful turn. An actual
  ten-second backend timeout was not induced in the running workflow.
- Archive integrity and an extracted archive's test suite are checked separately
  during delivery. The extraction uses the build environment's installed Python
  dependencies; it is not a second-machine dependency installation claim.

The original 5,000-person report at port 8812 still returned 200 after the n8n
restart; n8n health also returned 200. An unauthenticated request to the separate
HR policy service's protected health URL returned 401; authenticated policy
health and the policy app's test suite were outside this change's verification.

## Functional coverage

| Required behavior | Executed evidence |
|---|---|
| Sales satisfaction | Independent csv-module count 274 / 446 = 61.4%; pandas report agrees |
| R&D work-life balance | Independent count 666 / 961 = 69.3% |
| HR observed attrition | Independent count 12 / 63 = 19.0% |
| Correct denominators | Null answers removed separately per metric; valid counts verified |
| Missing department | One department question, then one metric question, then report |
| Multi-turn memory | Department/metric context and new sessions tested |
| Comparison | Sales/R&D and HR/R&D aliases, percentage-point explanations |
| Invalid department | Unknown names and unsupported metrics cannot reuse prior parameters |
| Historical report | Unsupported response with no fabricated scores |
| Malformed/empty data | Empty input, missing columns, invalid ranges, duplicate IDs and checksum failures rejected |
| Authorization | Sales-only scope enforced; request roles rejected; cross-identity sessions/receipts isolated |
| n8n-compatible response | Real webhook executed; typed response schemas; safe error branch |
| Follow-up | HR retains metric; attrition retains both compared departments |
| CSV export | Exact displayed department/metric rows; no individual columns |
| No fabricated numbers | Source arithmetic, suppressed small samples, absent metrics and EX25 refusal |
| Optional import | Admin scope, exact schema, finite scores, count checks, source isolation and CSV formula protection |

An initial test exposed a missing metric when asking for a second comparison
department. The conversation state was fixed and the full suite rerun. The
final run above includes that regression check and subsequent schema checks.

## Measured local response times

Latest final live run: `2026-10-20T17:37:49.445540+00:00` (21 October in Korea).
Actual samples and scenario responses are in `evidence/live-checks.json`.
Each timing group is **20 sequential localhost HTTP report requests**, with
client connection reuse. The n8n measurement includes the FastAPI relay and
the real local webhook. These are small local timing checks, not capacity tests.

| Mode | HTTP p50 | HTTP p95 | Maximum |
|---|---:|---:|---:|
| Direct API | 1.78 ms | 2.45 ms | 3.00 ms |
| n8n relay | 50.63 ms | 72.03 ms | 93.43 ms |

These numbers measure application response time. **Manual reporting time saved
and business ROI have not been measured.**

## Browser and visual checks

- Executed scenarios A–E through the real chat UI in Direct API mode.
- Downloaded the actual displayed CSV through the browser's Download button.
- Selected **n8n workflow** and verified the rendered Sales report from that path.
- Desktop 1280×1000: page width 1265; chat and report visible side by side.
- Mobile 390×844: page width 375 with no document overflow. Each corrected KPI
  card has client/scroll width 147. A first mobile review found a wide KPI label;
  mobile layout was corrected and checked again.
- Browser error-log query returned no errors. Temporary viewport override reset
  after review; the application tab is retained for the user.
- Screenshots: `screenshots/people-insights-desktop.png` and
  `screenshots/people-insights-mobile.png`.
- Optional CSV import was verified through API tests, not a browser upload.

## Boundaries

The native application server remains running for the user. The original policy,
Qwen, training exercises and survey calculations were not changed. Shared registry
metadata and the project README gained links to this new application.

Demo identities are public fixtures, not verified authentication. There is no
live vendor access, production release or actual employee assessment. Import
source authenticity is not verified. Real-data operation requires a separately
approved identity, authorization, privacy, retention and deployment design.
