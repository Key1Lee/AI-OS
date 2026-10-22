import re

RULES = {
    "payroll": ({"payroll", "pay", "paycheck", "payslip", "deposit", "salary", "tax"}, "Payroll"),
    "benefits": ({"benefit", "benefits", "insurance", "enrollment", "health", "dental"}, "Benefits"),
    "leave": ({"vacation", "pto", "leave", "holiday", "time off"}, "People Operations"),
    "onboarding": ({"onboarding", "orientation", "equipment", "laptop", "new hire"}, "People Operations"),
    "employee_relations": ({"harassment", "discrimination", "grievance", "complaint", "bullying"}, "People Partner"),
}


def route_request(text: str) -> dict:
    text = text.lower()
    matches = {category: sum(bool(re.search(r"\b" + re.escape(term) + r"\b", text)) for term in words)
               for category, (words, _) in RULES.items()}
    # Sensitive reports always go to a human People Partner.
    if matches["employee_relations"]:
        return dict(category="employee_relations", team="People Partner", confidence=1.0, needs_human=True)
    best = max(matches, key=matches.get)
    if not matches[best] or sum(score == matches[best] for score in matches.values()) > 1:
        return dict(category="general", team="HR Triage", confidence=0.0, needs_human=True)
    return dict(category=best, team=RULES[best][1], confidence=0.85, needs_human=False)
