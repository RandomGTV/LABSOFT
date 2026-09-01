"""Turnaround time and job status helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Optional, Sequence

__all__ = [
    "STATUS_DRAFT", "STATUS_IN_PROGRESS", "STATUS_READY", "STATUS_SENT",
    "STATUS_ORDER", "status_label",
    "due_at", "is_overdue", "humanise_delta", "format_dt", "format_date",
]

STATUS_DRAFT = "draft"
STATUS_IN_PROGRESS = "in_progress"
STATUS_READY = "ready"
STATUS_SENT = "sent"

STATUS_ORDER = [STATUS_DRAFT, STATUS_IN_PROGRESS, STATUS_READY, STATUS_SENT]

_STATUS_LABELS = {
    STATUS_DRAFT: "Registered",
    STATUS_IN_PROGRESS: "In progress",
    STATUS_READY: "Ready to send",
    STATUS_SENT: "Sent",
}


def status_label(status: str) -> str:
    return _STATUS_LABELS.get(status, status or "")


def due_at(received: datetime, tat_hours: Sequence[float]) -> datetime:
    """The job is due when its slowest test is due."""
    hours = [float(h) for h in tat_hours if h is not None]
    longest = max(hours) if hours else 24.0
    return received + timedelta(hours=longest)


def is_overdue(due: Optional[datetime], status: str, now: Optional[datetime] = None) -> bool:
    """Only unfinished work can be overdue; a sent report never is."""
    if due is None:
        return False
    if status in (STATUS_READY, STATUS_SENT):
        return False
    return (now or datetime.now()) > due


def humanise_delta(target: Optional[datetime], now: Optional[datetime] = None) -> str:
    """'2h late', 'in 45m', 'in 3d' — for the Due column."""
    if target is None:
        return ""
    now = now or datetime.now()
    seconds = (target - now).total_seconds()
    late = seconds < 0
    seconds = abs(seconds)

    if seconds < 60:
        text = "now"
        return text
    minutes = int(seconds // 60)
    if minutes < 60:
        text = f"{minutes}m"
    elif minutes < 60 * 48:
        hours = minutes / 60.0
        text = f"{hours:.0f}h" if hours >= 2 else f"{int(minutes)}m"
    else:
        text = f"{int(minutes // (60 * 24))}d"
    return f"{text} late" if late else f"in {text}"


def format_dt(value: Optional[datetime]) -> str:
    return value.strftime("%d-%m-%Y %H:%M") if value else ""


def format_date(value: Optional[datetime]) -> str:
    """The report prints the date only, with no time, as the lab's does."""
    return value.strftime("%d-%m-%Y") if value else ""
