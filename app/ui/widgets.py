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
    return label(text, "field")


def hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color: {style.LINE}; background: {style.LINE};")
    f.setMaximumHeight(1)
    return f


def name_fields(root) -> int:
    """Give every input on a built screen the caption printed beside it.

    A QLineEdit with nothing but a placeholder announces itself to NVDA as
    "edit", and nothing more: a blind or partially sighted operator tabbing
    through the Job screen hears "edit … edit … combo box" for the patient's
    name, initial, mobile and sex. Qt will read a control's accessibleName if
    it has one, and will fall back to a buddy label if it does not, so this
    walks the layout the screen was built with and sets both.

    Pairing follows how these screens are actually laid out:
      * a form row -- the label Qt already holds beside the field
      * a grid -- the label directly above, or directly to the left
      * a box layout -- the label immediately before the field

    Returns how many it named, so a test can hold the number to account.
    """
    from PyQt6.QtWidgets import (
        QAbstractSpinBox, QComboBox, QFormLayout, QGridLayout, QLayout,
        QPlainTextEdit, QTextEdit,
    )

    inputs = (QLineEdit, QComboBox, QPlainTextEdit, QTextEdit, QAbstractSpinBox)
    named = 0
    visited = set()

    #: roles that are headings, figures or prose -- never a field's caption
    NOT_CAPTIONS = {"h1", "hint", "statvalue", "statlabel", "statnote", "foot",
                    "money", "figure", "person", "error", "ok", "panic"}

    def caption_of(widget) -> str:
        if not isinstance(widget, QLabel):
            return ""
        if (widget.property("role") or "") in NOT_CAPTIONS:
            return ""
        text = widget.text().strip().rstrip(":").strip()
        # A caption is a few words. Anything longer is a sentence of help.
        return text if 0 < len(text) <= 40 else ""

    def as_buddy(lab, field) -> None:
        """Point a label at its field, without losing an ampersand.

        Qt reads "&" in a buddy label as a mnemonic marker, so "Clinical
        Remarks & Smear Impression" rendered as "Clinical Remarks_Smear
        Impression" the moment a buddy was set on it.
        """
        text = lab.text()
        if "&" in text and "&&" not in text:
            lab.setText(text.replace("&", "&&"))
        lab.setBuddy(field)

    def apply(cap, field) -> None:
        nonlocal named
        if not cap or not isinstance(field, inputs):
            return
        if field.accessibleName():
            return
        field.setAccessibleName(cap)
        named += 1

    def walk(layout) -> None:
        if isinstance(layout, QFormLayout):
            for r in range(layout.rowCount()):
                lab = layout.itemAt(r, QFormLayout.ItemRole.LabelRole)
                fld = layout.itemAt(r, QFormLayout.ItemRole.FieldRole)
                if lab and fld and lab.widget() and fld.widget():
                    apply(caption_of(lab.widget()), fld.widget())
                    if isinstance(lab.widget(), QLabel):
                        as_buddy(lab.widget(), fld.widget())
        elif isinstance(layout, QGridLayout):
            cells = {}
            for i in range(layout.count()):
                item = layout.itemAt(i)
                r, c, _rs, _cs = layout.getItemPosition(i)
                if item.widget() is not None:
                    cells[(r, c)] = item.widget()
            for (r, c), w in cells.items():
                if not isinstance(w, QLabel):
                    continue
                # the field under the caption, else the one beside it
                for spot in ((r + 1, c), (r, c + 1)):
                    if isinstance(cells.get(spot), inputs):
                        apply(caption_of(w), cells[spot])
                        as_buddy(w, cells[spot])
                        break
        else:
            previous = None
            for i in range(layout.count()):
                item = layout.itemAt(i)
                w = item.widget()
                if isinstance(w, QLabel):
                    previous = w
                elif isinstance(w, inputs):
                    if previous is not None:
                        apply(caption_of(previous), w)
                        as_buddy(previous, w)
                    previous = None
                elif w is not None:
                    previous = None
    # Every layout under this screen, however deeply it is nested inside
    # frames, cards and scroll areas. Walking the tree by hand stopped at
    # QScrollArea -- which holds its contents through setWidget rather than
    # through its own layout -- and so missed the whole of Settings.
    for lay in ([root.layout()] if root.layout() is not None else []) \
            + root.findChildren(QLayout):
        if id(lay) in visited:
            continue
        visited.add(id(lay))
        walk(lay)

    # Anything still unnamed falls back to its own placeholder, which is a
    # worse name than a caption but a great deal better than "edit".
    for cls in inputs:
        for w in root.findChildren(cls):
            if w.accessibleName():
                continue
            place = getattr(w, "placeholderText", lambda: "")()
            if place:
                w.setAccessibleName(place.split("—")[0].strip(" …"))
                named += 1
    return named


