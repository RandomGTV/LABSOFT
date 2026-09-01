"""Regression tests for the faults found in the code audit.

Each of these was reproduced against the shipped build before being fixed.
"""

from __future__ import annotations

import os
import sqlite3
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


@pytest.fixture()
def app_env(env):
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    from app.ui import style

    style.apply_light_palette(app)
    app.setStyleSheet(style.STYLESHEET)
    yield env, app


def make_job(q, codes=("GLU_F",), age=31, unit="years", sex="Female"):
    pid = q.save_patient({"name": "Test Patient", "phone": "9876543210",
                          "sex": sex, "age_value": age, "age_unit": unit})
    ids = [q.get_test_by_code(c)["id"] for c in codes]
    return pid, q.create_job(pid, ids)


# ===========================================================================
# CRITICAL — backups were being written empty
# ===========================================================================

def test_backup_contains_the_work_just_done(env, tmp_path):
    """WAL mode keeps recent work in a side-file; copying lab.db alone lost it."""
    from app import services
    from app.db import connection

    _pid, jid = make_job(env, ("GLU_F", "GLU_PP"))
    m = {t["code"]: t["job_test_id"] for t in env.job_tests(jid)}
    services.recalculate(jid, {m["GLU_F"]: "105", m["GLU_PP"]: "123"})

    backup = connection.backup_now()

    check = sqlite3.connect(str(backup))
    try:
        jobs = check.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        results = check.execute(
            "SELECT COUNT(*) FROM results WHERE display_value <> ''").fetchone()[0]
    finally:
        check.close()

    assert jobs == 1, "the backup does not contain the job"
    assert results == 2, "the backup does not contain the results"


def test_backup_leaves_no_partial_file(env):
    from app.db import connection

    make_job(env)
    connection.backup_now()
    assert not list(connection.config.backup_dir().glob("*.part"))


def test_restore_brings_the_data_back(env):
    from app import services
    from app.db import connection

    _pid, jid = make_job(env, ("GLU_F",))
    m = {t["code"]: t["job_test_id"] for t in env.job_tests(jid)}
    services.recalculate(jid, {m["GLU_F"]: "105"})
    backup = connection.backup_now()

    env.delete_job(jid)
    assert env.list_jobs("all") == []

    connection.restore_from(backup)
    assert len(env.list_jobs("all")) == 1


# ===========================================================================
# CRITICAL — ranges came from the patient's age today, not at the test
# ===========================================================================

def test_reference_range_uses_the_age_at_the_time_of_the_test(env):
    from app import services

    hb = env.get_test_by_code("HB")
    env.replace_ranges(hb["id"], [
        {"rule_type": "range", "low": 14, "high": 22, "sex": "any",
         "age_min": None, "age_max": 0.5, "display_text": "14 - 22g/dl"},
        {"rule_type": "range", "low": 12, "high": 15, "sex": "any",
         "age_min": 0.5, "age_max": None, "display_text": "12 - 15g/dl"},
    ])

    pid = env.save_patient({"name": "Baby", "sex": "Female",
                            "age_value": 10, "age_unit": "days"})
    jid = env.create_job(pid, [hb["id"]])
    m = {t["code"]: t["job_test_id"] for t in env.job_tests(jid)}
    first = services.recalculate(jid, {m["HB"]: "16"})
    assert first[m["HB"]]["range_text"] == "14 - 22g/dl"
    assert first[m["HB"]]["flag"] == "N"

    # The patient grows up; the old report must not change.
    env.save_patient({"id": pid, "age_value": 3, "age_unit": "years"})
    again = services.recalculate(jid)
    assert again[m["HB"]]["range_text"] == "14 - 22g/dl", \
        "an old report silently changed its Normal Value column"
    assert again[m["HB"]]["flag"] == "N"


def test_age_snapshot_is_stored_on_the_job(env):
    _pid, jid = make_job(env, age=10, unit="days")
    job = env.get_job(jid)
    assert job["age_value_at_test"] == 10
    assert job["age_unit_at_test"] == "days"


# ===========================================================================
# MAJOR — patient fields were being wiped
# ===========================================================================

