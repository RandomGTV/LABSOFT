"""Database connection, startup backup, and restore.

Opening the database is the one moment the program can protect the lab's data,
so the backup happens here, before any migration runs.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .. import config
from . import schema

_conn: Optional[sqlite3.Connection] = None


class DatabaseError(RuntimeError):
    """Raised with a message written for the lab, not for a programmer."""


def connect(path: Optional[Path] = None, do_backup: bool = True) -> sqlite3.Connection:
    """Open (creating if needed), back up, and migrate."""
    global _conn
    p = Path(path) if path else config.db_path()
    p.parent.mkdir(parents=True, exist_ok=True)

    existed = p.exists()
    if existed and do_backup:
        try:
            backup_now(p)
        except OSError:
            # A failed backup must not stop the lab working. The status bar
            # shows the last successful backup time, so this stays visible.
            pass

    try:
        conn = sqlite3.connect(str(p))
    except sqlite3.Error as exc:
        raise DatabaseError(
            f"The data file could not be opened:\n{p}\n\n{exc}\n\n"
            "If the file has been moved or deleted, restore it from the "
            "backups folder."
        ) from exc

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = FULL")
    schema.apply_migrations(conn)

    _conn = conn
    return conn


def get() -> sqlite3.Connection:
    if _conn is None:
        return connect()
    return _conn


def close() -> None:
    global _conn
    if _conn is not None:
        try:
            _conn.commit()
            # Fold the WAL in on the way out, so the data file on disk is
            # complete on its own — that is the file the lab copies to a pendrive.
            try:
                _conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except sqlite3.Error:
                pass
            _conn.close()
        finally:
            _conn = None


# ---------------------------------------------------------------- backups

def backup_now(source: Optional[Path] = None) -> Path:
    """Write a complete, consistent copy of the database into backups/.

    Uses SQLite's own backup API rather than copying the file. The database runs
    in WAL mode, so recent work lives in the -wal side-file until it is
    checkpointed: a plain file copy produces a backup that is missing exactly
    the work the lab would most want back. Copying lab.db alone was silently
    yielding backups with zero jobs in them.
    """
    src = Path(source) if source else config.db_path()
    dest_dir = config.backup_dir()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    dest = dest_dir / f"lab_{stamp}.db"

    if not src.exists():
        raise DatabaseError(f"There is no data file to back up at:\n{src}")

    tmp = dest.with_suffix(".db.part")
    source_conn = _conn if (_conn is not None and source is None) else None
    opened_here = None
    try:
        if source_conn is None:
            opened_here = sqlite3.connect(str(src))
            source_conn = opened_here
        target = sqlite3.connect(str(tmp))
        try:
            source_conn.backup(target)
            target.commit()
        finally:
            target.close()
    except sqlite3.Error as exc:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise DatabaseError(f"The backup could not be written:\n{exc}") from exc
    finally:
        if opened_here is not None:
            opened_here.close()

    if dest.exists():
        dest.unlink()
    tmp.replace(dest)
    prune_backups()
    _copy_to_cloud(dest)
    return dest


def _copy_to_cloud(backup: Path) -> None:
    """Mirror a backup into the cloud folder, if one is configured.

    Failure here is reported in Settings but never raised: a lab with no
    internet must still get its local backup.
    """
    try:
        from ..db import queries as q
        from ..output import cloud

        if not q.setting_bool("cloud_backup"):
            return
        status = cloud.copy_backup(
            backup,
            configured=q.get_setting("cloud_folder"),
            lab_name=(q.get_setting("lab_name_prefix") + " "
                      + q.get_setting("lab_name")).strip(),
        )
        q.set_setting("cloud_last_status", status.detail)
        if status.available:
            q.set_setting("cloud_last_copy", datetime.now().strftime("%Y-%m-%d %H:%M"))
    except Exception:
        pass


def checkpoint() -> None:
    """Fold the WAL back into the main file. Called before the app closes."""
    if _conn is None:
        return
    try:
        _conn.commit()
        _conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.Error:
        pass


def list_backups() -> List[Path]:
    """Newest first."""
    return sorted(
        config.backup_dir().glob("lab_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def prune_backups(keep: int = config.BACKUPS_TO_KEEP) -> int:
    removed = 0
    for old in list_backups()[keep:]:
        try:
            old.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def last_backup_time() -> Optional[datetime]:
    backups = list_backups()
    if not backups:
        return None
    return datetime.fromtimestamp(backups[0].stat().st_mtime)


def restore_from(backup: Path) -> None:
    """Replace the live database with a backup, after saving the current one."""
    src = Path(backup)
    if not src.exists():
        raise DatabaseError(f"That backup no longer exists:\n{src}")

    close()
    target = config.db_path()
    if target.exists():
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        shutil.copy2(target, config.backup_dir() / f"before_restore_{stamp}.db")
    # Remove WAL side-files so the restored database is not merged with newer
    # journal contents from the file being replaced.
    for suffix in ("-wal", "-shm"):
        side = Path(str(target) + suffix)
        if side.exists():
            try:
                side.unlink()
            except OSError:
                pass
    shutil.copy2(src, target)
    connect(target, do_backup=False)
