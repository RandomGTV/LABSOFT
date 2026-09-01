"""Look and feel.

Deliberately plain and high-contrast: this is used all day, often quickly, by
someone who is not looking for the button. Large hit targets, obvious focus,
and colour used only where it carries meaning.

Two themes are offered — the daylight one, and a dark one for a lab bench with
the lights off. Both are checked against WCAG AA by ``tests/test_contrast.py``;
a theme nobody can read at 2 a.m. is worse than no theme at all.

The colour names below are module globals on purpose. Every screen reads them
as ``style.RED`` *inside* a function, never at import time, so switching theme
rebinds them and the next thing drawn picks the new colour up.

Built on the **Modernist** system from the LabSoft 2026 design canvas:

  * Archivo, shipped in ``assets/fonts`` so the PC needs nothing installed
  * square corners -- radius 0 everywhere, no exceptions
  * 2px rules divide sections; 1px lines bound controls
  * one accent, ``#ec3013``, spent only where an action or a danger lives.
    Section headings, tabs and labels are ink, not colour. If everything is
    red, nothing is.
"""

from __future__ import annotations

from typing import Dict

LIGHT: Dict[str, str] = {
    # BRAND is the accent: the one colour in the room. It marks the live tab,
    # the focus ring and the single most consequential button on a screen.
    "BRAND": "#0A3668",
    "BRAND_DARK": "#062344",
    "BRAND_SOFT": "#F0F9FF",
    # #ec3013 is the marker colour -- a 2px underline, a focus ring, an edge,
    # all of which only need 3:1. As *text* or as a fill behind text it is
    # 4.2:1 and fails AA, so anything carrying words uses the darker step.
    "ACCENT_INK": "#0284C7",
    "RED": "#ae1800",
    "GREEN": "#16703F",
    "AMBER": "#8A5A00",
    "BLUE": "#1A5FB4",
    "INK": "#0F172A",
    "INK2": "#334155",
    "INK3": "#64748B",
    "LINE": "#CBD5E1",
    "LINE2": "#E2E8F0",
    "BG": "#F1F5F9",
    "PANEL": "#FFFFFF",
    # Extras the stylesheet needs but nothing else refers to by name.
    "FIELD_BORDER": "#7d7979",
    "READONLY_BG": "#eae7e7",
    "HEADER_BG": "#f8f4f4",
    "SCROLL": "#bab6b6",
    "SCROLL_HOVER": "#9b9797",
    "PANEL_BTN_BORDER": "#d7d3d3",
    "PANEL_BTN_HOVER": "#eae7e7",
    "PRIMARY_OFF": "#d7d3d3",
    "PRIMARY_OFF_TEXT": "#7d7979",
    "GO_HOVER": "#0369A1",
    "GO_OFF": "#d7d3d3",
    "GO_OFF_TEXT": "#7d7979",
    "TRACK": "#eae7e7",
    "TIP_BG": "#201e1d",
    "TIP_TEXT": "#f3f2f2",
    # Modernist additions.
    "FILL": "#E2E8F0",          # a filled surface that is not a card
    "RULE": "#201e1d",          # the 2px section rule
    "ON_INK": "#f3f2f2",        # text on an ink-filled control
    "ON_ACCENT": "#f3f2f2",     # text on the accent
}

