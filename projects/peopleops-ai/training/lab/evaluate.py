"""Deterministic API regression harness. Blocked != passed; no model grader."""
import argparse
import json
from pathlib import Path
import statistics
import time
import httpx
from lab.config import Settings
from lab.fixtures import load

ROOT = Path(__file__).resolve().parent.parent


def score(case, status, body, policies):
    if status == 501 and body.get("status") == "exercise_pending":
        return {"outcome": "blocked", "reason": body.get("exercise")}
    serialized = json.dumps(body).lower()
    leakage = any(value.lower() in serialized for value in case["forbidden"])
    correct = status == case["expected_status"] and all(body.get(k) == v for k, v in case["fields"].items())
    correct = correct and all(value.lower() in str(body.get("answer", "")).lower() for value in case["contains"])
    expected = case["expected_citations"]
    citations = body.get("citations", [])
    citation_validity = []
    for citation in citations:
        key = (citation.get("policy_id"), citation.get("version"), citation.get("section_id"))
        quote = citation.get("quote", "")
        citation_validity.append(bool(quote) and key in policies and quote in policies[key])
    covered = sum(any(all(c.get(k) == v for k, v in wanted.items()) and valid for c, valid in zip(citations, citation_validity)) for wanted in expected)
    recall = None
    if expected:
        wanted_ids = {f"{c['policy_id']}:{c['version']}:{c['section_id']}:0" for c in expected}
        recall = len(wanted_ids.intersection(body.get("retrieved_ids", [])[:3])) / len(wanted_ids)
        correct = correct and covered == len(expected) and bool(citations) and all(citation_validity)
    if case["kind"] in {"unsupported", "malicious", "ambiguous"} and case["path"] == "/api/assistant":
        correct = correct and not citations
    return {"outcome": "passed" if correct and not leakage else "failed", "correct": bool(correct), "leakage": leakage,
            "authorization_failure": case["kind"] in {"unauthorized", "unauthenticated"} and (status != case["expected_status"] or leakage),
            "retrieval_recall_at_3": recall, "citation_valid": sum(citation_validity), "citation_total": max(len(citations), len(expected)),
            "expected_citation_coverage": covered / len(expected) if expected else None}


def evaluate(client):
    cases = json.loads((ROOT / "fixtures" / "evaluations.json").read_text())
    identities = client.get("/lab/identities")
    identities.raise_for_status()
    tokens = {row["role"]: row["token"] for row in identities.json()}
    policies = {(p["policy_id"], p["version"], s["section_id"]): s["body"] for p in load()["policies"] for s in p["sections"]}
    results = []
    for case in cases:
        start = time.perf_counter()
        try:
            response = client.request(case["method"], case["path"], json=case["payload"],
                                      headers={"Authorization": "Bearer " + tokens[case["role"]]} if case["role"] else {})
            body = response.json()
            result = score(case, response.status_code, body if isinstance(body, dict) else {}, policies)
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            result = {"outcome": "failed", "error_type": type(exc).__name__}
        results.append({"id": case["id"], "kind": case["kind"], "latency_ms": round((time.perf_counter()-start)*1000, 2), **result})
    executed = [r for r in results if r["outcome"] != "blocked"]
    recalls = [r["retrieval_recall_at_3"] for r in executed if r.get("retrieval_recall_at_3") is not None]
    citation_total = sum(r.get("citation_total", 0) for r in executed)
    summary = {"total": len(results), "executed": len(executed), "blocked": len(results)-len(executed),
               "passed": sum(r["outcome"] == "passed" for r in results), "failed": sum(r["outcome"] == "failed" for r in results),
               "coverage": len(executed)/len(results), "pass_fraction_total": sum(r["outcome"] == "passed" for r in results)/len(results),
               "correctness_executed": sum(r.get("correct", False) for r in executed)/len(executed) if executed else None,
               "retrieval_recall_at_3": statistics.mean(recalls) if recalls else None,
               "citation_accuracy": sum(r.get("citation_valid", 0) for r in executed)/citation_total if citation_total else None,
               "authorization_failures": sum(r.get("authorization_failure", False) for r in executed),
               "privacy_leaks": sum(r.get("leakage", False) for r in executed)}
    return {"summary": summary, "results": results, "limitations": "Small synthetic regression set. Blocked cases do not establish safety or quality; correctness is deterministic assertions, not semantic adjudication."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-blocked", action="store_true", help="Foundation smoke only; still exits nonzero for actual failures")
    parser.add_argument("--output", default="reports/evaluation.json")
    args = parser.parse_args()
    with httpx.Client(base_url=Settings().api_url, timeout=25) as client:
        report = evaluate(client)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))
    raise SystemExit(1 if report["summary"]["failed"] or (report["summary"]["blocked"] and not args.allow_blocked) else 0)
