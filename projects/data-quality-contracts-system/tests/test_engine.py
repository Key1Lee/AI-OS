from copy import deepcopy
from decimal import Decimal, Inexact, ROUND_DOWN, ROUND_UP, localcontext

import pytest
from pydantic import ValidationError

from quality_system.contracts import AcceptedValues, Column, NotNull, Relationship, Unique
from quality_system.engine import money, quality_gate, validate, validate_bundle, value_matches
from quality_system.scenarios import BASE_CLOCK, BREAKS, ScenarioRequest, data_contract, fixture, scenario_input


def bundle(*corruptions):
    return validate_bundle(scenario_input(ScenarioRequest(corruptions=list(corruptions))))


def by_id(value, id):
    return next(r for r in value.results if r.rule_id == id)


def run_rule(rule_id, modify=None, expectation=None, severity=None, blocking=None):
    request = scenario_input(ScenarioRequest())
    if modify:
        modify(request.datasets)
    rule = next(r for r in bundle().rules if r.id == rule_id).model_copy(deep=True)
    if expectation is not None:
        rule.expectation = expectation
    if severity:
        rule.severity = severity
    if blocking is not None:
        rule.blocking = blocking
    return validate(rule, request.datasets, request.contract, BASE_CLOCK, "edge", "fixture-edge")


def test_valid_fixture_and_deterministic_contract():
    value = bundle()
    assert value.summary == {"PASS": 18, "WARN": 0, "FAIL": 0, "UNKNOWN": 0}
    assert value.gate.publication == "ELIGIBLE"
    assert value.model_dump_json() == bundle().model_dump_json()
    assert set(fixture()) == {"customers", "orders", "order_items", "payments", "products", "returns", "fct_orders"}
    assert by_id(value, "reconciliation").actual["warehouse_total"] == "550.00"
    assert by_id(value, "reconciliation").actual["source_net_total"] == "550.00"


@pytest.mark.parametrize("corruption,rule_id,status", [
    ("duplicate", "contract_grain", "FAIL"), ("orphan", "relationship_0_customer_id", "FAIL"),
    ("schema", "contract_schema", "FAIL"), ("stale", "freshness", "FAIL"),
    ("unpaid", "completed_paid", "FAIL"), ("null", "required_order_id", "FAIL"),
    ("invalid", "status_allowed", "FAIL"), ("shipment", "shipment_order", "FAIL"),
    ("negative", "nonnegative", "FAIL"), ("reconcile", "reconciliation", "FAIL"),
    ("empty", "volume", "FAIL"), ("warning", "description_complete", "WARN"),
])
def test_authored_break_and_repair(corruption, rule_id, status):
    value = bundle(corruption)
    assert by_id(value, rule_id).status == status
    assert value.gate.status == ("OPEN" if corruption == "warning" else "BLOCKED")
    assert bundle().summary["PASS"] == 18


def test_duplicate_counts_examples_and_revenue_inflation():
    value = bundle("duplicate")
    grain = by_id(value, "contract_grain")
    assert grain.total_rows == 11 and grain.failed_rows == 2
    assert grain.actual["distinct_non_null_keys"] == 10
    assert grain.actual["duplicate_extra_rows"] == 1
    assert {r["_row_number"] for r in grain.evidence.sample_rows} == {7, 11}
    assert by_id(value, "reconciliation").actual["warehouse_total"] == "620.00"
    assert grain.actual["semantic_grain_proof"] is False


def test_composite_key_and_null_policy():
    def duplicate(ds):
        ds["fct_orders"].rows[1]["order_id"] = "1001"
    assert run_rule("contract_grain", duplicate, Unique(columns=["order_id", "customer_id"])).status == "PASS"
    assert run_rule("contract_grain", duplicate, Unique(columns=["order_id"])).status == "FAIL"
    def nulls(ds):
        for row in ds["fct_orders"].rows:
            row["order_id"] = None
    assert run_rule("contract_grain", nulls, Unique(columns=["order_id"], null_policy="ignore")).status == "UNKNOWN"
    assert run_rule("contract_grain", nulls).status == "FAIL"


@pytest.mark.parametrize("value", ["", 0, False])
def test_non_null_means_not_none(value):
    def change(ds):
        ds["fct_orders"].rows[0]["description"] = value
    assert run_rule("description_complete", change).status == "PASS"


def test_completeness_threshold_inclusive():
    def change(ds):
        ds["fct_orders"].rows[0]["description"] = None
    result = run_rule("description_complete", change)
    assert result.status == "PASS" and result.failed_rows == 1
    assert result.actual["not_null_rate"] == "0.9"


