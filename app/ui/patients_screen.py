"""Patient records: every person, every visit, every file on disk.

A split view. The register runs down the left; choosing someone fills the
right with who they are, what they have spent, the visits they have made and
the folder those reports actually live in.

Each patient has a real folder on disk holding their reports and a plain-text
card of their details. That folder is readable without LabSoft -- from
Explorer, from a backup, or on another computer years from now -- which is
the point of keeping records at all. It is shown on this screen with its full
path, because a record nobody can find is not a record.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QStyle, QStyledItemDelegate, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from .. import config, services
from ..core import billing, turnaround
from ..db import queries as q
from ..output import sender
from . import style
from .widgets import (
    SearchBox, Table, button, error, info, label, row, warn,
)

LIST_W = 348          # the register, straight off the artboard
ROW_H = 68            # name over meta, with room to breathe
PERSON_ROLE = Qt.ItemDataRole.UserRole + 1

#: caption and the key it reads from the summary built in _person_summary.
FIGURES = [
    ("Visits", "visits"),
    ("First seen", "first_seen"),
    ("Last visit", "last_visit"),
    ("Billed", "billed"),
    ("Outstanding", "outstanding"),
]


def _font(px: int, weight: int = 400) -> QFont:
    f = QFont(style.FONT_FAMILY)
    f.setPixelSize(px)
    f.setWeight(QFont.Weight(weight))
    return f


class PersonDelegate(QStyledItemDelegate):
    """One register row: the name, when they were last in, and who they are.

    Painted rather than built from labels for the same reason the work queue
    is -- the list is rebuilt on every keystroke in the search box, and three
    widgets per row times five hundred patients is not free.
    """

    def sizeHint(self, option, index) -> QSize:       # noqa: N802 - Qt naming
        return QSize(option.rect.width(), ROW_H)

    def paint(self, painter, option, index) -> None:  # noqa: N802
        person = index.data(PERSON_ROLE)
        if not person:
            return super().paint(painter, option, index)

        painter.save()
        painter.setClipRect(option.rect)
        r = option.rect
        chosen = bool(option.state & QStyle.StateFlag.State_Selected)

        painter.fillRect(r, QColor(style.FILL if chosen else style.PANEL))
        painter.fillRect(QRect(r.left(), r.bottom(), r.width(), 1),
                         QColor(style.LINE2))
        if chosen:
            painter.fillRect(QRect(r.left(), r.top(), 3, r.height()),
                             QColor(style.ACCENT_INK))

        left = r.left() + 20
        width = max(40, r.width() - 32)
        last = person["last"]
        last_w = QFontMetrics(_font(11)).horizontalAdvance(last) + 10 if last else 0

        self._text(painter, QRect(left, r.top() + 13, width - last_w, 20),
                   person["name"], _font(14, 600 if chosen else 500), style.INK)
        if last:
            self._text(painter, QRect(r.right() - 20 - last_w, r.top() + 14, last_w, 18),
                       last, _font(11), style.INK3, right=True)
        self._text(painter, QRect(left, r.top() + 36, width, 18),
                   person["meta"], _font(11), style.INK3)
        painter.restore()

    @staticmethod
    def _text(painter, box, text, font, colour, right: bool = False) -> None:
        painter.setFont(font)
        painter.setPen(QColor(colour))
        shown = QFontMetrics(font).elidedText(
            str(text or ""), Qt.TextElideMode.ElideRight, box.width())
        flags = Qt.AlignmentFlag.AlignVCenter | (
            Qt.AlignmentFlag.AlignRight if right else Qt.AlignmentFlag.AlignLeft)
        painter.drawText(box, int(flags), shown)


class PatientsScreen(QWidget):
    open_job = pyqtSignal(int)
    preview_job = pyqtSignal(int)
    new_job_for = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.patients: List[dict] = []
        self.jobs: List[dict] = []
        self.files: List[Path] = []
        self.folder: Optional[Path] = None
        self._build()
        self.refresh()

    # ----------------------------------------------------------------- build
    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_register())
        lay.addWidget(self._build_detail(), 1)

    def _build_register(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("register")
        panel.setFixedWidth(LIST_W)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        head = QFrame()
        head.setObjectName("registerHead")
        head_lay = QVBoxLayout(head)
        head_lay.setContentsMargins(20, 18, 20, 18)
        head_lay.setSpacing(10)

        line = QHBoxLayout()
        line.setContentsMargins(0, 0, 0, 0)
        line.addWidget(label("Patients", "field"))
        line.addStretch(1)
        self.count_label = label("", "hint")
        line.addWidget(self.count_label)
        head_lay.addLayout(line)

        self.search = SearchBox("Search by name, initials or mobile…")
        self.search.searched.connect(lambda _t: self.refresh())
        self.search.setFixedHeight(34)
        head_lay.addWidget(self.search)
        lay.addWidget(head)

        self.patient_table = Table(
            ["Patient"], stretch_column=0,
            empty_text="No patients yet.\n\nRegister one on the Job tab.")
        self.patient_table.setObjectName("registerList")
        self.patient_table.setItemDelegate(PersonDelegate(self.patient_table))
        self.patient_table.horizontalHeader().hide()
        self.patient_table.verticalHeader().setDefaultSectionSize(ROW_H)
        self.patient_table.itemSelectionChanged.connect(self._patient_selected)
        lay.addWidget(self.patient_table, 1)
        return panel

    def _build_detail(self) -> QWidget:
        side = QWidget()
        lay = QVBoxLayout(side)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_header())

        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(24, 20, 24, 16)
        body_lay.setSpacing(18)

        self.job_table = Table(["Report no", "Date", "Tests", "Status"],
                               stretch_column=3,
                               empty_text="This patient has no visits recorded.")
        # Status is the column that carries words, so it gets the slack. The
        # other three hold a number or a date and never need more room than
        # they are given here.
        for column, width in ((0, 108), (1, 124), (2, 72)):
            self.job_table.setColumnWidth(column, width)
        self.job_table.doubleClicked.connect(self._open_job)
        visits = self._titled("Visits", self.job_table, row(
            button("Open visit", "primary", self._open_job),
            button("Preview report", "", self._preview_job),
            button("Send again", "", self._send_again), None))

        self.file_table = Table(["File", "Size", "Saved"], stretch_column=0,
                                empty_text="No reports saved for this patient yet.")
        self.file_table.doubleClicked.connect(self._open_file)
        self.folder_label = label("", "hint")
        self.folder_label.setWordWrap(True)
        folder = self._titled("Folder on disk", self.file_table, row(
            button("Open folder", "", self._open_folder),
            button("Open file", "", self._open_file),
            button("Rewrite card", "", self._rewrite_summary), None),
            extra=self.folder_label)

        body_lay.addWidget(visits, 1)
        body_lay.addWidget(folder, 1)
        lay.addWidget(body, 1)
        return side

    def _build_header(self) -> QWidget:
        head = QFrame()
        head.setObjectName("filterBar")
        lay = QVBoxLayout(head)
        lay.setContentsMargins(26, 22, 26, 20)
        lay.setSpacing(16)

        top = QHBoxLayout()
        top.setSpacing(9)
        names = QVBoxLayout()
        names.setContentsMargins(0, 0, 0, 0)
        names.setSpacing(3)
        self.who = label("", "person")
        self.details = label("", "hint")
        names.addWidget(self.who)
        names.addWidget(self.details)
        top.addLayout(names)
        top.addStretch(1)
        self.new_job_button = button("New job for patient", "primary", self._new_job)
        top.addWidget(self.new_job_button, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(top)

        figures = QHBoxLayout()
        figures.setContentsMargins(0, 0, 0, 0)
        figures.setSpacing(24)
        self.figures = {}
        for caption, key in FIGURES:
            block = QFrame()
            block.setObjectName("statBlock")
            bl = QVBoxLayout(block)
            bl.setContentsMargins(12, 0, 0, 0)
            bl.setSpacing(0)
            bl.addWidget(label(caption, "statlabel"))
            value = label("—", "figure")
            self.figures[key] = value
            bl.addWidget(value)
            figures.addWidget(block)
        figures.addStretch(1)
        lay.addLayout(figures)
        return head

    @staticmethod
    def _titled(text: str, table, actions, extra=None) -> QWidget:
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(label(text, "field"))
        if extra is not None:
            lay.addWidget(extra)
        lay.addWidget(table, 1)
        lay.addWidget(actions)
        return holder

    # ------------------------------------------------------------------ data
    def refresh(self) -> None:
        term = self.search.text().strip()
        self.patients = q.search_patients(term, limit=500) if term \
            else q.recent_patients(500)

        people = []
        for p in self.patients:
            jobs = q.patient_jobs(p["id"])
            last = q.to_dt(jobs[0]["received_at"]) if jobs else None
            bits = [b for b in (p.get("sex") or "", q._age_text(p) or "",
                                p["phone"] or "") if b]
            visits = f"{len(jobs)} visit" + ("s" if len(jobs) != 1 else "")
            people.append({
                "name": q.patient_full_name(p),
                "meta": " · ".join(bits + [visits]),
                "last": turnaround.format_date(last) if last else "never in",
            })
        self._fill_register(people)

        self.count_label.setText(
            f"{len(self.patients)} shown" if term
            else f"{len(self.patients)} on this PC")
        if self.patients:
            self.patient_table.selectRow(0)
        else:
            self._show_patient(None)

    def _fill_register(self, people: List[dict]) -> None:
        table = self.patient_table
        table.setUpdatesEnabled(False)
        try:
            table.setRowCount(len(people))
            for r, person in enumerate(people):
                item = QTableWidgetItem("")
                item.setData(PERSON_ROLE, person)
                table.setItem(r, 0, item)
                table.setRowHeight(r, ROW_H)
            table._refresh_empty()
        finally:
            table.setUpdatesEnabled(True)

    def _current_patient(self) -> Optional[dict]:
        i = self.patient_table.selected_row()
        return self.patients[i] if 0 <= i < len(self.patients) else None

    def _patient_selected(self) -> None:
        self._show_patient(self._current_patient())

    def _show_patient(self, patient: Optional[dict]) -> None:
        if not patient:
            self.who.setText("No patient chosen")
            self.details.setText("Choose someone from the list on the left.")
            for value in self.figures.values():
                value.setText("—")
            self.job_table.set_rows([])
            self.file_table.set_rows([])
            self.folder_label.setText("")
            self.new_job_button.setEnabled(False)
            self.jobs, self.files, self.folder = [], [], None
            return

        self.new_job_button.setEnabled(True)
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

        self._show_figures(patient)
        self._load_files(patient)

    def _show_figures(self, patient: dict) -> None:
        money = q.patient_money(patient["id"])
        first = q.to_dt(self.jobs[-1]["received_at"]) if self.jobs else None
        last = q.to_dt(self.jobs[0]["received_at"]) if self.jobs else None
        shown = {
            "visits": str(len(self.jobs)),
            "first_seen": turnaround.format_date(first) if first else "—",
            "last_visit": turnaround.format_date(last) if last else "—",
            "billed": billing.format_rupees(money["billed_paise"]),
            "outstanding": billing.format_rupees(money["outstanding_paise"]),
        }
        for key, text in shown.items():
            widget = self.figures[key]
            widget.setText(text)
            # Money still owed is the one figure here that is a problem.
            alert = key == "outstanding" and money["outstanding_paise"] > 0
            widget.setProperty("alert", "true" if alert else "false")
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def _load_files(self, patient: dict) -> None:
        folder = config.patient_dir(patient["id"], patient["name"],
                                    patient.get("phone", ""))
        self.folder = folder
        self.folder_label.setText(str(folder))
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
                    datetime.fromtimestamp(stat.st_mtime))
            except OSError:
                size, when = "", ""
            rows.append([f.name, size, when])
        self.file_table.set_rows(rows)
        self.file_table.set_empty_text(
            "No reports saved yet.\n\nThey will appear in the folder above.")

    # --------------------------------------------------------------- actions
    def _selected_job(self) -> Optional[dict]:
        i = self.job_table.selected_row()
        return self.jobs[i] if 0 <= i < len(self.jobs) else None

    def _new_job(self) -> None:
        """Start a job for this patient, on the Job screen.

        Its own signal rather than a job id with a sign flipped: the shell
        should not have to decode what a negative number means.
        """
        p = self._current_patient()
        if p:
            self.new_job_for.emit(int(p["id"]))

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
