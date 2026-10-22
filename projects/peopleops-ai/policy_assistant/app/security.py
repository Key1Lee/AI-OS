import hashlib
import hmac
import re
import unicodedata

from fastapi import HTTPException

from app.contracts import Answer, Identity


def authenticate(authorization: str | None, credentials) -> Identity:
    """Look up a bearer token in the server's identity map. Client-supplied roles and regions are never used."""
    scheme, _, token = (authorization or "").partition(" ")
    digest = hashlib.sha256(token.encode()).hexdigest()
    for credential in credentials:
        if scheme.lower() == "bearer" and token and hmac.compare_digest(digest, credential.token_sha256):
            return credential.identity
    raise HTTPException(401, "A valid bearer token is required", headers={"WWW-Authenticate": "Bearer"})


def require_admin(identity: Identity) -> Identity:
    """Require the admin role for ingestion and detailed health checks."""
    if identity.role != "admin":
        raise HTTPException(403, "Administrator access is required")
    return identity


def suspicious_instruction(text: str) -> bool:
    """Recognize common attempts to replace instructions or reveal secrets. This is an extra guard; SQL authorization remains the security boundary."""
    text = unicodedata.normalize("NFKC", text).casefold()
    return bool(re.search(r"ignore.{0,50}(instruction|previous|policy|rules)|system\s*prompt|developer\s*message|"
                          r"api[_ -]?key|access[_ -]?token|bypass.{0,40}(acl|access|permission)|"
                          r"<script|\[inst\]|reveal.{0,40}(secret|hidden)|act as.{0,30}(admin|system)", text, re.S))


def safety_response(question: str) -> Answer | None:
    """Route personal HR decisions to a human and refuse obvious instruction attacks. No employee record, benefit decision, or payroll action is available to this app."""
    if suspicious_instruction(question):
        return Answer(status="refused", answer="I can help with approved HR policy questions. I cannot change access rules or reveal private instructions.")
    q = unicodedata.normalize("NFKC", question).casefold()
    personal = re.search(r"\b(balances?|remaining|payslips?|paychecks?|salary|salaries|ssn|bank|diagnosis|medical records?|"
                         r"eligible|eligibility|qualify|coverage|covered|cover|deductible|reimburse|reimbursement)\b", q)
    personal = personal or re.search(r"\b(my|our|his|her|their|employee['’]?s|employee)\b.{0,45}\b(payroll|pay|benefits|leave|pto|account)\b", q)
    personal = personal or re.search(r"\b(am i|can i|do i|will i)\b.{0,50}\b(receive|get|entitled|take|paid|work|move)\b", q)
    personal = personal or re.search(r"\bhow (much|many)\b.{0,60}\b(pto|vacation|leave|pay)\b", q)
    if personal:
        return Answer(status="escalated", answer="This needs a private review by People Operations. I cannot determine a person's balance, pay, eligibility, or plan coverage. Use your organization's authenticated HR support channel; do not share payroll, banking, or medical details here.",
                      escalation="Contact People Operations through the authenticated HR portal. No ticket has been created.")
    return None
