# Independent Modeling Verification — 2026-10-02 (Asia/Seoul)

**STATUS: PASS**

All approved first-slice criteria have independent supporting evidence. The final
required checks pass, and no blocking correctness issue remains. This verdict
supersedes the interim FAIL report; the demonstrated defects and their independent
rechecks are retained below.

This report is owned by the exactly one Modeling Verification Agent. The verifier
inspected requirements, code, contracts, fixture rows, expected outputs, graph
relationships, and UI behavior; ran the required checks; and authored standalone
adversarial probes. It did not edit product code, tests, or contracts. The principal
agent implemented the repairs.

Contract sources: `/Users/key/_AI-OS/architecture/verification.md`, project
`AGENTS.md`, `docs/product-brief.md` section 63 and completion gates,
`docs/architecture.md`, API contracts, and the separately checked-in e-commerce
oracle. Approved scope is the first vertical slice, explicit data/evaluation
contracts, and alternative learner SQL. Dimensions/marts, customer LTV,
incremental/late-data/backfills/idempotency, SCD2/snapshots, dbt, and external
integrations are deferred and **have not been verified as delivered**. The small
prepared `completed_orders` view supports this slice; it does not establish a
completed intermediate-model curriculum.

## Requirements checked

The following maps all sixteen first-slice requirements to independent evidence.
The durable browser observations and screenshots are in
[`verification-evidence/2026-10-02/`](verification-evidence/2026-10-02/).

| # | Approved criterion | Independent evidence | Result |
| --- | --- | --- | --- |
| 1 | Load small e-commerce fixture | Inspected six source datasets, canonical types, rows and independent expected output. Initial browser/API counts: orders 5, customers 2, items 5, payments 5, products 5, returns 1. Packaged wheel also loads its own fixtures outside the repository. | PASS |
| 2 | Visualize source tables | Browser sees all six source cards, source previews, source inspector and graph. `initial-desktop.png`; `observations.json` → initial sources. | PASS |
| 3 | Show columns | Source cards report column counts 8/3/5/5/3/4; source and executed previews expose names, types and actual rows. Fact alternative exposes the actual added `customer_name` column. | PASS |
| 4 | Require learner to identify grain | All sources start `GRAIN UNKNOWN`; fact build is disabled. Declaring raw orders as order/orderId fails producer-grain and key checks. Declaring source_order_version/(orderId,sourceVersion) passes. Changed source drafts require rechecking before staging. | PASS |
| 5 | Visualize relationships | Every designed endpoint resolves. Items/payments/returns relationships originate at deduplicated stg_orders/order_id. Graph edges carry both source and target; native label clicks select the correct parent and executed step. | PASS |
| 6 | Allow a join | Independently operated LEFT/INNER, dataset/key/expectation controls, right aggregation and order_items→payments N:N interaction. NULLs remain unmatched; INNER explicitly shows removed left rows. | PASS |
| 7 | Compute resulting row count | Default direct join 4, aggregate-right 3; staging/customer LEFT 4, INNER 3; items/payments LEFT 8, aggregate-right 5. UI actual counts reconcile with separately calculated multiplicities and SQL output. | PASS |
| 8 | Detect cardinality | Observed 1:N, 1:1, N:1 and N:N. N:N O1 has two left × two right → four rows. Aggregating payments preserves five item rows and changes matched-key cardinality to N:1. Expected/actual mismatches fail visibly. | PASS |
| 9 | Demonstrate fanout | Completed-order amounts total USD 225.00; direct item join produces four rows and USD 325.00, with O1's USD 100.00 repeated twice. Temporary hidden-fanout variation still reports multiplication when total coincidentally equals USD 225.00. | PASS |
| 10 | Create staging model | Executed 5→4 deduplication, renames, decimal cents conversion, normalized statuses/currency and UTC timestamps. Cancelled O4 remains staged. Same-instant offset/version ambiguity and invalid source-version keys reject deterministically. | PASS |
| 11 | Create one fact model | Safe fct_orders has exactly the three completed orders and the required schema. Independent browser break produces four rows/USD 325.00/failure; repair restores three/USD 225.00/pass. CTE/customer-enriched equivalent SQL also passes. | PASS |
| 12 | Test primary key | Wrong/missing/duplicate/NULL keys fail. Explicit order grain and key contract are evaluated separately from uniqueness. UI key summary names the actual tested declaration, including ordered_at. | PASS |
| 13 | Define one metric | Revenue metadata exposes SUM(order_amount), completed orders, USD, ordered_at, dimensions, owner and gross-before-returns meaning. Browser calculation returns USD 225.00. AVG produces USD 75.00 and fails; SUM repair passes. | PASS |
| 14 | Evaluate output | Independent checked-in oracle, required schema, exact rows, key/null/status/currency/customer-reference checks. Same-total wrong rows fail the fact despite metric agreement; extra descriptive columns and equivalent SQL are allowed. | PASS |
| 15 | Explain result | Actual before/after rows, filters, renamed/removed/added columns, joins/windows, key evidence, group contributions and causal fanout explanations. Customer group total is shown once; item-only N:N traces show no money note. Prepared-view materialization and parent filter are inspectable. | PASS |
| 16 | Verify implementation | Final independent pytest, production build, all seven required browser journeys, two standalone browser probes, adversarial backend probes, screenshot inspection and outside-repository wheel execution pass. | PASS |

