# Data Modeling & Transformation Lab

An independent, local visual learning system for one question: **why is this data model correct?**
Project identity: `data-modeling-lab`. The first release teaches a complete e-commerce
path from operational records to a tested completed-order fact and a Revenue metric.

## Run

Requires Python 3.11+, Node 22.12+ (or supported Node 20.19+), npm, and uv.

```sh
make setup
make run
```

Open [the local lab](http://127.0.0.1:8075). The UI and API share one local origin.
No cloud warehouse, dbt installation, LLM account, or sibling project is required.
The session is held in browser memory; export its evidence before reloading.

For frontend development use `make dev-api` and `make dev-web` in separate terminals;
Vite runs at `http://127.0.0.1:5175` and proxies `/api` to port 8075.
Use `uv run python scripts/run.py --port 8077` to choose another production port.

## The first experiment

1. Inspect six small source tables. Raw `orderId` is repeated: declare source order
   **version** grain and the `(orderId, sourceVersion)` key.
2. Create staging. Five versions become four current orders. Column names, status,
   integer cents, and timestamps are standardized; cancelled orders remain.
3. Join three prepared completed orders to their items. One order has two items:
   three rows become four and USD 225.00 becomes USD 325.00 when amounts are summed.
4. Aggregate items to the join key before joining and observe the repaired result.
   Switch the left input to items and the right input to payments to see an N:N
   join: two O1 items × two O1 payment attempts become four matching rows. Aggregate
   payment attempts first to preserve item grain with an N:1 join.
5. Build `fct_orders` at completed-order grain with `order_id` as key. Inspect schema,
   golden rows, uniqueness, nullability, relationships, and business-rule assertions.
6. Break the fact by joining items, inspect failures, then repair it.
7. Define Revenue with SUM and calculate USD 225.00. Try AVG to see why USD 75.00
   answers a different question. Export definitions and evidence as JSON.

Beginner mode emphasizes rows and diagrams. Advanced mode reveals executed SQL,
lets you use equivalent transformations, and connects each actual parent to its
transformation explanation. Every explanation comes from deterministic evidence.

**Revenue is gross completed-order revenue before returns, in USD.** A USD 25.00
return and a failed payment attempt make the scope visible. Net revenue, payment
cash, and customer lifetime value need separate business definitions.

## Checks

```sh
make check
make contracts
```

Pytest proves engine/API invariants, edge cases, alternate SQL, cardinality, NULLs,
money, resource guards, and independent-verifier regressions. Playwright uses the
production build on a separate loopback port (8076), checks the complete workflow,
broken/repaired results, arrow explanations, export/reset, and mobile layout.
Its screenshots are saved in `docs/screenshots/`.

The engine accepts one bounded, deterministic read-only query against known tables.
External file/network access and extension loading are disabled. SQL has size/token/
nesting/AST-depth limits; DuckDB uses one thread, a 64 MB memory limit, and a two-second
interrupt. Results exceeding 200 rows are rejected instead of silently truncated.
This local exercise server is not an Internet-facing multi-tenant SQL service.

## Contracts and boundaries

Use `/openapi.json`, `/docs`, and `/api/contracts`, or generate `docs/contracts.json`
with `make contracts`. Contract version is `modeling-lab-v1`; decimal money is encoded
as strings. Binary extras use tagged hex objects, recursively in arrays/structures.
`BuildResult.inputs` defines extra actual input models, including a prepared view if
learner SQL reads `completed_orders`. Inferred join grain is labeled as inference.
Undeclared source and unbuilt model grain remain unknown.

The engine can also be packaged with `uv build`. Its fixture and oracle ship in the
wheel, and it runs independently of this checkout. Fonts ship with the frontend;
the local application needs no Internet connection after setup.

The future trainer consumes exercise/evaluation contracts; scoring stays there.
Observability can consume designed-state definitions through a consumer-owned
adapter; runtime monitoring and incidents stay there. There are no sibling imports.

This is **the first vertical slice**, not the entire roadmap. Intermediate/dimensional/
mart exercises, customer LTV, incremental/late-data/backfill labs, SCD2/snapshots, dbt,
other domains, warehouse adapters, and external integrations are pending later slices.

See [the architecture](docs/architecture.md), [the original product brief](docs/product-brief.md),
and [independent verification](docs/verification-agent.md).
