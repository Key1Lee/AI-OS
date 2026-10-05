from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal
from math import isfinite
from threading import Timer
from typing import Any

import duckdb
from sqlglot import exp

from .contracts import (
    BuildRequest, BuildResult, ColumnDefinition, ContractDefinition, EvaluationResult,
    GrainDefinition, GrainRequest, GrainResult, JoinRequest, JoinResult, JoinTrace,
    MetricDefinition, MetricRequest, ModelDefinition, RelationshipDefinition,
    ScenarioDefinition, StagingRequest, StagingResult, TestResult, TransformationStep,
)
from .fixtures import expected_data, fixture_data, load_fixtures
from .sql import LabError, inspect_query

STAGING_SQL = """WITH normalized AS (
    SELECT
        orderId AS order_id,
        customerId AS customer_id,
        lower(trim(status)) AS status,
        CAST(CAST(totalPriceCents AS DECIMAL(18,2)) / 100 AS DECIMAL(18,2)) AS order_amount,
        upper(trim(currency)) AS currency,
        CAST(createdAt AS TIMESTAMPTZ) AS ordered_at,
        ROW_NUMBER() OVER (
            PARTITION BY orderId
            ORDER BY CAST(updatedAt AS TIMESTAMPTZ) DESC, sourceVersion DESC
        ) AS version_rank
    FROM raw_orders
)
SELECT order_id, customer_id, status, order_amount, currency, ordered_at
FROM normalized
WHERE version_rank = 1"""

FACT_SQL = """SELECT order_id, customer_id, status, order_amount, currency, ordered_at
FROM stg_orders
WHERE status = 'completed'"""

BROKEN_FACT_SQL = """SELECT o.order_id, o.customer_id, o.status, o.order_amount, o.currency, o.ordered_at
FROM stg_orders AS o
LEFT JOIN order_items AS i ON o.order_id = i.order_id
WHERE o.status = 'completed'"""

BUSINESS_DEFINITION = (
    "Gross completed-order revenue before returns, in USD. Use the latest source order "
    "version, include only completed orders, and count each order amount once. "
    "This is neither net revenue after refunds nor the sum of payment attempts."
)


def quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"type": "binary", "encoding": "hex", "value": bytes(value).hex()}
    if isinstance(value, timedelta):
        return {"type": "interval", "days": value.days, "seconds": value.seconds, "microseconds": value.microseconds}
    if isinstance(value, float) and not isfinite(value):
        return {"type": "non_finite_number", "value": str(value)}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    return value


def money(value: Any) -> str:
    return format(Decimal(value or 0).quantize(Decimal("0.01")), ".2f")


def assertion(id: str, name: str, passed: bool, expected: Any, actual: Any, evidence: str) -> TestResult:
    return TestResult(id=id, name=name, status="pass" if passed else "fail", expected=expected, actual=actual, evidence=evidence)


