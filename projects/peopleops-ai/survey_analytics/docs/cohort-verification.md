# Synthetic 5,000-employee visualization — 2026-10-21

Delivered a second synthetic dataset and n8n workflow, with a responsive dashboard
and portable aggregate-only reports. No real employee data or external account
was used. The department mix and generated sentiment are illustrative, not claims
about Samsara. Original training exercises and HR application sources were not edited.

## Actual evidence

- Python tests: **25 passed**, including distinct employee grain, 5,000-person
  reconciliation, every department's independently recalculated experience/CSAT/
  eNPS, nullable denominators, fixture isolation, replay, empty dashboard,
  authenticated cohort export, stage ordering and generated artifacts. One
  existing Starlette TestClient/httpx deprecation warning remains.
- Real n8n workflow `samsaraSurvey5000` imported, published and executed via the
  dashboard run button, the real webhook smoke, and the n8n manual trigger.
- **7 cohort smoke checks passed**: actual collection/visualization; 5,000 distinct
  employee IDs; ten department counts; independent metric arithmetic; replay
  without row growth; HTML/CSV downloads; no employee/response IDs in artifacts.
  Full evidence: `reports/cohort-smoke.json`.
- Original small-fixture n8n regression: **7 live checks passed** after both
  datasets were present. Layer inspections in that check now scope counts by
  batch ID so a separate valid cohort does not invalidate the original test.
- Preserved HR app smoke command was rerun after n8n restart: **19 passed**.
  No enterprise 127-test evidence is claimed as a new run.
- Registry validation passed: **11 systems**. The PeopleOps owner now lists this
  component's entrypoints, contract sources and targeted tests.

## Persisted cohort

Batch SHA-256:
`071c8bf86bbf6798fa31c55031a3c5fcac7d8d48239efbde2dd63cf0d4ffe1b2`.
Survey `SV_SYNTHETIC_SAMSARA_5000`; metrics `survey-metrics-v2`.

| Cohort-scoped table | Rows |
|---|---:|
| bronze_batches | 1 |
| bronze_responses | 5,000 |
| silver_responses | 5,000 |
| quarantine | 0 |
| gold_snapshots | 1 |

All 5,000 invited fictional employees have complete synthetic responses, with
some unanswered questions. Mean engagement is 18,485 / 4,865 = 3.7995889;
experience score is 369,700 / 4,865 = **75.99/100**. CSAT is 3,310 / 4,828 =
**68.56%**. eNPS is 100 × (1,588 − 1,315) / 4,879 = **+5.60**. Every department
has more than five complete/per-question answers, so all ten slices can publish.

## Browser evidence

- The live dashboard initially showed an empty state, then its actual run button
  collected and displayed the committed cohort through n8n.
- All-department view: ten chart bars and ten detail rows; 5,000/5,000 respondents.
- Engineering filter: 1,200 responses; experience **79.3**, CSAT **76.7%**, eNPS
  **+22.9**, each matching that department's Gold values at one-decimal display
  precision. Filtering showed one chart bar and one table row.
- Switching to eNPS and all departments showed ten bars, including three negative
  values rendered to the left of zero. Restored the experience/all-department view.
- Desktop breakpoint 1440×1000: document width **1425**, ten bars/rows.
- Mobile breakpoint 390×844: document width **375**, no page overflow; table
  scrolls within its container. Temporary viewport override reset afterwards.
- Screenshots: `docs/cohort-dashboard-desktop.png` and
  `docs/cohort-dashboard-mobile.png`.
- New n8n canvas visibly contains Gold → Build department visualization → Return
  metrics, with all three production checklist configurations inherited from the
  synthetic demo. Time saved is still the earlier provisional 10-minute estimate,
  not a measured estimate for 5,000 records. No MCP client connection was made.
- The n8n manual trigger completed with item counts through the final response
  node. Screenshot: `docs/cohort-n8n-workflow.png`.

The existing Docker app was reused and remains running for inspection. No owned
temporary preview process was started; no shared runtime or real HR connection
was changed. HTML and CSV were actually downloaded through the app and copied to
`reports/samsara-5000.html` and `.csv`.

## Reproduce

From `/Users/key/_AI-OS/projects/peopleops-ai`:

```sh
policy_assistant/.venv/bin/python -m pytest survey_analytics/tests -q
policy_assistant/.venv/bin/python -m survey_analytics.cohort_smoke
policy_assistant/.venv/bin/python -m survey_analytics.smoke
```

This checks one fixed full-export snapshot. It does not establish real Qualtrics
compatibility, live Samsara staffing/results, a production privacy control,
sustained-load capacity, incremental ingestion, or real-world employee outcomes.