Additional approved contracts and completion gates:

| Criterion | Independent evidence | Result |
| --- | --- | --- |
| Reusable API/data/evaluation contracts | `/api/contracts` exports modeling-lab-v1 and ScenarioDefinition, ModelDefinition, EvaluationResult, BuildResult, JoinResult and MetricDefinition; OpenAPI, Pydantic contracts and checked-in docs/contracts.json inspected. Extra actual input definitions appear in BuildResult.inputs. | PASS |
| SQL equivalence, not SQL string grading | CTE/IN/order reversal, customer enrichment and full-row DISTINCT equivalent output accepted; incorrect aggregations and schema fail independently. | PASS |
| Decimal money and inspectable business meaning | DECIMAL(18,2), JSON decimal strings, USD and TIMESTAMPTZ enforced. Failed-payment attempts and return subtraction do not silently redefine this gross order metric. | PASS |
| Read-only, local, bounded learner SQL | Known-table/read-only AST validation, external access disabled, whitelisted functions, 10,000 characters/2,000 tokens/48 nesting/3,000 AST nodes/48 AST depth, 200 result-row bound, 64 MB/one thread and two-second cooperative execution interrupt. Exact malicious/error probes reject or fail structurally and recover. | PASS |
| Stable deterministic evidence | Five seeded permutations across all six source tables yield identical safe-build models, metrics and evidence. Execution/assertions certify correctness; explanation_source is deterministic_evidence. | PASS |
| Export/reset and valid UI state | Downloaded export includes versioned definitions, declarations, staging, build and metric. Reset cancellation preserves state; confirmation restores unknown sources and gates. Rechecked source declaration clears downstream executed evidence; SQL execution failure disables metric calculation; repaired SQL recovers. | PASS |
| Narrow viewport | Independently navigated all four views at 390 px; document width is exactly 390 px in each. Inspected screenshots for readable controls, tables, metric definition and layout. | PASS |
| Independent project and external-system/AI separation | Code/launcher/dependency inspection finds no sibling-project imports, scoring policy, incident management, AI SQL certification or cloud requirement. Standalone browser trace has no external requests/page errors. Fonts are bundled; launcher binds loopback. | PASS |

## Tests executed

Final checks were independently run against the final implementation, including the
last N:N aggregation/wording change:

| Command/check | Observed result |
| --- | --- |
| `uv run pytest` | Exit 0; **47 passed in 2.39 s**. Nonblocking upstream Starlette/httpx deprecation warning. |
| `npm --prefix apps/web run build` | Exit 0; TypeScript and Vite production build pass; 2,046 modules. Final assets index-DBQd8rq_.css and index-CUVt04JB.js. |
| `npm --prefix apps/web run test:e2e` | Exit 0; **7 passed in 8.2 s**. Full journey, source gate/redeclaration, join/NULL semantics, advanced parent arrows, metric mistakes, N:N plus repair, and 390 px flow. |
| Independent full browser probe | Exit 0; PASS, 5.7447 s; exact launcher on 127.0.0.1:8077. Grain gate, staging, joins, broken/repaired fact, equivalent SQL, actual arrow identity, metric, export, all narrow views, declared-key summary and reset. |
| Independent extra browser probe | Exit 0; PASS, 3.0154 s; N:N 8→5/N:1 repair, absent money note, source draft gate, prepared-view parent/materialization, SQL failure/recovery and dependent-evidence invalidation. Zero page errors or external requests. |
| Independent wheel execution | Imported engine and packaged fixture modules from dist/data_modeling_lab-0.1.0-py3-none-any.whl in a new temporary cwd outside the repository; module paths confirmed inside .whl. Safe evaluation pass, three fact rows, Revenue 225.00. |
| Standalone backend falsification | Direct engine, temporary fixture variations and FastAPI TestClient probes below; independent of product tests. No product fixtures/oracle/tests edited. |

