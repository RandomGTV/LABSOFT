"""End-to-end: enter results, calculate, produce a PDF."""

import os
from datetime import datetime

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("LABSOFT_HOME", str(tmp_path))
    from app.db import connection
    connection.close()
    connection.connect(do_backup=False)
    from app.db import queries as q, seed
    q.ensure_defaults()
    seed.seed_all()
    import app.services as services
    yield q, services
    connection.close()


def make_job(q, codes, sex="Female", age=31):
    pid = q.save_patient({"name": "FARAS .M.", "phone": "9876543210",
                          "sex": sex, "age_value": age, "age_unit": "years"})
    ids = [q.get_test_by_code(c)["id"] for c in codes]
    return pid, q.create_job(pid, ids)


def jt_map(q, job_id):
    return {t["code"]: t["job_test_id"] for t in q.job_tests(job_id)}


# -------------------------------------------------------------- calculation

def test_derived_values_calculate_and_save(app):
    q, s = app
    _p, jid = make_job(q, ["TP", "ALB", "GLOB", "AGR"])
    m = jt_map(q, jid)
    out = s.recalculate(jid, {m["TP"]: "7.2", m["ALB"]: "3.1"})

    assert out[m["GLOB"]]["display"] == "4.1g/dl"
    assert out[m["AGR"]]["display"] == "0.76"
    assert out[m["ALB"]]["flag"] == "L"      # 3.1 below 3.5
    assert out[m["GLOB"]]["flag"] == "H"     # 4.1 above 3.5


def test_derived_stays_blank_when_an_input_is_missing(app):
    q, s = app
    _p, jid = make_job(q, ["CHOL", "TG", "HDL", "LDL"])
    m = jt_map(q, jid)
    out = s.recalculate(jid, {m["CHOL"]: "212", m["TG"]: "180"})   # HDL blank
    assert out[m["LDL"]]["display"] == ""
    assert out[m["LDL"]]["flag"] == ""

    out = s.recalculate(jid, {m["HDL"]: "38"})
    assert out[m["LDL"]]["display"] == "138mg/dl"


def test_sex_specific_range_is_applied(app):
    q, s = app
    _p, jf = make_job(q, ["HB"], sex="Female")
    mf = jt_map(q, jf)
    of = s.recalculate(jf, {mf["HB"]: "12.5"})
    assert of[mf["HB"]]["flag"] == "N"
    assert of[mf["HB"]]["range_text"] == "12 - 15g/dl"

    _p, jm = make_job(q, ["HB"], sex="Male")
    mm = jt_map(q, jm)
    om = s.recalculate(jm, {mm["HB"]: "12.5"})
    assert om[mm["HB"]]["flag"] == "L"       # same value, different range
    assert om[mm["HB"]]["range_text"] == "13 - 17g/dl"


def test_option_results_flag_against_text(app):
    q, s = app
    _p, jid = make_job(q, ["HBSAG"])
    m = jt_map(q, jid)
    assert s.recalculate(jid, {m["HBSAG"]: "Non Reactive"})[m["HBSAG"]]["flag"] == "N"
    assert s.recalculate(jid, {m["HBSAG"]: "Reactive"})[m["HBSAG"]]["flag"] == "A"


def test_non_numeric_text_in_a_numeric_box_is_kept(app):
    q, s = app
    _p, jid = make_job(q, ["GLU_F"])
    m = jt_map(q, jid)
    out = s.recalculate(jid, {m["GLU_F"]: "Sample haemolysed"})
    assert out[m["GLU_F"]]["display"] == "Sample haemolysed"


def test_operator_prefixed_value_keeps_its_sign(app):
    q, s = app
    _p, jid = make_job(q, ["CRP"])
    m = jt_map(q, jid)
    out = s.recalculate(jid, {m["CRP"]: "<0.5"})
    assert out[m["CRP"]]["display"] == "<0.5mg/L"
    assert out[m["CRP"]]["flag"] == "N"


def test_status_advances_with_entry(app):
    q, s = app
    _p, jid = make_job(q, ["GLU_F", "GLU_PP"])
    m = jt_map(q, jid)
    assert q.get_job(jid)["status"] == "draft"

    s.recalculate(jid, {m["GLU_F"]: "105"})
    assert q.get_job(jid)["status"] == "in_progress"

    s.recalculate(jid, {m["GLU_PP"]: "123"})
    assert q.get_job(jid)["status"] == "ready"


