"""The job screen: register, choose tests, and enter results without leaving.

The lab asked for one screen rather than three, so this is the primary screen of
the program. Three bands stacked top to bottom:

    patient  ->  tests  ->  results

The results grid appears as soon as the first test is chosen. Values are written
to the database as each box is left, not on Save, so a crash mid-entry loses
nothing. Derived tests fill themselves in and cannot be typed into.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QComboBox, QCompleter, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLayout, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QProgressBar,
    QScrollArea, QSizePolicy, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from .. import services
from ..core import turnaround
from ..db import queries as q
from . import icons, style
from .pos_receipt_dialog import POSReceiptDialog
from .whatsapp_dialog import WhatsAppDialog
from .widgets import (
    EllipsisLabel, FlagLabel, SearchBox, age_unit_combo, button, column,
    confirm, error, field_label, hline, info, label, row, sex_combo, warn,
)


#: Result-field column widths, in pixels. The header row and every result row
#: use the same numbers, which is the only way a QGridLayout and a separate
#: header bar can stay in step.
LEFT_RAIL_W = 400
RESULT_W = 150
UNIT_W = 78
RANGE_W = 132
FLAG_W = 78
MENU_W = 34
ROW_H = 52


class FlowLayout(QLayout):
    """Left-to-right layout that wraps, for the panel buttons.

    Qt has no flow layout of its own, and a QHBoxLayout of twelve panel names
    either overflows the rail or squeezes every button until the labels elide.
    """

    def __init__(self, parent=None, spacing: int = 7):
        super().__init__(parent)
        self._items: List = []
        self._space = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):                      # noqa: N802 - Qt naming
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index):                      # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):                      # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):                # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:          # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):                  # noqa: N802
        super().setGeometry(rect)
        self._layout(rect, test_only=False)

    def sizeHint(self):                           # noqa: N802
        return self.minimumSize()

    def minimumSize(self):                        # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _layout(self, rect, test_only: bool) -> int:
        x, y, line_height = rect.x(), rect.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + self._space
            if next_x - self._space > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + self._space
                next_x = x + hint.width() + self._space
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y()


class ResultRow:
    """One line in the results grid."""

    def __init__(self, test: dict, on_changed, on_focus):
        self.test = test
        self.job_test_id = test["job_test_id"]
        self.is_derived = bool((test["formula"] or "").strip())
        rtype = (test["result_type"] or "numeric").strip().lower()
        self.is_heading = (rtype == "heading")

        self.name_label = EllipsisLabel(test["name"])
        # Stated outright rather than inherited, so no theme can render these
        # dark-on-dark.
        self.name_label.setStyleSheet(f"color: {style.INK}; background: transparent;")
        if self.is_heading:
            f = QFont()
            f.setBold(True)
            f.setPointSizeF(9.5)
            self.name_label.setFont(f)
            self.name_label.setStyleSheet(
                f"color: {style.INK}; font-weight: 700; background: transparent; padding-top: 5px;")
        elif self.is_derived:
            f = QFont()
            f.setItalic(True)
            self.name_label.setFont(f)
            self.name_label.setToolTip(f"Calculated: {test['formula']}")
            self.name_label.setStyleSheet(
                f"color: {style.INK2}; background: transparent;")

        self.editor: QWidget
        if self.is_heading:
            dummy = QWidget()
            dummy.setFixedWidth(0)
            dummy.hide()
            self.editor = dummy
        elif self.is_derived:
            e = QLineEdit()
            e.setReadOnly(True)
            e.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            e.setToolTip(f"Calculated from: {test['formula']}")
            self.editor = e
        elif rtype == "option" and (test["options"] or "").strip():
            c = QComboBox()
            c.setEditable(True)
            c.addItem("")
            c.addItems([o.strip() for o in test["options"].split("|") if o.strip()])
            # Deliberately NOT currentTextChanged: that fires on every keystroke,
            # so typing "Reactive" saved "R" and then rebuilt the row underneath
            # the operator's fingers. Fire when a choice is made or the box is left.
            c.currentIndexChanged.connect(lambda _i: on_changed())
            if c.lineEdit() is not None:
                c.lineEdit().editingFinished.connect(on_changed)
            self.editor = c
        else:
            e = QLineEdit()
            e.setProperty("kind", "result_entry")
            e.editingFinished.connect(on_changed)
            self.editor = e

        # The value is what the row is for, so it gets the size to say so:
        # a 40px box against an 11px unit and range.
        self.editor.setFixedWidth(RESULT_W)
        if not self.is_heading:
            self.editor.setFixedHeight(40)
        # Named for assistive technology: without this a screen reader announces
        # a row of identical unlabelled edit boxes.
        self.editor.setAccessibleName(f"{test['name']} result")
        unit = (test["unit"] or "").strip()
        self.editor.setAccessibleDescription(
            f"Enter the {test['name']} result{' in ' + unit if unit else ''}")

        self.unit_label = QLabel(test["unit"] or "")
        self.unit_label.setFixedWidth(UNIT_W)
        self.unit_label.setStyleSheet(
            f"color: {style.INK3}; background: transparent; font-size: 8.5pt;")
        self.range_label = QLabel("")
        self.range_label.setFixedWidth(RANGE_W)
        self.range_label.setStyleSheet(
            f"color: {style.INK3}; background: transparent; font-size: 8.5pt;")
        self.flag_label = FlagLabel()
        self.flag_label.setFixedWidth(FLAG_W)

        # How the value was arrived at, under the name. It answers the question
        # a clinician rings up to ask, without anybody opening the test master.
        method = (test.get("formula") or "").strip()
        self.method_label = QLabel(f"Calculated · {method}" if method else "")
        self.method_label.setProperty("role", "method")
        self.method_label.setStyleSheet(
            f"color: {style.INK3}; background: transparent; font-size: 8pt;")
        self.method_label.setVisible(bool(method))

        # Delta check label for historical comparison
        self.delta_label = QLabel("")
        # Drawn as a square edged block, the same shape as a result flag, so
        # the two read as one family rather than two unrelated badges.
        _delta_bg, _delta_edge = style.flag_fill("L")
        self.delta_label.setStyleSheet(
            f"color: {style.BLUE}; background: {_delta_bg}; "
            f"border: 1px solid {_delta_edge}; border-radius: 0; "
            f"padding: 1px 5px; font-size: 8pt; font-weight: 700;")
        self.delta_label.setVisible(False)

        self.not_done = bool(test.get("not_done"))

    def set_not_done(self, flag: bool) -> None:
        """A test that could not be run: kept on the job, left off the report."""
        self.not_done = bool(flag)
        self.editor.setEnabled(not flag)
        if flag:
            self.name_label.setStyleSheet(
                f"color: {style.INK3}; background: transparent; "
                f"text-decoration: line-through;")
            self.range_label.setText("not done")
            self.flag_label.set_flag("")
        else:
            self.name_label.setStyleSheet(
                f"color: {style.INK}; background: transparent;")

    def value(self) -> str:
        if isinstance(self.editor, QComboBox):
            return self.editor.currentText().strip()
        return self.editor.text().strip()

    def set_value(self, text: str) -> None:
        blocked = self.editor.blockSignals(True)
        if isinstance(self.editor, QComboBox):
            self.editor.setCurrentText(text or "")
        else:
            self.editor.setText(text or "")
        self.editor.blockSignals(blocked)


class JobScreen(QWidget):
    """Register a patient, pick tests, enter results, produce the report."""

    job_changed = pyqtSignal()
    request_send = pyqtSignal(int)     # job_id
    request_preview = pyqtSignal(int)  # job_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.job_id: Optional[int] = None
        self.patient_id: Optional[int] = None
        self.test_ids: List[int] = []
        self.rows: Dict[int, ResultRow] = {}
        self._loading = False

        self._build()
        self.new_job()

    # ------------------------------------------------------------------ build
    def _build(self) -> None:
        """The screen, in four surfaces of falling weight.

        A status rail states where the job stands; an ink money band states
        what is owed; a white field takes the results; a quiet column on the
        right carries what is blocking, what happened last visit, and the
        keys. Reception reads the rail, the technologist reads the field, and
        neither has to hunt through boxes of equal weight to find their half
        of the screen.
        """
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_status_rail())

        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)
        body_lay.addWidget(self._build_left_rail())

        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)
        right_lay.addWidget(self._build_bill())
        right_lay.addWidget(self._build_results(), 1)
        body_lay.addWidget(right, 1)

        outer.addWidget(body, 1)

    # -- the rail across the top ---------------------------------------
    def _build_status_rail(self) -> QWidget:
        """Report number, patient, due, state, progress, and the way out.

        One region instead of four: the number was top-left, the state
        top-right, the counter bottom-right and the blocker below that, so
        answering "where is this job?" meant reading three corners.
        """
        rail = QFrame()
        rail.setObjectName("statusRail")
        rail.setFixedHeight(64)
        lay = QHBoxLayout(rail)
        lay.setContentsMargins(0, 0, 16, 0)
        lay.setSpacing(16)

        # Who this job is for, on the same filled ground as the column beneath
        # it, so the two read as one panel rather than two strips that happen
        # to touch.
        who = QFrame()
        who.setObjectName("railLeft")
        who.setFixedWidth(LEFT_RAIL_W)
        who_lay = QHBoxLayout(who)
        who_lay.setContentsMargins(16, 8, 12, 8)
        who_lay.setSpacing(14)

        self.report_no_label = label("—", "railvalue")
        who_lay.addLayout(self._rail_item("Report no", self.report_no_label))
        who_lay.addWidget(self._rail_divider())

        self.title = EllipsisLabel("New job")
        self.title.setProperty("role", "railname")
        who_lay.addLayout(self._rail_item("Patient", self.title), 1)
        who_lay.addWidget(self._rail_divider())

        self.due_label = EllipsisLabel("—")
        self.due_label.setProperty("role", "hint")
        self.due_label.setMinimumWidth(120)
        who_lay.addLayout(self._rail_item("Due", self.due_label), 1)
        lay.addWidget(who)

        self.status_label = label("", "hint")
        self.progress_label = label("", "hint")
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(5)
        self.progress.setFixedWidth(150)
        self.progress.hide()

        state = QVBoxLayout()
        state.setContentsMargins(0, 0, 0, 0)
        state.setSpacing(3)
        state.addWidget(self.status_label)
        state.addWidget(self.progress_label)
        state.addWidget(self.progress)
        lay.addLayout(state)

        lay.addStretch(1)
        self.message = label("", "hint")
        self.message.setWordWrap(True)
        self.message.setMaximumWidth(260)
        lay.addWidget(self.message)

        self.clear_button = button("New job", "", self.new_job, "Start a fresh job (F2)"); self.clear_button.setIcon(icons.get_icon("new_job", style.INK2, 16))
        self.whatsapp_button = button("WhatsApp", "", self._open_whatsapp_dispatch, "Send structured WhatsApp report", "F8"); self.whatsapp_button.setIcon(icons.get_icon("whatsapp", style.GREEN, 16))
        self.preview_button = button("Preview", "", self.preview, "Look at the report before sending it"); self.preview_button.setIcon(icons.get_icon("preview", style.INK2, 16))
        self.verify_button = button("Check && make report", "go", self.verify, "Check every test is filled in, then make the report", "F9"); self.verify_button.setIcon(icons.get_icon("check_report", style.ON_ACCENT, 16))
        for b in (self.clear_button, self.whatsapp_button, self.preview_button, self.verify_button):
            lay.addWidget(b)
        return rail

    def _rail_item(self, caption: str, value: QWidget) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(1)
        col.addWidget(label(caption, "micro"))
        col.addWidget(value)
        return col

    def _rail_divider(self) -> QWidget:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFixedWidth(1)
        line.setStyleSheet(f"color: {style.LINE}; background: {style.LINE};")
        return line

    # -- the left rail: who, and what they are having ------------------
    def _build_left_rail(self) -> QWidget:
        rail = QFrame()
        rail.setObjectName("leftRail")
        rail.setFixedWidth(LEFT_RAIL_W)
        lay = QVBoxLayout(rail)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_patient())
        lay.addWidget(self._build_tests(), 1)
        return rail

    def _build_patient(self) -> QWidget:
        box = QFrame()
        box.setObjectName("patientBlock")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(9)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Patient name")
        self.name_edit.setAccessibleName("Patient name")
        self.name_edit.textEdited.connect(self._on_name_typed)
        self.name_edit.textEdited.connect(lambda _t: self._refresh_printed_name())

        # The initial is kept apart from the name so it can be searched on and
        # printed in the right place: FARAS .M. Kutty, never FARAS Kutty M.
        self.initial_edit = QLineEdit()
        self.initial_edit.setPlaceholderText("M")
        self.initial_edit.setAccessibleName("Patient initial")
        self.initial_edit.setMaxLength(4)
        self.initial_edit.setToolTip("The letter between the names — FARAS .M. Kutty")
        self.initial_edit.textEdited.connect(lambda _t: self._refresh_printed_name())

        self.name_matches = QListWidget()
        self.name_matches.setMaximumHeight(112)
        self.name_matches.hide()
        self.name_matches.itemClicked.connect(self._pick_existing_patient)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("Mobile number")
        self.phone_edit.setAccessibleName("Patient mobile number")
        self.phone_edit.textEdited.connect(lambda _t: self._refresh_printed_name())

        self.sex_combo = sex_combo()
        self.sex_combo.setAccessibleName("Patient sex")
        self.sex_combo.currentTextChanged.connect(lambda _t: self._recalc())
        self.sex_combo.currentTextChanged.connect(
            lambda _t: self._refresh_printed_name())

        self.age_spin = QSpinBox()
        self.age_spin.setAccessibleName("Patient age")
        self.age_spin.setRange(0, 130)
        self.age_spin.valueChanged.connect(lambda _v: self._recalc())

        self.age_unit = age_unit_combo()
        self.age_unit.currentTextChanged.connect(lambda _t: self._recalc())

        # A chooser, not a free-text box: a doctor picked from the list carries
        # their hospital and commission with them, where a retyped name makes a
        # second doctor who happens to be spelled the same.
        self.referrer_combo = QComboBox()
        self.referrer_combo.setAccessibleName("Referring doctor")
        self.referrer_combo.activated.connect(self._referrer_chosen)

        self.history_button = button("Patient history →", "quiet", self._open_history)
        self.history_button.setEnabled(False)

        lay.addWidget(row(label("Patient", "micro"), None, self.history_button))

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)
        grid.addWidget(label("Name", "micro"), 0, 0)
        grid.addWidget(label("Initial", "micro"), 0, 1)
        grid.addWidget(self.name_edit, 1, 0)
        grid.addWidget(self.initial_edit, 1, 1)
        grid.addWidget(label("Mobile", "micro"), 2, 0)
        grid.addWidget(label("Sex", "micro"), 2, 1)
        grid.addWidget(self.phone_edit, 3, 0)
        grid.addWidget(self.sex_combo, 3, 1)
        grid.addWidget(label("Age", "micro"), 4, 0)
        grid.addWidget(label("Referred by", "micro"), 4, 1)
        age_row = row(self.age_spin, self.age_unit)
        grid.addWidget(age_row, 5, 0)
        grid.addWidget(self.referrer_combo, 5, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)
        self.initial_edit.setMaximumWidth(84)
        lay.addLayout(grid)

        self.printed_name = label("", "hint")
        self.printed_name.setWordWrap(True)
        lay.addWidget(self.printed_name)
        lay.addWidget(self.name_matches)
        return box

    def printed_name_text(self) -> str:
        """The patient's name exactly as it will appear on the report."""
        return q.full_name(self.name_edit.text(), self.initial_edit.text())

    def _refresh_printed_name(self) -> None:
        """Show what will print, or what is still needed before it can.

        Beside the boxes rather than only in the dialog at the end, so nobody
        types a full set of results and only then discovers the job cannot be
        finished.
        """
        shown = self.printed_name_text()
        initial = self.initial_edit.text().strip()
        printed = f"Prints as:  {shown}" if shown and initial else ""

        problem = self.patient_problem()
        if problem and self.name_edit.text().strip():
            self.printed_name.setText(
                "   ·   ".join(x for x in
                               (printed, f"Still needed:  {problem[0]}") if x))
            self.printed_name.setStyleSheet(
                f"color: {style.AMBER}; font-weight: 600;")
        else:
            self.printed_name.setStyleSheet("")
            self.printed_name.setProperty("role", "hint")
            self.printed_name.setText(printed)
        self._refresh_counsel()

    def _build_tests(self) -> QWidget:
        box = QFrame()
        box.setObjectName("testsBlock")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(8)

        self.tests_count = label("", "hint")
        self.repeat_button = button(
            "Repeat last visit", "", self._repeat_last_tests,
            "Add exactly the tests this patient had last time")
        self.repeat_row = row(self.repeat_button, None)
        self.repeat_row.hide()
        lay.addWidget(row(label("Tests", "micro"), 8, self.tests_count, None))
        lay.addWidget(self.repeat_row)

        self.test_search = SearchBox("Type to add a test — filters as you type")
        self.test_search.searched.connect(self._search_tests)
        self.test_search.returnPressed.connect(self._add_first_match)

        self.test_matches = QListWidget()
        self.test_matches.setMaximumHeight(130)
        self.test_matches.hide()
        self.test_matches.itemActivated.connect(self._add_from_match)
        self.test_matches.itemClicked.connect(self._add_from_match)

        lay.addWidget(self.test_search)
        lay.addWidget(self.test_matches)

        # The panel buttons wrap, so the rail can be narrow without them
        # spilling off the side.
        self.panel_bar = QWidget()
        self.panel_layout = FlowLayout(self.panel_bar, spacing=7)
        lay.addWidget(self.panel_bar)
        lay.addStretch(1)
        return box

    # -- the money band ------------------------------------------------
    def _build_bill(self) -> QWidget:
        """What is owed, in ink, at the size the counter argues about."""
        self.bill_box = QFrame()
        self.bill_box.setObjectName("moneyBand")
        self.bill_box.setFixedHeight(96)
        lay = QHBoxLayout(self.bill_box)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(28)

        self.bill_summary = label("—", "money")
        net = QVBoxLayout()
        net.setContentsMargins(0, 0, 0, 0)
        net.setSpacing(0)
        net.addWidget(label("Net payable", "micro"))
        net.addWidget(self.bill_summary)
        lay.addLayout(net)

        self.bill_stats: Dict[str, QLabel] = {}
        for caption in ("Charged", "Discount", "Paid", "Outstanding"):
            value = label("—", "stat")
            self.bill_stats[caption] = value
            col = QVBoxLayout()
            col.setContentsMargins(0, 0, 0, 0)
            col.setSpacing(0)
            col.addWidget(label(caption, "micro"))
            col.addWidget(value)
            lay.addLayout(col)

        lay.addStretch(1)
        self.bill_hint = label("", "hint")
        self.bill_hint.setWordWrap(True)
        self.bill_hint.setMaximumWidth(230)
        lay.addWidget(self.bill_hint)

        self.bill_print_button = button("Print bill…", "", self._print_bill, "Show the receipt, then print, save or send it"); self.bill_print_button.setIcon(icons.get_icon("print", style.ON_INK, 16))
        self.bill_button2 = button("Make the bill", "primary", self._open_bill, "Record what is being charged", "F4"); self.bill_button2.setIcon(icons.get_icon("bill", style.INK, 16))
        self.pos_receipt_btn = button("POS Receipt", "", self._open_pos_receipt, "Print 80mm thermal receipt slip"); self.pos_receipt_btn.setIcon(icons.get_icon("pos", style.ON_INK, 16))
        lay.addWidget(self.pos_receipt_btn)
        lay.addWidget(self.bill_print_button)
        lay.addWidget(self.bill_button2)
        return self.bill_box

    def _refresh_bill(self) -> None:
        from ..core import auth, billing

        if not auth.can(auth.P_BILL):
            self.bill_box.hide()
            return
        self.bill_box.show()

        # Nothing to print until the job exists and has tests on it.
        self.bill_print_button.setEnabled(bool(self.job_id and self.test_ids))

        def stats(charged="—", discount="—", paid="—", outstanding="—",
                  due=False) -> None:
            for caption, text in (("Charged", charged), ("Discount", discount),
                                  ("Paid", paid), ("Outstanding", outstanding)):
                cell = self.bill_stats[caption]
                cell.setText(text)
                loud = due and caption in ("Discount", "Outstanding")
                # MONEY_ALERT, not BRAND: see the token's own note. Weight as
                # well as colour, so the two figures that say money is owed
                # read as louder even where the difference is subtle.
                cell.setStyleSheet(
                    f"color: {style.MONEY_ALERT if loud else style.ON_MONEY}; "
                    f"font-size: 12.5pt; font-weight: {800 if loud else 700};")

        if not self.job_id:
            self.bill_summary.setText("—")
            self.bill_hint.setText(
                "Choose the tests, then make the bill before starting work.")
            self.bill_button2.setText("Make the bill")
            stats()
            return

        bill = q.get_bill(self.job_id)
        if not bill:
            expected = sum(int(i["rate_paise"]) for i in
                           services.suggest_bill_items(self.job_id))
            self.bill_summary.setText(billing.format_rupees(expected))
            self.bill_hint.setText("Not billed yet — F4 takes payment.")
            self.bill_button2.setText("Make the bill")
            stats(charged=billing.format_rupees(expected),
                  outstanding=billing.format_rupees(expected), due=True)
            return

        totals = q.bill_totals(self.job_id)
        paid = totals.balance_paise <= 0
        self.bill_summary.setText(billing.format_rupees(totals.net_paise))
        self.bill_hint.setText("Paid in full." if paid else "Balance outstanding.")
        self.bill_button2.setText("Open the bill")
        stats(charged=billing.format_rupees(totals.gross_paise),
              discount=("—" if not totals.discount_paise
                        else "− " + billing.format_rupees(totals.discount_paise)),
              paid=billing.format_rupees(totals.paid_paise),
              outstanding=billing.format_rupees(max(0, totals.balance_paise)),
              due=not paid)

    def _refresh_counsel(self) -> None:
        """Fill the right-hand column: what is blocking, and what came before.

        This is the material an operator would otherwise have to ask someone
        for -- and the reason a wide monitor no longer ends in half a screen
        of nothing.
        """
        blockers: List[str] = []
        problem = self.patient_problem()
        if problem:
            blockers.append(f"·  {problem[0][0].upper()}{problem[0][1:]} is "
                            f"needed before this job can be finished.")
        if self.job_id:
            _complete, missing = q.job_is_complete(self.job_id)
            for name in missing[:3]:
                blockers.append(f"·  {name} has no value yet.")
            if len(missing) > 3:
                blockers.append(f"·  … and {len(missing) - 3} more still empty.")
            if not q.get_bill(self.job_id):
                blockers.append("·  No bill has been made for this job.")
        if not blockers:
            blockers.append("Nothing — this job is ready to go.")
        else:
            blockers.append("")
            blockers.append("Everything typed so far is already saved. "
                            "Leaving now loses nothing.")
        self.blockers.setText("\n".join(blockers))
        self.blockers.setStyleSheet(
            f"color: {style.AMBER if problem else style.INK2};")

        self.last_visit.setText(self._last_visit_text())

    def _last_visit_text(self) -> str:
        if not self.patient_id:
            return "No earlier visit."
        earlier = [j for j in q.patient_jobs(self.patient_id)
                   if j["id"] != self.job_id]
        if not earlier:
            return "No earlier visit."
        last = earlier[0]
        lines = [turnaround.format_date(q.to_dt(last["received_at"]))]
        for t in q.job_tests(last["id"])[:4]:
            r = (q.results_for_job(last["id"]) or {}).get(t["job_test_id"]) or {}
            shown = (r.get("display_value") or "").strip()
            if shown:
                lines.append(f"{t['name']}   {shown}")
        return "\n".join(lines)

    # -- the results field, and the column of counsel beside it --------
    def _build_results(self) -> QWidget:
        wrap = QWidget()
        wrap_lay = QHBoxLayout(wrap)
        wrap_lay.setContentsMargins(0, 0, 0, 0)
        wrap_lay.setSpacing(0)

        self.results_box = QFrame()
        self.results_box.setObjectName("resultsField")
        lay = QVBoxLayout(self.results_box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # A critical value is the one thing on this screen that earns the
        # accent outright, so the banner is named in the sheet and takes the
        # accent from whichever theme is in force.
        self.panic_banner = QFrame()
        self.panic_banner.setObjectName("panicBanner")
        self.panic_banner.setFixedHeight(40)
        panic_lay = QHBoxLayout(self.panic_banner)
        panic_lay.setContentsMargins(18, 2, 18, 2)
        panic_icon = QLabel("!")
        panic_icon.setStyleSheet(
            f"color: {style.ACCENT_INK}; font-size: 15pt; font-weight: 800; "
            f"background: transparent;")
        self.panic_text = QLabel("")
        self.panic_text.setProperty("role", "panic")
        panic_lay.addWidget(panic_icon)
        panic_lay.addWidget(self.panic_text, 1)
        self.panic_banner.hide()
        lay.addWidget(self.panic_banner)

        head = QFrame()
        head.setObjectName("resultsHead")
        head.setFixedHeight(30)
        head_lay = QHBoxLayout(head)
        head_lay.setContentsMargins(18, 0, 18, 0)
        head_lay.setSpacing(12)
        for caption, width in (("Test", 0), ("Result", RESULT_W),
                               ("Unit", UNIT_W), ("Normal range", RANGE_W),
                               ("Flag", FLAG_W)):
            cell = label(caption, "micro")
            if width:
                cell.setFixedWidth(width)
            head_lay.addWidget(cell, 1 if not width else 0)
        head_lay.addSpacing(MENU_W)
        lay.addWidget(head)

        self.empty_hint = label(
            "No tests chosen yet.\n\n"
            "Click a panel on the left, or type a test name — the result boxes "
            "appear here.\n\n"
            "F2 starts a new job.",
            "hint")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.empty_hint, 1)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("resultsScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setAutoFillBackground(True)
        self.grid_host = QWidget()
        self.grid_host.setObjectName("resultsHost")
        self.grid_host.setAutoFillBackground(True)
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(0)
        self.scroll.setWidget(self.grid_host)
        self.scroll.hide()
        lay.addWidget(self.scroll, 1)

        foot = QFrame()
        foot.setObjectName("footBar")
        foot.setFixedHeight(52)
        foot_lay = QHBoxLayout(foot)
        foot_lay.setContentsMargins(18, 0, 18, 0)
        foot_lay.setSpacing(9)
        foot_lay.addWidget(label(
            "Each box saves as you leave it. Nothing waits for a Save.", "hint"))
        foot_lay.addStretch(1)
        self.save_button = button("Save", "", self.save,
                                  "Save without producing a report", "Ctrl+S")
        self.bill_button = button("Bill", "", self._open_bill,
                                  "Record charges (optional)", "F4")
        foot_lay.addWidget(self.save_button)
        foot_lay.addWidget(self.bill_button)
        lay.addWidget(foot)

        wrap_lay.addWidget(self.results_box, 1)
        wrap_lay.addWidget(self._build_counsel())
        return wrap

    def _build_counsel(self) -> QWidget:
        """The third rail: what is blocking, what happened last time, the keys.

        A wide monitor used to end in half a screen of nothing. This is the
        material an operator would otherwise have to ask someone for.
        """
        panel = QFrame()
        panel.setObjectName("counsel")
        panel.setFixedWidth(292)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        block, inner = self._counsel_block("Before it can go")
        self.blockers = label("", "hint")
        self.blockers.setWordWrap(True)
        inner.addWidget(self.blockers)
        lay.addWidget(block)

        block, inner = self._counsel_block("Clinical Remarks & Smear Impression")
        self.remarks_edit = QTextEdit()
        # Tab leaves the box rather than typing a tab into it.
        self.remarks_edit.setTabChangesFocus(True)
        self.remarks_edit.setFixedHeight(72)
        self.remarks_edit.setPlaceholderText("Enter clinical remarks and smear impression...")
        self.remarks_edit.textChanged.connect(self._remarks_changed)
        inner.addWidget(self.remarks_edit)
        lay.addWidget(block)

        block, inner = self._counsel_block("Last visit")
        self.last_visit = label("No earlier visit.", "hint")
        self.last_visit.setWordWrap(True)
        inner.addWidget(self.last_visit)
        lay.addWidget(block)

        block, inner = self._counsel_block("Keyboard")
        for key, what in (("F2", "New job"), ("F4", "Bill"),
                          ("F8", "Preview"), ("F9", "Check & make report"),
                          ("Tab", "Next result box")):
            line = row(label(key, "field"), 10, label(what, "hint"), None)
            inner.addWidget(line)
        lay.addWidget(block)

        lay.addStretch(1)
        return panel

    def _counsel_block(self, caption: str):
        block = QFrame()
        block.setObjectName("counselBlock")
        inner = QVBoxLayout(block)
        inner.setContentsMargins(16, 14, 16, 14)
        inner.setSpacing(7)
        inner.addWidget(label(caption, "micro"))
        return block, inner

    # -------------------------------------------------------------- lifecycle
    def new_job(self) -> None:
        self._loading = True
        self.job_id = None
        self.patient_id = None
        self.test_ids = []
        self.rows = {}
        self.name_edit.clear()
        if hasattr(self, 'remarks_edit'):
            self.remarks_edit.clear()
        self.initial_edit.clear()
        self.printed_name.setText("")
        self.phone_edit.clear()
        self.sex_combo.setCurrentIndex(0)
        self.age_spin.setValue(0)
        self.age_unit.setCurrentIndex(0)
        self.test_search.clear()
        self.test_matches.hide()
        self.name_matches.hide()
        self.history_button.setEnabled(False)
        self.repeat_row.hide()
        self.title.setText("New job")
        self.report_no_label.setText("—")
        self.due_label.setText("")
        self.status_label.setText("")
        self.message.setText("")
        self.message.setStyleSheet("")
        # Cleared explicitly: left alone, the previous patient's doctor was
        # silently attached to the next patient's report and commission.
        self._reload_referrers(keep_id=None)
        self._reload_panels()
        self._rebuild_grid()
        self._loading = False
        self.name_edit.setFocus()

    def load_job(self, job_id: int) -> None:
        job = q.get_job(job_id)
        if not job:
            warn(self, "Job not found", "That job no longer exists.")
            return
        self._loading = True
        self.job_id = job_id
        self.patient_id = job["patient_id"]
        patient = q.get_patient(job["patient_id"]) or {}
        self.name_edit.setText(job["patient_name"] or "")
        self.initial_edit.setText(patient.get("initial", "") or "")
        self._refresh_printed_name()
        self.phone_edit.setText(job["patient_phone"] or "")
        self.sex_combo.setCurrentText(job["patient_sex"] or "")
        # The age recorded ON THIS JOB, not the patient's age today. Reading
        # the patient row showed "3 Years" in the box while the report printed
        # the "10 Days" the job was actually taken at.
        age_value = job["age_value_at_test"]
        age_unit = job["age_unit_at_test"]
        if age_value is None:
            age_value, age_unit = job["age_value"], job["age_unit"]
        self.age_spin.setValue(int(age_value or 0))
        self.age_unit.setCurrentText((age_unit or "Years").title())
        self._reload_referrers(keep_id=job["referrer_id"])
        self._reload_panels()

        self.test_ids = [t["id"] for t in q.job_tests(job_id)]
        self.history_button.setEnabled(True)
        if hasattr(self, 'remarks_edit'):
            self.remarks_edit.setPlainText(job.get('remarks') or '')
        self.repeat_row.setVisible(bool(self._previous_test_ids()))
        self.name_matches.hide()      # leftover suggestions belong to the old job

        # Drop the previous job's rows before rebuilding. _rebuild_grid carries
        # typed values forward by test id, which is right while working on one
        # job and badly wrong when switching to another: one patient's results
        # appeared in another patient's boxes and were saved there.
        self.rows = {}
        self._rebuild_grid()
        self._load_stored_results()
        self._loading = False
        self._refresh_header()

    # ------------------------------------------------------------- patient
    def _on_name_typed(self, text: str) -> None:
        """Offer returning patients from as little as two letters or initials."""
        text = (text or "").strip()
        if len(text) < 2:
            self.name_matches.hide()
            return
        matches = q.search_patients(text, limit=8)
        self.name_matches.clear()
        for p in matches:
            bits = [q.patient_full_name(p)]
            if p["phone"]:
                bits.append(p["phone"])
            age = q._age_text(p)
            if age:
                bits.append(age)
            if p.get("sex"):
                bits.append(p["sex"])
            visits = len(q.patient_jobs(p["id"]))
            if visits:
                bits.append(f"{visits} visit{'s' if visits != 1 else ''}")
            item = QListWidgetItem("   ·   ".join(b for b in bits if b))
            item.setData(Qt.ItemDataRole.UserRole, p["id"])
            self.name_matches.addItem(item)
        self.name_matches.setVisible(bool(matches))

    def new_job_for(self, patient_id: int) -> None:
        """A fresh job with the patient already filled in.

        Reception has just found this person on the Patients screen; making
        them type the name again is how a second record for the same person
        gets created.
        """
        self.new_job()
        self._fill_patient_fields(q.get_patient(patient_id))

    def _fill_patient_fields(self, p) -> None:
        """Put a patient's details into the intake fields."""
        if not p:
            return
        self.patient_id = int(p["id"])
        self.name_edit.setText(p["name"])
        self.initial_edit.setText(p["initial"] or "")
        self._refresh_printed_name()
        self.phone_edit.setText(p["phone"] or "")
        self.sex_combo.setCurrentText(p["sex"] or "")
        self.age_spin.setValue(int(p["age_value"] or 0))
        self.age_unit.setCurrentText((p["age_unit"] or "Years").title())
        self.name_matches.hide()

    def _pick_existing_patient(self, item: QListWidgetItem) -> None:
        person = q.get_patient(item.data(Qt.ItemDataRole.UserRole))
        if not person:
            return
        self._fill_patient_fields(person)
        self.history_button.setEnabled(True)
        if hasattr(self, 'remarks_edit'):
            self.remarks_edit.clear()
        self.repeat_row.setVisible(bool(self._previous_test_ids()))
        self.test_search.setFocus()
        self.message.setText(
            f"Loaded {person['name']} — details filled in from their last visit.")
        self.message.setStyleSheet(f"color: {style.GREEN}; font-weight: 600;")

    ADD_DOCTOR = -1        # the "add a new one" entry at the foot of the list
    KEEP = "keep"          # "leave whoever is chosen selected"

    def _reload_referrers(self, keep_id=KEEP) -> None:
        """Fill the doctor list.

        keep_id defaults to a sentinel rather than None because None is a real
        answer here -- "no doctor" -- and treating it as "keep the current one"
        meant starting a new job silently inherited the last patient's doctor,
        along with their commission.
        """
        if keep_id == self.KEEP:
            keep_id = self.referrer_combo.currentData()
        self.referrer_combo.blockSignals(True)
        self.referrer_combo.clear()
        self.referrer_combo.addItem("— none —", None)
        for r in q.list_referrers():
            self.referrer_combo.addItem(q.referrer_label(r), r["id"])
        self.referrer_combo.insertSeparator(self.referrer_combo.count())
        self.referrer_combo.addItem("Add a new doctor…", self.ADD_DOCTOR)
        self._select_referrer(keep_id)
        self.referrer_combo.blockSignals(False)

    def _select_referrer(self, referrer_id: Optional[int]) -> None:
        index = self.referrer_combo.findData(referrer_id) if referrer_id else 0
        self.referrer_combo.setCurrentIndex(index if index >= 0 else 0)

    def _referrer_chosen(self, _index: int) -> None:
        """Adding a doctor from here saves a trip to the Doctors tab."""
        if self.referrer_combo.currentData() != self.ADD_DOCTOR:
            return
        from .referrers_dialog import ReferrerEditor

        editor = ReferrerEditor(None, self)
        if editor.exec():
            self._reload_referrers(keep_id=getattr(editor, "saved_id", None))
        else:
            self._select_referrer(None)

    # --------------------------------------------------------------- tests
    def _reload_panels(self) -> None:
        while self.panel_layout.count():
            item = self.panel_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        for p in q.list_panels(quick_only=True):
            # Qt reads a single & as a keyboard shortcut marker and hides it, so
            # "Blood Sugar F & PP" would print as "Blood Sugar F _PP".
            b = button("+ " + p["name"].replace("&", "&&"), "panel")
            b.clicked.connect(lambda _c=False, pid=p["id"]: self._add_panel(pid))
            self.panel_layout.addWidget(b)

    def _previous_test_ids(self) -> List[int]:
        """The tests from this patient's most recent job."""
        if not self.patient_id:
            return []
        for job in q.patient_jobs(self.patient_id):
            if job["id"] == self.job_id:
                continue
            ids = [t["id"] for t in q.job_tests(job["id"])]
            if ids:
                return ids
        return []

    def _repeat_last_tests(self) -> None:
        """A follow-up visit is usually the same tests as last time."""
        ids = self._previous_test_ids()
        if not ids:
            info(self, "No earlier tests",
                 "This patient has no previous visit to copy from.")
            return
        added = 0
        for tid in ids:
            if tid not in self.test_ids:
                self.test_ids.append(tid)
                added += 1
        if not added:
            info(self, "Already added",
                 "Those tests are already on this job.")
            return
        self._persist_tests()
        self._rebuild_grid()
        self._focus_first_empty()
        self.message.setText(
            f"Added {added} test{'s' if added != 1 else ''} from the last visit.")
        self.message.setStyleSheet(f"color: {style.GREEN}; font-weight: 600;")

    def _add_panel(self, panel_id: int) -> None:
        added = 0
        for tid in q.panel_test_ids(panel_id):
            if tid not in self.test_ids:
                self.test_ids.append(tid)
                added += 1
        if added:
            self._persist_tests()
            self._rebuild_grid()
            self._focus_first_empty()

    def _search_tests(self, term: str) -> None:
        term = (term or "").strip()
        if len(term) < 2:
            self.test_matches.hide()
            return

        term_lower = term.lower()
        panels = [p for p in q.list_panels() if term_lower in p["name"].lower()]
        found = [t for t in q.search_tests(term, limit=12) if t["id"] not in self.test_ids]

        self.test_matches.clear()
        for p in panels:
            n_t = len(q.panel_test_ids(p["id"]))
            item = QListWidgetItem(f"★ Panel: {p['name']} ({n_t} test{'s' if n_t != 1 else ''})")
            item.setData(Qt.ItemDataRole.UserRole, ("panel", p["id"]))
            f = QFont()
            f.setBold(True)
            item.setFont(f)
            self.test_matches.addItem(item)

        for t in found:
            item = QListWidgetItem(f"{t['name']}    ·    {t['group_name']}")
            item.setData(Qt.ItemDataRole.UserRole, ("test", t["id"]))
            self.test_matches.addItem(item)

        self.test_matches.setVisible(bool(panels or found))

    def _add_first_match(self) -> None:
        if self.test_matches.isVisible() and self.test_matches.count():
            self._add_from_match(self.test_matches.item(0))

    def _add_from_match(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, tuple):
            kind, item_id = data
            if kind == "panel":
                self._add_panel(item_id)
            elif kind == "test":
                if item_id not in self.test_ids:
                    self.test_ids.append(item_id)
                    self._persist_tests()
                    self._rebuild_grid()
                    self._focus_first_empty()
        elif data and data not in self.test_ids:
            self.test_ids.append(data)
            self._persist_tests()
            self._rebuild_grid()
            self._focus_first_empty()
        self.test_search.clear()
        self.test_matches.hide()

    def _row_menu(self, job_test_id: int, anchor) -> None:
        """Per-test actions, including the not-done escape hatch."""
        from PyQt6.QtWidgets import QMenu

        rr = self.rows.get(job_test_id)
        if rr is None:
            return

        menu = QMenu(self)
        if rr.not_done:
            act_nd = menu.addAction("Undo — this test was done")
        else:
            act_nd = menu.addAction("Mark as not done (leave off the report)")
        act_prev = menu.addAction("Show this patient's previous results")
        menu.addSeparator()
        act_remove = menu.addAction("Remove this test from the job")

        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        if chosen is None:
            return
        if chosen is act_nd:
            self.set_not_done(job_test_id, not rr.not_done)
        elif chosen is act_prev:
            self._show_previous(rr)
        elif chosen is act_remove:
            self._remove_test(rr.test["id"])

    def set_not_done(self, job_test_id: int, flag: bool) -> None:
        rr = self.rows.get(job_test_id)
        if rr is None:
            return
        if flag and rr.value():
            if not confirm(self, "Mark as not done?",
                           f"'{rr.test['name']}' has a result typed in. Marking it "
                           f"not done leaves it off the report.\n\nContinue?",
                           "Mark not done"):
                return
            rr.set_value("")
        rr.set_not_done(flag)
        if self._ensure_job(silent=True):
            q.set_not_done(rr.job_test_id, flag)
            self._recalc()
        else:
            self._update_actions()

    def _show_previous(self, rr: "ResultRow") -> None:
        if not self.patient_id:
            info(self, "No history", "This patient has no earlier visits recorded.")
            return
        rows = q.previous_results(self.patient_id, rr.test["id"], self.job_id)
        if not rows:
            info(self, "No earlier results",
                 f"There is no previous {rr.test['name']} for this patient.")
            return
        lines = [f"   {turnaround.format_date(q.to_dt(x['received_at']))}"
                 f"     {x['display_value']}" for x in rows]
        info(self, f"Previous — {rr.test['name']}",
             "Most recent first:\n\n" + "\n".join(lines))

    def _remove_test(self, test_id: int) -> None:
        if test_id in self.test_ids:
            self.test_ids.remove(test_id)
            self._persist_tests()
            self._rebuild_grid()

    def _remove_group(self, group_name: str) -> None:
        """Remove all tests belonging to a clinical department/group with one click."""
        tests = (q.job_tests(self.job_id) if self.job_id else self._preview_tests())
        matching_ids = [t["id"] for t in tests if (t.get("group_name") or "").strip() == group_name]
        if not matching_ids:
            return
        if not confirm(self, f"Remove {group_name}?",
                       f"All {len(matching_ids)} tests under {group_name} will be removed from this job.", "Remove"):
            return
        self.test_ids = [tid for tid in self.test_ids if tid not in matching_ids]
        self._persist_tests()
        self._rebuild_grid()

    def _persist_tests(self) -> None:
        """Save the test list if the job already exists on disk."""
        if self.job_id:
            q.set_job_tests(self.job_id, self.test_ids)
            self._refresh_header()

    # ------------------------------------------------------------- results
    def _rebuild_grid(self) -> None:
        # Anything already typed is kept and put back afterwards. The grid is
        # rebuilt the moment the job is first saved, and without this the value
        # that triggered the save would be wiped by its own side effect.
        carried = {rr.test["id"]: rr.value() for rr in self.rows.values()}

        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                # setParent(None) first: deleteLater only runs when the event
                # loop next spins, so without this the old labels stay on screen
                # and draw on top of the new ones.
                w.setParent(None)
                w.deleteLater()
        self.rows = {}

        if not self.test_ids:
            self.scroll.hide()
            self.progress.hide()
            self.empty_hint.show()
            self._update_actions()
            return

        self.empty_hint.hide()
        self.scroll.show()

        tests = (q.job_tests(self.job_id) if self.job_id
                 else self._preview_tests())

        r = 0
        last_group = None
        for t in tests:
            group = (t["group_name"] or "").strip()
            if group and group != last_group:
                # A filled strip, not coloured text: it separates two sections
                # without spending the accent, which belongs to actions.
                strip = QFrame()
                strip.setObjectName("groupRow")
                strip.setFixedHeight(28)
                sl = QHBoxLayout(strip)
                sl.setContentsMargins(18, 0, 18, 0)
                sl.addWidget(label(group, "group"))
                sl.addStretch(1)
                rem_btn = button("✕ Remove group", "quiet", lambda _c=False, g=group: self._remove_group(g))
                rem_btn.setStyleSheet(f"font-size: 8pt; color: {style.ACCENT_INK};")
                sl.addWidget(rem_btn)
                self.grid.addWidget(strip, r, 0, 1, 6)
                last_group = group
                r += 1

            rr = ResultRow(t, on_changed=self._recalc, on_focus=None)
            self.rows[t["job_test_id"]] = rr
            if t["id"] in carried and carried[t["id"]]:
                rr.set_value(carried[t["id"]])

            # Delta Check historical lookup
            if self.patient_id and t.get("id"):
                prevs = q.previous_results(self.patient_id, t["id"], before_job=self.job_id, limit=1)
                if prevs and prevs[0].get("display_value"):
                    pv = prevs[0]
                    date_str = str(pv.get("received_at", ""))[:10] if pv.get("received_at") else ""
                    rr.delta_label.setText(f"Δ Prev: {pv['display_value']} ({date_str})")
                    rr.delta_label.setVisible(True)

            # Name over method, so the row reads downwards in one column and
            # the value keeps the eye's line across.
            name_cell = QWidget()
            name_lay = QVBoxLayout(name_cell)
            name_lay.setContentsMargins(18, 0, 0, 0)
            name_lay.setSpacing(1)
            name_lay.addWidget(rr.name_label)
            name_lay.addWidget(rr.method_label)
            name_lay.addWidget(rr.delta_label)

            if rr.is_heading:
                self.grid.addWidget(name_cell, r, 0, 1, 5)
            else:
                self.grid.addWidget(name_cell, r, 0)
                self.grid.addWidget(rr.editor, r, 1)
                self.grid.addWidget(rr.unit_label, r, 2)
                self.grid.addWidget(rr.range_label, r, 3)
                self.grid.addWidget(rr.flag_label, r, 4)
                self.grid.setRowMinimumHeight(r, ROW_H)

            menu_button = button("⋯", "quiet")
            menu_button.setFixedWidth(MENU_W)
            menu_button.setToolTip("More for this test")
            menu_button.clicked.connect(
                lambda _c=False, jt=t["job_test_id"], b=menu_button: self._row_menu(jt, b))
            self.grid.addWidget(menu_button, r, 5)

            if t.get("not_done"):
                rr.set_not_done(True)
            r += 1

        # The name column takes the slack; every other column is the width its
        # header says it is, so the two line up down the screen.
        self.grid.setColumnStretch(0, 1)
        for column_index, width in ((1, RESULT_W), (2, UNIT_W),
                                    (3, RANGE_W), (4, FLAG_W), (5, MENU_W)):
            self.grid.setColumnMinimumWidth(column_index, width)
            self.grid.setColumnStretch(column_index, 0)
        self.grid.setRowStretch(r, 1)
        self._update_actions()
        self._refresh_bill()

    def _preview_tests(self) -> List[dict]:
        """Tests chosen before the job exists on disk; keyed by a temporary id."""
        out = []
        for i, tid in enumerate(self.test_ids):
            t = q.get_test(tid)
            if t:
                t = dict(t)
                t["job_test_id"] = -(i + 1)
                t["not_done"] = 0
                out.append(t)
        return out

    def _load_stored_results(self) -> None:
        if not self.job_id:
            return
        stored = q.results_for_job(self.job_id)
        for jt_id, rr in self.rows.items():
            data = stored.get(jt_id)
            if not data:
                continue
            rr.set_value(data["raw_value"] or "")
            rr.range_label.setText(data["range_text"] or "")
            rr.flag_label.set_flag(data["flag"] or "")
        self._update_actions()

    def _focus_first_empty(self) -> None:
        for rr in self.rows.values():
            if not rr.is_derived and not getattr(rr, "is_heading", False) and not rr.value():
                rr.editor.setFocus()
                return

    # ---------------------------------------------------------- calculation
    def _recalc(self) -> None:
        """Save what has been typed and refresh every calculated value."""
        if self._loading or not self.test_ids:
            return
        if not self._ensure_job(silent=True):
            return

        typed = {jt: rr.value() for jt, rr in self.rows.items()
                 if not rr.is_derived and not rr.not_done}
        try:
            out = services.recalculate(self.job_id, typed)
        except Exception as exc:                      # pragma: no cover - defensive
            self.message.setText(f"Could not calculate: {exc}")
            self.message.setProperty("role", "error")
            # An inline rule beats the sheet, and save() leaves one behind in
            # the success green — so a failure was reported in the colour that
            # means "saved".
            self.message.setStyleSheet(f"color: {style.RED}; font-weight: 600;")
            return

        for jt, rr in self.rows.items():
            data = out.get(jt)
            if not data:
                continue
            if rr.is_derived:
                rr.set_value(data["display"])
                if data.get("error"):
                    rr.editor.setToolTip(data["error"])
            rr.range_label.setText(data["range_text"])
            rr.flag_label.set_flag(data["flag"])

        # Scan for Panic / Critical laboratory values
        panic_items = []
        for jt, rr in self.rows.items():
            val = rr.value()
            t = rr.test
            if val:
                try:
                    num = float(val)
                    code = (t.get("code") or "").upper()
                    if code in ("GLU_F", "GLU_R", "GLU_PP") and (num < 50 or num > 400):
                        panic_items.append(f"{t['name']}: {num} mg/dl")
                    elif code == "K" and (num < 2.8 or num > 6.2):
                        panic_items.append(f"Potassium: {num} mmol/L")
                    elif code == "HB" and num < 6.0:
                        panic_items.append(f"Haemoglobin: {num} g/dl")
                    elif code == "PLT" and num < 0.25:
                        panic_items.append(f"Platelets: {num} lakhs")
                    elif code in ("TROPI", "TROPT") and num > 0.04:
                        panic_items.append(f"{t['name']}: {num} (Critical)")
                except ValueError:
                    pass

        if panic_items:
            self.panic_text.setText("CRITICAL PANIC VALUE DETECTED — NOTIFY CLINICIAN:  " + " · ".join(panic_items))
            self.panic_banner.show()
        else:
            self.panic_banner.hide()

        self._refresh_header()
        self._update_actions()
        self._refresh_bill()
        self.job_changed.emit()

    def _update_actions(self) -> None:
        total = len(self.rows)
        done = sum(1 for rr in self.rows.values() if rr.value() or rr.not_done)
        ready = bool(self.test_ids) and done == total and total > 0

        # Only show a slim bar during entry; hide once all results are entered
        if total and not ready and done > 0:
            self.progress.show()
            self.progress.setRange(0, total)
            self.progress.setValue(done)
        else:
            self.progress.hide()

        self.verify_button.setEnabled(ready)
        if total and not ready:
            missing = total - done
            self.verify_button.setToolTip(
                f"{missing} test{'s' if missing != 1 else ''} still empty. "
                "Fill them in, or mark them not done.")
        else:
            self.verify_button.setToolTip("Produce the report PDF")

        self.tests_count.setText(
            f"{len(self.test_ids)} chosen · {total} result{'s' if total != 1 else ''}"
            if self.test_ids else "")
        self._refresh_counsel()

        if total:
            self.progress_label.setText(f"{done} of {total} entered")
            self.progress_label.setStyleSheet(
                f"color: {style.GREEN}; font-weight: 600;" if ready
                else f"color: {style.INK3};")
        else:
            self.progress_label.setText("")

    def _refresh_header(self) -> None:
        if not self.job_id:
            return
        job = q.get_job(self.job_id)
        if not job:
            return
        # The name as it will print, so the heading and the report agree.
        # No "Job —" prefix: the rail already has a PATIENT caption above it.
        self.title.setText(job["name_at_test"] or job["patient_name"] or "—")
        rev = int(job["revision_no"] or 1)
        suffix = "" if rev <= 1 else f"  (revision {rev})"
        self.report_no_label.setText(f"{job['report_no']}{suffix}")
        due = q.to_dt(job["due_at"])
        if due:
            late = turnaround.is_overdue(due, job["status"])
            # No "Due" prefix -- the caption above the value already says it.
            text = f"{turnaround.format_dt(due)} · {turnaround.humanise_delta(due)}"
            self.due_label.setText(text)
            self.due_label.setStyleSheet(
                f"color: {style.RED}; font-weight: 600;" if late else "")
        st = (job.get("status") or "draft").lower()
        st_type = "draft"
        if "prog" in st:
            st_type = "prog"
        elif "ready" in st:
            st_type = "ready"
        elif "sent" in st:
            st_type = "sent"
        fg, bg, edge = style.status_fill(st_type)
        self.status_label.setText(turnaround.status_label(job["status"]))
        self.status_label.setStyleSheet(
            f"color: {fg}; background: {bg}; border: 1px solid {edge}; "
            f"padding: 2px 9px; font-size: 8pt; font-weight: 800;")

    # ------------------------------------------------------------- actions
    def patient_problem(self) -> Optional[Tuple[str, QWidget]]:
        """What is missing before this patient can be recorded, if anything.

        Name, mobile and sex are all required. The mobile is how the report is
        sent and how the same person is recognised on their next visit; the sex
        decides which normal range a result is judged against, so a job saved
        without it would be flagged against the wrong one.

        Separate from save() so the rule can be tested without a dialog box
        standing in the way.
        """
        if not self.name_edit.text().strip():
            return ("the patient's name", self.name_edit)
        if not self.phone_edit.text().strip():
            return ("a mobile number", self.phone_edit)
        if not self.sex_combo.currentText().strip():
            return ("the patient's sex", self.sex_combo)
        return None

    def _collect_patient(self) -> Optional[dict]:
        problem = self.patient_problem()
        if problem:
            missing, widget = problem
            warn(self, "Not saved yet",
                 f"This job needs {missing}.\n\n"
                 f"Name, mobile number and sex are all required: the number is "
                 f"how the report reaches the patient and how they are found "
                 f"next time, and the sex decides which normal range each "
                 f"result is judged against.")
            widget.setFocus()
            return None
        return {
            "name": self.name_edit.text().strip(),
            "initial": self.initial_edit.text().strip().strip(".").upper(),
            "phone": self.phone_edit.text().strip(),
            "sex": self.sex_combo.currentText().strip(),
            "age_value": self.age_spin.value() or None,
            "age_unit": self.age_unit.currentText().lower(),
        }

    def _ensure_job(self, silent: bool = False) -> bool:
        """Create the job on first use so results have somewhere to be saved."""
        if self.job_id:
            return True
        data = self._collect_patient() if not silent else None
        if not silent:
            if data is None:
                return False
        else:
            # The quiet path -- results being saved as they are typed -- asks
            # only for a name. Holding it to the full rule would mean a screen
            # full of typed results kept nowhere while reception fetches the
            # patient's number, and losing those is worse than a draft with a
            # missing field. Nothing can be *finished* until save() is happy.
            if not self.name_edit.text().strip() or not self.test_ids:
                return False
            data = {
                "name": self.name_edit.text().strip(),
                "initial": self.initial_edit.text().strip().strip(".").upper(),
                "phone": self.phone_edit.text().strip(),
                "sex": self.sex_combo.currentText().strip(),
                "age_value": self.age_spin.value() or None,
                "age_unit": self.age_unit.currentText().lower(),
            }

        self.patient_id = services.upsert_patient(
            data["name"], data["phone"], data["sex"], data["age_value"],
            data["age_unit"], patient_id=self.patient_id,
            initial=data.get("initial"))

        referrer_id = self._resolve_referrer()
        self.job_id = q.create_job(self.patient_id, self.test_ids, referrer_id)
        self.history_button.setEnabled(True)
        if hasattr(self, 'remarks_edit') and self.remarks_edit.toPlainText().strip():
            q.update_job(self.job_id, remarks=self.remarks_edit.toPlainText().strip())

        # Re-key the existing rows onto the real job_test ids. Rebuilding the
        # grid here would destroy the very box being typed into: it swallowed
        # the keystroke, moved focus out of the results area, and truncated
        # dropdown values to their first letter.
        self._rekey_rows()
        self._refresh_header()
        return True

    def _rekey_rows(self) -> None:
        """Point the on-screen rows at the database rows now backing them."""
        if not self.job_id:
            return
        by_test = {t["id"]: t["job_test_id"] for t in q.job_tests(self.job_id)}
        rekeyed: Dict[int, ResultRow] = {}
        for rr in self.rows.values():
            new_id = by_test.get(rr.test["id"])
            if new_id is None:
                continue
            rr.job_test_id = new_id
            rr.test = dict(rr.test)
            rr.test["job_test_id"] = new_id
            rekeyed[new_id] = rr
        if rekeyed:
            self.rows = rekeyed

    def _resolve_referrer(self) -> Optional[int]:
        """The chosen doctor's id, or None when the job has no referrer."""
        chosen = self.referrer_combo.currentData()
        if chosen in (None, self.ADD_DOCTOR):
            return None
        return int(chosen)

    def _referrer_name(self) -> str:
        """The doctor's plain name, without the hospital shown in the picker."""
        referrer_id = self._resolve_referrer()
        if not referrer_id:
            return ""
        r = next((x for x in q.list_referrers() if x["id"] == referrer_id), None)
        return (r["name"] if r else "").strip()

    def save(self) -> None:
        if not self.test_ids:
            warn(self, "No tests chosen",
                 "Nothing was saved, because this job has no tests yet.\n\n"
                 "Click a panel button, or type a test name in the search box.")
            return
        if not self._ensure_job():
            return

        data = self._collect_patient()
        if data is None:
            return
        services.upsert_patient(data["name"], data["phone"], data["sex"],
                                data["age_value"], data["age_unit"],
                                patient_id=self.patient_id,
                                initial=data.get("initial"))
        q.set_job_tests(self.job_id, self.test_ids)
        q.update_job(self.job_id, referrer_id=self._resolve_referrer(),
                     referrer_name=self._referrer_name(),
                     # Stored as printed, so a name corrected later never
                     # changes what a report already sent out said.
                     name_at_test=q.full_name(data["name"], data.get("initial")),
                     sex_at_test=data["sex"] or "",
                     # The age as well. The reference range that decides
                     # whether a result reads normal or HIGH is chosen by it,
                     # so an age correction that stops at the patient record
                     # is a correction that never reaches the report.
                     age_at_test=q.age_text(data),
                     age_value_at_test=data.get("age_value"),
                     age_unit_at_test=(data.get("age_unit") or "").lower())
        self._recalc()
        self.message.setText("Saved")
        self.message.setProperty("role", "ok")
        self.message.setStyleSheet(f"color: {style.GREEN}; font-weight: 600;")
        self.job_changed.emit()

    def verify(self) -> None:
        if not self._ensure_job():
            return
        self.save()

        # Bill first is the lab's rule, so an unbilled report is worth stopping
        # for -- but only to ask. Blocking it would mean a patient in a hurry
        # cannot have their result, which is the wrong trade.
        from ..core import auth

        if auth.can(auth.P_BILL) and not q.get_bill(self.job_id):
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle("No bill has been made")
            box.setText(
                f"This job has no bill.\n\nThe report can still be made, but "
                f"nothing has been recorded as charged for {self.name_edit.text().strip()}.")
            make = box.addButton("Make the bill first", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Continue without a bill", QMessageBox.ButtonRole.DestructiveRole)
            box.exec()
            if box.clickedButton() is make:
                self._open_bill()
                if not q.get_bill(self.job_id):
                    return
            else:
                q.log_action("report_without_bill", "job", self.job_id)
        ok, missing, path = services.verify_job(self.job_id)
        if not ok:
            listed = "\n".join(f"   •  {m}" for m in missing[:12])
            more = f"\n   … and {len(missing) - 12} more" if len(missing) > 12 else ""
            warn(self, "Some tests are still empty",
                 "The report was not made, because these tests have no "
                 "result yet:\n\n" + listed + more +
                 "\n\nType the missing values.\n"
                 "If a test could not be run, click \u22ef beside it and choose "
                 "\u201cMark as not done\u201d.")
            self._focus_first_empty()
            return
        self._refresh_header()
        self.job_changed.emit()
        self.request_send.emit(self.job_id)

    def preview(self) -> None:
        """Show the report as it stands, without sending anything."""
        if not self.test_ids:
            warn(self, "Nothing to preview",
                 "This job has no tests yet, so there is no report to show.\n\n"
                 "Click a panel button, or type a test name.")
            return
        if not self._ensure_job():
            return
        self._recalc()
        self.request_preview.emit(self.job_id)

    def _open_bill(self) -> None:
        if not self._ensure_job():
            return
        from .bill_dialog import BillDialog

        dlg = BillDialog(self.job_id, self)
        dlg.exec()
        self._refresh_bill()
        self.job_changed.emit()

    def _print_bill(self) -> None:
        """Show the receipt for this job.

        Works whether or not a bill has been saved: with none saved it prints
        a proforma from the chosen tests, which is what the counter is asked
        for when a patient wants to know the cost first.
        """
        if not self._ensure_job():
            return
        from .bill_preview import BillPreviewDialog

        BillPreviewDialog(self.job_id, self).exec()
        self._refresh_bill()

    def _open_history(self) -> None:
        if not self.patient_id:
            return
        from .history_dialog import HistoryDialog

        HistoryDialog(self.patient_id, self).exec()

    def _open_tube_label(self) -> None:
        if not self.job_id or not self.test_ids:
            return
        job = q.get_job(self.job_id) or {}
        tests = q.job_tests(self.job_id)
        test_names = [t["name"] for t in tests]
        data = {
            "report_no": job.get("report_no", self.job_id),
            "patient_name": self.printed_name_text() or self.name_edit.text(),
            "age": f"{self.age_spin.value()} {self.age_unit.currentText()}",
            "sex": self.sex_combo.currentText(),
            "received_at": job.get("received_at", ""),
        }
        from .tube_label_dialog import TubeLabelDialog

        TubeLabelDialog(self, data, test_names).exec()

    def _open_whatsapp_dispatch(self) -> None:
        if not self.job_id:
            return
        job = q.get_job(self.job_id) or {}
        tests = q.job_tests(self.job_id)
        stored = q.results_for_job(self.job_id)
        lines = []
        for t in tests:
            jt = t["job_test_id"]
            r = stored.get(jt, {})
            val = r.get("display_value") or r.get("raw_value") or "—"
            unit = t.get("unit") or ""
            flag = f" [{r.get('flag')}]" if r.get("flag") else ""
            lines.append(f"• *{t['name']}:* {val} {unit}{flag}")
        
        data = {
            "report_no": job.get("report_no", self.job_id),
            "patient_name": self.printed_name_text() or self.name_edit.text(),
            "phone": self.phone_edit.text(),
            "received_at": job.get("received_at", ""),
        }
        WhatsAppDialog(self, data, "\n".join(lines)).exec()

    def _remarks_changed(self) -> None:
        if getattr(self, "_loading", False):
            return
        if self.job_id:
            q.update_job(self.job_id, remarks=self.remarks_edit.toPlainText().strip())

    def _open_pos_receipt(self) -> None:
        if not self.job_id:
            return
        POSReceiptDialog(self, self.job_id).exec()
