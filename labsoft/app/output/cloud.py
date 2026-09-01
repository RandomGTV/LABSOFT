"""Copying backups into a cloud-synced folder.

No accounts, no tokens, no consent screens. Google Drive for Desktop presents
itself as an ordinary folder; LabSoft finds it and copies backups in, and Drive
uploads them by itself. That means:

  * nothing to sign in to, and no password stored in the program
  * it works offline -- the copy is made locally and Drive catches up later
  * it works identically with OneDrive, Dropbox, or a pendrive, because the
    lab can point it at any folder

The alternative, talking to the Google API directly, needs a Google Cloud
project, a consent screen, and a token that expires -- all of which eventually
lands on a lab technician at 8pm with a broken backup.
"""

from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

FOLDER_NAME = "LabSoft Backups"
COPIES_TO_KEEP = 14


@dataclass
class CloudStatus:
    available: bool
    path: Optional[Path] = None
    provider: str = ""
    detail: str = ""


# ---------------------------------------------------------------------------
# Finding the synced folder
# ---------------------------------------------------------------------------

def _home() -> Path:
    return Path(os.path.expanduser("~"))


def candidate_folders() -> List[tuple]:
    """(provider, path) for every cloud folder that exists on this PC."""
    found: List[tuple] = []
    home = _home()

    def add(provider: str, path: Path) -> None:
        try:
            if path.is_dir() and not any(p == path for _n, p in found):
                found.append((provider, path))
        except OSError:
            pass

    # Google Drive for Desktop, in its various shapes across versions.
    add("Google Drive", home / "Google Drive")
    add("Google Drive", home / "My Drive")
    add("Google Drive", home / "GoogleDrive")

    if platform.system() == "Windows":
        # Newer Drive versions mount a virtual drive letter containing "My Drive".
        for letter in "GHIJKLMNOPQRSTUVWXYZ":
            root = Path(f"{letter}:/")
            try:
                if not root.exists():
                    continue
            except OSError:
                continue
            add("Google Drive", root / "My Drive")
            add("Google Drive", root / "Shared drives")

        env = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer")
        if env:
            add("OneDrive", Path(env))
    else:
        add("Google Drive", home / "gdrive")

    add("OneDrive", home / "OneDrive")
    add("Dropbox", home / "Dropbox")
    return found


def detect() -> CloudStatus:
    """The first cloud folder found, if any."""
    for provider, path in candidate_folders():
        return CloudStatus(True, path, provider,
                           f"{provider} found at {path}")
    return CloudStatus(
        False, None, "",
        "No Google Drive folder was found on this computer. Install Google "
        "Drive for Desktop, or choose any folder yourself in Settings.")


def resolve(configured: str = "") -> CloudStatus:
    """Use the folder the lab configured, else auto-detect."""
    text = (configured or "").strip()
    if text:
        path = Path(text).expanduser()
        if path.is_dir():
            return CloudStatus(True, path, "Chosen folder", f"Using {path}")
        return CloudStatus(
            False, path, "Chosen folder",
            f"The backup folder set in Settings does not exist:\n{path}\n\n"
            f"Either create it, or choose a different one.")
    return detect()


# ---------------------------------------------------------------------------
# Copying
# ---------------------------------------------------------------------------

def target_dir(status: CloudStatus, lab_name: str = "") -> Optional[Path]:
    if not status.available or status.path is None:
        return None
    name = FOLDER_NAME
    if lab_name.strip():
        name = f"{FOLDER_NAME} - {_safe(lab_name)}"
    folder = status.path / name
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    return folder


def _safe(text: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9 ._-]+", "", text or "").strip()[:40] or "Lab"


def copy_backup(backup: Path, configured: str = "",
                lab_name: str = "", keep: int = COPIES_TO_KEEP) -> CloudStatus:
    """Copy one backup into the cloud folder and prune old ones.

    Written to a .part name first and then moved, so the sync client never
    starts uploading a half-written database.
    """
    status = resolve(configured)
    if not status.available:
        return status

    folder = target_dir(status, lab_name)
    if folder is None:
        return CloudStatus(False, status.path, status.provider,
                           f"The folder could not be created inside {status.path}.")

    source = Path(backup)
    if not source.exists():
        return CloudStatus(False, folder, status.provider,
                           f"There is no backup to copy at:\n{source}")

    destination = folder / source.name
    temporary = folder / (source.name + ".part")
    try:
        shutil.copy2(source, temporary)
        if destination.exists():
            destination.unlink()
        temporary.replace(destination)
    except OSError as exc:
        try:
            if temporary.exists():
                temporary.unlink()
        except OSError:
            pass
        return CloudStatus(False, folder, status.provider,
                           f"The copy could not be written:\n{exc}")

    pruned = prune(folder, keep)
    detail = f"Copied to {status.provider}: {destination.name}"
    if pruned:
        detail += f" ({pruned} older cop{'y' if pruned == 1 else 'ies'} removed)"
    return CloudStatus(True, destination, status.provider, detail)


def list_copies(folder: Path) -> List[Path]:
    try:
        return sorted(Path(folder).glob("lab_*.db"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return []


def prune(folder: Path, keep: int = COPIES_TO_KEEP) -> int:
    removed = 0
    for old in list_copies(folder)[max(0, keep):]:
        try:
            old.unlink()
            removed += 1
        except OSError:
            pass
    return removed
