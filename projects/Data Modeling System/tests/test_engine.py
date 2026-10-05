from copy import deepcopy
from decimal import Decimal

import pytest

from data_modeling_lab.contracts import BuildRequest, GrainRequest, JoinRequest, MetricRequest, StagingRequest
from data_modeling_lab.engine import BROKEN_FACT_SQL, FACT_SQL, ModelingEngine
from data_modeling_lab.fixtures import expected_data, fixture_data
from data_modeling_lab.sql import LabError


def request(**kwargs):
    return BuildRequest(source_grain="source_order_version", grain="order", **kwargs)


def test_golden_fixture_is_independently_reconciled():
    oracle = expected_data()
    assert sum(Decimal(r["order_amount"]) for r in oracle["rows"]) == Decimal("225.00")
    e = ModelingEngine()
    built = e.build(request())
    assert built.fact.rows == oracle["rows"]
    assert built.fact.row_count == 3
    assert built.metric.value == "225.00"
    assert built.evaluation.status == "pass"
    assert all(t.status == "pass" for t in built.evaluation.tests)


def test_unknown_grain_and_source_version_gate():
    e = ModelingEngine()
    assert all(m.grain.status == "unknown" and m.grain.declared is None for m in e.scenario().sources)
    result = e.declare_grain(GrainRequest(table="raw_orders", grain="order", primary_key=["orderId"]))
    assert result.status == "fail"
    assert next(t.actual for t in result.tests if t.id == "unique_key") == 1
    with pytest.raises(LabError, match="source order version"):
        e.stage(StagingRequest(source_grain="order"))
    assert e.declare_grain(GrainRequest(table="raw_orders", grain="source_order_version", primary_key=["orderId", "sourceVersion"])).status == "pass"


def test_staging_deduplicates_and_preserves_source_statuses():
    stage = ModelingEngine().stage(StagingRequest(source_grain="source_order_version"))
    assert stage.model.row_count == 4
    assert stage.model.rows[0]["order_amount"] == "100.00"
    assert stage.model.rows[-1]["status"] == "cancelled"
    assert stage.model.rows[-1]["customer_id"] is None
    assert stage.transformation.input_rows == 5
    assert stage.transformation.output_rows == 4


def test_deduplication_has_explicit_tie_breaking():
    fixture = deepcopy(fixture_data())
    rows = fixture["tables"]["raw_orders"]["rows"]
    rows[0][6] = rows[1][6]
    assert ModelingEngine(fixture=fixture).stage(StagingRequest(source_grain="source_order_version")).model.rows[0]["order_amount"] == "100.00"
    rows[0][7] = rows[1][7]
    with pytest.raises(ValueError, match="Ambiguous source versions"):
        ModelingEngine(fixture=fixture).scenario()


def test_direct_join_fanout_and_aggregation_repair():
    e = ModelingEngine()
    broken = e.join(JoinRequest())
    assert broken.actual_cardinality == "1:N"
    assert broken.actual_rows == broken.calculated_rows == 4
    assert broken.fanout and broken.joined_amount == "325.00" and broken.baseline_amount == "225.00"
    assert next(t for t in broken.trace if t.key == "O1").contribution == "200.00"
    assert broken.resulting_grain.classification == "inference"
    safe = e.join(JoinRequest(aggregate_right=True, expected_cardinality="1:1"))
    assert safe.actual_rows == 3 and not safe.fanout and safe.joined_amount == "225.00"
    assert all(t.status == "pass" for t in safe.tests)


@pytest.mark.parametrize("left,right,lk,rk,expected", [
    ("completed_orders", "customers", "customer_id", "customer_id", "N:1"),
    ("completed_orders", "order_items", "order_id", "order_id", "1:N"),
    ("order_items", "payments", "order_id", "order_id", "N:N"),
    ("customers", "customers", "customer_id", "customer_id", "1:1"),
])
def test_all_cardinality_classes(left, right, lk, rk, expected):
    joined = ModelingEngine().join(JoinRequest(left_table=left, right_table=right, left_key=lk, right_key=rk))
    assert joined.actual_cardinality == expected
    assert joined.actual_rows == joined.calculated_rows


def test_null_join_keys_never_match_and_inner_removes_unmatched():
    e = ModelingEngine()
    kw = dict(left_table="stg_orders", right_table="customers", left_key="customer_id", right_key="customer_id")
    left = e.join(JoinRequest(**kw, kind="left"))
    inner = e.join(JoinRequest(**kw, kind="inner"))
    assert left.null_left_keys == left.unmatched_left_rows == 1
    assert left.actual_rows == 4 and inner.actual_rows == 3
    assert next(t for t in left.trace if t.key is None).right_rows == 0
    assert next(t for t in inner.trace if t.key is None).output_rows == 0


