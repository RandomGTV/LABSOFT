"""Patient records: every person, every visit, every report.

Each patient has a real folder on disk holding their reports and a plain-text
card of their details. That folder is readable without LabSoft — from Explorer,
from a backup, or on another computer years from now — which is the point of
keeping records at all.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHBoxLayout, QSplitter, QVBoxLayout, QWidget

from .. import config, services
from ..core import turnaround
from ..db import queries as q
from ..output import sender
from . import style
from .widgets import SearchBox, Table, button, error, field_label, info, label, row, warn


class PatientsScreen(QWidget):
    open_job = pyqtSignal(int)
    preview_job = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.patients: List[dict] = []
        self.jobs: List[dict] = []
        self.files: List[Path] = []
        self._build()
        self.refresh()

    # ----------------------------------------------------------------- build
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 10)
        lay.setSpacing(10)

        self.search = SearchBox("Search patients by name or mobile number…")
        self.search.searched.connect(lambda _t: self.refresh())
        lay.addWidget(self.search)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 6, 0)
        left_lay.addWidget(field_label("Patients"))
        self.patient_table = Table(
            ["Name", "Mobile", "Age", "Visits", "Last visit"], stretch_column=0,
            empty_text="No patients yet.\n\nRegister one on the Job tab.")
        self.patient_table.itemSelectionChanged.connect(self._patient_selected)
        left_lay.addWidget(self.patient_table, 1)
        splitter.addWidget(left)

        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(6, 0, 0, 0)

        self.who = label("", "h1")
        right_lay.addWidget(self.who)
        self.details = label("", "hint")
        self.details.setWordWrap(True)
        right_lay.addWidget(self.details)

        right_lay.addWidget(field_label("Visits"))
        self.job_table = Table(["Report No", "Date", "Tests", "Status"],
                               stretch_column=2,
                               empty_text="This patient has no visits recorded.")
        self.job_table.doubleClicked.connect(self._open_job)
        right_lay.addWidget(self.job_table, 1)

        right_lay.addWidget(row(
            button("Open visit", "primary", self._open_job),
            button("Preview report", "", self._preview_job),
            button("Send again", "", self._send_again), None))

        right_lay.addWidget(field_label("Files in this patient's folder"))
        self.file_table = Table(["File", "Size", "Saved"], stretch_column=0,
                                empty_text="No reports saved for this patient yet.")
        self.file_table.doubleClicked.connect(self._open_file)
        right_lay.addWidget(self.file_table, 1)

        right_lay.addWidget(row(
            button("Open folder", "", self._open_folder),
            button("Open file", "", self._open_file),
            button("Refresh card", "", self._rewrite_summary), None))

        splitter.addWidget(right)
        splitter.setSizes([420, 700])
        lay.addWidget(splitter, 1)

        self.count_label = label("", "hint")
        lay.addWidget(self.count_label)

    # ------------------------------------------------------------------ data
    def refresh(self) -> None:
        term = self.search.text().strip()
        self.patients = q.search_patients(term, limit=500) if term \
            else q.recent_patients(500)

        rows = []
        for p in self.patients:
            jobs = q.patient_jobs(p["id"])
            last = turnaround.format_date(q.to_dt(jobs[0]["received_at"])) if jobs else ""
            rows.append([q.patient_full_name(p), p["phone"] or "", q._age_text(p) or "",
                         len(jobs), last])
        self.patient_table.set_rows(rows)
        self.count_label.setText(f"{len(self.patients)} patients")
        if self.patients:
            self.patient_table.selectRow(0)
        else:
            self._show_patient(None)

    def _current_patient(self) -> Optional[dict]:
        i = self.patient_table.selected_row()
        return self.patients[i] if 0 <= i < len(self.patients) else None

    def _patient_selected(self) -> None:
        self._show_patient(self._current_patient())

    def _show_patient(self, patient: Optional[dict]) -> None:
        if not patient:
            self.who.setText("")
            self.details.setText("")
            self.job_table.set_rows([])
            self.file_table.set_rows([])
            self.jobs, self.files = [], []
            return

        self.who.setText(q.patient_full_name(patient))
        bits = [patient["phone"] or "no mobile number",
                patient.get("sex") or "",
                q._age_text(patient) or ""]
        if patient.get("address"):
            bits.append(patient["address"])
        self.details.setText("   ·   ".join(b for b in bits if b))

        self.jobs = q.patient_jobs(patient["id"])
        colours = {}
        rows = []
        for i, j in enumerate(self.jobs):
            rows.append([j["report_no"],
                         turnaround.format_date(q.to_dt(j["received_at"])),
                         j["n_tests"],
                         turnaround.status_label(j["status"])])
            if j["status"] == turnaround.STATUS_SENT:
                colours[i] = QColor(style.GREEN)
        self.job_table.set_rows(rows, colours)

        self._load_files(patient)

    def _load_files(self, patient: dict) -> None:
        folder = config.patient_dir(patient["id"], patient["name"], patient.get("phone", ""))
        try:
            self.files = sorted([p for p in folder.iterdir() if p.is_file()],
                                key=lambda p: p.stat().st_mtime, reverse=True)
        except OSError:
            self.files = []
        rows = []
        for f in self.files:
            try:
                stat = f.stat()
                size = f"{max(1, stat.st_size // 1024)} KB"
                when = turnaround.format_dt(
                    __import__("datetime").datetime.fromtimestamp(stat.st_mtime))
            except OSError:
                size, when = "", ""
            rows.append([f.name, size, when])
        self.file_table.set_rows(rows)
        self.file_table.set_empty_text(
            f"No reports saved yet.\n\nThey will appear in:\n{folder}")

    # --------------------------------------------------------------- actions
    def _selected_job(self) -> Optional[dict]:
        i = self.job_table.selected_row()
        return self.jobs[i] if 0 <= i < len(self.jobs) else None

    def _open_job(self) -> None:
        j = self._selected_job()
        if j:
            self.open_job.emit(j["id"])

    def _preview_job(self) -> None:
        j = self._selected_job()
        if j:
            self.preview_job.emit(j["id"])

    def _send_again(self) -> None:
        j = self._selected_job()
        if not j:
            return
        from .send_dialog import SendDialog

        SendDialog(j["id"], self).exec()
        self.refresh()

    def _open_folder(self) -> None:
        p = self._current_patient()
        if not p:
            return
        folder = config.patient_dir(p["id"], p["name"], p.get("phone", ""))
        services.write_patient_summary(p["id"])
        sender.open_folder(folder / "_patient details.txt")

    def _open_file(self) -> None:
        i = self.file_table.selected_row()
        if not (0 <= i < len(self.files)):
            warn(self, "No file chosen", "Select a file in the list first.")
            return
        path = self.files[i]
        try:
            import os
            import platform
            import subprocess

            if platform.system() == "Windows":
                os.startfile(str(path))          # type: ignore[attr-defined]
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            error(self, "Could not open the file",
                  f"{exc}\n\nThe file is at:\n{path}")

    def _rewrite_summary(self) -> None:
        p = self._current_patient()
        if not p:
            return
        path = services.write_patient_summary(p["id"])
        self._load_files(p)
        info(self, "Patient card updated",
             f"The details and visit list have been rewritten to:\n{path.name}")
