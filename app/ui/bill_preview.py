"""Look at the bill, print it, save it, or send it.

Drawn by the same code that writes the receipt PDF, so what is on the screen
and what comes out of the printer cannot drift apart.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import QDialog, QFileDialog, QLabel, QScrollArea, QVBoxLayout

from .. import services
from ..db import queries as q
from ..output import receipt as rcpt
from ..output import sender as snd
from . import style
from .widgets import button, error, info, label, row, warn

ZOOMS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]


class BillPreviewDialog(QDialog):
    def __init__(self, job_id: int, parent=None):
        super().__init__(parent)
        self.job_id = job_id
        self.job = q.get_job(job_id) or {}
        self.pages: List[QImage] = []
        self.zoom_index = 2
        self.pdf_path: Optional[Path] = None

        who = self.job.get("name_at_test") or self.job.get("patient_name") or ""
        self.setWindowTitle(f"Bill — {self.job.get('report_no', '')}  {who}")
        self.resize(900, 880)
        self._build()
        self._render()

    # ----------------------------------------------------------------- build
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(9)

        self.zoom_out_button = button("−", "", lambda: self._zoom(-1))
        self.zoom_in_button = button("+", "", lambda: self._zoom(1))
        self.zoom_label = label("100%", "hint")
        lay.addWidget(row(label("One page, as it will print.", "hint"), None,
                          self.zoom_out_button, self.zoom_label,
                          self.zoom_in_button))

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Themed, so the mount darkens with the rest of the program
        # instead of staying one fixed grey in both.
        self.scroll.setStyleSheet(
            f"background: {style.PAPER_MOUNT}; border: 0;")
        self.page_view = QLabel()
        self.page_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_view.setStyleSheet("background: transparent; padding: 18px;")
        self.scroll.setWidget(self.page_view)
        lay.addWidget(self.scroll, 1)

        self.note = label("", "hint")
        self.note.setWordWrap(True)
        lay.addWidget(self.note)

        lay.addWidget(row(button("Print…", "primary", self._print),
                          button("Save as PDF…", "", self._save_copy),
                          button("Send on WhatsApp", "", self._whatsapp),
                          None, button("Close", "", self.reject)))

    # ---------------------------------------------------------------- render
    def _render(self) -> None:
        try:
            data = services.build_bill_data(self.job_id)
            self.pages = rcpt.render_pages(data, width_px=1000)
        except Exception as exc:
            error(self, "The bill could not be drawn", str(exc))
            self.pages = []
        self._show_page()

    def _show_page(self) -> None:
        if not self.pages:
            self.page_view.setText("Nothing to show.")
            return
        image = self.pages[0]
        zoom = ZOOMS[self.zoom_index]
        pixmap = QPixmap.fromImage(image).scaledToWidth(
            int(image.width() * zoom * 0.62),
            Qt.TransformationMode.SmoothTransformation)
        self.page_view.setPixmap(pixmap)
        self.page_view.resize(pixmap.size())
        self.zoom_label.setText(f"{int(zoom * 100)}%")
        self.zoom_out_button.setEnabled(self.zoom_index > 0)
        self.zoom_in_button.setEnabled(self.zoom_index < len(ZOOMS) - 1)

    def _zoom(self, step: int) -> None:
        self.zoom_index = max(0, min(len(ZOOMS) - 1, self.zoom_index + step))
        self._show_page()

    # --------------------------------------------------------------- actions
    def _print(self) -> None:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        if QPrintDialog(printer, self).exec() != QPrintDialog.DialogCode.Accepted:
            return
        try:
            data = services.build_bill_data(self.job_id)
            rcpt.print_bill(data, printer, with_header=q.setting_bool("print_header"))
        except Exception as exc:
            error(self, "Printing failed", str(exc))
            return
        q.log_action("bill_printed", "job", self.job_id, "to printer")
        self._say("Sent to the printer.", style.GREEN)

    def _ensure_pdf(self) -> Optional[Path]:
        if self.pdf_path and self.pdf_path.exists():
            return self.pdf_path
        try:
            self.pdf_path = services.generate_bill_pdf(self.job_id)
        except Exception as exc:
            error(self, "The bill could not be saved", str(exc))
            return None
        return self.pdf_path

    def _save_copy(self) -> None:
        path = self._ensure_pdf()
        if not path:
            return
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Save a copy of this bill", path.name, "PDF (*.pdf)")
        if not chosen:
            return
        try:
            Path(chosen).write_bytes(path.read_bytes())
        except OSError as exc:
            error(self, "Could not save", str(exc))
            return
        info(self, "Saved", f"A copy has been written to:\n{chosen}")

    def _whatsapp(self) -> None:
        path = self._ensure_pdf()
        if not path:
            return
        settings = q.all_settings()
        phone = self.job.get("patient_phone") or ""
        if not snd.normalise_phone(phone, settings.get("country_code", "91")):
            warn(self, "No mobile number",
                 "This patient has no complete mobile number saved, so the bill "
                 "cannot be sent.\n\nAdd the number on the job screen first.")
            return

        lab = (settings.get("lab_name_prefix", "") + " " +
               settings.get("lab_name", "")).strip()
        message = (f"Dear {self.job.get('name_at_test') or self.job.get('patient_name')},"
                   f"\nYour bill from {lab} (No {self.job.get('report_no')}) is attached."
                   f"\nThank you.")
        sender = snd.get_sender("whatsapp", settings.get("country_code", "91"),
                                settings.get("whatsapp_mode", "auto"))
        try:
            result = sender.send(path, phone, message)
        except snd.SendError as exc:
            warn(self, "Could not send", str(exc))
            return
        q.log_action("bill_sent", "job", self.job_id, result.channel)
        self._say(result.manual_step, style.AMBER)

    def _say(self, text: str, colour: str) -> None:
        self.note.setText(text)
        self.note.setStyleSheet(f"color: {colour}; font-weight: 600;")
