from __future__ import annotations

import json
from types import SimpleNamespace as NS
import unittest

from py_dev.budget import CloudCallBudget
from py_dev.decisions import DecisionAnswer, DecisionQuestion, DecisionRequest, DecisionService, validate_answers
from py_dev.providers.jev import JevProvider


def request():
    return DecisionRequest("observability", "incident-001", {"pipeline": "SUCCESS", "revenue_change_pct": 38,
        "quality": "WARN", "lineage": ["orders", "revenue", "dashboard"], "historical_normal_pct": [-5, 5]}, {
        "severity": DecisionQuestion("choice", "Classify severity of supplied evidence", ("LOW", "MEDIUM", "HIGH", "CRITICAL"), "incident-v1"),
        "route": DecisionQuestion("choice", "Choose incident owner", ("DATA_ENGINEERING", "ANALYTICS", "PLATFORM", "HUMAN_REVIEW"), "incident-v1"),
        "risk": DecisionQuestion("score", "Rate incident risk", ("low", "medium", "high", "critical"), "incident-v1"),
        "escalate": DecisionQuestion("noul", "Does this warrant human escalation?", version="incident-v1")})


def sdk_response():
    return NS(model="jev-pinned", usage={"input_tokens": 120, "output_tokens": 12}, answers={
        "severity": NS(type="choice", choice="HIGH", confidence=.9, probabilities={"LOW": .01, "MEDIUM": .04, "HIGH": .9, "CRITICAL": .05}),
        "route": NS(type="choice", choice="DATA_ENGINEERING", confidence=.9, probabilities={"DATA_ENGINEERING": .9, "ANALYTICS": .04, "PLATFORM": .01, "HUMAN_REVIEW": .05}),
        "risk": NS(type="score", score=2.0, confidence=.9, legend={0:"low",1:"medium",2:"high",3:"critical"}, probabilities={0:0,1:.1,2:.8,3:.1}),
        "escalate": NS(type="noul", noul=.95)})


class FakeSDK:
    def __init__(self, response=None):
        self.response = response or sdk_response()
        self.calls = []
    def system_one(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def service(sdk=None, *, limit=2, sink=None):
    sdk = sdk or FakeSDK()
    return DecisionService(JevProvider("jev-pinned", sdk), enabled=True,
                           budget=CloudCallBudget(limit), audit_sink=sink or (lambda event: None)), sdk


class DecisionTests(unittest.TestCase):
    def test_incident_typed_fixture_requires_review(self):
        events=[]
        runtime, sdk = service(sink=events.append)
        result = runtime.decide(request(), policy=lambda answers: "REVIEW" if answers["escalate"].selected >= .8 else "ALLOW")
        self.assertEqual((result.status, result.branch), ("JUDGED", "REVIEW"))
        self.assertEqual(result.answers["severity"].selected, "HIGH")
        self.assertEqual(result.answers["route"].selected, "DATA_ENGINEERING")
        self.assertEqual(result.answers["risk"].selected, 2)
        self.assertIsNone(result.answers["escalate"].confidence)
        self.assertEqual(len(sdk.calls),1)
        self.assertEqual(sdk.calls[0]["questions"]["risk"]["criteria"], ["low", "medium", "high", "critical"])
        self.assertNotIn("state", events[0])
        self.assertNotIn("Classify severity", json.dumps(events))

    def test_false_success_deterministic_failure_precedes_jev(self):
        runtime, sdk=service()
        result=runtime.decide(request(), deterministic_checks={"records":1000 == 700}, policy=lambda _:"ALLOW")
        self.assertEqual((result.status,result.branch),("REJECTED","DENY"))
        self.assertEqual(sdk.calls,[])

    def test_deterministic_success_does_not_call_jev(self):
        runtime,sdk=service()
        self.assertEqual(runtime.decide(request(), deterministic_checks={"rows":True}).status,"VERIFIED")
        self.assertEqual(sdk.calls,[])

    def test_high_risk_without_human_approval_does_not_call_provider(self):
        runtime,sdk=service()
        self.assertEqual(runtime.decide(request(),high_risk=True,policy=lambda _:"ALLOW").branch,"REVIEW")
        self.assertEqual(sdk.calls,[])

    def test_low_confidence_overrides_allow_policy(self):
        raw=sdk_response();raw.answers["severity"].confidence=.3
        runtime,_=service(FakeSDK(raw))
        self.assertEqual(runtime.decide(request(),policy=lambda _:"ALLOW").branch,"REVIEW")

    def test_uncertain_noul_stays_review(self):
        raw=sdk_response();raw.answers["escalate"].noul=.5
        runtime,_=service(FakeSDK(raw))
        self.assertEqual(runtime.decide(request(),policy=lambda _:"ALLOW").branch,"REVIEW")

    def test_jev_error_or_exhausted_budget_stays_review(self):
        for sdk,limit in ((FakeSDK(TimeoutError("secret")),2),(FakeSDK(),0)):
            with self.subTest(limit=limit):
                runtime,_=service(sdk,limit=limit)
                result=runtime.decide(request(),policy=lambda _:"ALLOW")
                self.assertEqual((result.status,result.branch),("UNAVAILABLE","REVIEW"))
                self.assertNotIn("secret",str(result))

    def test_private_never_sends_state_to_jev(self):
        from dataclasses import replace
        runtime,sdk=service()
        self.assertEqual(runtime.decide(replace(request(),private=True)).status,"UNAVAILABLE")
        self.assertEqual(sdk.calls,[])

    def test_invalid_primitive_rejected(self):
        for kind in ("generate", "code", "prose"):
            with self.assertRaises(ValueError):
                DecisionQuestion(kind,"x").validate()

    def test_adversarial_sdk_values_fail_closed(self):
        mutations=[lambda r:setattr(r.answers["escalate"],"noul",float("nan")),
                   lambda r:setattr(r.answers["risk"],"score",4),
                   lambda r:setattr(r.answers["severity"],"choice","OTHER"),
                   lambda r:setattr(r.answers["severity"],"confidence",1.1),
                   lambda r:r.answers["severity"].probabilities.update(HIGH=.1),
                   lambda r:setattr(r,"model","other-model"),
                   lambda r:r.answers.pop("escalate"),
                   lambda r:r.answers["risk"].legend.update({2:"silently changed"})]
        for mutation in mutations:
            raw=sdk_response();mutation(raw)
            runtime,_=service(FakeSDK(raw))
            with self.subTest(mutation=mutation):
                self.assertEqual(runtime.decide(request(),policy=lambda _:"ALLOW").status,"UNAVAILABLE")

    def test_audit_failure_blocks_action(self):
        def failed(event): raise OSError()
        runtime,_=service(sink=failed)
        self.assertEqual(runtime.decide(request(),policy=lambda _:"ALLOW").branch,"REVIEW")

    def test_per_run_attempt_limit_counts_failed_calls(self):
        runtime,sdk=service(FakeSDK(TimeoutError()))
        self.assertEqual(runtime.decide(request()).status,"UNAVAILABLE")
        self.assertEqual(runtime.decide(request()).status,"UNAVAILABLE")
        self.assertEqual(len(sdk.calls),1)


if __name__=="__main__":
    unittest.main()