def test_threshold_and_output_ignore_ambient_decimal_context():
    def change(ds):
        ds["fct_orders"].rows = ds["fct_orders"].rows[:3]
        ds["fct_orders"].rows[1]["description"] = None
        ds["fct_orders"].rows[2]["description"] = None
    outputs = []
    exp = NotNull(column="description", minimum_rate="0.333333333333333333333333333333")
    for precision in [6, 28, 60]:
        with localcontext() as context:
            context.prec = precision
            outputs.append(run_rule("description_complete", change, exp).model_dump_json())
    assert len(set(outputs)) == 1
    assert '"status":"PASS"' in outputs[0]


def test_decimal_rounding_and_traps_cannot_change_results():
    def change(ds):
        ds["fct_orders"].rows=ds["fct_orders"].rows[:3]
        ds["fct_orders"].rows[1]["description"]=None
        ds["fct_orders"].rows[2]["description"]=None
    outputs=[]
    for rounding in [ROUND_DOWN,ROUND_UP]:
        with localcontext() as context:
            context.rounding=rounding;context.traps[Inexact]=True
            outputs.append(run_rule("description_complete",change).model_dump_json())
    assert len(set(outputs))==1


def test_integer_is_signed_64_bit_like_exported_dbt_bigint():
    column=Column(name="number",data_type="INTEGER",nullable=False)
    assert value_matches(-(2**63),column) and value_matches(2**63-1,column)
    assert not value_matches(2**63,column) and not value_matches(-(2**63)-1,column)
    assert not value_matches(True,column)


def test_accepted_values_keep_types_and_null_policy():
    def change(ds):
        ds["fct_orders"].rows[0]["status"] = True
    result = run_rule("status_allowed", change, AcceptedValues(column="status", values=[1]))
    assert result.status == "FAIL"
    def null(ds):
        ds["fct_orders"].rows[0]["status"] = None
    assert run_rule("status_allowed", null).status == "FAIL"
    exp = AcceptedValues(column="status", values=["completed"], allow_null=True)
    assert run_rule("status_allowed", null, exp).status == "PASS"


def test_relationship_optional_unknown_members_and_late_dimension():
    def null(ds):
        ds["fct_orders"].rows[0]["customer_id"] = None
    optional = Relationship(column="customer_id", parent_dataset="customers", parent_column="customer_id", allow_null=True)
    assert run_rule("relationship_0_customer_id", null, optional).status == "PASS"
    assert run_rule("relationship_0_customer_id", null).status == "FAIL"
    def unknown(ds):
        ds["fct_orders"].rows[0]["customer_id"] = "UNKNOWN"
        ds["customers"].rows.append({"customer_id": "UNKNOWN", "email": None})
    assert run_rule("relationship_0_customer_id", unknown).status == "PASS"
    def late(ds):
        ds["fct_orders"].rows[0]["customer_id"] = "LATE"
    tolerant = optional.model_copy(update={"maximum_orphan_rate": Decimal("0.1")})
    assert run_rule("relationship_0_customer_id", late, tolerant).status == "PASS"
    assert run_rule("relationship_0_customer_id", late).status == "FAIL"


@pytest.mark.parametrize("parent", ["missing", "rows_missing", "empty", "duplicates"])
def test_relationship_parent_evidence(parent):
    # The parametrized labels are intentionally separate evidence conditions.
    def change(ds):
        if parent == "missing": ds.pop("customers")
        if parent == "rows_missing": ds["customers"].rows = None
        if parent == "empty": ds["customers"].rows = []
        if parent == "duplicates": ds["customers"].rows.append(deepcopy(ds["customers"].rows[0]))
    status = "UNKNOWN" if parent in {"missing", "rows_missing"} else "FAIL"
    assert run_rule("relationship_0_customer_id", change).status == status


@pytest.mark.parametrize("column,value", [("net_revenue", "NaN"), ("net_revenue", 10.1),
    ("net_revenue", "0.001"), ("net_revenue", "10000000000000000"),
    ("ordered_at", "2026-10-02T00:00:00"), ("order_id", 1001)])
def test_schema_checks_actual_values_not_just_metadata(column,value):
    def change(ds): ds["fct_orders"].rows[0][column] = value
    assert run_rule("contract_schema",change).status == "FAIL"


def test_schema_nullability_and_missing_metadata():
    def nullable(ds): ds["fct_orders"].columns[0].nullable = True
    assert run_rule("contract_schema",nullable).status == "FAIL"
    def missing(ds): ds["fct_orders"].columns = None
    assert run_rule("contract_schema",missing).status == "UNKNOWN"
    value = bundle("schema")
    assert by_id(value,"required_ordered_at").status == "UNKNOWN"
    assert by_id(value,"shipment_order").status == "UNKNOWN"


def test_empty_and_missing_row_evidence_fail_closed():
    value=bundle("empty")
    assert by_id(value,"contract_grain").status == "UNKNOWN"
    assert value.gate.status == "BLOCKED"
    request=scenario_input(ScenarioRequest());request.datasets["fct_orders"].rows=None
    value=validate_bundle(request)
    assert set(r.status for r in value.results)=={"UNKNOWN"}


