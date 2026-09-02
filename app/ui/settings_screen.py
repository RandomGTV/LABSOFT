"""Settings: everything about the lab that appears on a report.

Nine sections down a rail on the left, one of them shown at a time. It was
one scrolling column of nine boxed groups and about sixty fields, which meant
finding "Back up now" involved scrolling past the whole letterhead.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QLineEdit, QListWidget, QPlainTextEdit, QScrollArea,
    QStackedWidget, QVBoxLayout, QWidget,
)

from .. import config
from ..db import connection, queries as q
from . import style
from .widgets import button, confirm, error, field_label, info, label, row, warn


#: One label column for every group on the page.
LABEL_W = 168


class SettingsScreen(QWidget):
    #: raised after Save, so the shell can re-read the laboratory's name
    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.editors: Dict[str, QWidget] = {}
        self._build()
        self.reload()

    def _build(self) -> None:
        """A rail of sections on the left, one section at a time on the right.

        Settings used to be every group stacked into one scrolling column --
        nine cards and about sixty fields, with the only way to reach the
        backup buttons being to scroll past all of it. The same content is
        here; it is just no longer all on screen at once.
        """
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        head = QFrame()
        head.setObjectName("filterBar")
        hl = QVBoxLayout(head)
        hl.setContentsMargins(24, 16, 24, 14)
        hl.setSpacing(3)
        hl.addWidget(label("Settings", "h1"))
        hl.addWidget(label(
            "The laboratory's own details, how the report prints, and where "
            "backups go. Changes take effect on the next report.", "hint"))
        outer.addWidget(head)

        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self.rail = QListWidget()
        self.rail.setObjectName("settingsRail")
        self.rail.setFixedWidth(232)
        self.rail.setAccessibleName("Settings sections")
        bl.addWidget(self.rail)

        self.pages = QStackedWidget()
        bl.addWidget(self.pages, 1)
        outer.addWidget(body, 1)

        for title, blurb, build in (
                ("Laboratory", "The name, address and phone line that print "
                 "at the top of every report.", self._page_laboratory),
                ("Signatories", "Who signs the report, and what goes under "
                 "each name.", self._page_signatories),
                ("Report layout", "What the printed page carries, and how "
                 "the letterhead is drawn.", self._page_report),
                ("Images", "The logo, the header photo, the watermark and "
                 "the signature.", self._page_images),
                ("Numbering", "Where the report numbers carry on from.",
                 self._page_numbering),
                ("WhatsApp", "How reports reach the patient, and the message "
                 "that goes with them.", self._page_whatsapp),
                ("Backups", "Where the data lives, and the copies of it.",
                 self._page_backups),
                ("Staff", "Who may sign in, and what each of them may do.",
                 self._page_staff),
                ("Appearance", "How LabSoft looks on this screen.",
                 self._page_appearance)):
            self.rail.addItem(title)
            self.pages.addWidget(self._section(title, blurb, build))
        self.rail.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.rail.setCurrentRow(0)

        foot = QFrame()
        foot.setObjectName("footBar")
        foot.setFixedHeight(56)
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(24, 0, 24, 0)
        fl.setSpacing(9)
        self.saved_note = label("", "ok")
        fl.addWidget(label("Nothing is saved until you press Save", "foot"))
        fl.addStretch(1)
        fl.addWidget(self.saved_note)
        fl.addWidget(button("Reload", "", self.reload))
        fl.addWidget(button("Save settings", "primary", self.save))
        outer.addWidget(foot)

    # ---------------------------------------------------------------- pieces
    def _section(self, title: str, blurb: str, build) -> QWidget:
        """One section: its heading, one line saying what it is for, and a
        scrolling body. Every section is built the same way, so they cannot
        drift apart the way nine hand-laid group boxes did."""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 22, 28, 10)
        lay.setSpacing(3)
        lay.addWidget(label(title, "h1"))
        note = label(blurb, "hint")
        note.setWordWrap(True)
        lay.addWidget(note)
        lay.addSpacing(16)

        host = QWidget()
        host.setObjectName("settingsHost")
        inner = QVBoxLayout(host)
        inner.setContentsMargins(0, 0, 14, 0)
        inner.setSpacing(14)
        build(inner)
        inner.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setWidget(host)
        lay.addWidget(scroll, 1)
        return page

    def _fields(self, into, keys) -> None:
        """A block of plain text settings, one per row, in one label column."""
        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        for key, caption in keys:
            if key == "whatsapp_template":
                editor = QPlainTextEdit()
                editor.setTabChangesFocus(True)
                editor.setFixedHeight(104)
            else:
                editor = QLineEdit()
                editor.setMaximumWidth(520)
            self.editors[key] = editor
            cap = field_label(caption)
            cap.setFixedWidth(LABEL_W)
            cap.setBuddy(editor)
            editor.setAccessibleName(caption)
            form.addRow(cap, editor)
        into.addLayout(form)

    @staticmethod
    def _group(keys):
        return dict(config.SETTINGS_GROUPS)[keys]

    def _explain(self, into, text: str) -> None:
        note = label(text, "hint")
        note.setWordWrap(True)
        into.addWidget(note)

    # ----------------------------------------------------------------- pages
    def _page_laboratory(self, into) -> None:
        self._fields(into, self._group("Laboratory"))
        self._explain(into,
                      "The prefix and the name are printed together at the top "
                      "of the letterhead — “New” and “MITHRA” read as “New "
                      "MITHRA”.")

    def _page_signatories(self, into) -> None:
        self._fields(into, self._group("Signatories"))
        self._explain(into,
                      "Up to three signatures print across the foot of the "
                      "report. Leave the middle one empty for two.")

    def _page_report(self, into) -> None:
        letter = QHBoxLayout()
        letter.setSpacing(10)
        self.header_style_combo = QComboBox()
        self.header_style_combo.addItem("Modern — navy band", "modern")
        self.header_style_combo.addItem("Classic — plain heading", "classic")
        self.header_style_combo.setMaximumWidth(320)
        self.header_style_combo.setAccessibleName("Letterhead design")
        cap = field_label("Letterhead design")
        cap.setFixedWidth(LABEL_W)
        cap.setBuddy(self.header_style_combo)
        letter.addWidget(cap)
        letter.addWidget(self.header_style_combo)
        letter.addStretch(1)
        into.addLayout(letter)

        self.print_header_check = QCheckBox(
            "Print the letterhead (turn off when using preprinted paper)")
        self.watermark_check = QCheckBox("Print the watermark behind the results")
        self.print_flags_check = QCheckBox(
            "Mark abnormal values with ↑ and ↓")
        self.specimen_check = QCheckBox(
            "Show the specimen (Serum, Plasma, Whole Blood…) under each heading")
        self.detail_check = QCheckBox(
            "Give long-form tests (HbA1c, TSH…) their own detailed PDF as well")
        self.disclaimer_check = QCheckBox("Print the disclaimer at the bottom")
        for box in (self.print_header_check, self.watermark_check,
                    self.print_flags_check, self.specimen_check,
                    self.detail_check, self.disclaimer_check):
            into.addWidget(box)

        self._explain(into,
                      "The WhatsApp PDF always includes the letterhead, whatever "
                      "is set here — a PDF with a blank top is not a usable "
                      "document.")
        self._fields(into, self._group("Report & Letterhead"))

    def _page_images(self, into) -> None:
        self.image_rows = {}
        for key, caption, advice in (
                ("logo_file", "Logo",
                 "Square badge, 512×512 to 1024×1024, PNG with a clear background."),
                ("header_photo_file", "Header photo",
                 "Landscape banner, about 1200×300, 4:1."),
                ("watermark_file", "Watermark",
                 "Printed very pale behind the results. Leave it empty to use "
                 "the logo instead."),
                ("signature_file", "Signature",
                 "Scanned on white or transparent, about 400×180.")):
            card = QFrame()
            card.setObjectName("imageCard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 13, 16, 13)
            cl.setSpacing(5)
            cl.addWidget(label(caption, "group"))
            shown = label("", "hint")
            shown.setWordWrap(True)
            self.image_rows[key] = shown
            cl.addWidget(shown)
            cl.addWidget(label(advice, "hint"))
            cl.addWidget(row(
                button(f"Choose {caption.lower()}…", "",
                       lambda _c=False, k=key: self._pick_image(k)),
                button("Remove", "quiet", lambda _c=False, k=key: self._clear_image(k)),
                None))
            into.addWidget(card)
        self._explain(into,
                      "Whatever you choose is copied into the assets folder "
                      "beside LabSoft, so the report still finds it if the "
                      "original is moved or deleted.")

    def _page_numbering(self, into) -> None:
        self._fields(into, self._group("Numbering"))
        self._explain(into,
                      "The next job registered takes this number, and it counts "
                      "up from there. Set it once, when moving over from a "
                      "register or from other software.")

    def _page_whatsapp(self, into) -> None:
        self.wa_status = label("", "hint")
        self.wa_status.setWordWrap(True)
        into.addWidget(self.wa_status)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        self.wa_mode_combo = QComboBox()
        # A list, not a text box that had to be typed as "auto", "desktop" or
        # "web" and was rejected on Save when it was not one of the three.
        self.wa_mode_combo.addItem("The WhatsApp app (attaches the report)", "desktop")
        self.wa_mode_combo.addItem("The app if it is installed, else the browser", "auto")
        self.wa_mode_combo.addItem("The browser only (message, no report)", "web")
        self.wa_mode_combo.setMaximumWidth(380)
        self.wa_mode_combo.setAccessibleName("Open WhatsApp in")
        cap = field_label("Open WhatsApp in")
        cap.setFixedWidth(LABEL_W)
        cap.setBuddy(self.wa_mode_combo)
        mode_row.addWidget(cap)
        mode_row.addWidget(self.wa_mode_combo)
        mode_row.addStretch(1)
        into.addLayout(mode_row)

        self.auto_attach_check = QCheckBox(
            "Attach the report into WhatsApp automatically")
        into.addWidget(self.auto_attach_check)
        self._explain(into,
                      "LabSoft brings WhatsApp to the front and pastes the "
                      "report in for you. Pressing Send is always left to you. "
                      "If another window steals focus, LabSoft stops rather "
                      "than pasting into the wrong place. This only works with "
                      "the WhatsApp application — a browser will not take a "
                      "file from LabSoft.")

        self._fields(into, [(k, c) for k, c in self._group("WhatsApp")
                            if k != "whatsapp_mode"])

        self.wa_number = QLineEdit()
        self.wa_number.setPlaceholderText("Your own mobile number, to test with")
        self.wa_number.setFixedWidth(320)
        self.wa_number.setAccessibleName("Number to test with")
        into.addWidget(row(self.wa_number,
                           button("Open a test chat", "", self._test_whatsapp),
                           None))
        self._explain(into,
                      "This opens WhatsApp on that number with a short test "
                      "message. Nothing is sent until you press Enter yourself.")

    def _page_backups(self, into) -> None:
        self.backup_label = label("", "hint")
        self.backup_label.setWordWrap(True)
        into.addWidget(self.backup_label)
        into.addWidget(row(button("Back up now", "primary", self._backup_now),
                           button("Restore from a backup…", "", self._restore),
                           button("Open data folder", "", self._open_data), None))

        card = QFrame()
        card.setObjectName("imageCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 13, 16, 13)
        cl.setSpacing(7)
        cl.addWidget(label("Cloud copy", "group"))
        self.cloud_check = QCheckBox(
            "Also copy every backup to Google Drive (or another synced folder)")
        cl.addWidget(self.cloud_check)
        self.cloud_status = label("", "hint")
        self.cloud_status.setWordWrap(True)
        cl.addWidget(self.cloud_status)
        self.cloud_folder_edit = QLineEdit()
        self.cloud_folder_edit.setPlaceholderText(
            "Leave empty to find Google Drive automatically")
        self.cloud_folder_edit.setAccessibleName("Cloud backup folder")
        cl.addWidget(row(self.cloud_folder_edit,
                         button("Choose folder…", "", self._pick_cloud_folder),
                         button("Copy now", "", self._cloud_copy_now)))
        cl.addWidget(label(
            "Install Google Drive for Desktop and LabSoft will find it by "
            "itself. Nothing is uploaded by LabSoft — the copy is put in the "
            "Drive folder and Google syncs it, so this works even with no "
            "internet at the time.", "hint"))
        into.addWidget(card)

    def _page_staff(self, into) -> None:
        self.staff_label = label("", "hint")
        self.staff_label.setWordWrap(True)
        into.addWidget(self.staff_label)
        into.addWidget(row(
            button("Manage staff and permissions", "primary", self._open_staff),
            button("Change my PIN", "", self._change_own_pin), None))
        self._explain(into,
                      "Each person gets their own username and PIN, and you "
                      "tick exactly what they may do. Every report, bill and "
                      "change is recorded against the person who made it.")

    def _page_appearance(self, into) -> None:
        theme_row = QHBoxLayout()
        theme_row.setSpacing(10)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Daylight — white background", "light")
        self.theme_combo.addItem("Night — dark background", "dark")
        self.theme_combo.setMaximumWidth(320)
        self.theme_combo.setAccessibleName("On-screen theme")
        self.theme_combo.currentIndexChanged.connect(self._theme_changed)
        cap = field_label("On-screen theme")
        cap.setFixedWidth(LABEL_W)
        cap.setBuddy(self.theme_combo)
        theme_row.addWidget(cap)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch(1)
        into.addLayout(theme_row)
        self._explain(into,
                      "Changes as soon as you pick it. Reports are always "
                      "printed on white — the night theme is for the screen "
                      "only.")

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
        self._select(self.wa_mode_combo,
                     (q.get_setting("whatsapp_mode") or "desktop").lower(),
                     "desktop")
        self.auto_attach_check.setChecked(q.setting_bool("auto_attach"))
        for key, shown in self.image_rows.items():
            name = (q.get_setting(key) or "").strip()
            here = (config.assets_dir() / name) if name else None
            missing = bool(name) and not (here and here.exists())
            shown.setText(
                f"{name}  ·  in the assets folder" if name and not missing
                else (f"{name}  ·  this file is not in the assets folder"
                      if name else "None chosen"))
            shown.setProperty("missing", "true" if missing else "false")
            shown.style().unpolish(shown)
            shown.style().polish(shown)
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
        values["whatsapp_mode"] = self.wa_mode_combo.currentData() or "desktop"
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
        # The Settings tab is also shown to whoever manages staff, so this is
        # the check that keeps them out of the letterhead, the signatories and
        # the report numbering.
        from ..core import auth

        if not auth.can(auth.P_SETTINGS):
            warn(self, "Not allowed",
                 "Changing the laboratory's settings needs the settings "
                 "permission. An administrator can grant it under Staff.")
            return False
        values = self.collect()
        problem = self.validate(values)
        if problem:
            warn(self, "Settings not saved", problem)
            return False

        q.set_settings(values)
        # The window title and the bar carry the laboratory's name and were
        # read once, at startup. Changing it under Settings put the new name
        # on every report and left the old one on the screen.
        self.settings_saved.emit()
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
            return ("The WhatsApp application is installed on this PC. Reports "
                    "will open in it with the PDF ready to attach.")
        import platform

        if platform.system() != "Windows":
            return ("This is not a Windows PC, so the WhatsApp application "
                    "cannot be opened from here.")
        return ("The WhatsApp application was not found on this PC. Install "
                "WhatsApp for Windows and sign in once — until then a report "
                "cannot be attached, because a browser will not take a file "
                "from LabSoft.")

    def _test_whatsapp(self) -> None:
        from ..output import sender

        number = self.wa_number.text().strip()
        if not sender.normalise_phone(number, self.editors["country_code"].text()):
            warn(self, "Number needed",
                 "Type a complete mobile number to test with, such as your own.")
            return

        mode = self.wa_mode_combo.currentData() or "desktop"

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
             f"If nothing appeared, the WhatsApp application is probably not "
             f"installed — choose the browser above and try again.")

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
        q.set_settings({key: dest.name})
        self.reload()
        info(self, "Image set",
             f"{dest.name} will be used from the next report onwards.")

    def _clear_image(self, key: str) -> None:
        """Unset an image without deleting the file it points at."""
        q.set_settings({key: ""})
        self.reload()

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
        # A restore replaces the users table along with everything else, so
        # whoever can do it can hand themselves an administrator account by
        # bringing their own lab.db on a USB stick. It is a delete-grade act
        # and it is confined to this PC's own backup folder.
        from ..core import auth

        if not auth.can(auth.P_DELETE):
            warn(self, "Not allowed",
                 "Restoring a backup replaces everything in LabSoft, including "
                 "the staff accounts. It needs the delete permission, which an "
                 "administrator can grant under Staff.")
            return
        backups = connection.list_backups()
        if not backups:
            warn(self, "No backups", "There are no backups to restore from yet.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a backup to restore", str(config.backup_dir()),
            "Database (*.db)")
        if not path:
            return
        chosen = Path(path).resolve()
        if chosen.parent != config.backup_dir().resolve():
            warn(self, "Not a LabSoft backup",
                 f"Only a backup LabSoft made itself can be restored, and those "
                 f"live in:\n{config.backup_dir()}\n\nThe file you picked is "
                 f"somewhere else, so it has not been opened.")
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

