"""Where things live on disk, and the built-in defaults.

Everything sits under one folder next to the executable, so the whole
installation can be copied to another PC or a pendrive by copying that folder.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "LabSoft"
APP_VERSION = "1.0.0"

BACKUPS_TO_KEEP = 30


def base_dir() -> Path:
    """The folder the program runs from.

    When frozen by PyInstaller, sys.executable is the .exe; otherwise it is the
    project root. An override lets the tests point everything at a temp folder.
    """
    override = os.environ.get("LABSOFT_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    return _ensure(base_dir() / "data")


def db_path() -> Path:
    return data_dir() / "lab.db"


def backup_dir() -> Path:
    return _ensure(data_dir() / "backups")


def assets_dir() -> Path:
    return _ensure(base_dir() / "assets")


def templates_dir() -> Path:
    return _ensure(base_dir() / "templates")


def reports_dir() -> Path:
    return _ensure(base_dir() / "reports")


def exports_dir() -> Path:
    return _ensure(base_dir() / "exports")


def logs_dir() -> Path:
    return _ensure(base_dir() / "logs")


def report_month_dir(when) -> Path:
    return _ensure(reports_dir() / when.strftime("%Y-%m"))


def patients_dir() -> Path:
    return _ensure(base_dir() / "patients")


def patient_dir(patient_id: int = 0, name: str = "", phone: str = "") -> Path:
    """Each patient has their own folder named with their name inside the patients directory."""
    import re

    safe_name = re.sub(r'[\\/:*?"<>|]+', '', (name or "Unknown")).strip()
    safe_name = re.sub(r"\s+", " ", safe_name)[:80].rstrip(" .") or "Unknown"
    return _ensure(patients_dir() / safe_name)


def _ensure(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# Default settings. Written on first run; editable in the Settings screen.
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = {
    "lab_name": "MITHRA",
    "lab_name_prefix": "New",
    "lab_subtitle": "MEDICAL LABORATORY",
    "lab_address_1": "Chettiyankinar Road, Kuttippala,",
    "lab_address_2": "Opp. Govt. Ayurveda Dispensary",
    "lab_phone": "Ph : +91 81578 87311, 95266 77311",
    "lab_email": "e-mail : mithralab12020@gmail.com",

    "sign_left_name": "SAHEED MOHAMED. P.",
    "sign_left_qual": "BScMLT",
    "sign_left_role": "Technologist",
    "sign_mid_name": "FATTIMATH SAKIRA.M.",
    "sign_mid_qual": "MScMicrobiology",
    "sign_mid_role": "Microbiologist",
    "sign_right_name": "ABDUNNASER MAYYERI",
    "sign_right_qual": "DMLT BScMLT",
    "sign_right_role": "Lab Incharge",

    "end_line_1": "-End of Report-",
    "end_line_2": "- New MITHRA -",
    "footer_note": "",
    "print_disclaimer": "0",
    "disclaimer_text": "The result of the investigations depends upon the quality of the specimen received for the investigations isolated laboratory investigations never confirm the final diagnosis of the diseases. The reported results are only for the information of the referring doctor. incase of doubts abouts results reported. referring doctors can request for a free recheck",

    # Printing
    "print_header": "0",       # 0 when using preprinted letterhead paper
    "blank_header_mm": "36",   # top spacing (mm) when print_header is 0
    "print_flags": "0",        # abnormal marking on the printed report, off
    "watermark": "0",
    # Letterhead design: "classic" is the old plain heading, "modern" is the
    # teal medical band. Only affects pages LabSoft prints the header on.
    "header_style": "modern",
    # Show the specimen (Serum, Plasma, Whole Blood…) under each group heading.
    "print_specimen": "1",
    # Long-form tests (HbA1c, TSH…) also get their own detailed PDF.
    "separate_detail_reports": "1",
    "logo_file": "logo.png",
    "header_photo_file": "header_photo.png",
    "signature_file": "",

    # Numbering
    "next_report_no": "51359",

    # WhatsApp
    "whatsapp_template": (
        "Dear {name},\n"
        "Your test report from {lab} (Report No {report_no}, {date}) is attached.\n"
        "For any query call {phone}.\n"
        "Thank you."
    ),
    "country_code": "91",
    # auto = use the desktop app when it is installed, otherwise WhatsApp Web.
    # Set to "web" to always use the browser, or "desktop" to always use the app.
    "whatsapp_mode": "auto",
    # Bring WhatsApp to the front and paste the report in automatically.
    # Sending itself always stays manual.
    "auto_attach": "1",
    # Show the report on screen after Check & make report, before sending.
    "preview_before_send": "1",

    # Cloud backup. Empty folder = auto-detect Google Drive.
    "cloud_backup": "1",
    "cloud_folder": "",

    # Behaviour
    "default_tat_hours": "24",
    "age_default_unit": "years",

    # Appearance on screen. "light" or "dark"; the report is never dark.
    "theme": "light",
}

# Displayed in the Settings screen, grouped and in this order.
SETTINGS_GROUPS = [
    ("Laboratory", [
        ("lab_name_prefix", "Name prefix"),
        ("lab_name", "Laboratory name"),
        ("lab_subtitle", "Subtitle strip"),
        ("lab_address_1", "Address line 1"),
        ("lab_address_2", "Address line 2"),
        ("lab_phone", "Phone line"),
        ("lab_email", "Email line"),
    ]),
    ("Signatories", [
        ("sign_left_name", "Left name"),
        ("sign_left_qual", "Left qualification"),
        ("sign_left_role", "Left role"),
        ("sign_mid_name", "Middle name (optional)"),
        ("sign_mid_qual", "Middle qualification"),
        ("sign_mid_role", "Middle role"),
        ("sign_right_name", "Right name"),
        ("sign_right_qual", "Right qualification"),
        ("sign_right_role", "Right role"),
    ]),
    ("Report & Letterhead", [
        ("blank_header_mm", "Preprinted letterhead top space (mm)"),
        ("end_line_1", "End line 1"),
        ("end_line_2", "End line 2"),
        ("footer_note", "Footer note"),
        ("disclaimer_text", "Bottom disclaimer note"),
        ("logo_file", "Logo file (in assets)"),
        ("header_photo_file", "Header photo file (in assets)"),
        ("signature_file", "Signature image (optional)"),
    ]),
    ("Numbering", [
        ("next_report_no", "Next report number"),
    ]),
    ("WhatsApp", [
        ("country_code", "Country code"),
        ("whatsapp_mode", "Open using (auto / desktop / web)"),
        ("whatsapp_template", "Message template"),
    ]),
]
