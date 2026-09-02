"""What this program is, who wrote it, and which version is running.

Plain type on the page ground, in the canvas idiom: an ink band with the
wordmark, a short table of facts, and the list of what the program does. No
gradient, no rounded card -- the rest of the application has neither.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QFrame, QHBoxLayout, QVBoxLayout

from .. import config
from ..db import queries as q
from .widgets import button, label, row

FEATURES = [
    "Calculation engine with delta checking against the previous visit",
    "Letterhead and detailed single-test reports, printed or as PDF",
    "Day book with live CSV export of the day's billing",
    "A4 invoices and 80mm counter receipts",
    "WhatsApp dispatch, with an audit trail of what was sent and when",
]


class AboutDialog(QDialog):
    """About and credits."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About LabSoft")
        self.setFixedSize(560, 480)
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._band())

        body = QFrame()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(22, 20, 22, 18)
        body_lay.setSpacing(14)

        lab = (q.get_setting("lab_name_prefix") + " "
               + q.get_setting("lab_name")).strip()
        facts = QFrame()
        facts_lay = QVBoxLayout(facts)
        facts_lay.setContentsMargins(0, 0, 0, 0)
        facts_lay.setSpacing(7)
        for caption, value in (
                ("Written by", "RANDOM_GTV"),
                ("Running at", lab or "—"),
                ("Version", f"{config.APP_VERSION}"),
                ("Built on", "PyQt6 · SQLite (WAL) · QPainter PDF")):
            line = QHBoxLayout()
            line.setSpacing(10)
            name = label(caption, "field")
            name.setFixedWidth(110)
            line.addWidget(name)
            line.addWidget(label(value))
            line.addStretch(1)
            facts_lay.addLayout(line)
        body_lay.addWidget(facts)

        body_lay.addWidget(label("What it does", "field"))
        for feature in FEATURES:
            line = QHBoxLayout()
            line.setSpacing(9)
            mark = label("—", "hint")
            mark.setFixedWidth(12)
            line.addWidget(mark)
            line.addWidget(label(feature), 1)
            body_lay.addLayout(line)

        body_lay.addStretch(1)
        close = button("Close", "primary", self.accept)
        close.setFixedWidth(110)
        body_lay.addWidget(row(None, close))
        lay.addWidget(body, 1)

    def _band(self) -> QFrame:
        band = QFrame()
        band.setObjectName("appBar")
        band.setFixedHeight(72)
        lay = QHBoxLayout(band)
        lay.setContentsMargins(22, 0, 22, 0)
        lay.setSpacing(14)

        mark = label("LABSOFT", "wordmark")
        lay.addWidget(mark)
        lay.addWidget(label("MEDICAL LABORATORY SOFTWARE", "barmuted"))
        lay.addStretch(1)
        lay.addWidget(label(config.APP_VERSION, "baruser"))
        return band
