"""The pathology test library the program ships with.

Written in the lab's own style: group headings as they print on the report,
units attached to the value (105mg/dl), and Normal Value strings spelled the
way the lab writes them rather than reassembled from numbers.

Everything here is editable and deletable in the Tests screen. Seeding runs
only when the tests table is empty, so it never overwrites the lab's edits.
"""

from __future__ import annotations

from typing import List

from ..core.billing import to_paise
from . import queries as q
from .connection import get

# Group headings, in the order they print on a report.
G_HAEM = "HAEMATOLOGY"
G_BIO = "BIO-CHEMISTRY (Routine)"
G_LIPID = "LIPID PROFILE"
G_LFT = "LIVER FUNCTION TEST"
G_RFT = "RENAL FUNCTION TEST"
G_THY = "THYROID PROFILE"
G_ELEC = "ELECTROLYTES"
G_SERO = "SEROLOGY"
G_URINE = "URINE ROUTINE EXAMINATION"
G_STOOL = "STOOL EXAMINATION"
G_MISC = "OTHER INVESTIGATIONS"
G_COAG = "COAGULATION PROFILE"
G_IRON = "IRON STUDIES"
G_HORM = "HORMONE ASSAY"
G_TUMOUR = "TUMOUR MARKERS"
G_CARD = "CARDIAC PROFILE"
G_CULT = "CULTURE & SENSITIVITY"
G_SEMEN = "SEMEN ANALYSIS"


def _r(rule="range", low=None, high=None, text=None, sex="any",
       amin=None, amax=None, show=""):
    return {"rule_type": rule, "low": low, "high": high, "text_value": text or "",
            "sex": sex, "age_min": amin, "age_max": amax, "display_text": show}


