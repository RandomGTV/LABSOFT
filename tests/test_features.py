"""Preview, patient folders, and cloud backup."""

from __future__ import annotations

import os
from pathlib import Path

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
    from app.ui import style

    app = QApplication.instance() or QApplication([])
    style.apply_light_palette(app)
    app.setStyleSheet(style.STYLESHEET)
    yield env, app


def finished_job(q, codes=("GLU_F", "GLU_PP"), name="FARAS .M.",
                 phone="9876543210"):
    from app import services

    pid = q.save_patient({"name": name, "phone": phone, "sex": "Female",
                          "age_value": 31, "age_unit": "years"})
    ids = [q.get_test_by_code(c)["id"] for c in codes]
    jid = q.create_job(pid, ids)
    m = {t["code"]: t["job_test_id"] for t in q.job_tests(jid)}
    services.recalculate(jid, {jt: "105" for jt in m.values()})
    return pid, jid


# ===========================================================================
# Preview
# ===========================================================================

def test_preview_renders_a_page_image(app_env):
    env, _app = app_env
    from app import services
    from app.output import report as rpt

    _pid, jid = finished_job(env)
    pages = rpt.render_pages(services.build_report_data(jid), width_px=800)

    assert len(pages) == 1
    assert pages[0].width() == 800
    assert pages[0].height() > 800          # A4 is taller than it is wide


def test_a_long_report_previews_every_page(app_env):
    env, _app = app_env
    from app import services
    from app.output import report as rpt

    codes = [t["code"] for t in env.list_tests()][:60]
    _pid, jid = finished_job(env, codes)

    data = services.build_report_data(jid)
    pages = rpt.render_pages(data, width_px=600)
    assert len(pages) > 1, "a long report previewed as a single page"
    assert all(not p.isNull() for p in pages)


def test_preview_pages_are_not_blank(app_env):
    """A page of pure white would mean the painter never drew anything."""
    env, _app = app_env
    from app import services
    from app.output import report as rpt

    _pid, jid = finished_job(env)
    image = rpt.render_pages(services.build_report_data(jid), width_px=700)[0]

    dark = 0
    for y in range(0, image.height(), 7):
        for x in range(0, image.width(), 7):
            if image.pixelColor(x, y).lightness() < 200:
                dark += 1
    assert dark > 50, "the previewed page looks blank"


def test_preview_dialog_opens_and_pages_through(app_env):
    env, _app = app_env
    from app.ui.preview_dialog import PreviewDialog

    codes = [t["code"] for t in env.list_tests()][:60]
    _pid, jid = finished_job(env, codes)

    dlg = PreviewDialog(jid)
    assert len(dlg.pages) > 1
    assert "Page 1 of" in dlg.page_label.text()
    assert not dlg.prev_button.isEnabled()

    dlg._next()
    assert "Page 2 of" in dlg.page_label.text()
    assert dlg.prev_button.isEnabled()

    dlg._zoom(1)
    assert dlg.zoom_label.text() == "125%"
    assert not dlg.send_requested
    dlg.deleteLater()


def test_preview_matches_the_pdf_page_count(app_env):
    """Preview and PDF share the paint code, so they must agree."""
    env, _app = app_env
    from app import services
    from app.output import report as rpt

    codes = [t["code"] for t in env.list_tests()][:60]
    _pid, jid = finished_job(env, codes)
    data = services.build_report_data(jid)

    previewed = len(rpt.render_pages(data, width_px=600))
    pdf = services.generate_pdf(jid)
    text = pdf.read_bytes()
    in_pdf = text.count(b"/Type /Page\n") or text.count(b"/Type/Page")
    assert previewed >= 2
    if in_pdf:
        assert previewed == in_pdf


# ===========================================================================
# Patient folders
# ===========================================================================

def test_report_is_filed_in_the_patients_own_folder(env):
    from app import services

    _pid, jid = finished_job(env)
    path = services.generate_pdf(jid)

    assert path.exists()
    assert path.parent.parent.name == "patients"
    assert "FARAS" in path.parent.name
    assert path.parent.name.endswith(f"#{_pid}"), \
        "the folder needs something unique to this patient in its name"
    assert path.name.endswith(".pdf")
    assert "51359" in path.name


def test_the_folder_carries_a_readable_patient_card(env):
    from app import services

    pid, jid = finished_job(env)
    services.generate_pdf(jid)

    card = services.patient_folder(pid) / "_patient details.txt"
    assert card.exists()

    text = card.read_text(encoding="utf-8")
    assert "FARAS .M." in text
    assert "9876543210" in text
    assert "31 Years" in text
    assert "51359" in text, "the visit list is missing from the card"