def test_no_matches_are_unknown_cardinality():
    joined = ModelingEngine().join(JoinRequest(right_table="products", right_key="product_id", kind="inner"))
    assert joined.actual_cardinality == "unknown" and joined.actual_rows == 0
    assert joined.joined_amount == "0.00"


def test_broken_fact_reports_key_and_output_failures():
    built = ModelingEngine().build(request(strategy="fanout"))
    assert built.evaluation.sql_valid
    assert built.evaluation.status == "fail" and not built.evaluation.output_matches_expected
    assert not built.evaluation.primary_key["unique"]
    assert built.fact.row_count == 4 and built.metric.value == "325.00"
    assert "order_items" in built.fact.parents


def test_equivalent_sql_and_extra_descriptive_column_are_accepted():
    sql = """WITH complete AS (SELECT * FROM stg_orders WHERE status IN ('completed'))
    SELECT o.*, c.name AS customer_name FROM complete o
    LEFT JOIN customers c ON o.customer_id = c.customer_id ORDER BY order_id DESC"""
    built = ModelingEngine().build(request(sql=sql))
    assert built.evaluation.status == "pass"
    assert set(built.fact.parents) == {"stg_orders", "customers"}
    assert next(s for s in built.transformations if s.input_model == "customers").output_rows == 3


@pytest.mark.parametrize("sql", [
    "SELECT * FROM stg_orders",
    "SELECT order_id, customer_id, status, CAST(order_amount AS DOUBLE) order_amount, currency, ordered_at FROM completed_orders",
    "SELECT order_id, customer_id, status, 'oops' AS order_amount, currency, ordered_at FROM completed_orders",
    "SELECT order_id, customer_id, status, NULL::DECIMAL(18,2) AS order_amount, currency, ordered_at FROM completed_orders",
    "SELECT order_id, customer_id, status, -order_amount AS order_amount, currency, ordered_at FROM completed_orders",
    "SELECT order_id, customer_id, status, order_amount, 'EUR' AS currency, ordered_at FROM completed_orders",
    "SELECT order_id, customer_id, status, order_amount, currency, ordered_at::TIMESTAMP ordered_at FROM completed_orders",
])
def test_valid_sql_is_not_sufficient_for_a_valid_model(sql):
    built = ModelingEngine().build(request(sql=sql))
    assert built.evaluation.sql_valid and built.evaluation.status == "fail"


def test_execution_errors_produce_failed_evaluation():
    built = ModelingEngine().build(request(sql="SELECT no_such_column FROM stg_orders"))
    assert not built.evaluation.sql_valid and built.evaluation.status == "fail"
    assert built.fact.row_count is None


@pytest.mark.parametrize("sql", [
    "DROP TABLE raw_orders", "SELECT * FROM stg_orders; DELETE FROM customers",
    "SELECT * FROM read_csv('/etc/passwd')", "SELECT * FROM duckdb_tables()",
    "SELECT * FROM 'https://example.com/data.parquet'", "SELECT random() FROM stg_orders",
    "SELECT * FROM information_schema.tables", "SELECT * FROM not_a_fixture",
    "SELECT * INTO other_table FROM stg_orders",
])
def test_unsafe_or_nondeterministic_sql_is_rejected(sql):
    with pytest.raises(LabError):
        ModelingEngine().build(request(sql=sql))


def test_result_bound_is_not_silently_truncated():
    with pytest.raises(LabError, match="200 result rows"):
        ModelingEngine().build(request(sql="SELECT a.*, b.orderId x FROM raw_orders a CROSS JOIN raw_orders b CROSS JOIN raw_orders c CROSS JOIN raw_orders d"))


def test_metric_denominator_and_business_definition():
    e = ModelingEngine()
    assert e.metric(MetricRequest(build=request())).value == "225.00"
    avg = e.metric(MetricRequest(build=request(), aggregation="AVG"))
    assert avg.value == "75.00" and avg.status == "fail"
    count = e.metric(MetricRequest(build=request(), aggregation="COUNT"))
    assert count.value == "3.00" and count.status == "fail"
    assert "before returns" in e.planned_metric().description


def test_same_input_produces_same_evidence_without_persistent_state():
    e = ModelingEngine()
    assert e.build(request()).model_dump() == e.build(request()).model_dump()
    assert e.join(JoinRequest()).model_dump() == e.join(JoinRequest()).model_dump()