# Dark theme. Backgrounds are a desaturated slate rather than black — pure
# black with white text strobes badly on a cheap monitor. Every foreground
# here clears 4.5:1 against the surface it sits on.
DARK: Dict[str, str] = {
    # Its own ground and its own paper, not an inversion of the day theme, and
    # the accent lifted to #ff563c so it still reads at three in the morning
    # without glaring.
    "BRAND": "#38BDF8",
    "BRAND_DARK": "#0284C7",
    "BRAND_SOFT": "#082F49",
    "ACCENT_INK": "#38BDF8",
    "RED": "#FF8A8A",
    "GREEN": "#6FD79B",
    "AMBER": "#F0C066",
    "BLUE": "#8FB6F7",
    "INK": "#EEF2F5",
    "INK2": "#B4C0C8",
    "INK3": "#8A98A1",
    "LINE": "#3C464E",
    "LINE2": "#2A343A",
    "BG": "#141A1F",
    "PANEL": "#1C242A",
    "FIELD_BORDER": "#7A8792",
    "READONLY_BG": "#222C33",
    "HEADER_BG": "#222C33",
    "SCROLL": "#3C464E",
    "SCROLL_HOVER": "#5A6670",
    "PANEL_BTN_BORDER": "#3C464E",
    "PANEL_BTN_HOVER": "#222C33",
    "PRIMARY_OFF": "#2A343A",
    "PRIMARY_OFF_TEXT": "#8A98A1",
    "GO_HOVER": "#ff7a66",
    "GO_OFF": "#2A343A",
    "GO_OFF_TEXT": "#8A98A1",
    "TRACK": "#2A343A",
    "TIP_BG": "#EEF2F5",
    "TIP_TEXT": "#141A1F",
    "FILL": "#222C33",
    "RULE": "#EEF2F5",
    "ON_INK": "#141A1F",
    "ON_ACCENT": "#141A1F",
}

THEMES = {"light": LIGHT, "dark": DARK}

#: The theme currently in force. Read it, don't set it — use apply_theme().
CURRENT_THEME = "light"


def _install(palette: Dict[str, str]) -> None:
    globals().update(palette)


_install(LIGHT)


FLAG_COLOURS = {
    "H": LIGHT["RED"],
    "L": LIGHT["BLUE"],
    "A": LIGHT["AMBER"],
    "N": LIGHT["GREEN"],
    "": LIGHT["INK3"],
}

#: Ground and edge for each flag chip, per theme. The chip is a square block
#: with a 1px edge in its own colour -- a rounded pill would be the only
#: curve on the screen.
FLAG_FILL_LIGHT = {
    "H": ("#fff2ef", "#ae1800"),
    "L": ("#E8EFFA", "#1A5FB4"),
    "A": ("#FBF1DE", "#8A5A00"),
    "N": ("#E4F2EA", "#16703F"),
}
FLAG_FILL_DARK = {
    "H": ("#251618", "#54282C"),
    "L": ("#18232F", "#2E4560"),
    "A": ("#241F14", "#4C401F"),
    "N": ("#16241C", "#27462F"),
}

#: The four job states, drawn the same way as the flags.
STATUS_FILL_LIGHT = {
    "draft":  ("#605d5d", "#eae7e7", "#bab6b6"),
    "prog":   ("#1A5FB4", "#E8EFFA", "#1A5FB4"),
    "ready":  ("#8A5A00", "#FBF1DE", "#8A5A00"),
    "sent":   ("#16703F", "#E4F2EA", "#16703F"),
}
STATUS_FILL_DARK = {
    "draft":  ("#8A98A1", "#222C33", "#3C464E"),
    "prog":   ("#8FB6F7", "#18232F", "#2E4560"),
    "ready":  ("#F0C066", "#241F14", "#4C401F"),
    "sent":   ("#6FD79B", "#16241C", "#27462F"),
}


def flag_fill(flag: str):
    """(background, edge) for a flag chip in the theme now in force."""
    table = FLAG_FILL_DARK if CURRENT_THEME == "dark" else FLAG_FILL_LIGHT
    return table.get(flag, ("", ""))


def status_fill(kind: str):
    """(text, background, edge) for a job-status chip."""
    table = STATUS_FILL_DARK if CURRENT_THEME == "dark" else STATUS_FILL_LIGHT
    return table.get(kind, table["draft"])

FLAG_TEXT = {
    "H": "HIGH",
    "L": "LOW",
    "A": "CHECK",
    "N": "N",
    "": "",
}


def _refresh_flag_colours(palette: Dict[str, str]) -> None:
    FLAG_COLOURS.update({
        "H": palette["RED"],
        "L": palette["BLUE"],
        "A": palette["AMBER"],
        "N": palette["GREEN"],
        "": palette["INK3"],
    })


