# How the demonstration works

1. Next.js checks input length, privacy boundaries and filter values, then forwards
   the natural-language question to the real n8n webhook. There is no word list
   in the interactive question path.
2. **Qwen Interpret Question** calls `/api/assistant/interpret`. The existing local
   Qwen returns schema-constrained intent, years, canonical departments and a
   retrieval query. The server validates the proposal and applies explicit filters.
   No model-selected URLs, SQL, tools, filesystem access or cloud fallback exist.
3. n8n fetches the full fictional Qualtrics snapshot and calls `/api/metrics`.
   TypeScript deduplicates, validates and calculates metrics, then compares every
   report field and source checksum against the independent Python reference.
   FAIL or NOT VERIFIED withholds numerical results.
4. **RAG Retrieval** searches four approved local Markdown documents using keyword
   overlap and topic boosts. Qwen rewrites the retrieval query; retrieval uses no
   embedding model or vector database. Sources explain methodology and limitations.
5. **Qwen Grounded Answer** calls `/api/assistant/answer`. The endpoint rechecks the
   approved report and local source text, builds exact fact/passage IDs, and asks
   Qwen to select relevant IDs. Unknown IDs, added prose, invalid JSON and truncated
   responses are refused. Only server-owned fact text and source excerpts appear
   in the answer. Qwen never writes numerical claims or performs arithmetic.
6. n8n attaches its real execution ID. React uses that same verified report for
   charts, tables and CSV, and displays the actual local model. Initial dashboard
   loading uses `/api/report` without claiming a Qwen or n8n execution.

## Reporting contract

- Metric: **Demo Company Engagement Score**, a fictional custom definition.
- QID1 recommendation; QID2 retention intention; QID3 meaningful work. Each is 1–5.
- Respondent score: `((QID1 + QID2 + QID3) / 3 - 1) * 25`.
- Company score: arithmetic mean of valid respondent scores, never an unweighted
  mean of department means. Pooled results weight responses equally across years.
- Deduplication: latest parsed UTC timestamp; later source position wins ties.
  Retain the latest revision even when invalid, then validate it.
- Validity: Finished is exactly 1; all three answers are integer 1–5; known year
  and department; timestamp matches SurveyYear and is within the reporting cutoff.
- Periods: 2024/2025 full calendar years; 2026 through 23:59:59.999 UTC on Oct 21.
- Response rate: valid deduplicated responses / eligible headcount * 100. The five
  department-year cohorts total 5,000 eligible opportunities annually; pooled eligibility means
  employee-year opportunities, not unique individuals across years.
- YoY: current score minus preceding calendar-year score in the same department
  scope, even when that earlier year is hidden by the display filter. 2024 is null.
- Trend: last selected year's score minus first selected year's score. A one-year
  selection has zero selected-period change. 2026 YTD warrants period caution.
- Quality counts for retrieved, deduplicated, duplicates removed and invalid
  excluded refer to the full source snapshot; used records refer to selected scope.
- SHA-256 input: recursively key-sorted compact JSON of `{responses, headcount}`,
  preserving response array order. Both raw data and eligibility affect the hash.
- PASS establishes agreement of these implementations against this synthetic
  snapshot. It is not evidence about real employees or correctness of a real survey.

## Failure behavior

Next.js → n8n has an 80-second timeout. Each Qwen call has 30 seconds; its n8n
HTTP node has 35 seconds. Other internal HTTP requests have 10 seconds; the
workflow has 90 seconds.
Unavailable n8n returns 503, malformed upstream responses 502, unsupported chat
questions 400, invalid/missing metric data 422 and reference mismatches 409.
No local chat fallback exists. Native HTTP error outputs converge on an error
Code node and Respond to Webhook. A numerical FAIL is preserved by the Metrics
Engine node and the answer builder refuses it. A failed interactive update leaves
the preceding verified report visible with an explicit unchanged-report message.

The golden report is versioned data, not regenerated during web startup. Explicit
seed/reference generation and rebuilding are required to change the source.
The default local n8n JavaScript runner may log that its optional Python runner
is absent. No workflow node uses Python; independent reference calculation runs
on the host before building the image.
