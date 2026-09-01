"""Professional WhatsApp Dispatch Dialog."""

from __future__ import annotations

import urllib.parse
import webbrowser
from PyQt6.QtWidgets import (
    QApplication, QDialog, QLabel, QTextEdit,
    QVBoxLayout, QWidget
)

from . import style
from .widgets import button, label, row, info


class WhatsAppDialog(QDialog):
    """Formats and dispatches structured clinical reports via WhatsApp."""

    def __init__(self, parent: QWidget | None, job_data: dict, results_summary: str):
        super().__init__(parent)
        self.setWindowTitle("Professional WhatsApp Dispatch (F8)")
        self.setFixedWidth(520)
        self.setFixedHeight(500)
        self.job_data = job_data
        self.phone = (job_data.get("phone") or "").replace("+", "").replace("-", "").replace(" ", "").strip()
        if len(self.phone) == 10:
            self.phone = "91" + self.phone

        self.msg_text = (
            f"*🧪 MITHRA DIAGNOSTIC CLINICAL LABORATORY*\n"
            f"*━━━━━━━━━━━━━━━━━━━━━━━━━━━━━*\n"
            f"👤 *Patient:* {job_data.get('patient_name', '')}\n"
            f"📋 *Report No:* #{job_data.get('report_no', '')}\n"
            f"📅 *Date:* {str(job_data.get('received_at', ''))[:10]}\n"
            f"*━━━━━━━━━━━━━━━━━━━━━━━━━━━━━*\n"
            f"*INVESTIGATION RESULTS:*\n"
            f"{results_summary}\n"
            f"*━━━━━━━━━━━━━━━━━━━━━━━━━━━━━*\n"
            f"✅ *Status:* Verified & Approved\n"
            f"📥 Detailed PDF report available at the laboratory desk."
        )

        self._build_ui()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        title = label("WhatsApp Dispatch (Direct Clinician/Patient Dispatch)", "strong")
        title.setStyleSheet(f"font-size: 12pt; color: {style.INK}; font-weight: 800;")
        lay.addWidget(title)

        meta = QLabel(f"Recipient: <b>+{self.phone}</b> ({self.job_data.get('patient_name', '')})")
        meta.setStyleSheet(f"font-size: 10pt; color: {style.INK2};")
        lay.addWidget(meta)

        self.preview_box = QTextEdit()
        self.preview_box.setPlainText(self.msg_text)
        self.preview_box.setStyleSheet(
            "font-family: monospace; font-size: 9.5pt; padding: 10px; border: 1.5px solid #cbd5e1; border-radius: 4px;"
        )
        lay.addWidget(self.preview_box, 1)

        copy_btn = button("📋 Copy Message", "", self._copy_text)
        send_btn = button("📱 Open WhatsApp Web / Desktop", "primary", self._open_whatsapp)
        send_btn.setStyleSheet("background: #25D366; color: #FFFFFF; font-weight: 700;")
        close_btn = button("Close", "", self.accept)

        lay.addWidget(row(copy_btn, None, close_btn, send_btn))

    def _copy_text(self) -> None:
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self.preview_box.toPlainText())
        info(self, "Copied", "WhatsApp message text copied to clipboard!")

    def _open_whatsapp(self) -> None:
        text = self.preview_box.toPlainText()
        encoded = urllib.parse.quote(text)
        url = f"https://wa.me/{self.phone}?text={encoded}"
        webbrowser.open(url)
        self.accept()
