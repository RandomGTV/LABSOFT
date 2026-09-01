"""Drives the real screens offscreen.

These catch the errors unit tests cannot: a mistyped import, a signal wired to a
method that does not exist, a widget touched before it is built. Every screen is
constructed and the main flow is walked end to end.
"""

from __future__ import annotations

import os

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


@pytest.fixture()
def widgets(env):
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    from app.ui import style

    app.setStyleSheet(style.STYLESHEET)
    yield app


# ------------------------------------------------------------ every screen

def test_all_screens_construct(widgets, env):
    from app.ui.billing_screen import BillingScreen
    from app.ui.job_screen import JobScreen
    from app.ui.queue_screen import QueueScreen
    from app.ui.settings_screen import SettingsScreen
    from app.ui.summaries_screen import SummariesScreen
    from app.ui.tests_screen import TestsScreen

    for cls in (JobScreen, QueueScreen, TestsScreen, BillingScreen,
                SummariesScreen, SettingsScreen):
        w = cls()
        assert w is not None
        w.deleteLater()


def test_main_window_constructs_and_refreshes(widgets, env):
    from app.ui.main_window import MainWindow

    win = MainWindow()
    # Job, Work Queue, Patients, Doctors, Tests, Billing, Summaries, Staff, Settings
    assert win.tabs.count() == 9
    assert [win.tabs.tabText(i) for i in range(win.tabs.count())][:4] == \
        ["Job", "Work Queue", "Patients", "Doctors"]
    for i in range(win.tabs.count()):
        win.tabs.setCurrentIndex(i)     # triggers each screen's refresh()
    win._refresh_status()
    win.close()


def test_dialogs_construct(widgets, env):
    from app.ui.panels_dialog import PanelEditor, PanelsDialog
    from app.ui.referrers_dialog import ReferrerEditor, ReferrersDialog
    from app.ui.tests_screen import TestEditor

    PanelsDialog().deleteLater()
    ReferrersDialog().deleteLater()
    ReferrerEditor(None).deleteLater()
    PanelEditor(None).deleteLater()
    TestEditor(None).deleteLater()
    TestEditor(env.get_test_by_code("GLU_F")["id"]).deleteLater()


# ---------------------------------------------------------- the main flow

def test_job_screen_end_to_end(widgets, env):
    """Type a patient, click a panel, fill results, and reach a PDF."""
    from app.ui.job_screen import JobScreen

    screen = JobScreen()
    screen.name_edit.setText("FARAS .M.")
    screen.phone_edit.setText("9876543210")
    screen.sex_combo.setCurrentText("Female")
    screen.age_spin.setValue(31)

    panel = next(p for p in env.list_panels() if p["name"] == "Blood Sugar F & PP")
    screen._add_panel(panel["id"])
    assert len(screen.rows) == 2
    assert screen.job_id is None          # nothing written until a value is typed

    rows = list(screen.rows.values())
    rows[0].set_value("105")
    screen._recalc()
    assert screen.job_id is not None      # job created on first entry
    assert not screen.verify_button.isEnabled()   # gate still closed

    # The value typed before the job existed must survive the rebuild.
    kept = [r.value() for r in screen.rows.values()]
    assert "105" in kept

    for r in screen.rows.values():
        if not r.value():
            r.set_value("123")
    screen._recalc()
    assert screen.verify_button.isEnabled()

    from app import services

    ok, missing, path = services.verify_job(screen.job_id)
    assert ok and not missing and path.exists()
    screen.deleteLater()


def test_derived_values_appear_on_screen(widgets, env):
    from app.ui.job_screen import JobScreen

    screen = JobScreen()
    screen.name_edit.setText("Ramesh")
    screen.age_spin.setValue(45)
    screen.sex_combo.setCurrentText("Male")

    for code in ("TP", "ALB", "GLOB", "AGR"):
        screen.test_ids.append(env.get_test_by_code(code)["id"])
    screen._rebuild_grid()

    by_code = {r.test["code"]: r for r in screen.rows.values()}
    by_code["TP"].set_value("7.2")
    by_code["ALB"].set_value("3.1")
    screen._recalc()

    by_code = {r.test["code"]: r for r in screen.rows.values()}
    assert by_code["GLOB"].value() == "4.1g/dl"
    assert by_code["AGR"].value() == "0.76"
    assert by_code["GLOB"].editor.isReadOnly()
    assert by_code["ALB"].flag_label.text() == "LOW"
    screen.deleteLater()