Historical runs: pytest initially passed 38 tests, then 42 and 46 as repairs gained
regressions. An earlier browser suite had five passes and one advanced-arrow locator
failure; the final native-wrapper click and all seven journeys pass. Passing initial
tests did not prevent the independent defects below from being discovered.

## Blocking failures

**None remain in the approved first slice.** All demonstrated blockers were repaired
by the principal agent and independently rechecked with the original probes.

| Earlier demonstrated defect | Independent repair evidence |
| --- | --- |
| `SELECT ` + 2,500 opening parentheses + `1` + 2,500 closing parentheses; 120 nested derived SELECTs: recursion error/HTTP 500 | Exact queries now return structured HTTP 422 sql_complexity; subsequent valid build passes. Token/recursion guards have dedicated regressions. |
| `SELECT ` + `+`.join(['1'] * 900): 1,806-character left-associated AST planned for 11.186 s before observing interrupt | AST operator-depth guard now rejects HTTP 422 in approximately 0.078 s before DuckDB planning; dedicated regression. |
| Same-instant `2026-09-28T18:05:00+09:00` vs UTC timestamp at the same sourceVersion chose O1 USD 90.00 or 100.00 by insertion order | Normalized TIMESTAMPTZ equality rejects ambiguity in either row order. Duplicate and NULL source-version keys also reject. |
| Non-UTF8 extra `CAST('\xFF' AS BLOB)` passed engine but API returned HTTP 500; ARRAY_AGG of it failed too | Recursive binary hex representation serializes scalar and nested outputs; API returns 200 with correct passing fact. Dedicated regression. |
| NULL parent customer key suppressed three missing-customer references through NOT IN | NULL-safe NOT EXISTS now reports relationship failure, actual 3; nullable child keys remain permitted. Dedicated regression. |

The first report's open execution, serialization and reference findings are therefore
closed. Current regressions are in `tests/test_verifier_regressions.py`.

## Modeling errors

**No unresolved first-slice modeling error.** Independent falsification included:

- Wrong grain, unique-but-wrong declared key, duplicate/nonexistent/NULL keys and
  unknown customer references. A unique key alone does not prove intended grain.
- Incorrect fact containing three USD 75.00 rows: Revenue totals USD 225.00, but exact
  fact output fails. The UI explicitly states that metric agreement does not certify
  the underlying fact.
- Equal order amounts: temporarily changing O2 to USD 100.00, with independently
  updated expected output, gives safe revenue USD 275.00. Full-row DISTINCT passes;
  SUM(DISTINCT order_amount) gives USD 175.00 and is not a general fanout repair.
- Payment attempts include O3's failed USD 75.00 payment and produce USD 300.00;
  subtracting its USD 25.00 return produces USD 200.00. Both fail this gross completed
  order fact/metric definition. AVG=75.00 and COUNT=3.00 also fail Revenue.
- Wrong numeric/time types, required NULL fields, missing columns, negative amounts
  and wrong currency reject. Additional valid descriptive fields remain permitted.
- Temporary duplicate C1 and two NULL right keys produce six LEFT/five INNER rows,
  N:N cardinality, and correctly unmatched NULL left keys.
- Hidden fanout: removing O1 matches and adding two O2 matches gives four INNER rows
  and the coincidentally correct USD 225.00. Evidence still reports fanout, 1:N and
  one unmatched left row; contributions are O1=0, O2=150.00, O3=75.00.
- Five seeded fixture-row permutations produce identical build/evaluation/metric
  results. Ambiguous source ordering rejects rather than guessing a winner.
- Billion-step recursive aggregation interrupts in 2.040 s; twelve-way Cartesian
  query in 2.091 s, with failed SQL evidence and no certified output. Blank/unterminated
  SQL, unsafe UNION arm, file CTE, extension PRAGMA and unknown function return
  structured errors. A fifty-CTE aggregate chain executes in 0.084 s and fails its
  output contract normally. Case-insensitive identifiers and CTE shadowing are
  evaluated on actual resulting rows.

