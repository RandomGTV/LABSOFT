"""The sign-in screen: what gets you in, and what does not.

These tests exist because of what was found in the old screen. It accepted
``1598`` as the PIN for any account on any installation, printed that number
in the error message when a real PIN was mistyped, used it to authorise
creating accounts, and re-created an ``admin`` login whenever the user list
came back empty. Every one of those has a test here, so it cannot come back
without a red run.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


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


@pytest.fixture()
def screen(env):
    from app.ui.login_dialog import ModernLoginDialog

    dlg = ModernLoginDialog()
    yield env, dlg
    dlg.deleteLater()


def _select(dlg, username: str) -> None:
    index = dlg.user_combo.findData(username)
    assert index >= 0, f"{username} is not in the list"
    dlg.user_combo.setCurrentIndex(index)


# ===========================================================================
# No way in but the right PIN
# ===========================================================================

@pytest.mark.parametrize("pin", ["1598", "0000", "1234", "9999", ""])
def test_no_pin_but_the_real_one_signs_anybody_in(env, pin):
    from app.core import auth
    from app.ui.login_dialog import ModernLoginDialog

    env.create_user("saheed", "Saheed", "4821", auth.ROLE_ADMIN,
                    auth.ALL_PERMISSIONS)
    dlg = ModernLoginDialog()
    _select(dlg, "saheed")
    dlg.pin_edit.setText(pin)
    dlg._do_sign_in()

    assert dlg.user is None
    assert auth.current() is None
    assert dlg.result() != dlg.DialogCode.Accepted
    dlg.deleteLater()


def test_the_right_pin_does_sign_in(screen):
    from app.core import auth

    env, dlg = screen
    env.create_user("ritu", "Ritu Patil", "7392", auth.ROLE_STAFF,
                    [auth.P_RESULTS])
    dlg._refresh_users_combo()
    _select(dlg, "ritu")
    dlg.pin_edit.setText("7392")
    dlg._do_sign_in()

    assert dlg.user is not None and dlg.user.username == "ritu"
    assert auth.current().username == "ritu"


def test_a_wrong_pin_never_names_a_number(screen):
    """The old message read "Default Master PIN is 1598"."""
    env, dlg = screen
    from app.core import auth

    env.create_user("ritu", "Ritu", "7392", auth.ROLE_STAFF, [auth.P_RESULTS])
    dlg._refresh_users_combo()
    _select(dlg, "ritu")
    dlg.pin_edit.setText("0000")
    dlg._do_sign_in()

    said = dlg.signin_error.text()
    assert said and not any(ch.isdigit() for ch in said)
    assert dlg.pin_edit.text() == ""       # cleared, ready for another go


# ===========================================================================
# An empty database has no accounts, and does not invent one
# ===========================================================================

def test_an_empty_database_stays_empty(env):
    from app.ui.login_dialog import ModernLoginDialog

    assert env.list_users() == []
    dlg = ModernLoginDialog()
    assert env.list_users() == [], "the screen created an account by itself"
    assert not dlg.pin_edit.isEnabled()
    assert "Create the first account" in dlg.add_account.text()
    dlg.deleteLater()


def test_the_first_account_needs_nobody_to_approve_it(screen):
    env, dlg = screen
    dlg.show_signup()
    assert dlg.admin_block.isHidden()


def test_every_later_account_needs_an_administrator(screen):
    from app.core import auth

    env, dlg = screen
    env.create_user("saheed", "Saheed", "4821", auth.ROLE_ADMIN,
                    auth.ALL_PERMISSIONS)
    dlg.show_signup()
    assert not dlg.admin_block.isHidden()

    dlg.su_name.setText("Ritu Patil")
    dlg.su_username.setText("ritu")
    dlg.su_pin.setText("7392")
    dlg.su_pin2.setText("7392")
    dlg.su_admin_pin.setText("1598")            # the old master PIN
    dlg._do_sign_up()

    assert [u.username for u in env.list_users()] == ["saheed"]
    assert not dlg.signup_error.isHidden()


def test_an_administrator_can_create_an_account(screen):
    from app.core import auth

    env, dlg = screen
    env.create_user("saheed", "Saheed", "4821", auth.ROLE_ADMIN,
                    auth.ALL_PERMISSIONS)
    dlg.show_signup()
    dlg.su_name.setText("Ritu Patil")
    dlg.su_username.setText("ritu")
    dlg.su_pin.setText("7392")
    dlg.su_pin2.setText("7392")
    dlg.su_admin_pin.setText("4821")
    dlg._do_sign_up()

    assert "ritu" in [u.username for u in env.list_users()]
    # Made, but not signed in: the person who typed the admin PIN is not the
    # person the account belongs to.
    assert auth.current() is None
    assert dlg.stack.currentIndex() == 0


def test_the_two_pins_have_to_match(screen):
    from app.core import auth

    env, dlg = screen
    env.create_user("saheed", "Saheed", "4821", auth.ROLE_ADMIN,
                    auth.ALL_PERMISSIONS)
    dlg.show_signup()
    dlg.su_name.setText("Ritu")
    dlg.su_username.setText("ritu")
    dlg.su_pin.setText("7392")
    dlg.su_pin2.setText("7393")
    dlg.su_admin_pin.setText("4821")
    dlg._do_sign_up()

    assert [u.username for u in env.list_users()] == ["saheed"]


# ===========================================================================
# The screen is themed, not painted
# ===========================================================================

def test_the_screen_carries_no_colour_of_its_own(screen):
    """Every surface is named in the sheet, so the night theme reaches it."""
    _env, dlg = screen
    assert dlg.styleSheet() == ""
    for child in dlg.findChildren(type(dlg.card)):
        assert child.styleSheet() == ""


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_both_themes_name_every_part_of_the_screen(theme):
    from app.ui import style

    sheet = style.stylesheet_for(theme)
    for name in ("#signInWindow", "#hero", "#heroRule", "#signInSide",
                 "#signInCard", "#pinField", "#cardRule",
                 'role="herowordmark"', 'role="heroname"', 'role="herosub"',
                 'role="heroblurb"', 'role="herolabel"', 'role="herofact"',
                 'role="cardtitle"'):
        assert name in sheet, f"{name} is unstyled in the {theme} theme"


def test_the_facts_are_read_not_invented(screen):
    """The panel used to claim a patient count on an empty database."""
    env, dlg = screen
    facts = dict(dlg._facts())
    assert facts["Patients on file"] == "0"
    assert facts["Last backup"] == "none yet"


# ===========================================================================
# Signing out
# ===========================================================================

def test_signing_out_asks_to_come_back_rather_than_quitting(env):
    """``main`` loops while this flag is set, instead of ending the program."""
    from app.core import auth
    from app.ui.main_window import MainWindow

    env.create_user("saheed", "Saheed", "4821", auth.ROLE_ADMIN,
                    auth.ALL_PERMISSIONS)
    auth.set_current(env.sign_in("saheed", "4821"))

    window = MainWindow()
    assert window.was_signed_out is False
    window._sign_out()
    assert window.was_signed_out is True
    window.deleteLater()