def test_queue_shows_and_filters_jobs(widgets, env):
    from app.ui.queue_screen import QueueScreen

    pid = env.save_patient({"name": "Sunita Devi", "phone": "91234 56780",
                            "sex": "Female", "age_value": 40, "age_unit": "years"})
    tid = env.get_test_by_code("TSH")["id"]
    env.create_job(pid, [tid])

    screen = QueueScreen()
    screen.refresh()
    assert screen.table.rowCount() == 1

    screen._set_scope("ready")
    assert screen.table.rowCount() == 0

    screen._set_scope("all")
    screen.search.setText("Sunita")
    screen.refresh()
    assert screen.table.rowCount() == 1
    screen.deleteLater()


def test_bill_dialog_totals(widgets, env):
    from app.core import billing
    from app.ui.bill_dialog import BillDialog

    pid = env.save_patient({"name": "Ramesh", "age_value": 45, "age_unit": "years"})
    cbc = next(p for p in env.list_panels() if p["name"] == "CBC")
    jid = env.create_job(pid, env.panel_test_ids(cbc["id"]))

    dlg = BillDialog(jid)
    assert dlg.items_table.rowCount() >= 1
    dlg.discount_value.setValue(10)
    dlg._recalc()
    assert "Balance" in dlg.totals_label.text()
    dlg._save()
    assert env.get_bill(jid) is not None
    dlg.deleteLater()


def test_history_dialog(widgets, env):
    from app.ui.history_dialog import HistoryDialog
    from app import services

    pid = env.save_patient({"name": "Repeat", "age_value": 40, "age_unit": "years"})
    tid = env.get_test_by_code("GLU_F")["id"]
    for value in ("101", "112"):
        jid = env.create_job(pid, [tid])
        jt = env.job_tests(jid)[0]["job_test_id"]
        services.recalculate(jid, {jt: value})

    dlg = HistoryDialog(pid)
    assert dlg.jobs_table.rowCount() == 2
    assert dlg.trend_table.rowCount() == 2
    dlg.deleteLater()


def test_settings_round_trip(widgets, env):
    from app.ui.settings_screen import SettingsScreen

    screen = SettingsScreen()
    screen.editors["lab_name"].setText("MITHRA LAB")
    screen.print_header_check.setChecked(False)
    screen.save()

    assert env.get_setting("lab_name") == "MITHRA LAB"
    assert env.get_setting("print_header") == "0"

    screen.reload()
    assert screen.editors["lab_name"].text() == "MITHRA LAB"
    assert not screen.print_header_check.isChecked()
    screen.deleteLater()


def test_settings_rejects_a_bad_report_number(widgets, env):
    from app.ui.settings_screen import SettingsScreen

    screen = SettingsScreen()

    screen.editors["next_report_no"].setText("fifty one thousand")
    assert "whole number" in screen.validate(screen.collect())

    screen.editors["next_report_no"].setText("51359")
    screen.editors["lab_name"].setText("")
    assert "cannot be empty" in screen.validate(screen.collect())

    screen.editors["lab_name"].setText("MITHRA")
    assert screen.validate(screen.collect()) == ""
    screen.deleteLater()


def test_settings_save_refuses_bad_input(widgets, env, monkeypatch):
    """save() must leave the stored value untouched when validation fails."""
    import app.ui.settings_screen as mod
    from app.ui.settings_screen import SettingsScreen

    shown = []
    monkeypatch.setattr(mod, "warn", lambda *a, **k: shown.append(a))

    screen = SettingsScreen()
    before = env.get_setting("next_report_no")
    screen.editors["next_report_no"].setText("abc")
    assert screen.save() is False
    assert shown
    assert env.get_setting("next_report_no") == before
    screen.deleteLater()


def test_tests_screen_lists_and_searches(widgets, env):
    from app.ui.tests_screen import TestsScreen

    screen = TestsScreen()
    total = screen.table.rowCount()
    assert total > 90

    screen.search.setText("glucose")
    screen.refresh()
    assert 0 < screen.table.rowCount() < total
    screen.deleteLater()


def test_summaries_screen_switches_mode(widgets, env):
    from app.ui.summaries_screen import SummariesScreen

    pid = env.save_patient({"name": "X", "age_value": 20, "age_unit": "years"})
    env.create_job(pid, [env.get_test_by_code("GLU_F")["id"]])

    screen = SummariesScreen()
    assert "Day sheet" in screen.headline.text()
    screen.mode.setCurrentIndex(1)
    assert "Month sheet" in screen.headline.text()
    screen.deleteLater()
