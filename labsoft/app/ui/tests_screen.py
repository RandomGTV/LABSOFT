"""The Tests master — where the lab controls what the program can do."""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout,
    QHBoxLayout, QHeaderView, QLineEdit, QPlainTextEdit, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..core import billing, formula, ranges as rng
from ..db import queries as q
from ..output import excel
from . import style
from .widgets import (
    SearchBox, Table, button, confirm, error, field_label, info, label, row, warn,
)


#: Offered in the specimen box. It stays editable — a lab that uses a
#: container this list has never heard of must not be stuck with the list.
SPECIMENS = [
    "Serum", "Plasma", "Whole Blood (EDTA)", "Plasma (Citrate)",
    "Fluoride Plasma", "Urine", "Random Urine", "24-hour Urine", "Stool",
    "Semen", "Sputum", "Swab", "Body Fluid", "CSF",
]


class TestEditor(QDialog):
    """Edit one test and its reference ranges."""

    def __init__(self, test_id: Optional[int], parent=None):
        super().__init__(parent)
        self.test_id = test_id
        self.setWindowTitle("Edit test" if test_id else "New test")
        self.resize(660, 620)
        self._build()
        self._load()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Short code used in formulas, e.g. GLU_F")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Prints exactly as typed")
        self.group_combo = QComboBox()
        self.group_combo.setEditable(True)
        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("mg/dl — joined onto the value")
        self.decimals_spin = QSpinBox()
        self.decimals_spin.setRange(0, 4)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["numeric", "text", "option"])
        self.options_edit = QLineEdit()
        self.options_edit.setPlaceholderText("Positive|Negative")
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0, 999999)
        self.rate_spin.setPrefix("₹ ")
        self.tat_spin = QDoubleSpinBox()
        self.tat_spin.setRange(0.5, 720)
        self.tat_spin.setSuffix(" hours")
        self.specimen_combo = QComboBox()
        self.specimen_combo.setEditable(True)
        self.specimen_combo.addItems(SPECIMENS)
        self.specimen_combo.lineEdit().setPlaceholderText(
            "Serum — printed under the heading on the report")

        form.addRow("Code", self.code_edit)
        form.addRow("Name", self.name_edit)
        form.addRow("Group heading", self.group_combo)
        form.addRow("Specimen", self.specimen_combo)
        form.addRow("Unit", self.unit_edit)
        form.addRow("Decimal places", self.decimals_spin)
        form.addRow("Result type", self.type_combo)
        form.addRow("Options", self.options_edit)
        form.addRow("Rate", self.rate_spin)
        form.addRow("Turnaround", self.tat_spin)
        lay.addLayout(form)

        self.separate_check = QCheckBox(
            "Also issue this test on its own detailed PDF")
        lay.addWidget(self.separate_check)
        lay.addWidget(label(
            "For tests the lab hands over with an explanation — HbA1c, TSH, "
            "Vitamin D. The result still appears on the main report as usual.",
            "hint"))

        lay.addWidget(field_label("Interpretation (printed on the detailed PDF)"))
        self.interp_edit = QPlainTextEdit()
        self.interp_edit.setFixedHeight(96)
        self.interp_edit.setPlaceholderText(
            "Normal   below 5.7 %\nPre-diabetes   5.7 – 6.4 %\nDiabetes   6.5 % and above")
        lay.addWidget(self.interp_edit)

        lay.addWidget(field_label("Formula (leave empty for a measured test)"))
        self.formula_edit = QLineEdit()
        self.formula_edit.setPlaceholderText("e.g.  TP - ALB     or    CHOL - HDL - TG/5")
        self.formula_edit.textChanged.connect(self._check_formula)
        lay.addWidget(self.formula_edit)
        self.formula_note = label("", "hint")
        self.formula_note.setWordWrap(True)
        lay.addWidget(self.formula_note)
        lay.addWidget(button("Show available codes", "quiet", self._show_codes))

        lay.addWidget(field_label("Normal values"))
        self.ranges_table = QTableWidget(0, 7)
        self.ranges_table.setHorizontalHeaderLabels(
            ["Rule", "Low", "High", "Text", "Sex", "Age from", "Prints as"])
        self.ranges_table.verticalHeader().setVisible(False)
        self.ranges_table.horizontalHeader().setSectionResizeMode(
            6, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.ranges_table, 1)
        lay.addWidget(row(button("Add row", "", self._add_range),
                          button("Remove row", "quiet", self._remove_range), None))

        lay.addWidget(row(None, button("Cancel", "", self.reject),
                          button("Save", "primary", self._save)))

    # ------------------------------------------------------------------ data
    def _load(self) -> None:
        self.group_combo.addItems(q.test_groups())
        if not self.test_id:
            self.decimals_spin.setValue(1)
            self.tat_spin.setValue(24)
            self.specimen_combo.setCurrentText("Serum")
            self._add_range()
            return

        t = q.get_test(self.test_id)
        self.code_edit.setText(t["code"])
        self.name_edit.setText(t["name"])
        self.group_combo.setCurrentText(t["group_name"])
        self.unit_edit.setText(t["unit"] or "")
        self.decimals_spin.setValue(int(t["decimals"] or 0))
        self.type_combo.setCurrentText(t["result_type"] or "numeric")
        self.options_edit.setText(t["options"] or "")
        self.rate_spin.setValue(billing.to_rupees(t["rate_paise"]))
        self.tat_spin.setValue(float(t["tat_hours"] or 24))
        self.formula_edit.setText(t["formula"] or "")
        self.specimen_combo.setCurrentText(t["specimen"] or "")
        self.separate_check.setChecked(bool(t["separate_report"]))
        self.interp_edit.setPlainText(t["interpretation"] or "")

        for r in q.ranges_for_test(self.test_id):
            self._add_range(r)

    def _add_range(self, data: Optional[dict] = None) -> None:
        r = self.ranges_table.rowCount()
        self.ranges_table.insertRow(r)

        rule = QComboBox()
        rule.addItems([rng.RULE_RANGE, rng.RULE_MAX, rng.RULE_MIN, rng.RULE_TEXT])
        sex = QComboBox()
        sex.addItems(["any", "M", "F"])
        if data:
            rule.setCurrentText(data.get("rule_type") or rng.RULE_RANGE)
            sex.setCurrentText(data.get("sex") or "any")
        self.ranges_table.setCellWidget(r, 0, rule)
        self.ranges_table.setCellWidget(r, 4, sex)

        def put(col: int, value) -> None:
            self.ranges_table.setItem(
                r, col, QTableWidgetItem("" if value is None else str(value)))

        put(1, (data or {}).get("low"))
        put(2, (data or {}).get("high"))
        put(3, (data or {}).get("text_value"))
        put(5, (data or {}).get("age_min"))
        put(6, (data or {}).get("display_text"))

    def _remove_range(self) -> None:
        r = self.ranges_table.currentRow()
        if r >= 0:
            self.ranges_table.removeRow(r)

    # -------------------------------------------------------------- formulas
    def _check_formula(self) -> None:
        text = self.formula_edit.text().strip()
        if not text:
            self.formula_note.setText("")
            self.formula_note.setStyleSheet("")
            return
        try:
            used = formula.codes_used(text)
        except formula.FormulaError as exc:
            self.formula_note.setText(str(exc))
            self.formula_note.setStyleSheet(f"color: {style.RED}; font-weight: 600;")
            return

        known = {t["code"].upper() for t in q.list_tests(include_inactive=True)}
        unknown = used - known
        if unknown:
            self.formula_note.setText(
                "These codes do not exist yet: " + ", ".join(sorted(unknown)))
            self.formula_note.setStyleSheet(f"color: {style.AMBER}; font-weight: 600;")
            return

        example = {c: 10.0 for c in used}
        try:
            value = formula.evaluate(text, example)
        except formula.FormulaError as exc:
            self.formula_note.setText(str(exc))
            self.formula_note.setStyleSheet(f"color: {style.RED}; font-weight: 600;")
            return
        shown = ", ".join(f"{c}=10" for c in sorted(used)) or "no inputs"
        self.formula_note.setText(
            f"Reads as {formula.describe(text)}.   With {shown} the answer is {value:g}.")
        self.formula_note.setStyleSheet(f"color: {style.GREEN};")

    def _show_codes(self) -> None:
        lines = [f"{t['code']:<12} {t['name']}" for t in q.list_tests()]
        dlg = QDialog(self)
        dlg.setWindowTitle("Test codes")
        dlg.resize(420, 520)
        lay = QVBoxLayout(dlg)
        table = Table(["Code", "Name"], stretch_column=1)
        table.set_rows([[t["code"], t["name"]] for t in q.list_tests()])
        lay.addWidget(table)
        lay.addWidget(button("Close", "primary", dlg.accept))
        dlg.exec()

    # ------------------------------------------------------------------ save
    def _save(self) -> None:
        code = self.code_edit.text().strip().upper()
        name = self.name_edit.text().strip()
        if not code or not name:
            warn(self, "Missing details", "A test needs both a code and a name.")
            return

        clash = q.get_test_by_code(code)
        if clash and clash["id"] != self.test_id:
            warn(self, "Code already used",
                 f"The code {code} belongs to '{clash['name']}'. Codes must be "
                 f"unique because formulas refer to them.")
            return

        # Editing a test must not quietly reorder it or un-hide it: those are
        # separate decisions, made elsewhere.
        existing = q.get_test(self.test_id) if self.test_id else None

        payload = {
            "id": self.test_id,
            "code": code,
            "name": name,
            "group_name": self.group_combo.currentText().strip(),
            "unit": self.unit_edit.text().strip(),
            "decimals": self.decimals_spin.value(),
            "result_type": self.type_combo.currentText(),
            "options": self.options_edit.text().strip(),
            "formula": self.formula_edit.text().strip(),
            "rate_paise": billing.to_paise(self.rate_spin.value()),
            "tat_hours": self.tat_spin.value(),
            "sort_order": int(existing["sort_order"] or 0) if existing else 0,
            "active": int(existing["active"] or 0) if existing else 1,
            "specimen": self.specimen_combo.currentText().strip(),
            "separate_report": 1 if self.separate_check.isChecked() else 0,
            "interpretation": self.interp_edit.toPlainText().strip(),
        }
        try:
            tid = q.save_test(payload)
        except formula.FormulaError as exc:
            warn(self, "The formula cannot be saved", str(exc))
            return

        rows = []
        for r in range(self.ranges_table.rowCount()):
            def cell(c: int) -> str:
                item = self.ranges_table.item(r, c)
                return item.text().strip() if item else ""

            def num(c: int):
                try:
                    return float(cell(c))
                except ValueError:
                    return None

            rule_widget = self.ranges_table.cellWidget(r, 0)
            sex_widget = self.ranges_table.cellWidget(r, 4)
            rows.append({
                "rule_type": rule_widget.currentText() if rule_widget else rng.RULE_RANGE,
                "low": num(1), "high": num(2), "text_value": cell(3),
                "sex": sex_widget.currentText() if sex_widget else "any",
                "age_min": num(5), "age_max": None,
                "display_text": cell(6),
            })
        q.replace_ranges(tid, rows)
        self.accept()


class TestsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tests: List[dict] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 10)
        lay.setSpacing(10)

        self.search = SearchBox("Search tests…")
        self.search.searched.connect(lambda _t: self.refresh())
        lay.addWidget(row(self.search,
                          button("New test", "primary", self._new),
                          button("Edit", "", self._edit),
                          button("Hide", "danger", self._deactivate)))

        self.table = Table(["Code", "Name", "Group", "Specimen", "Unit",
                            "Normal Value", "Formula", "Rate", "TAT"],
                           stretch_column=1)
        self.table.setColumnWidth(0, 90)   # Code
        self.table.setColumnWidth(2, 140)  # Group
        self.table.setColumnWidth(3, 130)  # Specimen
        self.table.setColumnWidth(4, 70)   # Unit
        self.table.setColumnWidth(5, 140)  # Normal Value
        self.table.setColumnWidth(6, 110)  # Formula
        self.table.setColumnWidth(7, 80)   # Rate
        self.table.setColumnWidth(8, 60)   # TAT
        self.table.doubleClicked.connect(self._edit)
        lay.addWidget(self.table, 1)

        self.count_label = label("", "hint")
        lay.addWidget(row(button("Import from Excel/CSV", "", self._import),
                          button("Export list", "", self._export),
                          button("Panels", "", self._panels),
                          button("Referring doctors", "", self._referrers),
                          None, self.count_label))

    def refresh(self) -> None:
        term = self.search.text().strip()
        self.tests = q.search_tests(term, limit=2000) if term else q.list_tests()
        all_ranges = q.all_test_ranges()
        display = []
        for t in self.tests:
            ranges = all_ranges.get(t["id"], [])
            normal = ranges[0]["display_text"] if ranges else ""
            if len(ranges) > 1:
                normal += f"  (+{len(ranges) - 1} more)"
            name = t["name"] + ("   · detailed PDF" if t["separate_report"] else "")
            display.append([t["code"], name, t["group_name"],
                            t["specimen"] or "", t["unit"], normal,
                            t["formula"] or "",
                            billing.format_rupees(t["rate_paise"], symbol=False),
                            f"{t['tat_hours']:g}h"])
        self.table.set_rows(display)
        self.count_label.setText(f"{len(self.tests)} tests")

    def _selected(self) -> Optional[dict]:
        i = self.table.selected_row()
        return self.tests[i] if 0 <= i < len(self.tests) else None

    def _new(self) -> None:
        if TestEditor(None, self).exec():
            self.refresh()

    def _edit(self) -> None:
        t = self._selected()
        if t and TestEditor(t["id"], self).exec():
            self.refresh()

    def _deactivate(self) -> None:
        t = self._selected()
        if not t:
            return
        if not confirm(self, "Hide this test?",
                       f"“{t['name']}” will stop appearing when you choose "
                       f"tests for a patient.\n\nReports that already used it stay "
                       f"exactly as they are, and you can bring it back later.",
                       "Hide it"):
            return
        q.delete_test(t["id"])
        self.refresh()

    def _export(self) -> None:
        from .. import config

        path, _ = QFileDialog.getSaveFileName(
            self, "Export test list", str(config.exports_dir() / "tests.xlsx"),
            "Excel (*.xlsx);;CSV (*.csv)")
        if not path:
            return
        written = excel.export_tests(path)
        info(self, "Exported", f"The test list has been written to:\n{written}")

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose the file to import", "",
            "Spreadsheets (*.xlsx *.xlsm *.csv);;All files (*.*)")
        if not path:
            return
        try:
            preview = excel.preview_tests_import(path)
        except Exception as exc:
            error(self, "Could not read that file", str(exc))
            return

        if not preview.get("ok"):
            warn(self, "Nothing to import",
                 preview.get("reason", "") +
                 "\n\nColumns found: " + ", ".join(preview.get("headers", [])))
            return

        n_new, n_upd, n_skip = (len(preview["new"]), len(preview["update"]),
                                len(preview["skipped"]))
        detail = ""
        if preview["update"]:
            named = [f"   {r['name']}  replaces  {r.get('replaces', r['code'])}"
                     for r in preview["update"][:6]]
            detail += "\n\nWill be overwritten:\n" + "\n".join(named)
            if n_upd > 6:
                detail += f"\n   … and {n_upd - 6} more"
        if preview["skipped"]:
            lines = [f"   line {ln}: {why}" for ln, why in preview["skipped"][:8]]
            detail = "\n\nSkipped:\n" + "\n".join(lines)
            if n_skip > 8:
                detail += f"\n   … and {n_skip - 8} more"

        if not confirm(self, "Import these tests?",
                       f"{n_new} new tests will be added.\n"
                       f"{n_upd} existing tests will be updated.\n"
                       f"{n_skip} rows will be skipped.{detail}\n\nContinue?",
                       "Import"):
            return

        result = excel.apply_tests_import(preview)
        self.refresh()
        msg = f"{result['added']} added, {result['updated']} updated."
        if result["failed"]:
            msg += "\n\nThese could not be imported:\n" + "\n".join(
                f"   {line}: {why}" for line, why in result["failed"][:10])
        info(self, "Import finished", msg)

    def _panels(self) -> None:
        from .panels_dialog import PanelsDialog

        PanelsDialog(self).exec()

    def _referrers(self) -> None:
        from .referrers_dialog import ReferrersDialog

        ReferrersDialog(self).exec()