def test_every_visit_lands_in_the_same_folder(env):
    from app import services

    pid, first = finished_job(env)
    services.generate_pdf(first)

    ids = [env.get_test_by_code("HB")["id"]]
    second = env.create_job(pid, ids)
    m = {t["code"]: t["job_test_id"] for t in env.job_tests(second)}
    services.recalculate(second, {m["HB"]: "13.5"})
    services.generate_pdf(second)

    folder = services.patient_folder(pid)
    pdfs = sorted(folder.glob("*.pdf"))
    assert len(pdfs) == 2, "the second visit was filed somewhere else"


def test_a_patient_with_an_initial_gets_one_folder_not_two(env):
    """Reports were filed under the printed name and the card under the plain
    one, so every patient with an initial had two folders and the Patients tab
    opened the empty one."""
    from app import services

    pid, jid = finished_job(env, name="Anil Sharma", phone="9988776655")
    env.save_patient({"id": pid, "initial": "K"})
    env.update_job(jid, name_at_test=env.full_name("Anil Sharma", "K"))
    report = services.generate_pdf(jid)

    assert report.parent == services.patient_folder(pid), \
        "the report and the patient card went to different folders"
    assert list(services.patient_folder(pid).glob("*.pdf")), \
        "Open folder shows a folder with no reports in it"


def test_the_folder_survives_the_name_being_corrected(env):
    """A name fixed after the first visit must not scatter the reports."""
    from app import services

    pid, first = finished_job(env, name="Ramesh Kumr", phone="9000000033")
    services.generate_pdf(first)

    env.save_patient({"id": pid, "name": "Ramesh Kumar"})
    ids = [env.get_test_by_code("HB")["id"]]
    second = env.create_job(pid, ids)
    m = {t["code"]: t["job_test_id"] for t in env.job_tests(second)}
    services.recalculate(second, {m["HB"]: "13.5"})
    services.generate_pdf(second)

    folder = services.patient_folder(pid)
    assert len(list(folder.glob("*.pdf"))) == 2, \
        "correcting the name left the earlier report in an orphaned folder"


def test_an_existing_split_folder_is_folded_back_into_one(env):
    """The shape found on the lab's own PC: reports filed under the printed
    name, the details card under the plain one, neither carrying an id."""
    from app import config, services

    pid, jid = finished_job(env, name="rajeev", phone="9000000044")
    env.save_patient({"id": pid, "initial": "H"})

    root = config.patients_dir()
    (root / "rajeev").mkdir(parents=True, exist_ok=True)
    (root / "rajeev" / "_patient details.txt").write_text("old card", encoding="utf-8")
    (root / "rajeev .H").mkdir(parents=True, exist_ok=True)
    (root / "rajeev .H" / "Report_51369.pdf").write_bytes(b"%PDF-1.4 old report")

    folder = services.patient_folder(pid)

    names = {f.name for f in folder.iterdir()}
    assert "Report_51369.pdf" in names, "the earlier report was left behind"
    assert "_patient details.txt" in names
    assert not (root / "rajeev .H").exists(), "the stray folder is still there"


def test_two_patients_with_the_same_name_get_separate_folders(env):
    from app import services

    p1, j1 = finished_job(env, name="Ramesh Kumar", phone="9000000011")
    p2, j2 = finished_job(env, name="Ramesh Kumar", phone="9000000022")
    services.generate_pdf(j1)
    services.generate_pdf(j2)

    assert services.patient_folder(p1) != services.patient_folder(p2)
    assert len(list(services.patient_folder(p1).glob("*.pdf"))) == 1
    assert len(list(services.patient_folder(p2).glob("*.pdf"))) == 1


def test_awkward_names_make_safe_folder_names(env):
    from app import config

    folder = config.patient_dir(7, 'A/B:C*D?"E<F>G|H', "98765 43210")
    assert not set(folder.name) & set('\\/:*?"<>|')
    assert folder.name.endswith("#7")


def test_a_month_copy_is_kept_as_well(env):
    """Patient folders are for one person; the month folder is for "last March"."""
    from app import config, services

    _pid, jid = finished_job(env)
    services.generate_pdf(jid)

    month_files = list(config.reports_dir().rglob("*.pdf"))
    assert month_files, "the by-month copy is missing"