# (code, name, group, unit, decimals, type, options, formula, rate, tat, ranges)
TESTS: List[tuple] = [

    # ------------------------------------------------------------- HAEMATOLOGY
    ("HB", "Haemoglobin", G_HAEM, "g/dl", 1, "numeric", "", "", 80, 3, [
        _r(low=13, high=17, sex="M", amin=15, show="13 - 17g/dl"),
        _r(low=12, high=15, sex="F", amin=15, show="12 - 15g/dl"),
        _r(low=11, high=14, amax=15, show="11 - 14g/dl"),
    ]),
    ("TC", "Total WBC Count", G_HAEM, "cells/cumm", 0, "numeric", "", "", 80, 3, [
        _r(low=4000, high=11000, show="4000 - 11000cells/cumm")]),
    ("RBC", "Total RBC Count", G_HAEM, "million/cumm", 2, "numeric", "", "", 80, 3, [
        _r(low=4.5, high=5.9, sex="M", show="4.5 - 5.9million/cumm"),
        _r(low=4.1, high=5.1, sex="F", show="4.1 - 5.1million/cumm")]),
    ("PLT", "Platelet Count", G_HAEM, "lakhs/cumm", 2, "numeric", "", "", 100, 3, [
        _r(low=1.5, high=4.5, show="1.5 - 4.5lakhs/cumm")]),
    ("PCV", "PCV / Haematocrit", G_HAEM, "%", 1, "numeric", "", "", 80, 3, [
        _r(low=40, high=50, sex="M", show="40 - 50%"),
        _r(low=36, high=46, sex="F", show="36 - 46%")]),
    ("MCV", "MCV", G_HAEM, "fl", 1, "numeric", "", "", 0, 3, [
        _r(low=80, high=100, show="80 - 100fl")]),
    ("MCH", "MCH", G_HAEM, "pg", 1, "numeric", "", "", 0, 3, [
        _r(low=27, high=32, show="27 - 32pg")]),
    ("MCHC", "MCHC", G_HAEM, "g/dl", 1, "numeric", "", "", 0, 3, [
        _r(low=32, high=36, show="32 - 36g/dl")]),
    ("RDW", "RDW-CV", G_HAEM, "%", 1, "numeric", "", "", 0, 3, [
        _r(low=11.5, high=14.5, show="11.5 - 14.5%")]),
    ("NEU", "Neutrophils", G_HAEM, "%", 0, "numeric", "", "", 0, 3, [
        _r(low=40, high=75, show="40 - 75%")]),
    ("LYM", "Lymphocytes", G_HAEM, "%", 0, "numeric", "", "", 0, 3, [
        _r(low=20, high=45, show="20 - 45%")]),
    ("EOS", "Eosinophils", G_HAEM, "%", 0, "numeric", "", "", 0, 3, [
        _r(low=1, high=6, show="1 - 6%")]),
    ("MON", "Monocytes", G_HAEM, "%", 0, "numeric", "", "", 0, 3, [
        _r(low=2, high=10, show="2 - 10%")]),
    ("BAS", "Basophils", G_HAEM, "%", 0, "numeric", "", "", 0, 3, [
        _r(rule="max", high=1, show="0 - 1%")]),
    ("DIFFTOT", "Differential Total", G_HAEM, "%", 0, "numeric", "",
     "NEU + LYM + EOS + MON + BAS", 0, 3, [
        _r(low=100, high=100, show="100%")]),
    ("ESR", "ESR (Westergren)", G_HAEM, "mm/hr", 0, "numeric", "", "", 60, 3, [
        _r(rule="max", high=15, sex="M", show="0 - 15mm/hr"),
        _r(rule="max", high=20, sex="F", show="0 - 20mm/hr")]),
    ("BT", "Bleeding Time", G_HAEM, "min", 1, "numeric", "", "", 60, 3, [
        _r(low=2, high=7, show="2 - 7min")]),
    ("CT", "Clotting Time", G_HAEM, "min", 1, "numeric", "", "", 60, 3, [
        _r(low=4, high=9, show="4 - 9min")]),
    ("PT", "Prothrombin Time", G_HAEM, "sec", 1, "numeric", "", "", 250, 6, [
        _r(low=11, high=15, show="11 - 15sec")]),
    ("INR", "INR", G_HAEM, "", 2, "numeric", "", "", 0, 6, [
        _r(low=0.8, high=1.2, show="0.8 - 1.2")]),
    ("RETIC", "Reticulocyte Count", G_HAEM, "%", 1, "numeric", "", "", 150, 6, [
        _r(low=0.5, high=2.5, show="0.5 - 2.5%")]),
    ("MP", "Malaria Parasite", G_HAEM, "", 0, "option", "Not Detected|Detected", "", 100, 3, [
        _r(rule="text", text="Not Detected", show="Not Detected")]),
    ("BLGRP", "Blood Group & Rh Type", G_HAEM, "", 0, "option",
     "A Positive|A Negative|B Positive|B Negative|AB Positive|AB Negative|O Positive|O Negative",
     "", 100, 3, []),

    # ------------------------------------------------------ BIO-CHEMISTRY
    ("GLU_F", "Blood Glucose [Fasting]", G_BIO, "mg/dl", 0, "numeric", "", "", 80, 4, [
        _r(low=70, high=110, show="70 - 110mg/dl")]),
    ("GLU_PP", "Blood Glucose [ P P 2 hrs ]", G_BIO, "mg/dl", 0, "numeric", "", "", 80, 4, [
        _r(low=70, high=140, show="70 - 140mg/dl")]),
    ("GLU_R", "Blood Glucose [Random]", G_BIO, "mg/dl", 0, "numeric", "", "", 80, 4, [
        _r(low=70, high=140, show="70 - 140mg/dl")]),
    ("HBA1C", "HbA1c (Glycated Haemoglobin)", G_BIO, "%", 1, "numeric", "", "", 450, 24, [
        _r(rule="max", high=5.7, show="< 5.7%")]),
    ("UREA", "Blood Urea", G_RFT, "mg/dl", 0, "numeric", "", "", 100, 4, [
        _r(low=15, high=45, show="15 - 45mg/dl")]),
    ("BUN", "Blood Urea Nitrogen", G_RFT, "mg/dl", 1, "numeric", "", "UREA / 2.14", 0, 4, [
        _r(low=7, high=21, show="7 - 21mg/dl")]),
    ("CREAT", "Serum Creatinine", G_RFT, "mg/dl", 2, "numeric", "", "", 120, 4, [
        _r(low=0.7, high=1.3, sex="M", show="0.7 - 1.3mg/dl"),
        _r(low=0.6, high=1.1, sex="F", show="0.6 - 1.1mg/dl")]),
    ("UA", "Serum Uric Acid", G_RFT, "mg/dl", 1, "numeric", "", "", 120, 4, [
        _r(low=3.5, high=7.2, sex="M", show="3.5 - 7.2mg/dl"),
        _r(low=2.6, high=6.0, sex="F", show="2.6 - 6.0mg/dl")]),
    ("CA", "Serum Calcium", G_BIO, "mg/dl", 1, "numeric", "", "", 150, 4, [
        _r(low=8.5, high=10.5, show="8.5 - 10.5mg/dl")]),
    ("PHOS", "Serum Phosphorus", G_BIO, "mg/dl", 1, "numeric", "", "", 150, 4, [
        _r(low=2.5, high=4.5, show="2.5 - 4.5mg/dl")]),
    ("AMY", "Serum Amylase", G_BIO, "U/L", 0, "numeric", "", "", 300, 6, [
        _r(low=30, high=110, show="30 - 110U/L")]),
    ("LIP", "Serum Lipase", G_BIO, "U/L", 0, "numeric", "", "", 350, 6, [
        _r(low=13, high=60, show="13 - 60U/L")]),
    ("CPK", "CPK Total", G_BIO, "U/L", 0, "numeric", "", "", 300, 6, [
        _r(low=25, high=195, show="25 - 195U/L")]),
    ("CKMB", "CK-MB", G_BIO, "U/L", 0, "numeric", "", "", 400, 6, [
        _r(rule="max", high=25, show="< 25U/L")]),
    ("LDH", "LDH", G_BIO, "U/L", 0, "numeric", "", "", 300, 6, [
        _r(low=140, high=280, show="140 - 280U/L")]),

    # ---------------------------------------------------- LIVER FUNCTION
    ("TBIL", "Total Bilirubin", G_LFT, "mg/dl", 2, "numeric", "", "", 100, 4, [
        _r(low=0.2, high=1.2, show="0.2 - 1.2mg/dl")]),
    ("DBIL", "Direct Bilirubin", G_LFT, "mg/dl", 2, "numeric", "", "", 100, 4, [
        _r(rule="max", high=0.3, show="< 0.3mg/dl")]),
    ("IBIL", "Indirect Bilirubin", G_LFT, "mg/dl", 2, "numeric", "", "TBIL - DBIL", 0, 4, [
        _r(low=0.2, high=0.9, show="0.2 - 0.9mg/dl")]),
    ("SGPT", "SGPT (ALT)", G_LFT, "U/L", 0, "numeric", "", "", 120, 4, [
        _r(rule="max", high=45, sex="M", show="< 45U/L"),
        _r(rule="max", high=34, sex="F", show="< 34U/L")]),
    ("SGOT", "SGOT (AST)", G_LFT, "U/L", 0, "numeric", "", "", 120, 4, [
        _r(rule="max", high=40, sex="M", show="< 40U/L"),
        _r(rule="max", high=32, sex="F", show="< 32U/L")]),
    ("ALP", "Alkaline Phosphatase", G_LFT, "U/L", 0, "numeric", "", "", 120, 4, [
        _r(low=44, high=147, show="44 - 147U/L")]),
    ("GGT", "Gamma GT", G_LFT, "U/L", 0, "numeric", "", "", 200, 6, [
        _r(rule="max", high=55, sex="M", show="< 55U/L"),
        _r(rule="max", high=38, sex="F", show="< 38U/L")]),
    ("TP", "Total Protein", G_LFT, "g/dl", 1, "numeric", "", "", 100, 4, [
        _r(low=6.0, high=8.3, show="6.0 - 8.3g/dl")]),
    ("ALB", "Albumin", G_LFT, "g/dl", 1, "numeric", "", "", 100, 4, [
        _r(low=3.5, high=5.2, show="3.5 - 5.2g/dl")]),
    ("GLOB", "Globulin", G_LFT, "g/dl", 1, "numeric", "", "TP - ALB", 0, 4, [
        _r(low=2.0, high=3.5, show="2.0 - 3.5g/dl")]),
    ("AGR", "A / G Ratio", G_LFT, "", 2, "numeric", "", "ALB / GLOB", 0, 4, [
        _r(low=1.0, high=2.1, show="1.0 - 2.1")]),

    # ------------------------------------------------------- LIPID PROFILE
    ("CHOL", "Total Cholesterol", G_LIPID, "mg/dl", 0, "numeric", "", "", 150, 6, [
        _r(rule="max", high=200, show="< 200mg/dl")]),
    ("TG", "Triglycerides", G_LIPID, "mg/dl", 0, "numeric", "", "", 150, 6, [
        _r(rule="max", high=150, show="< 150mg/dl")]),
    ("HDL", "HDL Cholesterol", G_LIPID, "mg/dl", 0, "numeric", "", "", 150, 6, [
        _r(rule="min", low=40, sex="M", show="> 40mg/dl"),
        _r(rule="min", low=50, sex="F", show="> 50mg/dl")]),
    ("LDL", "LDL Cholesterol", G_LIPID, "mg/dl", 0, "numeric", "",
     "CHOL - HDL - TG/5", 0, 6, [
        _r(rule="max", high=100, show="< 100mg/dl")]),
    ("VLDL", "VLDL Cholesterol", G_LIPID, "mg/dl", 0, "numeric", "", "TG / 5", 0, 6, [
        _r(low=5, high=40, show="5 - 40mg/dl")]),
    ("CHOLHDL", "Total Cholesterol / HDL Ratio", G_LIPID, "", 2, "numeric", "",
     "CHOL / HDL", 0, 6, [
        _r(rule="max", high=4.5, show="< 4.5")]),
    ("LDLHDL", "LDL / HDL Ratio", G_LIPID, "", 2, "numeric", "", "LDL / HDL", 0, 6, [
        _r(rule="max", high=3.5, show="< 3.5")]),

    # -------------------------------------------------------------- THYROID
    ("T3", "Total T3", G_THY, "ng/dl", 0, "numeric", "", "", 200, 24, [
        _r(low=80, high=200, show="80 - 200ng/dl")]),
    ("T4", "Total T4", G_THY, "µg/dl", 1, "numeric", "", "", 200, 24, [
        _r(low=5.1, high=14.1, show="5.1 - 14.1µg/dl")]),
    ("TSH", "TSH (Ultrasensitive)", G_THY, "µIU/ml", 2, "numeric", "", "", 250, 24, [
        _r(low=0.27, high=4.2, show="0.27 - 4.2µIU/ml")]),
    ("FT3", "Free T3", G_THY, "pg/ml", 2, "numeric", "", "", 300, 24, [
        _r(low=2.0, high=4.4, show="2.0 - 4.4pg/ml")]),
    ("FT4", "Free T4", G_THY, "ng/dl", 2, "numeric", "", "", 300, 24, [
        _r(low=0.93, high=1.7, show="0.93 - 1.7ng/dl")]),

    # ---------------------------------------------------------- ELECTROLYTES
    ("NA", "Serum Sodium", G_ELEC, "mmol/L", 0, "numeric", "", "", 150, 4, [
        _r(low=135, high=145, show="135 - 145mmol/L")]),
    ("K", "Serum Potassium", G_ELEC, "mmol/L", 1, "numeric", "", "", 150, 4, [
        _r(low=3.5, high=5.1, show="3.5 - 5.1mmol/L")]),
    ("CL", "Serum Chloride", G_ELEC, "mmol/L", 0, "numeric", "", "", 150, 4, [
        _r(low=98, high=107, show="98 - 107mmol/L")]),
    ("BICARB", "Serum Bicarbonate", G_ELEC, "mmol/L", 0, "numeric", "", "", 150, 4, [
        _r(low=22, high=29, show="22 - 29mmol/L")]),

    # -------------------------------------------------------------- SEROLOGY
    ("WIDAL", "Widal Test", G_SERO, "", 0, "text", "", "", 150, 6, []),
    ("CRP", "CRP (Quantitative)", G_SERO, "mg/L", 1, "numeric", "", "", 300, 6, [
        _r(rule="max", high=6, show="< 6mg/L")]),
    ("RA", "RA Factor", G_SERO, "IU/ml", 1, "numeric", "", "", 250, 6, [
        _r(rule="max", high=20, show="< 20IU/ml")]),
    ("ASO", "ASO Titre", G_SERO, "IU/ml", 0, "numeric", "", "", 250, 6, [
        _r(rule="max", high=200, show="< 200IU/ml")]),
    ("HBSAG", "HBsAg (Rapid)", G_SERO, "", 0, "option", "Non Reactive|Reactive", "", 200, 4, [
        _r(rule="text", text="Non Reactive", show="Non Reactive")]),
    ("HCV", "Anti HCV (Rapid)", G_SERO, "", 0, "option", "Non Reactive|Reactive", "", 300, 4, [
        _r(rule="text", text="Non Reactive", show="Non Reactive")]),
    ("HIV", "HIV I & II (Rapid)", G_SERO, "", 0, "option", "Non Reactive|Reactive", "", 300, 4, [
        _r(rule="text", text="Non Reactive", show="Non Reactive")]),
    ("VDRL", "VDRL / RPR", G_SERO, "", 0, "option", "Non Reactive|Reactive", "", 150, 4, [
        _r(rule="text", text="Non Reactive", show="Non Reactive")]),
    ("DENGUE", "Dengue NS1 / IgM / IgG", G_SERO, "", 0, "text", "", "", 600, 6, []),
    ("TYPHIDOT", "Typhidot IgM / IgG", G_SERO, "", 0, "text", "", "", 400, 6, []),
    ("UPT", "Urine Pregnancy Test", G_SERO, "", 0, "option", "Negative|Positive", "", 100, 1, [
        _r(rule="text", text="Negative", show="Negative")]),

    # ----------------------------------------------------------------- URINE
    ("U_COL", "Colour", G_URINE, "", 0, "text", "", "", 0, 2, []),
    ("U_APP", "Appearance", G_URINE, "", 0, "option", "Clear|Slightly Turbid|Turbid", "", 0, 2, [
        _r(rule="text", text="Clear", show="Clear")]),
    ("U_REACT", "Reaction (pH)", G_URINE, "", 1, "numeric", "", "", 0, 2, [
        _r(low=4.6, high=8.0, show="4.6 - 8.0")]),
    ("U_SG", "Specific Gravity", G_URINE, "", 3, "numeric", "", "", 0, 2, [
        _r(low=1.005, high=1.030, show="1.005 - 1.030")]),
    ("U_ALB", "Albumin", G_URINE, "", 0, "option", "Nil|Trace|+|++|+++", "", 0, 2, [
        _r(rule="text", text="Nil", show="Nil")]),
    ("U_SUG", "Sugar", G_URINE, "", 0, "option", "Nil|Trace|+|++|+++", "", 0, 2, [
        _r(rule="text", text="Nil", show="Nil")]),
    ("U_KET", "Ketone Bodies", G_URINE, "", 0, "option", "Nil|Trace|Present", "", 0, 2, [
        _r(rule="text", text="Nil", show="Nil")]),
    ("U_BS", "Bile Salt", G_URINE, "", 0, "option", "Absent|Present", "", 0, 2, [
        _r(rule="text", text="Absent", show="Absent")]),
    ("U_BP", "Bile Pigment", G_URINE, "", 0, "option", "Absent|Present", "", 0, 2, [
        _r(rule="text", text="Absent", show="Absent")]),
    ("U_PC", "Pus Cells", G_URINE, "/hpf", 0, "text", "", "", 0, 2, [
        _r(rule="text", text="0-2", show="0 - 2/hpf")]),
    ("U_EC", "Epithelial Cells", G_URINE, "/hpf", 0, "text", "", "", 0, 2, [
        _r(rule="text", text="0-2", show="0 - 2/hpf")]),
    ("U_RBC", "Red Blood Cells", G_URINE, "/hpf", 0, "text", "", "", 0, 2, [
        _r(rule="text", text="Nil", show="Nil")]),
    ("U_CAST", "Casts", G_URINE, "", 0, "text", "", "", 0, 2, [
        _r(rule="text", text="Nil", show="Nil")]),
    ("U_CRYS", "Crystals", G_URINE, "", 0, "text", "", "", 0, 2, [
        _r(rule="text", text="Nil", show="Nil")]),

    # ----------------------------------------------------------------- STOOL
    ("S_COL", "Colour", G_STOOL, "", 0, "text", "", "", 0, 2, []),
    ("S_CONS", "Consistency", G_STOOL, "", 0, "option", "Formed|Semi Formed|Loose", "", 0, 2, []),
    ("S_MUC", "Mucus", G_STOOL, "", 0, "option", "Absent|Present", "", 0, 2, [
        _r(rule="text", text="Absent", show="Absent")]),
    ("S_OVA", "Ova / Cyst", G_STOOL, "", 0, "option", "Not Seen|Seen", "", 0, 2, [
        _r(rule="text", text="Not Seen", show="Not Seen")]),
    ("S_PC", "Pus Cells", G_STOOL, "/hpf", 0, "text", "", "", 0, 2, [
        _r(rule="text", text="Nil", show="Nil")]),
    ("S_RBC", "Red Blood Cells", G_STOOL, "/hpf", 0, "text", "", "", 0, 2, [
        _r(rule="text", text="Nil", show="Nil")]),
    ("S_OB", "Occult Blood", G_STOOL, "", 0, "option", "Negative|Positive", "", 200, 4, [
        _r(rule="text", text="Negative", show="Negative")]),

    # ------------------------------------------------------------------ MISC
    ("VITD", "Vitamin D (25-OH)", G_MISC, "ng/ml", 1, "numeric", "", "", 1200, 48, [
        _r(low=30, high=100, show="30 - 100ng/ml")]),
    ("VITB12", "Vitamin B12", G_MISC, "pg/ml", 0, "numeric", "", "", 900, 48, [
        _r(low=200, high=900, show="200 - 900pg/ml")]),
    ("FERR", "Serum Ferritin", G_MISC, "ng/ml", 1, "numeric", "", "", 700, 24, [
        _r(low=30, high=400, sex="M", show="30 - 400ng/ml"),
        _r(low=13, high=150, sex="F", show="13 - 150ng/ml")]),
    ("IRON", "Serum Iron", G_MISC, "µg/dl", 0, "numeric", "", "", 400, 24, [
        _r(low=65, high=175, sex="M", show="65 - 175µg/dl"),
        _r(low=50, high=170, sex="F", show="50 - 170µg/dl")]),
    ("PSA", "PSA Total", G_MISC, "ng/ml", 2, "numeric", "", "", 700, 48, [
        _r(rule="max", high=4.0, sex="M", show="< 4.0ng/ml")]),
    # -------------------------------------------------------- SEMEN ANALYSIS
    ("SEMEN_TIME", "Collection Time", G_SEMEN, "", 0, "text", "", "", 0, 4, []),
    ("SEMEN_COL", "Colour", G_SEMEN, "", 0, "option",
     "Opaque white|Greyish white|Pale yellow|Dirty white", "", 0, 4, [
        _r(rule="text", text="Opaque white", show="Opaque white")]),
    ("SEMEN_REACT", "Reaction", G_SEMEN, "", 0, "option",
     "Alkaline|Acidic", "", 0, 4, [
        _r(rule="text", text="Alkaline", show="Alkaline")]),
    ("SEMEN_VISC", "Viscosity", G_SEMEN, "", 0, "option",
     "Normal|High|Low|Viscous", "", 0, 4, [
        _r(rule="text", text="Normal", show="Normal")]),
    ("SEMEN_LIQ", "Liquefaction Time", G_SEMEN, "", 0, "option",
     "> 1 hr|< 30 mins|30-60 mins|Within 30 mins", "", 0, 4, [
        _r(rule="text", text="Within 30 mins", show="Within 30 mins")]),
    ("SEMEN_VOL", "Volume", G_SEMEN, "ml", 1, "numeric", "", "", 0, 4, [
        _r(low=1.5, high=5.0, show="1.5 - 5.0ml")]),
    ("SEM_HDR_MIC", "Microscopic Examination", G_SEMEN, "", 0, "heading", "", "", 0, 4, []),
    ("SEMEN_COUNT", "Total Sperm Count", G_SEMEN, "million/ml", 0, "numeric", "", "", 400, 4, [
        _r(low=60, high=160, show="60-160million/ml")]),
    ("SEM_HDR_MOT", "Motility", G_SEMEN, "", 0, "heading", "", "", 0, 4, []),
    ("SEMEN_MOT_ACT", "Active", G_SEMEN, "%", 0, "numeric", "", "", 0, 4, [
        _r(rule="min", low=50, show="> 50%")]),
    ("SEMEN_MOT_SLUG", "Sluggish", G_SEMEN, "%", 0, "numeric", "", "", 0, 4, [
        _r(low=10, high=20, show="10 - 20%")]),
    ("SEMEN_MOT_NON", "Non-motile", G_SEMEN, "%", 0, "numeric", "", "", 0, 4, [
        _r(rule="max", high=20, show="< 20%")]),
    ("SEM_HDR_MORPH", "Morphology", G_SEMEN, "", 0, "heading", "", "", 0, 4, []),
    ("SEMEN_NORM", "Normal Forms", G_SEMEN, "%", 0, "numeric", "", "", 0, 4, [
        _r(rule="min", low=70, show="> 70%")]),
    ("SEMEN_GIANT", "Giant Head", G_SEMEN, "%", 0, "numeric", "", "", 0, 4, [
        _r(rule="max", high=15, show="< 15%")]),
    ("SEMEN_PIN", "Pin Head", G_SEMEN, "%", 0, "numeric", "", "", 0, 4, [
        _r(rule="max", high=5, show="< 5%")]),
    ("SEMEN_NECK", "Swollen Neck", G_SEMEN, "%", 0, "numeric", "", "", 0, 4, [
        _r(rule="max", high=5, show="< 5%")]),
    ("SEMEN_TAIL", "Long Tail", G_SEMEN, "%", 0, "numeric", "", "", 0, 4, [
        _r(rule="max", high=5, show="< 5%")]),
    ("SEMEN_PUS", "Pus Cells", G_SEMEN, "", 0, "text", "", "", 0, 4, [
        _r(rule="text", text="Nil / hpf seen", show="Nil / hpf seen")]),
    ("SEMEN_RBC", "RBCs", G_SEMEN, "", 0, "text", "", "", 0, 4, [
        _r(rule="text", text="Nil / hpf seen", show="Nil / hpf seen")]),
    ("SEMEN_BACT", "Bacteria", G_SEMEN, "", 0, "option",
     "Not seen|Seen|Occasional|Few", "", 0, 4, [
        _r(rule="text", text="Not seen", show="Not seen")]),
    ("SEMEN_OTH", "Others", G_SEMEN, "", 0, "text", "", "", 0, 4, [
        _r(rule="text", text="Not seen", show="Not seen")]),
]


