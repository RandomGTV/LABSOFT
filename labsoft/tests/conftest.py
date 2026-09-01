"""Shared test setup.

Qt needs a QGuiApplication in existence before it will lay out text or paint,
even when writing to a PDF with no window on screen. One instance is created
for the whole test session; Qt does not support creating a second.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session", autouse=True)
def qt_app():
    # QApplication, not QGuiApplication: it is the widget-aware subclass, and Qt
    # allows only one instance per process, so the widget tests would otherwise
    # inherit an instance that cannot hold a stylesheet or build a dialog.
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
