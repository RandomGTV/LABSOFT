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
        """A square block, edged in its own colour.

        Square because it is the house rule, and edged because the word inside
        must survive a photocopy, a projector, and an operator who cannot tell
        the red one from the blue one.
        """
        text = style.FLAG_TEXT.get(flag, "")
        colour = style.FLAG_COLOURS.get(flag, style.INK3)
        self.setText(text)
        if not text:
            self.setStyleSheet("")
            return
        bg, edge = style.flag_fill(flag)
        self.setStyleSheet(
            f"color: {colour}; background: {bg}; border: 1px solid {edge}; "
            f"border-radius: 0; padding: 2px 8px; font-weight: 800;")


def status_pill(text: str, status_type: str = "draft") -> QLabel:
    """The job-state block: draft, prog, ready or sent.

    Named "pill" from when it was rounded; it is a square block now, drawn the
    same way as a result flag so the two read as one family.
    """
    lab = QLabel(text.upper())
    lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lab.setProperty("role", f"pill_{status_type}")
    fg, bg, edge = style.status_fill(status_type)
    f = QFont()
    f.setBold(True)
    f.setPointSizeF(8.5)
    lab.setFont(f)
    lab.setStyleSheet(
        f"color: {fg}; background: {bg}; border: 1px solid {edge}; "
        f"border-radius: 0; padding: 3px 10px; font-weight: 800;")
    return lab


class EllipsisLabel(QLabel):
    """A label that shortens its text to fit instead of pushing its neighbours.

    A QLabel is never smaller than its text, so one long test name -- "Total
    Cholesterol / HDL Ratio" -- widened the whole name column and shoved every
    result box across the screen. This one keeps the full text for the tooltip
    and draws as much of it as the column allows.
    """

    def __init__(self, text: str = ""):
        super().__init__()
        self._full = text or ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored,
                           QSizePolicy.Policy.Preferred)
        self.setText(self._full)

    def setText(self, text: str) -> None:      # noqa: N802 - Qt naming
        self._full = text or ""
        if self._full:
            self.setToolTip(self._full)
        self._draw()

    def full_text(self) -> str:
        return self._full

    def resizeEvent(self, event):              # noqa: N802
        super().resizeEvent(event)
        self._draw()

    def _draw(self) -> None:
        metrics = self.fontMetrics()
        room = max(0, self.width() - 2)
        shown = (metrics.elidedText(self._full, Qt.TextElideMode.ElideRight, room)
                 if room > 24 else self._full)
        super().setText(shown)


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

        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
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
        self.blockSignals(True)
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
            self.blockSignals(False)
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


class TabDeck(QWidget):
    """A tab bar and its pages, with room between them for another strip.

    QTabWidget welds its bar to its pane, and the web application puts the
    function-key strip in exactly that gap. This keeps the small part of
    QTabWidget's interface the rest of the program uses, and lets the shell
    decide what goes between.
    """

    def __init__(self, parent=None):
        from PyQt6.QtWidgets import QStackedWidget, QTabBar

        super().__init__(parent)
        self.bar = QTabBar()
        self.bar.setDrawBase(False)
        self.bar.setExpanding(False)
        self.bar.setUsesScrollButtons(True)
        self.bar.setElideMode(Qt.TextElideMode.ElideNone)
        self.stack = QStackedWidget()

        self._between = QVBoxLayout()
        self._between.setContentsMargins(0, 0, 0, 0)
        self._between.setSpacing(0)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.bar)
        lay.addLayout(self._between)
        lay.addWidget(self.stack, 1)

        self.bar.currentChanged.connect(self.stack.setCurrentIndex)
        self.currentChanged = self.bar.currentChanged

    # -- the slice of QTabWidget the rest of the program calls ---------------
    def addTab(self, widget, *args) -> int:            # noqa: N802 - Qt naming
        """addTab(widget, text) or addTab(widget, icon, text)."""
        self.stack.addWidget(widget)
        return self.bar.addTab(*args)

    def insertBetween(self, widget) -> None:           # noqa: N802
        """Put a widget in the gap between the tabs and the page."""
        self._between.addWidget(widget)

    def count(self) -> int:
        return self.bar.count()

    def tabText(self, index: int) -> str:              # noqa: N802
        return self.bar.tabText(index)

    def setCurrentIndex(self, index: int) -> None:     # noqa: N802
        self.bar.setCurrentIndex(index)

    def currentIndex(self) -> int:                     # noqa: N802
        return self.bar.currentIndex()

    def widget(self, index: int):
        return self.stack.widget(index)

    def currentWidget(self):                           # noqa: N802
        return self.stack.currentWidget()

    def setCurrentWidget(self, widget) -> None:        # noqa: N802
        index = self.stack.indexOf(widget)
        if index >= 0:
            self.setCurrentIndex(index)

    def setDocumentMode(self, on: bool) -> None:       # noqa: N802
        self.bar.setDocumentMode(on)
