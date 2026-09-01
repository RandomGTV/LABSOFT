"""The dialog that appears once a report has been produced."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QDialog, QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QVBoxLayout,
)

from .. import services
from ..core import turnaround
from ..db import queries as q
from ..output import report as rpt
from ..output import sender as snd
from ..output import winauto
from . import style
from .widgets import button, error, field_label, info, label, row, warn


class _AttachWorker(QThread):
    """Waits for WhatsApp and pastes the report into it.

    On its own thread because WhatsApp can take many seconds to start, and a
    frozen window would look like the program had crashed.
    """

    finished_with = pyqtSignal(bool, str)

    def __init__(self, timeout: float, parent=None):
        super().__init__(parent)
        self.timeout = timeout

    def run(self) -> None:
        try:
            result = winauto.paste_into_whatsapp(timeout=self.timeout)
            self.finished_with.emit(result.ok, result.reason)
        except Exception as exc:                  # never let a thread die silently
            self.finished_with.emit(False, f"Automatic attaching failed: {exc}")


class SendDialog(QDialog):
    def __init__(self, job_id: int, parent=None):
        super().__init__(parent)
        self.job_id = job_id
        self.job = q.get_job(job_id)
        self.settings = q.all_settings()
        self.pdf_path: Optional[Path] = None

        self.setWindowTitle(f"Send report — {self.job['report_no']}")
        self.setMinimumWidth(560)
        self._build()
        self._prepare()

    # ----------------------------------------------------------------- build
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        self.file_label = label("", "")
        self.file_hint = label("", "hint")
        card = QFrame()
        card.setStyleSheet(
            f"background: #FAFBFC; border: 1px solid {style.LINE}; border-radius: 6px;")
        card_lay = QHBoxLayout(card)
        card_lay.setContentsMargins(14, 12, 14, 12)
        tag = QLabel("PDF")
        tag.setFixedSize(40, 48)
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tag.setStyleSheet(
            f"background: white; border: 1px solid {style.LINE}; border-radius: 4px;"
            f"color: {style.RED}; font-weight: 800; font-size: 9pt;")
        card_lay.addWidget(tag)
        inner = QVBoxLayout()
        inner.setSpacing(2)
        inner.addWidget(self.file_label)
        inner.addWidget(self.file_hint)
        card_lay.addLayout(inner, 1)
        lay.addWidget(card)

        lay.addWidget(field_label("Send to"))
        self.phone_edit = QLineEdit()
        lay.addWidget(self.phone_edit)
        self.phone_warning = label("", "error")
        self.phone_warning.hide()
        lay.addWidget(self.phone_warning)

        lay.addWidget(field_label("Message"))
        self.message_edit = QPlainTextEdit()
        self.message_edit.setFixedHeight(108)
        lay.addWidget(self.message_edit)

        self.note = label("", "hint")
        self.note.setWordWrap(True)
        lay.addWidget(self.note)

        self.print_button = button("Print", "", self._print)
        self.folder_button = button("Open folder", "", self._open_folder)
        self.web_button = button(
            "Use WhatsApp Web", "", lambda: self._send(force_mode="web"),
            "Open the chat in your browser instead of the desktop app")
        self.close_button = button("Close", "", self.reject)
        self.send_button = button("Open WhatsApp && send", "go", self._send)
        lay.addWidget(row(self.print_button, self.folder_button, self.web_button,
                          None, self.close_button, self.send_button))

    # --------------------------------------------------------------- prepare
    def _prepare(self) -> None:
        try:
            self.pdf_path = services.generate_pdf(self.job_id)
        except Exception as exc:
            error(self, "Report could not be produced",
                  f"{exc}\n\nNothing has been sent. Try again, and if it keeps "
                  f"failing, restart LabSoft.")
            self.send_button.setEnabled(False)
            self.print_button.setEnabled(False)
            return

        self.job = q.get_job(self.job_id)
        size_kb = max(1, self.pdf_path.stat().st_size // 1024)
        self.file_label.setText(self.pdf_path.name)
        f = QFont()
        f.setBold(True)
        self.file_label.setFont(f)
        self.file_hint.setText(f"{size_kb} KB  ·  saved in {self.pdf_path.parent.name}")

        phone = self.job.get("patient_phone") or ""
        self.phone_edit.setText(phone)
        self._check_phone()
        self.phone_edit.textChanged.connect(lambda _t: self._check_phone())

        # Structured Clinical Results Summary
        stored = q.results_for_job(self.job_id)
        test_lines = []
        for jt in stored.values():
            name = jt.get("test_name") or jt.get("name")
            val = jt.get("display_value") or jt.get("raw_value")
            u = jt.get("unit") or ""
            if name and val:
                test_lines.append(f"• *{name}:* {val} {u}".strip())

        test_summary = "\n".join(test_lines)
        lab_full = (self.settings.get("lab_name_prefix", "") + " " +
                    self.settings.get("lab_name", "")).strip()
        name_str = self.job.get("name_at_test") or self.job.get("patient_name") or ""
        rep_no = self.job.get("report_no") or ""
        date_str = turnaround.format_date(reported)
        phone_str = self.settings.get("lab_phone", "").replace("Ph :", "").strip()

        if test_summary:
            msg = (
                f"🏥 *{lab_full}*\n"
                f"*Diagnostic Investigation Report*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 *Patient:* {name_str}\n"
                f"📋 *Report No:* #{rep_no}\n"
                f"📅 *Date:* {date_str}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"*INVESTIGATION RESULTS:*\n"
                f"{test_summary}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔒 _Official digital report generated & verified._\n"
                f"📞 {phone_str}"
            )
        else:
            msg = snd.format_message(
                self.settings.get("whatsapp_template", ""),
                name=name_str,
                lab=lab_full,
                report_no=rep_no,
                date=date_str,
                phone=phone_str,
            )

        self.message_edit.setPlainText(msg)

    def _check_phone(self) -> None:
        number = snd.normalise_phone(self.phone_edit.text(),
                                     self.settings.get("country_code", "91"))
        if number:
            self.phone_warning.hide()
            self.send_button.setEnabled(True)
            self.send_button.setToolTip("")
        else:
            self.phone_warning.setText(
                "That number is not complete — nothing will be sent until it is fixed.")
            self.phone_warning.setStyleSheet(f"color: {style.RED}; font-weight: 600;")
            self.phone_warning.show()
            self.send_button.setEnabled(False)
            self.send_button.setToolTip("Enter a complete mobile number first")

    # ---------------------------------------------------------------- actions
    def _send(self, force_mode: str = "") -> None:
        if not self.pdf_path:
            return
        mode = force_mode or self.settings.get("whatsapp_mode", "auto")
        sender = snd.get_sender("whatsapp", self.settings.get("country_code", "91"),
                                mode)
        try:
            result = sender.send(self.pdf_path, self.phone_edit.text(),
                                 self.message_edit.toPlainText())
        except snd.SendError as exc:
            warn(self, "Could not send", str(exc))
            return

        q.update_job(self.job_id, status=turnaround.STATUS_SENT,
                     sent_at=q.now_str(), sent_via=result.channel)
        q.log_action("report_sent", "job", self.job_id,
                     f"{result.channel} to {result.detail}")

        self.send_button.setEnabled(False)
        self.close_button.setText("Done")
        # Kept enabled: if the desktop app opened but did nothing visible, the
        # operator needs a second route without redoing the whole job.
        self.web_button.setText("Open in WhatsApp Web")

        auto = str(self.settings.get("auto_attach", "1")).strip() in ("1", "true", "yes")
        if auto and winauto.supported():
            self.send_button.setText("Attaching…")
            self._say("Waiting for WhatsApp, then attaching the report. "
                      "Do not touch the keyboard until it appears.", style.AMBER)
            self._worker = _AttachWorker(timeout=25.0, parent=self)
            self._worker.finished_with.connect(self._attach_done)
            self._worker.start()
        else:
            self.send_button.setText("Sent ✓")
            self._say(result.manual_step, style.AMBER)

    def _say(self, text: str, colour: str) -> None:
        self.note.setText(text)
        self.note.setStyleSheet(f"color: {colour}; font-weight: 600;")

    def _attach_done(self, ok: bool, reason: str) -> None:
        self.send_button.setText("Sent ✓")
        if ok:
            self._say("Report attached in WhatsApp. Press Send in WhatsApp to "
                      "deliver it.", style.GREEN)
            q.log_action("report_attached", "job", self.job_id, "auto")
        else:
            self._say(reason or "The report could not be attached automatically. "
                                "It is on the clipboard — press Ctrl+V in WhatsApp.",
                      style.AMBER)

    def _print(self) -> None:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return
        try:
            data = services.build_report_data(self.job_id)
            with_header = str(self.settings.get("print_header", "1")) in ("1", "true", "yes")
            rpt.print_report(data, printer, with_header=with_header)
        except Exception as exc:
            error(self, "Printing failed",
                  f"{exc}\n\nThe report is still saved at:\n{self.pdf_path}")
            return
        q.log_action("report_printed", "job", self.job_id)
        info(self, "Sent to printer", "The report has been sent to the printer.")

    def _open_folder(self) -> None:
        if self.pdf_path:
            snd.open_folder(self.pdf_path)
