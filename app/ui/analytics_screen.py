"""The day book: what the laboratory took in today, counted not estimated.

Drawn in the canvas idiom -- a filter bar of figures over two plain lists,
square corners, one accent spent on the only number that is a problem. Every
value comes from ``queries.day_book``; nothing on this screen is a
percentage of another number on it.
"""

from __future__ import annotations

import csv
from datetime import date, datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QVBoxLayout, QWidget,
)

from ..core import billing
from ..db import queries as q
from .widgets import Table, button, info, label

#: caption, key, note, and whether a non-zero value is bad news.
CARDS = [
    ("Patients", "jobs", "registered today", False),
    ("Charged", "gross_paise", "before discount", False),
    ("Discount", "discount_paise", "given today", False),
    ("Net billed", "net_paise", "after discount", False),
    ("Collected", "collected_paise", "over the counter", False),
    ("Outstanding", "outstanding_paise", "still owed", True),
    ("Doctor commission", "commission_paise", "accrued today", False),
    ("Not billed", "unbilled", "jobs with no bill", True),
]


class AnalyticsScreen(QWidget):
    """The day book."""

    def __init__(self):
        super().__init__()
        self.data: dict = {}
        self._build()
        self.refresh()

    # ----------------------------------------------------------------- layout
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_bar())

        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(18, 16, 18, 16)
        body_lay.setSpacing(18)

        self.tests_table = Table(["Department", "Tests"], stretch_column=0,
                                 empty_text="Nothing registered today.")
        self.doctors_table = Table(["Referring doctor", "Jobs", "Commission"],
                                   stretch_column=0,
                                   empty_text="No referred work today.")
        body_lay.addWidget(self._titled("Busiest departments", self.tests_table), 1)
        body_lay.addWidget(self._titled("Referring doctors", self.doctors_table), 1)
        lay.addWidget(body, 1)

        foot = QWidget()
        foot.setObjectName("footBar")
        foot.setFixedHeight(40)
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(18, 0, 18, 0)
        self.as_of = label("", "foot")
        fl.addWidget(self.as_of)
        fl.addStretch(1)
        fl.addWidget(label("Collected counts money taken today, whichever day "
                           "the bill is from", "foot"))
        lay.addWidget(foot)

    def _build_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("filterBar")
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(9)
        title = label("Day book", "h1")
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(button("Refresh", "", self.refresh))
        head.addWidget(button("Export day sheet", "primary", self._export_csv))
        lay.addLayout(head)

        grid = QGridLayout()
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(12)
        self.values: dict = {}
        for i, (caption, key, note, _bad) in enumerate(CARDS):
            block = QFrame()
            block.setObjectName("statBlock")
            bl = QVBoxLayout(block)
            bl.setContentsMargins(12, 0, 0, 0)
            bl.setSpacing(0)
            bl.addWidget(label(caption, "statlabel"))
            line = QHBoxLayout()
            line.setContentsMargins(0, 0, 0, 0)
            line.setSpacing(7)
            value = label("—", "statvalue")
            line.addWidget(value)
            line.addWidget(label(note, "statnote"), 0, Qt.AlignmentFlag.AlignBottom)
            line.addStretch(1)
            bl.addLayout(line)
            self.values[key] = value
            grid.addWidget(block, i // 4, i % 4)
        lay.addLayout(grid)
        return bar

    @staticmethod
    def _titled(text: str, table) -> QWidget:
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(label(text, "field"))
        lay.addWidget(table, 1)
        return holder

    # ------------------------------------------------------------------- data
    def refresh(self) -> None:
        self.data = q.day_book(datetime.now())
        for caption, key, note, bad in CARDS:
            value = self.data.get(key, 0)
            text = (str(value) if key in ("jobs", "unbilled")
                    else billing.format_rupees(int(value)))
            widget = self.values[key]
            widget.setText(text)
            alert = bool(bad and value)
            widget.setProperty("alert", "true" if alert else "false")
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        self.tests_table.set_rows(
            [[t["name"] or "—", t["n"]] for t in self.data["tests"]])
        self.doctors_table.set_rows(
            [[d["name"], d["jobs"], billing.format_rupees(int(d["commission"]))]
             for d in self.data["doctors"]])
        self.as_of.setText(
            f"{self.data['date'].strftime('%d-%m-%Y')} · read at "
            f"{datetime.now().strftime('%H:%M')}")

    # ---------------------------------------------------------------- export
    def _export_csv(self) -> None:
        """One row per job, with the bill as it actually stands.

        Written from the same fields the screen shows, so the sheet handed to
        the accountant and the screen the operator read cannot disagree.
        """
        jobs = q.list_jobs(scope="today")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export day sheet", f"LabSoft day book {date.today()}.csv",
            "CSV files (*.csv)")
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Report no", "Patient", "Mobile", "Doctor",
                             "Charged", "Discount", "Net", "Paid", "Outstanding",
                             "Status"])
            for j in jobs:
                bill = q.get_bill(j["id"]) or {}
                net = int(bill.get("net_paise") or 0)
                paid = sum(int(p["amount_paise"])
                           for p in q.bill_payments(int(bill["id"]))) if bill else 0
                writer.writerow([
                    j.get("report_no", ""),
                    j.get("patient_name", ""),
                    j.get("patient_phone", ""),
                    j.get("referrer_name", ""),
                    f"{int(bill.get('gross_paise') or 0) / 100:.2f}",
                    f"{int(bill.get('discount_paise') or 0) / 100:.2f}",
                    f"{net / 100:.2f}",
                    f"{paid / 100:.2f}",
                    f"{max(0, net - paid) / 100:.2f}",
                    j.get("status", ""),
                ])
        info(self, "Day sheet saved", f"Written to:\n{path}")
