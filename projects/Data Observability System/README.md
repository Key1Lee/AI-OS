# Data Observability System

Understand and debug data systems from local metadata. This is an independently
installable Python package and reusable React UI, extracted on 2026-10-02.
It can run on its own; no Toptal modules or learner databases are required.

## Boundary

**Toptal Trainer → Observability contracts → Data Observability engine.**

Observability owns dbt ingestion, normalized nodes/edges/schema, immutable metadata
snapshots, graph traversal, incident evidence, impact and the generic map UI/API.
Toptal owns authored scenarios, rubrics, modes, disclosure, action telemetry,
drafts, assessment results and learner history. No reverse dependency exists.

The smallest boundary is an in-process package, without service-to-service calls.
Both local apps mount the same `/api/map` exploration router. The trainer injects
its own `MapContext` hooks for visibility, snapshot pinning and action recording.
Its investigation endpoints and notebook are separate consumer extensions.
The standalone app has no assessment or investigation endpoints.

## Run independently

Python 3.11+ and Node compatible with Vite 7 (this environment uses Python 3.13 and
Node 22+) are required. From this project directory:

```sh
make setup
make dev
```

Open `http://127.0.0.1:8002`. `make setup` installs the editable Python package,
dev/test dependencies and frontend dependencies, then builds the UI. DuckDB is
used only to regenerate and verify the trusted synthetic demo, never uploaded SQL.

Default metadata storage is `data/observability.db`; `OBSERVABILITY_DB` overrides
it. `OBSERVABILITY_WEB_DIST` overrides `web/dist`. Resolve relative overrides from
the launch directory; use absolute paths when integrating another application.
The config endpoint supplies a per-process mutation token. Standalone requests use
`X-Observability-Token`; the trainer supplies `X-Trainer-Token` to the same boundary.
Origins, local hosts, bounded artifact uploads and safe errors remain enforced.
No warehouse or AI credentials are needed.

## Consume the package

```sh
python -m pip install -e "../Data Observability System"
```

```python
from pathlib import Path
from data_system_map import create_service, GraphSnapshot
engine = create_service(Path("metadata.db"), seed_demo=True)
snapshot: GraphSnapshot = engine.snapshot("commerce-demo")
impact = engine.impact("commerce-demo", "model.commerce.fct_orders")
```

Consumers use the facade and serialized contracts, not adapter, SQLite or graph
internals. Stable schemas live in `data_system_map.contracts` and HTTP request
schemas in `data_system_map.api.contracts`; these contain no business policy.

The frontend exports typed `MapClient`, `DataMap`, graph/node views and DTOs from
`web/src/index.ts`. Supply a client and optional neutral extension slots. Toptal
resolves this source through Vite/TypeScript aliases and deduplicates React.
Run frontend dependency installation for both projects before building Toptal.
Generic UI, request code, widgets and foundational styles each have one owner.

## Checks

```sh
make test
make lint
make build
make check-demo
```

Tests use temporary metadata profiles. Toptal's `make test` runs its retained
trainer/integration suite plus this package's generic tests. Its existing browser
suite verifies assessment hiding, learning, SQL training and multi-tab recovery.
See [migration and recovery](docs/migration.md), [HTTP contracts](docs/api.md), and
[verification](docs/verification.md). `docs/initial-implementation/` is historical
baseline evidence, with paths and ownership as they existed before extraction.

## Current scope

The sample is original, synthetic and generated from trusted DuckDB transforms.
It records a healthy staging check, an anomaly at `int_order_items`, a uniqueness
failure at `fct_orders`, and dependent revenue/dashboard outputs. Diagnostics
label the earliest comparable anomaly as **INFERENCE**, never a proven root cause.
Impact is a declared dependency relation, not proof of incorrect output values.

Imported SQL is redacted and displayed as inert text. SQLGlot/SQLFluff analysis,
column-level lineage, natural-language queries, AI reasoning and runtime/provider
connections were not in the source implementation and remain future work.
Unavailable metadata and lineage stay explicitly unknown.
