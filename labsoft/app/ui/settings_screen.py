"""Settings: everything about the lab that appears on a report."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict

from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QLineEdit, QPlainTextEdit, QScrollArea, QVBoxLayout, QWidget,
)

from .. import config
from ..db import connection, queries as q
from . import style
from .widgets import button, confirm, error, field_label, info, label, row, warn


class SettingsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.editors: Dict[str, QWidget] = {}
        self._build()
        self.reload()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 10)
        outer.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setSpacing(12)

        for group_name, fields in config.SETTINGS_GROUPS:
            box = QGroupBox(group_name)
            form = QFormLayout(box)
            form.setSpacing(8)
            for key, caption in fields:
                if key == "whatsapp_template":
                    editor = QPlainTextEdit()
                    editor.setFixedHeight(110)
                else:
                    editor = QLineEdit()
                self.editors[key] = editor
                form.addRow(caption, editor)
            lay.addWidget(box)

        appearance = QGroupBox("Appearance")
        alay = QVBoxLayout(appearance)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Daylight — white background", "light")
        self.theme_combo.addItem("Night — dark background", "dark")
        self.theme_combo.setMaximumWidth(320)
        self.theme_combo.currentIndexChanged.connect(self._theme_changed)
        alay.addWidget(row(field_label("On-screen theme"), self.theme_combo, None))
        alay.addWidget(label(
            "Changes as soon as you pick it. Reports are always printed on "
            "white — the night theme is for the screen only.", "hint"))
        lay.addWidget(appearance)

        printing = QGroupBox("Printing")
        pform = QVBoxLayout(printing)
        self.header_style_combo = QComboBox()
        self.header_style_combo.addItem("Modern — teal band (new design)", "modern")
        self.header_style_combo.addItem("Classic — plain heading (as before)", "classic")
        self.header_style_combo.setMaximumWidth(320)
        pform.addWidget(row(field_label("Letterhead design"),
                            self.header_style_combo, None))
        self.print_header_check = QCheckBox(
            "Print the letterhead (turn off when using preprinted paper)")
        self.watermark_check = QCheckBox("Print the watermark")
        self.print_flags_check = QCheckBox(
            "Mark abnormal values on the printed report with ↑ and ↓")
        self.specimen_check = QCheckBox(
            "Show the specimen (Serum, Plasma, Whole Blood…) under each heading")
        self.detail_check = QCheckBox(
            "Give long-form tests (HbA1c, TSH…) their own detailed PDF as well")
        self.disclaimer_check = QCheckBox(
            "Print bottom disclaimer note on reports")
        pform.addWidget(self.print_header_check)
        pform.addWidget(self.watermark_check)
        pform.addWidget(self.print_flags_check)
        pform.addWidget(self.specimen_check)
        pform.addWidget(self.detail_check)
        pform.addWidget(self.disclaimer_check)
        pform.addWidget(label(
            "The WhatsApp PDF always includes the letterhead, whatever is set "
            "here — a PDF with a blank top is not a usable document.", "hint"))
        lay.addWidget(printing)

        images = QGroupBox("Images & Logo")
        ilay = QVBoxLayout(images)
        ilay.addWidget(label(
            "Recommended specifications for uploading images:\n"
            "  • Logo: Square or circular badge (PNG with transparent background or JPG/WebP)\n"
            "    Recommended size: 512×512 px to 1024×1024 px (1:1 ratio, 300 DPI)\n"
            "  • Header Banner Photo: Landscape image (PNG/JPG)\n"
            "    Recommended size: 1200×300 px to 1600×400 px (4:1 ratio)\n"
            "  • Signature: Scanned signature on white/transparent background (PNG/JPG)\n"
            "    Recommended size: 400×180 px to 600×250 px\n\n"
            "Uploaded files are automatically saved into the 'assets/' folder.", "hint"))
        ilay.addWidget(row(
            button("Choose logo…", "", lambda: self._pick_image("logo_file")),
            button("Choose header photo…", "", lambda: self._pick_image("header_photo_file")),
            button("Choose signature…", "", lambda: self._pick_image("signature_file")),
            None))
        lay.addWidget(images)

        whatsapp = QGroupBox("WhatsApp")
        wlay = QVBoxLayout(whatsapp)
        self.wa_status = label("", "hint")
        wlay.addWidget(self.wa_status)

        self.auto_attach_check = QCheckBox(
            "Attach the report into WhatsApp automatically")
        wlay.addWidget(self.auto_attach_check)
        wlay.addWidget(label(
            "LabSoft brings WhatsApp to the front and pastes the report in for "
            "you. Pressing Send is always left to you. If another window steals "
            "focus, LabSoft stops rather than pasting into the wrong place.",
            "hint"))
        self.wa_number = QLineEdit()
        self.wa_number.setPlaceholderText("Your own mobile number, to test with")
        self.wa_number.setMaximumWidth(260)
        wlay.addWidget(row(self.wa_number,
                           button("Open a test chat", "", self._test_whatsapp),
                           None))
        wlay.addWidget(label(
            "This opens WhatsApp on that number with a short test message. "
            "Nothing is sent until you press Enter yourself.", "hint"))
        lay.addWidget(whatsapp)

        cloudbox = QGroupBox("Cloud backup")
        clay = QVBoxLayout(cloudbox)
        self.cloud_check = QCheckBox(
            "Also copy every backup to Google Drive (or another synced folder)")
        clay.addWidget(self.cloud_check)
        self.cloud_status = label("", "hint")
        self.cloud_status.setWordWrap(True)
        clay.addWidget(self.cloud_status)
        self.cloud_folder_edit = QLineEdit()
        self.cloud_folder_edit.setPlaceholderText(
            "Leave empty to find Google Drive automatically")
        clay.addWidget(row(self.cloud_folder_edit,
                           button("Choose folder…", "", self._pick_cloud_folder),
                           button("Copy now", "", self._cloud_copy_now)))
        clay.addWidget(label(
            "Install Google Drive for Desktop and LabSoft will find it by itself. "
            "Nothing is uploaded by LabSoft — the copy is put in the Drive "
            "folder and Google syncs it, so this works even with no internet at "
            "the time.", "hint"))
        lay.addWidget(cloudbox)

        staff = QGroupBox("Staff")
        slay = QVBoxLayout(staff)
        self.staff_label = label("", "hint")
        slay.addWidget(self.staff_label)
        slay.addWidget(row(button("Manage staff and permissions", "", self._open_staff),
                           button("Change my PIN", "", self._change_own_pin), None))
        slay.addWidget(label(
            "Each person gets their own username and PIN, and you tick exactly "
            "what they may do. Every report, bill and change is recorded against "
            "the person who made it.", "hint"))
        lay.addWidget(staff)

        backups = QGroupBox("Data and backups")
        blay = QVBoxLayout(backups)
        self.backup_label = label("", "hint")
        blay.addWidget(self.backup_label)
        blay.addWidget(row(button("Back up now", "", self._backup_now),
                           button("Restore from a backup…", "", self._restore),
                           button("Open data folder", "", self._open_data), None))
        lay.addWidget(backups)

        lay.addStretch(1)
        scroll.setWidget(host)
        outer.addWidget(scroll, 1)

        self.saved_note = label("", "ok")
        outer.addWidget(row(button("Reload", "", self.reload),
                            None,
                            self.saved_note, 8,
                            button("Save settings", "primary", self.save)))

    # ------------------------------------------------------------------ data
    @staticmethod
    def _select(combo: QComboBox, value: str, fallback: str) -> None:
        i = combo.findData(value)
        combo.setCurrentIndex(i if i >= 0 else max(0, combo.findData(fallback)))

    def _theme_changed(self) -> None:
        """Switch theme the moment it is picked, and remember it.

        Saved on its own rather than waiting for Save, because a theme you have
        to save before you can see is a theme nobody tries.
        """
        theme = self.theme_combo.currentData() or "light"
        app = QApplication.instance()
        if app is not None:
            style.apply_theme(app, theme)
        q.set_settings({"theme": theme})

    def reload(self) -> None:
        values = q.all_settings()
        for key, editor in self.editors.items():
            text = values.get(key, "")
            if isinstance(editor, QPlainTextEdit):
                editor.setPlainText(text)
            else:
                editor.setText(text)
        self.print_header_check.setChecked(q.setting_bool("print_header"))
        self.watermark_check.setChecked(q.setting_bool("watermark"))
        self.print_flags_check.setChecked(q.setting_bool("print_flags"))
        self.specimen_check.setChecked(q.setting_bool("print_specimen"))
        self.detail_check.setChecked(q.setting_bool("separate_detail_reports"))
        self.disclaimer_check.setChecked(q.setting_bool("print_disclaimer"))
        self._select(self.header_style_combo,
                     (q.get_setting("header_style") or "modern").lower(), "modern")
        self.theme_combo.blockSignals(True)
        self._select(self.theme_combo,
                     style.normalise_theme(q.get_setting("theme")), "light")
        self.theme_combo.blockSignals(False)
        self.auto_attach_check.setChecked(q.setting_bool("auto_attach"))
        self.cloud_check.setChecked(q.setting_bool("cloud_backup"))
        self.cloud_folder_edit.setText(q.get_setting("cloud_folder"))
        self.cloud_status.setText(self._cloud_message())

        self.wa_status.setText(self._whatsapp_status())

        from ..core import auth
        n = len(q.list_users(include_inactive=True))
        me = auth.current()
        self.staff_label.setText(
            f"{n} account{'s' if n != 1 else ''}."
            + (f"   Signed in as {me.label}." if me else
               "   Nobody is signed in — LabSoft is running without accounts."))

        last = connection.last_backup_time()
        self.backup_label.setText(
            f"Data file: {config.db_path()}\n"
            f"Last backup: {last.strftime('%d-%m-%Y %H:%M') if last else 'none yet'}"
            f"   ·   {len(connection.list_backups())} kept")
        self.saved_note.setText("")

    def collect(self) -> Dict[str, str]:
        """Read the form. Separate from save() so it can be checked on its own."""
        values = {}
        for key, editor in self.editors.items():
            values[key] = (editor.toPlainText() if isinstance(editor, QPlainTextEdit)
                           else editor.text())
        values["print_header"] = "1" if self.print_header_check.isChecked() else "0"
        values["watermark"] = "1" if self.watermark_check.isChecked() else "0"
        values["print_flags"] = "1" if self.print_flags_check.isChecked() else "0"
        values["print_specimen"] = "1" if self.specimen_check.isChecked() else "0"
        values["separate_detail_reports"] = (
            "1" if self.detail_check.isChecked() else "0")
        values["print_disclaimer"] = "1" if self.disclaimer_check.isChecked() else "0"
        values["header_style"] = self.header_style_combo.currentData() or "modern"
        values["theme"] = self.theme_combo.currentData() or "light"
        values["auto_attach"] = "1" if self.auto_attach_check.isChecked() else "0"
        values["cloud_backup"] = "1" if self.cloud_check.isChecked() else "0"
        values["cloud_folder"] = self.cloud_folder_edit.text().strip()
        return values

    def validate(self, values: Dict[str, str]) -> str:
        """Return a message describing the first problem, or '' when fine.

        Kept apart from save() so the rules can be tested without a dialog box
        standing in the way.
        """
        from ..core import numbering

        number = values.get("next_report_no", "").strip()
        if number and numbering.normalise(number) is None:
            return ("The next report number must be a whole number, like 51359.\n\n"
                    f"'{number}' cannot be used.")
        if not values.get("lab_name", "").strip():
            return "The laboratory name cannot be empty — it prints on every report."

        mode = values.get("whatsapp_mode", "").strip().lower()
        if mode and mode not in ("auto", "desktop", "web"):
            return (f"'{mode}' is not a way of opening WhatsApp.\n\n"
                    "Use one of: auto, desktop, web.")

        code = values.get("country_code", "").strip()
        if code and not code.isdigit():
            return f"The country code must be digits only, like 91. '{code}' is not."
        return ""

    def save(self) -> bool:
        values = self.collect()
        problem = self.validate(values)
        if problem:
            warn(self, "Settings not saved", problem)
            return False

        q.set_settings(values)
        self.saved_note.setText("Settings saved")
        self.saved_note.setStyleSheet(f"color: {style.GREEN}; font-weight: 600;")
        return True

    # ----------------------------------------------------------------- staff
    def _open_staff(self) -> None:
        from ..core import auth
        from .users_dialog import UsersDialog

        if not auth.can(auth.P_USERS):
            warn(self, "Not allowed",
                 "Only an administrator can add or change staff accounts.")
            return
        UsersDialog(self).exec()
        self.reload()

    def _change_own_pin(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        from ..core import auth

        me = auth.current()
        if not me:
            warn(self, "Nobody is signed in",
                 "There are no accounts yet, so there is no PIN to change.\n\n"
                 "Use “Manage staff and permissions” to create the first one.")
            return
        pin, ok = QInputDialog.getText(self, "Change my PIN", "New PIN:",
                                       QLineEdit.EchoMode.Password)
        if not ok:
            return
        try:
            q.set_user_pin(me.id, pin)
        except auth.PinError as exc:
            warn(self, "PIN not changed", str(exc))
            return
        info(self, "PIN changed", "Use the new PIN next time you sign in.")

    # ----------------------------------------------------------------- cloud
    def _cloud_message(self) -> str:
        from ..output import cloud

        status = cloud.resolve(self.cloud_folder_edit.text().strip()
                               if hasattr(self, "cloud_folder_edit") else "")
        last = q.get_setting("cloud_last_copy")
        if not status.available:
            return status.detail
        folder = cloud.target_dir(status, q.get_setting("lab_name"))
        copies = len(cloud.list_copies(folder)) if folder else 0
        line = f"{status.provider} found.  Backups go to: {folder}"
        line += f"\n{copies} cop{'y' if copies == 1 else 'ies'} there now."
        if last:
            line += f"   Last copied {last}."
        return line

    def _pick_cloud_folder(self) -> None:
        start = self.cloud_folder_edit.text().strip() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(
            self, "Choose the folder to keep cloud backups in", start)
        if chosen:
            self.cloud_folder_edit.setText(chosen)
            self.cloud_status.setText(self._cloud_message())

    def _cloud_copy_now(self) -> None:
        from ..output import cloud

        backups = connection.list_backups()
        if not backups:
            warn(self, "No backup yet",
                 "There is nothing to copy. Click “Back up now” first.")
            return
        status = cloud.copy_backup(
            backups[0], configured=self.cloud_folder_edit.text().strip(),
            lab_name=q.get_setting("lab_name"))
        self.cloud_status.setText(self._cloud_message())
        if status.available:
            info(self, "Copied to the cloud folder",
                 f"{status.detail}\n\nGoogle Drive will upload it by itself the "
                 f"next time this computer is online.")
        else:
            warn(self, "Could not copy", status.detail)

    # -------------------------------------------------------------- whatsapp
    def _whatsapp_status(self) -> str:
        from ..output import sender

        if sender.desktop_app_available():
            return "WhatsApp Desktop is installed — reports will open in the app."
        import platform

        if platform.system() != "Windows":
            return "Not running on Windows; reports will open in WhatsApp Web."
        return ("WhatsApp Desktop was not found on this PC — reports will open "
                "in WhatsApp Web in your browser instead.")

    def _test_whatsapp(self) -> None:
        from ..output import sender

        number = self.wa_number.text().strip()
        if not sender.normalise_phone(number, self.editors["country_code"].text()):
            warn(self, "Number needed",
                 "Type a complete mobile number to test with, such as your own.")
            return

        mode = (self.editors["whatsapp_mode"].text().strip().lower() or "auto")
        if mode not in ("auto", "desktop", "web"):
            warn(self, "Setting not understood",
                 "'Open using' must be auto, desktop or web.")
            return

        try:
            # open_chat, not send: this must not put anything on the clipboard.
            result = sender.open_chat(
                number, "LabSoft test message — please ignore.",
                self.editors["country_code"].text(), mode)
        except sender.SendError as exc:
            error(self, "WhatsApp did not open", str(exc))
            return

        info(self, "WhatsApp opened",
             f"{result.manual_step}\n\nNothing has been sent — press Enter in "
             f"WhatsApp yourself if you want to send the test message.\n\n"
             f"If nothing appeared, set 'Open using' to web and try again.")

    # ---------------------------------------------------------------- images
    def _pick_image(self, key: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose an image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            return
        src = Path(path)
        dest = config.assets_dir() / src.name
        try:
            if src.resolve() != dest.resolve():
                shutil.copy2(src, dest)
        except OSError as exc:
            error(self, "Could not copy the image", str(exc))
            return
        self.editors[key].setText(dest.name)
        self.save()
        info(self, "Image set",
             f"{dest.name} will be used from the next report onwards.")

    # --------------------------------------------------------------- backups
    def _backup_now(self) -> None:
        try:
            path = connection.backup_now()
        except OSError as exc:
            error(self, "Backup failed", str(exc))
            return
        self.reload()
        info(self, "Backed up", f"A copy has been saved as:\n{path.name}")

    def _restore(self) -> None:
        backups = connection.list_backups()
        if not backups:
            warn(self, "No backups", "There are no backups to restore from yet.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a backup to restore", str(config.backup_dir()),
            "Database (*.db)")
        if not path:
            return
        if not confirm(
                self, "Restore this backup?",
                f"Everything currently in LabSoft will be replaced by the "
                f"contents of:\n\n{Path(path).name}\n\n"
                f"Your current data is saved first, so this can be undone.\n\n"
                f"LabSoft will need to be restarted afterwards.", "Restore"):
            return
        try:
            connection.restore_from(Path(path))
        except Exception as exc:
            error(self, "Restore failed", str(exc))
            return
        info(self, "Restored",
             "The backup has been restored. Please close and reopen LabSoft.")

    def _open_data(self) -> None:
        from ..output import sender

        sender.open_folder(config.db_path())

