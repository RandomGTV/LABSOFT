"""The application shell."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import QLabel, QMainWindow, QStatusBar, QTabWidget

from .. import config
from ..core import auth
from ..db import connection, queries as q
from . import style
from .billing_screen import BillingScreen
from .doctors_screen import DoctorsScreen
from .job_screen import JobScreen
from .patients_screen import PatientsScreen
from .queue_screen import QueueScreen
from .settings_screen import SettingsScreen
from .staff_screen import StaffScreen
from .summaries_screen import SummariesScreen
from .tests_screen import TestsScreen
from .widgets import error, info

TAB_JOB = 0
TAB_QUEUE = 1


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        lab = (q.get_setting("lab_name_prefix") + " " + q.get_setting("lab_name")).strip()
        self.setWindowTitle(f"LabSoft — {lab}")
        self.resize(1180, 820)

        self.tabs = QTabWidget()
        self.job_screen = JobScreen()
        self.queue_screen = QueueScreen()
        self.patients_screen = PatientsScreen()
        self.doctors_screen = DoctorsScreen()
        self.tests_screen = TestsScreen()
        self.billing_screen = BillingScreen()
        self.summaries_screen = SummariesScreen()
        self.staff_screen = StaffScreen()
        self.settings_screen = SettingsScreen()

        # Tabs a person cannot use are not shown at all. A greyed-out tab is an
        # invitation to ask why; an absent one is simply not their job.
        self.tabs.addTab(self.job_screen, "Job")
        self.tabs.addTab(self.queue_screen, "Work Queue")
        self.tabs.addTab(self.patients_screen, "Patients")
        self.tabs.addTab(self.doctors_screen, "Doctors")
        if auth.can(auth.P_TESTS):
            self.tabs.addTab(self.tests_screen, "Tests")
        if auth.can(auth.P_MONEY):
            self.tabs.addTab(self.billing_screen, "Billing")
            self.tabs.addTab(self.summaries_screen, "Summaries")
        if auth.can(auth.P_USERS):
            self.tabs.addTab(self.staff_screen, "Staff")
        if auth.can(auth.P_SETTINGS) or auth.can(auth.P_USERS):
            self.tabs.addTab(self.settings_screen, "Settings")
        self.tabs.currentChanged.connect(self._tab_changed)
        self.setCentralWidget(self.tabs)

        self.job_screen.job_changed.connect(self.queue_screen.refresh)
        self.job_screen.job_changed.connect(self._refresh_status)
        self.job_screen.request_send.connect(self._send)
        self.queue_screen.open_job.connect(self._open_job)
        self.queue_screen.preview_job.connect(lambda j: self.preview(j))
        self.patients_screen.open_job.connect(self._open_job)
        self.patients_screen.preview_job.connect(lambda j: self.preview(j))
        self.job_screen.request_preview.connect(lambda j: self.preview(j))
        self.queue_screen.send_job.connect(self._send)

        self._build_status_bar()
        self._build_shortcuts()
        self._refresh_status()

        self._ticker = QTimer(self)
        self._ticker.setInterval(60_000)   # keeps the overdue count honest
        self._ticker.timeout.connect(self._refresh_status)
        self._ticker.start()

    # ------------------------------------------------------------ furniture
    def _build_status_bar(self) -> None:
        bar = QStatusBar()
        self.count_label = QLabel("")
        self.backup_label = QLabel("")
        bar.addWidget(self.count_label, 1)
        user = auth.current()
        if user:
            self.who_label = QLabel(f"  {user.label}  ")
            self.who_label.setStyleSheet(
                f"color: {style.BRAND}; font-weight: 700;")
            bar.addPermanentWidget(self.who_label)
            sign_out = QLabel('<a href="#" style="color:%s">Sign out</a>' % style.BRAND)
            sign_out.setOpenExternalLinks(False)
            sign_out.linkActivated.connect(self._sign_out)
            bar.addPermanentWidget(sign_out)
        bar.addPermanentWidget(self.backup_label)
        about_link = QLabel('<a href="#" style="color:%s; text-decoration:none; font-weight:600;">ⓘ About</a>' % style.BRAND)
        about_link.setOpenExternalLinks(False)
        about_link.linkActivated.connect(self._show_about)
        bar.addPermanentWidget(about_link)
        self.setStatusBar(bar)

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence("F1"), self, activated=self._show_about)
        QShortcut(QKeySequence("F2"), self, activated=self._new_job)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._focus_search)
        QShortcut(QKeySequence("F5"), self, activated=self._refresh_all)
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self.tabs.setCurrentIndex(0))
        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self.tabs.setCurrentIndex(1))

    def _show_about(self) -> None:
        from .about_dialog import AboutDialog

        AboutDialog(self).exec()

    def _refresh_status(self) -> None:
        c = q.queue_counts()
        parts = [f"Today: {c['today']}", f"Pending results: {c['pending']}",
                 f"Ready to send: {c['ready']}"]
        if c["overdue"]:
            parts.append(f"Overdue: {c['overdue']}")
        self.count_label.setText("      ".join(parts))
        self.count_label.setStyleSheet(
            f"color: {style.RED}; font-weight: 700;" if c["overdue"] else "")

        last = connection.last_backup_time()
        if last:
            self.backup_label.setText(f"Backup: {last:%d-%m %H:%M} ✓")
            self.backup_label.setStyleSheet("")
        else:
            # A silent backup failure is exactly the thing that is only noticed
            # on the day it matters, so it is stated plainly here.
            self.backup_label.setText("Backup: none yet")
            self.backup_label.setStyleSheet(f"color: {style.AMBER}; font-weight: 700;")

    def _sign_out(self) -> None:
        from .widgets import confirm

        if not confirm(self, "Sign out?",
                       "LabSoft will close and ask for a PIN again.\n\n"
                       "Anything already typed has been saved.", "Sign out"):
            return
        q.log_action("signed_out", "user", (auth.current() or auth.User()).id)
        auth.set_current(None)
        self.close()

    # -------------------------------------------------------------- actions
    def _tab_changed(self, index: int) -> None:
        widget = self.tabs.widget(index)
        if hasattr(widget, "refresh"):
            widget.refresh()
        self._refresh_status()

    def _new_job(self) -> None:
        self.tabs.setCurrentIndex(TAB_JOB)
        self.job_screen.new_job()

    def _focus_search(self) -> None:
        """Ctrl+F searches the screen you are looking at.

        It used to jump to the work queue wherever you were, which meant
        pressing it on the Patients list threw away what you were doing.
        """
        here = self.tabs.currentWidget()
        box = getattr(here, "search", None)
        if box is None:
            self.tabs.setCurrentIndex(TAB_QUEUE)
            box = self.queue_screen.search
        box.setFocus()
        box.selectAll()

    def _refresh_all(self) -> None:
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if hasattr(w, "refresh"):
                w.refresh()
        self._refresh_status()

    def _open_job(self, job_id: int) -> None:
        self.tabs.setCurrentIndex(TAB_JOB)
        self.job_screen.load_job(job_id)

    def _send(self, job_id: int) -> None:
        from .send_dialog import SendDialog

        # Show the report first when asked to. Once it is sent the patient has
        # it, so this is the last moment anything can be checked.
        if q.setting_bool("preview_before_send"):
            if not self.preview(job_id, allow_send=True):
                return

        SendDialog(job_id, self).exec()
        self.queue_screen.refresh()
        self._refresh_status()

    def preview(self, job_id: int, allow_send: bool = False) -> bool:
        """Open the preview. Returns True when the operator chose to continue."""
        from .preview_dialog import PreviewDialog

        dlg = PreviewDialog(job_id, self, allow_send=allow_send)
        dlg.exec()
        return bool(dlg.send_requested) if allow_send else False

    def closeEvent(self, event) -> None:
        try:
            connection.close()
        finally:
            super().closeEvent(event)
