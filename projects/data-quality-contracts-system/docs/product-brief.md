You are **GPT-6.1 Sol Ultra** acting as the Principal Analytics Engineering Architect, Data Quality Architect, Data Contracts Architect, Data Platform Architect, and Senior Analytics Engineering Educator.

The user is a beginner learning Analytics Engineering who learns especially well through:

- diagrams
- visual flows
- cause → effect
- interactive examples
- intentionally broken systems
- small concrete datasets
- repeated visual patterns

You are building the next standalone project inside the user's AI OS:

# DATA QUALITY & CONTRACTS SYSTEM

Preferred project name:

`data-quality-contracts-system`

Existing sibling projects:

```text
data-modeling-system
data-orchestration-system
data-observability-system
toptal-system
```

Do NOT merge this project into those systems.

Toptal will eventually consume this system.

---

# PHASE 0 — AUDIT BEFORE BUILDING

Before implementing anything, inspect the existing:

- Data Modeling System
- Data Orchestration System
- Data Observability System
- Toptal System

Determine:

1. what Data Quality functionality already exists
2. what testing functionality already exists
3. what contracts already exist
4. what schemas/contracts are shared
5. where responsibilities overlap
6. what should remain where it currently lives
7. what should be moved or exposed through an interface
8. what must NOT be duplicated

Produce a short:

# CURRENT RESPONSIBILITY MAP

Example:

```text
MODELING
defines expected grain

QUALITY
verifies grain

ORCHESTRATION
executes validation

OBSERVABILITY
monitors validation results

TOPTAL
tests whether learner understands failure
```

Only after this audit should implementation begin.

---

# THE FIVE-SYSTEM MENTAL MODEL

Preserve these boundaries.

## DATA MODELING SYSTEM

Answers:

> What should the data look like?

Owns:

- grain definitions
- keys
- joins
- facts
- dimensions
- transformations
- marts
- model design
- metric inputs

---

## DATA ORCHESTRATION SYSTEM

Answers:

> When and how does work execute?

Owns:

- workflows
- scheduling
- dependencies
- retries
- backfills
- execution state
- task ordering

---

## DATA QUALITY & CONTRACTS SYSTEM

Answers:

> Is the data valid and safe to use?

Owns:

- expectations
- validation rules
- schema contracts
- key constraints
- freshness expectations
- volume expectations
- referential integrity
- business rules
- contract compatibility
- validation results
- quality gates
- severity
- acceptance/rejection policies

---

## DATA OBSERVABILITY SYSTEM

Answers:

> What happened, where did it happen, and what is affected?

Owns:

- monitoring
- trends
- anomalies
- lineage-based debugging
- incident evidence
- blast radius
- health
- root-cause investigation

---

## TOPTAL SYSTEM

Answers:

> Can the learner correctly diagnose and solve the problem?

Owns:

- assessment
- scoring
- exercises
- interviews
- learner telemetry

---

# MOST IMPORTANT DISTINCTION

Do NOT confuse:

```text
QUALITY
```

with:

```text
OBSERVABILITY
```

Example:

Quality rule:

```text
order_id MUST be unique
```

Quality System runs:

```text
unique(order_id)

FAIL

29,403 duplicates
```

Observability receives:

```text
fct_orders quality failure
      ↓
when did it begin?
      ↓
what changed upstream?
      ↓
which dashboards are affected?
```

QUALITY establishes:

> The rule failed.

OBSERVABILITY investigates:

> Why did it fail and what does it affect?

Preserve this boundary.

---

# PRODUCT MISSION

Teach the learner:

> Good data engineering is not merely producing a table.

A trustworthy analytical model has explicit assumptions.

Those assumptions must be:

```text
DEFINED
      ↓
TESTED
      ↓
ENFORCED
      ↓
OBSERVED
```

The learner should become naturally suspicious of undocumented assumptions.

---

# CORE VISUAL

The application's most important visualization should show data passing through quality gates.

