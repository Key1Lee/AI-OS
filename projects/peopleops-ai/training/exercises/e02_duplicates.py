from lab.contracts import PendingExercise


def latest_events(events: list[dict]) -> list[dict]:
    """E02: one event per event_id; newest aware source_updated_at wins.

    Equal timestamp: last input wins. Return event_id order without mutation.
    """
    raise PendingExercise("E02 latest_events")
