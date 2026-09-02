from datetime import datetime, timedelta

import pytest

from app.core.numbering import format_number, next_number, normalise, with_revision
from app.core.turnaround import (
    STATUS_DRAFT, STATUS_IN_PROGRESS, STATUS_READY, STATUS_SENT,
    due_at, format_date, format_dt, humanise_delta, is_overdue, status_label,
)

RECEIVED = datetime(2026, 8, 18, 9, 12)


def test_due_uses_the_slowest_test():
    assert due_at(RECEIVED, [2, 24, 6]) == RECEIVED + timedelta(hours=24)


def test_due_with_no_tats_defaults_to_a_day():
    assert due_at(RECEIVED, []) == RECEIVED + timedelta(hours=24)


def test_due_ignores_missing_tats():
    assert due_at(RECEIVED, [None, 4, None]) == RECEIVED + timedelta(hours=4)


def test_fractional_hours():
    assert due_at(RECEIVED, [1.5]) == RECEIVED + timedelta(minutes=90)


# ------------------------------------------------------------------- overdue

def test_overdue_only_applies_to_unfinished_work():
    due = datetime(2026, 8, 18, 14, 0)
    now = datetime(2026, 8, 18, 16, 0)
    assert is_overdue(due, STATUS_DRAFT, now) is True
    assert is_overdue(due, STATUS_IN_PROGRESS, now) is True
    # Finished work is never chased.
    assert is_overdue(due, STATUS_READY, now) is False
    assert is_overdue(due, STATUS_SENT, now) is False


def test_not_overdue_before_the_due_time():
    due = datetime(2026, 8, 18, 14, 0)
    assert is_overdue(due, STATUS_DRAFT, datetime(2026, 8, 18, 13, 59)) is False


def test_missing_due_is_never_overdue():
    assert is_overdue(None, STATUS_DRAFT, datetime.now()) is False


# ------------------------------------------------------------------ humanise

@pytest.mark.parametrize("delta_minutes,expected", [
    (-120, "2h late"),
    (-45,  "45m late"),
    (45,   "in 45m"),
    (180,  "in 3h"),
    (60 * 24 * 3, "in 3d"),
])
def test_humanise_delta(delta_minutes, expected):
    now = datetime(2026, 8, 18, 12, 0)
    assert humanise_delta(now + timedelta(minutes=delta_minutes), now) == expected


def test_humanise_blank_for_none():
    assert humanise_delta(None) == ""


def test_formats():
    assert format_dt(datetime(2026, 8, 18, 9, 5)) == "18-08-2026 09:05"
    # The report prints the date only, matching the lab's existing format.
    assert format_date(datetime(2026, 8, 18, 9, 5)) == "18-08-2026"
    assert format_date(None) == ""


def test_status_labels():
    assert status_label(STATUS_READY) == "Ready to send"
    assert status_label(STATUS_SENT) == "Sent"


# ----------------------------------------------------------------- numbering

@pytest.mark.parametrize("value,expected", [
    (51358, 51358), ("51358", 51358), (" 51358 ", 51358),
    (0, None), (-3, None), ("", None), (None, None), ("51A", None), ("abc", None),
])
def test_normalise(value, expected):
    assert normalise(value) == expected


def test_next_number_continues_the_lab_series():
    assert next_number(51358) == 51359
    assert next_number(None) == 1


def test_format_number():
    assert format_number(51359) == "51359"
    assert format_number(42, width=6) == "000042"
    assert format_number(42, prefix="NM-") == "NM-42"
    assert format_number(None) == ""


def test_revision_marking():
    assert with_revision(51359, 1) == "51359"
    assert with_revision(51359, 2) == "51359 / R2"