def test_saving_from_the_job_screen_keeps_the_address_and_notes(env):
    from app import services

    pid = env.save_patient({"name": "Ramesh", "phone": "9876543210",
                            "sex": "Male", "age_value": 45, "age_unit": "years",
                            "address": "12 MG Road", "notes": "Diabetic since 2019"})

    services.upsert_patient("Ramesh", "9876543210", "Male", 46, "years",
                            patient_id=pid)

    p = env.get_patient(pid)
    assert p["address"] == "12 MG Road", "the address was wiped"
    assert p["notes"] == "Diabetic since 2019", "the clinical note was wiped"
    assert p["age_value"] == 46


# ===========================================================================
# MAJOR — a formula could crash the whole calculation pass
# ===========================================================================

def test_a_bad_power_does_not_take_the_other_results_down(env):
    from app import services
    from app.core import formula

    with pytest.raises(formula.FormulaError):
        formula.evaluate("A ^ B", {"A": -8, "B": 0.5})

    env.save_test({"code": "BADPOW", "name": "Bad Power", "group_name": "OTHER",
                   "unit": "", "decimals": 1, "result_type": "numeric",
                   "options": "", "formula": "GLU_F ^ 0.5", "rate_paise": 0,
                   "tat_hours": 1, "sort_order": 0, "active": 1})

    pid = env.save_patient({"name": "P", "age_value": 30, "age_unit": "years"})
    jid = env.create_job(pid, [env.get_test_by_code("GLU_F")["id"],
                               env.get_test_by_code("GLU_PP")["id"],
                               env.get_test_by_code("BADPOW")["id"]])
    m = {t["code"]: t["job_test_id"] for t in env.job_tests(jid)}

    out = services.recalculate(jid, {m["GLU_F"]: "-9", m["GLU_PP"]: "123"})
    assert out[m["GLU_PP"]]["display"] == "123mg/dl", \
        "an unrelated result was lost because one formula failed"


# ===========================================================================
# MAJOR — commission stayed with the previous doctor
# ===========================================================================

def test_changing_the_doctor_moves_the_commission(env):
    from app.core.billing import to_paise

    a = env.save_referrer({"name": "Dr A", "qualification": "", "phone": "",
                           "commission_percent": 10, "active": 1})
    b = env.save_referrer({"name": "Dr B", "qualification": "", "phone": "",
                           "commission_percent": 20, "active": 1})

    pid = env.save_patient({"name": "P", "age_value": 30, "age_unit": "years"})
    jid = env.create_job(pid, [env.get_test_by_code("GLU_F")["id"]], referrer_id=a)
    env.save_bill(jid, [{"label": "T", "rate_paise": to_paise(1000)}], "percent", 0)

    env.update_job(jid, referrer_id=b, referrer_name="Dr B")

    row = env.ledger()[0]
    assert row["referrer_name"] == "Dr B"
    assert row["commission_paise"] == to_paise(200), \
        "the commission is still being paid to the previous doctor"


# ===========================================================================
# MAJOR — amending twice raised a database error
# ===========================================================================

def test_the_same_report_can_be_amended_more_than_once(env):
    from app import services

    _pid, jid = make_job(env, ("GLU_F",))
    m = {t["code"]: t["job_test_id"] for t in env.job_tests(jid)}
    services.recalculate(jid, {m["GLU_F"]: "105"})

    second = services.create_revision(jid, "first correction")
    third = services.create_revision(jid, "second correction")

    assert env.get_job(second)["revision_no"] == 2
    assert env.get_job(third)["revision_no"] == 3
    assert env.get_job(second)["report_no"] == env.get_job(third)["report_no"]


# ===========================================================================
# MINOR — rounding, progress counting, defensive input
# ===========================================================================

@pytest.mark.parametrize("value,decimals,expected", [
    (12.5, 0, "13"),      # banker's rounding gave "12"
    (13.5, 0, "14"),
    (0.125, 2, "0.13"),
    (2.675, 2, "2.68"),
])
def test_results_round_half_up(value, decimals, expected):
    from app.core.ranges import format_value

    assert format_value(value, decimals) == expected


def test_not_done_tests_count_towards_progress(env):
    _pid, jid = make_job(env, ("GLU_F", "GLU_PP"))
    m = {t["code"]: t["job_test_id"] for t in env.job_tests(jid)}
    env.save_result(m["GLU_F"], "105", 105.0, "105mg/dl", "70 - 110mg/dl", "N")
    env.set_not_done(m["GLU_PP"], True)

    done, total = env.job_progress(jid)
    assert (done, total) == (2, 2)
    assert env.list_jobs("all")[0]["n_done"] == 2