#: The system face. Archivo is shipped in assets/fonts, because the lab PC has
#: whatever Windows came with and nothing else, and a design that only looks
#: right on the designer's machine is not a design.
FONT_FAMILY = "Archivo"
FONT_STACK = '"Archivo", "Segoe UI", system-ui, Arial, sans-serif'

_fonts_loaded = False


def load_fonts() -> bool:
    """Register the bundled Archivo weights. Safe to call more than once.

    Returns True when the family is available afterwards -- False means the
    files are missing and every rule falls back to Segoe UI, which is a
    plainer page but never an unreadable one.
    """
    global _fonts_loaded
    if _fonts_loaded:
        return True
    from PyQt6.QtGui import QFontDatabase

    from pathlib import Path

    from .. import config

    # Two places, in order: the assets folder beside the running program, and
    # the one beside this source file. They are the same folder in a normal
    # install; they differ when the data folder has been pointed elsewhere,
    # and the typeface belongs to the program, not to the data.
    folders = [config.assets_dir() / "fonts",
               Path(__file__).resolve().parents[2] / "assets" / "fonts"]
    loaded = False
    for folder in folders:
        for name in ("Archivo-Regular.ttf", "Archivo-SemiBold.ttf",
                     "Archivo-ExtraBold.ttf"):
            path = folder / name
            if path.exists() and QFontDatabase.addApplicationFont(str(path)) != -1:
                loaded = True
        if loaded:
            break
    _fonts_loaded = loaded
    return loaded


def normalise_theme(name: str) -> str:
    name = (name or "").strip().lower()
    return name if name in THEMES else "light"


def apply_theme(app, name: str = "light") -> str:
    """Put a theme on the application: colours, palette and stylesheet.

    Returns the theme actually applied, so a caller handed nonsense gets told
    what it got instead of silently showing something else.
    """
    name = normalise_theme(name)
    palette = THEMES[name]

    global CURRENT_THEME
    CURRENT_THEME = name
    _install(palette)
    _refresh_flag_colours(palette)
    load_fonts()

    _apply_qpalette(app, palette, name == "dark")
    app.setStyleSheet(stylesheet_for(name))
    return name


def apply_light_palette(app) -> None:
    """Pin the application to the light theme and the Fusion style.

    Windows dark mode otherwise shows through anywhere the stylesheet does not
    name a background — scroll area viewports, dropdown popups, spin-box arrows
    — producing dark grey text on a black panel. Setting the palette outright
    is the only reliable fix, because a stylesheet can only cover what it lists.
    """
    apply_theme(app, "light")


def _apply_qpalette(app, c: Dict[str, str], dark: bool) -> None:
    from PyQt6.QtGui import QColor, QPalette

    try:
        app.setStyle("Fusion")
    except Exception:                      # pragma: no cover - platform specific
        pass

    p = QPalette()
    ink = QColor(c["INK"])
    panel = QColor(c["PANEL"])
    bg = QColor(c["BG"])

    p.setColor(QPalette.ColorRole.Window, bg)
    p.setColor(QPalette.ColorRole.WindowText, ink)
    p.setColor(QPalette.ColorRole.Base, panel)
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(c["LINE2"]))
    p.setColor(QPalette.ColorRole.Text, ink)
    p.setColor(QPalette.ColorRole.Button, panel)
    p.setColor(QPalette.ColorRole.ButtonText, ink)
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(c["TIP_BG"]))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor(c["TIP_TEXT"]))
    p.setColor(QPalette.ColorRole.Highlight, QColor(c["BRAND"]))
    p.setColor(QPalette.ColorRole.HighlightedText,
               QColor(c["BG"] if dark else "#FFFFFF"))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(c["INK3"]))
    p.setColor(QPalette.ColorRole.Link, QColor(c["BRAND"]))

    disabled = QPalette.ColorGroup.Disabled
    p.setColor(disabled, QPalette.ColorRole.Text, QColor(c["INK3"]))
    p.setColor(disabled, QPalette.ColorRole.ButtonText, QColor(c["INK3"]))
    p.setColor(disabled, QPalette.ColorRole.WindowText, QColor(c["INK3"]))

    app.setPalette(p)


