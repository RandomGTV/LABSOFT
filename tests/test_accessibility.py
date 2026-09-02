"""What an assistive tool, or an operator with poor sight, actually meets.

The lab PC runs Windows, where the screen reader is NVDA or Narrator. Qt
tells both of those a control's ``accessibleName``; with none set, a text box
announces itself as "edit" and nothing else. Tabbing the Job screen used to
be "edit, edit, combo box, spin box" for the patient's name, initial, sex and
age. These tests hold that shut.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _contrast(a: str, b: str) -> float:
    def lum(h: str) -> float:
        h = h.lstrip("#")
        c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
             for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.fixture()
def window(tmp_path, monkeypatch):
    monkeypatch.setenv("LABSOFT_HOME", str(tmp_path))
    from PyQt6.QtWidgets import QApplication
    from app.core import auth
    from app.db import connection, queries as q, seed
    from app.ui import style

    auth.set_current(None)
    connection.close()
    connection.connect(do_backup=False)
    q.ensure_defaults()
    seed.seed_all()
    app = QApplication.instance()
    style.apply_theme(app, "light")
    q.create_user("saheed", "Saheed Mohamed", "4821", auth.ROLE_ADMIN,
                  auth.ALL_PERMISSIONS)
    auth.set_current(q.sign_in("saheed", "4821"))

    from app.ui.main_window import MainWindow

    win = MainWindow()
    win.resize(1440, 900)
    win.show()
    app.processEvents()
    yield win, app
    win.close()
    win.deleteLater()
    auth.set_current(None)
    connection.close()


def _inputs(page):
    from PyQt6.QtWidgets import (
        QAbstractSpinBox, QComboBox, QLineEdit, QPlainTextEdit, QTextEdit,
    )

    kinds = (QLineEdit, QComboBox, QPlainTextEdit, QTextEdit, QAbstractSpinBox)
    out = []
    for cls in kinds:
        for w in page.findChildren(cls):
            # The QLineEdit Qt puts *inside* a date field or an editable combo
            # is not a control of its own; the container carries the name.
            if not w.isVisible() or isinstance(w.parent(), kinds):
                continue
            out.append(w)
    return out


# ===========================================================================
# 4.1.2 Name, role, value  /  3.3.2 Labels or instructions
# ===========================================================================

def test_every_field_on_every_screen_says_what_it_is(window):
    win, app = window
    deck = win.tabs
    nameless = []
    for i in range(deck.count()):
        deck.setCurrentIndex(i)
        app.processEvents()
        page = deck.widget(i)
        if hasattr(page, "refresh"):
            try:
                page.refresh()
            except Exception:
                pass
        app.processEvents()
        for w in _inputs(page):
            if not w.accessibleName().strip():
                nameless.append(f"{deck.tabText(i)}: {type(w).__name__} "
                                f"{w.objectName() or '(unnamed)'}")
    assert nameless == [], (
        f"{len(nameless)} fields announce themselves as nothing but their "
        f"type:\n  " + "\n  ".join(nameless[:20]))


def test_a_field_takes_the_caption_printed_beside_it(window):
    """Not just *a* name -- the one the operator can see on the screen.

    Settings is where this matters most: thirty text boxes down a scrolling
    page, none of which had a name, and all of which say what they are in a
    caption a sighted operator can read and a screen reader could not.
    """
    win, app = window
    win.tabs.setCurrentWidget(win.settings_screen)
    app.processEvents()
    names = {w.accessibleName() for w in _inputs(win.settings_screen)}
    for expected in ("Laboratory name", "Address line 1", "Phone line"):
        assert expected in names, f"no field is called {expected!r}"


def test_a_name_written_by_hand_is_never_overwritten(window):
    """The Job screen names its own fields better than a caption would."""
    win, _app = window
    names = {w.accessibleName() for w in _inputs(win.job_screen)}
    for expected in ("Patient name", "Patient mobile number", "Patient sex"):
        assert expected in names, f"{expected!r} was replaced: {sorted(names)}"


def test_naming_is_done_once_for_the_whole_window(window):
    """It is a sweep in MainWindow, not fifty calls that can be forgotten."""
    from app.ui.widgets import name_fields

    win, _app = window
    # Already named, so a second pass finds nothing left to do.
    assert name_fields(win.settings_screen) == 0


# ===========================================================================
# 2.5.8 Target size
# ===========================================================================

def test_a_checkbox_is_tall_enough_to_hit(window):
    from PyQt6.QtWidgets import QCheckBox

    win, app = window
    deck = win.tabs
    small = []
    for i in range(deck.count()):
        deck.setCurrentIndex(i)
        app.processEvents()
        for box in deck.widget(i).findChildren(QCheckBox):
            if box.isVisible() and box.height() < 24:
                small.append((deck.tabText(i), box.text()[:40], box.height()))
    assert small == [], f"under the 24px minimum: {small}"


# ===========================================================================
# 1.4.3 Contrast, and the things a ratio does not catch
# ===========================================================================

@pytest.mark.parametrize("theme", ["light", "dark"])
def test_a_disabled_button_can_still_be_read(theme):
    """"Check & make report" starts disabled and is the point of the screen.

    A disabled control is exempt from the contrast rule. It is not exempt
    from having to be legible: at 2.08:1 nobody could read what they were
    waiting for.
    """
    from app.ui import style

    c = style.THEMES[theme]
    for text, fill in ((c["PRIMARY_OFF_TEXT"], c["PRIMARY_OFF"]),
                       (c["GO_OFF_TEXT"], c["GO_OFF"])):
        assert _contrast(text, fill) >= 4.0, (
            f"{theme}: {text} on {fill} is {_contrast(text, fill):.2f}:1")


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_a_hairline_is_not_the_colour_of_what_it_divides(theme):
    """The night theme drew every rule in exactly the colour behind it.

    LINE2 and PANEL were both #1E293B, so the dark tables had no row
    separation at all -- a separator with a contrast ratio of 1.00:1.
    """
    from app.ui import style

    c = style.THEMES[theme]
    assert c["LINE2"].lower() != c["PANEL"].lower()
    assert _contrast(c["LINE2"], c["PANEL"]) >= 1.2, (
        f"{theme}: hairline {c['LINE2']} on panel {c['PANEL']} is "
        f"{_contrast(c['LINE2'], c['PANEL']):.2f}:1 -- invisible")


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_destructive_button_is_never_the_primary_colour(theme):
    """Sign out was BRAND, and BRAND is cyan at night -- the same cyan as
    Save settings and Open bill."""
    from app.ui import style

    c = style.THEMES[theme]
    assert c["ALERT"].lower() != c["ACCENT_INK"].lower()
    sheet = style.stylesheet_for(theme)
    danger = sheet.split('#appBar QPushButton[kind="danger"]')[1][:120]
    assert c["ALERT"] in danger, "Sign out no longer wears the alert colour"


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_a_checkbox_is_square_and_carries_a_tick(theme):
    """At 17px a radius of 8 is a circle, which means "one of these"."""
    from app.ui import style

    sheet = style.stylesheet_for(theme)
    box = sheet.split("QCheckBox::indicator {")[1].split("}")[0]
    assert "border-radius: 5px" in box, box
    ticked = sheet.split("QCheckBox::indicator:checked {")[1].split("}")[0]
    assert "image: url(" in ticked, "a ticked box has no tick in it"
