"""Doctors — everyone who sends the lab work, and how to reach them.

Kept as its own tab rather than a dialog buried under Tests, because the list
is looked at daily: to ring a doctor about a critical result, to check who
referred a patient, and to settle commissions at the end of the month.
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from ..core import billing
from ..db import queries as q
from .widgets import (
    SearchBox, Table, button, confirm, info, label, row, warn,
)


class DoctorsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: List[dict] = []
        self.show_hidden = False
        self._build()
        self.refresh()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 10)
        lay.setSpacing(10)

        lay.addWidget(label(
            "Doctors who refer patients here. Choosing one on the job screen "
            "puts their name on the report.", "hint"))

        self.search = SearchBox("Search by name, profession, hospital or number…")
        self.search.searched.connect(lambda _t: self.refresh())
        self.hidden_button = button("Show hidden", "", self._toggle_hidden,
                                    "Include doctors who have been removed")
        self.hidden_button.setCheckable(True)
        lay.addWidget(row(self.search,
                          button("Add doctor", "primary", self._new),
                          button("Edit", "", self._edit),
                          button("Remove", "danger", self._remove),
                          self.hidden_button))

        self.table = Table(["Name", "Profession", "Hospital / clinic",
                            "Contact number", "Qualification", "Commission",
                            "Patients sent"],
                           stretch_column=2,
                           empty_text="No doctors yet.\n\n"
                                      "Add one, and it appears in the "
                                      "“Referred by Dr” list on the job screen.")
        self.table.doubleClicked.connect(self._edit)
        lay.addWidget(self.table, 1)

        self.count_label = label("", "hint")
        lay.addWidget(row(self.count_label, None,
                          button("Refresh", "", self.refresh)))

    # ------------------------------------------------------------------ data
    def refresh(self) -> None:
        term = self.search.text().strip()
        self.rows = q.search_referrers(term, include_inactive=self.show_hidden)
        counts = q.jobs_per_referrer()

        display = []
        for r in self.rows:
            name = r["name"] + ("" if r["active"] else "   · hidden")
            display.append([
                name, r["profession"] or "—", r["hospital"] or "—",
                r["phone"] or "—", r["qualification"] or "—",
                f"{r['commission_percent']:g} %" if r["commission_percent"] else "—",
                str(counts.get(r["id"], 0)),
            ])
        self.table.set_rows(display)
        self.count_label.setText(
            f"{len(self.rows)} doctor{'s' if len(self.rows) != 1 else ''}"
            + ("   ·   including hidden ones" if self.show_hidden else ""))

    def _toggle_hidden(self) -> None:
        self.show_hidden = self.hidden_button.isChecked()
        self.hidden_button.setText("Hide removed" if self.show_hidden
                                   else "Show hidden")
        self.refresh()

    def _selected(self) -> Optional[dict]:
        i = self.table.selected_row()
        return self.rows[i] if 0 <= i < len(self.rows) else None

    # --------------------------------------------------------------- actions
    def _new(self) -> None:
        from .referrers_dialog import ReferrerEditor

        if ReferrerEditor(None, self).exec():
            self.search.clear()
            self.refresh()

    def _edit(self) -> None:
        from .referrers_dialog import ReferrerEditor

        r = self._selected()
        if not r:
            warn(self, "Nothing chosen", "Pick a doctor in the list first.")
            return
        if ReferrerEditor(r, self).exec():
            self.refresh()

    def _remove(self) -> None:
        r = self._selected()
        if not r:
            warn(self, "Nothing chosen", "Pick a doctor in the list first.")
            return
        if not r["active"]:
            q.save_referrer({**dict(r), "active": 1})
            self.refresh()
            info(self, "Back in the list",
                 f"{r['name']} will appear again when choosing a referring doctor.")
            return

        owed = q.commission_owed(r["id"])
        extra = ""
        if owed:
            extra = (f"\n\n{billing.format_rupees(owed)} of commission is still "
                     f"recorded against them — that stays on the books.")
        if not confirm(self, "Remove this doctor?",
                       f"{r['name']} will stop appearing when you choose a "
                       f"referring doctor.\n\nJobs already sent by them keep "
                       f"their record, and you can bring them back with "
                       f"“Show hidden”.{extra}", "Remove"):
            return
        q.delete_referrer(r["id"])
        self.refresh()