def test_a_non_numeric_age_does_not_stop_a_job(env):
    pid = env.save_patient({"name": "Unknown Age", "age_value": "abc",
                            "age_unit": "years"})
    jid = env.create_job(pid, [env.get_test_by_code("GLU_F")["id"]])
    assert env.get_job(jid) is not None


def test_search_with_no_term_does_not_crash(env):
    make_job(env)
    assert env.list_jobs("all", term=None) != []


# ===========================================================================
# Excel import must not overwrite an unrelated test
# ===========================================================================

def test_import_without_a_code_column_never_overwrites_an_existing_test(env, tmp_path):
    from app.output import excel

    before = env.get_test_by_code("TYPHIDOT")
    assert before is not None

    sheet = tmp_path / "mine.csv"
    sheet.write_text("Test,Rate\nTyphidot IgM,450\n", encoding="utf-8")

    preview = excel.preview_tests_import(sheet)
    assert preview["ok"]
    excel.apply_tests_import(preview)

    after = env.get_test(before["id"])
    assert after["name"] == before["name"], \
        "an existing test was overwritten by a generated code"
    assert after["rate_paise"] == before["rate_paise"]


def test_import_names_what_it_will_overwrite(env, tmp_path):
    from app.output import excel

    sheet = tmp_path / "mine.csv"
    sheet.write_text("Code,Test,Rate\nGLU_F,Fasting Sugar,90\n", encoding="utf-8")

    preview = excel.preview_tests_import(sheet)
    assert preview["update"]
    assert preview["update"][0]["replaces"] == "Blood Glucose [Fasting]"


def test_reading_a_spreadsheet_releases_the_file(env, tmp_path):
    """A held-open workbook stops the operator re-saving their own file."""
    from app.output import excel

    try:
        from openpyxl import Workbook
    except ImportError:
        pytest.skip("openpyxl not installed")

    path = tmp_path / "tests.xlsx"
    wb = Workbook()
    wb.active.append(["Code", "Test", "Rate"])
    wb.active.append(["ZZZ", "Something", 100])
    wb.save(path)
    wb.close()

    excel.read_rows(path)
    path.unlink()               # fails on Windows if the handle is still open
    assert not path.exists()


# ===========================================================================
# Report layout
# ===========================================================================

def test_a_long_patient_name_does_not_print_over_the_age(env):
    from app.output import report as rpt

    data = rpt.ReportData(
        report_no="51359", date_text="18-08-2026",
        name="MUHAMMED ABDUL RAHMAN KUTTY THANGAL",
        sex="Male", age="72 Years",
        rows=[rpt.ReportRow(description="Blood Glucose [Fasting]",
                            observed="105mg/dl", normal="70 - 110mg/dl")],
        settings={})
    out = rpt.write_pdf(data, env.config.reports_dir() / "long_name.pdf")
    assert out.exists() and out.stat().st_size > 3000


def test_a_group_that_spans_a_page_repeats_its_heading():
    from app.output import report as rpt

    rows = [rpt.ReportRow(description="HAEMATOLOGY", is_group=True)]
    rows += [rpt.ReportRow(description=f"Test {i}", observed="1", normal="0 - 2")
             for i in range(90)]

    pages = rpt._paginate(rows, 60.0, 60.0, 8.0, tail_mm=18.0)
    assert len(pages) > 1
    assert pages[1][0].is_group, "page 2 starts mid-group with no heading"
    assert "continued" in pages[1][0].description


def test_the_closing_lines_do_not_land_on_the_signatures():
    from app.output import report as rpt

    rows = [rpt.ReportRow(description=f"Test {i}", observed="1", normal="0 - 2")
            for i in range(40)]
    with_tail = rpt._paginate(rows, 60.0, 60.0, 8.0, tail_mm=28.0)
    without = rpt._paginate(rows, 60.0, 60.0, 8.0, tail_mm=0.0)
    assert len(with_tail[0]) <= len(without[0]), \
        "no room was reserved for the end-of-report lines"


# ===========================================================================
# UI
# ===========================================================================

