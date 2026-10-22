from lab.contracts import PendingExercise


def chunk_policy(policy: dict, max_words: int = 80) -> list[dict]:
    """E04: section-boundary chunks; preserve policy/version/section provenance.

    Return dictionaries with chunk_id, section_key, body. Never mix sections.
    """
    raise PendingExercise("E04 chunk_policy")
