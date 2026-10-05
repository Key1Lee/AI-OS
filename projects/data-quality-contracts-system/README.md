# Data Quality & Contracts System

A standalone local visual lab for **whether the data still satisfies the assumptions
our business depends on**. Project: `data-quality-contracts-system`.

## Run

Requires Python 3.11+, uv, Node 22.12+ and npm.

```sh
make setup
npm --prefix web run build
make run
```

Open [the local lab](http://127.0.0.1:8082). No account, cloud warehouse, AI model,
dbt installation or sibling app is needed for the main lab. All assets/fonts are
local. Choose another port with `uv run python scripts/run.py --port 8084`.
For frontend development: run `uv run uvicorn quality_system.api:app --host 127.0.0.1 --port 8082`
and `npm --prefix web run dev` in separate terminals.

## Your first experiment

1. Inspect the contract: one current row per order; order_id is a non-null unique
   key; each customer has a parent; net USD revenue is captured payments less refunds.
2. Predict the key result. Run validation: **18 PASS**, gate open, publication eligible.
3. Duplicate order 1007. Old evidence clears. Run again: **11 rows / 10 IDs**;
   two affected rows and one extra duplicate. Grain and reconciliation fail;
   fixture revenue rises from **550.00 to 620.00 USD**. The mart is withheld.
4. Inspect the highlighted rows, the rule's purpose and FACT evidence. Fix the fixture
   and run again to verify. Repeat with an orphan, missing column, stale arrival and
   completed unpaid order.
5. Remove optional descriptions: **17 PASS / 1 WARN**, and publication remains
   eligible. Make a warning rule blocking in the builder to see the different gate.
6. Explore exact reconciliation, policy-based contract evolution, unit vs data tests
   and the seven progressively revealed teaching stages. Export current evidence.

The five quality levels are schema, row, key/relationship, dataset, and business.
UNKNOWN means no usable evidence; it never grants publication for a blocking rule.
Keys support declared grain; they do not prove semantic row meaning. There is no
universal quality score. The app reports individual checks and meaningful evidence.

Session changes/custom rules/learning stage are in browser memory. Reload resets
them. Every mutation clears old validation; export evidence before reloading.
The simulation starts at 2026-10-02 09:00 Asia/Seoul, regardless of today's date.
Freshness uses arrival time, not task completion. No real mart is published.

## Checks

```sh
make check
make contracts
make check-dbt
```

`make check` runs pytest, the production TypeScript/Vite build and Playwright
journeys against an isolated loopback server on port 8083. If required, install
Chromium with `npm --prefix web exec playwright install chromium`.
`make check-dbt` installs the optional dbt runtime and executes the positive lab
plus duplicate, unpaid, schema and broken-unit negative controls in temporary copies.
Logs and summaries are in `docs/test-results/`; screenshots in `docs/screenshots/`.

Exactly one independent Data Quality Verification Agent challenges the contracts,
engine, adapters, browser and boundaries. Its criterion evidence/report belongs in
`docs/verification-agent.md`. Completion requires its PASS.

## Architecture and responsibility map

```text
MODELING       declares the intended data
ORCHESTRATION  builds it and calls checks
QUALITY        validates assumptions and returns gate eligibility
OBSERVABILITY  investigates recorded failures and their impact
TOPTAL         controls assessment, disclosure and scoring
```

The core Python package has no sibling imports. FastAPI exposes stateless scenario,
contract, compatibility and validation endpoints. React shows the same deterministic
results. dbt is an optional export/recorded-result adapter with a real local lab;
Great Expectations is explicitly design-only. No LLM decides validation.

Read the [Phase 0 audit](docs/system-audit.md), [architecture](docs/architecture.md),
[acceptance](docs/acceptance.md), [interfaces](docs/integrations.md),
[provider caveats and references](docs/provider-adapters.md), and
[implementation handoff](docs/implementation-handoff.md).

The six source concepts match the sibling domain, but these versioned fixtures are
distinct. This contract's net USD meaning does not replace Modeling's gross Revenue
or Observability's fanout demo. Live sibling connections are future consumer changes.
This first slice has no SQL transformer, scheduler, lineage/incident engine, scoring,
ML anomaly service, streaming infrastructure, persistent learning store or AI chatbot.

## Standalone use

```python
from quality_system.engine import validate_bundle
from quality_system.scenarios import ScenarioRequest, scenario_input

inputs = scenario_input(ScenarioRequest(corruptions=["duplicate"], run_id="example-1"))
evidence = validate_bundle(inputs)
assert evidence.gate.publication == "WITHHELD"
```

External consumers can send their explicit DataContract/datasets/clock to
`POST /api/validate`. The local API is a bounded teaching runtime (200 rows/dataset),
not a hosted warehouse service. Generated schemas/examples live in `contracts/`.
