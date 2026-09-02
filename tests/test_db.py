"""Database, seeding, and the result-calculation pipeline end to end."""

import os
from datetime import datetime, timedelta

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LABSOFT_HOME", str(tmp_path))
    # Re-import with the temp home in place.
    from app.db import connection
    connection.close()
    conn = connection.connect(do_backup=False)
    from app.db import queries as q, seed
    q.ensure_defaults()
    seed.seed_all()
    yield q
    connection.close()


# --------------------------------------------------------------------- seed

def test_library_seeds_once(db):
    tests = db.list_tests()
    assert len(tests) > 90
    assert {t["code"] for t in tests} >= {"HB", "GLU_F", "GLU_PP", "TP", "ALB", "GLOB"}

    from app.db import seed
    assert seed.seed_all() == 0     # second call is a no-op


def test_seeded_ranges_match_the_labs_wording(db):
    t = db.get_test_by_code("GLU_F")
    rows = db.ranges_for_test(t["id"])
    assert rows[0]["display_text"] == "70 - 110mg/dl"

    t2 = db.get_test_by_code("GLU_PP")
    assert db.ranges_for_test(t2["id"])[0]["display_text"] == "70 - 140mg/dl"


def test_panels_seeded_with_quick_buttons(db):
    quick = {p["name"] for p in db.list_panels(quick_only=True)}
    assert "CBC" in quick and "Lipid Profile" in quick
    cbc = next(p for p in db.list_panels() if p["name"] == "CBC")
    assert len(db.panel_test_ids(cbc["id"])) == 14


def test_every_seeded_formula_parses(db):
    from app.core import formula
    for t in db.list_tests():
        if (t["formula"] or "").strip():
            formula.parse(t["formula"])       # must not raise


def test_seeded_formulas_have_no_cycles(db):
    from app.core import formula
    forms = {t["code"]: t["formula"] for t in db.list_tests() if (t["formula"] or "").strip()}
    assert formula.check_cycles(forms) == []


def test_seeded_formula_codes_all_exist(db):
    from app.core import formula
    codes = {t["code"].upper() for t in db.list_tests()}
    for t in db.list_tests():
        f = (t["formula"] or "").strip()
        if f:
            missing = formula.codes_used(f) - codes
            assert not missing, f"{t['code']} refers to unknown {missing}"


# ------------------------------------------------------------------ settings

def test_settings_defaults_and_override(db):
    assert db.get_setting("lab_name") == "MITHRA"
    db.set_setting("lab_name", "New MITHRA LAB")
    assert db.get_setting("lab_name") == "New MITHRA LAB"
    assert db.all_settings()["lab_name"] == "New MITHRA LAB"


# ------------------------------------------------------------------ patients

def test_save_and_find_patient(db):
    pid = db.save_patient({"name": "FARAS .M.", "phone": "9876543210",
                           "sex": "Female", "age_value": 31, "age_unit": "years"})
    assert pid > 0
    assert db.get_patient(pid)["name"] == "FARAS .M."
    assert db.search_patients("faras")[0]["id"] == pid
    assert db.search_patients("98765")[0]["id"] == pid


# ---------------------------------------------------------------------- jobs

def make_job(db, codes=("GLU_F", "GLU_PP")):
    pid = db.save_patient({"name": "FARAS .M.", "phone": "9876543210",
                           "sex": "Female", "age_value": 31, "age_unit": "years"})
    ids = [db.get_test_by_code(c)["id"] for c in codes]
    return pid, db.create_job(pid, ids)


def test_report_numbers_continue_the_series(db):
    db.set_setting("next_report_no", "51359")
    _p, j1 = make_job(db)
    _p, j2 = make_job(db)
    assert db.get_job(j1)["report_no"] == 51359
    assert db.get_job(j2)["report_no"] == 51360


def test_report_numbers_are_never_duplicated(db):
    seen = set()
    for _ in range(25):
        _p, jid = make_job(db)
        n = db.get_job(jid)["report_no"]
        assert n not in seen
        seen.add(n)


