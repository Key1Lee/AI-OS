# Hiring manager pack and Execute test — 2026-10-21

Delivered two editable three-page Word documents, a guided architecture diagram
as SVG and PNG, a traceability CSV, and an interactive local guide at `/guide`.
The dashboard links to that guide. The synthetic cohort and workflow settings
were preserved; no n8n re-import or provider change was required.

## Actual execution checks

- Clicked the actual n8n **Execute workflow from Run synthetic survey** button.
  The workflow changed to running, then returned to idle with item counts through
  all eight executed connections and the final response. An n8n item contains the
  source array; the one-item labels do not mean one employee.
- Ran `policy_assistant/.venv/bin/python -m survey_analytics.cohort_smoke`:
  **7 checks passed**, including 5,000 distinct employee IDs, ten reconciled
  department counts, independent per-department arithmetic, unchanged row counts
  on replay, actual HTML/CSV downloads and aggregate-only exports.
- Ran `policy_assistant/.venv/bin/python -m survey_analytics.checklist_smoke`:
  **passed**. Failed probe execution **130** delivered a local inbox event;
  `reports/checklist-smoke.json` records receipt at
  `2026-10-20T16:02:24.013564+00:00` (21 October in the client timezone).
  No external messages were sent.
- One earlier notification-check attempt overlapped the deliberate API container
  restart and received a transport disconnect. It was not treated as a valid
  application result; `/health` was checked before the successful rerun.
- The guide's own Execute button called the real n8n webhook and displayed
  `Completed: 5,000 synthetic responses; 10 departments; batch 071c8bf86bbf6798…`.

## Automated and browser checks

- `policy_assistant/.venv/bin/python -m pytest survey_analytics/tests -q --junitxml=survey_analytics/reports/tests.xml`:
  **27 passed**, with one existing Starlette TestClient/httpx deprecation warning.
  The two added tests verify guide content, both actual DOCX downloads, the
  traceability CSV and rejection of arbitrary download filenames.
- Ruff passed. No learner exercises, policy rules or HR model configuration were edited.
- Browser verified stage selection, Next and Previous, Gold input/output/check
  text, expanded FR06 acceptance/evidence, and the live Execute result.
- Desktop 1280×1100: document width **1265**, six stage controls and 12 requirement
  details. Mobile 390×844: document width **375**; no page overflow. The temporary
  viewport override was reset. Guide and n8n tabs remain available for the user.

## Document quality checks

Authored with the bundled Python runtime, python-docx and Pillow. The bundled
renderer used the bundled LibreOffice via
`/Users/key/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice`.
No user-installed desktop office suite was used.

- BRD: **3 pages**, rendered and every page visually inspected in `qa-brd-final`.
- Requirements: **3 pages**, rendered and every page visually inspected in
  `qa-requirements-release`.
- First renders revealed paragraph overflow and an inherited title border.
  Paragraph flow was tightened without reducing body type; inherited paragraph
  borders were removed. Final pages have no isolated overflow page, clipped
  tables or title rule.
- Letter portrait, Arial body type, black headings, explicit light-gray table
  borders, repeatable table headers and a readable numbered architecture figure.

## Review content and boundaries

The BRD has six business requirements, scope, review roles, observed outputs and
production gaps. The requirements document covers 12 functional requirements,
four operating requirements, acceptance conditions, metric/data contracts and
execution instructions. The CSV maps functional requirements to business
requirements and evidence sources. Browser-only checks are not represented as
unit-test proof. No manager signoff or individual mastery score is inferred.

All employee data and results are fictional. The pack is a description of the
working local baseline, not a production release, live vendor integration or
measured ROI claim. No authenticated MCP client handshake or enterprise suite
rerun is claimed by this change. The inherited Docker services remain running;
no separate temporary preview server was started.
