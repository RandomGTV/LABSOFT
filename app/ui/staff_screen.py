"""Staff — who can sign in, with what PIN, and what each is allowed to do.

Its own tab because creating a login is something an administrator does on the
day someone joins, and hunting for it three levels down in Settings is how it
ends up not being done at all.
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

from ..core import auth
from ..db import queries as q
from . import style
from .widgets import (
    SearchBox, Table, button, confirm, info, label, row, warn,
)


class StaffScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.users: List[auth.User] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 10)
        lay.setSpacing(10)

        lay.addWidget(label(
            "Everyone who can sign in. Each person gets their own username and "
            "PIN, and you tick exactly what they may do — every report, bill "
            "and change is recorded against whoever made it.", "hint"))

        self.search = SearchBox("Search staff by name or username…")
        self.search.searched.connect(lambda _t: self.refresh())
        lay.addWidget(row(self.search,
                          button("Create login", "primary", self._add,
                                 "Add a person with their own username and PIN"),
                          button("Edit", "", self._edit),
                          button("Set a new PIN", "", self._reset_pin),
                          button("Turn off access", "danger", self._deactivate)))

        self.table = Table(["Name", "Username", "Account", "May…"],
                           stretch_column=3,
                           empty_text="No staff accounts yet.\n\n"
                                      "Create one and LabSoft will ask for a PIN "
                                      "next time it opens.")
        self.table.doubleClicked.connect(self._edit)
        lay.addWidget(self.table, 1)

        self.note = label("", "hint")
        self.note.setWordWrap(True)
        lay.addWidget(self.note)

    # ------------------------------------------------------------------ data
    def refresh(self) -> None:
        term = self.search.text().strip().lower()
        everyone = q.list_users(include_inactive=True)
        self.users = [u for u in everyone
                      if not term
                      or term in (u.display_name or "").lower()
                      or term in u.username.lower()]

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

        me = auth.current()
        active = sum(1 for u in everyone if u.active)
        self.note.setText(
            f"{active} account{'s' if active != 1 else ''} can sign in."
            + (f"   Signed in as {me.label}." if me else
               "   Nobody is signed in — LabSoft is running without accounts, "
               "so everything is available to whoever is at the PC.")
            + "\nPINs are stored scrambled: nobody, not even an administrator, "
              "can read one back — you can only set a new one.")

    def _selected(self) -> Optional[auth.User]:
        i = self.table.selected_row()
        return self.users[i] if 0 <= i < len(self.users) else None

    def _may_manage(self) -> bool:
        if auth.can(auth.P_USERS):
            return True
        warn(self, "Not allowed",
             "Only an administrator can add or change staff accounts.")
        return False

    # --------------------------------------------------------------- actions
    def _add(self) -> None:
        from .users_dialog import UserEditor

        if not self._may_manage():
            return
        if UserEditor(None, self).exec():
            self.search.clear()
            self.refresh()

    def _edit(self) -> None:
        from .users_dialog import UserEditor

        u = self._selected()
        if not u:
            warn(self, "Nothing chosen", "Pick a person in the list first.")
            return
        if not self._may_manage():
            return
        if UserEditor(u, self).exec():
            self.refresh()

    def _reset_pin(self) -> None:
        from PyQt6.QtWidgets import QInputDialog

        u = self._selected()
        if not u:
            warn(self, "Nothing chosen", "Pick a person in the list first.")
            return
        if not self._may_manage():
            return
        pin, ok = QInputDialog.getText(
            self, "Set a new PIN", f"New PIN for {u.display_name or u.username}:",
            QLineEdit.EchoMode.Password)
        if not ok:
            return
        try:
            q.set_user_pin(u.id, pin)
        except auth.PinError as exc:
            warn(self, "PIN not changed", str(exc))
            return
        info(self, "PIN changed",
             f"{u.display_name or u.username} can sign in with the new PIN now.")

    def _deactivate(self) -> None:
        u = self._selected()
        if not u:
            warn(self, "Nothing chosen", "Pick a person in the list first.")
            return
        if not self._may_manage():
            return
        if u.active and u.is_admin and q.last_admin_standing(u.id):
            warn(self, "Cannot turn this account off",
                 "This is the only administrator. Turning it off would leave "
                 "nobody able to reach Settings or add staff.\n\n"
                 "Make someone else an administrator first.")
            return
        if u.active and not confirm(
                self, "Turn off this account?",
                f"{u.display_name or u.username} will no longer be able to sign "
                f"in.\n\nNothing they have already done is affected, and you can "
                f"turn the account back on later.", "Turn it off"):
            return
        q.update_user(u.id, active=not u.active)
        self.refresh()