Example:

```text
SOURCE
orders

   ↓

┌─────────────────┐
│ SCHEMA CHECK    │
│       ✓         │
└─────────────────┘

   ↓

STAGING

   ↓

┌─────────────────┐
│ GRAIN CHECK     │
│ order_id unique │
│       ✓         │
└─────────────────┘

   ↓

FACT TABLE

   ↓

┌─────────────────┐
│ BUSINESS RULE   │
│ revenue >= 0    │
│       ✕         │
└─────────────────┘

   ↓

MART
BLOCKED
```

A beginner should immediately understand:

> The table exists, but it should not be trusted yet.

---

# TEACH FIVE LEVELS OF DATA QUALITY

Organize quality visually into five levels.

## LEVEL 1 — SCHEMA

Questions:

- does the column exist?
- is the type correct?
- was a required column removed?
- is nullable behavior correct?

Example:

```text
order_id
EXPECTED: STRING NOT NULL

ACTUAL:
STRING NULLABLE

✕ CONTRACT FAILURE
```

---

# LEVEL 2 — ROW

Questions:

- is this value null?
- does it fall in the allowed range?
- is its format correct?
- are values valid?

Examples:

```text
email IS NOT NULL

quantity > 0

status IN (
 pending,
 paid,
 cancelled
)
```

---

# LEVEL 3 — KEY / RELATIONSHIP

Questions:

- is the key unique?
- does every foreign key have a parent?
- is the relationship behaving as expected?

Example:

```text
fct_orders.customer_id
       ↓
dim_customers.customer_id

99.98% matched

23 unmatched customers

✕
```

---

# LEVEL 4 — DATASET

Questions:

- did row count suddenly change?
- did data arrive?
- is it fresh enough?
- is the dataset unexpectedly empty?
- does distribution look reasonable?

Example:

```text
EXPECTED ROWS
8M – 12M

ACTUAL
1.3M

✕
```

---

# LEVEL 5 — BUSINESS

Questions:

- can shipped date occur before ordered date?
- can revenue be negative?
- should completed orders have payments?
- do Finance totals reconcile?

Example:

```text
COMPLETED ORDER

payment_status = unpaid

✕

BUSINESS INVARIANT VIOLATED
```

Teach that these are often more important than simple null checks.

---

# DATA CONTRACT

Create a first-class:

# DATA CONTRACT

Example:

```text
fct_orders CONTRACT

GRAIN
1 row / order

PRIMARY KEY
order_id

REQUIRED COLUMNS
order_id
customer_id
ordered_at
net_revenue

SCHEMA
order_id       STRING NOT NULL
customer_id    STRING
ordered_at     TIMESTAMP NOT NULL
net_revenue    DECIMAL NOT NULL

RELATIONSHIPS
customer_id
→ dim_customers.customer_id

BUSINESS RULES
net_revenue >= 0

FRESHNESS
< 2 hours

OWNER
Commerce Analytics
```

This should be visually understandable.

---

# CONTRACT VS TEST

Teach this distinction clearly.

Contract:

> What must remain true.

Test:

> How we verify it.

Example:

```text
CONTRACT

order_id must uniquely identify an order

        ↓

TEST

COUNT(*)
vs
COUNT(DISTINCT order_id)
```

---

# QUALITY RULE CONTRACT

Create a provider-neutral representation.

Example:

```text
QualityRule {
    id
    name
    description

    target
    target_type

    dimension

    expectation

    severity

    blocking

    owner

    evidence_source
}
```

Dimensions may include:

```text
schema
completeness
uniqueness
validity
consistency
referential_integrity
freshness
volume
business_rule
```

---

# VALIDATION RESULT CONTRACT

Example:

```text
ValidationResult {
    rule_id
    target_id

    status

    expected
    actual

    failed_rows

    total_rows

    failure_rate

    severity

    executed_at

    evidence
}
```

Keep deterministic evidence separate from AI interpretation.