def test_report_number_recovers_if_setting_is_stale(db):
    """A hand-edited setting must not collide with numbers already issued."""
    _p, j1 = make_job(db)
    first = db.get_job(j1)["report_no"]
    db.set_setting("next_report_no", str(first))     # points at a used number
    _p, j2 = make_job(db)
    assert db.get_job(j2)["report_no"] == first + 1


def test_job_snapshots_patient_details(db):
    """Age and sex are frozen so an old report never silently changes."""
    pid, jid = make_job(db)
    job = db.get_job(jid)
    assert job["age_at_test"] == "31 Years"
    assert job["sex_at_test"] == "Female"

    db.save_patient({"id": pid, "name": "FARAS M", "phone": "9876543210",
                     "sex": "Male", "age_value": 45, "age_unit": "years"})
    again = db.get_job(jid)
    assert again["age_at_test"] == "31 Years"
    assert again["sex_at_test"] == "Female"


def test_due_date_from_slowest_test(db):
    pid = db.save_patient({"name": "X", "age_value": 30, "age_unit": "years"})
    ids = [db.get_test_by_code(c)["id"] for c in ("GLU_F", "HBA1C")]  # 4h and 24h
    jid = db.create_job(pid, ids, received=datetime(2026, 8, 18, 9, 0))
    job = db.get_job(jid)
    assert db.to_dt(job["due_at"]) == datetime(2026, 8, 19, 9, 0)


def test_changing_tests_keeps_results_and_updates_due(db):
    _p, jid = make_job(db, ("GLU_F", "GLU_PP"))
    jts = {t["code"]: t["job_test_id"] for t in db.job_tests(jid)}
    db.save_result(jts["GLU_F"], "105", 105.0, "105mg/dl", "70 - 110mg/dl", "N")

    keep = db.get_test_by_code("GLU_F")["id"]
    add = db.get_test_by_code("HBA1C")["id"]
    db.set_job_tests(jid, [keep, add])

    codes = {t["code"] for t in db.job_tests(jid)}
    assert codes == {"GLU_F", "HBA1C"}
    results = db.results_for_job(jid)
    assert any(r["display_value"] == "105mg/dl" for r in results.values())


def test_completeness_gate(db):
    _p, jid = make_job(db)
    ok, missing = db.job_is_complete(jid)
    assert not ok and len(missing) == 2

    jts = {t["code"]: t["job_test_id"] for t in db.job_tests(jid)}
    db.save_result(jts["GLU_F"], "105", 105.0, "105mg/dl", "70 - 110mg/dl", "N")
    ok, missing = db.job_is_complete(jid)
    assert not ok and missing == ["Blood Glucose [ P P 2 hrs ]"]

    db.set_not_done(jts["GLU_PP"], True)
    ok, missing = db.job_is_complete(jid)
    assert ok and missing == []


def test_empty_job_is_not_complete(db):
    pid = db.save_patient({"name": "Y", "age_value": 20, "age_unit": "years"})
    jid = db.create_job(pid, [])
    ok, _ = db.job_is_complete(jid)
    assert not ok


# ------------------------------------------------------------------- billing

def test_bill_payments_and_commission(db):
    from app.core.billing import to_paise
    ref = db.save_referrer({"name": "Dr. S. Mehta", "qualification": "MD",
                            "phone": "", "commission_percent": 10, "active": 1})
    pid = db.save_patient({"name": "Ramesh", "age_value": 45, "age_unit": "years"})
    tid = db.get_test_by_code("GLU_F")["id"]
    jid = db.create_job(pid, [tid], referrer_id=ref)

    bill_id = db.save_bill(jid, [{"label": "Blood Glucose [Fasting]",
                                  "rate_paise": to_paise(1450), "qty": 1}],
                           "percent", 10)
    t = db.bill_totals(jid)
    assert t.net_paise == to_paise(1305)
    assert t.balance_paise == to_paise(1305)

    db.add_payment(bill_id, to_paise(1000))
    t = db.bill_totals(jid)
    assert t.balance_paise == to_paise(305)

    rows = db.ledger()
    assert rows[0]["commission_paise"] == to_paise(130.5)


def test_job_reports_fine_with_no_bill(db):
    """Billing must never be a precondition for a report."""
    _p, jid = make_job(db)
    assert db.get_bill(jid) is None
    assert db.bill_totals(jid).net_paise == 0