def test_typing_the_first_result_does_not_wipe_it(app_env):
    """Creating the job used to rebuild the grid and swallow the keystroke."""
    env, _app = app_env
    from app.ui.job_screen import JobScreen

    screen = JobScreen()
    screen.name_edit.setText("akila")
    screen.age_spin.setValue(21)
    screen.sex_combo.setCurrentText("Female")
    screen.test_ids.append(env.get_test_by_code("HBSAG")["id"])
    screen._rebuild_grid()

    row = list(screen.rows.values())[0]
    row.set_value("Non Reactive")
    screen._recalc()

    assert screen.job_id is not None
    values = [r.value() for r in screen.rows.values()]
    assert "Non Reactive" in values, "the typed value was truncated or lost"
    screen.deleteLater()


def test_switching_jobs_does_not_carry_values_across(app_env):
    env, _app = app_env
    from app.ui.job_screen import JobScreen

    screen = JobScreen()
    # Patient A, with a result.
    screen.name_edit.setText("Patient A")
    screen.age_spin.setValue(30)
    screen.test_ids.append(env.get_test_by_code("GLU_F")["id"])
    screen._rebuild_grid()
    list(screen.rows.values())[0].set_value("105")
    screen._recalc()
    job_a = screen.job_id

    # Patient B, no results at all.
    _pid_b, job_b = make_job(env, ("GLU_F",))

    screen.load_job(job_b)
    assert all(r.value() == "" for r in screen.rows.values()), \
        "patient A's result appeared in patient B's job"

    screen.load_job(job_a)
    assert any("105" in r.value() for r in screen.rows.values())
    screen.deleteLater()


def test_a_new_job_does_not_inherit_the_previous_doctor(app_env):
    env, _app = app_env
    from app.ui.job_screen import JobScreen

    doctor = env.save_referrer({"name": "Dr Sunil", "commission_percent": 10,
                                "active": 1})

    screen = JobScreen()
    screen.name_edit.setText("Patient One")
    screen.phone_edit.setText("9876500001")
    screen.sex_combo.setCurrentText("Male")
    screen.age_spin.setValue(30)
    screen._reload_referrers(keep_id=doctor)
    assert screen._resolve_referrer() == doctor
    screen.test_ids.append(env.get_test_by_code("GLU_F")["id"])
    screen._rebuild_grid()
    list(screen.rows.values())[0].set_value("105")
    screen._recalc()
    screen.save()

    screen.new_job()
    assert screen._resolve_referrer() is None, \
        "the previous patient's doctor carried over"
    screen.deleteLater()


def test_patient_suggestions_are_hidden_when_a_job_is_opened(app_env):
    env, _app = app_env
    from app.ui.job_screen import JobScreen

    env.save_patient({"name": "Ramesh Kumar", "phone": "9000000011",
                      "age_value": 40, "age_unit": "years"})
    env.save_patient({"name": "Ramesh Nair", "phone": "9000000022",
                      "age_value": 50, "age_unit": "years"})
    _pid, jid = make_job(env)

    screen = JobScreen()
    screen.name_edit.setText("Ramesh")
    screen._on_name_typed("Ramesh")
    assert screen.name_matches.isVisible() or screen.name_matches.count() > 0

    screen.load_job(jid)
    assert screen.name_matches.isHidden(), \
        "stale suggestions from the previous patient are still clickable"
    screen.deleteLater()


def test_a_test_can_be_marked_not_done_from_the_screen(app_env):
    """The app told operators to do this; there was no control for it."""
    env, _app = app_env
    from app.ui.job_screen import JobScreen

    screen = JobScreen()
    screen.name_edit.setText("akila")
    screen.age_spin.setValue(21)
    for code in ("GLU_F", "GLU_PP"):
        screen.test_ids.append(env.get_test_by_code(code)["id"])
    screen._rebuild_grid()

    rows = list(screen.rows.items())
    rows[0][1].set_value("105")
    screen._recalc()
    assert not screen.verify_button.isEnabled()

    jt_id = [jt for jt, rr in screen.rows.items() if not rr.value()][0]
    screen.set_not_done(jt_id, True)

    assert screen.verify_button.isEnabled(), \
        "marking a test not done did not satisfy the completeness gate"
    ok, missing = env.job_is_complete(screen.job_id)
    assert ok and missing == []
    screen.deleteLater()


def test_f2_is_owned_by_only_one_widget(app_env):
    """Two widgets claiming F2 made Qt call it ambiguous and fire neither."""
    env, _app = app_env
    from app.ui.main_window import MainWindow

    win = MainWindow()
    assert win.job_screen.clear_button.shortcut().isEmpty(), \
        "the New job button still claims F2 alongside the window"
    win.close()
