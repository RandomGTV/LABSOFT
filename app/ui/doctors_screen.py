"""Doctors — everyone who sends the lab work, and how to reach them.

A split view, the same shape as Patients. The register on the left; on the
right, how to reach the doctor, what their referrals have been worth, and the
jobs themselves.

Kept as its own tab rather than a dialog buried under Tests, because the list
is looked at daily: to ring a doctor about a critical result, to check who
referred a patient, and to settle commissions at the end of the month.
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QStyle, QStyledItemDelegate, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from ..core import billing, turnaround
from ..db import queries as q
from . import style
from .widgets import SearchBox, Table, button, confirm, info, label, row, warn

LIST_W = 348
ROW_H = 68
DOCTOR_ROLE = Qt.ItemDataRole.UserRole + 1

FIGURES = [
    ("Patients sent", "jobs"),
    ("Last referral", "last"),
    ("Billed", "billed"),
    ("Commission", "commission"),
    ("Still owed", "owed"),
]


def _font(px: int, weight: int = 400) -> QFont:
    f = QFont(style.FONT_FAMILY)
    f.setPixelSize(px)
    f.setWeight(QFont.Weight(weight))
    return f


class DoctorDelegate(QStyledItemDelegate):
    """One register row: the doctor, their speciality, and where they work."""

    def sizeHint(self, option, index) -> QSize:       # noqa: N802 - Qt naming
        return QSize(option.rect.width(), ROW_H)

    def paint(self, painter, option, index) -> None:  # noqa: N802
        doctor = index.data(DOCTOR_ROLE)
        if not doctor:
            return super().paint(painter, option, index)

        painter.save()
        painter.setClipRect(option.rect)
        r = option.rect
        chosen = bool(option.state & QStyle.StateFlag.State_Selected)

        painter.fillRect(r, QColor(style.FILL if chosen else style.PANEL))
        painter.fillRect(QRect(r.left(), r.bottom(), r.width(), 1),
                         QColor(style.LINE2))
        if chosen:
            painter.fillRect(QRect(r.left(), r.top(), 3, r.height()),
                             QColor(style.ACCENT_INK))

        left = r.left() + 20
        width = max(40, r.width() - 32)
        sent = doctor["sent"]
        sent_w = QFontMetrics(_font(11)).horizontalAdvance(sent) + 10

        # A hidden doctor is greyed rather than removed, so that reading the
        # list with "Show hidden" on still tells you which is which.
        ink = style.INK if doctor["active"] else style.INK3
        self._text(painter, QRect(left, r.top() + 13, width - sent_w, 20),
                   doctor["name"], _font(14, 600 if chosen else 500), ink)
        self._text(painter, QRect(r.right() - 20 - sent_w, r.top() + 14, sent_w, 18),
                   sent, _font(11), style.INK3, right=True)
        self._text(painter, QRect(left, r.top() + 36, width, 18),
                   doctor["meta"], _font(11), style.INK3)
        painter.restore()

    @staticmethod
    def _text(painter, box, text, font, colour, right: bool = False) -> None:
        painter.setFont(font)
        painter.setPen(QColor(colour))
        shown = QFontMetrics(font).elidedText(
            str(text or ""), Qt.TextElideMode.ElideRight, box.width())
        flags = Qt.AlignmentFlag.AlignVCenter | (
            Qt.AlignmentFlag.AlignRight if right else Qt.AlignmentFlag.AlignLeft)
        painter.drawText(box, int(flags), shown)


class DoctorsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: List[dict] = []
        self.jobs: List[dict] = []
        self.show_hidden = False
        self._build()
        self.refresh()

    # ----------------------------------------------------------------- build
    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_register())
        lay.addWidget(self._build_detail(), 1)

    def _build_register(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("register")
        panel.setFixedWidth(LIST_W)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        head = QFrame()
        head.setObjectName("registerHead")
        head_lay = QVBoxLayout(head)
        head_lay.setContentsMargins(20, 18, 20, 18)
        head_lay.setSpacing(10)

        line = QHBoxLayout()
        line.setContentsMargins(0, 0, 0, 0)
        line.addWidget(label("Doctors", "field"))
        line.addStretch(1)
        self.count_label = label("", "hint")
        line.addWidget(self.count_label)
        head_lay.addLayout(line)

        self.search = SearchBox("Search name, profession, hospital or number…")
        self.search.searched.connect(lambda _t: self.refresh())
        self.search.setFixedHeight(34)
        head_lay.addWidget(self.search)

        self.hidden_button = button("Show hidden", "", self._toggle_hidden,
                                    "Include doctors who have been removed")
        self.hidden_button.setCheckable(True)
        self.add_button = button("Add doctor", "primary", self._new)
        head_lay.addWidget(row(self.add_button,
                               self.hidden_button, None))
        lay.addWidget(head)

        self.table = Table(
            ["Doctor"], stretch_column=0,
            empty_text="No doctors yet.\n\nAdd one, and it appears in the "
                       "“Referred by Dr” list on the job screen.")
        self.table.setObjectName("registerList")
        self.table.setItemDelegate(DoctorDelegate(self.table))
        self.table.horizontalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(ROW_H)
        self.table.itemSelectionChanged.connect(self._doctor_selected)
        self.table.doubleClicked.connect(self._edit)
        lay.addWidget(self.table, 1)
        return panel

    def _build_detail(self) -> QWidget:
        side = QWidget()
        lay = QVBoxLayout(side)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_header())

        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(24, 20, 24, 16)
        body_lay.setSpacing(8)
        body_lay.addWidget(label("Patients they have sent", "field"))

        self.job_table = Table(
            ["Report no", "Date", "Patient", "Billed", "Commission", "Status"],
            stretch_column=2,
            empty_text="No referrals recorded for this doctor yet.")
        for column, width in ((0, 108), (1, 124), (3, 126), (4, 130), (5, 140)):
            self.job_table.setColumnWidth(column, width)
        body_lay.addWidget(self.job_table, 1)
        lay.addWidget(body, 1)

        foot = QWidget()
        foot.setObjectName("footBar")
        foot.setFixedHeight(52)
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(24, 0, 24, 0)
        self.note = label("", "foot")
        fl.addWidget(self.note)
        fl.addStretch(1)
        fl.addWidget(label("Commission is recorded when the bill is saved", "foot"))
        lay.addWidget(foot)
        return side

    def _build_header(self) -> QWidget:
        head = QFrame()
        head.setObjectName("filterBar")
        lay = QVBoxLayout(head)
        lay.setContentsMargins(26, 22, 26, 20)
        lay.setSpacing(16)

        top = QHBoxLayout()
        top.setSpacing(9)
        names = QVBoxLayout()
        names.setContentsMargins(0, 0, 0, 0)
        names.setSpacing(3)
        self.who = label("", "person")
        self.details = label("", "hint")
        names.addWidget(self.who)
        names.addWidget(self.details)
        top.addLayout(names)
        top.addStretch(1)
        self.edit_button = button("Edit details", "", self._edit)
        self.remove_button = button("Remove", "danger", self._remove)
        top.addWidget(self.edit_button, 0, Qt.AlignmentFlag.AlignTop)
        top.addWidget(self.remove_button, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(top)

        figures = QHBoxLayout()
        figures.setContentsMargins(0, 0, 0, 0)
        figures.setSpacing(24)
        self.figures = {}
        for caption, key in FIGURES:
            block = QFrame()
            block.setObjectName("statBlock")
            bl = QVBoxLayout(block)
            bl.setContentsMargins(12, 0, 0, 0)
            bl.setSpacing(0)
            bl.addWidget(label(caption, "statlabel"))
            value = label("—", "figure")
            self.figures[key] = value
            bl.addWidget(value)
            figures.addWidget(block)
        figures.addStretch(1)
        lay.addLayout(figures)
        return head

    # ------------------------------------------------------------------ data
    def refresh(self) -> None:
        self._apply_permissions()
        keep = self._selected()
        term = self.search.text().strip()
        self.rows = q.search_referrers(term, include_inactive=self.show_hidden)
        counts = q.jobs_per_referrer()

        listed = []
        for r in self.rows:
            bits = [b for b in (r["profession"] or "", r["hospital"] or "",
                                r["phone"] or "") if b]
            sent = counts.get(r["id"], 0)
            listed.append({
                "name": r["name"] + ("" if r["active"] else "  · hidden"),
                "meta": " · ".join(bits) or "no details recorded",
                "sent": f"{sent} sent" if sent else "none yet",
                "active": bool(r["active"]),
            })
        self._fill_register(listed)

        self.count_label.setText(
            f"{len(self.rows)} doctor{'s' if len(self.rows) != 1 else ''}")
        if self.rows:
            # Stay on whoever was being read, if they are still in the list.
            index = next((i for i, r in enumerate(self.rows)
                          if keep and r["id"] == keep["id"]), 0)
            self.table.selectRow(index)
        else:
            self._show_doctor(None)

    def _fill_register(self, listed: List[dict]) -> None:
        table = self.table
        table.setUpdatesEnabled(False)
        try:
            table.setRowCount(len(listed))
            for r, doctor in enumerate(listed):
                item = QTableWidgetItem("")
                item.setData(DOCTOR_ROLE, doctor)
                table.setItem(r, 0, item)
                table.setRowHeight(r, ROW_H)
            table._refresh_empty()
        finally:
            table.setUpdatesEnabled(True)

    def _selected(self) -> Optional[dict]:
        i = self.table.selected_row()
        return self.rows[i] if 0 <= i < len(self.rows) else None

    def _doctor_selected(self) -> None:
        self._show_doctor(self._selected())

    def _show_doctor(self, doctor: Optional[dict]) -> None:
        if not doctor:
            self.who.setText("No doctor chosen")
            self.details.setText("Choose someone from the list on the left.")
            for value in self.figures.values():
                value.setText("—")
            self.job_table.set_rows([])
            self.note.setText("")
            self.edit_button.setEnabled(False)
            self.remove_button.setEnabled(False)
            self.jobs = []
            return

        self.edit_button.setEnabled(True)
        self.remove_button.setEnabled(True)
        self.remove_button.setText("Bring back" if not doctor["active"] else "Remove")
        self.who.setText(doctor["name"])
        bits = [doctor["profession"] or "", doctor["qualification"] or "",
                doctor["hospital"] or "", doctor["phone"] or "no contact number"]
        if doctor["commission_percent"]:
            bits.append(f"{doctor['commission_percent']:g}% commission")
        self.details.setText("   ·   ".join(b for b in bits if b))

        totals = q.referrer_totals(doctor["id"])
        last = q.to_dt(totals["last_referral"])
        shown = {
            "jobs": str(totals["jobs"]),
            "last": turnaround.format_date(last) if last else "—",
            "billed": billing.format_rupees(totals["billed_paise"]),
            "commission": billing.format_rupees(totals["commission_paise"]),
            "owed": billing.format_rupees(totals["owed_paise"]),
        }
        for key, text in shown.items():
            widget = self.figures[key]
            widget.setText(text)
            alert = key == "owed" and totals["owed_paise"] > 0
            widget.setProperty("alert", "true" if alert else "false")
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        self.jobs = q.referrer_jobs(doctor["id"])
        colours = {}
        rows = []
        for i, j in enumerate(self.jobs):
            rows.append([
                j["report_no"],
                turnaround.format_date(q.to_dt(j["received_at"])),
                j["patient_name"],
                billing.format_rupees(int(j["net_paise"])),
                billing.format_rupees(int(j["commission_paise"])),
                turnaround.status_label(j["status"]),
            ])
            if j["status"] == turnaround.STATUS_SENT:
                colours[i] = QColor(style.GREEN)
        self.job_table.set_rows(rows, colours)
        self.note.setText(
            "This doctor is hidden — they will not appear when choosing a "
            "referring doctor" if not doctor["active"]
            else f"{len(self.jobs)} referral"
                 f"{'s' if len(self.jobs) != 1 else ''} listed")

    def _toggle_hidden(self) -> None:
        self.show_hidden = self.hidden_button.isChecked()
        self.hidden_button.setText("Hide removed" if self.show_hidden
                                   else "Show hidden")
        self.refresh()

    # --------------------------------------------------------------- actions
    def _apply_permissions(self) -> None:
        """Grey the buttons somebody may not press, as well as guarding them.

        A guard alone turns every press into a refusal dialog; greying alone
        is not a check. Both.
        """
        from ..core import auth

        allowed = auth.can(auth.P_TESTS)
        for name in ("add_button", "edit_button", "remove_button"):
            b = getattr(self, name, None)
            if b is not None:
                b.setEnabled(allowed)
                if not allowed:
                    b.setToolTip("Needs the tests permission — a doctor's "
                                 "commission rate is money.")

    def _may_edit(self) -> bool:
        """A commission rate is money, and auth.py puts doctors under P_TESTS.

        The tab is only offered to someone holding it, but a screen that hides
        a button has not checked anything.
        """
        from ..core import auth

        if auth.can(auth.P_TESTS):
            return True
        warn(self, "Not allowed",
             "Adding or changing a referring doctor needs the tests "
             "permission, because it sets the commission they are owed.")
        return False

    def _new(self) -> None:
        if not self._may_edit():
            return
        from .referrers_dialog import ReferrerEditor

        if ReferrerEditor(None, self).exec():
            self.search.clear()
            self.refresh()

    def _edit(self) -> None:
        if not self._may_edit():
            return
        from .referrers_dialog import ReferrerEditor

        r = self._selected()
        if not r:
            warn(self, "Nothing chosen", "Pick a doctor in the list first.")
            return
        if ReferrerEditor(r, self).exec():
            self.refresh()

    def _remove(self) -> None:
        if not self._may_edit():
            return
        r = self._selected()
        if not r:
            warn(self, "Nothing chosen", "Pick a doctor in the list first.")
            return
        if not r["active"]:
            q.save_referrer({**dict(r), "active": 1})
            self.refresh()
            info(self, "Back in the list",
                 f"{r['name']} will appear again when choosing a referring doctor.")
            return

        owed = q.commission_owed(r["id"])
        extra = ""
        if owed:
            extra = (f"\n\n{billing.format_rupees(owed)} of commission is still "
                     f"recorded against them — that stays on the books.")
        if not confirm(self, "Remove this doctor?",
                       f"{r['name']} will stop appearing when you choose a "
                       f"referring doctor.\n\nJobs already sent by them keep "
                       f"their record, and you can bring them back with "
                       f"“Show hidden”.{extra}", "Remove"):
            return
        q.delete_referrer(r["id"])
        self.refresh()