def gutter(widget, left: int = 24, right: int = 24, top: int = 0,
           bottom: int = 0) -> QWidget:
    """Put a widget inside the page margin the rest of the screen uses.

    A QTableView draws its first column hard against its own left edge, so a
    table dropped straight into a screen with no margins loses the start of
    its first heading -- Billing read "eport no" and Staff's "Name" sat
    against the window frame. Wrapping keeps the table's own hairlines while
    lining its text up with the filter bar above it.
    """
    holder = QWidget()
    lay = QVBoxLayout(holder)
    lay.setContentsMargins(left, top, right, bottom)
    lay.setSpacing(0)
    lay.addWidget(widget)
    return holder


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
    lab = QLabel(text)
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
        # Headings sit over their own column's text. Qt centres them by
        # default, which puts "May…" in the middle of a wide column while the
        # words underneath start at the left edge.
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft
                                   | Qt.AlignmentFlag.AlignVCenter)
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

    def set_rows(self, rows: Iterable[Iterable], colours: Optional[dict] = None,
                 align: Optional[dict] = None,
                 cell_colours: Optional[dict] = None) -> None:
        """Fill the table.

        rows    -- iterable of cell values
        colours -- {row_index: QColor} for the text of a whole row
        align   -- {column_index: Qt.AlignmentFlag} for a whole column, so a
                   column of money can line up on its last digit instead of
                   its first, which is the only way a column of money can be
                   read down.
        cell_colours -- {(row, column): QColor} for one cell. Colouring a
                   whole row to mark one bad number turns the healthy figures
                   beside it into alarms as well.
        """
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
                    if align and c in align:
                        item.setTextAlignment(
                            int(align[c] | Qt.AlignmentFlag.AlignVCenter))
                    if cell_colours and (r, c) in cell_colours:
                        item.setForeground(cell_colours[(r, c)])
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
    fade_in(box)
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
    c.setAccessibleName("Patient sex")
    return c


def age_unit_combo() -> QComboBox:
    c = QComboBox()
    c.addItems(AGE_UNITS)
    # It sits beside the number with no caption of its own, so it has to
    # carry its own: "41" then "combo box" tells a screen reader nothing.
    c.setAccessibleName("Age is counted in")
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


# ---------------------------------------------------------------------------
# Elevation and motion
#
# Qt stylesheets have no box-shadow and no transitions, so the two things the
# web application leans on for depth and feedback have to be done in code.
# Both are used sparingly: a shadow under every button would cost a graphics
# effect per widget and buy nothing.
# ---------------------------------------------------------------------------

#: blur, y-offset, alpha -- the web app's --shadow-sm / --shadow-md / --shadow-lg
_ELEVATION = {
    1: (4, 1, 28),
    2: (12, 3, 38),
    3: (26, 8, 52),
}


def elevate(widget, level: int = 1):
    """Put a soft shadow under a surface that should read as raised.

    Only for surfaces -- a bar, a dialog, a panel. Applying a graphics effect
    to a scrolling list makes Qt re-render the whole thing on every paint,
    which is exactly where it must not be used.
    """
    from PyQt6.QtWidgets import QGraphicsDropShadowEffect

    blur, dy, alpha = _ELEVATION.get(level, _ELEVATION[1])
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setXOffset(0)
    effect.setYOffset(dy)
    effect.setColor(QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(effect)
    return widget


def fade_in(window, milliseconds: int = 110):
    """Bring a dialog up over a few frames instead of snapping it on.

    Animating the window's own opacity, not a graphics effect on its
    contents: the effect route re-rasterises every child widget and leaves
    text blurred while it runs.
    """
    from PyQt6.QtCore import QEasingCurve, QPropertyAnimation

    window.setWindowOpacity(0.0)
    animation = QPropertyAnimation(window, b"windowOpacity", window)
    animation.setDuration(milliseconds)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    # Held on the window so the animation is not collected mid-flight, which
    # would leave the dialog stuck at whatever opacity it had reached.
    window._fade = animation
    return window


def dialog_header(title: str, subtitle: str = ""):
    """A titled band for the top of a dialog.

    Dialogs inherit the palette and the controls from the stylesheet, so they
    were never wrong -- but they opened straight into a form with the only
    clue to their purpose in the window title bar, which on Windows is one
    line of 9pt text somebody has already stopped reading.
    """
    from PyQt6.QtWidgets import QFrame

    band = QFrame()
    band.setObjectName("dialogHeader")
    lay = QVBoxLayout(band)
    lay.setContentsMargins(0, 0, 0, 10)
    lay.setSpacing(2)
    lay.addWidget(label(title, "h1"))
    if subtitle:
        note = label(subtitle, "hint")
        note.setWordWrap(True)
        lay.addWidget(note)
    return band
