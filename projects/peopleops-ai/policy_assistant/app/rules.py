"""Typed, server-owned mock rules; request text never changes their authority."""
from functools import lru_cache
from pathlib import Path
import re
from typing import Literal

from pydantic import Field, model_validator
import yaml

from app.models import Intent, RuleMatch, Strict


class RuleInfo(Strict):
    id: str = Field(pattern=r"^(BR|RT|SEC)-[A-Z-]+$")
    description: str
    requirements: list[str]


class RoutingRule(RuleInfo):
    intent: Intent
    any_patterns: list[str] = Field(default_factory=list)
    all_patterns: list[str] = Field(default_factory=list)
    personal_patterns: list[str] = Field(default_factory=list)


class BusinessRules(Strict):
    version: Literal[1]
    mock_assumptions: Literal[True]
    minimum_query_coverage: float = Field(ge=.5, le=1)
    max_record_age_days: int = Field(ge=0, le=30)
    rules: list[RuleInfo]


class SecurityPolicies(Strict):
    version: Literal[1]
    mock_assumptions: Literal[True]
    deny_by_default: Literal[True]
    self_permission: Literal["pto:read:self"]
    delegated_permission: Literal["pto:read:delegated"]
    restricted_document_permission: Literal["policy:read:restricted"]
    internal_document_permission: Literal["policy:read:internal"]
    test_runner_permission: Literal["lab:run"]
    rules: list[RuleInfo]


class RoutingRules(Strict):
    version: Literal[1]
    mock_assumptions: Literal[True]
    target_pattern: str
    rules: list[RoutingRule]
    fallback: RoutingRule

    @model_validator(mode="after")
    def valid_patterns(self):
        for pattern in [self.target_pattern, *[p for r in self.rules for p in r.any_patterns+r.all_patterns+r.personal_patterns]]:
            re.compile(pattern, re.I)
        if {r.intent for r in [*self.rules, self.fallback]} != set(Intent):
            raise ValueError("All seven intent contracts must be configured")
        return self


class RuleBook:
    def __init__(self, directory):
        self.business = BusinessRules.model_validate(yaml.safe_load((directory/"business_rules.yaml").read_text()))
        self.security = SecurityPolicies.model_validate(yaml.safe_load((directory/"security_policies.yaml").read_text()))
        self.routing = RoutingRules.model_validate(yaml.safe_load((directory/"routing_rules.yaml").read_text()))
        self.catalog = {}
        for kind, filename, entries in [
            ("business", "business_rules.yaml", self.business.rules),
            ("security", "security_policies.yaml", self.security.rules),
            ("routing", "routing_rules.yaml", [*self.routing.rules, self.routing.fallback]),
        ]:
            for entry in entries:
                if entry.id in self.catalog:
                    raise ValueError("Duplicate governed rule ID")
                self.catalog[entry.id] = (kind, filename, entry)

    def match(self, rule_id, outcome="applied"):
        """Return only safe configured rule metadata for an actual decision."""
        kind, filename, entry = self.catalog[rule_id]
        return RuleMatch(rule_id=rule_id, kind=kind, source="config/"+filename,
                         description=entry.description, outcome=outcome, requirement_ids=entry.requirements)


@lru_cache(maxsize=1)
def default_rules():
    return RuleBook(Path(__file__).resolve().parents[1]/"config")
