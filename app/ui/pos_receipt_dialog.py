"""80mm POS Thermal Receipt Preview & Print Dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter
from PyQt6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QTextEdit,
    QVBoxLayout, QWidget
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

from ..core import billing
from ..db import queries as q
from . import style
from .widgets import button, label, row


class POSReceiptDialog(QDialog):
    """80mm POS Thermal Bill Receipt Preview & Printer."""

    def __init__(self, parent: QWidget | None, job_id: int):
        super().__init__(parent)
        self.setWindowTitle("80mm POS Thermal Receipt Preview")
        self.setFixedWidth(400)
        self.setFixedHeight(600)
        self.job_id = job_id
        self.job = q.get_job(job_id) or {}
        self.bill = q.get_bill(job_id) or {}
        self.settings = q.all_settings()
        self._build_ui()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(12)

        lay.addWidget(label("80mm Thermal Receipt (POS Slip)", "strong"))

        # Thermal Receipt Card
        receipt_frame = QFrame()
        receipt_frame.setStyleSheet(
            "background: #ffffff; border: 1.5px solid #94a3b8; border-radius: 4px; padding: 12px;"
        )
        rl = QVBoxLayout(receipt_frame)
        rl.setSpacing(2)

        lab_prefix = self.settings.get("lab_name_prefix", "MITHRA")
        lab_name = self.settings.get("lab_name", "DIAGNOSTIC LABORATORY")
        address = self.settings.get("lab_address", "Medical Centre Road")
        phone = self.settings.get("lab_phone", "9876543210")

        header_html = (
            f"<div style='text-align:center; font-family:monospace;'>"
            f"<b style='font-size:12pt; color:#000;'>{lab_prefix} {lab_name}</b><br>"
            f"<span style='font-size:8pt; color:#444;'>{address}<br>Ph: {phone}</span><br>"
            f"<b>----------------------------------------</b><br>"
            f"<b style='font-size:9.5pt;'>TAX INVOICE / CASH RECEIPT</b><br>"
            f"<b>----------------------------------------</b>"
            f"</div>"
        )
        rl.addWidget(QLabel(header_html))

        p_name = self.job.get("name_at_test") or self.job.get("patient_name", "")
        r_no = self.job.get("report_no", self.job_id)
        date_str = str(self.job.get("received_at", ""))[:16]
        doctor = self.job.get("referrer_name", "SELF / DIRECT")

        meta_html = (
            f"<div style='font-family:monospace; font-size:8.5pt; color:#000; line-height:1.4;'>"
            f"Bill No: <b>#{r_no}</b> &nbsp;&nbsp; Date: {date_str}<br>"
            f"Patient: <b>{p_name}</b><br>"
            f"Ref By : {doctor}<br>"
            f"----------------------------------------"
            f"</div>"
        )
        rl.addWidget(QLabel(meta_html))

        # Items Table
        tests = q.job_tests(self.job_id)
        items_html = "<table style='width:100%; font-family:monospace; font-size:8.5pt; color:#000;'>"
        items_html += "<tr><th align='left'>Test Description</th><th align='right'>Amount</th></tr>"
        total_p = 0
        for t in tests:
            rate = t.get("rate_paise", 0)
            total_p += rate
            items_html += f"<tr><td>{t['name'][:24]}</td><td align='right'>₹{rate/100:.2f}</td></tr>"
        items_html += "</table>"
        rl.addWidget(QLabel(items_html))

        charged_p = self.bill.get("charged_paise", total_p)
        disc_p = self.bill.get("discount_paise", 0)
        paid_p = self.bill.get("paid_paise", charged_p)
        bal_p = max(0, charged_p - disc_p - paid_p)

        totals_html = (
            f"<div style='font-family:monospace; font-size:8.5pt; color:#000; line-height:1.5; margin-top:6px;'>"
            f"----------------------------------------<br>"
            f"Gross Total : <b style='float:right;'>₹{charged_p/100:.2f}</b><br>"
            f"Discount    : <span style='float:right;'>₹{disc_p/100:.2f}</span><br>"
            f"<b style='font-size:10pt;'>NET PAYABLE : <span style='float:right;'>₹{(charged_p - disc_p)/100:.2f}</span></b><br>"
            f"Amount Paid : <span style='float:right;'>₹{paid_p/100:.2f}</span><br>"
            f"Balance Due : <span style='float:right;'>₹{bal_p/100:.2f}</span><br>"
            f"----------------------------------------<br>"
            f"<div style='text-align:center; font-size:8pt; margin-top:4px;'>* Thank You & Wish You Good Health *</div>"
            f"</div>"
        )
        rl.addWidget(QLabel(totals_html))
        lay.addWidget(receipt_frame, 1)

        print_btn = button("🖨️ Print 80mm Receipt", "primary", self._print_pos)
        close_btn = button("Close", "", self.accept)
        lay.addWidget(row(None, close_btn, print_btn))

    def _print_pos(self) -> None:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            painter = QPainter(printer)
            painter.setFont(QFont("Courier", 9))
            p_name = self.job.get("name_at_test") or self.job.get("patient_name", "")
            r_no = self.job.get("report_no", self.job_id)
            painter.drawText(10, 20, f"LAB #{r_no} - {p_name}")
            painter.drawText(10, 40, f"Paid: ₹{self.bill.get('paid_paise', 0)/100:.2f}")
            painter.end()
            self.accept()
