"""Day and month summaries — what the laboratory did over a period.

Same shape as the rest: a filter bar carrying the figures for whatever period
is chosen, two lists under it, and the export in the foot bar.

Distinct from the Day Book, which answers "what is in the drawer today". This
one answers "what did we do", and can look back at any day or month.
"""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QComboBox, QDateEdit, QFileDialog, QFrame, QHBoxLayout, QVBoxLayout, QWidget,
)

from .. import config
from ..core import billing
from ..db import queries as q
from ..output import excel
from .widgets import Table, button, field_label, info, label, warn

#: caption and key, for each of the two modes
DAY_FIGURES = [("Patients", "jobs"), ("Reports sent", "sent"),
               ("Still pending", "pending"), ("Billed", "billed"),
               ("Collected", "collected")]
MONTH_FIGURES = [("Patients", "jobs"), ("Days with work", "days"),
                 ("Billed", "billed"), ("Collected", "collected"),
                 ("Commission", "commission")]


class SummariesScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current = (None, None)
        self._build()
        self.refresh()

    # ----------------------------------------------------------------- build
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_filter_bar())

        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(24, 20, 24, 16)
        body_lay.setSpacing(18)

        self.table = Table(["Test", "Count"], stretch_column=0,
                           empty_text="Nothing recorded for this period.")
        self.second_table = Table(["Doctor", "Jobs", "Commission"],
                                  stretch_column=0,
                                  empty_text="No referred work in this period.")
        self.first_title = field_label("Tests done")
        self.second_title = field_label("Referring doctors")
        body_lay.addWidget(self._titled(self.first_title, self.table), 1)
        body_lay.addWidget(self._titled(self.second_title, self.second_table), 1)
        lay.addWidget(body, 1)

        foot = QFrame()
        foot.setObjectName("footBar")
        foot.setFixedHeight(60)
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(24, 0, 24, 0)
        fl.setSpacing(9)
        self.detail = label("", "foot")
        fl.addWidget(self.detail)
        fl.addStretch(1)
        fl.addWidget(button("Export", "primary", self._export))
        lay.addWidget(foot)

    def _build_filter_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("filterBar")
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(26, 22, 26, 20)
        lay.setSpacing(12)

        self.mode = QComboBox()
        self.mode.addItems(["Day sheet", "Month sheet"])
        self.mode.setFixedWidth(160)
        self.mode.currentIndexChanged.connect(lambda _i: self.refresh())

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd-MM-yyyy")
        self.date_edit.dateChanged.connect(lambda _d: self.refresh())

        top = QHBoxLayout()
        top.setSpacing(10)
        self.headline = label("", "h1")
        top.addWidget(self.headline)
        top.addStretch(1)
        top.addWidget(self.mode)
        top.addWidget(self.date_edit)
        lay.addLayout(top)

        figures = QHBoxLayout()
        figures.setContentsMargins(0, 0, 0, 0)
        figures.setSpacing(28)
        self.figures = {}
        # Five blocks, built once and relabelled when the mode changes.
        # Making and destroying them on every switch is how a screen ends up
        # with widgets nobody can see that Qt is still laying out.
        for slot in range(5):
            block = QFrame()
            block.setObjectName("statBlock")
            bl = QVBoxLayout(block)
            bl.setContentsMargins(12, 0, 0, 0)
            bl.setSpacing(0)
            caption = label("", "statlabel")
            value = label("—", "statvalue")
            bl.addWidget(caption)
            bl.addWidget(value)
            self.figures[slot] = (block, caption, value)
            figures.addWidget(block)
        figures.addStretch(1)
        lay.addLayout(figures)
        return bar

    @staticmethod
    def _titled(title, table) -> QWidget:
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(title)
        lay.addWidget(table, 1)
        return holder

    def _show_figures(self, spec, values: dict) -> None:
        for slot, (block, caption, value) in self.figures.items():
            if slot < len(spec):
                name, key = spec[slot]
                caption.setText(name)
                value.setText(values[key])
                block.show()
            else:
                block.hide()

    # ------------------------------------------------------------------ data
    def refresh(self) -> None:
        day = self.date_edit.date().toPyDate()
        if self.mode.currentIndex() == 0:
            self._show_day(datetime(day.year, day.month, day.day))
        else:
            self._show_month(day.year, day.month)

    def _show_day(self, when: datetime) -> None:
        s = q.day_summary(when)
        self.headline.setText(when.strftime("Day sheet · %d %B %Y"))
        self._show_figures(DAY_FIGURES, {
            "jobs": str(s["jobs"]),
            "sent": str(s["sent"]),
            "pending": str(s["pending"]),
            "billed": billing.format_rupees(s["billed_paise"]),
            "collected": billing.format_rupees(s["collected_paise"]),
        })

        self.first_title.setText("Tests done")
        self.table.setHorizontalHeaderLabels(["Test", "Count"])
        self.table.set_rows([[t["name"], t["n"]] for t in s["tests"]])

        # A single day has no by-doctor breakdown worth a grid of its own, so
        # the second list stands down and says where to find it, rather than
        # showing an empty table with headings over nothing.
        self.second_title.setText("Referring doctors")
        self.second_table.setHorizontalHeaderLabels(["Doctor", "Jobs", "Commission"])
        self.second_table.set_rows([])
        self.second_table.set_empty_text(
            "Commission is summarised by month.\n\n"
            "Switch to the month sheet to see it.")
        self.detail.setText(when.strftime("Day sheet for %d-%m-%Y"))
        self.current = ("day", s)

    def _show_month(self, year: int, month: int) -> None:
        s = q.month_summary(year, month)
        commission = sum(int(r["commission"]) for r in s["referrers"])
        self.headline.setText(datetime(year, month, 1).strftime("Month sheet · %B %Y"))
        self._show_figures(MONTH_FIGURES, {
            "jobs": str(s["jobs"]),
            "days": str(len(s["by_day"])),
            "billed": billing.format_rupees(s["billed_paise"]),
            "collected": billing.format_rupees(s["collected_paise"]),
            "commission": billing.format_rupees(commission),
        })

        self.first_title.setText("By day")
        self.table.setHorizontalHeaderLabels(["Date", "Patients", "Billed"])
        self.table.set_rows([
            [r["d"], r["jobs"], billing.format_rupees(r["billed"], symbol=False)]
            for r in s["by_day"]])

        self.second_title.setText("Commission by referring doctor")
        self.second_table.setHorizontalHeaderLabels(["Doctor", "Jobs", "Commission"])
        self.second_table.set_rows([
            [r["name"], r["jobs"], billing.format_rupees(r["commission"])]
            for r in s["referrers"]])
        self.second_table.set_empty_text("No referred work in this month.")
        self.detail.setText(
            datetime(year, month, 1).strftime("Month sheet for %B %Y"))
        self.current = ("month", s)

    # ---------------------------------------------------------------- export
    def _export(self) -> None:
        kind, s = self.current
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
