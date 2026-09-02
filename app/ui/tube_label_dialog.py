"""Phlebotomy Vacutainer Tube Barcode Label Printer Dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter
from PyQt6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel,
    QVBoxLayout, QWidget
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

from . import style
from .widgets import button, label, row


class TubeLabelDialog(QDialog):
    """50mm x 25mm Phlebotomy Vacutainer Sticker Label Dialog."""

    def __init__(self, parent: QWidget | None, job_data: dict, test_names: list[str]):
        super().__init__(parent)
        self.setWindowTitle("Phlebotomy Tube Barcode Label Printer (F7)")
        self.setFixedWidth(460)
        self.job_data = job_data
        self.test_names = test_names

        # Specimen Tube Color Detection
        tests_str = " ".join(test_names).upper()
        if any(x in tests_str for x in ("CBC", "HB", "ESR", "PLATELET", "SMEAR", "MALARIA")):
            self.tube_color = "#9333ea"  # Lavender (EDTA)
            self.tube_name = "EDTA WHOLE BLOOD (LAVENDER)"
        elif any(x in tests_str for x in ("GLUCOSE", "SUGAR", "FBS", "PPBS", "RBS")):
            self.tube_color = "#64748b"  # Grey (Fluoride)
            self.tube_name = "FLUORIDE PLASMA (GREY)"
        elif any(x in tests_str for x in ("PT", "INR", "APTT")):
            self.tube_color = "#0284c7"  # Blue (Citrate)
            self.tube_name = "CITRATE PLASMA (LIGHT BLUE)"
        else:
            self.tube_color = "#dc2626"  # Red / Gold (Serum)
            self.tube_name = "CLOT ACTIVATOR SERUM (RED)"

        self._build_ui()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        title = label("Phlebotomy Vacutainer Tube Sticker (50mm × 25mm)", "strong")
        title.setStyleSheet(f"font-size: 12pt; color: {style.INK}; font-weight: 800;")
        lay.addWidget(title)

        # Tube Type Banner
        tube_strip = QFrame()
        tube_strip.setFixedHeight(28)
        # The cap colours are the vacutainer convention, not this palette: a
        # lavender tube is lavender on every bench in the world.
        tube_strip.setStyleSheet(
            f"background: {self.tube_color}; border-radius: 0;")
        tl = QHBoxLayout(tube_strip)
        tl.setContentsMargins(12, 0, 12, 0)
        tb_label = QLabel(self.tube_name)
        tb_label.setStyleSheet(
            "color: #ffffff; font-weight: 800; font-size: 9.5pt; background: transparent;")
        tl.addWidget(tb_label)
        lay.addWidget(tube_strip)

        # Label Preview Box
        preview_box = QFrame()
        preview_box.setStyleSheet(
            f"background: {style.PANEL}; border: 1px dashed {style.FIELD_BORDER}; "
            f"border-radius: 0; padding: 14px;")
        pl = QVBoxLayout(preview_box)
        pl.setSpacing(4)

        report_no = self.job_data.get("report_no", "—")
        patient_name = self.job_data.get("patient_name", "PATIENT")
        patient_meta = f"{self.job_data.get('age', '')} / {self.job_data.get('sex', '')}"
        date_str = str(self.job_data.get("received_at", ""))[:16]

        pl.addWidget(QLabel(
            f"<b style='font-size:12pt; color:{style.INK};'>LAB REPORT #{report_no}</b>"))
        pl.addWidget(QLabel(
            f"<b style='font-size:11pt; color:{style.INK};'>{patient_name}</b> "
            f"({patient_meta})"))
        pl.addWidget(QLabel(
            f"<span style='font-size:8.5pt; color:{style.INK3};'>Date: {date_str}</span>"))

        # The report number, set large and monospaced so it can be read off a
        # tube across the bench. There was a drawn barcode here, but the bars
        # were decorative -- they encoded nothing. A sticker that looks
        # scannable and is not gets scanned anyway, and the specimen ends up
        # filed against whatever the scanner last read.
        number = QLabel(str(report_no))
        number.setStyleSheet(
            f"font-family: monospace; font-size: 26pt; font-weight: 800; "
            f"letter-spacing: 4px; color: {style.INK};")
        number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pl.addWidget(number)

        pl.addWidget(QLabel(f"<span style='font-size:8pt; color:#000;'><b>Tests:</b> {', '.join(self.test_names[:6])}</span>"))
        lay.addWidget(preview_box)

        # Buttons
        print_btn = button("Print Tube Sticker", "primary", self._print_sticker)
        close_btn = button("Close", "", self.accept)
        lay.addWidget(row(None, close_btn, print_btn))

    def _print_sticker(self) -> None:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            painter = QPainter(printer)
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            painter.drawText(20, 30, f"LAB #{self.job_data.get('report_no', '')} - {self.job_data.get('patient_name', '')}")
            painter.setFont(QFont("Arial", 8))
            painter.drawText(20, 50, f"Specimen: {self.tube_name}")
            painter.drawText(20, 70, f"Tests: {', '.join(self.test_names)}")
            painter.end()
            self.accept()
