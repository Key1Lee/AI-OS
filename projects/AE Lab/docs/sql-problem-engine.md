# SQL Problem Engine — Step 2

This extends Step 1's curriculum, `ae-problem-v1`, `LearningEngine`, Store,
append-only mastery evidence and PostgreSQL executor. It adds 116 original
problems; the four executable Step 1 SQL/debug exercises remain, for 120 total.
The two modeling and one architecture representatives also remain available.

## Curriculum and bank

The SQL curriculum covers filtering/expressions, conditional logic, aggregation,
NULL meaning, joins/cardinality, measure grain, CTEs/subqueries, windows/ranking,
deduplication, date/time, strings, casting/precision, sets, nested data,
analytical patterns and execution reasoning. Existing stable concept IDs remain.
The bank exercises every SQL leaf except the explicitly deferred recursive CTE
capability. Parent concepts do not inherit mastery automatically.

| Difficulty | Executable SQL/debug problems |
| --- | ---: |
| L1 | 12 |
| L2 | 27 |
| L3 | 37 |
| L4 | 29 |
| L5 | 12 |
| L6 | 3 |

Fifteen business domains: E-commerce, Retail, Marketplace, Lending, Banking,
Payments, Fintech, SaaS, Subscriptions, Advertising, Logistics, Travel, Support
Operations, Healthcare Operations and Insurance. Multiple internal dataset IDs
retain Step 1's existing contexts; they do not inflate the count of domains.

`curriculum/sql-bank.json` uses the established problem contract. Its authoring
source is `scripts/build_sql_bank.py`; it is not a runtime generation service.
`lab/problems.py` remains the one learner catalog. `sql_lab/catalog.py` derives
private execution contracts from those definitions. Fixtures and independently
authored Python business calculations live in `bank_data.py` / `bank_oracles.py`.
Changing an authoring definition requires regeneration and validation.

## Reasoning and interaction

Normal practice presents one recommendation and one active exercise. An optional
collapsed chooser provides access to the rest. The saved observation precedes
requirements, input/output keys and a short plan. Intermediate and advanced
requirements ask relevant business/time/population/NULL questions, rather than
requiring a mechanical questionnaire for every query.

Every listed join requires left grain, right grain, relationship and expected
output grain. The relationship is checked independently from SQL output; causal
prose requires review. Window tasks require partition, order and visible rows.
Deduplication tasks ask for logical identity before SQL. These checks also apply
to newly started Step 1 SQL sessions. Earlier saved sessions retain their existing
reasoning contract and continue through the same engine.

DEBUG and REVIEW show an executable candidate and observed sample output, then
ask **What is wrong?** before repair. REVIEW covers correctness, grain, join
safety, readability, maintenance, edge cases, performance, business semantics
and tests. INTERVIEW withholds skill tags, hints and result comparisons until
completion. Hints, explicit solution exposure and conservative mastery evidence
retain Step 1's rules. Fanout is not named by a pre-submission skill tag.

Output-prediction exercises check a submitted JSON rowset on the displayed clean
sample before construction. Predictions are saved separately and do not grant
application/mastery evidence. The five-stage commerce chain starts at
`SQL-GRN-003`, then adds refunds, recognition timing, refund-period recognition
and warehouse scale. A completed stage offers an explicit changed-requirement
continuation; it does not start automatically.

## Evaluation and hidden fixtures

Every SQL definition executes against clean, adversarial, reversed/rescaled and
late-revision fixture cases. Reference rows come from independent Python
calculations, with separate hand-calculated financial, NULL, DST and leap-day
sentinels. Private fixture and oracle hashes pin sessions to their definitions;
unordered oracle rows serialize stably across processes.

Evaluation compares column contracts and row **multisets**, including duplicate
multiplicity. It checks required ordering only when the consumer requests it.
Numeric normalization does not collapse textual identifiers such as `00123`
and `123`. CTEs, subqueries and other equivalent PostgreSQL approaches are
accepted. Native Modeling validates actual output keys and join multiplicities;
native Quality validates source/output contracts and exposes nonblocking
unknown-money warnings; native Observability retains declared lineage/evidence.

The six rubric dimensions stay separate: sample result correctness, output
 grain, hidden-case robustness, business interpretation, clarity and performance.
