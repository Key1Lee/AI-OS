from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .config import Settings
from .models import Assistance, Mode, Outcome


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def next_review_at(
    *,
    outcome: Outcome,
    assistance: Assistance,
    mode: Mode,
    is_transfer: bool,
    consecutive_failures: int,
    settings: Settings,
    now: datetime | None = None,
) -> datetime:
    now = now or utc_now()
    if outcome == Outcome.FAIL:
        hours = 12 if consecutive_failures >= 2 else settings.failure_interval_days * 24
        return now + timedelta(hours=hours)
    if assistance != Assistance.NONE:
        return now + timedelta(days=settings.hinted_interval_days)
    if is_transfer:
        return now + timedelta(days=settings.transfer_interval_days)
    if mode == Mode.COLD_RECALL:
        return now + timedelta(days=settings.cold_recall_interval_days)
    return now + timedelta(days=settings.independent_interval_days)
