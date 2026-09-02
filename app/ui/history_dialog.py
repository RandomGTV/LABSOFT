"""Everything a patient has ever had done, and how each value has moved."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QComboBox, QDialog, QVBoxLayout

from ..core import turnaround
from ..db import queries as q
from . import style
from .widgets import dialog_header, Table, button, field_label, label, row


class HistoryDialog(QDialog):
    def __init__(self, patient_id: int, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        patient = q.get_patient(patient_id) or {}
        self.setWindowTitle(f"History — {patient.get('name', '')}")
        self.resize(760, 520)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.addWidget(dialog_header(
            f"History · {patient.get('name', '')}",
            "Every result this patient has had here, newest first."))
        lay.setSpacing(10)

        bits = [patient.get("name", "")]
        if patient.get("phone"):
            bits.append(patient["phone"])
        if patient.get("age_value"):
            bits.append(f"{int(patient['age_value'])} {patient.get('age_unit', '')}")
        if patient.get("sex"):
            bits.append(patient["sex"])
        lay.addWidget(label("   ·   ".join(b for b in bits if b), "h1"))

        self.jobs_table = Table(
            ["Report No", "Date", "Tests", "Status"], stretch_column=2,
            empty_text="No visits recorded for this patient yet.\n\n"
                       "Their first job will appear here.")
        # A date column narrow enough to show "02-09-2..." is a date column
        # that answers nothing.
        for column, width in ((0, 110), (1, 130)):
            self.jobs_table.setColumnWidth(column, width)
        lay.addWidget(field_label("Visits"))
        lay.addWidget(self.jobs_table, 1)

        lay.addWidget(field_label("Trend for one test"))
        self.test_combo = QComboBox()
        self.test_combo.currentIndexChanged.connect(self._load_trend)
        lay.addWidget(self.test_combo)

        self.trend_table = Table(
            ["Report No", "Date", "Result", "Flag"], stretch_column=2,
            empty_text="Pick a test above to see how it has moved.")
        for column, width in ((0, 110), (1, 130)):
            self.trend_table.setColumnWidth(column, width)
        lay.addWidget(self.trend_table, 1)

        lay.addWidget(row(None, button("Close", "primary", self.accept)))

        self._load()

    def _load(self) -> None:
        jobs = q.patient_jobs(self.patient_id)
        self.jobs_table.set_rows([
            [j["report_no"],
             turnaround.format_dt(q.to_dt(j["received_at"])),
             j["n_tests"],
             turnaround.status_label(j["status"])]
            for j in jobs
        ])

        seen = {}
        for j in jobs:
            for t in q.job_tests(j["id"]):
                seen.setdefault(t["id"], t["name"])
        self.test_combo.clear()
        for tid, name in sorted(seen.items(), key=lambda kv: kv[1]):
            self.test_combo.addItem(name, tid)
        self._load_trend()

    def _load_trend(self) -> None:
        tid = self.test_combo.currentData()
        if not tid:
            self.trend_table.set_rows([])
            return
        rows = q.previous_results(self.patient_id, tid, limit=25)
        colours = {}
        display = []
        for i, r in enumerate(rows):
            display.append([
                r["report_no"],
                turnaround.format_dt(q.to_dt(r["received_at"])),
                r["display_value"],
                {"H": "High", "L": "Low", "A": "Check", "N": ""}.get(r["flag"], ""),
            ])
            if r["flag"] in ("H", "A"):
                colours[i] = QColor(style.RED)
            elif r["flag"] == "L":
                colours[i] = QColor(style.BLUE)
        self.trend_table.set_rows(display, colours)
