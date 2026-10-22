from lab.contracts import Principal, PendingExercise


def authorize(principal: Principal, action: str, resource: dict) -> bool:
    """E07: return a deny-by-default decision using docs/security.md's matrix."""
    raise PendingExercise("E07 authorize")
