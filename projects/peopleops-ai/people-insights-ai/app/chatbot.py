"""A small deterministic conversation handler with principal-bound session memory."""

import re
from collections import OrderedDict
from threading import RLock
from time import monotonic

from .analytics import METRICS

ALIASES = {
    "Sales": r"\bsales\b",
    "Research & Development": r"\b(?:research\s*(?:&|and)\s*development|r\s*&\s*d|r\s+and\s+d)\b",
    "Human Resources": r"\b(?:human resources|hr)\b",
}
METRIC_ALIASES = {
    "job_satisfaction": r"\b(?:job satisfaction|satisfaction|satisfied)\b",
    "work_life_balance": r"\b(?:work[ -]life(?: balance)?|wlb)\b",
    "attrition": r"\b(?:attrition|turnover|departures)\b",
    "overtime": r"\b(?:overtime|over time)\b",
    "engagement": r"\b(?:engagement|ex25)\b",
}
DEFAULT_METRICS = ["job_satisfaction", "work_life_balance"]


def unrecognized_words(text):
    """Detect unrecognized names or metrics rather than silently reusing old parameters."""
    remainder = text
    for pattern in [*ALIASES.values(), *METRIC_ALIASES.values()]:
        remainder = re.sub(pattern, " ", remainder)
    generic = r"\b(give|me|the|an|a|employee|employees|experience|happiness|happy|report|reports|show|can|you|please|what|about|compare|comparison|it|with|and|versus|vs|which|department|departments|has|have|is|are|lowest|highest|all|both|full|for|in|of|ibm|qualtrics|score|scores|metric|metrics|on|my|our|us|let|see|how|does|to|summarize|summarise|summary|analysis|analyze|analyse|snapshot|favorable|favourable|observed|working|i|want|would|like)\b"
    remainder = re.sub(generic, " ", remainder)
    return re.findall(r"[a-z]+", remainder)


class SessionStore:
    """Keep bounded, expiring conversation state isolated by the server-resolved principal."""

    def __init__(self):
        self.items = OrderedDict()
        self.lock = RLock()

    def get(self, owner, session):
        now = monotonic()
        for key in list(self.items):
            if now - self.items[key]["updated"] > 1800:
                del self.items[key]
        key = (owner, session)
        if key not in self.items:
            if len(self.items) >= 256:
                self.items.popitem(last=False)
            self.items[key] = {
                "departments": [],
                "metrics": [],
                "pending": None,
                "source": "ibm",
                "last_report": None,
                "updated": now,
            }
        self.items.move_to_end(key)
        self.items[key]["updated"] = now
        return self.items[key]


def reply(status, message, options=None, report=None):
    return {
        "status": status,
        "message": message,
        "options": options or [],
        "report": report,
    }


