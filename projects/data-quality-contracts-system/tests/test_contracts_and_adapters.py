from copy import deepcopy
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from quality_system.adapters import contract_from_modeling, dbt_export, dbt_result, gx_design, observability_test
from quality_system.api import create_app
from quality_system.compatibility import CompatibilityPolicy, CompatibilityRequest, compare_contracts
from quality_system.contracts import Column, Reconciliation
from quality_system.engine import validate, validate_bundle
from quality_system.scenarios import BASE_CLOCK, SCENARIO_ID, ScenarioRequest, data_contract, fixture, scenario_input


def reconciliation(warehouse="550.00", tolerance="0.01", relative="0", source_zero=False):
    request=scenario_input(ScenarioRequest())
    request.datasets["fct_orders"].rows[0]["net_revenue"]=str(Decimal(warehouse)-Decimal("540"))
    if source_zero:
        for row in request.datasets["payments"].rows:row["amount"]="0.00"
        request.datasets["returns"].rows=[]
    rule=next(r for r in request.contract.rules if r.id=="reconciliation")
    rule.expectation=Reconciliation(absolute_tolerance=tolerance,relative_tolerance=relative)
    return validate(rule,request.datasets,request.contract,BASE_CLOCK,"reconcile-test","fixed")


@pytest.mark.parametrize("amount,tolerance,relative,status", [
    ("550.01","0.01","0","PASS"), ("550.010001","0.01","0","FAIL"),
    ("555.50","0","0.01","PASS"), ("555.500001","0","0.01","FAIL"),
    ("549.99","0.01","0","PASS"), ("550","0","0","PASS")])
def test_reconciliation_exact_tolerances(amount,tolerance,relative,status):
    assert reconciliation(amount,tolerance,relative).status==status


def test_reconciliation_zero_source_and_aggregate_count_semantics():
    assert reconciliation("0","0","0",True).status=="PASS"
    result=reconciliation("1","0","1",True)
    assert result.status=="FAIL" and result.actual["relative_difference"] is None
    assert result.failed_rows is None


def test_relative_tolerance_uses_exact_ratio_not_rounded_quotient():
    request=scenario_input(ScenarioRequest())
    request.datasets["fct_orders"].rows=[{**request.datasets["fct_orders"].rows[0],"net_revenue":"4"}]
    request.datasets["payments"].rows=[{**request.datasets["payments"].rows[0],"amount":"3"}]
    request.datasets["returns"].rows=[]
    rule=next(r for r in request.contract.rules if r.id=="reconciliation")
    rule.expectation=Reconciliation(absolute_tolerance="0",relative_tolerance="0."+"3"*38)
    result=validate(rule,request.datasets,request.contract,BASE_CLOCK,"ratio","fixed")
    assert result.status=="FAIL"


@pytest.mark.parametrize("condition",["currency","row_currency","source","status","amount"])
def test_reconciliation_requires_compatible_evidence(condition):
    request=scenario_input(ScenarioRequest())
    if condition=="currency":request.datasets["payments"].currency="EUR"
    if condition=="row_currency":request.datasets["payments"].rows[0]["currency"]="KRW"
    if condition=="source":request.datasets.pop("payments")
    if condition=="status":request.datasets["payments"].rows[0].pop("status")
    if condition=="amount":request.datasets["payments"].rows[0]["amount"]="NaN"
    result=next(r for r in validate_bundle(request).results if r.rule_id=="reconciliation")
    assert result.status=="UNKNOWN"


def compare(change,policy=None,data=None):
    before=data_contract();after=before.model_copy(deep=True)
    change(after)
    return compare_contracts(CompatibilityRequest(before=before,after=after,policy=policy or CompatibilityPolicy(),compatible_data=data))


@pytest.mark.parametrize("change",[
    lambda c:setattr(c,"grain","1 row / item"),
    lambda c:setattr(c,"primary_key",["customer_id"]),
    lambda c:setattr(c,"semantic_meaning","Gross revenue instead of net"),
    lambda c:setattr(c,"columns",[column for column in c.columns if column.name!="ordered_at"]),
    lambda c:setattr(c.columns[1],"data_type","INTEGER"),
    lambda c:setattr(c.columns[1],"nullable",True)])
def test_structural_and_semantic_breaks(change):
    assert compare(change)["status"]=="BREAKING"


def test_optional_addition_is_policy_dependent():
    def change(c):c.columns.append(Column(name="promo_code",data_type="STRING",nullable=True,required=False))
    assert compare(change)["status"]=="COMPATIBLE"
    assert compare(change,CompatibilityPolicy(allow_optional_additions=False))["status"]=="BREAKING"