# Quick-access panels. quick_button=1 puts a big button on the job screen.
PANELS = [
    ("CBC", ["HB", "TC", "RBC", "PLT", "PCV", "MCV", "MCH", "MCHC", "RDW",
             "NEU", "LYM", "EOS", "MON", "BAS"], 350, 1),
    ("Blood Sugar F & PP", ["GLU_F", "GLU_PP"], 150, 1),
    ("HbA1c (with Mean Blood Glucose)", ["HBA1C", "MBG"], 450, 1),
    ("Lipid Profile", ["CHOL", "TG", "HDL", "LDL", "VLDL", "CHOLHDL", "LDLHDL"], 600, 1),
    ("Liver Function Test", ["TBIL", "DBIL", "IBIL", "SGPT", "SGOT", "ALP",
                             "TP", "ALB", "GLOB", "AGR"], 650, 1),
    ("Renal Function Test", ["UREA", "BUN", "CREAT", "UA", "NA", "K"], 600, 1),
    ("Thyroid Profile", ["T3", "T4", "TSH"], 550, 1),
    ("Urine Routine", ["U_COL", "U_APP", "U_REACT", "U_SG", "U_ALB", "U_SUG",
                       "U_KET", "U_BS", "U_BP", "U_PC", "U_EC", "U_RBC",
                       "U_CAST", "U_CRYS"], 100, 1),
    ("Stool Routine", ["S_COL", "S_CONS", "S_MUC", "S_OVA", "S_PC", "S_RBC"], 100, 0),
    ("Diabetic Profile", ["GLU_F", "GLU_PP", "HBA1C", "MBG", "UREA", "CREAT"], 700, 1),
    ("Semen Analysis", ["SEMEN_TIME", "SEMEN_COL", "SEMEN_REACT", "SEMEN_VISC",
                        "SEMEN_LIQ", "SEMEN_VOL", "SEM_HDR_MIC", "SEMEN_COUNT",
                        "SEM_HDR_MOT", "SEMEN_MOT_ACT", "SEMEN_MOT_SLUG", "SEMEN_MOT_NON",
                        "SEM_HDR_MORPH", "SEMEN_NORM", "SEMEN_GIANT", "SEMEN_PIN",
                        "SEMEN_NECK", "SEMEN_TAIL", "SEMEN_PUS", "SEMEN_RBC",
                        "SEMEN_BACT", "SEMEN_OTH"], 400, 1),
    ("Fever Profile", ["HB", "TC", "PLT", "MP", "WIDAL", "DENGUE"], 900, 1),
]


