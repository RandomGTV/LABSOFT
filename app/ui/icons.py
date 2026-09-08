"""Shared 24px outline icon family; geometry lives in assets/icons.json."""
from __future__ import annotations
import json
from pathlib import Path
from PyQt6.QtCore import QByteArray, QRectF
from PyQt6.QtGui import QColor, QIcon, QIconEngine, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

ICON_PATHS = json.loads((Path(__file__).resolve().parents[2] / "assets" / "icons.json").read_text(encoding="utf-8"))
SVG_ICONS = {name: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">' + body + '</svg>' for name, body in ICON_PATHS.items()}

class ThemeIcon(QIconEngine):
    def __init__(self, name, color):
        super().__init__()
        from . import style
        self.name = name
        self.color = color
        self.role = next((key for key in ("ON_ACCENT", "INK2", "GREEN", "INK", "ON_MONEY", "RED")
                          if getattr(style, key) == color), None) if color else "INK2"

    def clone(self):
        clone = ThemeIcon(self.name, self.color)
        clone.role = self.role
        return clone

    def paint(self, painter, rect, mode, state):
        from . import style
        color = getattr(style, self.role) if self.role else self.color
        if mode == QIcon.Mode.Disabled:
            color = style.INK3
        svg = SVG_ICONS.get(self.name, SVG_ICONS["info"]).format(color=color)
        QSvgRenderer(QByteArray(svg.encode())).render(painter, QRectF(rect))

    def pixmap(self, size, mode, state):
        pix = QPixmap(size)
        pix.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pix)
        self.paint(painter, pix.rect(), mode, state)
        painter.end()
        return pix


def get_icon(name: str, color: str = "", size: int = 18) -> QIcon:
    return QIcon(ThemeIcon(name, color))