---

# THREE RESULT STATES

Beginner mode should primarily use:

```text
PASS
WARN
FAIL
```

Also support:

```text
UNKNOWN
```

when evidence does not exist.

Never turn UNKNOWN into PASS.

---

# QUALITY GATES

Teach:

> Some failures should prevent downstream publication.

Example:

```text
fct_orders

unique(order_id)
FAIL

        ↓

QUALITY GATE

        ✕

        ↓

mart_revenue
NOT PUBLISHED
```

But another check may only warn:

```text
description NULL RATE
expected < 10%
actual 11%

WARN

pipeline continues
```

Teach the difference between:

```text
BLOCKING
```

and:

```text
NON-BLOCKING
```

quality rules.

---

# SEVERITY

Keep severity simple:

```text
INFO
WARNING
CRITICAL
```

Example:

Missing optional description:

WARNING

Duplicate order_id:

CRITICAL

Avoid arbitrary complexity.

---

# CONTRACT BREAKING CHANGES

Create a visual compatibility lab.

Example:

Version 1:

```text
customer_id STRING
```

Version 2:

```text
customer_id INTEGER
```

Show:

```text
SCHEMA CONTRACT

BREAKING CHANGE
```

Teach:

### Usually potentially breaking

- column removed
- column renamed
- incompatible type change
- nullable → required without compatible data
- grain change
- key change
- semantic meaning change

### Often additive

- new optional column

Do not oversimplify compatibility.

Allow configurable contract policies.

---

# GRAIN VALIDATION

Connect directly to Data Modeling.

Modeling declares:

```text
fct_orders
grain = order

primary key = order_id
```

Quality verifies:

```text
COUNT(*)
=
COUNT(DISTINCT order_id)
```

If false:

```text
DECLARED GRAIN
1 row / order

OBSERVED GRAIN
not unique by order_id

✕
```

This should be one of the strongest visual integrations between projects.

---

# REFERENTIAL INTEGRITY

Visualize:

```text
ORDERS
customer_id
     │
     │ must exist
     ▼
CUSTOMERS
customer_id
```

Broken:

```text
C10933
     ↓
NO CUSTOMER

✕ ORPHAN KEY
```

Teach:

- orphan records
- optional relationships
- unknown members
- late dimensions

---

# UNIQUENESS

Show actual duplicate examples.

Example:

```text
order_id

1001
1002
1002  ← DUPLICATE
1003
```

Then:

```text
unique(order_id)

FAIL
```

Avoid explaining quality only through abstract YAML.

---

# COMPLETENESS

Visualize:

```text
email

a@x.com
NULL      ←
b@x.com
NULL      ←
```

Then:

```text
NOT NULL RATE

EXPECTED
>= 99%

ACTUAL
96.2%

FAIL
```

Teach thresholds instead of assuming every null is invalid.

---

# VALIDITY

Examples:

```text
country_code

US ✓
KR ✓
UK ✓
ZZ ✕
```

or:

```text
quantity

3 ✓
1 ✓
-8 ✕
```

---

# CONSISTENCY

Teach cross-field relationships.

Example:

```text
status = shipped

shipped_at = NULL

✕
```

Another:

```text
cancelled_at
<
ordered_at

✕
```

---

# RECONCILIATION

This is extremely important for Senior Analytics Engineering.

Example:

```text
SOURCE PAYMENTS

$10,234,219

        ↓

WAREHOUSE REVENUE

$10,233,901

DIFFERENCE
$318
```

Teach:

```text
absolute difference
relative difference
tolerance
```

Support checks such as:

```text
source_total
≈
warehouse_total
```

within a configurable tolerance.

---

# FRESHNESS

Visualize:

```text
EXPECTED UPDATE

07:00

LAST DATA

04:12

AGE

2h 48m

FAIL
```

Quality defines the expectation.

Orchestration provides execution context.

Observability monitors the incident.

---

# VOLUME