The latter three are not certified by text matching. REVIEW/PERFORMANCE/design
submissions and L5/L6 SQL require a substantive saved assessment and tutor review
after objective success. The trusted CLI requires all authored criteria and a
reviewer/rationale tied to a real attempt. Objective correctness alone does not
receive full judgment credit.

The supported failure taxonomy is SYNTAX_ERROR, LOGIC_ERROR, GRAIN_ERROR,
JOIN_ERROR, NULL_ERROR, WINDOW_ERROR, DATE_ERROR, SEMANTIC_ERROR,
EDGE_CASE_FAILURE and PERFORMANCE_CONCERN. Observable execution/grain/fixture
failures get bounded automatic classifications. Tutors can add finer causal
classifications to the reviewed attempt; AST warnings remain potential risks.
Concept evidence records attempt classifications without overwriting history.

Examples explicitly distinguish no loan payments, an unknown recorded payment,
a known zero and signed adjustments. Lending defines latest transaction state,
reversals, charge-offs, schedules, explicit payment allocation, reported
 delinquencies and retrospective versus processing-cutoff balances. These are
stated exercise rules, with no implied production accounting policy.

## Adaptive evidence and system boundaries

The existing selector prioritizes due recall, recent failed concepts in a
different domain, simpler contexts after repeated misses, transfer opportunities
and unseen/under-covered appropriate-level concepts. Direct authored transfer
relationships are preferred when suitable; same-day or same-domain work cannot
establish transfer. The original understanding/debugging/multiple-task/spaced
recall requirements remain; a single query does not establish mastery.

`curriculum/coverage-matrix.json` is authored availability with zero learner
observations. Live coverage reads the existing profile's real evidence and
reports named mastery states and error counts, without invented percentages.

AE Lab owns instruction, original practice and local evidence. Toptal continues
to own stricter assessment/canonical examination mastery; existing exact-recall
contracts remain reused. Modeling owns grain/key/join engines; failed grain
practice can link to its existing Lab scenario. Quality owns technical checks;
AE supplies fixtures and teaches diagnosis. No sibling source, credentials or
learner database was modified. The existing Semantic synthetic contract does not
certify these new metrics.

## Dialects and performance

Only PostgreSQL 17 is executed. L4+ includes scale questions and a dialect
reference. PERFORMANCE mode exposes an actual bounded fixture `EXPLAIN` without
claiming a production benchmark. The 5B/150M/20B cardinalities are hypothetical;
physical partitioning and optimizer behavior need warehouse-specific evidence.

The portability reference links to official documentation:
[PostgreSQL windows](https://www.postgresql.org/docs/17/functions-window.html),
[JSON](https://www.postgresql.org/docs/17/functions-json.html),
[arrays](https://www.postgresql.org/docs/17/functions-array.html),
[CTE behavior](https://www.postgresql.org/docs/17/queries-with.html),
[Snowflake QUALIFY](https://docs.snowflake.com/en/sql-reference/constructs/qualify),
[BigQuery function safety](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/functions-reference),
[Databricks casts](https://docs.databricks.com/aws/en/sql/language-manual/functions/cast)
and [collection expansion](https://docs.databricks.com/gcp/en/sql/language-manual/functions/explode).
It distinguishes portable logical organization from physical execution.

## Reproduce validation

```sh
uv run python scripts/postgres_local.py start
uv run python scripts/build_sql_bank.py
uv run python scripts/curriculum_inventory.py
uv run python scripts/validate_sql_bank.py
uv run pytest -q
node --check lab/web_assets/learning.js
```

The bank validator checks schema/fixture loading, four oracle comparisons,
actual native constraints, an equivalent differently structured query for every
problem, authored broken-query detection, disclosure and private digests. It
writes `docs/sql-engine-validation.json` without reference SQL or hidden rows.
Validation profiles never write real learner attempts or mastery.

Deliberate limits: no cloud warehouse execution or automatic dialect translation,
recursive queries remain outside the bounded executor, performance judgments
are reviewed rather than benchmarked on billions of rows, prose is not
automatically certified, and this remains a trusted personal fixture sandbox.
Step 3 is not started.