def handle_chat(message, state, allowed, make_report, imported_available=False):
    """Resolve departments and metrics, ask one missing question, then call deterministic scoring."""
    text = message.lower().strip().rstrip(".!?")
    if re.search(
        r"\b(trend|historical|quarterly|monthly|last \d+ months|predict|prediction|forecast)\b",
        text,
    ):
        return reply(
            "unsupported",
            "The IBM sample is a single snapshot with no survey dates. I can report observed scores, but cannot provide historical trends or predict resignations.",
        )
    if re.search(
        r"\b(salary|payroll|individual|employee number|employee records|select |drop table|ignore .*instructions)\b",
        text,
    ):
        return reply(
            "unsupported",
            "I provide approved department aggregates only. Individual records, payroll and arbitrary queries are not supported.",
        )
    if re.search(r"\b(download|export|csv)\b", text):
        if state["last_report"]:
            return reply(
                "report",
                "Your displayed aggregate report is ready to download as CSV.",
                report=state["last_report"],
            )
        return reply(
            "clarification",
            "Which department would you like to analyze before downloading?",
            list(allowed),
        )
    source = (
        "qualtrics"
        if "qualtrics" in text
        else "ibm"
        if "ibm" in text
        else state["source"]
    )
    if source == "qualtrics" and not imported_available:
        return reply(
            "unsupported",
            "Genuine Qualtrics data is not connected. The IBM sample provides job satisfaction and work-life balance proxies, not an official Qualtrics engagement or EX25 score. An administrator can demonstrate the separate synthetic aggregate CSV import.",
        )
    explicit_departments = [
        name for name, pattern in ALIASES.items() if re.search(pattern, text)
    ]
    metrics = [
        key for key, pattern in METRIC_ALIASES.items() if re.search(pattern, text)
    ]
    if "all metrics" in text or "full report" in text:
        metrics = list(METRICS)
    elif re.search(r"\bboth\b", text):
        metrics = DEFAULT_METRICS.copy()
    if source == "ibm" and "engagement" in metrics:
        return reply(
            "unsupported",
            "Engagement and EX25 are not measured in the IBM sample. Choose job satisfaction or work-life balance; I will label them as sample proxies.",
            DEFAULT_METRICS,
        )
    if unrecognized_words(text):
        return reply(
            "clarification",
            "I could not match that department or metric. Choose a supported department, or ask for job satisfaction, work-life balance, attrition or overtime.",
            list(allowed),
        )
    if re.search(
        r"\b(marketing|finance|engineering|operations|support|atlantis|legal)\b", text
    ):
        return reply(
            "clarification",
            "That department is not in the IBM sample. Choose Sales, Research & Development, or Human Resources.",
            list(allowed),
        )
    compare = bool(re.search(r"\b(compare|comparison|versus|vs)\b", text))
    ranking = bool(re.search(r"\b(lowest|highest|all departments)\b", text))
    departments = explicit_departments or state["departments"].copy()
    if ranking:
        departments = list(allowed)
    elif compare and explicit_departments and len(explicit_departments) == 1:
        departments = list(dict.fromkeys(state["departments"] + explicit_departments))
    if any(name not in allowed for name in departments):
        return reply(
            "error",
            "This demo identity is not authorized for the requested department. No scores were returned.",
        )
    if not departments:
        state["metrics"] = metrics
        state["pending"] = "department"
        state["source"] = source
        return reply(
            "clarification",
            "Which department would you like to analyze?",
            list(allowed),
        )
    if compare and len(departments) < 2:
        state["departments"] = departments
        state["metrics"] = metrics or state["metrics"]
        state["pending"] = "comparison"
        return reply(
            "clarification",
            "Which second department would you like to compare?",
            [name for name in allowed if name not in departments],
        )
    if state["pending"] == "comparison" and explicit_departments:
        departments = list(dict.fromkeys(state["departments"] + explicit_departments))
    selected_metrics = metrics or state["metrics"].copy()
    if not selected_metrics:
        # A direct happiness request has a useful two-metric default. A missing-
        # department conversation explicitly asks its second question after selection.
        if state["pending"] != "department" and (
            re.search(r"\b(happiness|happy|report|compare|comparison)\b", text)
        ):
            selected_metrics = DEFAULT_METRICS.copy()
        else:
            state.update(departments=departments, pending="metrics", source=source)
            return reply(
                "clarification",
                "Would you like job satisfaction, work-life balance, or both?",
                ["Job satisfaction", "Work-life balance", "Both"],
            )
    # Unrecognized follow-ups must not silently repeat an old report.
    recognized = (
        explicit_departments
        or metrics
        or compare
        or ranking
        or re.search(r"\b(happiness|happy|report|both|qualtrics|ibm)\b", text)
    )
    if not recognized:
        return reply(
            "unsupported",
            "I can report job satisfaction, work-life balance, observed attrition and overtime for the three sample departments. Please name a department or metric.",
        )
    try:
        report = make_report(departments, selected_metrics, source)
    except ValueError as error:
        return reply("unsupported", str(error))
    state.update(
        departments=departments,
        metrics=selected_metrics,
        pending=None,
        source=source,
        last_report=report,
    )
    return reply(
        "report",
        "Here is your employee-experience report. All values come from the labeled source.",
        report=report,
    )