# ---------------------------------------------------------------- verify gate

def test_verify_refuses_an_incomplete_job(app):
    q, s = app
    _p, jid = make_job(q, ["GLU_F", "GLU_PP"])
    m = jt_map(q, jid)
    s.recalculate(jid, {m["GLU_F"]: "105"})

    ok, missing, path = s.verify_job(jid)
    assert not ok and path is None
    assert missing == ["Blood Glucose [ P P 2 hrs ]"]


def test_verify_produces_a_pdf_when_complete(app):
    q, s = app
    _p, jid = make_job(q, ["GLU_F", "GLU_PP"])
    m = jt_map(q, jid)
    s.recalculate(jid, {m["GLU_F"]: "105", m["GLU_PP"]: "123"})

    ok, missing, path = s.verify_job(jid)
    assert ok and not missing
    assert path.exists() and path.stat().st_size > 3000
    assert path.read_bytes()[:5] == b"%PDF-"
    assert q.get_job(jid)["status"] == "ready"


def test_not_done_satisfies_the_gate(app):
    q, s = app
    _p, jid = make_job(q, ["GLU_F", "GLU_PP"])
    m = jt_map(q, jid)
    s.recalculate(jid, {m["GLU_F"]: "105"})
    q.set_not_done(m["GLU_PP"], True)
    ok, missing, path = s.verify_job(jid)
    assert ok and path.exists()


# -------------------------------------------------------------- report shape

def test_report_matches_the_labs_layout(app):
    q, s = app
    _p, jid = make_job(q, ["GLU_F", "GLU_PP"])
    m = jt_map(q, jid)
    s.recalculate(jid, {m["GLU_F"]: "105", m["GLU_PP"]: "123"})
    q.update_job(jid, reported_at=q.dt_str(datetime(2026, 8, 18, 16, 5)))

    data = s.build_report_data(jid)
    assert data.name == "FARAS .M."
    assert data.sex == "Female"
    assert data.age == "31 Years"
    assert data.date_text == "18-08-2026"      # date only, no time

    # A group heading followed by its rows, units inline with the value.
    assert data.rows[0].is_group
    assert data.rows[0].description == "BIO-CHEMISTRY (Routine)"
    assert data.rows[1].description == "Blood Glucose [Fasting]"
    assert data.rows[1].observed == "105mg/dl"
    assert data.rows[1].normal == "70 - 110mg/dl"
    assert data.rows[2].observed == "123mg/dl"
    assert data.rows[2].normal == "70 - 140mg/dl"


def test_not_done_tests_are_left_off_the_report(app):
    q, s = app
    _p, jid = make_job(q, ["GLU_F", "GLU_PP"])
    m = jt_map(q, jid)
    s.recalculate(jid, {m["GLU_F"]: "105"})
    q.set_not_done(m["GLU_PP"], True)
    data = s.build_report_data(jid)
    assert [r.description for r in data.rows if not r.is_group] == ["Blood Glucose [Fasting]"]


def test_group_headings_appear_once_each(app):
    q, s = app
    _p, jid = make_job(q, ["TP", "ALB", "GLOB", "AGR", "GLU_F"])
    m = jt_map(q, jid)
    s.recalculate(jid, {m["TP"]: "7.2", m["ALB"]: "3.1", m["GLU_F"]: "105"})
    data = s.build_report_data(jid)
    groups = [r.description for r in data.rows if r.is_group]
    assert len(groups) == len(set(groups))


def test_long_report_paginates_without_orphaning_a_heading(app):
    q, s = app
    codes = [t["code"] for t in q.list_tests()][:60]
    _p, jid = make_job(q, codes)
    m = jt_map(q, jid)
    s.recalculate(jid, {jt: "5" for jt in m.values()})

    from app.output import report as rpt
    data = s.build_report_data(jid)
    pages = rpt._paginate(data.rows, 60.0, 60.0, 8.0)
    assert len(pages) > 1
    for page in pages:
        assert not (page and page[-1].is_group), "a heading was left alone at a page foot"


