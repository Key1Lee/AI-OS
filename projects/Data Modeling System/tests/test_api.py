from fastapi.testclient import TestClient

from data_modeling_lab.api import create_app

client = TestClient(create_app())
build_body = {"source_grain": "source_order_version", "grain": "order", "primary_key": ["order_id"]}


def test_scenario_contract_graph_and_schemas():
    scenario = client.get("/api/scenario").json()
    assert len(scenario["sources"]) == 6
    ids = {n["id"] for n in scenario["sources"] + scenario["planned_models"]}
    assert all(set(n["parents"]) <= ids for n in scenario["planned_models"])
    assert all(r["left_model"] in ids and r["right_model"] in ids for r in scenario["relationships"])
    exported = client.get("/api/contracts").json()
    assert exported["contract_version"] == "modeling-lab-v1"
    assert "EvaluationResult" in exported["schemas"]
    assert "scor" not in str(exported["schemas"]).lower()


def test_end_to_end_api_journey():
    declared = client.post("/api/grain", json={"table": "raw_orders", "grain": "source_order_version", "primary_key": ["orderId", "sourceVersion"]})
    assert declared.status_code == 200 and declared.json()["status"] == "pass"
    assert client.post("/api/staging", json={"source_grain": "source_order_version"}).json()["model"]["row_count"] == 4
    joined = client.post("/api/join", json={}).json()
    assert joined["fanout"] and joined["joined_amount"] == "325.00"
    built = client.post("/api/build", json=build_body)
    assert built.status_code == 200 and built.json()["evaluation"]["status"] == "pass"
    metric = client.post("/api/metric", json={"build": build_body}).json()
    assert metric["value"] == "225.00" and metric["status"] == "pass"


def test_grain_and_request_validation_errors_are_structured():
    assert client.post("/api/build", json={}).status_code == 422
    response = client.post("/api/build", json={**build_body, "source_grain": "order"})
    assert response.status_code == 422 and response.json()["error"]["code"] == "grain_required"
    assert client.post("/api/build", json={**build_body, "unexpected": True}).status_code == 422
    assert client.post("/api/join", json={"left_key": "x; DROP TABLE raw_orders"}).status_code == 422
    assert client.post("/api/build", json={**build_body, "sql": "x" * 10001}).status_code == 422


def test_errors_are_recoverable_and_evidence_is_grounded():
    bad = client.post("/api/build", json={**build_body, "sql": "SELECT missing FROM stg_orders"}).json()
    assert bad["evaluation"]["status"] == "fail"
    good = client.post("/api/build", json=build_body).json()
    assert good["evaluation"]["status"] == "pass"
    assert good["evaluation"]["explanation_source"] == "deterministic_evidence"


def test_api_contains_no_provider_credentials_or_sibling_dependencies():
    schema = client.get("/openapi.json").json()
    assert not any("toptal" in path.lower() or "incident" in path.lower() for path in schema["paths"])
    assert client.get("/api/health").json()["execution"] == "local DuckDB"


def test_equivalent_sql_exports_every_actual_parent_and_prepared_view_step():
    built = client.post("/api/build", json={**build_body, "sql": "SELECT o.*, c.name customer_name FROM completed_orders o LEFT JOIN customers c ON o.customer_id=c.customer_id"}).json()
    assert built["evaluation"]["status"] == "pass"
    inputs = {m["id"]: m for m in built["inputs"]}
    assert set(built["fact"]["parents"]) == {"completed_orders", "customers"}
    assert set(built["fact"]["parents"]) <= set(inputs) | {"stg_orders"}
    assert inputs["completed_orders"]["row_count"] == 3
    filter_step = next(s for s in built["transformations"] if s["output_model"] == "completed_orders")
    assert filter_step["input_model"] == "stg_orders" and filter_step["input_rows"] == 4 and filter_step["output_rows"] == 3