Teach basic deterministic volume checks first.

Example:

```text
7 DAY RANGE

8.1M
8.3M
8.2M
8.5M
8.4M
8.3M

TODAY

1.1M

⚠
```

Avoid pretending statistical anomaly detection is deterministic truth.

If anomaly models are added later, label them appropriately.

---

# UNIT TESTS VS DATA TESTS

Teach these separately.

## UNIT TEST

Question:

> Does transformation logic produce the expected result for controlled inputs?

Example:

INPUT

```text
status      amount
complete    100
cancelled   200
```

Expected transformation result:

```text
revenue = 100
```

---

## DATA TEST

Question:

> Does the produced dataset satisfy an assertion?

Example:

```text
unique(order_id)
```

Both are important.

Do not combine them conceptually.

---

# DBT INTEGRATION

Use current dbt functionality where applicable.

Support:

- data tests
- unit tests
- model contracts
- source tests
- relationships
- accepted values
- uniqueness
- not null
- custom generic tests
- singular tests

Do not make the core Quality domain dependent on dbt.

dbt should be an adapter.

---

# GREAT EXPECTATIONS ADAPTER

Design an optional adapter for Great Expectations.

Map generic:

```text
QualityRule
```

to:

```text
Expectation
```

where appropriate.

Do not make GX mandatory for MVP.

The system should function using its own deterministic quality engine and dbt integration first.

---

# QUALITY RULE BUILDER

Create a visual interface.

Example:

```text
TABLE
fct_orders

COLUMN
order_id

EXPECTATION
must be unique

SEVERITY
critical

BLOCK DOWNSTREAM?
yes
```

Then visually compile this into a QualityRule.

This teaches the concept before exposing configuration syntax.

---

# "WHY DOES THIS TEST EXIST?"

Every rule should answer this.

Example:

```text
TEST

unique(order_id)

WHY?

fct_orders promises one row per order.

If order_id duplicates,
revenue and order counts may be inflated.
```

This is critical for beginner learning.

Tests without purpose become memorization.

---

# BREAK IT MODE

This is mandatory.

Allow controlled corruption.

Examples:

## Duplicate rows

```text
Add duplicate order 1007
```

Observe:

```text
uniqueness
PASS → FAIL
```

---

## Missing foreign key

```text
customer_id = C999

customer doesn't exist
```

Observe:

```text
relationship
PASS → FAIL
```

---

## Remove column

```text
drop ordered_at
```

Observe:

```text
schema contract
PASS → FAIL
```

---

## Stale data

Advance simulated time without new data.

Observe:

```text
freshness
PASS → FAIL
```

---

## Business rule

Set:

```text
shipped_at < ordered_at
```

Observe:

```text
business invariant
PASS → FAIL
```

The learner should visually experience cause and effect.

---

# QUALITY SCORE

Do NOT create a meaningless universal 0–100 score.

Prefer displaying:

```text
12 checks

10 PASS
1 WARN
1 FAIL
```

plus the specific critical failure.

If scoring is required later, it must have a transparent deterministic rubric.

---

# QUALITY PROFILE VIEW

For a model:

```text
fct_orders

SCHEMA
✓

GRAIN
✕

COMPLETENESS
✓

RELATIONSHIPS
✓

FRESHNESS
✓

BUSINESS RULES
⚠
```

This should be visually compact and immediately understandable.

---

# QUALITY FLOW VIEW

Allow:

```text
raw_orders
   ✓
    ↓
stg_orders
   ✓
    ↓
int_orders
   ✓
    ↓
fct_orders
   ✕
    ↓
mart_revenue
 BLOCKED
```

The Quality System should identify the failing validation.

Observability should handle wider incident investigation.

---

# DESIGNED VS OBSERVED

Use the clean integration pattern:

