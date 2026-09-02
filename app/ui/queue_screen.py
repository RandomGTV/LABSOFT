"""The work queue: what is in the lab, and what each job is waiting for.

Built to artboard 02 of the LabSoft 2026 canvas -- "the board: 40px rows,
progress drawn, overdue says overdue". Four surfaces, top to bottom:

  * a filter bar on paper -- the search box, the four numbers that describe
    the day, and the three things you can do to the selected row;
  * a strip of scopes on the page ground, working like tabs;
  * the board itself, every row painted by :class:`BoardDelegate`;
  * a foot bar carrying the totals and the keys.

Every row is drawn rather than laid out with widgets. Fifteen rows of nine
widgets each is 135 widgets to build, style and throw away on every refresh,
and the queue refreshes whenever anything anywhere changes. The delegate
reads ``style.*`` at paint time, so switching theme repaints correctly with
nothing to rebuild.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from PyQt6.QtCore import QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout, QHeaderView, QStyle, QStyledItemDelegate, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from ..core import billing, turnaround
from ..db import queries as q
from . import style
from .widgets import SearchBox, Table, button, confirm, label, warn

# --- the grid, straight off the artboard -----------------------------------
# 6px stripe | 96 | 1fr | 220 | 116 | 168 | 152 | 128, gutter 12.
STRIPE, C_NO, C_PATIENT, C_TESTS, C_RECEIVED, C_PROGRESS, C_STATUS, \
    C_PAYMENT, C_DUE = range(9)

HEADERS = ["", "Report no", "Patient", "Tests", "Received", "Progress",
           "Status", "Payment", "Due"]

GAP = 12            # the gutter, taken out of the right of every cell
EDGE = 18           # the page margin on the far right of the board
ROW_H = 40
HEAD_H = 32

COL_W = {
    STRIPE: 6 + GAP,
    C_NO: 96 + GAP,
    C_TESTS: 220 + GAP,
    C_RECEIVED: 116 + GAP,
    C_PROGRESS: 168 + GAP,
    C_STATUS: 152 + GAP,
    C_PAYMENT: 116 + GAP,
    C_DUE: 128 + EDGE,
}

#: The whole job dict, hung on every cell of its row so the delegate can draw
#: any column without going back to the model.
ROW_ROLE = Qt.ItemDataRole.UserRole + 1

#: Database status -> the four chips defined in the design system.
CHIP = {
    turnaround.STATUS_DRAFT: ("draft", "REGISTERED"),
    turnaround.STATUS_IN_PROGRESS: ("prog", "IN PROGRESS"),
    turnaround.STATUS_READY: ("ready", "READY TO SEND"),
    turnaround.STATUS_SENT: ("sent", "SENT ✓"),
}

SCOPES = [("today", "Today"), ("pending", "Pending"), ("overdue", "Overdue"),
          ("ready", "Ready to send"), ("unpaid", "Unpaid"), ("all", "All")]


def _font(px: int, weight: int = 400, spacing: float = 0.0) -> QFont:
    """A font in pixels, because the artboard is specified in pixels.

    Qt treats these as logical pixels, so a 150% Windows display still gets a
    150% larger row -- the layout scales, the proportions do not drift.
    """
    f = QFont(style.FONT_FAMILY)
    f.setPixelSize(px)
    f.setWeight(QFont.Weight(weight))
    if spacing:
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 100 + spacing)
    return f


class BoardDelegate(QStyledItemDelegate):
    """Draws one cell of the board.

    Nothing here is cached: colours are read from ``style`` on every paint so
    that a theme change is one repaint away, and a repaint of fifteen rows is
    too cheap to measure.
    """

    def sizeHint(self, option, index) -> QSize:      # noqa: N802 - Qt naming
        return QSize(option.rect.width(), ROW_H)

    # ------------------------------------------------------------------ paint
    def paint(self, painter, option, index) -> None:  # noqa: N802
        job = index.data(ROW_ROLE)
        if not job:
            return super().paint(painter, option, index)

        painter.save()
        painter.setClipRect(option.rect)
        r = option.rect
        chosen = bool(option.state & QStyle.StateFlag.State_Selected)
        late = bool(job.get("late"))

        ground = style.FILL if chosen else (
            style.ALERT_SOFT if late else style.PANEL)
        painter.fillRect(r, QColor(ground))
        painter.fillRect(QRect(r.left(), r.bottom(), r.width(), 1),
                         QColor(style.LINE2))

        col = index.column()
        # The two right-aligned columns share the page margin so that
        # their headers, which are padded by the stylesheet, line up with
        # the values underneath them.
        pad = EDGE if col in (C_PAYMENT, C_DUE) else GAP
        box = QRect(r.left(), r.top(), max(0, r.width() - pad), r.height() - 1)

        if col == STRIPE:
            self._stripe(painter, r, job, chosen)
        elif col == C_NO:
            self._plain(painter, box, str(job["report_no"]),
                        _font(13, 800), style.INK)
        elif col == C_PATIENT:
            self._patient(painter, box, job)
        elif col == C_TESTS:
            self._plain(painter, box, job["tests"], _font(12), style.INK3)
        elif col == C_RECEIVED:
            self._plain(painter, box, job["received"], _font(12), style.INK3)
        elif col == C_PROGRESS:
            self._progress(painter, box, job)
        elif col == C_STATUS:
            self._chip(painter, box, job)
        elif col == C_PAYMENT:
            self._plain(painter, box, job["payment"],
                        _font(12, 700 if job["owing"] else 400),
                        style.INK if job["owing"] else style.INK3,
                        right=True)
        elif col == C_DUE:
            self._plain(painter, box, job["due"], _font(12, 700),
                        job["due_ink"], right=True)
        painter.restore()

    # ------------------------------------------------------------------ parts
    def _stripe(self, painter, r, job, chosen: bool) -> None:
        """The 6px edge: accent when the job is late, ink when it is chosen.

        A late row is already tinted, but tint alone disappears on a projector
        and on the lab's ten-year-old monitor. The bar survives both.
        """
        colour = ""
        if job.get("late"):
            colour = style.ALERT
        elif chosen:
            colour = style.ACCENT_INK
        if colour:
            painter.fillRect(QRect(r.left(), r.top(), 6, r.height()),
                             QColor(colour))

    def _plain(self, painter, box, text, font, colour, right: bool = False) -> None:
        painter.setFont(font)
        painter.setPen(QColor(colour))
        shown = QFontMetrics(font).elidedText(
            str(text or ""), Qt.TextElideMode.ElideRight, box.width())
        flags = Qt.AlignmentFlag.AlignVCenter | (
            Qt.AlignmentFlag.AlignRight if right else Qt.AlignmentFlag.AlignLeft)
        painter.drawText(box, int(flags), shown)

    def _patient(self, painter, box, job) -> None:
        """Name over mobile: two facts, one column, no second lookup.

        The mobile is what the operator reads out to confirm they have the
        right Anil Sharma, so it belongs beside the name and nowhere else.
        """
        name = QRect(box.left(), box.top() + 3, box.width(), 19)
        phone = QRect(box.left(), box.top() + 20, box.width(), 16)
        self._plain(painter, name, job["name"], _font(13, 700), style.INK)
        self._plain(painter, phone, job["phone"], _font(11), style.INK3)

    def _progress(self, painter, box, job) -> None:
        """A drawn bar and the count beside it.

        "4/6" alone makes the reader do arithmetic on every row. The bar is
        read at a glance and the numbers settle the ties.
        """
        count_w = 34
        track_w = max(20, box.width() - 9 - count_w)
        y = box.center().y() - 2
        painter.fillRect(QRect(box.left(), y, track_w, 6), QColor(style.TRACK))
        done = int(job["n_done"] or 0)
        total = int(job["n_tests"] or 0)
        if total > 0 and done > 0:
            width = max(2, int(round(track_w * min(1.0, done / total))))
            painter.fillRect(QRect(box.left(), y, width, 6),
                             QColor(style.ALERT if job.get("late")
                                    else style.ACCENT_INK))
        self._plain(painter,
                    QRect(box.right() - count_w, box.top(), count_w, box.height()),
                    f"{done}/{total}", _font(12, 700), style.INK, right=True)

    def _chip(self, painter, box, job) -> None:
        kind, text = CHIP.get(job["status"],
                              ("draft", turnaround.status_label(job["status"]).upper()))
        fg, bg, edge = style.status_fill(kind)
        font = _font(11, 800, 5)
        metrics = QFontMetrics(font)
        width = min(box.width(), metrics.horizontalAdvance(text) + 8 + 7 + 7 + 9)
        chip = QRect(box.left(), box.center().y() - 10, width, 21)
        painter.fillRect(chip, QColor(bg))
        painter.setPen(QColor(edge))
        painter.drawRect(chip.adjusted(0, 0, -1, -1))
        painter.fillRect(QRect(chip.left() + 8, chip.center().y() - 3, 7, 7),
                         QColor(fg))
        self._plain(painter,
                    QRect(chip.left() + 22, chip.top(), chip.width() - 26, chip.height()),
                    text, font, fg)


class Board(Table):
    """The list itself: fixed 40px rows on the artboard's grid."""

    def __init__(self) -> None:
        super().__init__(HEADERS, stretch_column=C_PATIENT)
        self.setObjectName("boardTable")
        self.setItemDelegate(BoardDelegate(self))
        self.setShowGrid(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        vertical = self.verticalHeader()
        vertical.setDefaultSectionSize(ROW_H)
        vertical.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        head = self.horizontalHeader()
        head.setFixedHeight(HEAD_H)
        head.setFont(_font(10, 800, 14))
        head.setDefaultAlignment(Qt.AlignmentFlag.AlignVCenter
                                 | Qt.AlignmentFlag.AlignLeft)
        for column, width in COL_W.items():
            head.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(column, width)
        head.setSectionResizeMode(C_PATIENT, QHeaderView.ResizeMode.Stretch)
        for column in (C_PAYMENT, C_DUE):
            item = self.horizontalHeaderItem(column)
            if item is not None:
                item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight
                                          | Qt.AlignmentFlag.AlignVCenter))
        self.setHorizontalHeaderLabels([h.upper() for h in HEADERS])

    def set_jobs(self, jobs: List[dict]) -> None:
        """Hang one dict on every cell of its row; the delegate does the rest."""
        self.setUpdatesEnabled(False)
        try:
            self.setRowCount(len(jobs))
            for r, job in enumerate(jobs):
                for c in range(len(HEADERS)):
                    item = QTableWidgetItem("")
                    item.setData(ROW_ROLE, job)
                    self.setItem(r, c, item)
                self.setRowHeight(r, ROW_H)
            self._refresh_empty()
        finally:
            self.setUpdatesEnabled(True)


