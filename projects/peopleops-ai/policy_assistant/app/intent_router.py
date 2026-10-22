"""Deterministic YAML router with an optional structured adapter contract."""
import re
from typing import Protocol

from app.models import Route
from app.rules import default_rules


class IntentRouter(Protocol):
    def route(self, question: str) -> Route: ...


def route_intent(question, rulebook=None):
    """Apply server-owned routing patterns without granting resource access."""
    configured = (rulebook or default_rules()).routing
    target = re.search(configured.target_pattern, question, re.I)
    for rule in configured.rules:
        any_match = not rule.any_patterns or any(re.search(p, question, re.I) for p in rule.any_patterns)
        all_match = all(re.search(p, question, re.I) for p in rule.all_patterns)
        if any_match and all_match:
            return Route(intent=rule.intent, target_employee=target[0].upper() if target else None,
                         personal_review=any(re.search(p, question, re.I) for p in rule.personal_patterns), rule_id=rule.id)
    return Route(intent=configured.fallback.intent, rule_id=configured.fallback.id)


class DeterministicRouter:
    def __init__(self, rulebook=None):
        self.rulebook = rulebook or default_rules()

    def route(self, question):
        return route_intent(question, self.rulebook)