```text
DATA MODELING

DESIGNED STATE

fct_orders
1 row / order

          ↓

DATA QUALITY

VALIDATION

Is order_id actually unique?

          ↓

DATA OBSERVABILITY

OBSERVED SYSTEM HEALTH

When did duplicates begin?
What downstream systems are affected?
```

This relationship should be central to the architecture.

---

# ORCHESTRATION INTEGRATION

Quality checks may execute as workflow steps.

Example:

```text
build_fct_orders
       ↓
quality_gate
       ↓
publish_mart
```

Orchestration owns:

```text
execution
```

Quality owns:

```text
validation
```

Do not confuse them.

---

# OBSERVABILITY EVENT

Emit structured results such as:

```text
QualityEvent {
    dataset_id
    rule_id

    status
    severity

    expected
    actual

    failure_count

    timestamp
}
```

Data Observability can ingest these events.

---

# TOPTAL INTEGRATION

Create deterministic scenario interfaces.

Example assessment:

> Finance reports that revenue is inflated.

Candidate may request:

```text
run uniqueness check
```

Quality System returns:

```text
unique(order_id)

FAIL

duplicates:
29,403
```

Toptal decides:

- whether the user may see that result
- scoring
- hints
- evaluation

Quality System must NOT contain Toptal scoring logic.

---

# VISUAL LEARNING LEVELS

## LEVEL 1

NULL
UNIQUE
VALID VALUES

## LEVEL 2

RELATIONSHIPS
GRAIN
SCHEMA

## LEVEL 3

BUSINESS RULES
RECONCILIATION

## LEVEL 4

FRESHNESS
VOLUME
QUALITY GATES

## LEVEL 5

CONTRACTS
SCHEMA EVOLUTION

## LEVEL 6

CROSS-SYSTEM QUALITY

## LEVEL 7

SENIOR INCIDENT SCENARIOS

Unlock concepts progressively.

---

# FIRST SCENARIO

Use the same e-commerce domain already shared across systems.

```text
customers
orders
order_items
payments
products
returns
```

Create:

```text
fct_orders
```

Contract:

```text
grain:
1 row / order

primary key:
order_id

required:
order_id
ordered_at
net_revenue

relationships:
customer_id → customers

rules:
net_revenue >= 0
```

Start fully valid.

---

# FIRST FAILURE

Introduce duplicate orders.

Show:

```text
EXPECTED

10 orders
10 distinct order_ids

ACTUAL

11 rows
10 distinct order_ids
```

Then:

```text
GRAIN CONTRACT

FAILED
```

Explain visually:

```text
duplicate
      ↓
order grain broken
      ↓
SUM(revenue) may inflate
```

---

# SECOND FAILURE

Introduce orphan `customer_id`.

Teach referential integrity.

---

# THIRD FAILURE

Remove required schema column.

Teach data contracts.

---

# FOURTH FAILURE

Make data stale.

Teach freshness.

---

# FIFTH FAILURE

Make completed order unpaid.

Teach business-quality rules.

---

# FIRST VERTICAL SLICE

Do NOT build the whole platform immediately.

Build exactly:

1. load deterministic e-commerce fixtures
2. define DataContract
3. define QualityRule
4. define ValidationResult
5. display contract visually
6. implement unique validation
7. implement not-null validation
8. implement relationship validation
9. implement accepted-values validation
10. implement one business rule
11. run validations
12. show PASS/WARN/FAIL
13. create one blocking quality gate
14. deliberately break fixture
15. show failure visually
16. emit QualityEvent
17. expose contract for Modeling integration
18. expose QualityEvent for Observability
19. expose validation endpoint for Toptal
20. test everything

Do this exceptionally well before expanding.

---

# DETERMINISTIC FIRST

AI must NOT decide whether:

- key is unique
- value is null
- schema matches
- relationship exists
- threshold passed
- reconciliation passed
- freshness threshold passed
- contract is structurally compatible

Use deterministic software.

AI may:

- explain
- teach
- summarize
- generate examples
- describe likely consequences
- suggest appropriate tests

AI explanations must distinguish:

