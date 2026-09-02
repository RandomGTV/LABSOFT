"""Professional WhatsApp Dispatch Dialog."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QApplication, QDialog, QLabel, QTextEdit,
    QVBoxLayout, QWidget
)

from ..db import queries as q
from . import style
from .widgets import button, label, row, info, warn


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
            # The laboratory's real name, not one written into the code:
            # "MITHRA DIAGNOSTIC CLINICAL LABORATORY" is not what the
            # letterhead says, and a lab that renames itself under Settings
            # would have gone on sending the old name here for ever.
            f"*🧪 {((q.get_setting('lab_name_prefix') + ' ' + q.get_setting('lab_name')).strip() or 'Laboratory').upper()}*\n"
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

        title = label("Send this report on WhatsApp", "cardtitle")
        title.setStyleSheet(f"font-size: 13pt; color: {style.INK}; font-weight: 700;")
        lay.addWidget(title)

        meta = QLabel(f"Recipient: <b>+{self.phone}</b> ({self.job_data.get('patient_name', '')})")
        meta.setStyleSheet(f"font-size: 10pt; color: {style.INK2};")
        lay.addWidget(meta)

        self.preview_box = QTextEdit()
        self.preview_box.setPlainText(self.msg_text)
        self.preview_box.setStyleSheet(
            f"font-family: monospace; font-size: 9.5pt; padding: 10px; "
            f"border: 1px solid {style.LINE}; border-radius: 0;"
        )
        lay.addWidget(self.preview_box, 1)

        copy_btn = button("📋 Copy Message", "", self._copy_text)
        send_btn = button("📱 Open WhatsApp Web / Desktop", "primary", self._open_whatsapp)
        # WhatsApp's own green, because the button opens WhatsApp -- it is a
        # logo colour, not a colour from this palette.
        send_btn.setStyleSheet(
            "background: #128C4A; color: #FFFFFF; font-weight: 800; "
            "border: 1px solid #128C4A; border-radius: 0;")
        close_btn = button("Close", "", self.accept)

        lay.addWidget(row(copy_btn, None, close_btn, send_btn))

    def _copy_text(self) -> None:
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self.preview_box.toPlainText())
        info(self, "Copied", "WhatsApp message text copied to clipboard!")

    def _open_whatsapp(self) -> None:
        """Open the chat through the shared sender, not through wa.me.

        This used to build `https://wa.me/<number>?text=<the whole report>`
        and hand it to the browser. Every result on the job — HIV, HBsAg, a
        pregnancy test — travelled to Meta's redirect service as a query
        string, and stayed in the browser's history and address bar. The
        sender opens the WhatsApp application on the right chat instead, and
        only the covering message goes in the URL.
        """
        from ..output import sender as snd

        try:
            result = snd.open_chat(
                self.phone, self.covering_message(),
                q.get_setting("country_code") or "91",
                q.get_setting("whatsapp_mode") or "desktop")
        except snd.SendError as exc:
            warn(self, "WhatsApp did not open", str(exc))
            return
        info(self, "WhatsApp opened",
             f"{result.manual_step}\n\nThe results are on the clipboard if "
             f"you want them in the message — paste them yourself. Nothing "
             f"has been sent.")
        self.accept()

    def covering_message(self) -> str:
        """The short line that goes in the URL. Not the results."""
        name = (self.job_data.get("patient_name")
                or self.job_data.get("name") or "").strip()
        report = self.job_data.get("report_no", "")
        lab = (q.get_setting("lab_name_prefix") + " "
               + q.get_setting("lab_name")).strip()
        return (f"Dear {name}, your report {report} from {lab} is ready. "
                f"The report is attached.").strip()