def test_pdf_filename_is_safe_and_descriptive(app):
    q, s = app
    _p, jid = make_job(q, ["GLU_F"])
    m = jt_map(q, jid)
    s.recalculate(jid, {m["GLU_F"]: "105"})
    s.verify_job(jid)
    name = s.pdf_filename(q.get_job(jid))
    assert name.endswith(".pdf")
    assert "FARAS" in name
    assert not set(name) & set('\\/:*?"<>|')


def test_pdf_written_with_no_part_file_left(app):
    q, s = app
    _p, jid = make_job(q, ["GLU_F"])
    m = jt_map(q, jid)
    s.recalculate(jid, {m["GLU_F"]: "105"})
    _ok, _m, path = s.verify_job(jid)
    assert not list(path.parent.glob("*.part"))


# ---------------------------------------------------------------- revisions

def test_revision_keeps_the_original_intact(app):
    q, s = app
    _p, jid = make_job(q, ["GLU_F"])
    m = jt_map(q, jid)
    s.recalculate(jid, {m["GLU_F"]: "105"})
    s.verify_job(jid)
    q.update_job(jid, status="sent", sent_at=q.now_str(), sent_via="whatsapp")
    original_no = q.get_job(jid)["report_no"]

    new_id = s.create_revision(jid, reason="value corrected")
    new_job = q.get_job(new_id)
    assert new_job["report_no"] == original_no
    assert new_job["revision_no"] == 2

    old = q.get_job(jid)
    assert old["status"] == "sent" and old["revision_no"] == 1

    # The revision carries the original results forward, ready to be corrected.
    nm = jt_map(q, new_id)
    assert q.results_for_job(new_id)[nm["GLU_F"]]["display_value"] == "105mg/dl"


def test_revision_number_prints_on_the_report(app):
    q, s = app
    _p, jid = make_job(q, ["GLU_F"])
    m = jt_map(q, jid)
    s.recalculate(jid, {m["GLU_F"]: "105"})
    new_id = s.create_revision(jid)
    s.recalculate(new_id, {jt_map(q, new_id)["GLU_F"]: "150"})
    data = s.build_report_data(new_id)
    assert data.report_no.endswith("/ R2")


# ------------------------------------------------------------------ billing

def test_suggested_bill_collapses_a_full_panel(app):
    q, s = app
    cbc = next(p for p in q.list_panels() if p["name"] == "CBC")
    codes = [q.get_test(i)["code"] for i in q.panel_test_ids(cbc["id"])]
    _p, jid = make_job(q, codes + ["GLU_F"])

    items = s.suggest_bill_items(jid)
    labels = {i["label"] for i in items}
    assert "CBC" in labels
    assert "Blood Glucose [Fasting]" in labels
    assert "Haemoglobin" not in labels      # folded into the panel


def test_header_setting_does_not_affect_the_whatsapp_pdf(app):
    """Print-header off is a paper setting; the PDF always carries the header."""
    q, s = app
    q.set_setting("print_header", "0")
    _p, jid = make_job(q, ["GLU_F"])
    m = jt_map(q, jid)
    s.recalculate(jid, {m["GLU_F"]: "105"})
    _ok, _mi, path = s.verify_job(jid)
    with_header = path.stat().st_size

    q.set_setting("print_header", "1")
    _p, jid2 = make_job(q, ["GLU_F"])
    m2 = jt_map(q, jid2)
    s.recalculate(jid2, {m2["GLU_F"]: "105"})
    _ok, _mi, path2 = s.verify_job(jid2)

    # Both PDFs contain the letterhead, so neither is materially smaller.
    assert abs(with_header - path2.stat().st_size) < with_header * 0.35


def test_hba1c_and_mean_blood_glucose_calculation(app):
    q, s = app
    _p, jid = make_job(q, ["HBA1C", "MBG"])
    m = jt_map(q, jid)
    # When HbA1c is 7.1%, 28.7 * 7.1 - 46.7 = 157.07 -> 157 mg/dl
    out = s.recalculate(jid, {m["HBA1C"]: "7.1"})
    assert out[m["HBA1C"]]["display"] == "7.1%"
    assert out[m["MBG"]]["display"] == "157mg/dl"

    # Check detailed report data
    hba1c_job_test = next(t for t in q.job_tests(jid) if t["code"] == "HBA1C")
    dt = s.build_detail_data(jid, hba1c_job_test)
    assert "REFERENCE RANGE" in dt.interpretation
    assert "Glycosylated hemoglobin values are used" in dt.interpretation
    assert len(dt.rows) >= 3  # Header group, HBA1C, MBG