# ---------------------------------------------------------------------------
# Added after the first release, on the lab's request. Anything already in the
# database is skipped, so these appear on existing installations too.
# ---------------------------------------------------------------------------

TESTS += [

    # ----------------------------------------------- HAEMATOLOGY (additions)
    ("ANC", "Absolute Neutrophil Count", G_HAEM, "cells/cumm", 0, "numeric", "",
     "TC * NEU / 100", 0, 3, [
        _r(low=1800, high=7700, show="1800 - 7700cells/cumm")]),
    ("ALC", "Absolute Lymphocyte Count", G_HAEM, "cells/cumm", 0, "numeric", "",
     "TC * LYM / 100", 0, 3, [
        _r(low=1000, high=4800, show="1000 - 4800cells/cumm")]),
    ("AEC", "Absolute Eosinophil Count", G_HAEM, "cells/cumm", 0, "numeric", "",
     "TC * EOS / 100", 60, 3, [
        _r(low=40, high=440, show="40 - 440cells/cumm")]),
    ("NLR", "Neutrophil / Lymphocyte Ratio", G_HAEM, "", 2, "numeric", "",
     "NEU / LYM", 0, 3, [
        _r(rule="max", high=3.0, show="< 3.0")]),
    ("MPV", "Mean Platelet Volume", G_HAEM, "fl", 1, "numeric", "", "", 0, 3, [
        _r(low=7.5, high=11.5, show="7.5 - 11.5fl")]),
    ("PS", "Peripheral Smear Study", G_HAEM, "", 0, "text", "", "", 200, 6, []),
    ("G6PD", "G6PD (Quantitative)", G_HAEM, "U/g Hb", 1, "numeric", "", "", 600, 24, [
        _r(low=6.8, high=13.6, show="6.8 - 13.6U/g Hb")]),
    ("SICKLE", "Sickling Test", G_HAEM, "", 0, "option", "Negative|Positive", "", 200, 6, [
        _r(rule="text", text="Negative", show="Negative")]),
    ("COOMBS", "Coombs Test (Direct)", G_HAEM, "", 0, "option",
     "Negative|Positive", "", 300, 6, [
        _r(rule="text", text="Negative", show="Negative")]),

    # ------------------------------------------------------------ COAGULATION
    ("APTT", "APTT", G_COAG, "sec", 1, "numeric", "", "", 350, 6, [
        _r(low=25, high=35, show="25 - 35sec")]),
    ("FIB", "Fibrinogen", G_COAG, "mg/dl", 0, "numeric", "", "", 450, 6, [
        _r(low=200, high=400, show="200 - 400mg/dl")]),
    ("DDIMER", "D-Dimer", G_COAG, "ng/ml", 0, "numeric", "", "", 900, 6, [
        _r(rule="max", high=500, show="< 500ng/ml")]),

    # ---------------------------------------------- BIO-CHEMISTRY (additions)
    ("MG", "Serum Magnesium", G_ELEC, "mg/dl", 2, "numeric", "", "", 250, 4, [
        _r(low=1.7, high=2.4, show="1.7 - 2.4mg/dl")]),
    ("ANGAP", "Anion Gap", G_ELEC, "mmol/L", 0, "numeric", "",
     "NA - CL - BICARB", 0, 4, [
        _r(low=8, high=16, show="8 - 16mmol/L")]),
    ("CACORR", "Corrected Calcium", G_BIO, "mg/dl", 1, "numeric", "",
     "CA + 0.8 * (4 - ALB)", 0, 4, [
        _r(low=8.5, high=10.5, show="8.5 - 10.5mg/dl")]),
    ("BUNCR", "BUN / Creatinine Ratio", G_RFT, "", 1, "numeric", "",
     "BUN / CREAT", 0, 4, [
        _r(low=10, high=20, show="10 - 20")]),
    ("MBG", "Mean Blood Glucose", G_BIO, "mg/dl", 0, "numeric", "",
     "28.7 * HBA1C - 46.7", 0, 24, [
        _r(rule="max", high=117, show="< 117mg/dl")]),
    ("EAG", "Estimated Average Glucose", G_BIO, "mg/dl", 0, "numeric", "",
     "28.7 * HBA1C - 46.7", 0, 24, [
        _r(rule="max", high=117, show="< 117mg/dl")]),
    ("INSULIN", "Fasting Insulin", G_BIO, "µIU/ml", 1, "numeric", "", "", 700, 24, [
        _r(low=2.6, high=24.9, show="2.6 - 24.9µIU/ml")]),
    ("HOMAIR", "HOMA-IR (Insulin Resistance)", G_BIO, "", 2, "numeric", "",
     "GLU_F * INSULIN / 405", 0, 24, [
        _r(rule="max", high=2.0, show="< 2.0")]),
    ("GTT1", "GTT — 1 hour", G_BIO, "mg/dl", 0, "numeric", "", "", 90, 4, [
        _r(rule="max", high=180, show="< 180mg/dl")]),
    ("GTT2", "GTT — 2 hours", G_BIO, "mg/dl", 0, "numeric", "", "", 90, 4, [
        _r(rule="max", high=140, show="< 140mg/dl")]),

    # ------------------------------------------------------ LIPID (additions)
    ("NONHDL", "Non-HDL Cholesterol", G_LIPID, "mg/dl", 0, "numeric", "",
     "CHOL - HDL", 0, 6, [
        _r(rule="max", high=130, show="< 130mg/dl")]),

    # ------------------------------------------------------------ IRON STUDIES
    ("TIBC", "Total Iron Binding Capacity", G_IRON, "µg/dl", 0, "numeric", "", "", 400, 24, [
        _r(low=250, high=450, show="250 - 450µg/dl")]),
    ("UIBC", "Unsaturated Iron Binding Capacity", G_IRON, "µg/dl", 0, "numeric", "",
     "TIBC - IRON", 0, 24, [
        _r(low=120, high=380, show="120 - 380µg/dl")]),
    ("TSAT", "Transferrin Saturation", G_IRON, "%", 1, "numeric", "",
     "IRON / TIBC * 100", 0, 24, [
        _r(low=20, high=50, show="20 - 50%")]),

    # ------------------------------------------------------------- HORMONES
    ("FSH", "FSH", G_HORM, "mIU/ml", 2, "numeric", "", "", 450, 24, [
        _r(low=1.5, high=12.4, sex="M", show="1.5 - 12.4mIU/ml"),
        _r(low=3.5, high=12.5, sex="F", show="3.5 - 12.5mIU/ml (follicular)")]),
    ("LH", "LH", G_HORM, "mIU/ml", 2, "numeric", "", "", 450, 24, [
        _r(low=1.7, high=8.6, sex="M", show="1.7 - 8.6mIU/ml"),
        _r(low=2.4, high=12.6, sex="F", show="2.4 - 12.6mIU/ml (follicular)")]),
    ("PRL", "Prolactin", G_HORM, "ng/ml", 1, "numeric", "", "", 450, 24, [
        _r(low=4.0, high=15.2, sex="M", show="4.0 - 15.2ng/ml"),
        _r(low=4.8, high=23.3, sex="F", show="4.8 - 23.3ng/ml")]),
    ("TESTO", "Testosterone (Total)", G_HORM, "ng/dl", 1, "numeric", "", "", 600, 24, [
        _r(low=249, high=836, sex="M", show="249 - 836ng/dl"),
        _r(low=8, high=48, sex="F", show="8 - 48ng/dl")]),
    ("E2", "Estradiol (E2)", G_HORM, "pg/ml", 1, "numeric", "", "", 650, 24, [
        _r(low=27, high=122, sex="F", show="27 - 122pg/ml (follicular)")]),
    ("PROG", "Progesterone", G_HORM, "ng/ml", 2, "numeric", "", "", 650, 24, [
        _r(rule="max", high=1.0, sex="F", show="< 1.0ng/ml (follicular)")]),
    ("BHCG", "Beta HCG", G_HORM, "mIU/ml", 2, "numeric", "", "", 700, 24, [
        _r(rule="max", high=5.0, show="< 5.0mIU/ml (non-pregnant)")]),
    ("AMH", "AMH", G_HORM, "ng/ml", 2, "numeric", "", "", 1800, 48, [
        _r(low=1.0, high=4.0, sex="F", show="1.0 - 4.0ng/ml")]),
    ("CORT", "Cortisol (Morning)", G_HORM, "µg/dl", 1, "numeric", "", "", 700, 24, [
        _r(low=6.2, high=19.4, show="6.2 - 19.4µg/dl")]),
    ("PTH", "Parathyroid Hormone (Intact)", G_HORM, "pg/ml", 1, "numeric", "", "", 1100, 48, [
        _r(low=15, high=65, show="15 - 65pg/ml")]),
    ("ATPO", "Anti-TPO Antibody", G_THY, "IU/ml", 1, "numeric", "", "", 900, 48, [
        _r(rule="max", high=34, show="< 34IU/ml")]),
    ("FOLATE", "Serum Folate", G_MISC, "ng/ml", 1, "numeric", "", "", 800, 48, [
        _r(low=3.1, high=20.5, show="3.1 - 20.5ng/ml")]),

    # -------------------------------------------------------- TUMOUR MARKERS
    ("AFP", "Alpha Feto Protein (AFP)", G_TUMOUR, "ng/ml", 1, "numeric", "", "", 800, 48, [
        _r(rule="max", high=10, show="< 10ng/ml")]),
    ("CEA", "CEA", G_TUMOUR, "ng/ml", 1, "numeric", "", "", 850, 48, [
        _r(rule="max", high=5, show="< 5ng/ml")]),
    ("CA125", "CA 125", G_TUMOUR, "U/ml", 1, "numeric", "", "", 950, 48, [
        _r(rule="max", high=35, show="< 35U/ml")]),
    ("CA199", "CA 19-9", G_TUMOUR, "U/ml", 1, "numeric", "", "", 1100, 48, [
        _r(rule="max", high=37, show="< 37U/ml")]),
    ("CA153", "CA 15-3", G_TUMOUR, "U/ml", 1, "numeric", "", "", 1100, 48, [
        _r(rule="max", high=31.3, show="< 31.3U/ml")]),
    ("FPSA", "Free PSA", G_TUMOUR, "ng/ml", 2, "numeric", "", "", 800, 48, [
        _r(rule="min", low=0, sex="M", show="—")]),
    ("PSARATIO", "Free / Total PSA Ratio", G_TUMOUR, "%", 1, "numeric", "",
     "FPSA / PSA * 100", 0, 48, [
        _r(rule="min", low=25, sex="M", show="> 25%")]),

    # -------------------------------------------------------------- CARDIAC
    ("TROPI", "Troponin I", G_CARD, "ng/ml", 3, "numeric", "", "", 900, 3, [
        _r(rule="max", high=0.04, show="< 0.04ng/ml")]),
    ("TROPT", "Troponin T", G_CARD, "ng/ml", 3, "numeric", "", "", 900, 3, [
        _r(rule="max", high=0.014, show="< 0.014ng/ml")]),
    ("NTPROBNP", "NT-proBNP", G_CARD, "pg/ml", 0, "numeric", "", "", 1800, 6, [
        _r(rule="max", high=125, show="< 125pg/ml")]),
    ("HSCRP", "hs-CRP", G_CARD, "mg/L", 2, "numeric", "", "", 600, 24, [
        _r(rule="max", high=1.0, show="< 1.0mg/L (low risk)")]),

    # ------------------------------------------------------ SEROLOGY additions
    ("HPYLORI", "H. Pylori Antibody", G_SERO, "", 0, "option",
     "Negative|Positive", "", 500, 6, [
        _r(rule="text", text="Negative", show="Negative")]),
    ("TPHA", "TPHA", G_SERO, "", 0, "option", "Non Reactive|Reactive", "", 400, 6, [
        _r(rule="text", text="Non Reactive", show="Non Reactive")]),
    ("CHIK", "Chikungunya IgM", G_SERO, "", 0, "option", "Negative|Positive", "", 700, 6, [
        _r(rule="text", text="Negative", show="Negative")]),
    ("SCRUB", "Scrub Typhus IgM", G_SERO, "", 0, "option", "Negative|Positive", "", 800, 6, [
        _r(rule="text", text="Negative", show="Negative")]),
    ("LEPTO", "Leptospira IgM", G_SERO, "", 0, "option", "Negative|Positive", "", 800, 6, [
        _r(rule="text", text="Negative", show="Negative")]),
    ("MANTOUX", "Mantoux Test", G_SERO, "mm", 0, "numeric", "", "", 300, 72, [
        _r(rule="max", high=9, show="< 10mm (negative)")]),

    # --------------------------------------------------------- URINE additions
    ("U_MALB", "Urine Microalbumin", G_URINE, "mg/L", 1, "numeric", "", "", 500, 24, [
        _r(rule="max", high=30, show="< 30mg/L")]),
    ("U_CREAT", "Urine Creatinine", G_URINE, "mg/dl", 1, "numeric", "", "", 200, 24, [
        _r(low=20, high=320, show="20 - 320mg/dl")]),
    ("U_ACR", "Urine Albumin / Creatinine Ratio", G_URINE, "mg/g", 1, "numeric", "",
     "U_MALB / U_CREAT * 100", 0, 24, [
        _r(rule="max", high=30, show="< 30mg/g")]),
    ("U_PROT24", "24 Hour Urine Protein", G_URINE, "mg/24hr", 0, "numeric", "", "", 400, 24, [
        _r(rule="max", high=150, show="< 150mg/24hr")]),

    # ---------------------------------------------------------- SEMEN ANALYSIS
    ("SM_VOL", "Volume", G_SEMEN, "ml", 1, "numeric", "", "", 0, 6, [
        _r(rule="min", low=1.5, show="> 1.5ml")]),
    ("SM_COUNT", "Sperm Concentration", G_SEMEN, "million/ml", 1, "numeric", "", "", 0, 6, [
        _r(rule="min", low=15, show="> 15million/ml")]),
    ("SM_TOTAL", "Total Sperm Count", G_SEMEN, "million", 1, "numeric", "",
     "SM_VOL * SM_COUNT", 0, 6, [
        _r(rule="min", low=39, show="> 39million")]),
    ("SM_MOT", "Total Motility", G_SEMEN, "%", 0, "numeric", "", "", 0, 6, [
        _r(rule="min", low=40, show="> 40%")]),
    ("SM_PROG", "Progressive Motility", G_SEMEN, "%", 0, "numeric", "", "", 0, 6, [
        _r(rule="min", low=32, show="> 32%")]),
    ("SM_MORPH", "Normal Morphology", G_SEMEN, "%", 0, "numeric", "", "", 0, 6, [
        _r(rule="min", low=4, show="> 4%")]),

    # ------------------------------------------------------------- CULTURES
    ("CUL_URINE", "Urine Culture & Sensitivity", G_CULT, "", 0, "text", "", "", 600, 72, []),
    ("CUL_BLOOD", "Blood Culture & Sensitivity", G_CULT, "", 0, "text", "", "", 900, 120, []),
    ("CUL_STOOL", "Stool Culture & Sensitivity", G_CULT, "", 0, "text", "", "", 600, 72, []),
    ("CUL_SWAB", "Throat / Wound Swab Culture", G_CULT, "", 0, "text", "", "", 600, 72, []),
]