def test_patients_screen_lists_people_and_their_files(app_env):
    env, _app = app_env
    from app import services
    from app.ui.patients_screen import PatientsScreen

    _pid, jid = finished_job(env)
    services.generate_pdf(jid)

    screen = PatientsScreen()
    assert screen.patient_table.rowCount() == 1
    assert screen.job_table.rowCount() == 1
    names = [screen.file_table.item(r, 0).text()
             for r in range(screen.file_table.rowCount())]
    assert any(n.endswith(".pdf") for n in names)
    assert any("patient details" in n for n in names)
    screen.deleteLater()


# ===========================================================================
# Cloud backup
# ===========================================================================

def test_a_chosen_folder_is_used(env, tmp_path):
    from app.output import cloud

    drive = tmp_path / "MyDrive"
    drive.mkdir()
    status = cloud.resolve(str(drive))
    assert status.available and status.path == drive


def test_a_missing_folder_is_reported_clearly(env, tmp_path):
    from app.output import cloud

    status = cloud.resolve(str(tmp_path / "not-there"))
    assert not status.available
    assert "does not exist" in status.detail


def test_backup_is_copied_into_the_cloud_folder(env, tmp_path):
    from app.db import connection
    from app.output import cloud

    drive = tmp_path / "GoogleDrive"
    drive.mkdir()
    env.set_setting("cloud_folder", str(drive))
    env.set_setting("cloud_backup", "1")

    finished_job(env)
    backup = connection.backup_now()

    copies = list(drive.rglob("lab_*.db"))
    assert copies, "nothing reached the cloud folder"
    assert copies[0].name == backup.name
    assert copies[0].stat().st_size == backup.stat().st_size


def test_the_cloud_copy_contains_the_data(env, tmp_path):
    import sqlite3

    from app.db import connection

    drive = tmp_path / "Drive"
    drive.mkdir()
    env.set_setting("cloud_folder", str(drive))

    finished_job(env)
    connection.backup_now()

    copy = list(drive.rglob("lab_*.db"))[0]
    check = sqlite3.connect(str(copy))
    try:
        jobs = check.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    finally:
        check.close()
    assert jobs == 1


def test_turning_cloud_backup_off_stops_the_copy(env, tmp_path):
    from app.db import connection

    drive = tmp_path / "Drive"
    drive.mkdir()
    env.set_setting("cloud_folder", str(drive))
    env.set_setting("cloud_backup", "0")

    finished_job(env)
    connection.backup_now()
    assert not list(drive.rglob("lab_*.db"))


def test_a_broken_cloud_folder_never_stops_the_local_backup(env, tmp_path):
    """No internet, no Drive, wrong path — the lab still gets its backup."""
    from app.db import connection

    env.set_setting("cloud_folder", str(tmp_path / "nowhere"))
    finished_job(env)

    backup = connection.backup_now()
    assert backup.exists() and backup.stat().st_size > 0


def test_old_cloud_copies_are_pruned(env, tmp_path):
    from app.output import cloud

    drive = tmp_path / "Drive"
    folder = drive / "LabSoft Backups"
    folder.mkdir(parents=True)
    for i in range(20):
        (folder / f"lab_2026-08-{i + 1:02d}_000000.db").write_bytes(b"x")

    removed = cloud.prune(folder, keep=14)
    assert removed == 6
    assert len(cloud.list_copies(folder)) == 14


def test_a_half_written_copy_is_never_left_behind(env, tmp_path):
    from app.db import connection
    from app.output import cloud

    drive = tmp_path / "Drive"
    drive.mkdir()
    env.set_setting("cloud_folder", str(drive))
    finished_job(env)
    connection.backup_now()

    assert not list(drive.rglob("*.part"))


def test_detection_reports_when_no_drive_is_installed(env, monkeypatch):
    from app.output import cloud

    monkeypatch.setattr(cloud, "candidate_folders", lambda: [])
    status = cloud.detect()
    assert not status.available
    assert "Google Drive" in status.detail


def test_settings_screen_shows_cloud_state(app_env, tmp_path):
    env, _app = app_env
    from app.ui.settings_screen import SettingsScreen

    drive = tmp_path / "Drive"
    drive.mkdir()
    env.set_setting("cloud_folder", str(drive))

    screen = SettingsScreen()
    screen.reload()
    assert str(drive) in screen.cloud_status.text()
    assert screen.collect()["cloud_folder"] == str(drive)
    screen.deleteLater()
