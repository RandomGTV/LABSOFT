"""Pathology Smart-Phrases & Peripheral Smear Comment Library Dialog."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QGroupBox, QListWidget, QListWidgetItem,
    QTextEdit, QVBoxLayout, QHBoxLayout, QWidget
)

from . import style
from .widgets import button, label, row

PHRASES = {
    "Peripheral Blood Smear (PBS)": [
        ("Normocytic Normochromic", "RBCs are predominantly normocytic and normochromic. WBC count and distribution within normal limits. Platelets appear adequate on smear. No hemoparasites seen."),
        ("Microcytic Hypochromic (Iron Deficiency)", "RBCs show marked microcytosis, hypochromia with mild to moderate anisopoikilocytosis and pencil cells. Platelets adequate. Features suggestive of Microcytic Hypochromic Anemia."),
        ("Dimorphic Anemia", "Dual population of microcytic hypochromic and macrocytic normochromic red cells observed. Features consistent with Dimorphic Anemia."),
        ("Neutrophilic Leukocytosis", "Marked leukocytosis with toxic granules and shift to left. Features suggestive of acute pyogenic infection / inflammatory response."),
        ("Thrombocytopenia", "Platelets markedly reduced on smear examination. No giant platelets or aggregates seen. Clinical correlation advised.")
    ],
    "Urine Examination": [
        ("Normal Routine Urine", "Clear pale yellow, acidic, nil albumin, nil sugar. Microscopic: 1-2 pus cells/hpf, epithelial cells occasional, nil casts/crystals."),
        ("Urinary Tract Infection (UTI)", "Turbid appearance. Albumin trace to 1+. Pus cells 25-30/hpf in clumps, plenty of epithelial cells and bacteria seen. Suggestive of active UTI."),
        ("Glucosuria & Ketonuria", "Sugar +++ (3+), Ketones moderate (++). Albumin trace. Acidic pH. Suggestive of diabetic ketosis.")
    ],
    "Lipid Profile Impression": [
        ("Desirable Lipid Profile", "All lipid parameters within optimal reference intervals for cardiovascular risk stratification."),
        ("Mixed Dyslipidemia", "Elevated Total Cholesterol and Triglycerides with low HDL-C. Suggestive of Mixed Dyslipidemia / Atherogenic risk.")
    ],
    "Thyroid Impression": [
        ("Primary Hypothyroidism", "Significantly elevated serum TSH with suppressed/low Free T4. Consistent with Primary Hypothyroidism."),
        ("Subclinical Hypothyroidism", "Mildly elevated serum TSH with normal Free T4/Total T4 concentrations. Suggestive of Subclinical Hypothyroidism.")
    ]
}


class SmartPhrasesDialog(QDialog):
    """Clinical comment & impression selector."""

    def __init__(self, parent: QWidget | None, on_insert: callable):
        super().__init__(parent)
        self.setWindowTitle("Pathology Smart-Phrases & Smear Comment Library")
        self.setFixedWidth(720)
        self.setFixedHeight(540)
        self.on_insert = on_insert
        self._build_ui()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        lay.addWidget(label("1-Click Clinical Impressions & Peripheral Smear Library", "strong"))

        h_split = QHBoxLayout()
        h_split.setSpacing(14)

        # Left List
        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(280)
        self.list_widget.setStyleSheet(
            "font-size: 10pt; font-weight: 600; padding: 4px; border: 1.5px solid #cbd5e1; border-radius: 4px;"
        )
        self.list_widget.itemSelectionChanged.connect(self._selection_changed)

        for cat, items in PHRASES.items():
            header = QListWidgetItem(f"📁 {cat.upper()}")
            header.setFlags(header.flags() & ~header.flags().ItemIsSelectable)
            self.list_widget.addItem(header)
            for title, phrase in items:
                it = QListWidgetItem(f"   • {title}")
                it.setData(32, phrase)
                self.list_widget.addItem(it)

        h_split.addWidget(self.list_widget)

        # Right Preview
        self.preview = QTextEdit()
        self.preview.setPlaceholderText("Select a clinical smart-phrase on the left to preview and edit...")
        self.preview.setStyleSheet(
            "font-size: 10pt; padding: 10px; border: 1.5px solid #cbd5e1; border-radius: 4px;"
        )
        h_split.addWidget(self.preview, 1)

        lay.addLayout(h_split, 1)

        insert_btn = button("✓ Insert into Job Remarks", "primary", self._insert_phrase)
        close_btn = button("Cancel", "", self.reject)
        lay.addWidget(row(None, close_btn, insert_btn))

    def _selection_changed(self) -> None:
        items = self.list_widget.selectedItems()
        if items:
            text = items[0].data(32)
            if text:
                self.preview.setPlainText(text)

    def _insert_phrase(self) -> None:
        text = self.preview.toPlainText().strip()
        if text and self.on_insert:
            self.on_insert(text)
        self.accept()
