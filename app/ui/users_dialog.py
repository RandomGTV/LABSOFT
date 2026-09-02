"""Staff accounts and what each person is allowed to do."""

from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QGroupBox, QLineEdit, QVBoxLayout,
)

from ..core import auth
from ..db import queries as q
from . import style
from .widgets import Table, button, confirm, error, field_label, info, label, row, warn


class UserEditor(QDialog):
    def __init__(self, user: Optional[auth.User], parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Edit staff member" if user else "Add staff member")
        self.setMinimumWidth(520)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(9)
        self.name_edit = QLineEdit(user.display_name if user else "")
        self.name_edit.setPlaceholderText("Full name, as you'd say it")
        self.user_edit = QLineEdit(user.username if user else "")
        self.user_edit.setPlaceholderText("short name used to sign in")
        if user:
            self.user_edit.setReadOnly(True)
            self.user_edit.setToolTip("A username cannot be changed once created.")
        self.role_combo = QComboBox()
        self.role_combo.addItem("Staff — only what is ticked below", auth.ROLE_STAFF)
        self.role_combo.addItem("Administrator — everything", auth.ROLE_ADMIN)
        if user and user.is_admin:
            self.role_combo.setCurrentIndex(1)
        self.role_combo.currentIndexChanged.connect(self._role_changed)

        form.addRow("Full name", self.name_edit)
        form.addRow("Username", self.user_edit)
        form.addRow("Account type", self.role_combo)
        lay.addLayout(form)

        pin_box = QGroupBox("PIN")
        pin_lay = QVBoxLayout(pin_box)
        self.pin_edit = QLineEdit()
        self.pin_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_edit.setPlaceholderText(
            "Leave empty to keep the current PIN" if user else "At least 4 characters")
        pin_lay.addWidget(self.pin_edit)
        pin_lay.addWidget(label(
            "PINs are stored scrambled — nobody, including an administrator, "
            "can read someone's PIN back. You can only set a new one.", "hint"))
        lay.addWidget(pin_box)

        self.perm_box = QGroupBox("This person may…")
        perm_lay = QVBoxLayout(self.perm_box)
        self.checks: Dict[str, QCheckBox] = {}
        for key in auth.ALL_PERMISSIONS:
            cb = QCheckBox(auth.PERMISSION_LABELS[key])
            if user:
                cb.setChecked(key in user.permissions)
            elif key in auth.STAFF_DEFAULT:
                cb.setChecked(True)
            self.checks[key] = cb
            perm_lay.addWidget(cb)
        lay.addWidget(self.perm_box)

        self.problem = label("", "error")
        self.problem.setWordWrap(True)
        lay.addWidget(self.problem)

        lay.addWidget(row(None, button("Cancel", "", self.reject),
                          button("Save", "primary", self._save)))
        self._role_changed()

    def _role_changed(self) -> None:
        is_admin = self.role_combo.currentData() == auth.ROLE_ADMIN
        self.perm_box.setEnabled(not is_admin)
        self.perm_box.setTitle("This person may…" if not is_admin
                               else "An administrator may do everything")
        if is_admin:
            for cb in self.checks.values():
                cb.setChecked(True)

    def _complain(self, text: str) -> None:
        self.problem.setText(text)
        self.problem.setStyleSheet(f"color: {style.RED}; font-weight: 600;")

    def _save(self) -> None:
        role = self.role_combo.currentData()
        chosen = [k for k, cb in self.checks.items() if cb.isChecked()]
        pin = self.pin_edit.text()

        if self.user:
            # Refuse to strip the last administrator of their powers.
            if (self.user.is_admin and role != auth.ROLE_ADMIN
                    and q.last_admin_standing(self.user.id)):
                self._complain(
                    "This is the only administrator left. Make someone else an "
                    "administrator first, otherwise nobody could reach Settings.")
                return
            try:
                q.update_user(self.user.id, display_name=self.name_edit.text(),
                              role=role, permissions=chosen)
                if pin.strip():
                    q.set_user_pin(self.user.id, pin)
            except (ValueError, auth.PinError) as exc:
                self._complain(str(exc))
                return
        else:
            try:
                q.create_user(self.user_edit.text(), self.name_edit.text(),
                              pin, role, chosen)
            except (ValueError, auth.PinError) as exc:
                self._complain(str(exc))
                return
        self.accept()


class UsersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Staff")
        self.resize(720, 460)
        self.users: List[auth.User] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(10)
        lay.addWidget(label("Everyone who can sign in, and what each may do.", "hint"))

        self.table = Table(["Name", "Username", "Account", "Can do"],
                           stretch_column=3,
                           empty_text="No staff accounts yet.")
        # Wide enough for a real name and a real role: at the default width
        # every row read "Saheed ..." and "Administ...".
        self.table.verticalHeader().setDefaultSectionSize(44)
        for column, width in ((0, 220), (1, 150), (2, 150)):
            self.table.setColumnWidth(column, width)
        self.table.doubleClicked.connect(self._edit)
        lay.addWidget(self.table, 1)

        lay.addWidget(row(button("Add staff", "primary", self._add),
                          button("Edit", "", self._edit),
                          button("Set a new PIN", "", self._reset_pin),
                          button("Turn off access", "danger", self._deactivate),
                          None, button("Close", "", self.accept)))
        self.refresh()

    def refresh(self) -> None:
        self.users = q.list_users(include_inactive=True)
        rows = []
        for u in self.users:
            if u.is_admin:
                allowed = "everything"
            elif not u.permissions:
                allowed = "nothing yet"
            else:
                allowed = ", ".join(auth.PERMISSION_SHORT[p]
                                    for p in auth.ALL_PERMISSIONS
                                    if p in u.permissions)
            rows.append([u.display_name or "—", u.username,
                         ("Administrator" if u.is_admin else "Staff")
                         + ("" if u.active else " · off"),
                         allowed])
        self.table.set_rows(rows)

    def _selected(self) -> Optional[auth.User]:
        i = self.table.selected_row()
        return self.users[i] if 0 <= i < len(self.users) else None

    def _add(self) -> None:
        if UserEditor(None, self).exec():
            self.refresh()

    def _edit(self) -> None:
        u = self._selected()
        if u and UserEditor(u, self).exec():
            self.refresh()

    def _reset_pin(self) -> None:
        u = self._selected()
        if not u:
            return
        from PyQt6.QtWidgets import QInputDialog

        pin, ok = QInputDialog.getText(
            self, "Set a new PIN",
            f"New PIN for {u.display_name or u.username}:",
            QLineEdit.EchoMode.Password)
        if not ok:
            return
        try:
            q.set_user_pin(u.id, pin)
        except auth.PinError as exc:
            warn(self, "PIN not changed", str(exc))
            return
        info(self, "PIN changed",
             f"{u.display_name or u.username} can now sign in with the new PIN.")

    def _deactivate(self) -> None:
        u = self._selected()
        if not u:
            return
        if u.active and u.is_admin and q.last_admin_standing(u.id):
            warn(self, "Cannot turn this account off",
                 "This is the only administrator. Turning it off would leave "
                 "nobody able to reach Settings or add staff.\n\n"
                 "Make someone else an administrator first.")
            return
        turning_off = u.active
        if turning_off and not confirm(
                self, "Turn off this account?",
                f"{u.display_name or u.username} will no longer be able to sign "
                f"in.\n\nNothing they have already done is affected, and you can "
                f"turn the account back on later.", "Turn it off"):
            return
        q.update_user(u.id, active=not u.active)
        self.refresh()