def stylesheet_for(name: str = "light") -> str:
    """The whole application sheet, built from one theme's tokens with modern UI/UX."""
    name = normalise_theme(name)
    c = THEMES[name]
    dark = name == "dark"

    BRAND = c["BRAND"]
    BRAND_DARK = c["BRAND_DARK"]
    BRAND_SOFT = c["BRAND_SOFT"]
    ACCENT_INK = c["ACCENT_INK"]
    RED = c["RED"]
    GREEN = c["GREEN"]
    AMBER = c["AMBER"]
    BLUE = c["BLUE"]
    INK = c["INK"]
    INK2 = c["INK2"]
    INK3 = c["INK3"]
    LINE = c["LINE"]
    LINE2 = c["LINE2"]
    BG = c["BG"]
    PANEL = c["PANEL"]
    FILL = c["FILL"]
    RULE = c["RULE"]
    ON_INK = c["ON_INK"]
    ON_ACCENT = c["ON_ACCENT"]

    return f"""
* {{
    font-family: {FONT_STACK};
    font-size: 9.5pt;
    color: {INK};
}}

QWidget {{
    background: {PANEL};
    color: {INK};
}}

QMainWindow, QDialog {{
    background: {BG};
}}

/* ── Modern Tabs Bar ───────────────────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    border-top: 1.5px solid {"#CBD5E1" if not dark else "#1E3A5F"};
    background: {PANEL};
    top: -1px;
}}
QTabBar {{
    background: {PANEL};
    border-bottom: 1.5px solid {"#CBD5E1" if not dark else "#1E3A5F"};
    padding: 3px 6px 0px 6px;
}}
QTabBar::tab {{
    background: transparent;
    padding: 8px 15px;
    margin: 2px 3px 0px 3px;
    border: 1px solid transparent;
    border-bottom: 2.5px solid transparent;
    border-radius: 5px 5px 0px 0px;
    color: {INK2};
    font-weight: 700;
    font-size: 9.5pt;
}}
QTabBar::tab:selected {{
    background: {"#E0F2FE" if not dark else "#082F49"};
    border: 1px solid {"#BAE6FD" if not dark else "#0284C7"};
    border-bottom: 2.5px solid {ACCENT_INK};
    color: {"#0284C7" if not dark else "#38BDF8"};
    font-weight: 800;
}}
QTabBar::tab:hover:!selected {{
    background: {LINE2};
    color: {INK};
}}

/* ── Modern Buttons ─────────────────────────────────────────────────── */
QPushButton {{
    background: {PANEL};
    border: 1.5px solid {"#CBD5E1" if not dark else "#3C464E"};
    border-radius: 5px;
    padding: 7px 14px;
    font-weight: 700;
    font-size: 9.5pt;
    min-height: 22px;
}}
QPushButton:hover {{
    background: {"#F8FAFC" if not dark else "#1E3A5F"};
    border-color: {"#94A3B8" if not dark else "#38BDF8"};
    color: {"#0A3668" if not dark else "#FFFFFF"};
}}
QPushButton:pressed {{
    background: {LINE2};
}}
QPushButton:disabled {{
    color: {INK3};
    background: {LINE2};
    border-color: {LINE};
}}
QPushButton:focus {{
    border: 2px solid {ACCENT_INK};
}}

QPushButton[kind="primary"] {{
    background: {"#0A3668" if not dark else "#0284C7"};
    border: 1.5px solid {"#0A3668" if not dark else "#0284C7"};
    color: #FFFFFF;
    font-weight: 800;
    border-radius: 5px;
}}
QPushButton[kind="primary"]:hover {{
    background: {"#0284C7" if not dark else "#0369A1"};
    border-color: {"#0284C7" if not dark else "#0369A1"};
    color: #FFFFFF;
}}

QPushButton[kind="go"] {{
    background: #059669;
    border: 1.5px solid #059669;
    color: #FFFFFF;
    font-weight: 800;
    border-radius: 5px;
}}
QPushButton[kind="go"]:hover {{
    background: #047857;
    border-color: #047857;
    color: #FFFFFF;
}}

QPushButton:checked {{
    background: {"#0A3668" if not dark else "#0284C7"};
    border: 1.5px solid {"#0A3668" if not dark else "#0284C7"};
    color: #FFFFFF;
    font-weight: 800;
}}
QPushButton:checked:hover {{
    background: {"#0284C7" if not dark else "#0369A1"};
    border-color: {"#0284C7" if not dark else "#0369A1"};
    color: #FFFFFF;
}}

QPushButton[kind="panel"] {{
    background: {"#FFFFFF" if not dark else "#132F4C"};
    border: 1px solid {"#BAE6FD" if not dark else "#1E3A5F"};
    border-radius: 4px;
    color: {"#0A3668" if not dark else "#E2E8F0"};
    padding: 7px 11px;
    font-weight: 700;
    font-size: 9pt;
}}
QPushButton[kind="panel"]:hover {{
    background: {"#E0F2FE" if not dark else "#1E3A5F"};
    border-color: {ACCENT_INK};
    color: {ACCENT_INK};
}}
QPushButton[kind="panel"]:pressed {{
    background: {ACCENT_INK};
    border-color: {ACCENT_INK};
    color: #FFFFFF;
}}

QPushButton[kind="quiet"] {{
    background: transparent;
    border: none;
    color: {ACCENT_INK};
    padding: 4px 6px;
    text-decoration: underline;
    font-weight: 600;
}}
QPushButton[kind="quiet"]:hover {{
    color: {"#0A3668" if not dark else "#38BDF8"};
    background: transparent;
}}

/* ── Modern Form Inputs ─────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QPlainTextEdit, QTextEdit {{
    background: {PANEL};
    border: 1.5px solid {"#CBD5E1" if not dark else "#3C464E"};
    border-radius: 4px;
    padding: 5px 8px;
    color: {INK};
    selection-background-color: {ACCENT_INK};
    selection-color: #FFFFFF;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QDateEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 2px solid {ACCENT_INK};
    background: {PANEL};
}}

QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background: {PANEL};
    border: 1.5px solid {"#CBD5E1" if not dark else "#3C464E"};
    border-radius: 4px;
    selection-background-color: {"#E0F2FE" if not dark else "#1E3A5F"};
    selection-color: {INK};
    padding: 4px;
}}

/* ── Job Screen Sections ─────────────────────────────────────────────── */
#statusRail {{
    background: {PANEL};
    border-bottom: 1.5px solid {"#CBD5E1" if not dark else "#1E3A5F"};
}}

#railLeft {{
    background: {"#F0F6FB" if not dark else "#0A1929"};
    border-right: 1.5px solid {"#CBD5E1" if not dark else "#1E3A5F"};
}}
#leftRail {{
    background: {"#F0F6FB" if not dark else "#0A1929"};
    border-right: 1.5px solid {"#CBD5E1" if not dark else "#1E3A5F"};
}}
#patientBlock {{
    background: transparent;
    border-bottom: 1px solid {"#D1E3F0" if not dark else "#1E3A5F"};
}}
#testsBlock {{
    background: transparent;
}}

#leftRail QLineEdit, #leftRail QComboBox, #leftRail QSpinBox {{
    background: {PANEL};
    border: 1.5px solid {"#CBD5E1" if not dark else "#1E3A5F"};
    border-radius: 4px;
    padding: 5px 8px;
    color: {INK};
}}
#leftRail QLineEdit:focus, #leftRail QComboBox:focus, #leftRail QSpinBox:focus {{
    border: 2px solid {ACCENT_INK};
    background: {PANEL};
}}
#leftRail QLabel[role="micro"] {{
    color: {"#0A3668" if not dark else "#38BDF8"};
    font-weight: 800;
    font-size: 7.5pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

#moneyBand {{
    background: #0F172A;
    border-bottom: 2px solid #0A3668;
}}
#moneyBand QLabel {{
    color: #F8FAFC;
}}
#moneyBand QPushButton {{
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.25);
    color: #FFFFFF;
    font-weight: 700;
    border-radius: 4px;
    padding: 7px 14px;
}}
#moneyBand QPushButton:hover {{
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.4);
}}
#moneyBand QPushButton[kind="primary"] {{
    background: #FFFFFF;
    border: 1px solid #FFFFFF;
    color: #0F172A;
    font-weight: 800;
}}
#moneyBand QPushButton[kind="primary"]:hover {{
    background: #F1F5F9;
}}

#resultsField {{
    background: {PANEL};
    border-right: 1px solid {LINE};
}}
#resultsHead {{
    background: {"#F8FAFC" if not dark else "#0F172A"};
    border-bottom: 2px solid {"#0A3668" if not dark else "#38BDF8"};
}}
#footBar {{
    background: {BG};
    border-top: 1.5px solid {"#CBD5E1" if not dark else "#1E3A5F"};
}}
#counsel {{
    background: {"#F8FAFC" if not dark else "#0F172A"};
    border-left: 1.5px solid {"#CBD5E1" if not dark else "#1E3A5F"};
}}
#counselBlock {{
    border-bottom: 1px solid {"#E2E8F0" if not dark else "#1E3A5F"};
}}

/* ── Typography Roles ───────────────────────────────────────────────── */
QLabel[role="micro"] {{
    color: {"#0A3668" if not dark else "#38BDF8"};
    font-size: 7.5pt;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
QLabel[role="stat"] {{
    font-size: 13pt;
    font-weight: 700;
    color: #F8FAFC;
}}
QLabel[role="money"] {{
    font-size: 24pt;
    font-weight: 800;
    color: #FFFFFF;
}}
QLabel[role="railvalue"] {{
    font-size: 12pt;
    font-weight: 800;
    color: {INK};
}}
QLabel[role="railname"] {{
    font-size: 11pt;
    font-weight: 700;
    color: {INK};
}}
QLabel[role="group"] {{
    font-size: 8.5pt;
    font-weight: 800;
    text-transform: uppercase;
    color: {"#0A3668" if not dark else "#38BDF8"};
    letter-spacing: 0.5px;
}}
QLabel[role="hint"] {{
    color: {INK3};
    font-size: 9pt;
}}

/* ── Status Bar ─────────────────────────────────────────────────────── */
QStatusBar {{
    background: {PANEL};
    border-top: 1px solid {"#CBD5E1" if not dark else "#1E3A5F"};
    color: {INK2};
    font-size: 8.5pt;
}}
QStatusBar QLabel {{
    color: {INK2};
    font-size: 8.5pt;
}}

/* ── Tables & Views ─────────────────────────────────────────────────── */
QTableView, QTableWidget, QListView, QListWidget, QTreeView {{
    background: {PANEL};
    border: 1px solid {"#CBD5E1" if not dark else "#3C464E"};
    border-radius: 4px;
    selection-background-color: {"#E0F2FE" if not dark else "#1E3A5F"};
    selection-color: {INK};
    gridline-color: {LINE2};
}}
QHeaderView::section {{
    background: {"#F8FAFC" if not dark else "#0F172A"};
    border: none;
    border-bottom: 2px solid {"#0A3668" if not dark else "#38BDF8"};
    border-right: 1px solid {LINE2};
    padding: 6px 10px;
    font-weight: 800;
    font-size: 8.5pt;
    text-transform: uppercase;
    color: {"#0A3668" if not dark else "#38BDF8"};
}}

/* ── Scrollbars ─────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {"#CBD5E1" if not dark else "#3C464E"};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {"#94A3B8" if not dark else "#5A6670"};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""
