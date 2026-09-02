"""What a staff account can reach, and what it cannot.

Every test here is a hole that was open. A screen that hides a button has
checked nothing: the handler behind it ran for anybody who could get to it,
and on this program most of them could.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

WEB_PAGE = Path(__file__).resolve().parent.parent / "web" / "index.html"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("LABSOFT_HOME", str(tmp_path))
    from app.core import auth
    from app.db import connection, queries as q, seed

    auth.set_current(None)
    connection.close()
    connection.connect(do_backup=False)
    q.ensure_defaults()
    seed.seed_all()
    yield q
    auth.set_current(None)
    connection.close()


def _as(env, permissions, username="ritu"):
    """Sign in as a staff account holding exactly these permissions."""
    from app.core import auth

    env.create_user(username, username.title(), "7392", auth.ROLE_STAFF,
                    list(permissions))
    auth.set_current(env.sign_in(username, "7392"))
    return auth.current()


def _job(env):
    from app import services

    pid = env.save_patient({"name": "Faras M Kutty", "phone": "98470 22118"})
    jid = env.create_job(pid, [t["id"] for t in env.list_tests()[:2]])
    env.save_bill(jid, services.suggest_bill_items(jid), "percent", 0)
    env.add_payment(jid, 5000, "cash")
    return jid


# ===========================================================================
# No master PIN anywhere in the product
# ===========================================================================

def test_the_web_page_carries_no_master_pin():
    """1598 signed you in as any account, and the page printed it.

    It was removed from the desktop program and left in the web one, which is
    the copy published on the internet.
    """
    page = WEB_PAGE.read_text(encoding="utf-8")
    code = page.split("</style>", 1)[-1]          # skip CSS class names
    for offender in ('pin === "1598"', 'adminPin === "1598"',
                     'Default Master PIN', 'Default PIN is',
                     'pin: "1598"'):
        assert offender not in code, f"the web page still has {offender!r}"


def test_the_web_page_stores_no_pin_at_all():
    """A page served from a static host cannot keep a credential."""
    page = WEB_PAGE.read_text(encoding="utf-8")
    assert not re.search(r'pin\s*:\s*"[0-9]{4,}"', page), \
        "an account in the web page still ships with a PIN"


def test_the_web_page_carries_no_real_person_or_number():
    """It is deployed publicly; the lab's staff and phone are not demo data."""
    page = WEB_PAGE.read_text(encoding="utf-8")
    for private in ("Abdunnaser", "SAHEED MOHAMED", "81578 87311",
                    "mithralab12020", "Chettiyankinar"):
        assert private not in page, f"{private!r} is still on the public page"


def test_the_web_page_claims_no_tax_registration():
    """A fabricated GSTIN under the words TAX INVOICE is a false document."""
    page = WEB_PAGE.read_text(encoding="utf-8")
    assert "GSTIN" not in page
    assert "TAX INVOICE" not in page


def test_the_old_master_pin_cannot_be_chosen(env):
    from app.core import auth

    assert "1598" in auth.KNOWN_DEFAULTS
    with pytest.raises(auth.PinError):
        auth.hash_pin("1598")


# ===========================================================================
# Permissions, checked where the work happens
# ===========================================================================

def test_a_job_cannot_be_deleted_without_the_delete_permission(env, monkeypatch):
    from app.core import auth
    from app.ui import queue_screen as qs

    jid = _job(env)
    _as(env, [auth.P_RESULTS])
    screen = qs.QueueScreen()
    screen.refresh()
    warned = []
    monkeypatch.setattr(qs, "warn", lambda *a: warned.append(a))
    monkeypatch.setattr(qs, "confirm", lambda *a, **k: True)
    screen._delete_selected()

    assert env.get_job(jid) is not None, "a results-only account deleted a job"
    assert warned, "it failed silently instead of saying why"
    screen.deleteLater()


def test_settings_cannot_be_saved_without_the_settings_permission(env, monkeypatch):
    from app.core import auth
    from app.ui import settings_screen as ss

    _as(env, [auth.P_USERS])
    screen = ss.SettingsScreen()
    monkeypatch.setattr(ss, "warn", lambda *a: None)
    screen.editors["lab_name"].setText("HIJACKED LAB")

    assert screen.save() is False
    assert env.get_setting("lab_name") != "HIJACKED LAB"
    screen.deleteLater()


