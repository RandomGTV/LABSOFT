"""The 80mm counter slip: what it will look like, and printing it.

What is on screen here is the slip itself, painted by ``output.receipt`` at
the size it prints. That is deliberate. The previous version drew its own
HTML copy of a receipt, which meant two renderers that could disagree — and
they did, in three ways at once:

  * it read ``charged_paise`` and ``paid_paise`` off the bill row. The bills
    table has neither column: it holds gross, discount and net, and what has
    been paid is the sum of the payments table. Both reads fell through to
    their defaults, so every slip printed "Amount Paid" equal to the total
    and "Balance Due ₹0.00" however much was actually owed.
  * every colour in it was written as ``#000`` and ``#444``, so in the night
    theme the whole receipt was black text on a dark panel.
  * printing did not print the receipt. It drew two lines of text — the
    report number and a figure — and stopped.

A receipt is white paper in both themes, so the preview is an image of the
paper on a plain mount rather than a screen-coloured imitation of it.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QScrollArea, QVBoxLayout, QWidget,
)

from .. import config, services
from ..core import billing
from ..db import queries as q
from ..output import receipt as rcpt
from .widgets import button, dialog_header, error, info, label, row

#: the slip on screen, in pixels. 80mm at roughly 5 px/mm reads comfortably.
PREVIEW_W = 400


class POSReceiptDialog(QDialog):
    """Preview and print the 80mm slip for one job."""

    def __init__(self, parent: QWidget | None, job_id: int):
        super().__init__(parent)
        self.job_id = job_id
        self.job = q.get_job(job_id) or {}
        self.setWindowTitle(f"Counter slip — report {self.job.get('report_no', '')}")
        self.resize(520, 720)
        self._build()
        self.refresh()

    # ----------------------------------------------------------------- build
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        lay.addWidget(dialog_header(
            "Counter slip · 80mm",
            "Exactly what the thermal printer will put on the roll."))

        self.paper = label("")
        self.paper.setAlignment(Qt.AlignmentFlag.AlignHCenter
                                | Qt.AlignmentFlag.AlignTop)

        mount = QFrame()
        mount.setObjectName("slipMount")
        ml = QVBoxLayout(mount)
        ml.setContentsMargins(20, 20, 20, 20)
        ml.addWidget(self.paper)
        ml.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("slipScroll")
        scroll.setWidgetResizable(True)
        scroll.setWidget(mount)
        lay.addWidget(scroll, 1)

        self.summary = label("", "hint")
        lay.addWidget(self.summary)

        lay.addWidget(row(
            None,
            button("Save as PDF", "", self._save_pdf),
            button("Close", "", self.reject),
            button("Print slip", "primary", self._print)))

    # ------------------------------------------------------------------ data
    def refresh(self) -> None:
        try:
            self.data = services.build_bill_data(self.job_id)
        except Exception as exc:
            error(self, "Nothing to print", str(exc))
            self.summary.setText("")
            return

        image = rcpt.render_slip(self.data, PREVIEW_W)
        self.paper.setPixmap(QPixmap.fromImage(image))
        self.paper.setFixedSize(image.width(), image.height())

        totals = self.data.totals()
        money = q.job_money(self.job_id)
        # Read back from the ledger as well as from the document, and say so
        # if the two ever disagree — that is the failure this screen had.
        agrees = (not money["billed"]
                  or (money["net_paise"] == totals.net_paise
                      and money["paid_paise"] == totals.paid_paise))
        self.summary.setText(
            f"Net {billing.format_rupees(totals.net_paise)} · "
            f"paid {billing.format_rupees(totals.paid_paise)} · "
            f"balance {billing.format_rupees(totals.balance_paise)}"
            + ("" if agrees else
               "   ⚠ this does not match the ledger — reopen the bill and save it"))
        self.summary.setProperty("role", "hint" if agrees else "error")
        self.summary.style().unpolish(self.summary)
        self.summary.style().polish(self.summary)

    # --------------------------------------------------------------- actions
    def _print(self) -> None:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setFullPage(True)
        if QPrintDialog(printer, self).exec() != QDialog.DialogCode.Accepted:
            return
        try:
            rcpt.print_slip(self.data, printer)
        except Exception as exc:
            error(self, "The slip did not print", str(exc))
            return
        q.log_action("slip_printed", "job", self.job_id)
        self.accept()

    def _save_pdf(self) -> None:
        default = config.exports_dir() / f"slip_{self.data.bill_no}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save the slip", str(default), "PDF (*.pdf)")
        if not path:
            return
        try:
            written = rcpt.write_slip_pdf(self.data, path)
        except Exception as exc:
            error(self, "The slip was not saved", str(exc))
            return
        info(self, "Saved", f"Written to:\n{written}")