PANELS += [
    ("Iron Studies", ["IRON", "TIBC", "UIBC", "TSAT", "FERR"], 1200, 1),
    ("Coagulation Profile", ["PT", "INR", "APTT"], 650, 0),
    ("Anaemia Profile", ["HB", "TC", "RBC", "PLT", "PCV", "MCV", "MCH", "MCHC",
                         "RETIC", "IRON", "TIBC", "TSAT", "FERR", "VITB12"], 2200, 1),
    ("Cardiac Profile", ["TROPI", "CKMB", "CPK", "LDH", "HSCRP"], 1800, 0),
    ("Full Body Checkup", ["HB", "TC", "PLT", "PCV", "ESR", "GLU_F", "HBA1C",
                           "UREA", "CREAT", "UA", "CHOL", "TG", "HDL", "LDL",
                           "TBIL", "SGPT", "SGOT", "ALP", "TP", "ALB", "TSH"],
     2500, 1),
    ("Fever Profile (Extended)", ["HB", "TC", "PLT", "MP", "WIDAL", "DENGUE",
                                  "CHIK", "SCRUB", "LEPTO", "CRP"], 1800, 0),
    ("PCOS Profile", ["FSH", "LH", "PRL", "TESTO", "TSH", "INSULIN", "GLU_F",
                      "HOMAIR"], 2800, 0),
]


