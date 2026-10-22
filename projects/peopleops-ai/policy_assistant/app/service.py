from datetime import datetime
from zoneinfo import ZoneInfo

from app.contracts import Answer, Citation
from app.security import safety_response, suspicious_instruction
from app.storage import retrieve


def grounded_answer(selection, passages) -> Answer:
    """Build an answer only from complete, authorized source chunks. Unknown or duplicate citation IDs cause abstention instead of invented text."""
    sources = {p["chunk_id"]: p for p in passages}
    ids = selection.chunk_ids
    if not selection.supported or not ids or len(set(ids)) != len(ids) or any(i not in sources for i in ids):
        return Answer(status="abstained", answer="I do not have enough current, authorized policy evidence to answer that. Please contact People Operations.")
    selected = [sources[i] for i in ids]
    if any(suspicious_instruction(p["body"]) for p in selected):
        return Answer(status="abstained", answer="The available evidence needs review by People Operations.")
    citations = [Citation(policy_id=p["policy_id"], version=p["version"], title=p["title"], section=p["section"],
                          chunk_id=p["chunk_id"], source=p["source"], effective_on=p["effective_on"], quote=p["body"]) for p in selected]
    answer = "Relevant fictional policy excerpts (not a personal entitlement decision):\n\n"
    answer += "\n\n".join(f"[{i}] {citation.quote}" for i, citation in enumerate(citations, 1))
    return Answer(status="answered", answer=answer, citations=citations)


def ask_policy(conn, question, identity, providers, settings, as_of=None) -> Answer:
    """Apply safety rules, retrieve authorized evidence, then validate the model's selection. Missing evidence produces an explicit abstention."""
    early = safety_response(question)
    if early:
        return early
    today = as_of or datetime.now(ZoneInfo(settings.policy_timezone)).date()
    passages = retrieve(conn, question, identity, providers, settings, today)
    if not passages:
        return Answer(status="abstained", answer="I do not have enough current, authorized policy evidence to answer that. Please contact People Operations.")
    return grounded_answer(providers.select(question, passages), passages)
