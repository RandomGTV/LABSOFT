"""The billing ledger: charged, paid, outstanding, and commission owed.

Same shape as the work queue -- a filter bar carrying the figures that
describe the range you are looking at, the ledger itself, and a foot bar with
what you can do to the line you have chosen.

Money columns are right-aligned. A column of rupees that starts at the same
left edge cannot be read down; one that ends at the same right edge can.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QFileDialog, QFrame, QHBoxLayout,
    QVBoxLayout, QWidget,
)

from .. import config
from ..core import billing
from ..db import queries as q
from ..output import excel
from . import style
from .widgets import (
    SearchBox, Table, button, field_label, gutter, info, label, warn,
)

HEADERS = ["Report no", "Date", "Patient", "Referred by", "Charged",
           "Discount", "Net", "Paid", "Balance", "Commission"]

#: the columns that hold money, and therefore line up on the right
MONEY = (4, 5, 6, 7, 8, 9)

ROW_H = 48

#: caption, key, and whether a non-zero value is bad news.
FIGURES = [
    ("Billed", "net", False),
    ("Collected", "paid", False),
    ("Outstanding", "due", True),
    ("Commission", "commission", False),
]


class BillingScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: List[dict] = []
        self._build()
        self.refresh()

    # ----------------------------------------------------------------- build
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_filter_bar())

        self.table = Table(HEADERS, stretch_column=2,
                           empty_text="No bills in this date range.")
        self.table.setObjectName("boardTable")
        self.table.verticalHeader().setDefaultSectionSize(ROW_H)
        self.table.doubleClicked.connect(self._open_bill)
        for column, width in ((0, 108), (1, 120), (3, 168), (4, 112), (5, 112),
                              (6, 112), (7, 112), (8, 124), (9, 126)):
            self.table.setColumnWidth(column, width)
        for column in MONEY:
            item = self.table.horizontalHeaderItem(column)
            if item is not None:
                item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight
                                          | Qt.AlignmentFlag.AlignVCenter))
        lay.addWidget(gutter(self.table), 1)
        lay.addWidget(self._build_foot())

    def _build_filter_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("filterBar")
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(12)

        self.from_date = QDateEdit(QDate.currentDate().addDays(-30))
        self.to_date = QDateEdit(QDate.currentDate())
        for edit in (self.from_date, self.to_date):
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("dd-MM-yyyy")
            edit.dateChanged.connect(self._dates_changed)

        self.referrer_combo = QComboBox()
        self.referrer_combo.setMinimumWidth(180)
        self.referrer_combo.currentIndexChanged.connect(lambda _i: self.refresh())
        self.unpaid_check = QCheckBox("Unpaid only")
        self.unpaid_check.stateChanged.connect(lambda _s: self.refresh())

        self.search = SearchBox("Patient, mobile, report number or doctor…")
        self.search.searched.connect(lambda _t: self.refresh())
        self.search.setFixedWidth(300)
        self.search.setFixedHeight(34)

        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(self.search)
        top.addWidget(field_label("From"))
        top.addWidget(self.from_date)
        top.addWidget(field_label("To"))
        top.addWidget(self.to_date)
        # Chips, not links. Picking a period is the same act here as it is on
        # the Work Queue, so it wears the same control: two underlined words
        # in a row of fields read as help text, and neither of them showed
        # which period was actually in force.
        self.period_buttons = {}
        period_strip = QWidget()
        period_strip.setObjectName("periodStrip")
        ps = QHBoxLayout(period_strip)
        ps.setContentsMargins(0, 0, 0, 0)
        ps.setSpacing(4)
        for key, text, handler in (("today", "Today", self._today),
                                   ("month", "This month", self._this_month)):
            b = button(text)
            b.setCheckable(True)
            b.setFixedHeight(30)
            b.clicked.connect(lambda _c=False, h=handler, k=key: self._set_period(k, h))
            self.period_buttons[key] = b
            ps.addWidget(b)
        top.addWidget(period_strip)
        top.addWidget(field_label("Doctor"))
        top.addWidget(self.referrer_combo)
        top.addWidget(self.unpaid_check)
        top.addStretch(1)
        lay.addLayout(top)

        figures = QHBoxLayout()
        figures.setContentsMargins(0, 0, 0, 0)
        figures.setSpacing(28)
        self.figures = {}
        for caption, key, _bad in FIGURES:
            block = QFrame()
            block.setObjectName("statBlock")
            bl = QVBoxLayout(block)
            bl.setContentsMargins(12, 0, 0, 0)
            bl.setSpacing(0)
            bl.addWidget(label(caption, "statlabel"))
            value = label("—", "statvalue")
            self.figures[key] = value
            bl.addWidget(value)
            figures.addWidget(block)
        figures.addStretch(1)
        lay.addLayout(figures)
        return bar

    def _build_foot(self) -> QWidget:
        foot = QFrame()
        foot.setObjectName("footBar")
        foot.setFixedHeight(60)
        lay = QHBoxLayout(foot)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(9)
        self.count_label = label("", "foot")
        lay.addWidget(self.count_label)
        lay.addStretch(1)
        lay.addWidget(button("Export to Excel", "", self._export))
        lay.addWidget(button("Print bill…", "", self._print_bill))
        lay.addWidget(button("Open bill", "primary", self._open_bill))
        return foot

    def _matching(self, rows: List[dict]) -> List[dict]:
        """Narrow the ledger to what was searched for.

        Filtered here rather than in SQL because the ledger is already in hand
        and a lab's month of bills is small — and because it lets one box match
        a name, a mobile number, a report number or a doctor at once, which is
        how someone at the counter actually asks for a bill.
        """
        term = self.search.text().strip().lower()
        if not term:
            return rows
        digits = "".join(ch for ch in term if ch.isdigit())
        out = []
        for r in rows:
            hay = " ".join(str(r.get(k) or "").lower() for k in
                           ("patient_name", "referrer_name", "report_no",
                            "patient_phone"))
            phone = "".join(ch for ch in str(r.get("patient_phone") or "")
                            if ch.isdigit())
            if term in hay or (digits and len(digits) >= 3 and digits in phone):
                out.append(r)
        return out

    # ------------------------------------------------------------------ data
    def refresh(self) -> None:
        # Rebuilt every refresh. It was filled only when empty, so a doctor
        # added on the Doctors tab could not be filtered on until LabSoft was
        # restarted -- and their commission could not be looked up at all.
        current = self.referrer_combo.currentData()
        self.referrer_combo.blockSignals(True)
        self.referrer_combo.clear()
        self.referrer_combo.addItem("All", None)
        for r in q.list_referrers():
            self.referrer_combo.addItem(r["name"], r["id"])
        at = self.referrer_combo.findData(current)
        self.referrer_combo.setCurrentIndex(at if at >= 0 else 0)
        self.referrer_combo.blockSignals(False)

        self.rows = q.ledger(
            date_from=self.from_date.date().toPyDate(),
            date_to=self.to_date.date().toPyDate(),
            unpaid_only=self.unpaid_check.isChecked(),
            referrer_id=current,
        )
        self.rows = self._matching(self.rows)

        display, colours, cells = [], {}, {}
        for i, r in enumerate(self.rows):
            # A job with no bill has not been charged zero -- it has not been
            # charged at all. Printing 0.00 across the row says the first,
            # and hides the jobs that still need a bill.
            billed = r.get("bill_id") is not None

            def money(key: str) -> str:
                return (billing.format_rupees(r[key], symbol=False)
                        if billed else "—")

            display.append([
                r["report_no"],
                (q.to_dt(r["received_at"]) or datetime.now()).strftime("%d-%m-%Y"),
                r["patient_name"], r.get("referrer_name") or "—",
                money("gross_paise"), money("discount_paise"), money("net_paise"),
                money("paid_paise"), money("balance_paise"),
                money("commission_paise"),
            ])
            if not billed:
                colours[i] = QColor(style.INK3)
            elif r["balance_paise"] > 0:
                # Only the balance is a problem. The charge and the discount
                # beside it are just facts.
                cells[(i, 8)] = QColor(style.ALERT)
        self.table.set_rows(
            display, colours,
            align={c: Qt.AlignmentFlag.AlignRight for c in MONEY},
            cell_colours=cells)

        self._refresh_figures()

    def _refresh_figures(self) -> None:
        totals = {
            "net": sum(r["net_paise"] for r in self.rows),
            "paid": sum(r["paid_paise"] for r in self.rows),
            "due": sum(r["balance_paise"] for r in self.rows
                       if r["balance_paise"] > 0),
            "commission": sum(r["commission_paise"] for r in self.rows),
        }
        for _caption, key, bad in FIGURES:
            widget = self.figures[key]
            widget.setText(billing.format_rupees(totals[key]))
            alert = bool(bad and totals[key])
            widget.setProperty("alert", "true" if alert else "false")
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        # Counted separately, because "10 bills" over a list where six of the
        # lines have no bill on them is not true.
        billed = [r for r in self.rows if r.get("bill_id") is not None]
        unpaid = sum(1 for r in billed if r["balance_paise"] > 0)
        unbilled = len(self.rows) - len(billed)

        parts = [f"{len(billed)} bill{'s' if len(billed) != 1 else ''}"]
        if unpaid:
            parts.append(f"{unpaid} not settled")
        if unbilled:
            parts.append(f"{unbilled} job{'s' if unbilled != 1 else ''} "
                         f"with no bill yet")
        self.count_label.setText(" · ".join(parts))

    def _set_period(self, key: str, handler) -> None:
        """Light the chip that was pressed, and put the dates where it says."""
        self._setting_period = True
        try:
            handler()
        finally:
            self._setting_period = False
        for name, chip in self.period_buttons.items():
            chip.setChecked(name == key)
        self.refresh()

    def _dates_changed(self, _date=None) -> None:
        """A date typed by hand belongs to no chip, so no chip stays lit."""
        if not getattr(self, "_setting_period", False):
            for chip in getattr(self, "period_buttons", {}).values():
                chip.setChecked(False)
            self.refresh()

    def _this_month(self) -> None:
        today = QDate.currentDate()
        self.from_date.setDate(QDate(today.year(), today.month(), 1))
        self.to_date.setDate(today)

    def _today(self) -> None:
        today = QDate.currentDate()
        self.from_date.setDate(today)
        self.to_date.setDate(today)

    # --------------------------------------------------------------- actions
    def _selected(self) -> Optional[dict]:
        i = self.table.selected_row()
        return self.rows[i] if 0 <= i < len(self.rows) else None

    def _open_bill(self) -> None:
        r = self._selected()
        if not r:
            warn(self, "Nothing chosen", "Pick a line in the list first.")
            return
        from .bill_dialog import BillDialog

        BillDialog(r["job_id"], self).exec()
        self.refresh()

    def _print_bill(self) -> None:
        """Reprint a bill from the ledger — the usual reason being that the
        patient has lost theirs and needs it for a claim."""
        r = self._selected()
        if not r:
            warn(self, "Nothing chosen", "Pick a line in the list first.")
            return
        from .bill_preview import BillPreviewDialog

        BillPreviewDialog(r["job_id"], self).exec()

    def _export(self) -> None:
        if not self.rows:
            warn(self, "Nothing to export", "There are no entries in this date range.")
            return
        default = config.exports_dir() / f"ledger_{datetime.now():%Y-%m-%d}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export ledger", str(default), "Excel (*.xlsx);;CSV (*.csv)")
        if not path:
            return
        written = excel.export_ledger(path, self.rows)
        info(self, "Exported", f"Written to:\n{written}")
