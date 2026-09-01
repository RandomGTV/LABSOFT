"""Patients with initials, doctors with a hospital, staff logins, and search.

Everything here was asked for by the lab after using the program, so each test
stands for a way the software did not fit the way they actually work.
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
    from app.core import auth
    from app.db import queries as q, seed

    # Whoever a previous test signed in must not decide what this one can see.
    auth.set_current(None)
    q.ensure_defaults()
    seed.seed_all()
    yield q
    auth.set_current(None)
    connection.close()


@pytest.fixture()
def screen(env, qt_app):
    from app.ui.job_screen import JobScreen

    s = JobScreen()
    yield s
    s.deleteLater()


# ===========================================================================
# The patient's initial
# ===========================================================================

def test_the_initial_prints_between_the_names():
    from app.db.queries import full_name

    assert full_name("FARAS Kutty", "M") == "FARAS .M. Kutty"
    assert full_name("FARAS", "M") == "FARAS .M."
    assert full_name("FARAS Kutty", "") == "FARAS Kutty"


def test_the_initial_is_tidied_however_it_is_typed():
    from app.db.queries import full_name

    for typed in ("m", "M", ".m.", "m."):
        assert full_name("FARAS Kutty", typed) == "FARAS .M. Kutty"


def test_a_patient_can_be_found_by_their_initials(env):
    env.save_patient({"name": "FARAS Kutty", "initial": "M",
                      "phone": "9876543210", "sex": "Male",
                      "age_value": 34, "age_unit": "years"})

    for typed in ("fmk", "f.m", "faras", "kutty", "43210"):
        found = env.search_patients(typed)
        assert found and found[0]["name"] == "FARAS Kutty", \
            f"typing {typed!r} did not find the patient"


def test_the_report_carries_the_name_as_printed(env):
    from app import services

    pid = env.save_patient({"name": "FARAS Kutty", "initial": "M",
                            "phone": "9876543210", "sex": "Male",
                            "age_value": 34, "age_unit": "years"})
    jid = env.create_job(pid, [env.get_test_by_code("GLU_F")["id"]])
    jt = env.job_tests(jid)[0]["job_test_id"]
    services.recalculate(jid, {jt: "105"})

    assert services.build_report_data(jid).name == "FARAS .M. Kutty"


def test_correcting_a_name_later_does_not_rewrite_an_old_report(env):
    """What a report said when it went out has to stay said."""
    pid = env.save_patient({"name": "FARAS Kutty", "initial": "M",
                            "phone": "9876543210", "sex": "Male"})
    jid = env.create_job(pid, [env.get_test_by_code("GLU_F")["id"]])
    env.save_patient({"id": pid, "name": "FIRAS Kutty", "initial": "K"})

    assert env.get_job(jid)["name_at_test"] == "FARAS .M. Kutty"


def test_the_job_screen_shows_what_will_print(screen):
    screen.name_edit.setText("FARAS Kutty")
    screen.initial_edit.setText("m")
    screen._refresh_printed_name()

    assert screen.printed_name_text() == "FARAS .M. Kutty"
    assert "FARAS .M. Kutty" in screen.printed_name.text()


# ===========================================================================
# Name, mobile and sex are required
# ===========================================================================

def test_a_job_cannot_be_saved_without_the_three_important_fields(screen):
    assert screen.patient_problem()[0] == "the patient's name"

    screen.name_edit.setText("Ramesh")
    assert screen.patient_problem()[0] == "a mobile number"

    screen.phone_edit.setText("9876543210")
    assert screen.patient_problem()[0] == "the patient's sex"

    screen.sex_combo.setCurrentText("Male")
    assert screen.patient_problem() is None


def test_what_is_missing_is_shown_before_the_end(screen):
    """Not only in the dialog at the end — by then results have been typed."""
    screen.name_edit.setText("Ramesh")
    screen._refresh_printed_name()

    assert "mobile" in screen.printed_name.text().lower()


def test_results_typed_before_the_number_arrives_are_still_kept(env, screen):
    """The rule blocks finishing a job, never saving work in progress.

    Holding results until reception fetches the mobile number would mean a
    screenful of typing kept nowhere, which is a worse failure than a draft
    with a missing field.
    """
    screen.name_edit.setText("Ramesh")
    screen.test_ids.append(env.get_test_by_code("GLU_F")["id"])
    screen._rebuild_grid()
    list(screen.rows.values())[0].set_value("105")
    screen._recalc()

    assert screen.job_id is not None
    stored = env.results_for_job(screen.job_id)
    assert any((r.get("display_value") or "").strip() for r in stored.values())


def test_save_refuses_and_says_why(env, screen, monkeypatch):
    import app.ui.job_screen as mod

    said = []
    monkeypatch.setattr(mod, "warn", lambda *a, **k: said.append(a))

    screen.name_edit.setText("Ramesh")
    screen.test_ids.append(env.get_test_by_code("GLU_F")["id"])
    screen._rebuild_grid()
    screen.save()

    assert said, "the operator was told nothing"
    assert "mobile" in " ".join(str(x) for x in said[0]).lower()


# ===========================================================================
# Doctors
# ===========================================================================

def test_a_doctor_keeps_their_profession_and_hospital(env):
    rid = env.save_referrer({"name": "Dr S. Mehta", "profession": "Cardiologist",
                             "hospital": "City Heart Centre",
                             "phone": "9800011122", "qualification": "MBBS, MD",
                             "commission_percent": 10, "active": 1})
    r = next(x for x in env.list_referrers() if x["id"] == rid)

    assert r["profession"] == "Cardiologist"
    assert r["hospital"] == "City Heart Centre"
    assert r["phone"] == "9800011122"


def test_a_doctor_added_in_a_hurry_still_saves(env):
    """The quick add on the job screen predates these columns."""
    rid = env.save_referrer({"name": "Dr Quick", "commission_percent": 0,
                             "active": 1})
    r = next(x for x in env.list_referrers() if x["id"] == rid)

    assert r["profession"] == "" and r["hospital"] == ""


def test_doctors_can_be_searched_every_way_they_are_remembered(env):
    env.save_referrer({"name": "Dr S. Mehta", "profession": "Cardiologist",
                       "hospital": "City Heart Centre", "phone": "9800011122",
                       "commission_percent": 0, "active": 1})
    env.save_referrer({"name": "Dr A. Iyer", "profession": "Paediatrician",
                       "hospital": "Kuttippala Clinic", "phone": "9800033344",
                       "commission_percent": 0, "active": 1})

    assert len(env.search_referrers("mehta")) == 1
    assert len(env.search_referrers("paediat")) == 1
    assert len(env.search_referrers("clinic")) == 1
    assert len(env.search_referrers("011122")) == 1
    assert len(env.search_referrers("")) == 2


def test_removing_a_doctor_hides_them_and_keeps_the_history(env):
    """Old jobs point at this doctor, and so do unpaid commissions."""
    rid = env.save_referrer({"name": "Dr Gone", "commission_percent": 0,
                             "active": 1})
    pid = env.save_patient({"name": "P", "phone": "9", "sex": "Male"})
    jid = env.create_job(pid, [env.get_test_by_code("GLU_F")["id"]],
                         referrer_id=rid)

    env.delete_referrer(rid)

    assert not any(r["id"] == rid for r in env.list_referrers())
    assert any(r["id"] == rid for r in env.list_referrers(include_inactive=True))
    assert env.get_job(jid)["referrer_id"] == rid


def test_the_picker_says_where_to_find_the_doctor(env):
    r = {"name": "Dr S. Mehta", "profession": "Cardiologist",
         "hospital": "City Heart Centre"}

    assert env.referrer_label(r) == "Dr S. Mehta — Cardiologist · City Heart Centre"
    assert env.referrer_label({"name": "Dr Plain"}) == "Dr Plain"


def test_the_doctors_screen_lists_and_filters(env, qt_app):
    from app.ui.doctors_screen import DoctorsScreen

    env.save_referrer({"name": "Dr S. Mehta", "profession": "Cardiologist",
                       "hospital": "City Heart Centre", "commission_percent": 0,
                       "active": 1})
    env.save_referrer({"name": "Dr A. Iyer", "profession": "Paediatrician",
                       "commission_percent": 0, "active": 1})

    s = DoctorsScreen()
    try:
        assert s.table.rowCount() == 2
        s.search.setText("cardio")
        s.refresh()
        assert s.table.rowCount() == 1
    finally:
        s.deleteLater()


# ===========================================================================
# Choosing the doctor on the job screen
# ===========================================================================

def test_the_doctor_is_chosen_from_the_list(env, screen):
    rid = env.save_referrer({"name": "Dr S. Mehta", "profession": "Cardiologist",
                             "hospital": "City Heart Centre",
                             "commission_percent": 10, "active": 1})
    screen._reload_referrers()

    assert screen.referrer_combo.findData(rid) > 0
    screen._select_referrer(rid)
    assert screen._resolve_referrer() == rid
    assert screen._referrer_name() == "Dr S. Mehta", \
        "the hospital shown in the picker must not end up on the report"


def test_choosing_none_leaves_the_job_without_a_doctor(env, screen):
    env.save_referrer({"name": "Dr S. Mehta", "commission_percent": 0,
                       "active": 1})
    screen._reload_referrers()
    screen._select_referrer(None)

    assert screen._resolve_referrer() is None
    assert screen._referrer_name() == ""


def test_the_list_offers_a_way_to_add_a_doctor(env, screen):
    screen._reload_referrers()
    last = screen.referrer_combo.count() - 1

    assert screen.referrer_combo.itemData(last) == screen.ADD_DOCTOR
    screen.referrer_combo.setCurrentIndex(last)
    assert screen._resolve_referrer() is None, \
        "the add-a-doctor entry must never be saved as a doctor"


# ===========================================================================
# Staff logins
# ===========================================================================

def test_an_administrator_can_create_a_login(env, qt_app):
    from app.core import auth
    from app.ui.users_dialog import UserEditor

    editor = UserEditor(None)
    try:
        editor.name_edit.setText("Ritu Patil")
        editor.user_edit.setText("ritu")
        editor.pin_edit.setText("7392")
        editor._save()
    finally:
        editor.deleteLater()

    user = env.sign_in("ritu", "7392")
    assert user and user.display_name == "Ritu Patil"
    assert user.can(auth.P_RESULTS)
    assert not user.can(auth.P_SETTINGS)


def test_the_staff_screen_lists_and_filters(env, qt_app):
    from app.ui.staff_screen import StaffScreen

    env.create_user("ritu", "Ritu Patil", "7392", "staff", ["results"])
    env.create_user("saheed", "Saheed Mohamed", "5150", "staff", ["bill"])

    s = StaffScreen()
    try:
        assert s.table.rowCount() == 2
        s.search.setText("ritu")
        s.refresh()
        assert s.table.rowCount() == 1
    finally:
        s.deleteLater()


def test_staff_is_a_tab_of_its_own_for_an_administrator(env, qt_app):
    from app.ui.main_window import MainWindow

    win = MainWindow()
    try:
        names = [win.tabs.tabText(i) for i in range(win.tabs.count())]
        assert "Staff" in names
        assert "Doctors" in names
    finally:
        win.close()
        win.deleteLater()


def test_staff_and_settings_are_hidden_from_ordinary_staff(env, qt_app):
    from app.core import auth
    from app.ui.main_window import MainWindow

    env.create_user("ritu", "Ritu Patil", "7392", "staff", ["results", "send"])
    auth.set_current(env.sign_in("ritu", "7392"))
    win = MainWindow()
    try:
        names = [win.tabs.tabText(i) for i in range(win.tabs.count())]
        assert "Staff" not in names
        assert "Settings" not in names
        assert "Doctors" in names, "everyone needs to know who referred a patient"
    finally:
        win.close()
        win.deleteLater()
        auth.set_current(None)


# ===========================================================================
# Search
# ===========================================================================

def test_every_list_has_a_search_box(env, qt_app):
    from app.ui.billing_screen import BillingScreen
    from app.ui.doctors_screen import DoctorsScreen
    from app.ui.patients_screen import PatientsScreen
    from app.ui.queue_screen import QueueScreen
    from app.ui.staff_screen import StaffScreen
    from app.ui.tests_screen import TestsScreen
    from app.ui.widgets import SearchBox

    for cls in (QueueScreen, PatientsScreen, TestsScreen, BillingScreen,
                DoctorsScreen, StaffScreen):
        s = cls()
        try:
            assert isinstance(getattr(s, "search", None), SearchBox), \
                f"{cls.__name__} has nothing to search with"
        finally:
            s.deleteLater()


def test_the_ledger_can_be_searched(env, qt_app):
    from app import services
    from app.ui.billing_screen import BillingScreen

    for name, phone in (("Anil Sharma", "9988776655"),
                        ("Sunita Devi", "9123456780")):
        pid = env.save_patient({"name": name, "phone": phone, "sex": "Male"})
        jid = env.create_job(pid, [env.get_test_by_code("GLU_F")["id"]])
        env.save_bill(jid, services.suggest_bill_items(jid), "percent", 0)

    s = BillingScreen()
    try:
        assert s.table.rowCount() == 2
        s.search.setText("sunita")
        s.refresh()
        assert s.table.rowCount() == 1
        s.search.setText("776655")
        s.refresh()
        assert s.table.rowCount() == 1
        s.search.setText("")
        s.refresh()
        assert s.table.rowCount() == 2
    finally:
        s.deleteLater()


def test_ctrl_f_searches_the_screen_you_are_on(env, qt_app):
    from app.ui.main_window import MainWindow

    win = MainWindow()
    try:
        names = [win.tabs.tabText(i) for i in range(win.tabs.count())]
        win.tabs.setCurrentIndex(names.index("Patients"))
        win._focus_search()
        assert win.tabs.currentWidget() is win.patients_screen, \
            "Ctrl+F threw away what the operator was doing"
    finally:
        win.close()
        win.deleteLater()
