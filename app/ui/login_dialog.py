"""Signing in, and creating the accounts that make signing in mean anything.

Two panels. The left is the laboratory: its name, and three facts about this
PC read from the database rather than typed in. The right asks the only two
questions there are -- who is at the counter, and their PIN.

Nothing here carries a colour of its own. Every surface is named in
``style.stylesheet_for``, so the night theme repaints it with the rest.

--------------------------------------------------------------------------
What this file used to do
--------------------------------------------------------------------------
The previous version accepted ``1598`` as a PIN for *any* account. Typing it
signed you in as whoever was selected in the dropdown -- an administrator
included, on every installation -- and the error message printed the number
when you got a PIN wrong. The same constant authorised creating accounts. It
also re-created an ``admin`` / ``1598`` login whenever the user list came
back empty, which quietly undid removing that account anywhere else.

All of it is gone. A PIN is checked against the stored hash and nothing
else. The only account that can be made without an administrator's PIN is
the very first one, on a database that has no accounts at all.
"""

from __future__ import annotations

import platform
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLineEdit,
    QStackedWidget, QVBoxLayout, QWidget,
)

from .. import config
from ..core import auth
from ..db import connection, queries as q
from .widgets import button, elevate, fade_in, label, row


class ModernLoginDialog(QDialog):
    """The sign-in screen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user: Optional[auth.User] = None
        self._attempts = 0
        self.setWindowTitle("LabSoft — sign in")
        self.setObjectName("signInWindow")
        self.resize(1100, 700)
        # A dialog gets no minimise button and, full screen, no way off the
        # screen at all: the sign-in filled the monitor with nothing to press
        # but Sign in. These are the buttons every other window has.
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowSystemMenuHint)
        self._build()
        self._refresh_users_combo()

    # ----------------------------------------------------------------- build
    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_hero(), 55)
        lay.addWidget(self._build_side(), 45)

    def _build_hero(self) -> QWidget:
        """The laboratory's own panel: who this is, and how the PC is doing."""
        hero = QFrame()
        hero.setObjectName("hero")
        lay = QVBoxLayout(hero)
        lay.setContentsMargins(56, 48, 56, 44)
        lay.setSpacing(0)

        lay.addWidget(label("LABSOFT", "herowordmark"))
        lay.addStretch(1)

        prefix = q.get_setting("lab_name_prefix") or ""
        name = q.get_setting("lab_name") or "Laboratory"
        subtitle = q.get_setting("lab_subtitle") or ""
        title = label(f"{prefix} {name}".strip(), "heroname")
        title.setWordWrap(True)
        lay.addWidget(title)
        if subtitle:
            lay.addWidget(label(subtitle.title(), "herosub"))

        blurb = label(
            "Everything runs on this PC. Signing in needs no internet, and "
            "neither does anything you do after it.", "heroblurb")
        blurb.setWordWrap(True)
        blurb.setMaximumWidth(460)
        lay.addSpacing(18)
        lay.addWidget(blurb)
        lay.addStretch(1)

        rule = QFrame()
        rule.setObjectName("heroRule")
        rule.setFixedHeight(1)
        lay.addWidget(rule)
        lay.addSpacing(18)

        facts = QHBoxLayout()
        facts.setContentsMargins(0, 0, 0, 0)
        facts.setSpacing(40)
        for caption, value in self._facts():
            block = QVBoxLayout()
            block.setContentsMargins(0, 0, 0, 0)
            block.setSpacing(4)
            block.addWidget(label(caption, "herolabel"))
            block.addWidget(label(value, "herofact"))
            facts.addLayout(block)
        facts.addStretch(1)
        lay.addLayout(facts)
        return hero

    @staticmethod
    def _facts() -> list:
        """Three things about this machine, all read rather than written.

        The panel used to claim "4,812 patients on file" whether or not the
        database held any. A number on a sign-in screen that nobody can check
        is worse than no number.
        """
        try:
            people = f"{q.patient_count():,}"
        except Exception:
            people = "—"
        last = connection.last_backup_time()
        return [
            ("This PC", platform.node() or "this computer"),
            ("Patients on file", people),
            ("Last backup", last.strftime("%d-%m %H:%M") if last else "none yet"),
        ]

    def _build_side(self) -> QWidget:
        side = QFrame()
        side.setObjectName("signInSide")
        outer = QVBoxLayout(side)
        outer.setContentsMargins(40, 40, 40, 40)
        outer.addStretch(1)

        holder = QHBoxLayout()
        holder.addStretch(1)

        self.card = QFrame()
        self.card.setObjectName("signInCard")
        self.card.setFixedWidth(420)
        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(32, 30, 32, 28)
        card_lay.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_signin_view())
        self.stack.addWidget(self._build_signup_view())
        card_lay.addWidget(self.stack)

        # Qt stylesheets have no box-shadow, so the card is lifted off the
        # ground with a graphics effect instead.
        elevate(self.card, 2)
        holder.addWidget(self.card)
        holder.addStretch(1)
        outer.addLayout(holder)
        outer.addStretch(1)
        return side

    # -------------------------------------------------------------- sign in
    def _build_signin_view(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(label("Sign in", "cardtitle"))
        self.when = label("", "hint")
        lay.addWidget(self.when)
        lay.addSpacing(22)

        lay.addWidget(label("Who is at the counter", "field"))
        lay.addSpacing(6)
        self.user_combo = QComboBox()
        self.user_combo.setFixedHeight(44)
        lay.addWidget(self.user_combo)
        lay.addSpacing(16)

        lay.addWidget(label("PIN", "field"))
        lay.addSpacing(6)
        self.pin_edit = QLineEdit()
        self.pin_edit.setObjectName("pinField")
        self.pin_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_edit.setFixedHeight(44)
        self.pin_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pin_edit.setPlaceholderText("••••")
        self.pin_edit.returnPressed.connect(self._do_sign_in)
        lay.addWidget(self.pin_edit)

        self.signin_error = label("", "error")
        self.signin_error.setWordWrap(True)
        self.signin_error.hide()
        lay.addSpacing(8)
        lay.addWidget(self.signin_error)

        lay.addSpacing(18)
        go = button("Sign in", "primary", self._do_sign_in)
        go.setFixedHeight(46)
        lay.addWidget(go)

        lay.addSpacing(20)
        rule = QFrame()
        rule.setObjectName("cardRule")
        rule.setFixedHeight(1)
        lay.addWidget(rule)
        lay.addSpacing(14)

        health = QHBoxLayout()
        health.setSpacing(9)
        dot = QFrame()
        dot.setObjectName("signedInDot")
        dot.setFixedSize(8, 8)
        health.addWidget(dot)
        self.health = label("", "hint")
        health.addWidget(self.health)
        health.addStretch(1)
        lay.addLayout(health)

        lay.addSpacing(6)
        self.forgotten = label("", "hint")
        self.forgotten.setWordWrap(True)
        lay.addWidget(self.forgotten)

        lay.addSpacing(10)
        self.add_account = button("Add a staff account", "quiet", self.show_signup)
        lay.addWidget(row(self.add_account, None))
        return page

    def _refresh_users_combo(self) -> None:
        """Fill the list, and say plainly when there is nobody to fill it with.

        This used to create an administrator with a fixed PIN when the list
        came back empty. A program that invents its own way in is a program
        with no way of keeping anybody out.
        """
        self.user_combo.clear()
        users = q.list_users()
        for u in users:
            role = "administrator" if u.is_admin else (u.role or "staff")
            self.user_combo.addItem(f"{u.display_name or u.username} · {role}",
                                    u.username)

        first_run = not users
        self.user_combo.setEnabled(not first_run)
        self.pin_edit.setEnabled(not first_run)
        self.add_account.setText("Create the first account" if first_run
                                 else "Add a staff account")
        if first_run:
            self.user_combo.addItem("No accounts yet", "")
            self.signin_error.setText(
                "Nobody can sign in yet. Create the first account to begin — "
                "it will be the administrator.")
            self.signin_error.show()

        now = datetime.now()
        self.when.setText(now.strftime("%A %d-%m-%Y · %H:%M")
                          + f" · version {config.APP_VERSION}")
        last = connection.last_backup_time()
        self.health.setText(
            f"Database open · last backup {last.strftime('%d-%m %H:%M')}"
            if last else "Database open · no backup taken yet")
        self.forgotten.setText(
            "Forgotten your PIN? An administrator can set a new one for you "
            "under Staff.")
        # The name is nearly always already right, so the cursor starts where
        # the typing starts.
        if not first_run:
            self.pin_edit.setFocus()

    def _do_sign_in(self) -> None:
        username = (self.user_combo.currentData() or "").strip()
        pin = self.pin_edit.text().strip()

        if not username:
            self.signin_error.setText("There is nobody to sign in as yet.")
            self.signin_error.show()
            return
        if not pin:
            self.signin_error.setText("Enter your PIN.")
            self.signin_error.show()
            return

        # The only check there is. A PIN either matches the stored hash for
        # this account or it does not, and there is no other way through.
        user = q.sign_in(username, pin)
        if user:
            self.user = user
            auth.set_current(user)
            self.accept()
            return

        self._attempts += 1
        self.pin_edit.clear()
        self.pin_edit.setFocus()
        self.signin_error.setText(
            "That PIN does not match this account."
            + ("  An administrator can set you a new one under Staff."
               if self._attempts >= 3 else ""))
        self.signin_error.show()

    # -------------------------------------------------------------- sign up
    def _build_signup_view(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(label("New account", "cardtitle"))
        self.signup_note = label("", "hint")
        self.signup_note.setWordWrap(True)
        lay.addWidget(self.signup_note)
        lay.addSpacing(20)

        lay.addWidget(label("Their name", "field"))
        lay.addSpacing(6)
        self.su_name = QLineEdit()
        self.su_name.setFixedHeight(40)
        self.su_name.setPlaceholderText("Ritu Patil")
        lay.addWidget(self.su_name)
        lay.addSpacing(14)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        grid.addWidget(label("Username", "field"), 0, 0)
        grid.addWidget(label("Role", "field"), 0, 1)
        self.su_username = QLineEdit()
        self.su_username.setFixedHeight(40)
        self.su_username.setPlaceholderText("ritu")
        self.su_role = QComboBox()
        self.su_role.setFixedHeight(40)
        self.su_role.addItem("Reception", auth.ROLE_STAFF)
        self.su_role.addItem("Technologist", auth.ROLE_STAFF)
        self.su_role.addItem("Administrator", auth.ROLE_ADMIN)
        grid.addWidget(self.su_username, 1, 0)
        grid.addWidget(self.su_role, 1, 1)
        lay.addLayout(grid)
        lay.addSpacing(14)

        pins = QGridLayout()
        pins.setContentsMargins(0, 0, 0, 0)
        pins.setHorizontalSpacing(12)
        pins.setVerticalSpacing(6)
        pins.addWidget(label("PIN", "field"), 0, 0)
        pins.addWidget(label("PIN again", "field"), 0, 1)
        self.su_pin = QLineEdit()
        self.su_pin2 = QLineEdit()
        for box in (self.su_pin, self.su_pin2):
            box.setFixedHeight(40)
            box.setEchoMode(QLineEdit.EchoMode.Password)
            box.setPlaceholderText("••••")
        pins.addWidget(self.su_pin, 1, 0)
        pins.addWidget(self.su_pin2, 1, 1)
        lay.addLayout(pins)
        lay.addSpacing(14)

        self.admin_block = QWidget()
        ab = QVBoxLayout(self.admin_block)
        ab.setContentsMargins(0, 0, 0, 0)
        ab.setSpacing(6)
        ab.addWidget(label("An administrator's PIN", "field"))
        pair = QHBoxLayout()
        pair.setSpacing(12)
        self.su_admin_user = QComboBox()
        self.su_admin_user.setFixedHeight(40)
        self.su_admin_pin = QLineEdit()
        self.su_admin_pin.setFixedHeight(40)
        self.su_admin_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.su_admin_pin.setPlaceholderText("their PIN")
        # Names are longer than PINs, so they get more of the row.
        pair.addWidget(self.su_admin_user, 3)
        pair.addWidget(self.su_admin_pin, 2)
        ab.addLayout(pair)
        lay.addWidget(self.admin_block)

        self.signup_error = label("", "error")
        self.signup_error.setWordWrap(True)
        self.signup_error.hide()
        lay.addSpacing(8)
        lay.addWidget(self.signup_error)

        lay.addSpacing(18)
        make = button("Create the account", "primary", self._do_sign_up)
        make.setFixedHeight(46)
        lay.addWidget(make)
        lay.addSpacing(10)
        lay.addWidget(row(button("Back to sign in", "quiet", self.show_signin), None))
        return page

    def show_signin(self) -> None:
        self.signup_error.hide()
        self.stack.setCurrentIndex(0)
        self._refresh_users_combo()
        self.pin_edit.setFocus()

    def show_signup(self) -> None:
        """Open the new-account page, asking for authority unless it is day one."""
        admins = [u for u in q.list_users() if u.is_admin]
        self.su_admin_user.clear()
        for u in admins:
            self.su_admin_user.addItem(u.display_name or u.username, u.username)

        # The one account that needs nobody's permission is the very first one
        # on a database with NO accounts at all.
        #
        # This used to test "are there any administrators", which is not the
        # same question: an installation whose first account was created as
        # Reception then had staff and no admin for ever, and the free path
        # stayed open -- so anyone who sat down at the locked sign-in screen
        # could press "Add a staff account" and make themselves one.
        first_run = not q.list_users(include_inactive=True)
        self.admin_block.setVisible(not first_run)
        self.signup_note.setText(
            "An administrator has to approve a new account."
            if not first_run else
            "This is the first account on this PC, so it is the "
            "administrator. Choose a PIN only you know.")
        # And it is an administrator whether or not the role box says so:
        # a lab with staff accounts and nobody who can reach Settings has
        # locked itself out of its own program.
        index = self.su_role.findData(auth.ROLE_ADMIN)
        if first_run and index >= 0:
            self.su_role.setCurrentIndex(index)
        self.su_role.setEnabled(not first_run)
        self.signup_error.hide()
        self.stack.setCurrentIndex(1)
        self.su_name.setFocus()

    def _do_sign_up(self) -> None:
        name = self.su_name.text().strip()
        username = self.su_username.text().strip().lower()
        role = self.su_role.currentData() or auth.ROLE_STAFF
        pin = self.su_pin.text().strip()
        pin2 = self.su_pin2.text().strip()

        if not name or not username or not pin:
            self._signup_problem("Fill in the name, the username and a PIN.")
            return
        if pin != pin2:
            self._signup_problem("The two PINs are not the same.")
            return
        problem = auth.check_pin_quality(pin)
        if problem:
            self._signup_problem(problem)
            return

        first_run = not q.list_users(include_inactive=True)
        if first_run:
            # Forced, not merely preselected: the role box is disabled on the
            # first run, and a disabled box is not a promise.
            role = auth.ROLE_ADMIN
        else:
            # Checked against a real administrator's stored PIN. There is no
            # master PIN, and there was never a good reason for one.
            if not [u for u in q.list_users() if u.is_admin]:
                self._signup_problem(
                    "There is no administrator on this PC to approve a new "
                    "account. Ask whoever set LabSoft up.")
                return
            approver = (self.su_admin_user.currentData() or "").strip()
            approval = self.su_admin_pin.text().strip()
            # check_pin, not sign_in: approving an account must not quietly
            # hand the counter over to whoever typed the PIN.
            if not approval or not q.check_pin(approver, approval):
                self._signup_problem(
                    "That administrator's PIN does not match. Only an "
                    "administrator can create an account.")
                return

        try:
            perms = (auth.ALL_PERMISSIONS if role == auth.ROLE_ADMIN
                     else auth.STAFF_DEFAULT)
            q.create_user(username, name, pin, role, perms)
        except Exception as exc:                       # readable, not a trace
            self._signup_problem(str(exc))
            return

        # Created, but not signed in: whoever typed an administrator's PIN is
        # not necessarily the person the account is for.
        for box in (self.su_name, self.su_username, self.su_pin, self.su_pin2,
                    self.su_admin_pin):
            box.clear()
        self.show_signin()
        index = self.user_combo.findData(username)
        if index >= 0:
            self.user_combo.setCurrentIndex(index)
        self.signin_error.setText(
            f"{name} can sign in now. Hand the PC over and let them type "
            f"their own PIN.")
        self.signin_error.show()

    def _signup_problem(self, text: str) -> None:
        self.signup_error.setText(text)
        self.signup_error.show()


def sign_in_at_startup(parent=None) -> tuple[bool, Optional[auth.User]]:
    """Ask who is there, before anything is shown."""
    dlg = ModernLoginDialog(parent)
    # Maximised, not full screen. Full screen took the title bar with it, so
    # there was nothing to minimise or close the window with.
    dlg.showMaximized()
    fade_in(dlg, 180)
    dlg.pin_edit.setFocus()
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return False, None
    return True, dlg.user
