"""Day and month summaries."""

from __future__ import annotations

from datetime import datetime
from typing import List

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QComboBox, QDateEdit, QFileDialog, QSpinBox, QVBoxLayout, QWidget

from .. import config
from ..core import billing
from ..db import queries as q
from ..output import excel
from . import style
from .widgets import Table, button, field_label, info, label, row, warn


class SummariesScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self.refresh()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 10)
        lay.setSpacing(10)

        self.mode = QComboBox()
        self.mode.addItems(["Day sheet", "Month sheet"])
        self.mode.currentIndexChanged.connect(lambda _i: self.refresh())

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd-MM-yyyy")
        self.date_edit.dateChanged.connect(lambda _d: self.refresh())

        lay.addWidget(row(self.mode, self.date_edit, None,
                          button("Export", "", self._export)))

        self.headline = label("", "h1")
        lay.addWidget(self.headline)

        self.detail = label("", "hint")
        lay.addWidget(self.detail)

        self.table = Table(["", "", "", ""], stretch_column=0)
        lay.addWidget(self.table, 1)

        self.second_title = label("", "")
        self.second_title.setStyleSheet("font-weight: 700;")
        lay.addWidget(self.second_title)
        self.second_table = Table(["", "", ""], stretch_column=0)
        lay.addWidget(self.second_table, 1)

    # ------------------------------------------------------------------ data
    def refresh(self) -> None:
        day = self.date_edit.date().toPyDate()
        if self.mode.currentIndex() == 0:
            self._show_day(datetime(day.year, day.month, day.day))
        else:
            self._show_month(day.year, day.month)

    def _show_day(self, when: datetime) -> None:
        s = q.day_summary(when)
        self.headline.setText(when.strftime("Day sheet — %d %B %Y"))
        self.detail.setText(
            f"{s['jobs']} patients registered     {s['sent']} reports sent     "
            f"{s['pending']} still pending")
        self.table.setHorizontalHeaderLabels(["Test", "Count", "", ""])
        self.table.set_rows([[t["name"], t["n"], "", ""] for t in s["tests"]])
        self.second_title.setText(
            f"Billed {billing.format_rupees(s['billed_paise'])}          "
            f"Collected {billing.format_rupees(s['collected_paise'])}")
        self.second_table.setHorizontalHeaderLabels(["", "", ""])
        self.second_table.set_rows([])
        self.current = ("day", s)

    def _show_month(self, year: int, month: int) -> None:
        s = q.month_summary(year, month)
        self.headline.setText(datetime(year, month, 1).strftime("Month sheet — %B %Y"))
        self.detail.setText(
            f"{s['jobs']} patients     "
            f"Billed {billing.format_rupees(s['billed_paise'])}     "
            f"Collected {billing.format_rupees(s['collected_paise'])}")
        self.table.setHorizontalHeaderLabels(["Date", "Patients", "Billed", ""])
        self.table.set_rows([
            [r["d"], r["jobs"], billing.format_rupees(r["billed"], symbol=False), ""]
            for r in s["by_day"]])
        self.second_title.setText("Commission by referring doctor")
        self.second_table.setHorizontalHeaderLabels(["Doctor", "Jobs", "Commission"])
        self.second_table.set_rows([
            [r["name"], r["jobs"], billing.format_rupees(r["commission"])]
            for r in s["referrers"]])
        self.current = ("month", s)

    # ---------------------------------------------------------------- export
    def _export(self) -> None:
        kind, s = getattr(self, "current", (None, None))
        if not kind:
            return
        if kind == "day":
            default = config.exports_dir() / f"day_{s['date']:%Y-%m-%d}.xlsx"
            headers = ["Test", "Count"]
            rows = [[t["name"], t["n"]] for t in s["tests"]]
        else:
            default = config.exports_dir() / f"month_{s['year']}-{s['month']:02d}.xlsx"
            headers = ["Date", "Patients", "Billed ₹"]
            rows = [[r["d"], r["jobs"], billing.to_rupees(r["billed"])]
                    for r in s["by_day"]]
        if not rows:
            warn(self, "Nothing to export", "There is no activity in this period.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export summary", str(default), "Excel (*.xlsx);;CSV (*.csv)")
        if not path:
            return
        written = excel.write_sheet(path, headers, rows, "Summary")
        info(self, "Exported", f"Written to:\n{written}")
