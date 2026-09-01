"""Optional billing for one job. Never blocks a report."""

from __future__ import annotations

from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QHeaderView, QLineEdit, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from .. import services
from ..core import billing
from ..db import queries as q
from . import style
from .widgets import Table, button, confirm, field_label, info, label, row, warn


class BillDialog(QDialog):
    def __init__(self, job_id: int, parent=None):
        super().__init__(parent)
        self.job_id = job_id
        self.job = q.get_job(job_id)
        self.items: List[dict] = []

        self.setWindowTitle(f"Bill — Report {self.job['report_no']}")
        self.resize(640, 560)
        self._build()
        self._load()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(9)

        lay.addWidget(label(f"{self.job['patient_name']}", "h1"))

        lay.addWidget(field_label("Charges"))
        self.items_table = QTableWidget(0, 3)
        self.items_table.setHorizontalHeaderLabels(["Item", "Rate ₹", "Qty"])
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.items_table.itemChanged.connect(lambda _i: self._recalc())
        lay.addWidget(self.items_table, 1)

        self.discount_type = QComboBox()
        self.discount_type.addItems(["Percent %", "Flat ₹"])
        self.discount_type.currentIndexChanged.connect(self._recalc)
        self.discount_value = QDoubleSpinBox()
        self.discount_value.setRange(0, 999999)
        self.discount_value.setDecimals(2)
        self.discount_value.valueChanged.connect(lambda _v: self._recalc())
        lay.addWidget(row(field_label("Discount"), self.discount_type,
                          self.discount_value, None))

        self.totals_label = label("", "")
        self.totals_label.setStyleSheet("font-size: 12pt; font-weight: 700;")
        lay.addWidget(self.totals_label)

        lay.addWidget(field_label("Payments"))
        self.payments_table = Table(["Amount", "Mode", "When"], stretch_column=2)
        self.payments_table.setMaximumHeight(140)
        lay.addWidget(self.payments_table)

        self.pay_amount = QDoubleSpinBox()
        self.pay_amount.setRange(0, 9999999)
        self.pay_amount.setDecimals(2)
        self.pay_amount.setPrefix("₹ ")
        self.pay_mode = QComboBox()
        self.pay_mode.addItems(["cash", "upi", "card", "other"])
        lay.addWidget(row(self.pay_amount, self.pay_mode,
                          button("Add payment", "", self._add_payment),
                          button("Remove selected", "quiet", self._remove_payment), None))

        lay.addWidget(row(button("🖨️ Print A4 Invoice", "primary", self._print_a4),
                          button("🧾 Print 80mm POS Slip", "", self._print_pos),
                          None, button("Close", "", self.reject),
                          button("Save bill", "", self._save)))

    # ------------------------------------------------------------------ data
    def _load(self) -> None:
        bill = q.get_bill(self.job_id)
        if bill:
            self.items = [
                {"label": i["label"], "rate_paise": i["rate_paise"], "qty": i["qty"],
                 "test_id": i["test_id"], "panel_id": i["panel_id"]}
                for i in q.bill_items(bill["id"])
            ]
            self.discount_type.setCurrentIndex(
                0 if bill["discount_type"] == billing.DISCOUNT_PERCENT else 1)
            self.discount_value.setValue(float(bill["discount_value"] or 0))
        else:
            self.items = services.suggest_bill_items(self.job_id)

        self.items_table.blockSignals(True)
        self.items_table.setRowCount(len(self.items))
        for r, it in enumerate(self.items):
            name = QTableWidgetItem(it["label"])
            name.setFlags(name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.items_table.setItem(r, 0, name)
            self.items_table.setItem(
                r, 1, QTableWidgetItem(f"{billing.to_rupees(it['rate_paise']):.2f}"))
            self.items_table.setItem(r, 2, QTableWidgetItem(str(it.get("qty", 1))))
        self.items_table.blockSignals(False)

        self._load_payments()
        self._recalc()

    def _load_payments(self) -> None:
        bill = q.get_bill(self.job_id)
        self.payment_rows = q.bill_payments(bill["id"]) if bill else []
        self.payments_table.set_rows([
            [billing.format_rupees(p["amount_paise"]), p["mode"], p["paid_at"]]
            for p in self.payment_rows
        ])

    def _read_items(self) -> List[dict]:
        out = []
        for r in range(self.items_table.rowCount()):
            base = self.items[r] if r < len(self.items) else {}
            rate_cell = self.items_table.item(r, 1)
            qty_cell = self.items_table.item(r, 2)
            try:
                qty = max(1, int(float(qty_cell.text()))) if qty_cell else 1
            except ValueError:
                qty = 1
            out.append({
                "label": self.items_table.item(r, 0).text(),
                "rate_paise": billing.to_paise(rate_cell.text() if rate_cell else 0),
                "qty": qty,
                "test_id": base.get("test_id"),
                "panel_id": base.get("panel_id"),
            })
        return out

    def _recalc(self) -> None:
        items = self._read_items()
        dtype = (billing.DISCOUNT_PERCENT if self.discount_type.currentIndex() == 0
                 else billing.DISCOUNT_FLAT)
        totals = billing.compute_totals(
            [billing.LineItem(i["label"], i["rate_paise"], i["qty"]) for i in items],
            dtype, self.discount_value.value(),
            [billing.Payment(int(p["amount_paise"])) for p in getattr(self, "payment_rows", [])],
        )
        colour = style.GREEN if totals.balance_paise <= 0 else style.AMBER
        self.totals_label.setText(
            f"Total {billing.format_rupees(totals.net_paise)}"
            f"      Paid {billing.format_rupees(totals.paid_paise)}"
            f"      Balance {billing.format_rupees(totals.balance_paise)}")
        self.totals_label.setStyleSheet(
            f"font-size: 12pt; font-weight: 700; color: {colour};")

    # --------------------------------------------------------------- actions
    def _save(self) -> int:
        dtype = (billing.DISCOUNT_PERCENT if self.discount_type.currentIndex() == 0
                 else billing.DISCOUNT_FLAT)
        bill_id = q.save_bill(self.job_id, self._read_items(), dtype,
                              self.discount_value.value())
        self._load_payments()
        self._recalc()
        return bill_id

    def _print_a4(self) -> None:
        from .bill_preview import BillPreviewDialog
        self._save()
        BillPreviewDialog(self.job_id, self).exec()

    def _print_pos(self) -> None:
        from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
        from ..output import receipt as rcpt
        self._save()
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        if QPrintDialog(printer, self).exec() == QPrintDialog.DialogCode.Accepted:
            try:
                data = services.build_bill_data(self.job_id)
                rcpt.print_bill(data, printer, with_header=True)
                info(self, "Receipt Printed", "80mm POS thermal receipt sent to printer.")
            except Exception as exc:
                error(self, "Printing failed", str(exc))

    def _add_payment(self) -> None:
        amount = billing.to_paise(self.pay_amount.value())
        if amount <= 0:
            warn(self, "Nothing to add", "Enter the amount received first.")
            return
        bill_id = self._save()
        q.add_payment(bill_id, amount, self.pay_mode.currentText())
        self.pay_amount.setValue(0)
        self._load_payments()
        self._recalc()

    def _remove_payment(self) -> None:
        i = self.payments_table.selected_row()
        if i < 0 or i >= len(self.payment_rows):
            return
        p = self.payment_rows[i]
        if not confirm(self, "Remove this payment?",
                       f"{billing.format_rupees(p['amount_paise'])} received on "
                       f"{p['paid_at']} will be removed from the record.", "Remove"):
            return
        q.delete_payment(p["id"])
        self._load_payments()
        self._recalc()
