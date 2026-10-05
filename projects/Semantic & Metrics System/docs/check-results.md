# Implementation check evidence — 2026-10-04

Run from this project root:

```sh
python3 -m semantic validate
python3 -m unittest discover -s tests -v
python3 -m semantic query net_revenue --consumer ai --start 2026-09-30 --end 2026-10-02 --dimensions date
python3 -m semantic scenario SEM-REVENUE-001
```

Observed registry result: PASS, 4 metric contracts, synthetic_scenario scope.

Observed test result: **36 tests passed**. Coverage includes known fixture calculations, cancellation/unfulfilled/currency population, local-midnight reporting, created versus fulfillment time, half-open windows, effective-time boundaries, explicit Customer identity, duplicate Order/refund/dimension rejection, dimension compatibility, refund as-of and currency, exact integer money including very large/negative amounts, all-five-consumer consistency, caller override rejection, lineage, ownership approval, immutable versions, breaking major revisions and consumer migration, lifecycle/deprecation, dependency/asset cycles, changed source bindings, evidence gates, scaffolded design, contradictory prose rejection, complete scenario verification, recall remaining unassessed, concurrent state preservation and subprocess CLI behavior.

The AI query returns Sep30 $3,800,000.00 and Oct1 $4,400,000.00 under America/Chicago fulfillment time, with exact cents and definition/catalog/source fingerprints.

The opening presents $8.7M and $8.2M plus authored technical status. It does not disclose formulas, a canonical answer or recognition time.

Tests create isolated temporary scenario state and do not complete the user's learner session. No sibling tests, live adapters, provider calls or production approval were executed. Independent helper evidence must be reported separately from these implementation checks.
