# Observed verification — October 22, 2026

## October 22 — local Qwen question interpretation and RAG

The interactive assistant now uses actual `Qwen3-4B-Q4_K_M` inference on the
existing Mac runtime for interpretation and evidence selection. It no longer
routes free-form chat through the fixed-vocabulary parser. Unknown department
names can be preserved in structured generation and rejected by local allowlists;
forcing an enum during generation had allowed an unknown department to become a
company-wide request. Explicit dropdown filters still override inferred scope.

Observed on the final running Compose build:

- `evidence/checks.json`: all six commands PASS; 22 TypeScript tests, 3 Python
  tests, independent 217-scope reconciliation, lint, typecheck and production build.
- `evidence/qwen-integration.json`: 8 supported natural-language cases passed
  through actual Qwen and n8n, with provider token/latency receipts and independent
  Python agreement. Cases cover Engineering possessives, eng/latest, CS/last year,
  highest department, question wording, causal limitations, duplicates and counts.
  Finance, weather, fabricated-score instructions and actual attrition were declined.
  Altered metrics returned 409 and injected knowledge returned 502, without a report.
- `evidence/integration.json`: the original five questions and all five canonical
  departments passed; dashboard/chat agreement, webhook, filters, missing records,
  changed-source rejection and checksum assertions passed with real Qwen receipts.
- `evidence/failure-probes.json`: corrupted reference produced FAIL with no report,
  missing reference produced NOT VERIFIED, stopped project n8n produced 503, and
  both the original reference and service recovered. The shared Qwen server was
  preserved. Qwen outage, truncated output and wrong-model responses are exercised
  through injected unit-test transports; no live shared-model outage is claimed.
- `evidence/qwen-browser.json` and `qwen-assistant.jpg`: refreshed the user's stale
  180-eligible tab and submitted “What was Engineering's Survey Score”. Actual
  n8n execution **93** displayed 60.19, 66.55 and 71.82 for 2024/2025/2026 YTD,
  with the same values in the table and no browser console errors.
- `evidence/qwen-executions.json`: native execution 93 completed both Qwen HTTP
  nodes, retrieval, metrics, answer validation and the webhook response.

RAG uses query rewriting and keyword retrieval over four approved local Markdown
files. Qwen selects exact server-owned fact/passage IDs; the rendered answer is
extractive. There is no embedding model, vector database, generated arithmetic,
cloud fallback, statistical test or causal analysis. The fixture and golden
reference are unchanged by this integration. The earlier leadership PDF is a
historical export of the pre-Qwen workflow.


The updated application starts in Docker Compose on ports 3000 and 5678. The
fictional population is 5,000 eligible employees in each reporting year, split
across the five requested departments. These are illustrative staffing and survey
figures, not actual Samsara employee data. The 2026 reporting cutoff remains
October 21, 2026, in UTC.

| Department | Eligible per year |
| --- | ---: |
| Human Resources | 250 |
| Marketing | 500 |
| Engineering & Product | 2,000 |
| Sales | 1,250 |
| Customer Success & Support | 1,000 |
| **Total** | **5,000** |

## Reconciled annual results

| Period | Score /100 | Valid responses | Eligible | Response rate | YoY points |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024 | 57.28 | 3,770 | 5,000 | 75.40% | — |
| 2025 | 63.13 | 3,843 | 5,000 | 76.86% | +5.86 |
| 2026 YTD | 68.58 | 3,720 | 5,000 | 74.40% | +5.45 |

Pooled score: **62.97/100** from **11,333** valid responses.
Pooled eligibility is 15,000 employee-year opportunities, not 15,000 distinct
employees. Company and pooled scores weight valid respondents equally.

The source contains 12,335 submission records. Deduplication removes 116
records; validity checks exclude 886 unique responses. All 123 comparisons
in the full-scope runtime receipt pass.

Source checksum: `c40c1567c7737bcd61eb53a932c10f9d936dd0862def22c0f267504b8c5500fd`.

## Checks and acceptance evidence

| Criterion | Observed evidence |
| --- | --- |
| Reproducible realistic source | Python regenerates identical bytes into an isolated temporary directory; asserts all 15 department-year cohorts and 5,000 annual eligibility totals |
| Independent numerical reconciliation | All 217 nonempty year/department subset combinations pass: 7 year subsets × 31 department subsets |
| Business rules and regressions | 18 TypeScript and 3 Python tests pass, including unequal weighting, latest invalid duplicates, YTD cutoff, old department aliases, ampersands, partial three-department scope and source tampering |
| Larger snapshot over HTTP | Actual snapshot exceeds the former 1 MB limit; bounded 8 MB parser accepts it, oversized bodies are rejected, and the full export passes through n8n |
| Real n8n workflow | Default question, four other examples, and one question per requested department all return PASS; actual execution IDs and reports are in `evidence/integration.json` |
| Chat/dashboard consistency | Integration compares returned report objects against Python and `/api/report`; browser checks compare displayed annual scores with the answer |
| Headcount and filters | Browser verifies five department rows total 5,000, checks per-department scope denominators, and checks the year filter |
| Responsive charts | Browser checks desktop, tablet and mobile layouts, including long names, three visible charts, and no page-level horizontal overflow |
| CSV export | Exports annual and department rows with validation statuses and the source checksum; numerical values come from the same verified report |
| Negative runtime checks | Corrupt reference returns FAIL/report:null, missing reference returns NOT VERIFIED/report:null, unavailable n8n returns 503, and recovery succeeds |
| Build gates | Host build, lint, type checking and Docker production build pass; logs in `evidence/checks.json` and `evidence/docker-build.log` |

The native workflow executes Webhook → Parse Request → Valid Request → Mock
Qualtrics → Metrics Engine → RAG Retrieval → Build Grounded Answer → Respond to
Webhook. The calculator and verification gate run inside the Metrics Engine API;
RAG provides approved methodology excerpts. Read-only execution summaries are
saved in `evidence/n8n-executions.json`. Live failure drill receipts are in
`evidence/failure-probes.json`. Browser observations and screenshots are in
`evidence/browser.json`, `evidence/dashboard-desktop.jpg`,
`evidence/verified-chat-desktop.jpg` and `evidence/dashboard-mobile.jpg`.

During service replacement, an early integration request reached the old
department parser; the metrics endpoint rejected that stale plan. After workflow
import/publish completed, the fresh full and department executions passed.
Original 180-eligible fixtures, screenshots and receipts remain in
`evidence/archive/180-eligible/` as historical evidence.

## Limits

The source and results are entirely synthetic. Natural-language interpretation and evidence selection now use the existing local
Qwen model. See `local-qwen.md` and current `evidence/qwen-integration.json`; the
October 21 leadership PDF describes the earlier workflow. The golden Python reference
is regenerated explicitly when source data changes and is bound to that source
checksum; Python is not executed per browser request. Reporting remains aggregate
and local, with no production authentication or real Qualtrics integration.
Only the published webhook is exercised; the optional n8n editor test listener
is documented but not tested. The optional Python task-runner warning in n8n
does not affect the JavaScript workflow.
