from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from data_modeling_lab.api import create_app
from data_modeling_lab.contracts import BuildRequest
from data_modeling_lab.engine import ModelingEngine
from data_modeling_lab.fixtures import fixture_data


@pytest.mark.parametrize("sql", [
    "SELECT " + "(" * 2500 + "1" + ")" * 2500,
    "SELECT * FROM (" * 120 + "SELECT * FROM stg_orders" + ") sub" * 120,
    "SELECT " + "+".join(["1"] * 900),
])
def test_deep_learner_sql_is_a_structured_error_not_http_500(sql):
    with TestClient(create_app()) as client:
        response = client.post("/api/build", json={"source_grain": "source_order_version", "grain": "order", "sql": sql})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "sql_complexity"
        assert client.post("/api/build", json={"source_grain": "source_order_version", "grain": "order"}).json()["evaluation"]["status"] == "pass"


@pytest.mark.parametrize("expression,expected", [
    (r"CAST('\xFF' AS BLOB)", {"type": "binary", "encoding": "hex", "value": "ff"}),
    (r"ARRAY_AGG(CAST('\xFF' AS BLOB)) OVER ()", [{"type": "binary", "encoding": "hex", "value": "ff"}] * 3),
])
def test_binary_and_nested_binary_extra_columns_have_explicit_json_encoding(expression, expected):
    with TestClient(create_app()) as client:
        response = client.post("/api/build", json={"source_grain": "source_order_version", "grain": "order", "sql": f"SELECT *, {expression} payload FROM completed_orders"})
        assert response.status_code == 200
        assert response.json()["evaluation"]["status"] == "pass"
        assert response.json()["fact"]["rows"][0]["payload"] == expected


@pytest.mark.parametrize("reverse", [False, True])
def test_equal_timestamp_instants_cannot_choose_different_order_versions(reverse):
    fixture = deepcopy(fixture_data())
    rows = fixture["tables"]["raw_orders"]["rows"]
    rows[0][6], rows[0][7] = "2026-09-28T18:05:00+09:00", 2
    if reverse:
        rows.reverse()
    with pytest.raises(ValueError, match="Ambiguous source versions"):
        ModelingEngine(fixture=fixture).scenario()


def test_null_parent_keys_do_not_hide_missing_child_relationships():
    fixture = deepcopy(fixture_data())
    fixture["tables"]["customers"]["rows"].append([None, "Unknown", "Unknown"])
    built = ModelingEngine(fixture=fixture).build(BuildRequest(source_grain="source_order_version", grain="order", sql="SELECT order_id, 'missing-customer' customer_id, status, order_amount, currency, ordered_at FROM completed_orders"))
    relationship = next(t for t in built.evaluation.tests if t.id == "relationships")
    assert relationship.status == "fail" and relationship.actual == 3