These are small local fixture observations, not a claim that observed cardinality
establishes a future production guarantee. The cooperative interrupt is an execution
bound supported by these probes, not an operating-system isolation guarantee.

## Architectural violations

None demonstrated. The engine independently executes and asserts output; AI does not
certify SQL. Project business logic/contracts/tests stay inside this project. No
Toptal scoring policy or Data Observability incident logic exists in the verified
slice. Local execution does not require a warehouse service, cloud account, secrets,
external font requests or persistent learner database.

## Missing tests

No identified blocking regression gap remains within the approved first slice.
Parser/AST depth, normalized version ambiguity, recursive binary encoding and
NULL-parent FK regressions were added by the principal agent. The required browser
suite includes native parent-arrow clicks and the N:N aggregation repair. Independent
standalone probes additionally preserve reset/export, stale-state invalidation,
prepared-input/materialization, grouped-money wording and all four narrow views.

Deferred incremental and SCD behavior has not been tested; it is outside this verdict.
This is functional/visual acceptance, not a formal accessibility audit or an empirical
novice-learning study.

## UX findings

No blocking UX issue remains. The following earlier findings were rechecked in the
finished browser, not merely accepted from implementation statements:

- Grouped customer key C1 has two left rows and USD 150.00 total/contribution; the two
  output chips carry no repeated USD 150.00 label. Item-only N:N traces show no money
  contribution or misleading amount footnote.
- Unaggregated naturally unique joins receive a correct causal explanation. INNER
  displays missing-key losses rather than implying preservation of every left row.
- Advanced multi-parent arrows identify both endpoints. Native label-wrapper clicks
  select stg_orders 4→fct_orders 3 or customers 2→fct_orders 3 as appropriate.
  Prepared stg_orders 4→completed_orders 3 filter and completed_orders 3→fact 3 are
  separately visible, with actual view materialization.
- Fact key summary shows the tested declared key ordered_at when selected; it does
  not mislabel that uniqueness as order_id.
- Source draft changes block staging until checked. Source redeclaration clears prior
  downstream fact/metric evidence. Execution failure leaves a failed fact and disabled
  metric; valid SQL repair recovers. Unknown grain remains visible when undeclared.
- Export includes the actual executed evidence and versioned contracts. Reset cancel
  preserves state; confirmed reset clears it. Navigation and all four 390 px views
  were operated and visually inspected without global horizontal overflow.

## Evidence

- [`check-results.json`](verification-evidence/2026-10-02/check-results.json): recorded
  final command results, production asset identities and outside-repository wheel
  module paths. This is an observation summary, not a raw console transcript.
- [`observations.json`](verification-evidence/2026-10-02/observations.json) and
  [`extra-observations.json`](verification-evidence/2026-10-02/extra-observations.json):
  standalone browser assertions and actual explanatory text; both end in PASS.
- [`browser-probes.mjs`](verification-evidence/2026-10-02/browser-probes.mjs) and
  [`advanced-probes.mjs`](verification-evidence/2026-10-02/advanced-probes.mjs):
  verifier-authored reproducible probes. Run with Node and explicit local launcher URL;
  they use the project's installed Playwright and save outputs under /tmp.
- [`export.json`](verification-evidence/2026-10-02/export.json): actual UI download with
  modeling-lab-v1 schemas, declarations, staging, passing fact and Revenue 225.00.
- Inspected current screenshots: initial-desktop, staging-desktop, join-customer-desktop,
  broken-fact-desktop, advanced-graph-desktop, metric-desktop, many-to-many-desktop,
  prepared-view-desktop, and mobile captures for all four views. Old failure captures
  were not presented as final screenshots.
- [`sha256.json`](verification-evidence/2026-10-02/sha256.json): hashes of the preserved
  evidence files.

Reproduction after dependencies and a production build:

```sh
uv run python scripts/run.py --port 8077
```

In a second terminal:

```sh
node docs/verification-evidence/2026-10-02/browser-probes.mjs http://127.0.0.1:8077
node docs/verification-evidence/2026-10-02/advanced-probes.mjs http://127.0.0.1:8077
```

## Recommended fixes

None required for approved first-slice acceptance. Keep this scope boundary explicit
when presenting the result. Later slices require their own implementations, adversarial
fixtures and independent acceptance evidence before being claimed delivered.
