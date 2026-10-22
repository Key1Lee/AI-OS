# Observed verification — October 21, 2026

The application was built and started with Docker Compose on local ports 3000 and
5678. Both services reported healthy. The real published n8n webhook executed the
native Webhook, Parse Request, Valid Request, Mock Qualtrics, Metrics Engine, RAG
Retrieval, Build Grounded Answer and Respond to Webhook nodes. This is an executed
workflow, not a diagram or a fallback simulation.

## Reconciled synthetic results

| Period | Score /100 | Valid responses | Eligible | Response rate | YoY points |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024 | 54.38 | 137 | 180 | 76.11% | — |
| 2025 | 63.40 | 135 | 180 | 75.00% | +9.02 |
| 2026 YTD through October 21 | 69.74 | 133 | 180 | 73.89% | +6.34 |

The pooled score is 62.43/100 across 405 valid responses and 540 employee-year
opportunities. Selected-period change is +15.36 points. These values are entirely
fabricated, not Samsara's actual results. Of 495 retrieved submissions, 18 duplicate
records were removed and 72 invalid unique responses were excluded.

The source snapshot checksum, including eligible headcount, is
`76259ef730acb947bb6c45dff30813db400ddf3d9fc590372c19ff4e575418f1`.
The full-scope receipt contains 87 passing comparisons, including dimensions,
counts, scores, rates, YoY, department results, pooled results, trend and checksum.

## Acceptance evidence

| Criterion | Observed evidence |
| --- | --- |
| Build, lint, type checking | Successful host commands and production Docker build; `evidence/checks.json`, `evidence/docker-build.log` |
| Deterministic fixture | Python seed test regenerates source bytes in an isolated temporary directory; all nine cohorts have 60 eligible participants and 40–50 valid responses |
| Independent calculations | 14 TypeScript tests, 3 Python tests, independent Python fixture check; all 49 nonempty filter combinations agree |
| Default question and four examples | Each executes the real webhook and reconciles its returned report independently in `scripts/integration.py`; receipts in `evidence/integration.json` |
| Actual native n8n nodes | Read-only execution database summaries in `evidence/n8n-executions.json` show complete successful node paths |
| Chat/dashboard agreement | Integration compares report objects; browser assertions compare each visible annual-table score with the rendered answer |
| RAG grounding | Formula question ranks `engagement_score_definition.md` first; normal methodology explanations extract approved Markdown lines; document names and excerpts appear in the UI |
| Year and department filters | Browser changed year to 2025 and department to Engineering; answer, table, KPIs and charts updated through n8n; eligible headcount became 60 |
| Duplicates and invalid rows | Both implementations test latest revision before validation, tie ordering, missing/out-of-range/fractional scores, completion and YTD cutoff |
| Corrupt computed score/reference | Intentional score alteration fails unit verification; live container reference corruption returns 409/FAIL from report and actual n8n chat with `report:null` |
| Missing reference | Live report returns NOT VERIFIED and `report:null` |
| Missing survey records/unknown inputs | Live API rejects empty snapshot, Finance, 2023 and individual-answer questions; direct webhook input validation also exercised |
| Unavailable n8n | Live drill stops only this n8n service; chat returns 503/NOT VERIFIED with no-execution message; restart and a fresh passing execution confirm recovery |
| Responsive layout | Browser inspection at desktop 1440px, tablet 1024px and mobile 390px confirmed all three charts and no page-level horizontal overflow; annual table scrolls internally on narrow screens |

Browser receipts and screenshots are in `evidence/browser.json`,
`evidence/dashboard-desktop.jpg`, `evidence/verified-chat-desktop.jpg` and
`evidence/dashboard-mobile.jpg`. Failure receipts are in
`evidence/failure-probes.json`. Scripts preserve actual timestamps and execution
IDs; static documentation does not fabricate a fresh run timestamp.

An initial imported formatter referenced a transpiler helper that was absent in
n8n. The generated Code node now declares that helper explicitly, a sandbox test
executes the actual generated nodes, and workflow-source checksum tracking imports
changed JSON before n8n starts. Subsequent actual webhook executions passed.

## Limits

Natural-language recognition intentionally uses a restricted deterministic
vocabulary; unsupported questions are rejected. No LLM is configured. The n8n
editor can require optional local owner setup; webhook import/publication and
application operation were automated and tested without editor setup. Only the
published webhook was executed; the editor's temporary test-listener URL is
documented but was not exercised.

This local aggregate sandbox has no authentication, real company integrations or
production assurance. The independent reference is generated explicitly and bound
to the full source checksum; Python is not invoked per browser request. The n8n
image logs an optional missing internal Python runner; all workflow Code nodes use
the working JavaScript runner. No external runner or additional service is needed
for the requested demo. Screenshots and execution receipts certify the observed
local build, not statistical significance, actual Samsara results or future runs.
