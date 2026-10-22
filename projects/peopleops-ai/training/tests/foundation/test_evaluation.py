import json
from pathlib import Path
from lab.evaluate import score


def case():
    return {"kind": "supported", "path": "/api/assistant", "expected_status": 200, "fields": {"status": "answered"},
            "contains": ["160"], "forbidden": [], "expected_citations": [{"policy_id": "PTO", "version": 2, "section_id": "1"}]}


def test_cannot_pass_hallucinated_quote_or_missing_retrieval():
    c = case()
    body = {"status": "answered", "answer": "160 hours", "citations": [{"policy_id": "PTO", "version": 2, "section_id": "1", "quote": "invented 160"}]}
    result = score(c, 200, body, {("PTO", 2, "1"): "Receive 160 hours."})
    assert result["outcome"] == "failed" and result["citation_valid"] == 0 and result["retrieval_recall_at_3"] == 0


def test_blocked_is_not_passed():
    assert score(case(), 501, {"status": "exercise_pending", "exercise": "E06"}, {})["outcome"] == "blocked"


def test_leak_fails_even_when_http_status_is_correct():
    c = dict(case(), kind="unauthorized", expected_status=403, fields={}, contains=[], expected_citations=[], forbidden=["private-value"])
    result = score(c, 403, {"detail": "private-value"}, {})
    assert result["outcome"] == "failed" and result["leakage"] and result["authorization_failure"]


def test_dataset_has_diverse_unique_scenarios():
    rows = json.loads((Path(__file__).resolve().parents[2] / "fixtures" / "evaluations.json").read_text())
    assert len(rows) >= 30 and len({r["id"] for r in rows}) == len(rows)
    assert {"supported", "unsupported", "ambiguous", "malicious", "unauthorized", "confirmation"} <= {r["kind"] for r in rows}
