"""Signing in, and creating the first admin account.

The lab is a shared room. This is not about keeping out attackers — it is about
knowing which of three people entered a result, and stopping a temp from
changing the report letterhead or seeing the day's takings.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QGroupBox, QLineEdit, QVBoxLayout,
)

from ..core import auth
from ..db import queries as q
from . import style
from .widgets import button, error, field_label, info, label, row, warn


class FirstRunDialog(QDialog):
    """Create the very first admin, before anyone can sign in."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set up the first account")
        self.setMinimumWidth(520)
        self.created = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(11)

        title = label("Who runs this laboratory?", "h1")
        lay.addWidget(title)
        lay.addWidget(label(
            "This first account is the administrator — it can do everything, "
            "including adding staff later.\n\nKeep the PIN somewhere safe. "
            "Without an admin nobody can reach Settings.", "hint"))

        form = QFormLayout()
        form.setSpacing(9)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Abdunnaser Mayyeri")
        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("e.g. admin")
        self.pin_edit = QLineEdit()
        self.pin_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin2_edit = QLineEdit()
        self.pin2_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Full name", self.name_edit)
        form.addRow("Username", self.user_edit)
        form.addRow("PIN", self.pin_edit)
        form.addRow("PIN again", self.pin2_edit)
        lay.addLayout(form)

        self.problem = label("", "error")
        self.problem.setWordWrap(True)
        lay.addWidget(self.problem)

        self.skip_button = button("Not now — work without sign-in", "quiet", self._skip)
        lay.addWidget(row(self.skip_button, None,
                          button("Create account", "primary", self._create)))

        self.name_edit.setFocus()

    def _complain(self, text: str) -> None:
        self.problem.setText(text)
        self.problem.setStyleSheet(f"color: {style.RED}; font-weight: 600;")

    def _create(self) -> None:
        username = self.user_edit.text().strip() or "admin"
        pin, pin2 = self.pin_edit.text(), self.pin2_edit.text()

        problem = auth.check_username(username)
        if problem:
            self._complain(problem)
            return
        if pin != pin2:
            self._complain("The two PINs are different. Type the same one twice.")
            self.pin2_edit.clear()
            self.pin2_edit.setFocus()
            return
        problem = auth.check_pin_quality(pin)
        if problem:
            self._complain(problem)
            return

        try:
            uid = q.create_user(username, self.name_edit.text(), pin,
                                auth.ROLE_ADMIN, auth.ALL_PERMISSIONS)
        except (ValueError, auth.PinError) as exc:
            self._complain(str(exc))
            return

        auth.set_current(q.get_user(uid))
        self.created = True
        self.accept()

    def _skip(self) -> None:
        """Allowed on purpose: a one-person lab should not be forced into this."""
        self.created = False
        self.accept()


class LoginDialog(QDialog):
    """Username and PIN. Escape closes the program rather than bypassing it."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sign in — LabSoft")
        self.setMinimumWidth(430)
        self.user: Optional[auth.User] = None
        self._attempts = 0

        lab = (q.get_setting("lab_name_prefix") + " " + q.get_setting("lab_name")).strip()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 18)
        lay.setSpacing(10)

        heading = label(lab or "LabSoft", "h1")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(heading)
        sub = label("Sign in to continue", "hint")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)
        lay.addSpacing(6)

        lay.addWidget(field_label("Who are you?"))
        self.user_combo = QComboBox()
        self.user_combo.setEditable(True)
        for u in q.list_users():
            self.user_combo.addItem(u.display_name or u.username, u.username)
        lay.addWidget(self.user_combo)

        lay.addWidget(field_label("PIN"))
        self.pin_edit = QLineEdit()
        self.pin_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_edit.returnPressed.connect(self._sign_in)
        lay.addWidget(self.pin_edit)

        self.show_pin = QCheckBox("Show PIN")
        self.show_pin.stateChanged.connect(
            lambda _s: self.pin_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if self.show_pin.isChecked()
                else QLineEdit.EchoMode.Password))
        lay.addWidget(self.show_pin)

        self.problem = label("", "error")
        self.problem.setWordWrap(True)
        lay.addWidget(self.problem)

        lay.addWidget(row(button("Close LabSoft", "quiet", self.reject), None,
                          button("Sign in", "primary", self._sign_in)))

        self.pin_edit.setFocus()

    def _sign_in(self) -> None:
        username = (self.user_combo.currentData()
                    or self.user_combo.currentText()).strip()
        user = q.sign_in(username, self.pin_edit.text())
        if user:
            self.user = user
            self.accept()
            return

        self._attempts += 1
        self.pin_edit.clear()
        self.pin_edit.setFocus()
        # The message never says which half was wrong: naming the username as
        # correct would tell anyone holding the machine which accounts exist.
        text = "That username and PIN do not match."
        if self._attempts >= 3:
            text += ("\n\nIf you have forgotten it, an administrator can set a "
                     "new PIN for you under Settings → Staff.")
        self.problem.setText(text)
        self.problem.setStyleSheet(f"color: {style.RED}; font-weight: 600;")


def sign_in_at_startup(parent=None) -> tuple:
    """Returns (proceed, user).

    A lab with no accounts is offered the chance to make one, and may decline —
    a single-operator lab should not be forced to type a PIN all day.
    """
    if q.user_count() == 0:
        dlg = FirstRunDialog(parent)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False, None
        return True, auth.current()

    dlg = LoginDialog(parent)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return False, None
    return True, dlg.user
