"""About & Credits dialog for LabSoft."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QVBoxLayout

from . import style
from .widgets import button, label, row


class AboutDialog(QDialog):
    """Single canonical software version, author credit, and system overview dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About LabSoft — Pathology Laboratory System")
        self.setFixedSize(540, 520)
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 20)
        lay.setSpacing(14)

        # 1. Header Banner Card (Medical Sapphire #0A3668)
        card = QFrame()
        card.setObjectName("aboutHeaderCard")
        card.setStyleSheet("""
            QFrame#aboutHeaderCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #062344, stop:0.6 #0A3668, stop:1 #0284C7);
                border: none;
                border-radius: 6px;
                padding: 16px;
            }
        """)
        clay = QVBoxLayout(card)
        clay.setContentsMargins(14, 12, 14, 12)
        clay.setSpacing(4)

        top_row = QHBoxLayout()
        app_title = QLabel("LabSoft")
        app_title.setStyleSheet("color: #FFFFFF; font-size: 22pt; font-weight: 800; background: transparent; border: none;")
        top_row.addWidget(app_title)

        ver_pill = QLabel(" 2026.08 ")
        ver_pill.setStyleSheet("color: #0A3668; background: #FFFFFF; font-size: 9.5pt; font-weight: 800; border-radius: 3px; padding: 2px 6px; border: none;")
        top_row.addWidget(ver_pill)
        top_row.addStretch(1)
        clay.addLayout(top_row)

        subtitle = QLabel("Medical Diagnostic Laboratory Information & Reporting System")
        subtitle.setStyleSheet("color: #E0F2FE; font-size: 10pt; font-weight: 600; background: transparent; border: none;")
        clay.addWidget(subtitle)

        tagline = QLabel("ACCURACY  •  CLINICAL CARE  •  TRUST")
        tagline.setStyleSheet("color: #BAE6FD; font-size: 7.5pt; font-weight: 800; letter-spacing: 1.5px; padding-top: 4px; background: transparent; border: none;")
        clay.addWidget(tagline)

        lay.addWidget(card)

        # 2. Author Credit & System Metadata Card
        info_frame = QFrame()
        info_frame.setObjectName("aboutInfoBox")
        info_frame.setStyleSheet(f"""
            QFrame#aboutInfoBox {{
                background: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 12px;
            }}
            QFrame#aboutInfoBox QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        flay = QVBoxLayout(info_frame)
        flay.setContentsMargins(14, 12, 14, 12)
        flay.setSpacing(9)

        # Author Credit
        author_row = QHBoxLayout()
        lbl_author = QLabel("Author / Developer:")
        lbl_author.setStyleSheet("color: #475569; font-weight: 600; font-size: 9.5pt;")
        val_author = QLabel("RANDOM_GTV")
        val_author.setStyleSheet("color: #0284C7; font-weight: 800; font-size: 10.5pt;")
        author_row.addWidget(lbl_author)
        author_row.addSpacing(8)
        author_row.addWidget(val_author)
        author_row.addStretch(1)
        flay.addLayout(author_row)

        # Operating Facility
        fac_row = QHBoxLayout()
        lbl_fac = QLabel("Licensed Facility:")
        lbl_fac.setStyleSheet("color: #475569; font-weight: 600; font-size: 9.5pt;")
        val_fac = QLabel("MITHRA MEDICAL LABORATORY")
        val_fac.setStyleSheet("color: #0A3668; font-weight: 800; font-size: 9.5pt;")
        fac_row.addWidget(lbl_fac)
        fac_row.addSpacing(8)
        fac_row.addWidget(val_fac)
        fac_row.addStretch(1)
        flay.addLayout(fac_row)

        # Core Engine Architecture
        engine_row = QHBoxLayout()
        lbl_eng = QLabel("System Architecture:")
        lbl_eng.setStyleSheet("color: #475569; font-weight: 600; font-size: 9.5pt;")
        val_eng = QLabel("PyQt6 • SQLite WAL • 80mm POS • QPdf Engine")
        val_eng.setStyleSheet("color: #64748B; font-size: 9pt; font-weight: 500;")
        engine_row.addWidget(lbl_eng)
        engine_row.addSpacing(8)
        engine_row.addWidget(val_eng)
        engine_row.addStretch(1)
        flay.addLayout(engine_row)

        lay.addWidget(info_frame)

        # 3. Key Capabilities
        lbl_cap = QLabel("KEY CLINICAL CAPABILITIES:")
        lbl_cap.setStyleSheet("color: #0A3668; font-size: 8.5pt; font-weight: 800; letter-spacing: 0.8px; margin-top: 2px;")
        lay.addWidget(lbl_cap)

        features = [
            "Clinical calculation engine with real-time delta check analysis",
            "Multi-style diagnostic letterheads & dual HbA1c report layouts",
            "Executive Day-Book financial dashboard with live CSV exports",
            "Dual invoicing: Official A4 Tax Invoices + 80mm POS thermal slips",
            "Instant WhatsApp structured report dispatch & medico-legal audit",
        ]
        for f in features:
            h_row = QHBoxLayout()
            h_row.setSpacing(8)
            chk = QLabel("✓")
            chk.setStyleSheet("color: #059669; font-weight: 800; font-size: 9.5pt;")
            txt = QLabel(f)
            txt.setStyleSheet("color: #334155; font-size: 9pt; font-weight: 500;")
            h_row.addWidget(chk)
            h_row.addWidget(txt, 1)
            lay.addLayout(h_row)

        lay.addStretch(1)

        # 4. Footer Close Button
        btn_close = button("Close", "primary", self.accept)
        btn_close.setFixedWidth(110)
        lay.addWidget(row(None, btn_close))