@pytest.mark.parametrize("nullable", [False, True])
@pytest.mark.parametrize("allow_optional_additions", [False, True])
def test_required_presence_relaxation_breaks_even_with_complete_sample(nullable, allow_optional_additions):
    before = data_contract()
    column = next(c for c in before.columns if c.name == "description")
    column.required = True
    column.nullable = nullable
    after = before.model_copy(deep=True)
    next(c for c in after.columns if c.name == column.name).required = False
    result = compare_contracts(CompatibilityRequest(
        before=before, after=after, compatible_data=fixture()["fct_orders"],
        policy=CompatibilityPolicy(allow_optional_additions=allow_optional_additions,
                                   allow_nullable_relaxation=True)))
    assert result["status"] == "BREAKING"
    assert result["changes"] == [{
        "kind": "presence_relaxed", "subject": "description", "classification": "BREAKING",
        "reason": "Consumers promised this column's presence may now receive data without it."}]


@pytest.mark.parametrize("required", [False, True])
def test_unchanged_presence_does_not_report_a_change(required):
    before = data_contract()
    next(c for c in before.columns if c.name == "description").required = required
    result = compare_contracts(CompatibilityRequest(before=before, after=before.model_copy(deep=True)))
    assert result["status"] == "COMPATIBLE" and result["changes"] == []


@pytest.mark.parametrize("nullable", [False, True])
def test_optional_presence_tightening_still_breaks(nullable):
    before = data_contract()
    next(c for c in before.columns if c.name == "description").nullable = nullable
    after = before.model_copy(deep=True)
    next(c for c in after.columns if c.name == "description").required = True
    result = compare_contracts(CompatibilityRequest(before=before, after=after))
    assert result["status"] == "BREAKING"
    assert len(result["changes"]) == 1
    assert result["changes"][0]["kind"] == "presence_tightened"


def test_missing_column_gate_transition_is_reported_as_breaking_by_api():
    request = scenario_input(ScenarioRequest())
    next(c for c in request.contract.columns if c.name == "description").required = True
    before = request.contract.model_copy(deep=True)
    dataset = request.datasets["fct_orders"]
    dataset.columns = [c for c in dataset.columns if c.name != "description"]
    for row in dataset.rows:
        row.pop("description", None)
    preserved_data = deepcopy(request.datasets)
    assert validate_bundle(request).gate.status == "BLOCKED"
    next(c for c in request.contract.columns if c.name == "description").required = False
    assert validate_bundle(request).gate.status == "OPEN"
    comparison = CompatibilityRequest(before=before, after=request.contract)
    response = client.post("/api/compatibility", json=comparison.model_dump(mode="json"))
    assert response.status_code == 200
    result = response.json()
    assert result == compare_contracts(comparison)
    assert result["contract_version"] == "contract-compatibility-v1"
    assert result["status"] == "BREAKING"
    assert len(result["changes"]) == 1
    assert result["changes"][0]["kind"] == "presence_relaxed"
    assert result["changes"][0]["subject"] == "description"
    assert result["changes"][0]["classification"] == "BREAKING"
    assert request.datasets == preserved_data


def test_nullable_tightening_needs_nonempty_compatible_matching_data():
    def change(c):c.columns[6].nullable=False
    assert compare(change)["status"]=="BREAKING"
    data=fixture()["fct_orders"]
    assert compare(change,data=data)["status"]=="COMPATIBLE"
    data.rows[0]["shipped_at"]=None
    assert compare(change,data=data)["status"]=="BREAKING"
    data.rows=[]
    assert compare(change,data=data)["status"]=="BREAKING"
    data=fixture()["fct_orders"];data.id="other"
    assert compare(change,data=data)["status"]=="BREAKING"


def test_modeling_requires_explicit_designed_state_and_preserves_semantics():
    payload={"contract_version":"modeling-lab-v1","dataset_id":"fct_orders","fact_contract":{
      "grain":"completed order","primary_key":["order_id"],"columns":[
        {"name":"order_id","data_type":"VARCHAR","nullable":False},
        {"name":"order_amount","data_type":"DECIMAL(18,2)","nullable":False},
        {"name":"ordered_at","data_type":"TIMESTAMP WITH TIME ZONE","nullable":False}],
      "owner":"Finance","semantic_meaning":"Gross completed-order revenue before returns in USD"}}
    c=contract_from_modeling(payload)
    assert c.grain=="1 row / completed order" and c.columns[1].scale==2
    assert c.semantic_meaning==payload["fact_contract"]["semantic_meaning"]
    assert c.rules==[] and c.relationships==[]
    with pytest.raises(ValueError):contract_from_modeling({"contract_version":"modeling-lab-v1","models":[]})
    payload["fact_contract"]["columns"][2]["data_type"]="TIMESTAMP"
    with pytest.raises(ValueError,match="Unsupported"):contract_from_modeling(payload)


