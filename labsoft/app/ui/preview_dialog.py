"""Look at the report before it goes anywhere.

The pages are drawn by the same code that writes the PDF, at screen resolution.
A preview produced by separate code would eventually stop matching the file
actually sent, which would be worse than having no preview.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from .. import services
from ..db import queries as q
from ..output import report as rpt
from . import style
from .widgets import button, error, info, label, row

ZOOMS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]


class PreviewDialog(QDialog):
    """Show every page of a report, with page and zoom controls."""

    def __init__(self, job_id: int, parent=None, allow_send: bool = False):
        super().__init__(parent)
        self.job_id = job_id
        self.allow_send = allow_send
        self.pages: List[QImage] = []
        self.page_index = 0
        self.zoom_index = 2          # 100%
        self.send_requested = False

        job = q.get_job(job_id) or {}
        who = job.get("name_at_test") or job.get("patient_name") or ""
        self.setWindowTitle(f"Report preview — {job.get('report_no', '')}  {who}")
        self.resize(980, 900)

        self._build()
        self._render()

    # ----------------------------------------------------------------- build
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(9)

        self.prev_button = button("‹ Previous", "", self._previous)
        self.next_button = button("Next ›", "", self._next)
        self.page_label = label("", "hint")
        self.zoom_out_button = button("−", "", lambda: self._zoom(-1))
        self.zoom_in_button = button("+", "", lambda: self._zoom(1))
        self.zoom_label = label("100%", "hint")

        lay.addWidget(row(self.prev_button, self.next_button, 10, self.page_label,
                          None,
                          self.zoom_out_button, self.zoom_label, self.zoom_in_button))

        self.scroll = QScrollArea()
        self.scroll.setObjectName("previewScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setStyleSheet(f"background: #6E7781; border: 0;")

        self.page_view = QLabel()
        self.page_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_view.setStyleSheet("background: transparent; padding: 18px;")
        self.scroll.setWidget(self.page_view)
        lay.addWidget(self.scroll, 1)

        self.hint = label(
            "This is exactly what the patient will receive.", "hint")
        lay.addWidget(self.hint)

        buttons = [button("Print…", "", self._print),
                   button("Save a copy…", "", self._save_copy),
                   None,
                   button("Close", "", self.reject)]
        if self.allow_send:
            buttons.append(button("Looks right — send", "go", self._accept_send))
        lay.addWidget(row(*buttons))

    # ---------------------------------------------------------------- render
    def _render(self) -> None:
        try:
            with_hdr = q.setting_bool("print_header", False)
            data = services.build_report_data(self.job_id)
            pages = list(rpt.render_pages(data, width_px=1000, with_header=with_hdr))
            if q.setting_bool("separate_detail_reports"):
                for test in services.detailed_tests(self.job_id):
                    detail_data = services.build_detail_data(self.job_id, test)
                    pages.extend(rpt.render_pages(detail_data, width_px=1000, with_header=with_hdr))
            self.pages = pages
        except Exception as exc:
            error(self, "Preview could not be drawn",
                  f"{exc}\n\nThe report itself is unaffected — you can still "
                  f"print or send it.")
            self.pages = []
        self.page_index = 0
        self._show_page()

    def _show_page(self) -> None:
        total = len(self.pages)
        if not total:
            self.page_view.setText("Nothing to preview yet.")
            self.page_label.setText("")
            for b in (self.prev_button, self.next_button):
                b.setEnabled(False)
            return

        self.page_index = max(0, min(self.page_index, total - 1))
        image = self.pages[self.page_index]
        zoom = ZOOMS[self.zoom_index]
        pixmap = QPixmap.fromImage(image).scaledToWidth(
            int(image.width() * zoom * 0.62),
            Qt.TransformationMode.SmoothTransformation)
        self.page_view.setPixmap(pixmap)
        self.page_view.resize(pixmap.size())

        self.page_label.setText(f"Page {self.page_index + 1} of {total}")
        self.prev_button.setEnabled(self.page_index > 0)
        self.next_button.setEnabled(self.page_index < total - 1)
        self.zoom_label.setText(f"{int(zoom * 100)}%")
        self.zoom_out_button.setEnabled(self.zoom_index > 0)
        self.zoom_in_button.setEnabled(self.zoom_index < len(ZOOMS) - 1)

    # --------------------------------------------------------------- actions
    def _previous(self) -> None:
        self.page_index -= 1
        self._show_page()

    def _next(self) -> None:
        self.page_index += 1
        self._show_page()

    def _zoom(self, step: int) -> None:
        self.zoom_index = max(0, min(len(ZOOMS) - 1, self.zoom_index + step))
        self._show_page()

    def keyPressEvent(self, event):        # noqa: N802 - Qt naming
        key = event.key()
        if key in (Qt.Key.Key_Right, Qt.Key.Key_PageDown):
            self._next()
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_PageUp):
            self._previous()
        elif key == Qt.Key.Key_Plus:
            self._zoom(1)
        elif key == Qt.Key.Key_Minus:
            self._zoom(-1)
        else:
            super().keyPressEvent(event)

    def _print(self) -> None:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return
        try:
            data = services.build_report_data(self.job_id)
            rpt.print_report(data, printer)
        except Exception as exc:
            error(self, "Printing failed", str(exc))
            return
        q.log_action("report_printed", "job", self.job_id, "from preview")

    def _save_copy(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        job = q.get_job(self.job_id) or {}
        suggested = services.pdf_filename(job)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save a copy of this report", suggested, "PDF (*.pdf)")
        if not path:
            return
        try:
            data = services.build_report_data(self.job_id)
            rpt.write_pdf(data, Path(path))
        except Exception as exc:
            error(self, "Could not save", str(exc))
            return
        info(self, "Saved", f"A copy has been written to:\n{path}")

    def _accept_send(self) -> None:
        self.send_requested = True
        self.accept()
