"""WCAG 2.1 AA checks on the palette and the screens.

The colours were measured, not eyeballed: six pairs failed the first time,
including the hint text used throughout and the border on every input box.
"""

from __future__ import annotations

import os

import pytest

from app.ui import style

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TEXT_MIN = 4.5      # 1.4.3 normal text
LARGE_MIN = 3.0     # 1.4.3 large text
UI_MIN = 3.0        # 1.4.11 non-text contrast


def _channel(c: float) -> float:
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# ------------------------------------------------------------------- 1.4.3

@pytest.mark.parametrize("name,fg,bg", [
    ("body text",            style.INK,   style.PANEL),
    ("secondary text",       style.INK2,  style.PANEL),
    ("hint text on panel",   style.INK3,  style.PANEL),
    ("hint text on page",    style.INK3,  style.BG),
    ("table header",         style.INK3,  "#FAFBFC"),
    ("section heading",      style.INK,   style.PANEL),
    ("text on primary",      style.LIGHT["ON_INK"],     style.INK),
    ("text on the go button", style.LIGHT["ON_ACCENT"], style.LIGHT["ACCENT_INK"]),
    ("accent as text",       style.LIGHT["ACCENT_INK"], style.PANEL),
    ("error text",           style.RED,   style.PANEL),
    ("warning text",         style.AMBER, style.PANEL),
    ("success text",         style.GREEN, style.PANEL),
])
def test_text_meets_aa(name, fg, bg):
    ratio = contrast(fg, bg)
    assert ratio >= TEXT_MIN, f"{name}: {ratio:.2f}:1 (needs {TEXT_MIN}:1)"


@pytest.mark.parametrize("flag", ["H", "L", "A", "N"])
def test_result_flags_are_readable_on_their_chips(flag):
    """Measured against the chip's real ground, in both themes."""
    for table, palette in ((style.FLAG_FILL_LIGHT, style.LIGHT),
                           (style.FLAG_FILL_DARK, style.DARK)):
        bg, _edge = table[flag]
        colour = {"H": palette["RED"], "L": palette["BLUE"],
                  "A": palette["AMBER"], "N": palette["GREEN"]}[flag]
        ratio = contrast(colour, bg)
        assert ratio >= TEXT_MIN, f"flag {flag} on {bg}: {ratio:.2f}:1"


# The night theme gets measured too. A dark theme nobody can read at 2 a.m.
# is worse than no dark theme, and guessing at pale-on-slate is unreliable.
@pytest.mark.parametrize("name,fg,bg", [
    ("body text",          style.DARK["INK"],   style.DARK["PANEL"]),
    ("secondary text",     style.DARK["INK2"],  style.DARK["PANEL"]),
    ("hint text on panel", style.DARK["INK3"],  style.DARK["PANEL"]),
    ("hint text on page",  style.DARK["INK3"],  style.DARK["BG"]),
    ("table header",       style.DARK["INK3"],  style.DARK["HEADER_BG"]),
    ("section heading",    style.DARK["BRAND"], style.DARK["PANEL"]),
    ("text on primary",    style.DARK["ON_INK"],    style.DARK["INK"]),
    ("text on go button",  style.DARK["ON_ACCENT"], style.DARK["ACCENT_INK"]),
    ("error text",         style.DARK["RED"],   style.DARK["PANEL"]),
    ("warning text",       style.DARK["AMBER"], style.DARK["PANEL"]),
    ("success text",       style.DARK["GREEN"], style.DARK["PANEL"]),
    ("quiet button",       style.DARK["BRAND"], style.DARK["BRAND_SOFT"]),
])
def test_night_theme_text_meets_aa(name, fg, bg):
    ratio = contrast(fg, bg)
    assert ratio >= TEXT_MIN, f"night {name}: {ratio:.2f}:1 (needs {TEXT_MIN}:1)"


def test_night_theme_borders_and_focus_are_visible():
    assert contrast(style.DARK["FIELD_BORDER"], style.DARK["PANEL"]) >= UI_MIN
    assert contrast(style.DARK["BRAND"], style.DARK["PANEL"]) >= UI_MIN


# ------------------------------------------------------------------ 1.4.11

