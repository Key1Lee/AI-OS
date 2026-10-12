# Ten business architecture exercises

Open the Desktop launcher, then **Exercise library**. Ten new cases sit beside
the original integrated retry-safety exercise. Each has a stable ID and distinct
synthetic inputs, faulty SQL, repaired SQL, independent expected rows, business
requirements, diagnosis, repair choice, recall question, and design tradeoffs.

| Case | Business problem | Architectural decision |
|---|---|---|
| BIZ-VENDOR-001 | A renamed vendor export doubles retail sales | Content identity, an accepted-content manifest, and stable sale grain |
| BIZ-API-001 | A premature checkpoint skips invoice pages | Durable extraction boundaries and deduplicated replay |
| BIZ-CDC-001 | A deleted SKU reappears in replenishment | Resolve source positions before applying delete semantics |
| BIZ-LATE-001 | Offline courier events disappear | Event-time corrections, bounded lookback, and explicit older backfill |
| BIZ-FANOUT-001 | Basket detail inflates order revenue | Change child grain before joining parent measures |
| BIZ-RESTATE-001 | Finance changes gross to net after API history expires | Retained source facts and a versioned historical restatement |
| BIZ-SCHEMA-001 | N/A becomes zero and Fahrenheit becomes Celsius | Typed normalization with visible, accounted-for quarantine |
| BIZ-PARTITION-001 | One daily report scans unrelated dates | Match storage/query scope to the consumer predicate |
| BIZ-ML-001 | Historical training includes future knowledge | Separate latest BI semantics from an as-of ML snapshot |
| BIZ-PUBLISH-001 | Executives see a half-written revenue release | A validated, atomically released snapshot pointer |

## Learning flow

Every case follows Orient → Predict → Run → Observe → Diagnose → Fix → Verify
→ Recall → Connect. Before repair, the diagram describes the existing faulty
path. Only after a supported diagnosis does it expose the proposed repair,
the **Why this architecture?** explanation, alternatives, and tradeoffs.
Question option positions are shuffled deterministically per case and stage.

Prediction feedback and execution evidence are withheld until Observe.
Incorrect predictions still proceed to the experiment; incorrect diagnosis
and recall choices remain at their current step. A wrong repair cannot execute
the correct transformation. Optional diagnostic prose is saved for reflection,
while native Toptal objective enforcement grades only the authored choice.

Evidence includes actual source/output rows, executed SQL, native key tests,
native quality bundles, quarantine records where applicable, and a repeated
transformation. All expected rows are independently authored in the catalog,
not derived by executing the repaired SQL. Quality can pass while full business
reconciliation fails: finance semantics, scan scope, and temporal ML leakage
demonstrate this distinction deliberately.

## Execution and architecture boundary

- `lab/business_catalog.py` owns the original cases and their answer/oracle contracts.
- `lab/business.py` owns the versioned session kind, fixture pinning, orchestration of calls, evidence exports, and local release gate.
- Native Modeling's public `connection`, `rows`, `columns`, and `key_tests` APIs execute the actual authored SQL. Its commerce-specific `BuildRequest` evaluation is not used to certify unrelated business grains. An empty commerce compatibility table supports the native connection's standard staging view without contributing business rows.
- Native Quality's typed `DataContract`, `Dataset`, and `validate_bundle` interfaces check generic schema, grain/key, and exact volume. The Lab composes these results with independent complete-row comparison; it does not create another quality engine.
- The existing Toptal bridge accepts a server-authored rubric and uses its native deterministic checks and authoritative enforcement. It writes no canonical learner records.
- A real local SQLite transaction saves a candidate snapshot and changes the release pointer only if every required check passes. The faulty candidate leaves the validated baseline pointer unchanged.
- Each run preserves its original fault, source fingerprint, definition fingerprint, canonical events, and three Mermaid views under its isolated run directory.

API, file, CDC, arrival, and commit conditions are **fixture facts**. The Lab
does not contact vendors, run Kafka/CDC infrastructure, measure warehouse scan
performance, deploy a scheduler, or send reverse ETL. It does not claim native
orchestrator or observability execution for these new cases. The original retry
exercise continues to use all five sibling integrations and its durable loader.

The partition case models seven assumed 100 MB partitions; its result is not
a benchmark or cloud bill. Whole-dollar money fixtures use exact integers.
The temperature fixture uses exactly representable 10°C/20°C examples. The ML
checksum is an illustrative comparison, not accuracy or a business KPI. The
publication case retains the previous complete release rather than pretending
the failed candidate writer recovered; freshness remains a separate concern.

Business cases persist their exact `learning_step`, so interrupted native
operations resume at the same required action. Repeating a transformation
demonstrates deterministic fixture replay, not end-to-end distributed retry
safety. A definition or fixture change blocks execution and asks for a fresh
case while retaining prior evidence. Verified guided cases end at **COMPLETED**,
which does not confer canonical mastery or independently assess prose/design skill.

Browser `POST /api/sessions` accepts `scenario_id`. `GET /api/catalog` returns
summaries without SQL or answer keys. CLI `scenarios`, `progress`, and `inspect`
support the expanded history; executable CLI lesson commands retain the original
retry contract and direct business-session continuation back to the browser.

## Design decision

Keep the original verified five-system coordinator intact. Use a separate,
versioned business coordinator over the same Store and existing native APIs,
rather than widening its hard-coded order/1,000-row/retry invariants into generic
claims. This costs another bounded coordinator, but avoids changing established
recovery semantics or duplicating sibling domain engines. These are deliberately
small experiments suitable for learning before adopting distributed systems.

## Sources

The user-provided [DataDriven pipeline-design lesson](https://datadriven.io/learn/pa_pattern_design_pipeline_intermediate)
informed the organization around ingestion, storage, transformation, consumers,
and reliability. The stories, datasets, choices, and SQL are original Lab work.
No vendor pricing, throughput, or exact interview question is reused.

Technical references linked inside relevant exercises:

- [Debezium PostgreSQL connector](https://debezium.io/documentation/reference/stable/connectors/postgresql.html): source changes and delete events.
- [BigQuery partition queries](https://docs.cloud.google.com/bigquery/docs/querying-partitioned-tables): eligible filters and partition pruning.
- [Feast feature retrieval](https://docs.feast.dev/v0.52-branch/getting-started/concepts/feature-retrieval): historical point-in-time feature use. The exercise additionally requires an explicit availability cutoff, whose distinction is documented in the project's [as-of-known-time issue](https://github.com/feast-dev/feast/issues/6615); no assumption is made that default retrieval enforces that cutoff.
- [PostgreSQL transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html): atomic visibility and all-or-nothing release behavior.

## Reproducible checks

`uv run pytest -q` runs the original checks plus all ten complete native HTTP
journeys, answer gates, disclosure, snapshot release protection, repeated output,
source pinning, preserved old evidence, and CLI compatibility. JavaScript syntax:
`node --check lab/web_assets/app.js` and `node --check lab/web_assets/business-app.js`.
Browser smoke checks and final command results are recorded separately in
`business-exercises-verification.md`; existing Phase 1 verification remains separate.
