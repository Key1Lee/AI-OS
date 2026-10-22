from app.intent_router import route_intent
from evals.common import cases, outcome, ratio, summarize


def evaluate_routing():
    results = [outcome(case["id"], route_intent(case["question"]).intent.value == case["expected_intent"]) for case in cases("routing")]
    report = summarize(results)
    report["accuracy"] = ratio(report["passed"], report["total"])
    return report