def test_observability_mapping_preserves_unknown_and_expected_shape():
    value=validate_bundle(scenario_input(ScenarioRequest(corruptions=["schema"])))
    for event in value.events:
        normalized=observability_test(event,event.rule_id)
        assert normalized["status"]=={"PASS":"HEALTHY","WARN":"WARNING","FAIL":"FAILED","UNKNOWN":"UNKNOWN"}[event.status]
        assert normalized["provenance"]["classification"]=="FACT"
        assert normalized["node_id"]=="fct_orders"
        assert "score" not in normalized


def test_dbt_export_supported_rules_are_explicit_and_unknown_remains_unknown():
    c=data_contract();export=dbt_export(c)
    model=export["document"]["models"][0]
    assert model["config"]["contract"]["enforced"] is True
    assert "arguments:" in export["yaml"] and "data_tests:" in export["yaml"]
    assert "quality_unique_key" in export["yaml"]
    rule=next(r for r in c.rules if r.id=="completed_paid")
    assert dbt_result(rule,None,BASE_CLOCK,"dbt-run","dbt-fingerprint").status=="UNKNOWN"
    assert dbt_result(rule,{"status":"error","quality_rule_id":rule.id,"failures":None},BASE_CLOCK,"dbt-run","dbt-fingerprint").status=="UNKNOWN"
    raw={"status":"fail","quality_rule_id":rule.id,"failures":2}
    result=dbt_result(rule,raw,BASE_CLOCK,"dbt-run","dbt-fingerprint")
    assert result.status=="FAIL" and result.failed_rows is None


@pytest.mark.parametrize("failures",[-1,True,"1",1.5,3])
def test_dbt_pass_rejects_invalid_or_contradictory_count(failures):
    rule=data_contract().rules[0]
    raw={"status":"pass","quality_rule_id":rule.id,"failures":failures}
    assert dbt_result(rule,raw,BASE_CLOCK,"dbt","fingerprint").status=="UNKNOWN"


def test_gx_is_design_only_and_does_not_require_vendor():
    rule=next(r for r in data_contract().rules if r.id=="description_complete")
    assert gx_design(rule)["mapping"]["type"]=="ExpectColumnValuesToNotBeNull"
    assert gx_design(rule)["executed"] is False


client=TestClient(create_app())


def test_api_scenario_validation_and_contract_schemas():
    assert client.get('/api/health').status_code==200
    assert client.get('/api/scenarios').json()[0]['id']==SCENARIO_ID
    assert client.get(f'/api/scenarios/{SCENARIO_ID}').json()['contract']['primary_key']==['order_id']
    value=client.post(f'/api/scenarios/{SCENARIO_ID}/validate',json={"corruptions":["duplicate"]}).json()
    assert value['summary']['FAIL']==2 and value['gate']['status']=='BLOCKED'
    assert client.get('/api/contracts').json()['quality_event']['properties']['status']
    assert client.get('/openapi.json').status_code==200


def test_external_validation_and_single_rule_fail_closed():
    request=scenario_input(ScenarioRequest())
    request.rule_ids=['contract_grain']
    response=client.post('/api/validate',json=request.model_dump(mode='json'))
    assert response.status_code==200 and response.json()['gate']['status']=='BLOCKED'


@pytest.mark.parametrize("payload",[{"corruptions":["bad"]},{"executed_at":"2026-10-02"},{"score":100},
    {"rule_ids":["missing"]},{"run_id":""},{"rule_ids":["contract_grain","contract_grain"]}])
def test_api_rejects_invalid_input_and_scoring_fields(payload):
    assert client.post(f'/api/scenarios/{SCENARIO_ID}/validate',json=payload).status_code==422


def test_additional_rule_cannot_replace_contract_rule():
    rule=data_contract().rules[0]
    response=client.post(f'/api/scenarios/{SCENARIO_ID}/validate',json={'additional_rules':[rule.model_dump(mode='json')]})
    assert response.status_code==422


def test_preview_clock_matches_validation_and_unknown_scenarios():
    preview=client.post(f'/api/scenarios/{SCENARIO_ID}/preview',json={'corruptions':['stale']}).json()
    value=client.post(f'/api/scenarios/{SCENARIO_ID}/validate',json={'corruptions':['stale']}).json()
    assert preview['executed_at']==value['results'][0]['executed_at']
    assert client.get('/api/scenarios/missing').status_code==404


def test_dataset_map_identity_is_validated():
    request=scenario_input(ScenarioRequest()).model_dump(mode='json')
    request['datasets']['fct_orders']['id']='customers'
    assert client.post('/api/validate',json=request).status_code==422