class StatBlock(QWidget):
    """One of the four numbers over the board, and a way into that scope."""

    clicked = pyqtSignal(str)

    def __init__(self, caption: str, note: str, scope: str):
        super().__init__()
        self.scope = scope
        self.value = label("0", "statvalue")
        self.note = label(note, "statnote")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(label(caption, "statlabel"))
        line = QHBoxLayout()
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(7)
        line.addWidget(self.value)
        line.addWidget(self.note, 0, Qt.AlignmentFlag.AlignBottom)
        line.addStretch(1)
        lay.addLayout(line)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Show only these ({caption.lower()})")

    def set_value(self, value: int, note: str = "", alert: bool = False) -> None:
        self.value.setText(str(value))
        if note:
            self.note.setText(note)
        # A dynamic property needs the style re-read to take effect; without
        # the unpolish/polish pair the number would stay whatever colour it
        # was when the screen was built.
        self.value.setProperty("alert", "true" if alert else "false")
        self.value.style().unpolish(self.value)
        self.value.style().polish(self.value)

    def mousePressEvent(self, event):            # noqa: N802 - Qt naming
        self.clicked.emit(self.scope)
        super().mousePressEvent(event)


class QueueScreen(QWidget):
    open_job = pyqtSignal(int)
    send_job = pyqtSignal(int)
    preview_job = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scope = "today"
        self.rows: List[dict] = []
        self._build()
        self.refresh()

    # ----------------------------------------------------------------- layout
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_filter_bar())
        lay.addWidget(self._build_scope_strip())

        self.table = Board()
        self.table.doubleClicked.connect(self._open_selected)
        lay.addWidget(self.table, 1)
        lay.addWidget(self._build_foot())

        # The keys the foot bar promises. Bound to the board rather than the
        # screen so that Space still types a space in the search box.
        QShortcut(QKeySequence(Qt.Key.Key_Space), self.table,
                  activated=self._open_selected,
                  context=Qt.ShortcutContext.WidgetShortcut)
        QShortcut(QKeySequence(Qt.Key.Key_Return), self.table,
                  activated=self._open_selected,
                  context=Qt.ShortcutContext.WidgetShortcut)
        # Ctrl+P is not bound here: the Preview button already carries it, and
        # two owners of one sequence make Qt fire neither.
        QShortcut(QKeySequence(Qt.Key.Key_F5), self, activated=self.refresh,
                  context=Qt.ShortcutContext.WidgetWithChildrenShortcut)

    def _build_filter_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("filterBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(20)

        self.search = SearchBox("Report no, name or mobile — filters as you type")
        self.search.searched.connect(lambda _t: self.refresh())
        self.search.setFixedWidth(320)
        self.search.setFixedHeight(34)
        search_box = QWidget()
        sbl = QVBoxLayout(search_box)
        sbl.setContentsMargins(0, 0, 0, 0)
        sbl.setSpacing(5)
        sbl.addWidget(label("Search", "statlabel"))
        sbl.addWidget(self.search)
        lay.addWidget(search_box, 0, Qt.AlignmentFlag.AlignVCenter)

        self.stats: Dict[str, StatBlock] = {}
        stats_row = QWidget()
        srl = QHBoxLayout(stats_row)
        srl.setContentsMargins(8, 0, 0, 0)
        srl.setSpacing(36)
        for caption, note, scope, key in (
                ("Waiting", "no results yet", "pending", "waiting"),
                ("In progress", "part entered", "pending", "in_progress"),
                ("Ready to send", "verified", "ready", "ready"),
                ("Overdue", "nothing late", "overdue", "overdue")):
            block = StatBlock(caption, note, scope)
            block.clicked.connect(self._set_scope)
            self.stats[key] = block
            srl.addWidget(block)
        lay.addWidget(stats_row, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addStretch(1)

        self.revise_button = button("Correct && reissue", "", self._revise_selected)
        self.send_button = button("Send / reprint", "", self._send_selected)
        self.open_button = button("Open · Space", "go", self._open_selected)
        self.preview_button = button("Preview", "quiet", self._preview_selected,
                                     shortcut="Ctrl+P")
        for b in (self.preview_button, self.revise_button, self.send_button,
                  self.open_button):
            b.setFixedHeight(32)
            lay.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.setSpacing(9)
        return bar

    def _build_scope_strip(self) -> QWidget:
        strip = QWidget()
        strip.setObjectName("scopeStrip")
        strip.setFixedHeight(34)
        lay = QHBoxLayout(strip)
        lay.setContentsMargins(18, 0, 18, 0)
        lay.setSpacing(4)

        self.scope_buttons: Dict[str, object] = {}
        for key, text in SCOPES:
            b = button(text)
            b.setCheckable(True)
            b.setFixedHeight(24)
            b.clicked.connect(lambda _c=False, k=key: self._set_scope(k))
            self.scope_buttons[key] = b
            lay.addWidget(b)
        self.scope_buttons["today"].setChecked(True)
        lay.addStretch(1)
        self.showing = label("", "foot")
        lay.addWidget(self.showing)
        return strip

    def _build_foot(self) -> QWidget:
        foot = QWidget()
        foot.setObjectName("footBar")
        foot.setFixedHeight(40)
        lay = QHBoxLayout(foot)
        lay.setContentsMargins(18, 0, 18, 0)
        lay.setSpacing(20)
        # The day's counts are on the window's status line, which every screen
        # shares. Printing them here as well gave the operator two rows of the
        # same numbers and a moment's doubt about which to believe, so these
        # two are kept for the tests and for whoever reads them in code, and
        # are not shown.
        self.counts = label("", "foot")
        self.late_note = label("", "foot")
        self.counts.hide()
        self.late_note.hide()
        lay.addStretch(1)
        self.delete_button = button("Delete", "quiet", self._delete_selected)
        lay.addWidget(self.delete_button)
        lay.addWidget(label(
            "Space opens · Ctrl+P prints · F5 re-reads the file", "foot"))
        return foot

    # ------------------------------------------------------------------- data
    def _set_scope(self, scope: str) -> None:
        self.scope = scope
        for key, b in self.scope_buttons.items():
            b.setChecked(key == scope)
        self.refresh()

    def refresh(self) -> None:
        term = self.search.text().strip()
        self.rows = q.list_jobs(self.scope, term)
        self.table.set_jobs([self._painted(j) for j in self.rows])
        self.table.set_empty_text(self._empty_message(term))
        self._refresh_stats(term)

    def _painted(self, job: dict) -> dict:
        """Everything one row needs, worked out once, before any painting."""
        due = q.to_dt(job["due_at"])
        late = turnaround.is_overdue(due, job["status"])
        paid = int(job.get("paid_paise") or 0)
        net = job.get("net_paise")
        owing = 0 if net is None else max(0, int(net) - paid)

        if net is None:
            payment = "—"
        elif owing:
            payment = f"{billing.format_rupees(owing)} due"
        else:
            payment = "Paid"

        return {
            "id": job["id"],
            "report_no": job["report_no"],
            "name": job["patient_name"] or "",
            "phone": job["patient_phone"] or "",
            "tests": (job["test_names"] or "").replace(", ", " · "),
            "received": self._clock(q.to_dt(job["received_at"])),
            "n_done": job["n_done"],
            "n_tests": job["n_tests"],
            "status": job["status"],
            "payment": payment,
            "owing": bool(owing),
            "late": late,
            "due": self._due_text(job, due, late),
            "due_ink": (style.ALERT if late else
                        (style.INK3 if job["status"] == turnaround.STATUS_SENT
                         else style.INK)),
        }

    @staticmethod
    def _clock(when: Optional[datetime]) -> str:
        """Today is a time; any other day needs its date to mean anything."""
        if not when:
            return ""
        if when.date() == datetime.now().date():
            return when.strftime("%H:%M")
        return when.strftime("%d-%m %H:%M")

    def _due_text(self, job: dict, due: Optional[datetime], late: bool) -> str:
        """The column says what happened, not just when.

        A red timestamp asks the reader to work out that it is in the past.
        "overdue 1h 12m" does not.
        """
        if job["status"] == turnaround.STATUS_SENT:
            sent = q.to_dt(job.get("sent_at")) or q.to_dt(job.get("reported_at"))
            return f"delivered {self._clock(sent)}" if sent else "delivered"
        if not due:
            return ""
        if late:
            return "overdue " + turnaround.humanise_delta(due).replace(" late", "")
        text = turnaround.humanise_delta(due)
        if text.endswith(" late"):
            # A finished job past its time is not overdue -- the work is done --
            # but "22m late" against a verified report reads as a failure that
            # is nobody's to fix. What is actually outstanding is the sending.
            return "send now"
        return text

    def _refresh_stats(self, term: str) -> None:
        c = q.queue_counts()
        self.stats["waiting"].set_value(c.get("waiting", 0))
        self.stats["in_progress"].set_value(c.get("in_progress", 0))
        self.stats["ready"].set_value(c.get("ready", 0))

        late = c.get("overdue", 0)
        note = "nothing late"
        if late:
            oldest = q.to_dt(q.oldest_overdue_at())
            if oldest:
                note = "oldest " + turnaround.humanise_delta(oldest).replace(" late", "")
        self.stats["overdue"].set_value(late, note, alert=bool(late))

        shown = len(self.rows)
        scope_name = dict(SCOPES).get(self.scope, self.scope).lower()
        self.showing.setText(
            f"{shown} shown · {'matching “%s”' % term if term else scope_name}")
        self.counts.setText(f"{c.get('today', 0)} of {c.get('total', 0)} jobs today")
        self.late_note.setText(f"{late} overdue" if late else "")
        self.late_note.setStyleSheet(
            f"color: {style.ALERT}; font-weight: 700;" if late else "")

    def _empty_message(self, term: str) -> str:
        """Say why the list is empty and what to do, not just show nothing."""
        if term:
            return (f"No job matches “{term}”.\n\n"
                    "Search by patient name, mobile number, or report number.")
        return {
            "today": "No patients registered today.\n\n"
                     "Press F2 to start the first one.",
            "pending": "No results are waiting.\n\nEverything registered has "
                       "been entered.",
            "overdue": "Nothing is overdue. ",
            "ready": "No reports are waiting to be sent.",
            "unpaid": "No unpaid bills.",
            "all": "No jobs recorded yet.\n\nPress F2 to register the first "
                   "patient.",
        }.get(self.scope, "Nothing here yet.")

    # --------------------------------------------------------------- actions
    def _selected(self) -> dict | None:
        i = self.table.selected_row()
        if i < 0 or i >= len(self.rows):
            return None
        return self.rows[i]

    def _open_selected(self) -> None:
        j = self._selected()
        if j:
            self.open_job.emit(j["id"])

    def _preview_selected(self) -> None:
        j = self._selected()
        if j:
            self.preview_job.emit(j['id'])

    def _send_selected(self) -> None:
        j = self._selected()
        if not j:
            return
        if j["n_tests"] and j["n_done"] < j["n_tests"]:
            warn(self, "Some tests are still empty",
                 "This job cannot be sent yet, because some tests have no "
                 "result.\n\nClick Open and fill them in.")
            return
        self.send_job.emit(j["id"])

    def _revise_selected(self) -> None:
        j = self._selected()
        if not j:
            return
        if not confirm(
                self, "Correct and reissue this report?",
                f"Report {j['report_no']} will be reissued as revision "
                f"{int(j['revision_no'] or 1) + 1}.\n\n"
                "The original stays exactly as it was sent, and both versions are "
                "kept. Continue?",
                "Correct & reissue"):
            return
        from .. import services

        new_id = services.create_revision(j["id"])
        self.refresh()
        self.open_job.emit(new_id)

    def _delete_selected(self) -> None:
        j = self._selected()
        if not j:
            return
        if j["status"] == turnaround.STATUS_SENT:
            warn(self, "Already sent",
                 "This report has been sent to the patient, so it cannot be "
                 "deleted.\n\nIf a result is wrong, use “Correct & reissue” "
                 "instead. The patient gets a corrected copy and both "
                 "versions are kept.")
            return
        if not confirm(self, "Delete this job?",
                       f"Job {j['report_no']} for {j['patient_name']} and all its "
                       f"results will be removed. This cannot be undone.",
                       "Delete"):
            return
        q.delete_job(j["id"])
        self.refresh()