def test_ledger_unpaid_filter(db):
    from app.core.billing import to_paise
    _p, jid = make_job(db)
    bid = db.save_bill(jid, [{"label": "T", "rate_paise": to_paise(600)}], "percent", 0)
    assert len(db.ledger(unpaid_only=True)) == 1
    db.add_payment(bid, to_paise(600))
    assert db.ledger(unpaid_only=True) == []


# --------------------------------------------------------------------- queue

def test_queue_scopes_and_counts(db):
    _p, jid = make_job(db)
    assert len(db.list_jobs("today")) == 1
    assert len(db.list_jobs("pending")) == 1
    assert db.list_jobs("ready") == []

    counts = db.queue_counts()
    assert counts["today"] == 1 and counts["pending"] == 1

    db.update_job(jid, status="ready")
    assert len(db.list_jobs("ready")) == 1
    assert db.queue_counts()["pending"] == 0


def test_search_finds_by_report_number_and_phone(db):
    _p, jid = make_job(db)
    no = db.get_job(jid)["report_no"]
    assert len(db.list_jobs("all", term=str(no))) == 1
    assert len(db.list_jobs("all", term="98765")) == 1


def test_overdue_only_counts_unfinished(db):
    pid = db.save_patient({"name": "Z", "age_value": 20, "age_unit": "years"})
    tid = db.get_test_by_code("GLU_F")["id"]
    jid = db.create_job(pid, [tid], received=datetime.now() - timedelta(days=2))
    assert db.queue_counts()["overdue"] == 1
    db.update_job(jid, status="sent")
    assert db.queue_counts()["overdue"] == 0


def test_previous_results_for_history(db):
    pid = db.save_patient({"name": "Repeat", "age_value": 40, "age_unit": "years"})
    tid = db.get_test_by_code("GLU_F")["id"]
    for value in ("101", "112"):
        jid = db.create_job(pid, [tid])
        jt = db.job_tests(jid)[0]["job_test_id"]
        db.save_result(jt, value, float(value), f"{value}mg/dl", "70 - 110mg/dl", "N")
    hist = db.previous_results(pid, tid)
    assert [h["display_value"] for h in hist] == ["112mg/dl", "101mg/dl"]


# ------------------------------------------------------------- test master

def test_saving_a_circular_formula_is_refused(db):
    from app.core.formula import FormulaError
    a = db.save_test({"code": "AAA", "name": "A", "group_name": "G", "unit": "",
                      "decimals": 1, "result_type": "numeric", "options": "",
                      "formula": "", "rate_paise": 0, "tat_hours": 1,
                      "sort_order": 0, "active": 1})
    db.save_test({"code": "BBB", "name": "B", "group_name": "G", "unit": "",
                  "decimals": 1, "result_type": "numeric", "options": "",
                  "formula": "AAA + 1", "rate_paise": 0, "tat_hours": 1,
                  "sort_order": 0, "active": 1})
    with pytest.raises(FormulaError, match="loop"):
        db.save_test({"id": a, "code": "AAA", "name": "A", "group_name": "G",
                      "unit": "", "decimals": 1, "result_type": "numeric",
                      "options": "", "formula": "BBB + 1", "rate_paise": 0,
                      "tat_hours": 1, "sort_order": 0, "active": 1})


def test_saving_a_broken_formula_is_refused(db):
    from app.core.formula import FormulaError
    with pytest.raises(FormulaError):
        db.save_test({"code": "CCC", "name": "C", "group_name": "G", "unit": "",
                      "decimals": 1, "result_type": "numeric", "options": "",
                      "formula": "TP - ", "rate_paise": 0, "tat_hours": 1,
                      "sort_order": 0, "active": 1})


def test_deleting_a_test_deactivates_it(db):
    t = db.get_test_by_code("PSA")
    db.delete_test(t["id"])
    assert t["code"] not in {x["code"] for x in db.list_tests()}
    assert t["code"] in {x["code"] for x in db.list_tests(include_inactive=True)}


# --------------------------------------------------------------------- audit

def test_audit_records_state_changes(db):
    _p, jid = make_job(db)
    actions = {a["action"] for a in db.recent_audit()}
    assert "job_created" in actions
