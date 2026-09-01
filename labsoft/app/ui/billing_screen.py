"""The billing ledger: charged, paid, outstanding, and commission owed."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QCheckBox, QComboBox, QDateEdit, QFileDialog, QVBoxLayout, QWidget

from .. import config
from ..core import billing
from ..db import queries as q
from ..output import excel
from . import style
from .widgets import (
    SearchBox, Table, button, field_label, info, label, row, warn,
)


class BillingScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: List[dict] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 10)
        lay.setSpacing(10)

        self.from_date = QDateEdit(QDate.currentDate().addDays(-30))
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("dd-MM-yyyy")
        self.to_date = QDateEdit(QDate.currentDate())
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("dd-MM-yyyy")
        self.from_date.dateChanged.connect(lambda _d: self.refresh())
        self.to_date.dateChanged.connect(lambda _d: self.refresh())

        self.referrer_combo = QComboBox()
        self.referrer_combo.currentIndexChanged.connect(lambda _i: self.refresh())
        self.unpaid_check = QCheckBox("Unpaid only")
        self.unpaid_check.stateChanged.connect(lambda _s: self.refresh())

        self.search = SearchBox("Search by patient, mobile, report number or doctor…")
        self.search.searched.connect(lambda _t: self.refresh())
        lay.addWidget(self.search)

        lay.addWidget(row(field_label("From"), self.from_date,
                          field_label("To"), self.to_date,
                          field_label("Doctor"), self.referrer_combo,
                          self.unpaid_check, None,
                          button("This month", "quiet", self._this_month),
                          button("Today", "quiet", self._today)))

        self.table = Table(["Report No", "Date", "Patient", "Referred by", "Charged",
                            "Discount", "Net", "Paid", "Balance", "Commission"],
                           stretch_column=2)
        self.table.doubleClicked.connect(self._open_bill)
        lay.addWidget(self.table, 1)

        self.totals = label("", "")
        self.totals.setStyleSheet("font-size: 11pt; font-weight: 700;")
        lay.addWidget(row(button("Open bill", "primary", self._open_bill),
                          button("Print bill…", "", self._print_bill),
                          button("Export to Excel", "", self._export),
                          None, self.totals))

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
        current = self.referrer_combo.currentData()
        if self.referrer_combo.count() == 0:
            self.referrer_combo.addItem("All", None)
            for r in q.list_referrers():
                self.referrer_combo.addItem(r["name"], r["id"])

        self.rows = q.ledger(
            date_from=self.from_date.date().toPyDate(),
            date_to=self.to_date.date().toPyDate(),
            unpaid_only=self.unpaid_check.isChecked(),
            referrer_id=current,
        )
        self.rows = self._matching(self.rows)

        display, colours = [], {}
        for i, r in enumerate(self.rows):
            display.append([
                r["report_no"],
                (q.to_dt(r["received_at"]) or datetime.now()).strftime("%d-%m-%Y"),
                r["patient_name"], r.get("referrer_name") or "",
                billing.format_rupees(r["gross_paise"], symbol=False),
                billing.format_rupees(r["discount_paise"], symbol=False),
                billing.format_rupees(r["net_paise"], symbol=False),
                billing.format_rupees(r["paid_paise"], symbol=False),
                billing.format_rupees(r["balance_paise"], symbol=False),
                billing.format_rupees(r["commission_paise"], symbol=False),
            ])
            if r["balance_paise"] > 0:
                colours[i] = QColor(style.AMBER)
        self.table.set_rows(display, colours)

        net = sum(r["net_paise"] for r in self.rows)
        paid = sum(r["paid_paise"] for r in self.rows)
        due = sum(r["balance_paise"] for r in self.rows if r["balance_paise"] > 0)
        comm = sum(r["commission_paise"] for r in self.rows)
        self.totals.setText(
            f"Billed {billing.format_rupees(net)}      "
            f"Collected {billing.format_rupees(paid)}      "
            f"Outstanding {billing.format_rupees(due)}      "
            f"Commission {billing.format_rupees(comm)}")
        self.totals.setStyleSheet(
            "font-size: 11pt; font-weight: 700; "
            + (f"color: {style.AMBER};" if due else f"color: {style.GREEN};"))

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
