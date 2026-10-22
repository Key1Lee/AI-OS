# Final results report — 2026-10-21

The final report is served at `http://127.0.0.1:8812/report`. Prominent buttons
in the guide and dashboard lead to it. The existing n8n publication step now
generates this report as its HTML artifact, alongside the unchanged department
CSV. `report_url` is included in the publication response.

The report reads committed Gold aggregates, with no external model or vendor
request. Findings are calculated from the department aggregates; metric values
are preserved. It includes explicit synthetic labels, independent question
counts, missing-answer coverage, calculation rules and batch provenance.

## Executed checks

From the PeopleOps project root:

```sh
policy_assistant/.venv/bin/python -m pytest survey_analytics/tests -q --junitxml=survey_analytics/reports/tests.xml
policy_assistant/.venv/bin/python -m survey_analytics.cohort_smoke
policy_assistant/.venv/bin/ruff check survey_analytics/final_report.py survey_analytics/api.py survey_analytics/visualization.py survey_analytics/tests/test_final_report.py
```

- **29 tests passed**, with one existing Starlette TestClient/httpx deprecation
  warning. New coverage checks empty state, Gold values and sample sizes,
  aggregate-only export, download behavior, navigation links, source preservation,
  escaped department labels and findings derived from changed aggregates.
- **7 live n8n checks passed**: collection/publication, 5,000 distinct IDs,
  ten department totals, independent arithmetic, idempotent replay, downloaded
  HTML/CSV and aggregate-only artifacts. Full evidence is in
  `reports/cohort-smoke.json`; downloaded report is `reports/samsara-5000.html`.
- Ruff passed for the changed application and test modules.
- Survey sidecar restarted, then `/health` returned HTTP 200 before live checks.
  n8n and the HR policy service were not restarted.

## Browser review

Clicked **View final report** from the actual guide and confirmed the report
rendered. Reviewed the cover, KPI cards, department chart, scorecard and mobile
methodology. Desktop breakpoint 1280×1000: document width 1265, ten scorecard
rows. Mobile breakpoint 390×844: document width 375 with no page overflow;
the wide scorecard scrolls inside its own container.

Screenshots: `reports/final-report-desktop.png`,
`reports/final-report-departments.png`, `reports/final-report-mobile.png`.
The mobile screenshot shows methodology and question coverage. A print stylesheet
and browser **Print / Save PDF** action are provided; no generated PDF or print
pagination verification is claimed. This update does not modify the previously
delivered BRD or requirements Word documents, which retain their own verification.

No production readiness, real Samsara results, statistical significance, historical
trend, causal explanation or measured ROI is inferred. The inherited local Docker
service remains available; no additional preview server was started.
