# Semantic & Metrics System

This independent project makes business meaning explicit and reusable. Modeling defines structure; Quality validates data; Observability records system behavior; FDE discovers the customer problem. This project owns entity identity contracts, dimensions, measures, metric definitions, ownership, time semantics, versions, lineage and governed consumption.

Phase 1 is a Python 3.11+ standard-library CLI/library. No service, provider, warehouse, BI account or production credential is required. Every bundled transaction, approval and incident report is synthetic. The authored Finance contract here is distinct from the existing Modeling, AE and Northstar FDE definitions recorded in [discovery](docs/semantic-inventory.md).

```text
RAW -> MODELED -> EXPLICIT BUSINESS MEANING -> GOVERNED METRIC -> BI / API / AI
```

Start from this project directory:

```sh
python3 -m semantic scenario SEM-REVENUE-001
python3 -m semantic scenario SEM-REVENUE-001 predict --text 'What do the two reports measure, and what does healthy data actually establish?'
python3 -m semantic scenario SEM-REVENUE-001 inspect --artifact health
python3 -m semantic scenario SEM-REVENUE-001 inspect --artifact models
```

Request one artifact at a time. The lab requires relevant evidence before diagnosis, a learner proposal before implementation, and deterministic verification before recall. It records reasoning without automatically grading prose or granting mastery. Default progress stays in this project's `state/`; select a new `--state-dir` to start an independent session while preserving previous work.

For one concept at a time:

```sh
python3 -m semantic concept measure
python3 -m semantic concept measure --step fix
python3 -m semantic concept measure --step recall
```

The default concept view presents one concept, diagram, business example, failure and question. Fixes and recall checks require an explicit selected step. The scenario provides the complete investigate → diagnose → design → implement → verify → recall sequence; transfer is deferred.

Registry and integration commands are explicit engineering inspection, and may reveal definitions. Use them when you choose to inspect a known metric rather than during an unguided first attempt:

```sh
python3 -m semantic entities
python3 -m semantic dimensions
python3 -m semantic measures
python3 -m semantic metrics
python3 -m semantic show net_revenue
python3 -m semantic lineage net_revenue
python3 -m semantic explain net_revenue
python3 -m semantic compare gross_revenue net_revenue
python3 -m semantic query net_revenue --consumer ai --start 2026-09-30 --end 2026-10-02
python3 -m semantic export observability
make check
```

The canonical contract and query schemas live in `contracts/`; `Registry` performs the additional semantic and governance checks. Query windows are start-inclusive and end-exclusive reporting dates. Consumers send a metric ID/version and requested dimensions. They cannot submit a formula or SQL meaning override. Results carry owner, grain, time basis, timezone, as-of timestamp and definition/catalog/source fingerprints.

Three entities, four dimensions, three measures and four metrics are defined in `semantic/data/catalog.json`. Input is an already-modeled snapshot with one Order row, one refund aggregate per Order, and unique Customer/Product dimensions. Multi-product orders and item-level allocation are outside this bounded contract.

[Architecture](docs/architecture.md) explains boundaries and enforcement. [Integration contracts](docs/integrations.md) describe five explicit artifact interfaces. [Phase 1 report](docs/phase1-report.md) contains maintainer results and known gaps; it reveals the investigated incident outcome. [Checks](docs/check-results.md) record reproducible implementation evidence. Independent review is separate.
