"""The application shell: the ink bar, the tab strip, and the status line.

Drawn to artboard 01 of the LabSoft 2026 canvas. Nothing here carries a
colour of its own -- every surface is named in ``style.stylesheet_for`` so a
theme change repaints the shell along with everything inside it.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .. import config
from ..core import auth
from ..db import connection, queries as q
from . import icons, style
from .analytics_screen import AnalyticsScreen
from .billing_screen import BillingScreen
from .doctors_screen import DoctorsScreen
from .job_screen import JobScreen
from .patients_screen import PatientsScreen
from .queue_screen import QueueScreen
from .settings_screen import SettingsScreen
from .staff_screen import StaffScreen
from .summaries_screen import SummariesScreen
from .tests_screen import TestsScreen
from .widgets import TabDeck, elevate, name_fields


TAB_JOB = 0
TAB_QUEUE = 1


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.was_signed_out = False
        lab = (q.get_setting("lab_name_prefix") + " " + q.get_setting("lab_name")).strip()
        self.setWindowTitle(f"LabSoft — {lab}")
        self.resize(1220, 840)

        # Central container holding Top Brand Bar + Modern Tabs
        central = QWidget()
        central_lay = QVBoxLayout(central)
        central_lay.setContentsMargins(0, 0, 0, 0)
        central_lay.setSpacing(0)

        central_lay.addWidget(elevate(self._build_app_bar(lab), 2))

        self.tabs = TabDeck()
        self.tabs.setDocumentMode(True)
        self.job_screen = JobScreen()
        self.queue_screen = QueueScreen()
        self.patients_screen = PatientsScreen()
        self.doctors_screen = DoctorsScreen()
        self.tests_screen = TestsScreen()
        self.billing_screen = BillingScreen()
        self.analytics_screen = AnalyticsScreen()
        self.summaries_screen = SummariesScreen()
        self.staff_screen = StaffScreen()
        self.settings_screen = SettingsScreen()

        # Every field on every screen takes the name of the caption printed
        # beside it, so a screen reader says "Mobile, edit" rather than
        # "edit". Done here, once, rather than at fifty call sites.
        for screen in (self.job_screen, self.queue_screen, self.patients_screen,
                       self.doctors_screen, self.tests_screen,
                       self.billing_screen, self.analytics_screen,
                       self.summaries_screen, self.staff_screen,
                       self.settings_screen):
            name_fields(screen)

        # Numbered and iconed, the way the web application labels them, so
        # that "go to 05" means the same thing on either. Tabs a person
        # cannot use are not shown at all.
        self._add_tab(self.job_screen, "job", "01. Job")
        self._add_tab(self.queue_screen, "queue", "02. Work Queue")
        self._add_tab(self.patients_screen, "patients", "03. Patients")
        # Doctors stays visible to everyone: reception has to see who referred
        # a patient in order to pick them on a job. What is gated is CHANGING
        # one -- a commission rate is money -- and that check lives on the
        # buttons in doctors_screen, which is where it belongs.
        self._add_tab(self.doctors_screen, "doctors", "04. Doctors")
        if auth.can(auth.P_TESTS):
            self._add_tab(self.tests_screen, "tests", "05. Tests")
        if auth.can(auth.P_MONEY):
            self._add_tab(self.billing_screen, "billing", "06. Billing")
            self._add_tab(self.analytics_screen, "analytics", "07. Day Book")
            self._add_tab(self.summaries_screen, "summaries", "08. Summaries")
        if auth.can(auth.P_USERS):
            self._add_tab(self.staff_screen, "staff", "09. Staff")
        # P_SETTINGS only. The "or P_USERS" that used to be here let whoever
        # manages logins rewrite the letterhead, the signatories' names and
        # qualifications, and the report-number sequence -- everything that
        # makes a report attributable. The Staff tab above already covers them.
        if auth.can(auth.P_SETTINGS):
            self._add_tab(self.settings_screen, "settings", "10. Settings")
        self.tabs.currentChanged.connect(self._tab_changed)
        
        # The key strip sits between the tabs and the page, where the web
        # application puts it.
        self.tabs.insertBetween(self._build_key_strip())
        central_lay.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

        self.job_screen.job_changed.connect(self.queue_screen.refresh)
        self.job_screen.job_changed.connect(self._refresh_status)
        self.job_screen.request_send.connect(self._send)
        self.queue_screen.open_job.connect(self._open_job)
        self.queue_screen.preview_job.connect(lambda j: self.preview(j))
        self.patients_screen.open_job.connect(self._open_job)
        self.patients_screen.preview_job.connect(lambda j: self.preview(j))
        self.patients_screen.new_job_for.connect(self._new_job_for)
        self.job_screen.request_preview.connect(lambda j: self.preview(j))
        self.queue_screen.send_job.connect(self._send)
        self.settings_screen.settings_saved.connect(self._relabel)

        self._build_status_bar()
        self._build_shortcuts()
        self._refresh_status()

        self._ticker = QTimer(self)
        self._ticker.setInterval(60_000)
        self._ticker.timeout.connect(self._refresh_status)
        self._ticker.start()

    def _relabel(self) -> None:
        """Re-read the laboratory's name after Settings has been saved."""
        lab = (q.get_setting("lab_name_prefix") + " "
               + q.get_setting("lab_name")).strip()
        self.setWindowTitle(f"LabSoft — {lab}")
        if getattr(self, "_where_label", None) is not None:
            self._where_label.setText(
                f"{lab.upper()} · {config.APP_NAME} {config.APP_VERSION}")

    # ------------------------------------------------------------ furniture
    def _add_tab(self, screen: QWidget, icon: str, text: str) -> None:
        self.tabs.addTab(screen, icons.get_icon(icon, style.INK2, 15), text)

    def _build_key_strip(self) -> QWidget:
        """The dark strip of function keys, as the web application shows it.

        The keys exist either way; printing them means nobody has to be told
        twice, and it is the fastest thing on this screen for an operator who
        works here every day.
        """
        strip = QFrame()
        strip.setObjectName("keyStrip")
        strip.setFixedHeight(28)
        lay = QHBoxLayout(strip)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(18)
        for key, what in (("F2", "New job"), ("F3", "Find a patient"),
                          ("F4", "Settle bill"), ("F8", "WhatsApp"),
                          ("F9", "Report print"), ("F10", "Day book"),
                          ("Ctrl+F", "Search this screen")):
            cap = QLabel(key)
            cap.setProperty("role", "keycap")
            lay.addWidget(cap)
            name = QLabel(what)
            name.setProperty("role", "keyname")
            lay.addWidget(name)
        lay.addStretch(1)
        return strip

    def _build_app_bar(self, lab: str) -> QWidget:
        """The 44px ink bar from artboard 01: program, laboratory, operator.

        Every colour comes from the stylesheet rather than from here, so the
        bar follows a theme change instead of staying whatever it was painted
        on the day it was written.
        """
        bar = QFrame()
        bar.setObjectName("appBar")
        bar.setFixedHeight(44)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 0, 18, 0)
        lay.setSpacing(16)

        wordmark = QLabel("LABSOFT")
        wordmark.setProperty("role", "wordmark")
        lay.addWidget(wordmark)

        where = QLabel(f"{lab.upper()} · {config.APP_NAME} {config.APP_VERSION}")
        where.setProperty("role", "barmuted")
        self._where_label = where
        lay.addWidget(where)
        lay.addStretch(1)

        user = auth.current()
        if user:
            dot = QFrame()
            dot.setObjectName("signedInDot")
            dot.setFixedSize(9, 9)
            lay.addWidget(dot)

            who = QLabel(user.label)
            who.setProperty("role", "baruser")
            lay.addWidget(who)

            out = QPushButton("Sign out")
            out.setProperty("kind", "danger")
            out.setCursor(Qt.CursorShape.PointingHandCursor)
            out.clicked.connect(self._sign_out)
            lay.addWidget(out)
        return bar

    def _build_status_bar(self) -> None:
        bar = QStatusBar()
        self.count_label = QLabel("")
        self.overdue_label = QLabel("")
        self.backup_label = QLabel("")
        self.backup_label.setProperty("role", "hint")
        bar.addWidget(self.count_label)
        bar.addWidget(self.overdue_label, 1)
        bar.addPermanentWidget(self.backup_label)

        # "&&", or Qt eats the ampersand as a mnemonic -- which both dropped
        # the word from the label and bound the button to Alt+Space, the
        # Windows system-menu key.
        about = QPushButton("About && credits · F1")
        about.setProperty("kind", "quiet")
        about.setCursor(Qt.CursorShape.PointingHandCursor)
        about.clicked.connect(self._show_about)
        bar.addPermanentWidget(about)
        self.setStatusBar(bar)

    def _build_shortcuts(self) -> None:
        """One owner per key.

        Qt fires NEITHER handler when two live widgets claim the same
        shortcut -- it reports the press as ambiguous and drops it. F8 and F9
        were bound here AND on the Job screen's own buttons, so the two keys
        the foot bar advertises did nothing at all; F9 worked only while
        "Check & make report" was disabled and had stopped competing. F5 was
        claimed here and again by the Work Queue. The buttons keep F8/F9,
        because a key printed on a button is the one people find.
        """
        QShortcut(QKeySequence("F1"), self, activated=self._show_about)
        QShortcut(QKeySequence("F2"), self, activated=self._new_job)
        QShortcut(QKeySequence("F3"), self, activated=self._find_patient)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._focus_search)
        QShortcut(QKeySequence("F5"), self, activated=self._refresh_all)
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self.tabs.setCurrentIndex(0))
        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self.tabs.setCurrentIndex(1))
        QShortcut(QKeySequence("F10"), self, activated=lambda: self.tabs.setCurrentWidget(self.analytics_screen))

    def _show_about(self) -> None:
        from .about_dialog import AboutDialog

        AboutDialog(self).exec()

    def _refresh_status(self) -> None:
        """The day in one line, with only the bad number in the accent.

        Colouring the whole line when something was overdue made three
        healthy figures look like three problems.
        """
        c = q.queue_counts()
        line = (f"Today {c['today']}      Pending results {c['pending']}"
                f"      Ready to send {c['ready']}")
        self.count_label.setText(line)
        self.count_label.setStyleSheet(f"color: {style.INK2}; font-weight: 600;")

        late = c.get("overdue", 0)
        self.overdue_label.setText(f"Overdue {late}" if late else "")
        self.overdue_label.setStyleSheet(
            f"color: {style.ALERT}; font-weight: 800;")

        # The last backup that actually happened, not the clock. Printing the
        # current time made the bar say "backed up" even when the copy had
        # failed, which is the one moment the operator needs the truth.
        last = connection.last_backup_time()
        self.backup_label.setText(
            f"Backup {last.strftime('%d-%m %H:%M')}" if last else "No backup yet")
        self.backup_label.setStyleSheet(
            f"color: {style.INK3};" if last else f"color: {style.ALERT}; font-weight: 700;")

    def _tab_changed(self, index: int) -> None:
        # One branch. There used to be a `hasattr(w, "load")` arm first, but
        # no screen defines load(), so it never ran.
        w = self.tabs.widget(index)
        if hasattr(w, "refresh"):
            w.refresh()
        self._refresh_status()

    def _new_job(self) -> None:
        self.tabs.setCurrentIndex(TAB_JOB)
        self.job_screen.new_job()

    def _find_patient(self) -> None:
        """F3, which the key strip has always advertised and nothing bound.

        Go to the Patients register and put the cursor in its search box —
        which is what "Find a patient" means.
        """
        self.tabs.setCurrentWidget(self.patients_screen)
        box = getattr(self.patients_screen, "search", None)
        if box is not None:
            box.setFocus()
            box.selectAll()

    def _focus_search(self) -> None:
        """Put the cursor in the search box of the screen already open.

        It used to jump to the Job screen wherever you were, which meant
        Ctrl+F halfway through the patients list threw away what you were
        doing. Only fall back to Job when the current screen has nothing to
        search with.
        """
        current = self.tabs.currentWidget()
        box = getattr(current, "search", None) or getattr(current, "test_search", None)
        if box is None:
            self.tabs.setCurrentIndex(TAB_JOB)
            box = self.job_screen.test_search
        box.setFocus()
        box.selectAll()

    def _new_job_for(self, patient_id: int) -> None:
        self.tabs.setCurrentIndex(TAB_JOB)
        self.job_screen.new_job_for(patient_id)

    def _open_job(self, job_id: int) -> None:
        self.tabs.setCurrentIndex(TAB_JOB)
        self.job_screen.load_job(job_id)

    def _after_send(self, job_id: int) -> None:
        """The Job screen is the one in front when a report is sent from it.

        Only the queue and the status bar were refreshed, so the job header
        went on saying "Ready to send" after the report had gone out.
        """
        self.queue_screen.refresh()
        if self.job_screen.job_id == job_id:
            self.job_screen.load_job(job_id)
        self._refresh_status()

    def _send(self, job_id: int) -> None:
        from .send_dialog import SendDialog

        SendDialog(job_id, self).exec()
        self._after_send(job_id)

    def preview(self, job_id: int) -> None:
        from .preview_dialog import PreviewDialog

        PreviewDialog(job_id, self).exec()

    def _refresh_all(self) -> None:
        self._refresh_status()
        w = self.tabs.currentWidget()
        if hasattr(w, "refresh"):
            w.refresh()

    def _sign_out(self) -> None:
        self.was_signed_out = True
        self.close()
