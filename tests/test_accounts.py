"""Sign-in, permissions, bill-first, patient reuse, and the expanded library."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("LABSOFT_HOME", str(tmp_path))
    from app.core import auth
    from app.db import connection

    auth.set_current(None)
    connection.close()
    connection.connect(do_backup=False)
    from app.db import queries as q, seed

    q.ensure_defaults()
    seed.seed_all()
    yield q
    auth.set_current(None)
    connection.close()


@pytest.fixture()
def app_env(env):
    from PyQt6.QtWidgets import QApplication
    from app.ui import style

    app = QApplication.instance() or QApplication([])
    style.apply_light_palette(app)
    app.setStyleSheet(style.STYLESHEET)
    yield env, app


# ===========================================================================
# PINs
# ===========================================================================

def test_a_pin_is_never_stored_in_readable_form():
    from app.core import auth

    stored = auth.hash_pin("2580")
    assert "2580" not in stored
    assert stored.startswith("pbkdf2$")
    assert auth.verify_pin("2580", stored)
    assert not auth.verify_pin("2581", stored)


def test_the_same_pin_hashes_differently_each_time():
    """Salting: two people using 1379 must not have matching rows."""
    from app.core import auth

    assert auth.hash_pin("1379") != auth.hash_pin("1379")


@pytest.mark.parametrize("pin,complaint", [
    ("", "at least"),
    ("123", "at least"),
    ("1234", "guess"),
    ("0000", "guess"),
    ("x" * 40, "fewer"),
])
def test_weak_pins_are_refused(pin, complaint):
    from app.core import auth

    assert complaint in auth.check_pin_quality(pin)


def test_a_reasonable_pin_is_accepted():
    from app.core import auth

    assert auth.check_pin_quality("8461") == ""


def test_verify_survives_rubbish_input():
    from app.core import auth

    assert not auth.verify_pin("1234", "")
    assert not auth.verify_pin("1234", "not-a-hash")
    assert not auth.verify_pin("", auth.hash_pin("8461"))


# ===========================================================================
# Accounts and permissions
# ===========================================================================

def test_admin_can_do_everything_without_ticking_anything(env):
    from app.core import auth

    uid = env.create_user("boss", "Abdunnaser", "8461", auth.ROLE_ADMIN, [])
    user = env.get_user(uid)
    assert all(user.can(p) for p in auth.ALL_PERMISSIONS)


def test_staff_can_only_do_what_was_ticked(env):
    from app.core import auth

    uid = env.create_user("ritu", "Ritu Patil", "7392", auth.ROLE_STAFF,
                          [auth.P_RESULTS, auth.P_SEND])
    user = env.get_user(uid)
    assert user.can(auth.P_RESULTS) and user.can(auth.P_SEND)
    assert not user.can(auth.P_MONEY)
    assert not user.can(auth.P_SETTINGS)
    assert not user.can(auth.P_USERS)


def test_signing_in_needs_the_right_pin(env):
    from app.core import auth

    env.create_user("ritu", "Ritu", "7392", auth.ROLE_STAFF, [auth.P_RESULTS])
    assert env.sign_in("ritu", "0000") is None
    assert env.sign_in("nobody", "7392") is None

    user = env.sign_in("ritu", "7392")
    assert user is not None and user.username == "ritu"
    assert auth.current().username == "ritu"


def test_a_turned_off_account_cannot_sign_in(env):
    from app.core import auth

    uid = env.create_user("temp", "Temp", "5150", auth.ROLE_STAFF, [])
    env.update_user(uid, active=False)
    assert env.sign_in("temp", "5150") is None


def test_usernames_are_unique_and_tidy(env):
    from app.core import auth

    env.create_user("Ritu", "Ritu", "7392", auth.ROLE_STAFF, [])
    assert env.get_user_by_name("ritu") is not None
    with pytest.raises(ValueError, match="already"):
        env.create_user("RITU", "Someone else", "6284", auth.ROLE_STAFF, [])


@pytest.mark.parametrize("name", ["", "a", "way" * 20, "bad!char", "we;drop"])
def test_bad_usernames_are_refused(name):
    from app.core import auth

    assert auth.check_username(name) != ""


def test_spaces_in_a_username_are_forgiven_not_refused():
    """Typing "ritu patil" gives "ritupatil", and signing in the same way works,
    because the login field is normalised identically."""
    from app.core import auth

    assert auth.check_username("ritu patil") == ""
    assert auth.normalise_username("Ritu Patil") == "ritupatil"


def test_the_last_admin_cannot_be_removed(env):
    from app.core import auth

    admin = env.create_user("boss", "Boss", "8461", auth.ROLE_ADMIN, [])
    env.create_user("ritu", "Ritu", "7392", auth.ROLE_STAFF, [auth.P_RESULTS])
    assert env.last_admin_standing(admin) is True

    second = env.create_user("boss2", "Deputy", "9517", auth.ROLE_ADMIN, [])
    assert env.last_admin_standing(admin) is False
    env.update_user(second, active=False)
    assert env.last_admin_standing(admin) is True


def test_with_nobody_signed_in_everything_still_works():
    """A one-person lab that skipped accounts must not be locked out."""
    from app.core import auth

    auth.set_current(None)
    assert all(auth.can(p) for p in auth.ALL_PERMISSIONS)


def test_the_audit_log_records_who_did_it(env):
    from app.core import auth

    env.create_user("ritu", "Ritu Patil", "7392", auth.ROLE_STAFF, [auth.P_RESULTS])
    env.sign_in("ritu", "7392")

    pid = env.save_patient({"name": "P", "age_value": 30, "age_unit": "years"})
    env.create_job(pid, [env.get_test_by_code("GLU_F")["id"]])

    entry = next(a for a in env.recent_audit() if a["action"] == "job_created")
    assert entry["user_name"] == "Ritu Patil"



def tab_names(win):
    """The tab labels without their numbering.

    The shell numbers its tabs -- "03. Patients" -- so that a number means the
    same thing here as it does in the web application. These tests care which
    screens are reachable, not how they are numbered.
    """
    import re

    return [re.sub(r"^\d+\.\s*", "", win.tabs.tabText(i))
            for i in range(win.tabs.count())]


def test_screens_a_person_cannot_use_are_not_shown(app_env):
    env, _app = app_env
    from app.core import auth
    from app.ui.main_window import MainWindow

    uid = env.create_user("ritu", "Ritu", "7392", auth.ROLE_STAFF,
                          [auth.P_RESULTS, auth.P_SEND])
    auth.set_current(env.get_user(uid))

    win = MainWindow()
    tabs = set(tab_names(win))
    assert "Job" in tabs and "Work Queue" in tabs
    assert "Settings" not in tabs, "a staff member can reach Settings"
    assert "Billing" not in tabs
    assert "Tests" not in tabs
    win.close()

    auth.set_current(env.get_user(
        env.create_user("boss", "Boss", "8461", auth.ROLE_ADMIN, [])))
    win2 = MainWindow()
    tabs2 = set(tab_names(win2))
    assert {"Settings", "Billing", "Tests", "Summaries"} <= tabs2
    win2.close()


# ===========================================================================
# Bill first
# ===========================================================================

def make_job(env, screen, codes=("GLU_F",)):
    screen.name_edit.setText("akila")
    screen.age_spin.setValue(21)
    for c in codes:
        screen.test_ids.append(env.get_test_by_code(c)["id"])
    screen._rebuild_grid()
    for r in screen.rows.values():
        if not r.is_derived:
            r.set_value("105")
    screen._recalc()
    return screen.job_id


def test_the_bill_band_sits_above_the_results(app_env):
    """Money is settled at the counter before the work starts, so the band
    carrying it comes before the field the results go into."""
    env, _app = app_env
    from app.ui.job_screen import JobScreen

    screen = JobScreen()
    column = screen.bill_box.parentWidget().layout()
    order = [column.itemAt(i).widget() for i in range(column.count())]

    assert screen.bill_box in order, "the bill band is not in this column"
    band_at = order.index(screen.bill_box)
    results_at = next(i for i, w in enumerate(order)
                      if w is not None and screen.results_box in
                      w.findChildren(type(screen.results_box)) + [w])
    assert band_at < results_at, "billing must come before results"
    screen.deleteLater()


def test_the_bill_band_says_when_nothing_is_billed(app_env):
    env, _app = app_env
    from app.ui.job_screen import JobScreen

    screen = JobScreen()
    make_job(env, screen)
    screen._refresh_bill()
    band = screen.bill_summary.text() + " " + screen.bill_hint.text()
    assert "Not billed" in band
    assert screen.bill_stats["Outstanding"].text() != "—", \
        "the band should show what is owed, not a dash"
    screen.deleteLater()


def test_the_bill_band_shows_the_total_once_billed(app_env):
    env, _app = app_env
    from app.core.billing import to_paise
    from app.ui.job_screen import JobScreen

    screen = JobScreen()
    jid = make_job(env, screen)
    bill_id = env.save_bill(jid, [{"label": "T", "rate_paise": to_paise(600)}],
                            "percent", 0)
    env.add_payment(bill_id, to_paise(600))
    screen._refresh_bill()

    assert "600" in screen.bill_summary.text()
    assert "Paid in full" in screen.bill_hint.text()
    screen.deleteLater()


def test_an_unbilled_report_is_still_possible(app_env, monkeypatch):
    """Warn, never block — an urgent case must not wait on paperwork."""
    env, _app = app_env
    from app import services
    from app.ui.job_screen import JobScreen

    screen = JobScreen()
    jid = make_job(env, screen)
    assert env.get_bill(jid) is None

    ok, missing, path = services.verify_job(jid)
    assert ok and path.exists(), "a report could not be made without a bill"
    screen.deleteLater()


def test_the_bill_band_is_hidden_from_staff_who_cannot_bill(app_env):
    env, _app = app_env
    from app.core import auth
    from app.ui.job_screen import JobScreen

    uid = env.create_user("ritu", "Ritu", "7392", auth.ROLE_STAFF, [auth.P_RESULTS])
    auth.set_current(env.get_user(uid))

    screen = JobScreen()
    screen._refresh_bill()
    assert screen.bill_box.isHidden()
    screen.deleteLater()


# ===========================================================================
# Finding and reusing a patient
# ===========================================================================

@pytest.fixture()
def people(env):
    env.save_patient({"name": "FARAS .M. Kutty", "phone": "9876543210",
                      "sex": "Male", "age_value": 31, "age_unit": "years"})
    env.save_patient({"name": "Sunita Devi", "phone": "9123456780",
                      "sex": "Female", "age_value": 40, "age_unit": "years"})
    env.save_patient({"name": "Ramesh Kumar Nair", "phone": "9000000011",
                      "sex": "Male", "age_value": 52, "age_unit": "years"})
    return env


@pytest.mark.parametrize("typed,expected", [
    ("far", "FARAS .M. Kutty"),         # start of the first name
    ("FAR", "FARAS .M. Kutty"),         # case does not matter
    ("fmk", "FARAS .M. Kutty"),         # initials
    ("f.m", "FARAS .M. Kutty"),         # initials with punctuation
    ("kutty", "FARAS .M. Kutty"),       # a later word
    ("43210", "FARAS .M. Kutty"),       # part of the mobile number
    ("sun", "Sunita Devi"),
    ("rkn", "Ramesh Kumar Nair"),       # initials again
    ("nair", "Ramesh Kumar Nair"),
])
def test_a_patient_is_found_from_very_little_typing(people, typed, expected):
    results = people.search_patients(typed, limit=5)
    assert results, f"nothing found for “{typed}”"
    assert results[0]["name"] == expected, \
        f"“{typed}” gave {results[0]['name']}, expected {expected}"


def test_a_search_that_matches_nobody_returns_nothing(people):
    assert people.search_patients("zzzzz") == []


def test_an_empty_search_offers_the_most_recent_patients(people):
    assert len(people.search_patients("")) == 3


def test_the_most_recent_visitor_comes_first_among_equals(env):
    from datetime import datetime, timedelta

    a = env.save_patient({"name": "Ramesh One", "age_value": 30, "age_unit": "years"})
    b = env.save_patient({"name": "Ramesh Two", "age_value": 30, "age_unit": "years"})
    tid = env.get_test_by_code("GLU_F")["id"]
    env.create_job(a, [tid], received=datetime.now() - timedelta(days=30))
    env.create_job(b, [tid], received=datetime.now())

    assert env.search_patients("ramesh")[0]["name"] == "Ramesh Two"


def test_picking_a_patient_fills_their_details_in(app_env):
    env, _app = app_env
    from app.ui.job_screen import JobScreen
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QListWidgetItem

    pid = env.save_patient({"name": "FARAS .M.", "phone": "9876543210",
                            "sex": "Male", "age_value": 31, "age_unit": "years"})

    screen = JobScreen()
    screen.name_edit.setText("fm")
    screen._on_name_typed("fm")
    assert screen.name_matches.count() >= 1

    screen._pick_existing_patient(screen.name_matches.item(0))
    assert screen.patient_id == pid
    assert screen.name_edit.text() == "FARAS .M."
    assert screen.phone_edit.text() == "9876543210"
    assert screen.age_spin.value() == 31
    assert screen.sex_combo.currentText() == "Male"
    screen.deleteLater()


def test_a_returning_patient_can_repeat_their_last_tests(app_env):
    env, _app = app_env
    from app import services
    from app.ui.job_screen import JobScreen

    pid = env.save_patient({"name": "Anil Sharma", "phone": "9988776655",
                            "sex": "Male", "age_value": 52, "age_unit": "years"})
    codes = ["GLU_F", "GLU_PP", "HBA1C"]
    first = env.create_job(pid, [env.get_test_by_code(c)["id"] for c in codes])
    m = {t["code"]: t["job_test_id"] for t in env.job_tests(first)}
    services.recalculate(first, {m["GLU_F"]: "148", m["GLU_PP"]: "212",
                                 m["HBA1C"]: "7.8"})

    screen = JobScreen()
    screen.name_edit.setText("anil")
    screen._on_name_typed("anil")
    screen._pick_existing_patient(screen.name_matches.item(0))

    assert screen.repeat_row is not None
    screen._repeat_last_tests()

    got = {t["code"] for t in
           [env.get_test(tid) for tid in screen.test_ids]}
    assert got == set(codes), "the previous visit's tests were not carried over"
    screen.deleteLater()


def test_repeat_does_nothing_for_a_brand_new_patient(app_env):
    env, _app = app_env
    from app.ui.job_screen import JobScreen

    screen = JobScreen()
    screen.name_edit.setText("Nobody New")
    assert screen._previous_test_ids() == []
    screen.deleteLater()


# ===========================================================================
# The expanded library
# ===========================================================================

def test_the_library_now_covers_the_common_departments(env):
    codes = {t["code"] for t in env.list_tests()}
    for code in ("ANC", "ALC", "AEC", "APTT", "DDIMER", "TIBC", "TSAT",
                 "FSH", "LH", "PRL", "TESTO", "BHCG", "CORT", "PTH",
                 "AFP", "CEA", "CA125", "TROPI", "NTPROBNP", "HSCRP",
                 "MG", "ANGAP", "CACORR", "HOMAIR", "U_ACR", "SM_COUNT",
                 "CUL_URINE", "HPYLORI", "MANTOUX"):
        assert code in codes, f"{code} is missing from the library"


def test_the_library_is_substantially_bigger(env):
    assert len(env.list_tests()) >= 165


def test_the_new_groups_exist(env):
    groups = set(env.test_groups())
    assert {"COAGULATION PROFILE", "IRON STUDIES", "HORMONE ASSAY",
            "TUMOUR MARKERS", "CARDIAC PROFILE", "CULTURE & SENSITIVITY",
            "SEMEN ANALYSIS"} <= groups


def test_the_new_panels_exist(env):
    names = {p["name"] for p in env.list_panels()}
    assert {"Iron Studies", "Anaemia Profile", "Full Body Checkup",
            "PCOS Profile", "Coagulation Profile"} <= names


def test_every_panel_actually_contains_tests(env):
    for panel in env.list_panels():
        assert env.panel_test_ids(panel["id"]), \
            f"panel “{panel['name']}” is empty — a code must be misspelled"


@pytest.mark.parametrize("codes,typed,code,expected", [
    (["TC", "NEU", "ANC"], {"TC": "8200", "NEU": "62"}, "ANC", "5084cells/cumm"),
    (["TC", "LYM", "ALC"], {"TC": "8200", "LYM": "28"}, "ALC", "2296cells/cumm"),
    (["CA", "ALB", "CACORR"], {"CA": "8.2", "ALB": "2.9"}, "CACORR", "9.1mg/dl"),
    (["NA", "CL", "BICARB", "ANGAP"],
     {"NA": "140", "CL": "104", "BICARB": "24"}, "ANGAP", "12mmol/L"),
    (["IRON", "TIBC", "TSAT"], {"IRON": "60", "TIBC": "400"}, "TSAT", "15.0%"),
    (["HBA1C", "EAG"], {"HBA1C": "7.8"}, "EAG", "177mg/dl"),
    (["GLU_F", "INSULIN", "HOMAIR"],
     {"GLU_F": "110", "INSULIN": "18.5"}, "HOMAIR", "5.02"),
    (["CHOL", "HDL", "NONHDL"], {"CHOL": "212", "HDL": "38"}, "NONHDL", "174mg/dl"),
    (["SM_VOL", "SM_COUNT", "SM_TOTAL"],
     {"SM_VOL": "3.2", "SM_COUNT": "42"}, "SM_TOTAL", "134.4million"),
    (["U_MALB", "U_CREAT", "U_ACR"],
     {"U_MALB": "45", "U_CREAT": "110"}, "U_ACR", "40.9mg/g"),
])
def test_the_new_calculations_are_right(env, codes, typed, code, expected):
    from app import services

    pid = env.save_patient({"name": "Calc", "sex": "Male",
                            "age_value": 45, "age_unit": "years"})
    jid = env.create_job(pid, [env.get_test_by_code(c)["id"] for c in codes])
    m = {t["code"]: t["job_test_id"] for t in env.job_tests(jid)}
    out = services.recalculate(jid, {m[k]: v for k, v in typed.items()})
    assert out[m[code]]["display"] == expected


def test_a_calculated_test_stays_blank_without_its_inputs(env):
    from app import services

    pid = env.save_patient({"name": "Calc", "age_value": 45, "age_unit": "years"})
    codes = ["TC", "NEU", "ANC"]
    jid = env.create_job(pid, [env.get_test_by_code(c)["id"] for c in codes])
    m = {t["code"]: t["job_test_id"] for t in env.job_tests(jid)}

    out = services.recalculate(jid, {m["TC"]: "8200"})       # NEU left empty
    assert out[m["ANC"]]["display"] == ""


def test_new_tests_reach_an_existing_installation(env):
    """A lab that installed last month must get the new tests on upgrade."""
    from app.db import seed

    test = env.get_test_by_code("TROPI")
    env.delete_test(test["id"])                  # pretend it was never shipped
    with env.transaction() as c:
        c.execute("DELETE FROM tests WHERE id = ?", (test["id"],))

    added = seed.seed_all()
    assert added >= 1
    assert env.get_test_by_code("TROPI") is not None


def test_topping_up_never_disturbs_an_edited_test(env):
    from app.db import seed

    original = env.get_test_by_code("GLU_F")
    env.save_test({**dict(original), "name": "Fasting Sugar (our wording)",
                   "rate_paise": 12345})

    seed.seed_all()

    after = env.get_test_by_code("GLU_F")
    assert after["name"] == "Fasting Sugar (our wording)"
    assert after["rate_paise"] == 12345


def test_a_hidden_test_does_not_come_back(env):
    from app.db import seed

    test = env.get_test_by_code("PSA")
    env.delete_test(test["id"])
    seed.seed_all()
    assert env.get_test(test["id"])["active"] == 0