# ---------------------------------------------------------------------------
# What each group is normally run on. A pathology report must say which
# specimen was tested: the same analyte read from serum and from whole blood
# does not mean the same thing.
# ---------------------------------------------------------------------------

GROUP_SPECIMEN = {
    G_HAEM: "Whole Blood (EDTA)",
    G_BIO: "Serum",
    G_LIPID: "Serum (fasting)",
    G_LFT: "Serum",
    G_RFT: "Serum",
    G_THY: "Serum",
    G_ELEC: "Serum",
    G_SERO: "Serum",
    G_URINE: "Urine (random)",
    G_STOOL: "Stool",
    G_MISC: "Serum",
    G_COAG: "Plasma (Citrate)",
    G_IRON: "Serum",
    G_HORM: "Serum",
    G_TUMOUR: "Serum",
    G_CARD: "Serum",
    G_CULT: "As collected",
    G_SEMEN: "Semen",
}

# A few tests are not run on their group's usual specimen.
SPECIMEN_OVERRIDES = {
    "HBA1C": "Whole Blood (EDTA)",
    "MBG": "Whole Blood (EDTA)",
    "EAG": "Whole Blood (EDTA)",
    "ESR": "Whole Blood (EDTA)",
    "BLGRP": "Whole Blood (EDTA)",
    "MP": "Whole Blood (EDTA)",
    "G6PD": "Whole Blood (EDTA)",
    "SICKLE": "Whole Blood (EDTA)",
    "COOMBS": "Whole Blood (EDTA)",
    "GLU_F": "Fluoride Plasma",
    "GLU_PP": "Fluoride Plasma",
    "GLU_R": "Fluoride Plasma",
    "GTT1": "Fluoride Plasma",
    "GTT2": "Fluoride Plasma",
    "HOMAIR": "Fluoride Plasma / Serum",
    "UPT": "Urine (first morning)",
    "U_PROT24": "Urine (24 hour)",
    "CUL_URINE": "Midstream Urine",
    "CUL_BLOOD": "Blood (culture bottle)",
    "CUL_STOOL": "Stool",
    "CUL_SWAB": "Swab",
    "MANTOUX": "Intradermal",
}


