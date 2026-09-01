"""Referring doctors: who they are, where they work, and their commission.

The editor lives here and is used from two places — the Doctors tab, and the
quick "add the doctor I just typed" prompt on the job screen — so a doctor
added in a hurry at the counter has exactly the same record as one entered
properly afterwards.
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QLineEdit, QVBoxLayout,
)

from ..db import queries as q
from .widgets import Table, button, confirm, label, row, warn

#: Offered in the profession box, which stays editable — a lab that deals with
#: a speciality this list has never heard of must not be stuck with the list.
PROFESSIONS = [
    "General Physician", "General Surgeon", "Paediatrician", "Gynaecologist",
    "Orthopaedic Surgeon", "Cardiologist", "Diabetologist", "Nephrologist",
    "Dermatologist", "ENT Surgeon", "Ophthalmologist", "Neurologist",
    "Pulmonologist", "Gastroenterologist", "Urologist", "Oncologist",
    "Psychiatrist", "Ayurveda Physician", "Homeopath", "Dentist",
]


class ReferrerEditor(QDialog):
    def __init__(self, data: Optional[dict], parent=None, name: str = ""):
        super().__init__(parent)
        self.data = dict(data or {})
        self.setWindowTitle("Edit doctor" if data else "New doctor")
        self.setMinimumWidth(460)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(10)
        form = QFormLayout()
        form.setSpacing(9)

        self.name_edit = QLineEdit(self.data.get("name", "") or name)
        self.name_edit.setPlaceholderText("Dr. S. Mehta")
        self.qual_edit = QLineEdit(self.data.get("qualification", ""))
        self.qual_edit.setPlaceholderText("MBBS, MD")
        self.prof_combo = QComboBox()
        self.prof_combo.setEditable(True)
        self.prof_combo.addItem("")
        self.prof_combo.addItems(PROFESSIONS)
        self.prof_combo.setCurrentText(self.data.get("profession", "") or "")
        self.hospital_edit = QLineEdit(self.data.get("hospital", ""))
        self.hospital_edit.setPlaceholderText("Clinic or hospital they work from")
        self.phone_edit = QLineEdit(self.data.get("phone", ""))
        self.phone_edit.setPlaceholderText("Number to ring them back on")
        self.pct_spin = QDoubleSpinBox()
        self.pct_spin.setRange(0, 100)
        self.pct_spin.setSuffix(" %")
        self.pct_spin.setValue(float(self.data.get("commission_percent") or 0))

        form.addRow("Name", self.name_edit)
        form.addRow("Qualification", self.qual_edit)
        form.addRow("Profession", self.prof_combo)
        form.addRow("Hospital / clinic", self.hospital_edit)
        form.addRow("Contact number", self.phone_edit)
        form.addRow("Commission", self.pct_spin)
        lay.addLayout(form)

        lay.addWidget(label(
            "The contact number is for the lab, not the patient — it is what you "
            "ring when a result needs telling straight away. It never prints on "
            "a report.", "hint"))
        lay.addWidget(label(
            "Commission is worked out from the net bill amount.", "hint"))
        lay.addWidget(row(None, button("Cancel", "", self.reject),
                          button("Save", "primary", self._save)))
        self.name_edit.setFocus()

    def _save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            warn(self, "Name needed", "Enter the doctor's name.")
            return
        self.saved_id = q.save_referrer({
            "id": self.data.get("id"),
            "name": name,
            "qualification": self.qual_edit.text().strip(),
            "profession": self.prof_combo.currentText().strip(),
            "hospital": self.hospital_edit.text().strip(),
            "phone": self.phone_edit.text().strip(),
            "commission_percent": self.pct_spin.value(),
            "active": 1,
        })
        self.accept()


class ReferrersDialog(QDialog):
    """The same list as the Doctors tab, for reaching it from elsewhere."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Referring doctors")
        self.resize(720, 460)

        from .doctors_screen import DoctorsScreen

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        self.screen = DoctorsScreen(self)
        lay.addWidget(self.screen, 1)
        lay.addWidget(row(None, button("Close", "primary", self.accept)))

    def refresh(self) -> None:
        self.screen.refresh()
