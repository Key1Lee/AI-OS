from app.security import suspicious_instruction


def rejection_reason(document, as_of):
    """Reject lifecycle and instruction hazards independently of the model or source's claims."""
    if document.status != "approved":
        return document.status
    if document.effective_date > as_of:
        return "not_yet_effective"
    if document.expiration_date and document.expiration_date <= as_of:
        return "expired"
    if document.classification == "confidential":
        return "confidential_not_indexable"
    if suspicious_instruction(document.text) or suspicious_instruction(document.title):
        return "prompt_injection"
    return None