def specimen_for(code: str, group: str) -> str:
    return SPECIMEN_OVERRIDES.get(code.upper(), GROUP_SPECIMEN.get(group, "Serum"))


# ---------------------------------------------------------------------------
# Tests detailed enough to be issued on their own sheet, with the standard
# interpretation printed under the result.
# ---------------------------------------------------------------------------

DETAILED = {
    "HBA1C": (
        "REFERENCE RANGE & GLYCEMIC TARGETS\n"
        "    Normal            : < 5.7\n"
        "    Pre Diabetes      : 5.7 - 6.5\n"
        "    Diabetes          : > 6.5\n"
        "\n"
        "    Good Control      : < 6.5\n"
        "    Adequate Control  : 6.5 - 7.5\n"
        "    Inadequate Control: 7.5 - 8.5\n"
        "    Poor Control      : > 8.5\n"
        "\n"
        "Mean Blood Glucose (mg/dl) = 28.7 * HbA1c - 46.7\n"
        "\n"
        "NOTES:\n"
        "Glycosylated hemoglobin values are used to assess long-term glucose control in diabetes, "
        "especially in insulin-dependent diabetics whose glucose levels are labile, and in whom blood "
        "and urine glucose measurements exhibit significant daily variation. GHb measurements reflect "
        "the level of control present over the preceding 100-120 days. In such patients, whose fasting "
        "glucose concentrations are fairly consistent from day to day, there is a correlation between "
        "glycosylated hemoglobin and single fasting glucose levels. Continued high levels of blood glucose "
        "are reflected in high GHb concentrations. Glycosylated hemoglobin predicts the progression of "
        "retinopathy.\n\n"
        "Chronic blood loss, hemolytic anemia, or other setting for decrease in RBC life span, results in a "
        "decrease in the glycosylated hemoglobin level. Pregnancy may lower glycosylated hemoglobin."
    ),
    "TSH": (
        "TSH is the most sensitive single test of thyroid function. It should be "
        "read together with Free T4 where available.\n"
        "\n"
        "INTERPRETATION\n"
        "    TSH low,  T4 high     Hyperthyroidism\n"
        "    TSH high, T4 low      Hypothyroidism\n"
        "    TSH high, T4 normal   Subclinical hypothyroidism\n"
        "    TSH low,  T4 normal   Subclinical hyperthyroidism\n"
        "\n"
        "TSH rises in the evening and falls in the morning, so samples taken at "
        "different times of day are not directly comparable. Values are also "
        "affected by pregnancy, recent illness, steroids and biotin supplements."
    ),
    "PSA": (
        "PSA is prostate specific, not cancer specific.\n"
        "\n"
        "INTERPRETATION BY AGE\n"
        "    40 - 49 years     up to 2.5ng/ml\n"
        "    50 - 59 years     up to 3.5ng/ml\n"
        "    60 - 69 years     up to 4.5ng/ml\n"
        "    70 years and over up to 6.5ng/ml\n"
        "\n"
        "Raised values also occur in benign prostatic hyperplasia, prostatitis, "
        "urinary retention, and for some days after catheterisation, cycling or "
        "a rectal examination. A single raised result should be repeated before "
        "any conclusion is drawn."
    ),
    "VITD": (
        "INTERPRETATION\n"
        "    Below 20ng/ml     Deficiency\n"
        "    20 - 29ng/ml      Insufficiency\n"
        "    30 - 100ng/ml     Sufficiency\n"
        "    Above 100ng/ml    Possible toxicity\n"
        "\n"
        "Vitamin D deficiency is common and often without symptoms. Levels vary "
        "with sun exposure, skin pigmentation, obesity and supplementation."
    ),
    "SEMEN": (
        "Reported against WHO 2021 lower reference limits.\n"
        "\n"
        "    Volume                 1.4ml or more\n"
        "    Sperm concentration    16 million/ml or more\n"
        "    Total sperm count      39 million or more\n"
        "    Total motility         42% or more\n"
        "    Progressive motility   30% or more\n"
        "    Normal morphology      4% or more\n"
        "\n"
        "A single abnormal sample does not establish infertility. At least two "
        "samples, collected two to three weeks apart after 2 to 7 days of "
        "abstinence, are recommended before any conclusion."
    ),
}


