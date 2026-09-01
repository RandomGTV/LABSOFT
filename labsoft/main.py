"""LabSoft — laboratory reporting for New Mithra Medical Laboratory.

Start with:  python main.py
"""

from __future__ import annotations

import re
import sys
import traceback
from datetime import datetime
from pathlib import Path


def _logs_dir() -> Path:
    """The log folder, found without importing anything that might be broken.

    Startup logging cannot depend on app.config, because a failure to import
    the application is exactly the case this has to record.
    """
    import os

    override = os.environ.get("LABSOFT_HOME")
    if override:
        base = Path(override).expanduser()
    elif getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent
    d = base / "logs"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        return base
    return d


def _log_error(text: str) -> Path:
    path = _logs_dir() / "error.log"
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"\n{'=' * 70}\n{datetime.now():%Y-%m-%d %H:%M:%S}\n{text}\n")
    except OSError:
        pass
    return path


def _log_startup_failure(exc: BaseException) -> None:
    """Write why the program could not start, in words the lab can act on.

    When launched with pythonw there is no console, so an unwritten error is an
    error nobody ever sees: the window simply vanishes. The launcher reads this
    file back and shows it.
    """
    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    if isinstance(exc, ImportError):
        # exc.name is not always populated (it is empty when the failure comes
        # from inside the module rather than from it being absent), so fall
        # back to the message, which always names it.
        missing = getattr(exc, "name", "") or ""
        if not missing:
            match = re.search(r"No module named ['\"]([\w.]+)['\"]", str(exc))
            missing = match.group(1) if match else ""
        missing = missing.split(".")[0] or "a required part"
        advice = (
            f"A required part of LabSoft is not installed: {missing}\n\n"
            f"This usually means Python was installed twice, and LabSoft was\n"
            f"started with the copy that does not have its parts.\n\n"
            f"To fix it, run INSTALL.bat in the LabSoft folder again.\n\n"
            f"Python being used:\n  {sys.executable}\n"
        )
    else:
        advice = (
            f"{type(exc).__name__}: {exc}\n\n"
            f"Python being used:\n  {sys.executable}\n"
        )

    try:
        with open(_logs_dir() / "startup_error.txt", "w", encoding="utf-8") as fh:
            fh.write(advice)
    except OSError:
        pass
    _log_error(detail)


def _install_error_handler(app) -> None:
    """Show unexpected errors as a plain sentence, never a traceback.

    The operator cannot act on a stack trace, and an unhandled exception in Qt
    otherwise vanishes silently and leaves the program in an odd state.
    """
    from PyQt6.QtWidgets import QMessageBox

    def handle(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        detail = "".join(traceback.format_exception(exc_type, exc, tb))
        path = _log_error(detail)
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Something went wrong")
        box.setText(
            "LabSoft hit a problem it did not expect.\n\n"
            "Your data is safe — everything typed so far has already been saved.\n\n"
            "Try the action again. If it keeps happening, close and reopen LabSoft."
        )
        box.setDetailedText(f"Saved to {path}\n\n{detail}")
        box.exec()

    sys.excepthook = handle


def main() -> int:
    from PyQt6.QtWidgets import QApplication, QMessageBox

    app = QApplication(sys.argv)
    app.setApplicationName("LabSoft")

    from app import config
    from app.ui import style

    # Palette first, then the stylesheet. A stylesheet only covers what it
    # names; the palette covers everything else, including popups and the
    # scroll-area viewports that Windows dark mode would otherwise paint black.
    style.apply_theme(app, "light")
    _install_error_handler(app)

    # Database: open, back up, migrate, seed on first run.
    try:
        from app.db import connection, queries, seed

        connection.connect()
        queries.ensure_defaults()
        made = seed.seed_all()
        # The chosen theme lives in the database, which only opens now — the
        # daylight one above stood in for these few milliseconds.
        style.apply_theme(app, queries.get_setting("theme") or "light")
    except Exception as exc:
        detail = traceback.format_exc()
        path = _log_error(detail)
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("LabSoft cannot start")
        box.setText(
            f"The data file could not be opened.\n\n{exc}\n\n"
            f"If the file has been moved or deleted, a copy is usually in:\n"
            f"{config.backup_dir()}")
        box.setDetailedText(f"Saved to {path}\n\n{detail}")
        box.exec()
        return 1

    # Sign in before anything is shown, so the window is built with the right
    # tabs for whoever is actually standing there.
    from app.ui.login_dialog import sign_in_at_startup
    from app.ui.main_window import MainWindow

    first_run_notification = made

    while True:
        proceed, _user = sign_in_at_startup()
        if not proceed or not _user:
            return 0

        window = MainWindow()
        window.show()

        if first_run_notification:
            QMessageBox.information(
                window, "Welcome to LabSoft",
                f"{first_run_notification} common tests have been loaded, with their usual normal "
                f"values.\n\nEverything is editable under the Tests tab — change "
                f"the wording, rates and ranges to match your lab, and delete what "
                f"you do not use.\n\nCheck the Settings tab to set your report "
                f"number and add your logo.")
            first_run_notification = 0

        app.exec()

        if not getattr(window, "was_signed_out", False):
            # User clicked X or closed the window to exit the application
            return 0
        # Otherwise was_signed_out is True: loop reopens the sign-in screen!


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as exc:            # noqa: BLE001 - last line of defence
        _log_startup_failure(exc)
        # If Qt is available at all, say so on screen too.
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox

            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(
                None, "LabSoft cannot start",
                "LabSoft could not start.\n\n"
                "The reason has been saved to logs\\startup_error.txt in the "
                "LabSoft folder.\n\nRunning INSTALL.bat again usually fixes it.")
        except BaseException:
            pass
        sys.exit(1)
