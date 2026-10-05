from collections import Counter
from copy import deepcopy

from lab.adapters.modeling import NativeModelingAdapter
from lab.adapters.orchestration import NativeOrchestrationAdapter
from lab.fixtures import commerce, revenue


def test_native_modeling_uses_custom_source_and_preserves_duplicate_output():
    source = commerce(7)["orders"][:3]
    source[0]["order_id"], source[0]["order_amount"] = "CUSTOM-ORDER-A", "45.01"
    source[1]["order_id"], source[1]["order_amount"] = "CUSTOM-ORDER-B", "12.34"
    source[2]["order_id"], source[2]["order_amount"] = "CUSTOM-ORDER-C", "0.29"
    original = deepcopy(source)
    adapter = NativeModelingAdapter()
    healthy = adapter.build(source, source, "model-custom-healthy")
    assert healthy["status"] == "PASS"
    assert healthy["row_count"] == 3
    assert healthy["rows"] == source
    assert healthy["revenue"] == "57.64"
    assert "ModelingEngine.build" in healthy["provenance"]
    assert "loaded_orders" in healthy["sql"]
    assert all(bundle["evaluation"]["output_matches_expected"] for bundle in healthy["results"])
    assert source == original

    loaded = source + source[:2]
    corrupt = adapter.build(loaded, source, "model-custom-corrupt")
    assert corrupt["status"] == "FAIL"
    assert corrupt["row_count"] == 5
    assert Counter(row["order_id"] for row in corrupt["rows"]) == Counter(row["order_id"] for row in loaded)
    assert corrupt["revenue"] == revenue(loaded) == "114.99"
    tests = {test["id"]: test for test in corrupt["results"][0]["evaluation"]["tests"]}
    assert tests["unique_key"]["status"] == "fail"
    assert tests["unique_key"]["actual"] == 2
    assert tests["expected_output"]["status"] == "fail"
    assert tests["row_count"]["expected"] == 3
    assert tests["row_count"]["actual"] == 5


def test_native_model_golden_reference_detects_wrong_amount_with_unique_keys():
    source = commerce()["orders"][:2]
    loaded = deepcopy(source)
    loaded[0]["order_amount"] = "99.99"
    result = NativeModelingAdapter().build(loaded, source, "model-wrong-amount")
    tests = {test["id"]: test for test in result["results"][0]["evaluation"]["tests"]}
    assert result["status"] == "FAIL"
    assert tests["unique_key"]["status"] == "pass"
    assert tests["row_count"]["status"] == "pass"
    assert tests["expected_output"]["status"] == "fail"
    assert result["revenue"] != revenue(source)


def test_native_orchestration_retries_the_declared_transient_failure():
    adapter = NativeOrchestrationAdapter()
    retry = adapter.schedule("contract-native-retry", 37)
    assert retry["status"] == "SUCCESS"
    assert [attempt["status"] for attempt in retry["attempts"]] == ["FAILED", "SUCCESS"]
    assert retry["attempts"][0]["error"]["type"] == "transient"
    assert "37 committed rows" in retry["attempts"][0]["error"]["message"]
    assert retry["attempts"][1]["start_minute"] > retry["attempts"][0]["end_minute"]
    assert any(event["status"] == "RETRYING" for event in retry["events"])
    assert all(event["contract_version"] == "orchestration-event-v1" and event["run_id"] == "contract-native-retry"
               for event in retry["events"])
    assert "actual rows measured by Lab" in retry["provenance"]
    baseline = adapter.schedule("contract-native-baseline", None)
    assert baseline["status"] == "SUCCESS"
    assert len(baseline["attempts"]) == 1
    assert baseline["attempts"][0]["status"] == "SUCCESS"
    assert not any(event["status"] == "RETRYING" for event in baseline["events"])


def test_native_model_detects_offsetting_wrong_values_with_correct_total():
    source = commerce()["orders"][:2]
    loaded = deepcopy(source)
    from decimal import Decimal
    loaded[0]["order_amount"] = str(Decimal(loaded[0]["order_amount"]) + Decimal("1.00"))
    loaded[1]["order_amount"] = str(Decimal(loaded[1]["order_amount"]) - Decimal("1.00"))
    result = NativeModelingAdapter().build(loaded, source, "model-offsetting-amounts")
    assert result["revenue"] == revenue(source)
    assert result["status"] == "FAIL"
    assert any(test["id"] == "expected_output" and test["status"] == "fail"
               for bundle in result["results"] for test in bundle["evaluation"]["tests"])
