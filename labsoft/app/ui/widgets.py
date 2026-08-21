"""Small shared widgets and helpers used by more than one screen."""

from __future__ import annotations

from typing import Callable, Iterable, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QComboBox, QCompleter, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import style


def button(text: str, kind: str = "", on_click: Optional[Callable] = None,
           tooltip: str = "", shortcut: str = "") -> QPushButton:
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    if on_click:
        b.clicked.connect(on_click)
    if shortcut:
        b.setShortcut(shortcut)
        tooltip = f"{tooltip}  ({shortcut})".strip()
    if tooltip:
        b.setToolTip(tooltip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def label(text: str, role: str = "") -> QLabel:
    lab = QLabel(text)
    if role:
        lab.setProperty("role", role)
    return lab


def field_label(text: str) -> QLabel:
    return label(text.upper(), "field")


def hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color: {style.LINE}; background: {style.LINE};")
    f.setMaximumHeight(1)
    return f


def row(*widgets, spacing: int = 8, stretch_last: bool = False) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    for item in widgets:
        if item is None:
            lay.addStretch(1)
        elif isinstance(item, int):
            lay.addSpacing(item)
        else:
            lay.addWidget(item)
    if stretch_last:
        lay.setStretch(lay.count() - 1, 1)
    return w


def column(*widgets, spacing: int = 8, margins=(0, 0, 0, 0)) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    for item in widgets:
        if item is None:
            lay.addStretch(1)
        elif isinstance(item, int):
            lay.addSpacing(item)
        else:
            lay.addWidget(item)
    return w


class FlagLabel(QLabel):
    """The coloured N / HIGH / LOW marker beside a result box."""

    def __init__(self):
        super().__init__("")
        self.setMinimumWidth(62)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont()
        f.setBold(True)
        f.setPointSizeF(9.0)
        self.setFont(f)

    def set_flag(self, flag: str) -> None:
        text = style.FLAG_TEXT.get(flag, "")
        colour = style.FLAG_COLOURS.get(flag, style.INK3)
        self.setText(text)
        if not text:
            self.setStyleSheet("")
            return
        is_dark = style.CURRENT_THEME == "dark"
        if is_dark:
            bg = {"H": "#3A2326", "L": "#22303F", "A": "#38301E", "N": "#1F3229"}.get(flag, "")
        else:
            bg = {"H": "#FDECEB", "L": "#EAF1FC", "A": "#FDF5E3", "N": "#EAF5EE"}.get(flag, "")
        self.setStyleSheet(
            f"color: {colour}; background: {bg}; border-radius: 10px; padding: 2px 8px; font-weight: 700;")


def status_pill(text: str, status_type: str = "draft") -> QLabel:
    """A rounded status pill for job status (draft, prog, ready, sent)."""
    lab = QLabel(text)
    lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lab.setProperty("role", f"pill_{status_type}")
    return lab


class SearchBox(QLineEdit):
    """A search field that reports changes after the operator stops typing."""

    searched = pyqtSignal(str)

    def __init__(self, placeholder: str = "Search…"):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        from PyQt6.QtCore import QTimer

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(220)
        self._timer.timeout.connect(lambda: self.searched.emit(self.text()))
        self.textChanged.connect(lambda _t: self._timer.start())
        self.returnPressed.connect(lambda: self.searched.emit(self.text()))


class Table(QTableWidget):
    """A read-only list table with sensible defaults and an empty state.

    An empty table with no explanation reads as "broken" rather than "nothing
    here yet", which is the difference between the operator carrying on and the
    operator calling for help.
    """

    def __init__(self, headers: List[str], stretch_column: int = 1,
                 empty_text: str = ""):
        super().__init__(0, len(headers))
        self._empty_label: Optional[QLabel] = None
        self._empty_text = empty_text
        self.setHorizontalHeaderLabels(headers)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.verticalHeader().setDefaultSectionSize(34)
        header = self.horizontalHeader()
        header.setHighlightSections(False)
        from PyQt6.QtWidgets import QHeaderView

        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        if 0 <= stretch_column < len(headers):
            header.setSectionResizeMode(stretch_column, QHeaderView.ResizeMode.Stretch)

    def set_empty_text(self, text: str) -> None:
        self._empty_text = text
        self._refresh_empty()

    def _refresh_empty(self) -> None:
        if not self._empty_text:
            if self._empty_label is not None:
                self._empty_label.hide()
            return
        if self._empty_label is None:
            lab = QLabel(self._empty_text, self.viewport())
            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lab.setWordWrap(True)
            lab.setStyleSheet(
                f"color: {style.INK3}; background: transparent; font-size: 11pt;")
            self._empty_label = lab
        self._empty_label.setText(self._empty_text)
        if self.rowCount() == 0:
            self._empty_label.setGeometry(self.viewport().rect().adjusted(30, 30, -30, -30))
            self._empty_label.show()
            self._empty_label.raise_()
        else:
            self._empty_label.hide()

    def resizeEvent(self, event):          # noqa: N802 - Qt naming
        super().resizeEvent(event)
        self._refresh_empty()

    def set_rows(self, rows: Iterable[Iterable], colours: Optional[dict] = None) -> None:
        """rows: iterable of cell values. colours: {row_index: QColor} for text."""
        data = [list(r) for r in rows]
        self.setUpdatesEnabled(False)
        try:
            self.setRowCount(len(data))
            for r, cells in enumerate(data):
                for c, value in enumerate(cells):
                    item = QTableWidgetItem("" if value is None else str(value))
                    if colours and r in colours:
                        item.setForeground(colours[r])
                    self.setItem(r, c, item)
            self._refresh_empty()
        finally:
            self.setUpdatesEnabled(True)

    def selected_row(self) -> int:
        rows = self.selectionModel().selectedRows() if self.selectionModel() else []
        return rows[0].row() if rows else -1


def info(parent, title: str, text: str) -> None:
    QMessageBox.information(parent, title, text)


def warn(parent, title: str, text: str) -> None:
    QMessageBox.warning(parent, title, text)


def error(parent, title: str, text: str) -> None:
    QMessageBox.critical(parent, title, text)


def confirm(parent, title: str, text: str, ok_text: str = "Yes") -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Question)
    yes = box.addButton(ok_text, QMessageBox.ButtonRole.AcceptRole)
    box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    return box.clickedButton() is yes


SEXES = ["", "Male", "Female", "Other"]
AGE_UNITS = ["Years", "Months", "Days"]


def sex_combo() -> QComboBox:
    c = QComboBox()
    c.addItems(SEXES)
    return c


def age_unit_combo() -> QComboBox:
    c = QComboBox()
    c.addItems(AGE_UNITS)
    return c