FACT

from:

HYPOTHESIS

---

# VISUAL LEARNING LOOP

Optimize for:

```text
SEE EXPECTATION
       ↓
PREDICT RESULT
       ↓
RUN TEST
       ↓
SEE EVIDENCE
       ↓
BREAK DATA
       ↓
SEE FAILURE
       ↓
UNDERSTAND CONSEQUENCE
       ↓
FIX
       ↓
VERIFY
```

This is the primary learning experience.

---

# EXACTLY ONE HELPER AGENT

Create exactly one helper agent:

# DATA QUALITY VERIFICATION AGENT

The main agent owns architecture and implementation.

The helper only audits and attempts to falsify it.

Verify:

- uniqueness
- null rules
- accepted values
- relationships
- schema contracts
- grain validation
- freshness
- reconciliation
- business rules
- severity
- blocking behavior
- contract compatibility
- deterministic results
- integration boundaries
- no Observability duplication
- no Modeling duplication
- no Orchestration duplication
- no Toptal scoring leakage

The verification agent must intentionally test edge cases.

---

# VERIFICATION AGENT OUTPUT

Return:

STATUS:
PASS | FAIL

TESTS EXECUTED

CONTRACT FAILURES

QUALITY ENGINE ERRORS

BOUNDARY VIOLATIONS

MISSING TESTS

UX ISSUES

EVIDENCE

RECOMMENDED FIXES

PASS only if no blocking correctness issues remain.

If FAIL:

1. reproduce
2. fix
3. add regression test
4. rerun tests
5. rerun verification

---

# ARCHITECTURAL TEST

At completion, the system family should make this sequence obvious:

```text
DATA MODELING
"We expect one row per order."

        ↓

DATA ORCHESTRATION
"Build fct_orders."

        ↓

DATA QUALITY
"Verify one row per order."

        ↓

FAIL
duplicate order_id

        ↓

DATA OBSERVABILITY
"When did this begin?
Where upstream?
What is impacted?"

        ↓

TOPTAL
"Can the learner diagnose it?"
```

If responsibilities are not this clear, refactor them.

---

# DO NOT BUILD YET

Do not build:

- sophisticated ML anomaly detection
- giant enterprise rule catalogs
- real-time streaming quality
- Kafka infrastructure
- another lineage engine
- another orchestration engine
- another observability dashboard
- generic AI chatbot
- meaningless data-quality score

Build the fundamentals first.

---

# COMPLETION TEST

A beginner should be able to explain:

- what data quality means
- what a data contract is
- why grain must be tested
- what uniqueness means
- what completeness means
- what validity means
- what referential integrity means
- what reconciliation means
- what freshness means
- what a quality gate is
- why some failures block publication
- difference between unit tests and data tests
- difference between quality and observability
- how quality integrates with orchestration
- how quality integrates with modeling

If the system cannot teach these visually, simplify it.

---

# AFTER IMPLEMENTATION

Provide:

## SYSTEM AUDIT

What overlapping functionality existed in sibling systems.

## FINAL RESPONSIBILITY MAP

Who owns what.

## ARCHITECTURE

Show the new system.

## FIRST SCENARIO

Show the complete e-commerce learning flow.

## TEST RESULTS

Show deterministic results.

## VERIFICATION

PASS / FAIL.

## NEXT INTEGRATION

Explain how Modeling, Orchestration, Quality, Observability, and Toptal now interact.

---

# FINAL PRINCIPLE

A Senior Analytics Engineer should never merely ask:

> "Did the pipeline finish?"

They should ask:

> "Did it produce data that still satisfies the assumptions our business depends on?"

Build the entire Data Quality & Contracts System around teaching that instinct.

Inspect the existing AI OS projects first.

Audit boundaries.

Then build the smallest excellent vertical slice.

Do not duplicate existing systems.

Test deterministically.

Use exactly one independent Verification Agent.

Do not declare completion until verification passes.