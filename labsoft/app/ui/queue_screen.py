"""The work queue: what is in the lab and what each job is waiting for."""

from __future__ import annotations

from typing import Dict, List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..core import billing, turnaround
from ..db import queries as q
from . import style
from .widgets import SearchBox, Table, button, confirm, info, label, row, warn

HEADERS = ["Report No", "Patient", "Tests", "Received", "Due", "Progress",
           "Status", "Payment"]


class QueueScreen(QWidget):
    open_job = pyqtSignal(int)
    send_job = pyqtSignal(int)
    preview_job = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scope = "today"
        self.rows: List[dict] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 10)
        lay.setSpacing(10)

        self.search = SearchBox("Search name, mobile or report number…")
        self.search.searched.connect(lambda _t: self.refresh())

        self.scope_buttons: Dict[str, object] = {}
        bar = QWidget()
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(0, 0, 0, 0)
        bar_lay.setSpacing(6)
        bar_lay.addWidget(self.search, 1)
        for key, text in (("today", "Today"), ("pending", "Pending"),
                          ("overdue", "Overdue"), ("ready", "Ready to send"),
                          ("unpaid", "Unpaid"), ("all", "All")):
            b = button(text)
            b.setCheckable(True)
            b.clicked.connect(lambda _c=False, k=key: self._set_scope(k))
            self.scope_buttons[key] = b
            bar_lay.addWidget(b)
        self.scope_buttons["today"].setChecked(True)
        lay.addWidget(bar)

        self.table = Table(HEADERS, stretch_column=1,
                           empty_text="Nothing here yet.")
        self.table.doubleClicked.connect(self._open_selected)
        lay.addWidget(self.table, 1)

        self.open_button = button("Open", "primary", self._open_selected)
        self.preview_button = button("Preview", "", self._preview_selected)
        self.send_button = button("Send / reprint", "", self._send_selected)
        self.revise_button = button("Correct && reissue", "", self._revise_selected)
        self.delete_button = button("Delete", "danger", self._delete_selected)
        self.counts = label("", "hint")
        lay.addWidget(row(self.open_button, self.preview_button,
                          self.send_button, self.revise_button,
                          None, self.delete_button, 12, self.counts))

    # ------------------------------------------------------------------ data
    def _set_scope(self, scope: str) -> None:
        self.scope = scope
        for key, b in self.scope_buttons.items():
            b.setChecked(key == scope)
        self.refresh()

    def refresh(self) -> None:
        term = self.search.text().strip()
        self.rows = q.list_jobs(self.scope, term)

        display = []
        colours = {}
        for i, j in enumerate(self.rows):
            due = q.to_dt(j["due_at"])
            late = turnaround.is_overdue(due, j["status"])
            due_text = ""
            if due:
                due_text = f"{turnaround.format_dt(due)}  ({turnaround.humanise_delta(due)})"

            paid = int(j.get("paid_paise") or 0)
            net = j.get("net_paise")
            if net is None:
                payment = "—"
            elif int(net) - paid <= 0:
                payment = "Paid"
            else:
                payment = f"{billing.format_rupees(int(net) - paid)} due"

            names = j["test_names"] or ""
            if len(names) > 58:
                names = names[:57].rstrip(", ") + "…"

            display.append([
                j["report_no"],
                f"{j['patient_name']}   ·   {j['patient_phone'] or ''}".strip(" ·"),
                names,
                turnaround.format_dt(q.to_dt(j["received_at"])),
                due_text,
                f"{j['n_done']}/{j['n_tests']}",
                turnaround.status_label(j["status"]),
                payment,
            ])
            if late:
                colours[i] = QColor(style.RED)
            elif j["status"] == turnaround.STATUS_READY:
                colours[i] = QColor(style.GREEN)

        self.table.set_rows(display, colours)
        self.table.set_empty_text(self._empty_message(term))

        c = q.queue_counts()
        parts = [f"Today {c['today']}", f"Pending {c['pending']}",
                 f"Ready {c['ready']}"]
        if c["overdue"]:
            parts.append(f"Overdue {c['overdue']}")
        self.counts.setText("     ".join(parts))
        self.counts.setStyleSheet(
            f"color: {style.RED}; font-weight: 600;" if c["overdue"] else "")

    def _empty_message(self, term: str) -> str:
        """Say why the list is empty and what to do, not just show nothing."""
        if term:
            return (f"No job matches \u201c{term}\u201d.\n\n"
                    "Search by patient name, mobile number, or report number.")
        return {
            "today": "No patients registered today.\n\n"
                     "Press F2 to start the first one.",
            "pending": "No results are waiting.\n\nEverything registered has "
                       "been entered.",
            "overdue": "Nothing is overdue. ",
            "ready": "No reports are waiting to be sent.",
            "unpaid": "No unpaid bills.",
            "all": "No jobs recorded yet.\n\nPress F2 to register the first "
                   "patient.",
        }.get(self.scope, "Nothing here yet.")

    # --------------------------------------------------------------- actions
    def _selected(self) -> dict | None:
        i = self.table.selected_row()
        if i < 0 or i >= len(self.rows):
            return None
        return self.rows[i]

    def _open_selected(self) -> None:
        j = self._selected()
        if j:
            self.open_job.emit(j["id"])

    def _preview_selected(self) -> None:
        j = self._selected()
        if j:
            self.preview_job.emit(j['id'])

    def _send_selected(self) -> None:
        j = self._selected()
        if not j:
            return
        if j["n_tests"] and j["n_done"] < j["n_tests"]:
            warn(self, "Some tests are still empty",
                 "This job cannot be sent yet, because some tests have no "
                 "result.\n\nClick Open and fill them in.")
            return
        self.send_job.emit(j["id"])

    def _revise_selected(self) -> None:
        j = self._selected()
        if not j:
            return
        if not confirm(
                self, "Correct and reissue this report?",
                f"Report {j['report_no']} will be reissued as revision "
                f"{int(j['revision_no'] or 1) + 1}.\n\n"
                "The original stays exactly as it was sent, and both versions are "
                "kept. Continue?",
                "Correct & reissue"):
            return
        from .. import services

        new_id = services.create_revision(j["id"])
        self.refresh()
        self.open_job.emit(new_id)

    def _delete_selected(self) -> None:
        j = self._selected()
        if not j:
            return
        if j["status"] == turnaround.STATUS_SENT:
            warn(self, "Already sent",
                 "This report has been sent to the patient, so it cannot be "
                 "deleted.\n\nIf a result is wrong, use \u201cCorrect & reissue\u201d "
                 "instead. The patient gets a corrected copy and both "
                 "versions are kept.")
            return
        if not confirm(self, "Delete this job?",
                       f"Job {j['report_no']} for {j['patient_name']} and all its "
                       f"results will be removed. This cannot be undone.",
                       "Delete"):
            return
        q.delete_job(j["id"])
        self.refresh()