def test_the_settings_tab_does_not_come_with_the_staff_tab(env):
    """P_USERS used to bring Settings with it, letterhead and all."""
    from app.core import auth
    from app.ui.main_window import MainWindow

    _as(env, [auth.P_USERS])
    win = MainWindow()
    try:
        names = [win.tabs.tabText(i) for i in range(win.tabs.count())]
        assert any("Staff" in n for n in names)
        assert not any("Settings" in n for n in names)
    finally:
        win.close()
        win.deleteLater()


def test_a_bill_cannot_be_changed_with_only_ledger_permission(env, monkeypatch):
    """P_MONEY is "see the ledger". P_BILL is "change what is owed"."""
    from app.core import auth
    from app.ui import bill_dialog as bd

    jid = _job(env)
    before = env.job_money(jid)
    _as(env, [auth.P_MONEY])
    monkeypatch.setattr(bd, "warn", lambda *a: None)
    dlg = bd.BillDialog(jid)
    dlg.discount_value.setValue(100.0)

    assert dlg._save() == 0
    dlg.payments_table.selectRow(0)
    dlg._remove_payment()

    after = env.job_money(jid)
    assert after["net_paise"] == before["net_paise"]
    assert after["paid_paise"] == before["paid_paise"]
    dlg.deleteLater()


def test_a_doctor_cannot_be_edited_without_the_tests_permission(env, monkeypatch):
    from app.core import auth
    from app.ui import doctors_screen as ds

    env.save_referrer({"name": "Dr Anil Menon", "phone": "98470 11223",
                       "commission_percent": 10})
    _as(env, [auth.P_RESULTS])
    monkeypatch.setattr(ds, "warn", lambda *a: None)
    screen = ds.DoctorsScreen()
    screen.refresh()

    assert screen._may_edit() is False
    assert not screen.add_button.isEnabled()
    assert not screen.edit_button.isEnabled()
    screen.deleteLater()


# ===========================================================================
# A patient's name is not a command line
# ===========================================================================

@pytest.mark.parametrize("typed,forbidden", [
    ("Anil $(Invoke-WebRequest evil)", "$("),
    ("Ritu `whoami`", "`"),
    ("A; rm -rf /", ";"),
    ("B & C", "&"),
    ("D | E", "|"),
])
def test_a_patient_name_cannot_carry_shell_characters(typed, forbidden):
    """The folder name ends up in a PowerShell command line.

    `Set-Clipboard -LiteralPath "<path>"` was built by interpolation, and
    PowerShell expands $(...) inside double quotes — so registering a patient
    under that name ran the command the first time anyone pressed Send.
    """
    from app import config

    assert forbidden not in config.patient_name_part(typed)


def test_the_clipboard_call_passes_the_path_as_data():
    """Not as script text. This is the lock the sanitiser backs up."""
    from app.output import sender

    source = Path(sender.__file__).read_text(encoding="utf-8")
    assert "$args[0]" in source
    # Look at the code, not the note explaining what the code replaced.
    code = "\n".join(line for line in source.splitlines()
                     if not line.lstrip().startswith("#"))
    assert "f'Set-Clipboard" not in code
    assert 'f"Set-Clipboard' not in code


@pytest.mark.parametrize("reserved", ["CON", "nul", "LPT1", "com3.pdf"])
def test_a_windows_device_name_cannot_become_a_folder(reserved):
    from app import config

    made = config.patient_name_part(reserved)
    assert made != reserved
    assert not made.upper().startswith(reserved.split(".")[0].upper())


# ===========================================================================
# Nothing about a patient leaves through git or the cloud by default
# ===========================================================================

def test_the_repository_ignores_every_patient_file():
    ignore = Path(__file__).resolve().parent.parent / ".gitignore"
    assert ignore.exists(), "there is no .gitignore, and PUSH TO GIT.bat runs git add -A"
    text = ignore.read_text(encoding="utf-8")
    for folder in ("data/", "patients/", "reports/", "exports/", "logs/", "*.db"):
        assert folder in text, f"{folder} is not ignored"


def test_the_cloud_copy_is_off_until_it_is_turned_on():
    from app import config

    assert config.DEFAULT_SETTINGS["cloud_backup"] == "0"


def test_results_never_travel_in_a_url():
    """wa.me put every result in a query string, and in browser history."""
    from app.ui import whatsapp_dialog

    source = Path(whatsapp_dialog.__file__).read_text(encoding="utf-8")
    # Strip the docstrings and comments; what is left is what runs.
    code = re.sub(r'"""[\s\S]*?"""', "", source)
    code = "\n".join(line for line in code.splitlines()
                     if not line.lstrip().startswith("#"))
    assert "wa.me" not in code
    assert "webbrowser" not in code
