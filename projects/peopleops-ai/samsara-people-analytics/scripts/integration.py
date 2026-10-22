"""Live integration checks. Requires the project's Compose services to be up."""
import importlib.util
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("DEMO_URL", "http://localhost:3000")
WEBHOOK = os.environ.get("DEMO_WEBHOOK", "http://localhost:5678/webhook/samsara-survey")
spec = importlib.util.spec_from_file_location("reference", ROOT / "scripts/verify.py")
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)


def request(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=85) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def main():
    examples = ["What was everyone's company survey score at Samsara over the last three years?",
                "Compare Engineering & Product and Sales engagement scores in 2025.",
                "Did engagement increase between 2024 and 2026?",
                "How is the engagement score calculated?",
                "What was the company-wide survey response rate?"]
    status, snapshot = request(BASE + "/api/mock-qualtrics/responses")
    assert status == 200 and snapshot["synthetic"] is True
    assert ref.checksum({"responses": snapshot["responses"], "headcount": snapshot["headcount"]}) == snapshot["sourceChecksum"]
    assert len(json.dumps(snapshot).encode()) > 1_000_000, "Exercise the scaled snapshot across the old payload limit"
    for year in (2024, 2025, 2026):
        cohorts = [c for c in snapshot["headcount"] if c["SurveyYear"] == year]
        assert len(cohorts) == 5 and sum(c["EligibleEmployees"] for c in cohorts) == 5000
    receipts = []
    for question in examples:
        status, result = request(BASE + "/api/chat", {"question": question})
        assert status == 200, result
        assert result["validation"]["status"] == "PASS", result
        assert result["orchestration"]["mode"] == "n8n" and result["orchestration"]["executionId"]
        plan, report = result["plan"], result["report"]
        expected = ref.reference(snapshot, plan["years"], plan["departments"])
        assert ref.close(report, expected), question
        assert result["validation"]["sourceChecksum"] == snapshot["sourceChecksum"]
        assert result["validation"]["recordsRetrieved"] == len(snapshot["responses"])
        assert result["validation"]["validRecordsUsed"] == report["overall"]["validRespondents"]
        assert all(c["pass"] for c in result["validation"]["comparisons"])
        assert result["references"]
        assert result["ai"]["provider"] == "qwen_local"
        assert result["ai"]["interpretation"]["inputTokens"] > 0
        assert result["ai"]["answer"]["outputTokens"] > 0
        if plan["metric"] == "definition":
            assert result["references"][0]["document"] == "engagement_score_definition.md"
            assert "QID1 + QID2 + QID3" in result["answer"]
        elif question.startswith("Compare"):
            for department in report["departments"]:
                assert f"{department['score']:.2f}" in result["answer"]
        elif question.startswith("Did"):
            assert f"{report['trend']['change']:.2f}" in result["answer"]
        else:
            for annual in report["annual"]:
                value = annual["responseRate"] if plan["metric"] == "responseRate" else annual["score"]
                assert f"{value:.2f}" in result["answer"]
        from urllib.parse import urlencode
        query = urlencode({"years": ",".join(map(str, plan["years"])), "departments": ",".join(plan["departments"])})
        status, dashboard = request(BASE + "/api/report?" + query)
        assert status == 200 and ref.close(dashboard["report"], report), "Chat/dashboard discrepancy"
        receipts.append({"question": question, "execution": result["orchestration"], "ai": result["ai"], "validation": result["validation"], "report": report, "answer": result["answer"]})
        print(f"PASS n8n #{result['orchestration']['executionId']}: {question}")
    status, direct = request(WEBHOOK, {"question": examples[0]})
    assert status == 200 and direct["validation"]["status"] == "PASS", direct
    status, invalid = request(WEBHOOK, {"question": "Finance engagement in 2025"})
    assert status == 400 and invalid["error"], invalid
    for invalid_question in ["Finance engagement in 2025", "survey score in 2023", "individual employee survey score"]:
        status, result = request(BASE + "/api/chat", {"question": invalid_question})
        assert status == 400 and result["validation"]["status"] == "NOT VERIFIED"
    assert request(BASE + "/api/report?departments=Finance")[0] == 422
    assert request(BASE + "/api/report?years=2023")[0] == 422
    status, missing = request(BASE + "/api/metrics", {"plan": {"years": [2025], "departments": ["Sales"]}, "snapshot": {"responses": [], "headcount": snapshot["headcount"]}})
    assert status == 422 and "No survey records" in missing["error"]
    changed = {"responses": snapshot["responses"][1:], "headcount": snapshot["headcount"]}
    status, mismatched = request(BASE + "/api/metrics", {"plan": {"years": [2025], "departments": ["Sales"]}, "snapshot": changed})
    assert status == 409 and mismatched["validation"]["status"] == "FAIL" and mismatched["report"] is None
    status, filtered = request(BASE + "/api/chat", {"question": examples[0], "filters": {"years": [2026], "departments": ["Customer Success & Support"]}})
    assert status == 200 and filtered["report"]["overall"]["eligibleEmployees"] == 1000
    assert filtered["validation"]["status"] == "PASS"
    department_receipts = []
    for department in ref.DEPARTMENTS:
        question = f"What was {department} engagement in 2026?"
        status, scoped = request(BASE + "/api/chat", {"question": question})
        assert status == 200 and scoped["validation"]["status"] == "PASS", scoped
        assert scoped["plan"]["departments"] == [department]
        expected = ref.reference(snapshot, [2026], [department])
        assert ref.close(scoped["report"], expected)
        department_receipts.append({"department": department, "execution": scoped["orchestration"], "report": scoped["report"], "validation": scoped["validation"]})
        print(f"PASS n8n #{scoped['orchestration']['executionId']}: {department}")
    evidence = {"timestamp": datetime.now(timezone.utc).isoformat(), "status": "PASS", "baseUrl": BASE, "questions": receipts, "departmentQuestions": department_receipts,
                "checks": ["five real n8n executions", "independent Python reconciliation", "chat/dashboard parity", "direct webhook", "invalid input rejected", "missing data rejected", "changed dataset blocked", "filter execution verified"]}
    (ROOT / "evidence/integration.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("PASS live workflow, endpoint errors, source checksums and chat/dashboard parity.")


if __name__ == "__main__":
    main()
