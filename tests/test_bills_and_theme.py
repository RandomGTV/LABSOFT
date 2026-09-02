"""The printed bill, the specimen line, the detailed sheets, and the themes.

Each test here stands for something that was either asked for by the lab or
went wrong once and must not go wrong again.
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


def _job(q, codes, values):
    from app import services

    pid = q.save_patient({"name": "FARAS .M. Kutty", "phone": "9876543210",
                          "sex": "M", "age_value": 34, "age_unit": "years"})
    ids = [q.get_test_by_code(c)["id"] for c in codes]
    jid = q.create_job(pid, ids)
    typed = {t["job_test_id"]: values[t["code"]]
             for t in q.job_tests(jid) if t["code"] in values}
    services.recalculate(jid, typed)
    return pid, jid


# ===========================================================================
# Money in words
# ===========================================================================

def test_amount_in_words_uses_lakh_not_million():
    from app.core.billing import amount_in_words

    assert amount_in_words(10_000_000) == "Rupees One Lakh only"
    assert amount_in_words(1_000_000_000) == "Rupees One Crore only"


def test_amount_in_words_matches_the_figure_beside_it():
    from app.core.billing import amount_in_words

    assert amount_in_words(143_100) == \
        "Rupees One Thousand Four Hundred Thirty One only"
    assert amount_in_words(0) == "Rupees Zero only"
    assert "Fifty Paise" in amount_in_words(10_050)


def test_amount_in_words_never_swallows_the_paise():
    """Rounding the paise into the rupees would make the words disagree with
    the figure printed next to them, which is what a receipt is for."""
    from app.core.billing import amount_in_words

    assert "Ninety Nine Paise" in amount_in_words(199)


# ===========================================================================
# The printed bill
# ===========================================================================

def test_bill_pdf_is_written_and_is_one_page(env):
    from app import services
    from app.output import receipt as rcpt

    q = env
    _pid, jid = _job(q, ["GLU_F", "CHOL"], {"GLU_F": "105", "CHOL": "210"})
    q.save_bill(jid, services.suggest_bill_items(jid), "percent", 10.0)

    path = services.generate_bill_pdf(jid)
    assert path.exists() and path.stat().st_size > 1000
    assert len(rcpt.render_pages(services.build_bill_data(jid), width_px=600)) == 1


def test_bill_can_be_printed_before_it_is_saved(env):
    """A patient asking what it will cost must not force a bill to be committed."""
    from app import services

    q = env
    _pid, jid = _job(q, ["GLU_F"], {"GLU_F": "105"})
    data = services.build_bill_data(jid)

    assert q.get_bill(jid) is None
    assert data.lines, "a proforma must still list the chosen tests"
    assert data.totals().net_paise > 0


def test_bill_totals_on_paper_match_the_stored_bill(env):
    from app import services

    q = env
    _pid, jid = _job(q, ["GLU_F", "CHOL", "TG"],
                     {"GLU_F": "105", "CHOL": "210", "TG": "150"})
    q.save_bill(jid, services.suggest_bill_items(jid), "flat", 50.0)
    q.add_payment(q.get_bill(jid)["id"], 10000, "cash")

    printed = services.build_bill_data(jid).totals()
    stored = q.bill_totals(jid)
    assert printed.net_paise == stored.net_paise
    assert printed.paid_paise == stored.paid_paise == 10000
    assert printed.balance_paise == stored.balance_paise


def test_a_long_bill_stays_on_one_page(env):
    """A receipt that runs to two sheets gets separated and then proves nothing."""
    from app import services
    from app.output import receipt as rcpt

    q = env
    _pid, jid = _job(q, ["GLU_F"], {"GLU_F": "105"})
    data = services.build_bill_data(jid)
    data.lines = [rcpt.BillLine(f"Test number {i}", 10000, 1) for i in range(60)]

    assert len(rcpt.render_pages(data, width_px=600)) == 1


# ===========================================================================
# Specimen on the report
# ===========================================================================

def test_a_group_with_one_specimen_says_so_once(env):
    from app import services

    q = env
    _pid, jid = _job(q, ["CHOL", "HDL", "TG"],
                     {"CHOL": "210", "HDL": "40", "TG": "150"})
    rows = services.build_report_data(jid).rows

    groups = [r for r in rows if r.is_group]
    assert groups and all(g.specimen for g in groups)
    assert not any(r.specimen for r in rows if not r.is_group), \
        "a shared specimen belongs on the heading, not on every line"


def test_a_mixed_group_names_the_specimen_on_each_line(env):
    """HbA1c is whole blood and fasting glucose is fluoride plasma, yet both sit
    under BIO-CHEMISTRY. One heading claiming a single specimen would be wrong."""
    from app import services

    q = env
    _pid, jid = _job(q, ["HBA1C", "GLU_F"], {"HBA1C": "7.8", "GLU_F": "142"})
    rows = services.build_report_data(jid).rows

    heading = next(r for r in rows if r.is_group)
    assert heading.specimen == "", "the heading must not pick one of two specimens"
    named = {r.description: r.specimen for r in rows if not r.is_group}
    assert all(named.values()), named
    assert len(set(named.values())) == 2


def test_the_specimen_line_can_be_turned_off(env):
    from app import services

    q = env
    _pid, jid = _job(q, ["CHOL", "HDL"], {"CHOL": "210", "HDL": "40"})
    q.set_settings({"print_specimen": "0"})
    rows = services.build_report_data(jid).rows

    assert not any(r.specimen for r in rows)


# ===========================================================================
# Detailed single-test sheets
# ===========================================================================

def test_hba1c_gets_its_own_sheet(env):
    from app import services

    q = env
    _pid, jid = _job(q, ["HBA1C", "CHOL"], {"HBA1C": "7.8", "CHOL": "210"})
    services.generate_pdf(jid)

    files = services.report_files(jid)
    assert len(files) == 2, [f.name for f in files]
    assert any("HbA1c" in f.name for f in files)


def test_extra_pdf_paths_survive_being_saved(env):
    """update_job silently ignores any column it does not name, so a new one
    has to be added there as well -- this is that guard."""
    from app import services

    q = env
    _pid, jid = _job(q, ["HBA1C"], {"HBA1C": "7.8"})
    services.generate_pdf(jid)

    assert (q.get_job(jid)["extra_pdfs"] or "").strip(), \
        "the detail sheet was made and then forgotten"


def test_detailed_sheets_can_be_turned_off(env):
    from app import services

    q = env
    _pid, jid = _job(q, ["HBA1C"], {"HBA1C": "7.8"})
    q.set_settings({"separate_detail_reports": "0"})
    services.generate_pdf(jid)

    assert len(services.report_files(jid)) == 1


def test_the_detail_sheet_carries_the_interpretation(env):
    from app import services

    q = env
    _pid, jid = _job(q, ["HBA1C"], {"HBA1C": "7.8"})
    test = next(t for t in services.detailed_tests(jid) if t["code"] == "HBA1C")
    data = services.build_detail_data(jid, test)

    assert "Pre Diabetes" in data.interpretation or "Prediabetes" in data.interpretation
    assert data.format_type == "hba1c"


def test_long_notes_are_wrapped_not_cut_short(env):
    """An ellipsis in the middle of a clinical note loses exactly the sentence
    that matters."""
    from app.output import report as rpt

    text = ("Results may read falsely low in haemolytic anaemia, recent blood "
            "loss or transfusion, and falsely high in iron deficiency anaemia. "
            "Clinical correlation is advised.")
    data = rpt.ReportData(report_no="1", name="X",
                          rows=[rpt.ReportRow(description="HbA1c", observed="7.8")],
                          title="HbA1c — Detailed Report", interpretation=text)
    images = rpt.render_pages(data, width_px=800)
    assert len(images) == 1


# ===========================================================================
# The letterhead
# ===========================================================================

def test_the_letterhead_design_is_a_real_setting(env):
    from app import config

    assert "header_style" in config.DEFAULT_SETTINGS
    assert env.get_setting("header_style") in ("modern", "classic")


def test_both_letterheads_render(env):
    from app import services
    from app.output import report as rpt

    q = env
    _pid, jid = _job(q, ["GLU_F"], {"GLU_F": "105"})
    for style_name in ("classic", "modern"):
        q.set_settings({"header_style": style_name})
        pages = rpt.render_pages(services.build_report_data(jid), width_px=600)
        assert len(pages) == 1


# ===========================================================================
# Themes
# ===========================================================================

def test_a_nonsense_theme_falls_back_to_daylight():
    from app.ui import style

    assert style.normalise_theme("purple") == "light"
    assert style.normalise_theme("") == "light"
    assert style.normalise_theme(" DARK ") == "dark"


def test_switching_theme_moves_the_colours(qt_app):
    from app.ui import style

    try:
        style.apply_theme(qt_app, "dark")
        dark_bg, dark_ink = style.BG, style.INK
        assert style.CURRENT_THEME == "dark"
        style.apply_theme(qt_app, "light")
        assert (style.BG, style.INK) != (dark_bg, dark_ink)
        assert style.CURRENT_THEME == "light"
    finally:
        style.apply_theme(qt_app, "light")


def test_the_dark_theme_is_actually_dark():
    """The window the night sheet paints must be dark, measured not assumed.

    This used to check that the daylight background string was absent from
    the night sheet. That broke the day the two palettes shared a value --
    #F8FAFC is the day theme's page and the night theme's *text* -- and the
    test failed while the sheet was perfectly correct. Read the colour the
    sheet actually gives the window instead.
    """
    import re

    from app.ui import style
    from tests.test_contrast import luminance

    sheet = style.stylesheet_for("dark")
    assert style.DARK["BG"] in sheet

    match = re.search(r"QMainWindow, QDialog \{ background: (#[0-9A-Fa-f]{6}); \}",
                      sheet)
    assert match, "the window background could not be found in the night sheet"
    assert luminance(match.group(1)) < 0.1, \
        f"the night theme paints the window {match.group(1)}"


# ===========================================================================
# The screens that own these settings
# ===========================================================================

def test_settings_screen_saves_the_new_choices(env, qt_app):
    from app.ui import style
    from app.ui.settings_screen import SettingsScreen

    style.apply_theme(qt_app, "light")
    screen = SettingsScreen()
    try:
        screen.header_style_combo.setCurrentIndex(
            screen.header_style_combo.findData("classic"))
        screen.specimen_check.setChecked(False)
        screen.detail_check.setChecked(False)
        assert screen.save()

        assert env.get_setting("header_style") == "classic"
        assert not env.setting_bool("print_specimen")
        assert not env.setting_bool("separate_detail_reports")

        screen.reload()
        assert screen.header_style_combo.currentData() == "classic"
        assert screen.specimen_check.isChecked() is False
    finally:
        screen.deleteLater()


def test_picking_a_theme_takes_effect_at_once(env, qt_app):
    """A theme you have to press Save to see is a theme nobody tries."""
    from app.ui import style
    from app.ui.settings_screen import SettingsScreen

    screen = SettingsScreen()
    try:
        screen.theme_combo.setCurrentIndex(screen.theme_combo.findData("dark"))
        assert style.CURRENT_THEME == "dark"
        assert env.get_setting("theme") == "dark"
    finally:
        screen.deleteLater()
        style.apply_theme(qt_app, "light")


def test_a_test_can_be_given_a_specimen_and_its_own_sheet(env, qt_app):
    from app.ui.tests_screen import TestEditor

    existing = env.get_test_by_code("CHOL")
    editor = TestEditor(existing["id"])
    try:
        editor.specimen_combo.setCurrentText("Plasma (Citrate)")
        editor.separate_check.setChecked(True)
        editor.interp_edit.setPlainText("Below 200 mg/dl is desirable.")
        editor._save()
    finally:
        editor.deleteLater()

    saved = env.get_test_by_code("CHOL")
    assert saved["specimen"] == "Plasma (Citrate)"
    assert saved["separate_report"] == 1
    assert "desirable" in saved["interpretation"]


def test_editing_a_test_does_not_quietly_reorder_or_unhide_it(env, qt_app):
    from app.ui.tests_screen import TestEditor

    before = env.get_test_by_code("HDL")
    env.delete_test(before["id"])                    # "Hide" in the Tests screen
    editor = TestEditor(before["id"])
    try:
        editor.unit_edit.setText("mg/dl")
        editor._save()
    finally:
        editor.deleteLater()

    after = env.get_test_by_code("HDL")
    assert after["active"] == 0, "editing a hidden test brought it back"
    assert after["sort_order"] == before["sort_order"]


def test_the_report_is_never_drawn_in_the_dark_theme(env, qt_app):
    """A theme is for the screen. A report printed on a dark background would
    empty a toner cartridge and be unreadable."""
    from app import services
    from app.ui import style

    q = env
    _pid, jid = _job(q, ["GLU_F"], {"GLU_F": "105"})
    try:
        style.apply_theme(qt_app, "dark")
        data = services.build_report_data(jid)
        assert "theme" not in str(data.setting("header_style"))
        from app.output import report as rpt

        image = rpt.render_pages(data, width_px=400)[0]
        # Top-left corner of the page margin is paper, and paper is white.
        assert image.pixelColor(2, 2).lightness() > 200
    finally:
        style.apply_theme(qt_app, "light")
