"""Panels: named groups of tests, and the quick buttons on the job screen."""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDoubleSpinBox, QLineEdit, QListWidget, QListWidgetItem,
    QVBoxLayout,
)

from ..core import billing
from ..db import queries as q
from .widgets import Table, button, confirm, field_label, label, row, warn


class PanelEditor(QDialog):
    def __init__(self, panel_id: Optional[int], parent=None):
        super().__init__(parent)
        self.panel_id = panel_id
        self.setWindowTitle("Edit panel" if panel_id else "New panel")
        self.resize(520, 620)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(9)

        self.name_edit = QLineEdit()
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 999999)
        self.price_spin.setPrefix("₹ ")
        self.quick_check = QCheckBox("Show as a one-click button on the job screen")

        lay.addWidget(field_label("Panel name"))
        lay.addWidget(self.name_edit)
        lay.addWidget(field_label("Bundled price (0 = add up the tests)"))
        lay.addWidget(self.price_spin)
        lay.addWidget(self.quick_check)

        lay.addWidget(field_label("Tests in this panel"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter the list…")
        self.search.textChanged.connect(self._filter)
        lay.addWidget(self.search)

        self.list = QListWidget()
        lay.addWidget(self.list, 1)

        lay.addWidget(row(None, button("Cancel", "", self.reject),
                          button("Save", "primary", self._save)))
        self._load()

    def _load(self) -> None:
        chosen = set(q.panel_test_ids(self.panel_id)) if self.panel_id else set()
        if self.panel_id:
            p = next((x for x in q.list_panels() if x["id"] == self.panel_id), None)
            if p:
                self.name_edit.setText(p["name"])
                self.price_spin.setValue(billing.to_rupees(p["price_paise"] or 0))
                self.quick_check.setChecked(bool(p["quick_button"]))

        for t in q.list_tests():
            item = QListWidgetItem(f"{t['name']}    ·    {t['group_name']}")
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if t["id"] in chosen
                               else Qt.CheckState.Unchecked)
            self.list.addItem(item)

    def _filter(self, text: str) -> None:
        text = (text or "").lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(text) and text not in item.text().lower()
                           and item.checkState() != Qt.CheckState.Checked)

    def _save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            warn(self, "Name needed", "Give the panel a name first.")
            return
        ids = [self.list.item(i).data(Qt.ItemDataRole.UserRole)
               for i in range(self.list.count())
               if self.list.item(i).checkState() == Qt.CheckState.Checked]
        if not ids:
            warn(self, "No tests chosen", "A panel needs at least one test in it.")
            return
        price = billing.to_paise(self.price_spin.value())
        q.save_panel({"id": self.panel_id, "name": name,
                      "price_paise": price or None,
                      "quick_button": 1 if self.quick_check.isChecked() else 0,
                      "sort_order": 0, "active": 1}, ids)
        self.accept()


class PanelsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Panels")
        self.resize(620, 460)
        self.panels: List[dict] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(9)
        lay.addWidget(label("Panels group several tests so a common job is one click.",
                            "hint"))

        self.table = Table(["Panel", "Tests", "Price", "Quick button"], stretch_column=0)
        self.table.doubleClicked.connect(self._edit)
        lay.addWidget(self.table, 1)
        lay.addWidget(row(button("New", "primary", self._new),
                          button("Edit", "", self._edit),
                          button("Remove", "danger", self._remove),
                          None, button("Close", "", self.accept)))
        self.refresh()

    def refresh(self) -> None:
        self.panels = q.list_panels()
        self.table.set_rows([
            [p["name"], len(q.panel_test_ids(p["id"])),
             billing.format_rupees(p["price_paise"]) if p["price_paise"] else "—",
             "Yes" if p["quick_button"] else ""]
            for p in self.panels
        ])

    def _selected(self) -> Optional[dict]:
        i = self.table.selected_row()
        return self.panels[i] if 0 <= i < len(self.panels) else None

    def _new(self) -> None:
        if PanelEditor(None, self).exec():
            self.refresh()

    def _edit(self) -> None:
        p = self._selected()
        if p and PanelEditor(p["id"], self).exec():
            self.refresh()

    def _remove(self) -> None:
        p = self._selected()
        if not p:
            return
        if not confirm(self, "Remove this panel?",
                       f"'{p['name']}' will no longer appear. The tests inside it "
                       f"are not affected.", "Remove"):
            return
        q.save_panel({"id": p["id"], "name": p["name"],
                      "price_paise": p["price_paise"], "quick_button": 0,
                      "sort_order": p["sort_order"], "active": 0},
                     q.panel_test_ids(p["id"]))
        self.refresh()