def needs_seeding() -> bool:
    row = get().execute("SELECT COUNT(*) AS n FROM tests").fetchone()
    return int(row["n"]) == 0


def seed_all(force: bool = False) -> int:
    """Load the library, and top up with any tests added since installation.

    Tests already present are left completely alone -- including ones the lab
    has edited or hidden, because `existing` counts inactive tests too. So a
    test the lab deliberately hid never comes back.
    """
    existing = {t["code"].upper() for t in q.list_tests(include_inactive=True)}
    made = 0
    order_by_group: dict = {}

    for (code, name, group, unit, decimals, rtype, options, form,
         rate, tat, range_rows) in TESTS:
        if code.upper() in existing:
            continue
        order_by_group[group] = order_by_group.get(group, 0) + 10
        tid = q.save_test({
            "code": code, "name": name, "group_name": group, "unit": unit,
            "decimals": decimals, "result_type": rtype, "options": options,
            "formula": form, "rate_paise": to_paise(rate), "tat_hours": tat,
            "sort_order": order_by_group[group], "active": 1,
            "specimen": specimen_for(code, group),
            "separate_report": 1 if code.upper() in DETAILED else 0,
            "interpretation": DETAILED.get(code.upper(), ""),
        })
        if range_rows:
            q.replace_ranges(tid, range_rows)
        made += 1

    by_code = {t["code"].upper(): t["id"] for t in q.list_tests(include_inactive=True)}
    have_panels = {p["name"] for p in q.list_panels()}
    for i, (pname, codes, price, quick) in enumerate(PANELS):
        if pname in have_panels:
            continue
        ids = [by_code[c.upper()] for c in codes if c.upper() in by_code]
        if ids:
            q.save_panel({"name": pname, "price_paise": to_paise(price),
                          "quick_button": quick, "sort_order": i, "active": 1}, ids)

    q.log_action("library_seeded", "tests", None, f"{made} tests")
    return made
