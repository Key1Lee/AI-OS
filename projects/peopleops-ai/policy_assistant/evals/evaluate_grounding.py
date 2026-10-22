import json
from app.workday_client import MockWorkdayClient, MockWorkdayTransport
from evals.common import cases, outcome, ratio, summarize


def citation_valid(citation, sources):
    """Check exact quoted text against source fixtures, not citation existence alone."""
    document = sources.get((citation.get("document_id"), citation.get("version")))
    return bool(document and citation.get("quote") and citation["quote"] in document["text"] and citation.get("title") == document["title"])


def request_case(client, settings, case):
    transport = MockWorkdayTransport(scenario=case.get("fault", "normal"), database_path=settings.database_path)
    client.app.state.orchestrator.workday = MockWorkdayClient(settings, transport, sleep=lambda _: None)
    response = client.post("/ask", headers={"Authorization": "Bearer demo-" + case["actor"]}, json={"question": case["question"], **case.get("overrides", {})})
    return response, transport.calls


def evaluate_grounding(client, settings):
    sources = {}
    for line in (settings.fixture_root / "documents/policies.jsonl").read_text().splitlines():
        doc = json.loads(line)
        if "version" in doc:
            sources[(doc["document_id"], doc["version"])] = doc
    rows = []
    valid_citations = citation_count = support = policy_answers = pto_exact = pto_count = abstained = abstention_count = fact_hits = fact_count = 0
    for case in cases("grounding"):
        response, calls = request_case(client, settings, case)
        data = response.json()
        citations = data.get("citations", [])
        actual_docs = {c["document_id"] for c in citations}
        correct = response.status_code == 200 and data.get("status") == case["expected_status"]
        correct &= set(case.get("expected_documents", [])) <= actual_docs
        facts = case.get("expected_facts", {})
        facts_ok = all(data.get("facts", {}).get(key) == value for key, value in facts.items())
        fact_hits += sum(fact in data.get("answer", "") for fact in case.get("accepted_facts", []))
        fact_count += len(case.get("accepted_facts", []))
        correct &= facts_ok and all(fact in data.get("answer", "") for fact in case.get("accepted_facts", []))
        if facts:
            pto_count += 1
            pto_exact += facts_ok and data.get("status") == "answered"
        if case["expected_status"] in ("abstained", "clarify", "escalated", "refused"):
            abstention_count += 1
            abstained += data.get("status") == case["expected_status"]
        for citation in citations:
            citation_count += 1
            valid_citations += citation_valid(citation, sources)
        if data.get("status") == "answered" and citations:
            policy_answers += 1
            exact = data["answer"] == "Approved fictional policy excerpt:\n\n[1] " + citations[0]["quote"] and all(citation_valid(c, sources) for c in citations)
            support += exact
            correct &= exact
        rows.append(outcome(case["id"], correct, actual_status=data.get("status"), tool_calls=calls))
    report = summarize(rows)
    report.update({"correctness": ratio(report["passed"], report["total"]), "citation_validity": ratio(valid_citations, citation_count),
        "extractive_support": ratio(support, policy_answers), "unsupported_policy_answers": policy_answers - support,
        "pto_exactness": ratio(pto_exact, pto_count), "appropriate_abstention": ratio(abstained, abstention_count),
        "accepted_fact_coverage": ratio(fact_hits, fact_count),
        "evaluator_limit": "Exact source support and labeled facts only; not a comprehensive semantic groundedness or completeness judgment"})
    return report