@pytest.mark.parametrize("loaded,status", [
    ("2026-10-01T22:00:00Z","PASS"), ("2026-10-01T21:59:59.999999Z","FAIL"),
    ("2026-10-02T07:00:00+09:00","PASS"), ("2026-10-02T00:00:01Z","UNKNOWN"),
    ("2026-10-02T00:00:00","UNKNOWN"), ("not-a-date","UNKNOWN"), (None,"UNKNOWN")])
def test_freshness_explicit_clock_boundary_and_timezone(loaded,status):
    def change(ds):ds["fct_orders"].loaded_at=loaded
    assert run_rule("freshness",change).status==status


def test_stale_mode_advances_clock_without_changing_arrival():
    request=scenario_input(ScenarioRequest(corruptions=["stale"]))
    assert request.executed_at=="2026-10-02T03:00:00+00:00"
    assert request.datasets["fct_orders"].loaded_at==fixture()["fct_orders"].loaded_at
    assert by_id(validate_bundle(request),"freshness").actual["age_minutes"]=="210"


def test_warn_severity_and_blocking_are_independent():
    request=scenario_input(ScenarioRequest(corruptions=["warning"]))
    warning=next(r for r in request.contract.rules if r.id=="description_complete")
    warning.blocking=True
    value=validate_bundle(request)
    assert value.summary["WARN"]==1 and value.gate.status=="BLOCKED"
    assert bundle("warning").gate.status=="OPEN"


def test_gate_rejects_missing_duplicate_stale_mismatched_or_wrong_target():
    value=bundle()
    def gate(results, dataset="fct_orders"):
        return quality_gate(dataset,value.rules,results,value.run_id,value.input_fingerprint,BASE_CLOCK)
    assert gate(value.results).status=="OPEN"
    assert gate(value.results[1:]).status=="BLOCKED"
    assert gate(value.results+[value.results[0]]).status=="BLOCKED"
    for field,replacement in [("run_id","old"),("input_fingerprint","stale"),("target_id","customers"),
                              ("executed_at","2026-10-01T00:00:00Z"),("expected",{}),("status","UNKNOWN")]:
        changed=deepcopy(value.results);setattr(changed[0],field,replacement)
        assert gate(changed).status=="BLOCKED"
    with pytest.raises(ValueError,match="target"):
        gate(value.results,"mart_revenue")


def test_selected_checks_do_not_approve_unchecked_gate():
    request=scenario_input(ScenarioRequest(rule_ids=["contract_grain"]))
    value=validate_bundle(request)
    assert len(value.results)==1 and value.results[0].status=="PASS"
    assert value.gate.status=="BLOCKED"


def test_events_preserve_result_evidence_unknown_and_identity():
    value=bundle("schema")
    for r,e in zip(value.results,value.events):
        assert (r.status,r.rule_id,r.target_id,r.run_id,r.input_fingerprint)==(e.status,e.rule_id,e.dataset_id,e.run_id,e.input_fingerprint)
        assert r.evidence==e.evidence and e.evidence.classification=="FACT"


def test_precision_guard_supports_decimal_38_0_independent_of_context():
    value="9"*38
    column=Column(name="amount",data_type="DECIMAL",nullable=False,precision=38,scale=0)
    for precision in [6,28,60]:
        with localcontext() as context:
            context.prec=precision
            assert money(value)==Decimal(value)
            assert value_matches(value,column)


def test_invalid_contracts_and_corruptions_are_rejected():
    with pytest.raises(ValidationError):
        Unique(columns=["order_id","order_id"])
    with pytest.raises(ValidationError):
        ScenarioRequest(corruptions=["unknown"])
    with pytest.raises(ValidationError):
        ScenarioRequest(executed_at="2026-10-02")
    with pytest.raises(ValidationError):
        type(data_contract()).model_validate({**data_contract().model_dump(),"primary_key":["description"]})


def test_combining_every_corruption_is_bounded_and_repairable():
    value=bundle(*BREAKS)
    assert value.gate.status=="BLOCKED"
    assert len(value.results)==18
    assert bundle().gate.status=="OPEN"


def test_source_rows_cannot_override_evidence_locations():
    def change(ds):
        ds["fct_orders"].rows[0]["order_id"] = None
        ds["fct_orders"].rows[0]["_row_number"] = 999
    assert run_rule("required_order_id",change).evidence.sample_rows[0]["_row_number"]==1


def test_maximum_length_column_compiles_stable_bounded_rules():
    from quality_system.contracts import DataContract
    from quality_system.engine import compile_contract
    name="x"*80
    c=DataContract(id="long",dataset_id="long",grain="1 row / identifier",primary_key=[name],
        columns=[Column(name=name,data_type="STRING",nullable=False)],owner="Owner",semantic_meaning="Identifier")
    first=compile_contract(c)
    assert all(len(r.id)<=80 for r in first)
    assert [r.id for r in first]==[r.id for r in compile_contract(c)]
