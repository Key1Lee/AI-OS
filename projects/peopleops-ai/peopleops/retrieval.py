"""Permission-filtered sparse TF-IDF retrieval with extractive, grounded answers.

No cloud model, neural embedding service, or API key. An LLM extension would
replace only the answer assembly after permission filtering and retrieval.
"""
from collections import Counter
from math import log, sqrt
import re
from .db import rows

STOP = set("a an the is are am i my me you your how what when where can do does to of for in on and or it with this that have get much many please company employee employees fictional".split())
SYNONYMS = {"pto": "vacation", "holiday": "vacation", "holidays": "vacation", "paycheck": "payroll",
            "payslip": "payroll", "payslips": "payroll", "paid": "payroll", "pay": "payroll",
            "benefit": "benefits", "insurance": "benefits", "laptop": "equipment", "start": "onboarding",
            "onboard": "onboarding", "first": "onboarding", "remote": "remote", "wfh": "remote"}


def tokens(text: str) -> list[str]:
    return [SYNONYMS.get(word, word) for word in re.findall(r"[a-z]+", text.lower()) if word not in STOP]


def visible_policies(conn, role: str) -> list[dict]:
    return rows(conn, "SELECT * FROM policies WHERE available=1 AND (visibility='public' OR ?='hr') ORDER BY policy_id", (role,))


def answer_question(conn, question: str, role: str) -> dict:
    fallback = dict(answer="I could not find an approved policy passage that safely answers this question. Submit an HR request for a person to review it.",
                    citations=[], confidence=0.0, escalated=True, method="extractive_tf_idf", reason="no_supported_answer")
    if re.search(r"ignore.*(instruction|rule)|system prompt|reveal.*(secret|restricted)|\bsalary\b|\bssn\b|bank account|another employee|coworker", question, re.I):
        return {**fallback, "reason": "sensitive_or_unsafe_question"}
    documents = visible_policies(conn, role)  # Authorization happens BEFORE ranking/chunking.
    chunks = [{**doc, "passage": passage.strip()} for doc in documents for passage in doc["body"].split("\n\n") if passage.strip()]
    query = Counter(tokens(question))
    if not query or not chunks:
        return fallback
    counts = [Counter(tokens(chunk["title"] + " " + chunk["passage"])) for chunk in chunks]
    frequency = Counter(term for count in counts for term in count)
    idf = {term: log((1+len(chunks))/(1+df))+1 for term, df in frequency.items()}

    def vector(count):
        values = {term: amount * idf.get(term, log(1+len(chunks))+1) for term, amount in count.items()}
        norm = sqrt(sum(value*value for value in values.values())) or 1
        return {term: value/norm for term, value in values.items()}

    query_vector = vector(query)
    scores = [sum(query_vector.get(term, 0)*weight for term, weight in vector(count).items()) for count in counts]
    best = max(range(len(scores)), key=scores.__getitem__)
    if scores[best] < 0.16:
        return fallback
    winner = chunks[best]
    # Exact approved text, rather than free-form model output, makes citation support testable.
    return dict(answer=winner["passage"], citations=[dict(policy_id=winner["policy_id"], title=winner["title"],
                version=winner["version"], passage=winner["passage"], url=f"/api/policies/{winner['policy_id']}")],
                confidence=round(scores[best], 3), escalated=False, method="extractive_tf_idf", reason="approved_passage")