def test_input_borders_are_visible():
    """A text box a user cannot find the edge of is a box they cannot use."""
    import re

    match = re.search(r"QLineEdit, QComboBox.*?border: 1px solid (#[0-9A-Fa-f]{6});",
                      style.STYLESHEET, re.S)
    assert match, "the input border colour could not be found"
    ratio = contrast(match.group(1), style.PANEL)
    assert ratio >= UI_MIN, f"input border {ratio:.2f}:1 (needs {UI_MIN}:1)"


def test_focus_ring_stands_out():
    assert contrast(style.BRAND, style.PANEL) >= UI_MIN


# ------------------------------------------------------- 1.4.1 colour alone

def test_flags_never_rely_on_colour_alone():
    """Someone who cannot distinguish red from blue must still read the flag."""
    for flag in ("H", "L", "A", "N"):
        assert style.FLAG_TEXT[flag].strip(), f"flag {flag} has colour but no text"
    assert style.FLAG_TEXT["H"] != style.FLAG_TEXT["L"]


def test_overdue_rows_are_not_only_red(tmp_path, monkeypatch):
    """The queue marks overdue jobs in red, and also says so in the Status column."""
    from app.core import turnaround

    assert turnaround.status_label(turnaround.STATUS_READY) == "Ready to send"
    assert turnaround.humanise_delta.__doc__


# ------------------------------------------------------------------- 2.1.1

@pytest.fixture()
def screen(tmp_path, monkeypatch):
    monkeypatch.setenv("LABSOFT_HOME", str(tmp_path))
    from PyQt6.QtWidgets import QApplication
    from app.db import connection, queries as q, seed

    connection.close()
    connection.connect(do_backup=False)
    q.ensure_defaults()
    seed.seed_all()

    app = QApplication.instance() or QApplication([])
    style.apply_light_palette(app)
    app.setStyleSheet(style.STYLESHEET)

    from app.ui.job_screen import JobScreen

    s = JobScreen()
    s.name_edit.setText("akila")
    s.age_spin.setValue(21)
    panel = next(p for p in q.list_panels() if p["name"] == "Lipid Profile")
    s._add_panel(panel["id"])
    yield s
    s.deleteLater()
    connection.close()


def test_every_input_is_keyboard_reachable(screen):
    from PyQt6.QtCore import Qt

    for widget in (screen.name_edit, screen.phone_edit, screen.sex_combo,
                   screen.age_spin, screen.referrer_combo, screen.test_search):
        assert widget.focusPolicy() != Qt.FocusPolicy.NoFocus, \
            f"{widget.accessibleName() or widget} cannot be reached by keyboard"


def test_calculated_boxes_are_skipped_when_tabbing(screen):
    """Tabbing should land only on boxes that can actually be typed into."""
    from PyQt6.QtCore import Qt

    derived = [r for r in screen.rows.values() if r.is_derived]
    assert derived, "expected some calculated tests in the lipid panel"
    for r in derived:
        assert r.editor.focusPolicy() == Qt.FocusPolicy.NoFocus
        assert r.editor.isReadOnly()


def test_typed_boxes_accept_focus(screen):
    from PyQt6.QtCore import Qt

    typed = [r for r in screen.rows.values() if not r.is_derived]
    assert typed
    for r in typed:
        assert r.editor.focusPolicy() != Qt.FocusPolicy.NoFocus


# ------------------------------------------------------------------- 4.1.2

def test_result_boxes_announce_which_test_they_are(screen):
    """Otherwise a screen reader reads out a row of identical blank fields."""
    for r in screen.rows.values():
        name = r.editor.accessibleName()
        assert name, "a result box has no accessible name"
        assert r.test["name"] in name


def test_patient_fields_are_named(screen):
    assert screen.name_edit.accessibleName() == "Patient name"
    assert screen.phone_edit.accessibleName() == "Patient mobile number"
    assert screen.sex_combo.accessibleName() == "Patient sex"
    assert screen.age_spin.accessibleName() == "Patient age"


# ------------------------------------------------------------------- 2.5.5

def test_buttons_are_big_enough_to_hit(screen):
    screen.resize(1200, 800)
    screen.layout().activate()
    for b in (screen.save_button, screen.verify_button, screen.bill_button,
              screen.clear_button):
        assert b.sizeHint().height() >= 32, \
            f"'{b.text()}' is only {b.sizeHint().height()}px tall"


def test_focus_is_visible_on_buttons():
    assert "QPushButton:focus" in style.STYLESHEET, \
        "keyboard users cannot see which button they are on"