class ModelingEngine:
    """No student state, grading policy, monitoring, or AI is part of this engine."""

    def __init__(self, fixture: dict | None = None, expected: dict | None = None):
        self.fixture = fixture if fixture is not None else fixture_data()
        self.expected = expected if expected is not None else expected_data()

    @contextmanager
    def connection(self):
        db = duckdb.connect(":memory:", config={
            "enable_external_access": "false", "autoload_known_extensions": "false",
            "autoinstall_known_extensions": "false", "allow_unsigned_extensions": "false",
            "memory_limit": "64MB", "threads": "1",
        })
        try:
            db.execute("SET TimeZone = 'UTC'")
            load_fixtures(db, self.fixture)
            db.execute(f"CREATE VIEW stg_orders AS {STAGING_SQL}")
            db.execute("CREATE VIEW completed_orders AS SELECT * FROM stg_orders WHERE status = 'completed'")
            yield db
        finally:
            db.close()

    @property
    def available_tables(self) -> set[str]:
        return set(self.fixture["tables"]) | {"stg_orders", "completed_orders"}

    def columns(self, db, table: str) -> list[ColumnDefinition]:
        return [ColumnDefinition(name=r[0], data_type=r[1], nullable=r[2] == "YES")
                for r in db.execute(f"DESCRIBE {quote(table)}").fetchall()]

    def rows(self, db, table: str) -> list[dict]:
        result = db.execute(f"SELECT * FROM {quote(table)} ORDER BY ALL LIMIT 201")
        columns = [col[0] for col in result.description]
        rows = result.fetchall()
        if len(rows) > 200:
            raise LabError("This small-fixture lab supports at most 200 result rows.", "result_limit")
        return [dict(zip(columns, map(json_value, row))) for row in rows]

    def count(self, db, table: str) -> int:
        return db.execute(f"SELECT count(*) FROM {quote(table)}").fetchone()[0]

    def key_tests(self, db, table: str, keys: list[str]) -> list[TestResult]:
        names = {col.name for col in self.columns(db, table)}
        if len(set(keys)) != len(keys) or not keys or any(k not in names for k in keys):
            return [assertion("primary_key", "Primary key exists", False, keys, sorted(names), "Declare distinct keys that exist in the result.")]
        nulls = db.execute(f"SELECT count(*) FROM {quote(table)} WHERE " + " OR ".join(f"{quote(k)} IS NULL" for k in keys)).fetchone()[0]
        duplicates = db.execute(f"SELECT coalesce(sum(n - 1), 0) FROM (SELECT count(*) n FROM {quote(table)} GROUP BY " + ", ".join(map(quote, keys)) + " HAVING count(*) > 1)").fetchone()[0]
        return [
            assertion("not_null_key", "Primary key is not null", nulls == 0, 0, nulls, f"{nulls} rows have a NULL in {', '.join(keys)}."),
            assertion("unique_key", "Primary key is unique", duplicates == 0, 0, duplicates, f"{duplicates} extra rows repeat {', '.join(keys)}."),
        ]

    def source_model(self, db, name: str) -> ModelDefinition:
        d = self.fixture["tables"][name]
        return ModelDefinition(id=name, name=f"raw.{d['label']}", layer="source", why=d["description"],
                               grain=GrainDefinition(), columns=self.columns(db, name),
                               row_count=self.count(db, name), rows=self.rows(db, name), materialization="source table")

    def fact_contract(self) -> ContractDefinition:
        return ContractDefinition(
            grain="order", primary_key=["order_id"], semantic_meaning=BUSINESS_DEFINITION,
            columns=[ColumnDefinition(name=name, data_type=typ, nullable=name == "customer_id")
                     for name, typ in zip(self.expected["columns"], self.expected["types"])],
        )

    def planned_metric(self) -> MetricDefinition:
        return MetricDefinition(name="Revenue", description=BUSINESS_DEFINITION, measure="order_amount",
                                aggregation="SUM", time_dimension="ordered_at", filters=["status = 'completed'"],
                                dimensions=["customer_id", "currency"], grain="order", owner="Finance",
                                currency="USD", expected_value=self.expected["revenue"])

    def staging_step(self, db=None) -> TransformationStep:
        return TransformationStep(
            id="clean-orders", input_model="raw_orders", output_model="stg_orders", operation="CLEAN & DEDUPLICATE",
            why="Keep one current record per order before applying business rules. Cancelled orders remain in source-conformed staging.",
            input_grain="source order version (scenario contract)", output_grain="order (declared model contract)",
            input_rows=self.count(db, "raw_orders") if db else None,
            output_rows=self.count(db, "stg_orders") if db else None,
            columns_removed=["updatedAt", "sourceVersion"],
            columns_renamed={"orderId": "order_id", "customerId": "customer_id", "totalPriceCents": "order_amount", "createdAt": "ordered_at"},
            filters=["version_rank = 1"], windows=["ROW_NUMBER by orderId; newest updatedAt, then highest sourceVersion"],
            tests=self.key_tests(db, "stg_orders", ["order_id"]) if db else [],
        )

    def scenario(self) -> ScenarioDefinition:
        with self.connection() as db:
            sources = [self.source_model(db, name) for name in self.fixture["tables"]]
            planned = [
                ModelDefinition(id="stg_orders", name="stg_orders", layer="staging", why="Normalize source names, amounts, and UTC timestamps; keep the latest version of each order.", grain=GrainDefinition(), parents=["raw_orders"]),
                ModelDefinition(id="fct_orders", name="fct_orders", layer="fact", why="Represent each completed order once, so revenue can be added without duplication.", grain=GrainDefinition(), parents=["stg_orders"]),
                ModelDefinition(id="revenue", name="Revenue", layer="metric", why=BUSINESS_DEFINITION, grain=GrainDefinition(), parents=["fct_orders"], materialization="semantic definition"),
            ]
            return ScenarioDefinition(
                id=self.fixture["id"], title=self.fixture["title"], business_question="How much gross revenue did completed orders generate?",
                business_definition=BUSINESS_DEFINITION, sources=sources, planned_models=planned,
                relationships=[
                    RelationshipDefinition(id="orders-items", left_model="stg_orders", right_model="order_items", left_key="order_id", right_key="order_id", expected="1:N", description="After order-version deduplication, one order can have many items."),
                    RelationshipDefinition(id="orders-customers", left_model="raw_orders", right_model="customers", left_key="customerId", right_key="customer_id", expected="N:1", description="Many orders can belong to one customer. NULL customer keys remain possible."),
                    RelationshipDefinition(id="orders-payments", left_model="stg_orders", right_model="payments", left_key="order_id", right_key="order_id", expected="1:N", description="A deduplicated order can have multiple payment attempts."),
                    RelationshipDefinition(id="items-products", left_model="order_items", right_model="products", left_key="product_id", right_key="product_id", expected="N:1", description="Each item references a product."),
                    RelationshipDefinition(id="orders-returns", left_model="stg_orders", right_model="returns", left_key="order_id", right_key="order_id", expected="1:N", description="An order may have returns; this metric is before returns."),
                ],
                transformations=[self.staging_step(), TransformationStep(id="model-orders", input_model="stg_orders", output_model="fct_orders", operation="MODEL", why="Business logic belongs after staging: include completed orders exactly once.", input_grain="order (planned)", output_grain="order (planned)", filters=["status = 'completed'"]),
                                 TransformationStep(id="define-revenue", input_model="fct_orders", output_model="revenue", operation="MEASURE", why=BUSINESS_DEFINITION, input_grain="order (planned)", output_grain="one metric value", aggregations=["SUM(order_amount)"])],
                reference_sql={"staging": STAGING_SQL, "safe": FACT_SQL, "fanout": BROKEN_FACT_SQL},
                fact_contract=self.fact_contract(), expected_revenue=self.expected["revenue"], planned_metric=self.planned_metric(),
            )

    def declare_grain(self, request: GrainRequest) -> GrainResult:
        if request.table not in self.fixture["tables"]:
            raise LabError("Declare a grain for a source table in this scenario.", "unknown_table")
        d = self.fixture["tables"][request.table]
        with self.connection() as db:
            model = self.source_model(db, request.table)
            tests = self.key_tests(db, request.table, request.primary_key)
            tests.append(assertion("source_grain", "Grain matches source meaning", request.grain == d["grain"], d["grain_label"], request.grain,
                                   f"The scenario's producer contract says {d['grain_label']}. A unique key alone does not prove row meaning."))
            tests.append(assertion("source_key", "Key matches producer contract", set(request.primary_key) == set(d["primary_key"]), d["primary_key"], request.primary_key,
                                   "The source contract identifies this row using " + ", ".join(d["primary_key"]) + "."))
            passed = all(t.status == "pass" for t in tests)
            model.grain = GrainDefinition(declared=request.grain, label=d["grain_label"] if passed else f"Declared: {request.grain}", status="pass" if passed else "fail", classification="declared", evidence=" ".join(t.evidence for t in tests))
            model.primary_key, model.status, model.tests = request.primary_key, model.grain.status, tests
            return GrainResult(model=model, tests=tests, status=model.status)

    def require_source_grain(self, grain: str):
        if grain != self.fixture["tables"]["raw_orders"]["grain"]:
            raise LabError("First declare the source grain: one row per source order version. Raw orderId is repeated.", "grain_required")

    def staging_model(self, db) -> ModelDefinition:
        tests = self.key_tests(db, "stg_orders", ["order_id"])
        return ModelDefinition(id="stg_orders", name="stg_orders", layer="staging", why="Normalize source records and select their newest version; preserve source-level order statuses.",
                               grain=GrainDefinition(declared="order", label="1 row / order", status="pass", classification="declared", evidence="Declared order grain; order_id is unique and not null in the fixture."),
                               primary_key=["order_id"], columns=self.columns(db, "stg_orders"), row_count=self.count(db, "stg_orders"),
                               rows=self.rows(db, "stg_orders"), parents=["raw_orders"], sql=STAGING_SQL, status="pass", tests=tests)

    def stage(self, request: StagingRequest) -> StagingResult:
        self.require_source_grain(request.source_grain)
        with self.connection() as db:
            return StagingResult(model=self.staging_model(db), transformation=self.staging_step(db))

    def _execute_candidate(self, db, sql: str) -> tuple[str, list[str], exp.Expression]:
        normalized, parents, tree = inspect_query(sql, self.available_tables)
        timeout = Timer(2.0, db.interrupt)
        timeout.daemon = True
        timeout.start()
        try:
            db.execute(f"CREATE TEMP TABLE candidate AS {normalized}")
        finally:
            timeout.cancel()
        return normalized, parents, tree

    def _evaluate(self, db, request: BuildRequest) -> EvaluationResult:
        columns = self.columns(db, "candidate")
        rows = self.rows(db, "candidate")
        types = {c.name: c.data_type for c in columns}
        expected_cols = self.expected["columns"]
        schema_ok = all(types.get(c) == typ for c, typ in zip(expected_cols, self.expected["types"]))
        projected = [tuple(row.get(c) for c in expected_cols) for row in rows]
        expected_rows = [tuple(row[c] for c in expected_cols) for row in self.expected["rows"]]
        output_matches = schema_ok and Counter(projected) == Counter(expected_rows)
        tests = [assertion("schema", "Model schema satisfies contract", schema_ok, dict(zip(expected_cols, self.expected["types"])), types, "Required columns use exact monetary precision and timezone-aware timestamps; additional columns are allowed."),
                 assertion("expected_output", "Output matches golden rows", output_matches, self.expected["rows"], rows, "Compare every required field and row, including row multiplicity; SQL text and row order do not matter."),
                 assertion("row_count", "Completed-order row count", len(rows) == len(expected_rows), len(expected_rows), len(rows), "The fixture has three completed orders; the cancelled order does not belong in this fact.")]
        key_tests = self.key_tests(db, "candidate", request.primary_key)
        tests.extend(key_tests)
        key_ok = all(t.status == "pass" for t in key_tests)
        declared_ok = request.grain == "order" and request.primary_key == ["order_id"]
        grain_ok = declared_ok and key_ok
        tests.append(assertion("grain", "Declared grain is supported", grain_ok, "order; key = order_id", f"{request.grain}; key = {','.join(request.primary_key)}", "Order meaning is declared explicitly. A unique, non-null order_id must support it; golden row comparison checks the business meaning."))
        if schema_ok:
            rules = [
                ("required_values", "Required fields are not null", "order_id IS NULL OR status IS NULL OR order_amount IS NULL OR currency IS NULL OR ordered_at IS NULL"),
                ("completed_only", "Only completed orders", "status IS DISTINCT FROM 'completed'"),
                ("non_negative", "Amounts are non-negative", "order_amount < 0"),
                ("currency", "One declared currency: USD", "currency IS DISTINCT FROM 'USD'"),
                ("relationships", "Customer keys reference customers", "customer_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM customers c WHERE c.customer_id = candidate.customer_id)"),
            ]
            for id, label, predicate in rules:
                failures = db.execute(f"SELECT count(*) FROM candidate WHERE {predicate}").fetchone()[0]
                tests.append(assertion(id, label, failures == 0, 0, failures, f"{failures} rows violate this dataset assertion."))
        passed = all(t.status == "pass" for t in tests)
        warnings = []
        if not key_ok:
            warnings.append("Repeating an order key can repeat its full amount. Aggregating after the join does not repair inflated measures.")
        if not schema_ok:
            warnings.append("A valid query can still violate a model's schema or monetary/time contract.")
        return EvaluationResult(sql_valid=True, output_matches_expected=output_matches,
                                grain=GrainDefinition(declared=request.grain, label=f"1 row / {request.grain}", status="pass" if grain_ok else "fail", classification="declared", evidence="Declared by the learner; supported by key assertions" if grain_ok else "Declared grain is contradicted by the key or expected grain."),
                                primary_key={"expected": ["order_id"], "declared": request.primary_key, "unique": any(t.id == "unique_key" and t.status == "pass" for t in key_tests), "not_null": any(t.id == "not_null_key" and t.status == "pass" for t in key_tests)},
                                tests=tests, warnings=warnings, status="pass" if passed else "fail",
                                explanation=(f"All {len(tests)} assertions pass: three completed orders occur once and match the independently specified golden rows. Revenue can be summed at order grain." if passed else f"{sum(t.status == 'fail' for t in tests)} assertions fail. SQL executed, but the dataset does not satisfy the declared order model. Inspect failed assertions and repeated keys."),
                                performance_notes=["Measured on a tiny local fixture; no warehouse performance guarantee is inferred."])

    def _metric(self, db, aggregation: str = "SUM", name: str = "Revenue") -> MetricDefinition:
        definition = self.planned_metric()
        definition.name, definition.aggregation = name, aggregation
        types = {c.name: c.data_type for c in self.columns(db, "candidate")}
        if not {"order_amount", "currency", "status"} <= types.keys():
            definition.status, definition.evidence = "fail", "Required amount, status, or currency column is missing."
            return definition
        if not types["order_amount"].startswith("DECIMAL(") or types["currency"] != "VARCHAR" or types["status"] != "VARCHAR":
            definition.status, definition.evidence = "fail", "Metric inputs must use exact DECIMAL money and text currency/status columns."
            return definition
        invalid_currency = db.execute("SELECT count(*) FROM candidate WHERE currency IS DISTINCT FROM 'USD'").fetchone()[0]
        if invalid_currency:
            definition.status, definition.evidence = "fail", "Mixed or unknown currencies cannot be summed as USD revenue."
            return definition
        result = db.execute(f"SELECT {aggregation}(order_amount) FROM candidate WHERE status = 'completed'").fetchone()[0]
        definition.value = money(result)
        correct = aggregation == "SUM" and definition.value == self.expected["revenue"]
        definition.status = "pass" if correct else "fail"
        definition.evidence = (f"{aggregation}(order_amount) over completed USD rows = {definition.value}. "
                               f"The business definition requires SUM and the golden result is {self.expected['revenue']}. "
                               "Metric agreement alone does not certify the fact: its row/key tests must also pass.")
        return definition

    def build(self, request: BuildRequest) -> BuildResult:
        self.require_source_grain(request.source_grain)
        sql = request.sql if request.sql is not None else (FACT_SQL if request.strategy == "safe" else BROKEN_FACT_SQL)
        with self.connection() as db:
            staging = self.staging_model(db)
            try:
                normalized, parents, tree = self._execute_candidate(db, sql)
            except duckdb.Error as exc:
                error_test = assertion("sql", "SQL executes", False, "valid query", str(exc), "DuckDB rejected or interrupted the query; no output is certified.")
                evaluation = EvaluationResult(sql_valid=False, output_matches_expected=False, grain=GrainDefinition(declared=request.grain, label=f"Declared: {request.grain}", classification="declared", status="unknown"), primary_key={"expected": ["order_id"], "declared": request.primary_key, "unique": False, "not_null": False}, tests=[error_test], status="fail", explanation=str(exc))
                fact = ModelDefinition(id="fct_orders", name="fct_orders", layer="fact", why="Represent each completed order once.", grain=evaluation.grain, sql=sql, status="fail", tests=[error_test])
                return BuildResult(staging=staging, fact=fact, metric=self.planned_metric(), evaluation=evaluation, transformations=[self.staging_step(db)])
            evaluation = self._evaluate(db, request)
            metric = self._metric(db)
            fact = ModelDefinition(id="fct_orders", name="fct_orders", layer="fact", why="Represent each completed order once, making its amount safely additive at order grain.",
                                   grain=evaluation.grain, primary_key=request.primary_key, columns=self.columns(db, "candidate"), row_count=self.count(db, "candidate"),
                                   rows=self.rows(db, "candidate"), parents=parents, sql=normalized, status=evaluation.status, tests=evaluation.tests, materialization="local exercise table")
            steps = [self.staging_step(db)]
            inputs = []
            if "completed_orders" in parents:
                tests = self.key_tests(db, "completed_orders", ["order_id"])
                inputs.append(ModelDefinition(id="completed_orders", name="completed_orders", layer="intermediate",
                                              why="Prepared teaching input: filter staged orders to completed status, preserving one row per order.",
                                              grain=GrainDefinition(declared="order", label="1 row / order", classification="declared", status="pass", evidence="Prepared view's declared order grain is supported by key assertions."),
                                              primary_key=["order_id"], columns=self.columns(db, "completed_orders"), rows=self.rows(db, "completed_orders"),
                                              row_count=self.count(db, "completed_orders"), parents=["stg_orders"], sql="SELECT * FROM stg_orders WHERE status = 'completed'", status="pass", tests=tests))
                steps.append(TransformationStep(id="staging-to-completed", input_model="stg_orders", output_model="completed_orders", operation="FILTER",
                                                why=inputs[-1].why, input_grain="order", output_grain="order", input_rows=self.count(db, "stg_orders"),
                                                output_rows=self.count(db, "completed_orders"), filters=["status = 'completed'"], tests=tests))
            for parent in parents:
                if parent in self.fixture["tables"]:
                    inputs.append(self.source_model(db, parent))
                input_columns = {c.name for c in self.columns(db, parent)}
                output_columns = {c.name for c in fact.columns}
                input_grain = "order" if parent in {"stg_orders", "completed_orders"} else self.fixture["tables"][parent]["grain_label"] + " (scenario contract)"
                steps.append(TransformationStep(id=f"{parent}-to-fact", input_model=parent, output_model="fct_orders", operation="MODEL", why=fact.why,
                                                input_grain=input_grain, output_grain=fact.grain.label, input_rows=self.count(db, parent), output_rows=fact.row_count,
                                                columns_added=sorted(output_columns - input_columns), columns_removed=sorted(input_columns - output_columns),
                                                filters=[w.sql(dialect="duckdb") for w in tree.find_all(exp.Where)],
                                                joins=[j.sql(dialect="duckdb") for j in tree.find_all(exp.Join)],
                                                aggregations=[a.sql(dialect="duckdb") for a in tree.find_all(exp.AggFunc)],
                                                windows=[w.sql(dialect="duckdb") for w in tree.find_all(exp.Window)], tests=fact.tests))
            steps.append(TransformationStep(id="define-revenue", input_model="fct_orders", output_model="revenue", operation="MEASURE", why=BUSINESS_DEFINITION,
                                            input_grain=fact.grain.label, output_grain="one metric value", input_rows=fact.row_count, output_rows=1, aggregations=["SUM(order_amount)"], filters=["status = 'completed'"]))
            return BuildResult(staging=staging, fact=fact, metric=metric, evaluation=evaluation, transformations=steps, inputs=inputs)

    def metric(self, request: MetricRequest) -> MetricDefinition:
        self.require_source_grain(request.build.source_grain)
        sql = request.build.sql if request.build.sql is not None else (FACT_SQL if request.build.strategy == "safe" else BROKEN_FACT_SQL)
        with self.connection() as db:
            try:
                self._execute_candidate(db, sql)
            except duckdb.Error as exc:
                raise LabError("Build an executable fact first: " + str(exc), "sql_execution") from exc
            self.rows(db, "candidate")  # Enforce the same output bound as model evaluation.
            return self._metric(db, request.aggregation, request.name)

    def _grain_label(self, name: str) -> str:
        if name in {"stg_orders", "completed_orders"}:
            return "1 row / order (prepared teaching input)"
        return self.fixture["tables"][name]["grain_label"] + " (scenario contract)"

    def join(self, request: JoinRequest) -> JoinResult:
        if request.left_table not in self.available_tables or request.right_table not in self.available_tables:
            raise LabError("Choose tables from this fixture scenario.", "unknown_table")
        with self.connection() as db:
            left, right = request.left_table, request.right_table
            lc, rc = self.columns(db, left), self.columns(db, right)
            if request.left_key not in {c.name for c in lc} or request.right_key not in {c.name for c in rc}:
                raise LabError("The selected join key must exist on each side.", "join_key")
            lt = next(c.data_type for c in lc if c.name == request.left_key)
            rt = next(c.data_type for c in rc if c.name == request.right_key)
            if lt != rt:
                raise LabError("Choose compatible join-key types; this lab does not silently cast keys.", "join_key_type")
            lkey, rkey = quote(request.left_key), quote(request.right_key)
            right_after = right
            if request.aggregate_right:
                db.execute(f"CREATE TEMP TABLE right_aggregated AS SELECT {rkey}, count(*) AS matched_records FROM {quote(right)} GROUP BY {rkey}")
                right_after = "right_aggregated"
            right_cols = self.columns(db, right_after)
            projections = [f"l.{quote(c.name)} AS {quote('left_' + c.name)}" for c in lc] + [f"r.{quote(c.name)} AS {quote('right_' + c.name)}" for c in right_cols]
            sql = f"SELECT {', '.join(projections)} FROM {quote(left)} l {'LEFT' if request.kind == 'left' else 'INNER'} JOIN {quote(right_after)} r ON l.{lkey} = r.{rkey}"
            db.execute(f"CREATE TEMP TABLE join_result AS {sql}")
            lfreq = dict(db.execute(f"SELECT {lkey}, count(*) FROM {quote(left)} GROUP BY {lkey} ORDER BY 1").fetchall())
            rfreq = dict(db.execute(f"SELECT {rkey}, count(*) FROM {quote(right_after)} GROUP BY {rkey} ORDER BY 1").fetchall())
            matched = {key for key in lfreq if key is not None and key in rfreq}
            lmany = any(lfreq[k] > 1 for k in matched)
            rmany = any(rfreq[k] > 1 for k in matched)
            actual = ("N:N" if lmany and rmany else "N:1" if lmany else "1:N" if rmany else "1:1") if matched else "unknown"
            calculated = sum(n * (rfreq.get(k, 0) if k is not None else 0) if request.kind == "inner" else n * max(1, rfreq.get(k, 0) if k is not None else 0) for k, n in lfreq.items())
            unmatched = sum(n for k, n in lfreq.items() if k is None or k not in rfreq)
            fanout = any(rfreq[k] > 1 for k in matched)
            left_cols = {c.name for c in lc}
            has_amount = {"order_amount", "currency"} <= left_cols
            currencies = db.execute(f"SELECT DISTINCT currency FROM {quote(left)}").fetchall() if has_amount else []
            currency = currencies[0][0] if len(currencies) == 1 and currencies[0][0] is not None else None
            baseline = money(db.execute(f"SELECT sum(order_amount) FROM {quote(left)}").fetchone()[0]) if has_amount and currency else None
            joined = money(db.execute("SELECT sum(left_order_amount) FROM join_result").fetchone()[0]) if has_amount and currency else None
            amounts = dict(db.execute(f"SELECT {lkey}, sum(order_amount) FROM {quote(left)} GROUP BY {lkey}").fetchall()) if baseline else {}
            traces = []
            for k, n in lfreq.items():
                right_n = rfreq.get(k, 0) if k is not None else 0
                multiplier = max(1, right_n) if request.kind == "left" else right_n
                traces.append(JoinTrace(key=json_value(k), left_rows=n, right_rows=right_n, output_rows=n * multiplier, repeated=right_n > 1,
                                        order_amount=money(amounts[k]) if k in amounts else None,
                                        contribution=money(amounts[k] * multiplier) if k in amounts else None))
            rows = self.rows(db, "join_result")
            tests = [assertion("join_rows", "Execution matches multiplicity calculation", len(rows) == calculated, calculated, len(rows), "For each non-null key, multiply left and right matches; LEFT preserves each unmatched left row."),
                     assertion("expected_cardinality", "Cardinality matches your expectation", actual == request.expected_cardinality, request.expected_cardinality, actual, "Observed on matched fixture keys, not a guarantee for future production data."),
                     assertion("expected_rows", "Rows match your expectation", len(rows) == request.expected_rows, request.expected_rows, len(rows), "Expected rows are the learner's estimate; actual rows come from DuckDB execution.")]
            if fanout:
                grain = GrainDefinition(label="1 row / left–right match (inferred)", classification="inference", status="warning", evidence="At least one left key matches multiple right rows. Do not assume the left grain survives.")
                repeated = ", ".join(str(t.key) for t in traces if t.repeated)
                explanation = f"Keys {repeated} match multiple right records. Each match carries the full left row again: {self.count(db, left)} left rows become {len(rows)} joined rows."
                if baseline and joined:
                    explanation += f" Summing the repeated order amount changes {currency} {baseline} to {currency} {joined}. Aggregate the right side to the join key before joining."
            else:
                grain = GrainDefinition(label="Left row grain preserved (observed)" if request.kind == "left" else "Subset of left row grain (observed)", classification="inference", status="pass", evidence="Every matched left row has at most one right match in this fixture; INNER may still remove unmatched rows.")
                explanation = f"Every matched left row has at most one right match. The result contains {len(rows)} rows; {unmatched} left rows have no match. " + ("LEFT retains unmatched rows." if request.kind == "left" else "INNER removes unmatched rows.")
            return JoinResult(left_table=left, right_table=right, left_rows=self.count(db, left), right_rows=self.count(db, right), right_rows_after=self.count(db, right_after),
                              expected_cardinality=request.expected_cardinality, actual_cardinality=actual, expected_rows=request.expected_rows, calculated_rows=calculated, actual_rows=len(rows),
                              unmatched_left_rows=unmatched, null_left_keys=lfreq.get(None, 0), null_right_keys=rfreq.get(None, 0), left_grain=self._grain_label(left),
                              right_grain="1 row / join key after aggregation (declared operation)" if request.aggregate_right else self._grain_label(right),
                              resulting_grain=grain, fanout=fanout, baseline_amount=baseline, joined_amount=joined, currency=currency,
                              trace=traces, rows=rows, sql=sql, tests=tests, explanation=explanation)
