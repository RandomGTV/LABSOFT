"""Where things live on disk, and the built-in defaults.

Everything sits under one folder next to the executable, so the whole
installation can be copied to another PC or a pendrive by copying that folder.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, Sequence

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


#: Names Windows reserves for devices. A folder called CON or LPT1 cannot be
#: created, so a patient called that would have had no folder at all.
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{n}" for n in range(1, 10)),
    *(f"LPT{n}" for n in range(1, 10)),
}


def patient_name_part(name: str) -> str:
    """The readable half of a patient folder's name.

    This strips more than Windows forbids, on purpose. The folder name ends up
    inside command lines -- the report is put on the clipboard by PowerShell,
    and the folder is opened by Explorer -- and a patient's name is typed by
    whoever is at the counter. Shell metacharacters have no business in a
    folder name, and taking them out here means no caller has to remember to
    quote. (The PowerShell call passes the path as an argument as well; this is
    the second of the two locks, not the only one.)
    """
    import re

    safe = re.sub(r'[\\/:*?"<>|$`;&()\[\]{}%!^~\x00-\x1f]+', '',
                  (name or "Unknown")).strip()
    safe = re.sub(r"\s+", " ", safe)[:80].rstrip(" .")
    if not safe:
        return "Unknown"
    # CON.pdf is as reserved as CON, so the stem is what has to be checked --
    # and the fix has to be a PREFIX: "CON (name)" still begins with the
    # reserved stem as far as Windows is concerned.
    if safe.split(".")[0].upper() in _RESERVED_NAMES:
        return f"Patient {safe}"
    return safe


def patient_dir(patient_id: int = 0, name: str = "", phone: str = "",
                also_known_as: Optional[Sequence[str]] = None) -> Path:
    """One folder per patient: ``patients/<Name> #<id>``.

    The id is not decoration. Two people genuinely are called Anil Sharma, and
    without something unique they share a folder -- one patient opening it sees
    the other's reports, and the second details card overwrites the first.

    The id also keeps the folder findable when the name is corrected later: an
    existing folder carrying this id is renamed rather than abandoned, so a
    patient's history never splits in two.
    """
    readable = patient_name_part(name)
    if not patient_id:
        return _ensure(patients_dir() / readable)

    root = patients_dir()
    canonical = root / f"{readable} #{int(patient_id)}"
    if canonical.exists():
        return canonical

    marker = f" #{int(patient_id)}"
    for existing in sorted(root.iterdir()) if root.exists() else []:
        # Same patient, different spelling of their name: move it, don't
        # start a second folder beside it.
        if existing.is_dir() and existing.name.endswith(marker):
            return _rename_patient_dir(existing, canonical)

    # Installations filed before the id was part of the name. There may be more
    # than one such folder for the same person: reports were filed under the
    # printed name ("rajeev .H") while the details card went under the plain
    # one ("rajeev"). Adopt the first and fold the rest into it, so nothing
    # already on disk is left stranded.
    candidates = [readable]
    for alias in (also_known_as or []):
        alias = patient_name_part(alias)
        if alias and alias not in candidates:
            candidates.append(alias)

    legacy = [root / c for c in candidates if (root / c).is_dir()]
    if not legacy:
        return _ensure(canonical)

    home = _rename_patient_dir(legacy[0], canonical)
    for stray in legacy[1:]:
        _merge_patient_dir(stray, home)
    return home


def _merge_patient_dir(stray: Path, home: Path) -> None:
    """Move one folder's files into another, then drop the empty shell.

    Nothing is overwritten: a name already taken in the destination keeps a
    suffix. Two files with the same name are two different pieces of a
    patient's history, and deciding which to discard is not this function's
    business.
    """
    try:
        for item in sorted(stray.iterdir()):
            if not item.is_file():
                continue
            target = home / item.name
            n = 2
            while target.exists():
                target = home / f"{item.stem} ({n}){item.suffix}"
                n += 1
            item.rename(target)
        stray.rmdir()
    except OSError:
        pass          # a locked file must never cost the operator their folder


def _rename_patient_dir(old: Path, new: Path) -> Path:
    """Move a patient's folder, and carry on with the old one if we cannot.

    A rename fails when a report in the folder is open in a PDF reader. Losing
    the report because the folder could not be tidied would be a far worse
    outcome than an untidy folder name.
    """
    try:
        old.rename(new)
        return new
    except OSError:
        return old


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
    # Its own image, rather than always reusing the logo: a logo is
    # drawn to be read small and dark, and a watermark to disappear
    # behind text. Left empty, the logo stands in as it always did.
    "watermark_file": "",
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
    # The desktop app, not the browser: a report can only be attached
    # to the application. "web" stays available for a lab that has no
    # desktop WhatsApp and is content to send the message alone.
    "whatsapp_mode": "desktop",
    # Bring WhatsApp to the front and paste the report in automatically.
    # Sending itself always stays manual.
    "auto_attach": "1",
    # Show the report on screen after Check & make report, before sending.
    "preview_before_send": "1",

    # Cloud backup. Empty folder = auto-detect Google Drive.
    # OFF until the lab turns it on. It defaulted to "1" with an empty folder
    # meaning "find one automatically", and the finder takes the first of
    # Google Drive / OneDrive / Dropbox it sees — so on a PC with any of those
    # installed for personal use, the complete unencrypted patient database
    # began uploading from first launch, with no prompt.
    "cloud_backup": "0",
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
        # The four image settings used to be typed in here as filenames. They
        # live on the Images page now, where they are chosen with a file
        # picker and shown with whether the file is actually there -- a
        # filename typed by hand is a filename that can be typed wrong.
    ]),
    ("Numbering", [
        ("next_report_no", "Next report number"),
    ]),
    ("WhatsApp", [
        ("country_code", "Country code"),
        ("whatsapp_mode", "Open WhatsApp in"),
        ("whatsapp_template", "Message template"),
    ]),
]
