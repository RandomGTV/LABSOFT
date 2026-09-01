"""Startup failure reporting.

When launched with pythonw there is no console, so an error that is not written
to a file is an error nobody ever sees — the window just flashes and vanishes.
These tests hold that path honest.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("LABSOFT_HOME", str(tmp_path))
    sys.modules.pop("main", None)
    import main

    return main, tmp_path


def test_missing_part_is_explained_not_swallowed(home):
    main, tmp = home
    exc = ImportError("No module named 'PyQt6'", name="PyQt6")
    main._log_startup_failure(exc)

    report = (tmp / "logs" / "startup_error.txt").read_text(encoding="utf-8")
    assert "PyQt6" in report
    assert "INSTALL.bat" in report          # tells the reader what to do
    assert sys.executable in report         # names which Python was used
    assert "Traceback" not in report        # the operator gets words, not a dump


def test_other_failures_are_reported_too(home):
    main, tmp = home
    main._log_startup_failure(PermissionError("data file is locked"))
    report = (tmp / "logs" / "startup_error.txt").read_text(encoding="utf-8")
    assert "PermissionError" in report
    assert "data file is locked" in report


def test_full_traceback_goes_to_the_error_log(home):
    """The readable file is for the lab; the full trace is kept for whoever fixes it."""
    main, tmp = home
    try:
        raise ValueError("boom")
    except ValueError as exc:
        main._log_startup_failure(exc)

    log = (tmp / "logs" / "error.log").read_text(encoding="utf-8")
    assert "Traceback" in log
    assert "boom" in log


def test_logs_dir_is_created_when_absent(home):
    main, tmp = home
    assert not (tmp / "logs").exists()
    main._log_error("hello")
    assert (tmp / "logs" / "error.log").exists()


def test_launcher_never_uses_a_bare_pythonw():
    """The original bug: 'pythonw' from PATH may be a different Python with
    nothing installed, and it discards the error because it has no console."""
    root = Path(__file__).resolve().parent.parent
    launcher = (root / "RUN LabSoft.bat").read_text(encoding="utf-8", errors="replace")

    assert "import PyQt6" in launcher, "launcher must verify PyQt6 before starting"
    assert "python_path.txt" in launcher, "launcher must use the recorded interpreter"
    assert "startup_error.txt" in launcher, "launcher must surface a startup failure"
    assert "pause" in launcher, "the window must stay open when something is wrong"

    for line in launcher.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("start ") and "pythonw" in stripped.lower():
            assert "%PYW%" in stripped, f"launcher starts an unverified pythonw: {stripped}"


def test_installer_records_the_interpreter_it_used():
    root = Path(__file__).resolve().parent.parent
    installer = (root / "INSTALL.bat").read_text(encoding="utf-8", errors="replace")
    assert "python_path.txt" in installer
    assert "import PyQt6" in installer, "installer must verify before claiming success"


def test_diagnose_script_exists():
    root = Path(__file__).resolve().parent.parent
    assert (root / "DIAGNOSE.bat").exists()
