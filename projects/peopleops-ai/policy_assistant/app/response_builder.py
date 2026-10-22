from app.models import HRResponse, SourceCitation


def simple_response(status, intent, message, escalation=None):
    return HRResponse(status=status, intent=intent, answer=message, escalation=escalation)


def record_response(record, intent, self_service=True):
    """Format only the exact source value, unit and effective date, without model generation."""
    value = format(record.pto_balance, "f")
    subject = "Your" if self_service else "The requested"
    return HRResponse(status="answered", intent=intent,
                      answer=f"{subject} synthetic PTO balance is {value} {record.unit}, as of {record.as_of_date.isoformat()} (mock Workday).",
                      facts={"pto_balance": value, "unit": record.unit, "as_of_date": record.as_of_date.isoformat(), "source_system": record.source_system})


def policy_response(question, passages, intent, minimum_coverage=0.8):
    """Abstain on inadequate/conflicting evidence; otherwise quote only the selected approved source."""
    adequate = [p for p in passages if p["query_coverage"] >= minimum_coverage]
    if not adequate:
        response = simple_response("abstained", intent, "I do not have enough current, authorized policy evidence. Contact People Operations.")
        response.failure_code = "insufficient_evidence"
        return response
    claims = {}
    for passage in adequate:
        meta = passage["metadata"]
        for fact, value in meta["facts"].items():
            key = (meta["policy_key"], fact)
            if key in claims and claims[key] != value:
                response = simple_response("abstained", intent, "The current authorized sources conflict. People Operations needs to resolve the policy before I can answer.")
                response.failure_code = "conflicting_evidence"
                return response
            claims[key] = value
    # One strongest complete passage keeps the answer bounded and checkable.
    passage = adequate[0]
    meta = passage["metadata"]
    citation = SourceCitation(document_id=meta["document_id"], policy_id=meta["document_id"], title=meta["title"],
                              version=meta["version"], chunk_id=passage["chunk_id"], section=passage["section"], quote=passage["body"],
                              source=meta["source_system"], effective_on=meta["effective_date"])
    return HRResponse(status="answered", intent=intent, answer="Approved fictional policy excerpt:\n\n[1] " + passage["body"], citations=[citation])
