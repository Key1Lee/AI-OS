from collections.abc import Callable
from lab.contracts import PendingExercise


def fetch_all(fetch_page: Callable, sleep: Callable, max_attempts: int = 3) -> list[dict]:
    """E11: fetch_page(cursor=0, attempt=1); retry timeouts/429/5xx only.

    Bounded backoff 0.1, 0.2 seconds; independent per page; detect cyclic cursors.
    Reject schema_version != 1 and malformed pages. No partial successful result.
    """
    raise PendingExercise("E11 fetch_all")
