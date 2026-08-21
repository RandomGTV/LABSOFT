"""About & Credits dialog for LabSoft."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QVBoxLayout

from .. import config
from ..output.report import BLUE_DARK, BLUE_PRIMARY, BLUE_TINT
from . import style
from .widgets import button, field_label, hline, label, row


class AboutDialog(QDialog):
    """Show software version, author credit, and system overview."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About LabSoft")
        self.setFixedSize(520, 480)
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        # Header card with medical blue banner
        card = QFrame()
        card.setObjectName("aboutCard")
        card.setStyleSheet(f"""
            QFrame#aboutCard {{
                background: {BLUE_DARK.name()};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        clay = QVBoxLayout(card)
        clay.setContentsMargins(12, 10, 12, 10)
        clay.setSpacing(4)

        app_title = QLabel("LabSoft")
        app_title.setStyleSheet("color: #FFFFFF; font-size: 20pt; font-weight: 800;")
        clay.addWidget(app_title)

        subtitle = QLabel("Medical Diagnostic Laboratory Information & Reporting System")
        subtitle.setStyleSheet("color: #48CAE4; font-size: 9.5pt; font-weight: 600;")
        clay.addWidget(subtitle)

        tagline = QLabel("ACCURACY  •  CARE  •  TRUST")
        tagline.setStyleSheet("color: #D4E7FA; font-size: 7.5pt; font-weight: 700; letter-spacing: 1px; padding-top: 4px;")
        clay.addWidget(tagline)

        lay.addWidget(card)

        # Author & Version Info Box
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background: {style.PANEL};
                border: 1px solid {style.LINE};
                border-radius: 6px;
                padding: 12px;
            }}
        """)
        flay = QVBoxLayout(info_frame)
        flay.setSpacing(8)

        # Author Credit
        author_row = QHBoxLayout()
        lbl_author = QLabel("Author / Developer:")
        lbl_author.setStyleSheet(f"color: {style.INK2}; font-weight: 600; font-size: 10pt;")
        val_author = QLabel("RANDOM_GTV")
        val_author.setStyleSheet(f"color: {BLUE_PRIMARY.name()}; font-weight: 800; font-size: 11pt;")
        author_row.addWidget(lbl_author)
        author_row.addSpacing(8)
        author_row.addWidget(val_author)
        author_row.addStretch(1)
        flay.addLayout(author_row)

        # Version & Architecture
        ver_row = QHBoxLayout()
        lbl_ver = QLabel("Version:")
        lbl_ver.setStyleSheet(f"color: {style.INK2}; font-weight: 600; font-size: 10pt;")
        val_ver = QLabel("v1.0.0 (Production Release)")
        val_ver.setStyleSheet(f"color: {style.INK}; font-weight: 600; font-size: 10pt;")
        ver_row.addWidget(lbl_ver)
        ver_row.addSpacing(8)
        ver_row.addWidget(val_ver)
        ver_row.addStretch(1)
        flay.addLayout(ver_row)

        # System Engine
        engine_row = QHBoxLayout()
        lbl_eng = QLabel("Core Engine:")
        lbl_eng.setStyleSheet(f"color: {style.INK2}; font-weight: 600; font-size: 10pt;")
        val_eng = QLabel("PyQt6 • SQLite WAL • QPdf Engine")
        val_eng.setStyleSheet(f"color: {style.INK3}; font-size: 9.5pt;")
        engine_row.addWidget(lbl_eng)
        engine_row.addSpacing(8)
        engine_row.addWidget(val_eng)
        engine_row.addStretch(1)
        flay.addLayout(engine_row)

        lay.addWidget(info_frame)

        # Key Features Summary
        feat_label = label("Key Capabilities:", "field")
        lay.addWidget(feat_label)

        features = [
            "✓ Clinical calculation engine & formula evaluation",
            "✓ Standard & detailed single-sheet HbA1c with clinical notes",
            "✓ Multi-style letterhead with high-resolution logo integration",
            "✓ Reception billing, thermal receipts & doctor commissions",
            "✓ Automated WhatsApp PDF dispatch & local encrypted audit",
        ]
        for f in features:
            flbl = QLabel(f)
            flbl.setStyleSheet(f"color: {style.INK2}; font-size: 9pt;")
            lay.addWidget(flbl)

        lay.addStretch(1)

        # Bottom Close button
        btn_close = button("Close", "primary", self.accept)
        btn_close.setFixedWidth(110)
        lay.addWidget(row(None, btn_close))
