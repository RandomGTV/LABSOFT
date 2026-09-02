"""Put LabSoft back to a factory-fresh state.

Everything the laboratory has recorded is removed: patients, jobs, results,
bills, payments, report PDFs, the settings, the staff logins and the test
library. What is left is the program itself and the assets folder, so the
logo, header photo and the bundled typeface survive.

Nothing is deleted until a complete copy has been zipped up, so a reset done
by mistake at half past eight on a Monday is recoverable.

Run it with RESET.bat, or:

    python reset_data.py            ask before doing anything
    python reset_data.py --yes      no questions (for a scripted rebuild)
"""

from __future__ import annotations

import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent

#: Wiped completely. Each is recreated empty the next time LabSoft opens.
FOLDERS = ["patients", "reports", "exports", "logs"]

#: The database and its write-ahead log. Deleting lab.db alone can leave a
#: half-written transaction in the -wal file that SQLite would replay into the
#: new database, so all three go together.
DB_FILES = ["data/lab.db", "data/lab.db-wal", "data/lab.db-shm"]

#: Dated copies made by the program itself. They hold the same patient data,
#: so a reset that left them behind would not be a reset.
BACKUP_DIR = "data/backups"

KEPT = ["assets (logo, header photo, signature, fonts)",
        "the program itself and its tests"]


def targets() -> list[Path]:
    found = [HERE / name for name in FOLDERS]
    found += [HERE / name for name in DB_FILES]
    found.append(HERE / BACKUP_DIR)
    return [p for p in found if p.exists()]


def describe(paths: list[Path]) -> str:
    lines = []
    for p in paths:
        if p.is_dir():
            files = [f for f in p.rglob("*") if f.is_file()]
            size = sum(f.stat().st_size for f in files)
            lines.append(f"    {p.name + '/':<22} {len(files):>5} files   "
                         f"{size / 1_048_576:6.1f} MB")
        else:
            lines.append(f"    {p.name:<22} {'':>5}         "
                         f"{p.stat().st_size / 1_048_576:6.1f} MB")
    return "\n".join(lines) or "    (nothing — LabSoft is already empty)"


def archive(paths: list[Path]) -> Path:
    """Zip everything that is about to go, before any of it goes."""
    stamp = datetime.now().strftime("%Y-%m-%d %H%M")
    out_dir = HERE / "data" / "before-reset"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"LabSoft data before reset {stamp}.zip"

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            if p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        z.write(f, f.relative_to(HERE))
            else:
                z.write(p, p.relative_to(HERE))
    return out


def remove(paths: list[Path]) -> list[str]:
    """Delete, reporting anything that would not go rather than stopping."""
    stuck = []
    for p in paths:
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
        except OSError as exc:
            stuck.append(f"{p.name}: {exc}")
    return stuck


def main() -> int:
    print()
    print("  LabSoft — clear all data")
    print("  " + "=" * 58)
    print()

    paths = targets()
    if not paths:
        print("  There is nothing to clear.")
        return 0

    print("  This will permanently remove:")
    print()
    print(describe(paths))
    print()
    print("  Everything goes: patients, results, reports, bills, the lab's")
    print("  own settings, the staff logins and the test library. LabSoft will")
    print("  start up as though it had just been installed.")
    print()
    print("  Kept:")
    for k in KEPT:
        print(f"    · {k}")
    print()
    print("  A zip of everything above is written to data\\before-reset first.")
    print()

    if "--yes" not in sys.argv:
        print("  Close LabSoft before continuing, or the database cannot be")
        print("  deleted while it is open.")
        print()
        if input("  Type  RESET  to go ahead: ").strip().upper() != "RESET":
            print("\n  Nothing was changed.\n")
            return 1

    print()
    print("  Making the backup…")
    try:
        saved = archive(paths)
    except OSError as exc:
        print(f"\n  Could not write the backup: {exc}")
        print("  Nothing has been deleted.\n")
        return 2
    print(f"  Saved: {saved.name}")

    print("  Clearing…")
    stuck = remove(paths)
    if stuck:
        print()
        print("  These could not be removed — LabSoft is probably still open:")
        for s in stuck:
            print(f"    · {s}")
        print("  Close it and run this again.")
        print()
        return 3

    print()
    print("  Done. LabSoft is empty.")
    print()
    print("  Next time it opens it will ask you to create the administrator")
    print("  account, load the test library again, and start numbering from")
    print("  whatever you set as the first report number.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
