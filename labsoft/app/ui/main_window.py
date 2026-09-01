"""The application shell with modern web-style UI/UX header and tabs."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QTabWidget,
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
from .widgets import error, info

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

        # 1. Top Brand Header Bar
        header = QFrame()
        header.setObjectName("topHeaderBar")
        header.setFixedHeight(46)
        header.setStyleSheet("""
            QFrame#topHeaderBar {
                background-color: #FFFFFF;
                border-bottom: 1.5px solid #CBD5E1;
                padding: 0 16px;
            }
        """)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(16, 0, 16, 0)
        h_lay.setSpacing(12)

        # Brand Title
        brand_lbl = QLabel("LabSoft")
        brand_lbl.setFont(QFont("Archivo", 13, QFont.Weight.ExtraBold))
        brand_lbl.setStyleSheet("color: #0A3668; border: none; background: transparent;")
        h_lay.addWidget(brand_lbl)

        # Version Badge
        badge = QLabel("2026.08")
        badge.setFont(QFont("Archivo", 8, QFont.Weight.Bold))
        badge.setStyleSheet("background-color: #0284C7; color: #FFFFFF; padding: 2px 6px; border-radius: 3px; border: none;")
        h_lay.addWidget(badge)

        # Facility Name Subtitle
        lab_name_sub = QLabel("·   MITHRA MEDICAL LABORATORY")
        lab_name_sub.setFont(QFont("Archivo", 9, QFont.Weight.DemiBold))
        lab_name_sub.setStyleSheet("color: #64748B; border: none; background: transparent;")
        h_lay.addWidget(lab_name_sub)

        h_lay.addStretch(1)

        # Right side: User pill
        user = auth.current()
        if user:
            user_pill = QFrame()
            user_pill.setStyleSheet("""
                QFrame {
                    background-color: #F1F5F9;
                    border: 1px solid #CBD5E1;
                    border-radius: 14px;
                    padding: 2px 10px;
                }
            """)
            u_lay = QHBoxLayout(user_pill)
            u_lay.setContentsMargins(8, 2, 8, 2)
            u_lay.setSpacing(6)

            dot = QFrame()
            dot.setFixedSize(7, 7)
            dot.setStyleSheet("background-color: #059669; border-radius: 3px;")
            u_lay.addWidget(dot)

            u_lbl = QLabel(user.label)
            u_lbl.setFont(QFont("Archivo", 9, QFont.Weight.Bold))
            u_lbl.setStyleSheet("color: #0A3668; border: none; background: transparent;")
            u_lay.addWidget(u_lbl)
            h_lay.addWidget(user_pill)

            btn_signout = QPushButton("Sign Out")
            btn_signout.setFont(QFont("Archivo", 9, QFont.Weight.DemiBold))
            btn_signout.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #64748B;
                    text-decoration: underline;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    color: #DC2626;
                }
            """)
            btn_signout.clicked.connect(self._sign_out)
            h_lay.addWidget(btn_signout)

        central_lay.addWidget(header)

        # 2. Modern Navigation Tabs
        self.tabs = QTabWidget()
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

        # Tabs a person cannot use are not shown at all
        self.tabs.addTab(self.job_screen, icons.get_icon("job", "#0A3668", 16), "Job")
        self.tabs.addTab(self.queue_screen, icons.get_icon("queue", "#0A3668", 16), "Work Queue")
        self.tabs.addTab(self.patients_screen, icons.get_icon("patients", "#0A3668", 16), "Patients")
        self.tabs.addTab(self.doctors_screen, icons.get_icon("doctors", "#0A3668", 16), "Doctors")
        if auth.can(auth.P_TESTS):
            self.tabs.addTab(self.tests_screen, icons.get_icon("tests", "#0A3668", 16), "Tests")
        if auth.can(auth.P_MONEY):
            self.tabs.addTab(self.billing_screen, icons.get_icon("billing", "#0A3668", 16), "Billing")
            self.tabs.addTab(self.analytics_screen, icons.get_icon("analytics", "#0A3668", 16), "Analytics")
            self.tabs.addTab(self.summaries_screen, icons.get_icon("summaries", "#0A3668", 16), "Summaries")
        if auth.can(auth.P_USERS):
            self.tabs.addTab(self.staff_screen, icons.get_icon("staff", "#0A3668", 16), "Staff")
        if auth.can(auth.P_SETTINGS) or auth.can(auth.P_USERS):
            self.tabs.addTab(self.settings_screen, icons.get_icon("settings", "#0A3668", 16), "Settings")
        self.tabs.currentChanged.connect(self._tab_changed)
        
        central_lay.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

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
        self._ticker.setInterval(60_000)
        self._ticker.timeout.connect(self._refresh_status)
        self._ticker.start()

    # ------------------------------------------------------------ furniture
    def _build_status_bar(self) -> None:
        bar = QStatusBar()
        bar.setStyleSheet("""
            QStatusBar {
                background-color: #FFFFFF;
                border-top: 1.5px solid #CBD5E1;
                color: #475569;
                padding: 3px 12px;
            }
        """)
        self.count_label = QLabel("")
        self.count_label.setFont(QFont("Archivo", 9, QFont.Weight.DemiBold))
        self.backup_label = QLabel("")
        self.backup_label.setFont(QFont("Archivo", 9, QFont.Weight.Medium))
        bar.addWidget(self.count_label, 1)
        bar.addPermanentWidget(self.backup_label)
        
        about_link = QLabel('<a href="#" style="color:#0284C7; text-decoration:none; font-weight:700;">ⓘ About & Credits (F1)</a>')
        about_link.setFont(QFont("Archivo", 9, QFont.Weight.Bold))
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
        QShortcut(QKeySequence("F8"), self, activated=lambda: self.job_screen._open_whatsapp_dispatch())
        QShortcut(QKeySequence("F9"), self, activated=lambda: self.preview(self.job_screen.job_id))
        QShortcut(QKeySequence("F10"), self, activated=lambda: self.tabs.setCurrentWidget(self.analytics_screen))

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
            f"color: {style.RED}; font-weight: 700;" if c["overdue"] else "color: #334155; font-weight: 600;")

        from datetime import datetime
        now = datetime.now()
        self.backup_label.setText(f"Backup: {now.strftime('%d-%m %H:%M')} ✓  ")
        self.backup_label.setStyleSheet("color: #059669; font-weight: 700;")

    def _tab_changed(self, index: int) -> None:
        w = self.tabs.widget(index)
        if hasattr(w, "load"):
            w.load()
        elif hasattr(w, "refresh"):
            w.refresh()
        self._refresh_status()

    def _new_job(self) -> None:
        self.tabs.setCurrentIndex(TAB_JOB)
        self.job_screen.new_job()

    def _focus_search(self) -> None:
        self.tabs.setCurrentIndex(TAB_JOB)
        self.job_screen.test_search.setFocus()
        self.job_screen.test_search.selectAll()

    def _open_job(self, job_id: int) -> None:
        self.tabs.setCurrentIndex(TAB_JOB)
        self.job_screen.load_job(job_id)

    def _send(self, job_id: int) -> None:
        from .send_dialog import SendDialog

        SendDialog(job_id, self).exec()
        self.queue_screen.refresh()
        self._refresh_status()

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
