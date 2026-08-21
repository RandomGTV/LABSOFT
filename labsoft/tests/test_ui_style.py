"""Guards for the visual faults found on the lab's PC.

Windows dark mode was showing through wherever the stylesheet did not name a
background, so the results panel rendered black with dark grey text on it.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("LABSOFT_HOME", str(tmp_path))
    from app.db import connection

    connection.close()
    connection.connect(do_backup=False)
    from app.db import queries as q, seed

    q.ensure_defaults()
    seed.seed_all()
    yield q
    connection.close()


@pytest.fixture()
def dark_app(env):
    """An application started under a dark system theme, as on the lab's PC."""
    from PyQt6.QtGui import QColor, QPalette
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])

    dark = QPalette()
    for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Base,
                 QPalette.ColorRole.Button, QPalette.ColorRole.AlternateBase):
        dark.setColor(role, QColor("#101114"))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                 QPalette.ColorRole.ButtonText):
        dark.setColor(role, QColor("#E6E6E6"))
    app.setPalette(dark)

    from app.ui import style

    style.apply_light_palette(app)
    app.setStyleSheet(style.STYLESHEET)
    yield app


def _luminance(colour) -> float:
    return (0.299 * colour.red() + 0.587 * colour.green() + 0.114 * colour.blue()) / 255


# ------------------------------------------------------------------ palette

def test_light_palette_overrides_a_dark_system_theme(dark_app):
    from PyQt6.QtGui import QPalette

    p = dark_app.palette()
    for role in (QPalette.ColorRole.Base, QPalette.ColorRole.Window,
                 QPalette.ColorRole.Button):
        assert _luminance(p.color(role)) > 0.85, f"{role} is still dark"
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText,
                 QPalette.ColorRole.ButtonText):
        assert _luminance(p.color(role)) < 0.3, f"{role} is not dark enough to read"


def test_text_and_background_actually_contrast(dark_app):
    from PyQt6.QtGui import QPalette

    p = dark_app.palette()
    gap = abs(_luminance(p.color(QPalette.ColorRole.Base))
              - _luminance(p.color(QPalette.ColorRole.Text)))
    assert gap > 0.6, "results panel text would be hard to read"


# --------------------------------------------------------------- stylesheet

@pytest.mark.parametrize("rule", [
    "QScrollArea",
    "QAbstractScrollArea::viewport",
    "QComboBox QAbstractItemView",
    "QListWidget",
    "QPushButton:checked",
])
def test_stylesheet_covers_the_widgets_that_leaked(rule):
    from app.ui import style

    assert rule in style.STYLESHEET, f"{rule} has no background and will inherit the OS theme"


# ------------------------------------------------------------- the grid itself

def test_results_panel_is_light_under_dark_mode(dark_app, env):
    from app.ui.job_screen import JobScreen

    screen = JobScreen()
    screen.name_edit.setText("akila")
    screen.age_spin.setValue(21)
    panel = next(p for p in env.list_panels() if p["name"] == "Lipid Profile")
    screen._add_panel(panel["id"])
    screen.show()

    bg = screen.grid_host.palette().color(screen.grid_host.backgroundRole())
    assert _luminance(bg) > 0.85, "the results panel is dark again"

    for rr in screen.rows.values():
        assert "color:" in rr.name_label.styleSheet(), \
            "test names must state their colour, not inherit it"
    screen.deleteLater()


def test_rebuilding_the_grid_leaves_no_ghost_widgets(dark_app, env):
    """Old rows were staying on screen and drawing over the new ones."""
    from app.ui.job_screen import JobScreen

    screen = JobScreen()
    screen.name_edit.setText("akila")
    screen.age_spin.setValue(21)

    lipid = next(p for p in env.list_panels() if p["name"] == "Lipid Profile")
    screen._add_panel(lipid["id"])
    first = set(screen.rows)

    screen._rebuild_grid()
    screen._rebuild_grid()

    live = [w for w in screen.grid_host.children()
            if w.isWidgetType() and w.parent() is screen.grid_host]
    assert len(live) == screen.grid.count(), \
        "widgets from an earlier rebuild are still parented and visible"
    assert set(screen.rows) != set() and len(screen.rows) == len(first)
    screen.deleteLater()


def test_ampersand_in_a_panel_name_is_not_eaten(dark_app, env):
    """Qt treats a single & as a shortcut marker: 'F & PP' printed as 'F _PP'."""
    from PyQt6.QtWidgets import QPushButton
    from app.ui.job_screen import JobScreen

    screen = JobScreen()
    labels = [screen.panel_layout.itemAt(i).widget().text()
              for i in range(screen.panel_layout.count())
              if isinstance(screen.panel_layout.itemAt(i).widget(), QPushButton)]

    match = [t for t in labels if "Blood Sugar" in t]
    assert match, "the Blood Sugar panel button is missing"
    assert "&&" in match[0], "a single & would be swallowed by Qt"
    screen.deleteLater()


def test_progress_count_is_readable_outside_the_bar(dark_app, env):
    """Text drawn inside a filled progress bar is unreadable at 100%."""
    from app.ui.job_screen import JobScreen

    screen = JobScreen()
    screen.name_edit.setText("akila")
    screen.age_spin.setValue(21)
    panel = next(p for p in env.list_panels() if p["name"] == "Blood Sugar F & PP")
    screen._add_panel(panel["id"])

    assert not screen.progress.isTextVisible()
    assert "of" in screen.progress_label.text()
    screen.deleteLater()


def test_long_test_names_do_not_collide_with_the_result_box(dark_app, env):
    from app.ui.job_screen import JobScreen

    screen = JobScreen()
    screen.name_edit.setText("akila")
    screen.age_spin.setValue(21)
    panel = next(p for p in env.list_panels() if p["name"] == "Lipid Profile")
    screen._add_panel(panel["id"])
    screen.resize(1200, 800)
    # Force the layout to compute geometry directly. processEvents() would also
    # flush every deleteLater() queued by earlier tests, which tears down widgets
    # this one is still holding.
    screen.grid_host.adjustSize()
    screen.grid.activate()

    for rr in screen.rows.values():
        name_right = rr.name_label.geometry().right()
        editor_left = rr.editor.geometry().left()
        assert name_right <= editor_left, \
            f"'{rr.test['name']}' overlaps its result box"
    screen.deleteLater()
