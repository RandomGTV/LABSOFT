"""The work queue board: what each row says, and that it can be drawn.

The board is painted rather than laid out, so a mistake here is invisible to
an ordinary widget test -- the row exists, the text is simply never drawn, or
drawn in the wrong place. These tests check the two halves separately: the
sentence each row is meant to say, and that painting every column of every
state completes without Qt raising.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("LABSOFT_HOME", str(tmp_path))
    from app.db import connection

    connection.close()
    connection.connect(do_backup=False)
    from app.db import queries as q, seed

    q.ensure_defaults()
    seed.seed_all()
    yield q
    connection.close()


def _job(q, name, phone, when, due, status="draft", done=0):
    pid = q.save_patient({"name": name, "phone": phone, "sex": "Male",
                          "age_value": 40, "age_unit": "years"})
    tests = [t["id"] for t in q.list_tests()[:2]]
    jid = q.create_job(pid, tests, received=when)
    q.update_job(jid, due_at=due.strftime("%Y-%m-%d %H:%M:%S"), status=status)
    for jt in q.job_tests(jid)[:done]:
        q.save_result(jt["job_test_id"], "5.2", 5.2, "5.2", "3.5 - 6.0", "")
    return jid


def test_a_late_job_says_overdue_and_carries_the_stripe(env, qt_app):
    """Colour alone is not a message; the row has to use the word."""
    from app.ui.queue_screen import QueueScreen, ROW_ROLE

    now = datetime.now()
    _job(env, "Sameer Rao", "99584 10022", now - timedelta(hours=3),
         now - timedelta(minutes=72), status="in_progress", done=1)

    screen = QueueScreen()
    screen._set_scope("all")
    try:
        row = screen.table.item(0, 0).data(ROW_ROLE)
        assert row["late"] is True
        assert row["due"].startswith("overdue")
        assert "1h" in row["due"] or "72m" in row["due"]
    finally:
        screen.deleteLater()


def test_a_finished_job_past_its_time_is_not_called_late(env, qt_app):
    """The work is done; what is outstanding is the sending, so say that."""
    from app.ui.queue_screen import QueueScreen, ROW_ROLE

    now = datetime.now()
    _job(env, "Fatima Sheikh", "97444 88210", now - timedelta(hours=4),
         now - timedelta(minutes=22), status="ready", done=2)

    screen = QueueScreen()
    screen._set_scope("all")
    try:
        row = screen.table.item(0, 0).data(ROW_ROLE)
        assert row["late"] is False
        assert "late" not in row["due"]
        assert row["due"] == "send now"
    finally:
        screen.deleteLater()


def test_a_sent_job_reports_when_it_was_delivered(env, qt_app):
    from app.ui.queue_screen import QueueScreen, ROW_ROLE

    now = datetime.now()
    jid = _job(env, "Vikram Joshi", "98470 55123", now - timedelta(hours=5),
               now - timedelta(hours=2), status="ready", done=2)
    env.update_job(jid, status="sent",
                   sent_at=(now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"))

    screen = QueueScreen()
    screen._set_scope("all")
    try:
        row = screen.table.item(0, 0).data(ROW_ROLE)
        assert row["due"].startswith("delivered")
    finally:
        screen.deleteLater()


def test_the_numbers_over_the_board_match_the_database(env, qt_app):
    from app.ui.queue_screen import QueueScreen

    now = datetime.now()
    _job(env, "Waiting One", "90000 00001", now, now + timedelta(hours=6))
    _job(env, "Waiting Two", "90000 00002", now, now + timedelta(hours=6))
    _job(env, "Half Typed", "90000 00003", now, now + timedelta(hours=6),
         status="in_progress", done=1)
    _job(env, "Verified", "90000 00004", now, now + timedelta(hours=6),
         status="ready", done=2)

    screen = QueueScreen()
    try:
        assert screen.stats["waiting"].value.text() == "2"
        assert screen.stats["in_progress"].value.text() == "1"
        assert screen.stats["ready"].value.text() == "1"
        assert screen.stats["overdue"].value.text() == "0"
        # Nothing late: the number must not be shouting.
        assert screen.stats["overdue"].value.property("alert") == "false"
    finally:
        screen.deleteLater()


def test_the_overdue_number_shows_how_old_the_oldest_one_is(env, qt_app):
    from app.ui.queue_screen import QueueScreen

    now = datetime.now()
    _job(env, "Late A", "90000 00005", now - timedelta(hours=4),
         now - timedelta(minutes=30), status="in_progress", done=1)
    _job(env, "Late B", "90000 00006", now - timedelta(hours=6),
         now - timedelta(minutes=200), status="in_progress", done=1)

    screen = QueueScreen()
    screen._set_scope("all")
    try:
        assert screen.stats["overdue"].value.text() == "2"
        assert screen.stats["overdue"].value.property("alert") == "true"
        assert screen.stats["overdue"].note.text().startswith("oldest")
        # The oldest, not the newest: 3h beats 30m.
        assert "3h" in screen.stats["overdue"].note.text()
    finally:
        screen.deleteLater()


def test_progress_counts_the_tests_that_are_done(env, qt_app):
    from app.ui.queue_screen import QueueScreen, ROW_ROLE

    now = datetime.now()
    _job(env, "Half Done", "90000 00007", now, now + timedelta(hours=6),
         status="in_progress", done=1)

    screen = QueueScreen()
    try:
        row = screen.table.item(0, 0).data(ROW_ROLE)
        assert (row["n_done"], row["n_tests"]) == (1, 2)
    finally:
        screen.deleteLater()


def test_every_column_of_every_state_can_be_painted(env, qt_app):
    """Draw the whole board for real, in both themes.

    A delegate that raises paints nothing and leaves no trace in a widget
    test -- the row is there, the pixels are not. This forces the paint.
    """
    from PyQt6.QtCore import QRect
    from PyQt6.QtGui import QPainter, QPixmap
    from PyQt6.QtWidgets import QStyleOptionViewItem

    from app.ui import style
    from app.ui.queue_screen import HEADERS, QueueScreen

    now = datetime.now()
    _job(env, "Registered", "90000 00011", now, now + timedelta(hours=6))
    _job(env, "In Progress", "90000 00012", now, now - timedelta(minutes=10),
         status="in_progress", done=1)
    _job(env, "Ready", "90000 00013", now, now + timedelta(hours=1),
         status="ready", done=2)
    jid = _job(env, "Sent", "90000 00014", now, now + timedelta(hours=1),
               status="ready", done=2)
    env.update_job(jid, status="sent", sent_at=now.strftime("%Y-%m-%d %H:%M:%S"))

    for theme in ("light", "dark"):
        style.apply_theme(qt_app, theme)
        screen = QueueScreen()
        screen._set_scope("all")
        try:
            table = screen.table
            delegate = table.itemDelegate()
            assert table.rowCount() == 4
            pixmap = QPixmap(400, 60)
            painter = QPainter(pixmap)
            try:
                for r in range(table.rowCount()):
                    for c in range(len(HEADERS)):
                        option = QStyleOptionViewItem()
                        option.rect = QRect(0, 0, 200, 40)
                        delegate.paint(painter, option, table.model().index(r, c))
            finally:
                painter.end()
        finally:
            screen.deleteLater()
    style.apply_theme(qt_app, "light")


def test_the_board_keeps_the_actions_the_rest_of_the_app_calls(env, qt_app):
    """main_window wires these by name; renaming one breaks the queue silently."""
    from app.ui.queue_screen import QueueScreen

    screen = QueueScreen()
    try:
        for name in ("open_job", "send_job", "preview_job", "search", "table",
                     "refresh", "open_button", "send_button", "preview_button",
                     "revise_button", "delete_button", "counts"):
            assert hasattr(screen, name), f"the queue lost {name}"
    finally:
        screen.deleteLater()