def test_semen_analysis_panel_and_reporting(app):
    q, s = app
    semen_panel = next(p for p in q.list_panels() if p["name"] == "Semen Analysis")
    codes = [q.get_test(i)["code"] for i in q.panel_test_ids(semen_panel["id"])]
    assert "SEMEN_TIME" in codes
    assert "SEMEN_COUNT" in codes
    assert "SEMEN_MOT_ACT" in codes
    assert "SEMEN_NORM" in codes
    assert "SEMEN_PUS" in codes

    _p, jid = make_job(q, codes, sex="Male", age=33)
    m = jt_map(q, jid)
    results = {
        m["SEMEN_TIME"]: "08:53AM",
        m["SEMEN_COL"]: "Opaque white",
        m["SEMEN_REACT"]: "Alkaline",
        m["SEMEN_VISC"]: "High",
        m["SEMEN_LIQ"]: "> 1 hr",
        m["SEMEN_VOL"]: "2.5",
        m["SEMEN_COUNT"]: "32",
        m["SEMEN_MOT_ACT"]: "15",
        m["SEMEN_MOT_SLUG"]: "55",
        m["SEMEN_MOT_NON"]: "30",
        m["SEMEN_NORM"]: "75",
        m["SEMEN_GIANT"]: "15",
        m["SEMEN_PIN"]: "5",
        m["SEMEN_NECK"]: "3",
        m["SEMEN_TAIL"]: "2",
        m["SEMEN_PUS"]: "3-5 / hpf seen",
        m["SEMEN_RBC"]: "Nil / hpf seen",
        m["SEMEN_BACT"]: "Not seen",
        m["SEMEN_OTH"]: "Not seen",
    }
    out = s.recalculate(jid, results)
    assert out[m["SEMEN_COUNT"]]["display"] == "32million/ml"
    assert out[m["SEMEN_COUNT"]]["flag"] == "L"  # < 60 is low
    assert out[m["SEMEN_MOT_ACT"]]["display"] == "15%"

    ok, missing, pdf_path = s.verify_job(jid)
    assert ok
    assert pdf_path is not None
    assert pdf_path.exists()


def test_preprinted_letterhead_and_three_signatories(app):
    q, s = app
    q.set_setting("sign_left_name", "SAHEED MOHAMED. P.")
    q.set_setting("sign_left_qual", "BScMLT")
    q.set_setting("sign_left_role", "Technologist")
    q.set_setting("sign_mid_name", "FATTIMATH SAKIRA.M.")
    q.set_setting("sign_mid_qual", "MScMicrobiology")
    q.set_setting("sign_mid_role", "Microbiologist")
    q.set_setting("sign_right_name", "ABDUNNASER MAYYERI")
    q.set_setting("sign_right_qual", "DMLT BScMLT")
    q.set_setting("sign_right_role", "Lab Incharge")
    q.set_setting("blank_header_mm", "38")
    q.set_setting("print_header", "0")
    q.set_setting("print_disclaimer", "1")

    _p, jid = make_job(q, ["GLU_F"])
    m = jt_map(q, jid)
    s.recalculate(jid, {m["GLU_F"]: "95"})
    data = s.build_report_data(jid)

    from app.output import report as rpt
    from PyQt6.QtGui import QPainter, QPdfWriter, QPageSize, QPageLayout
    from PyQt6.QtCore import QMarginsF
    from pathlib import Path
    import tempfile

    tmp_pdf = Path(tempfile.gettempdir()) / "test_preprinted.pdf"
    writer = QPdfWriter(str(tmp_pdf))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    painter = QPainter(writer)
    try:
        dpmm = writer.logicalDpiX() / 25.4
        renderer = rpt._Renderer(painter, data, dpmm, with_header=False)
        top = renderer.draw_header()
        assert top >= 38.0
        renderer.draw_signatures()
        renderer.draw_footer()
    finally:
        painter.end()
    assert tmp_pdf.exists()
