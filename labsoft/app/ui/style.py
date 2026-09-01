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
    "INK": "#201e1d",
    "INK2": "#444141",
    "INK3": "#605d5d",
    "LINE": "#d7d3d3",
    "LINE2": "#eae7e7",
    "BG": "#f3f2f2",
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
    "FILL": "#eae7e7",          # a filled surface that is not a card
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
    """The whole application sheet, built from one theme's tokens.

    Modernist rules, applied without exception:
      * radius 0 -- nothing is rounded
      * 2px rules separate sections, 1px lines bound controls
      * the accent appears on the live tab, the focus ring, and the one button
        on a screen that finishes the job. Nowhere else.
    """
    c = THEMES[normalise_theme(name)]
    dark = normalise_theme(name) == "dark"

    BRAND = c["BRAND"]
    BRAND_DARK = c["BRAND_DARK"]
    BRAND_SOFT = c["BRAND_SOFT"]
    RED = c["RED"]
    GREEN = c["GREEN"]
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
    ACCENT_INK = c["ACCENT_INK"]
    FONT = FONT_STACK

    return f"""
QWidget {{
    font-family: {FONT};
    font-size: 10.5pt;
    color: {INK};
}}
QMainWindow, QDialog {{ background: {BG}; }}

/* Scroll areas: the viewport is a separate widget and inherits the system
   theme unless it is named here. This is what made the results panel black. */
QScrollArea {{ background: {PANEL}; border: 0; }}
QScrollArea > QWidget > QWidget {{ background: {PANEL}; }}
QAbstractScrollArea {{ background: {PANEL}; }}
QAbstractScrollArea::viewport {{ background: {PANEL}; }}
#resultsHost, #resultsScroll {{ background: {PANEL}; }}

/* Dropdown popups are top-level windows and miss the parent's styling. */
QComboBox QAbstractItemView {{
    background: {PANEL};
    color: {INK};
    border: 1px solid {INK};
    selection-background-color: {FILL};
    selection-color: {INK};
    outline: 0;
}}
QListWidget, QListView, QTreeView {{
    background: {PANEL};
    color: {INK};
    border: 1px solid {LINE};
    border-radius: 0;
}}
QListWidget::item {{ padding: 7px 9px; }}
QListWidget::item:selected {{ background: {FILL}; color: {INK}; }}
QListWidget::item:hover {{ background: {LINE2}; }}
QMenu {{ background: {PANEL}; color: {INK}; border: 1px solid {INK}; }}
QMenu::item {{ padding: 7px 16px; }}
QMenu::item:selected {{ background: {FILL}; }}

/* Tabs: a 2px rule runs the width of the bar, and the live tab is the one
   carrying the accent. */
QTabWidget::pane {{
    border: 0;
    border-top: 2px solid {RULE};
    background: {PANEL};
    border-radius: 0;
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    padding: 9px 18px 8px 18px;
    margin: 0 2px 0 0;
    border: 0;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: {INK3};
    font-weight: 500;
}}
QTabBar::tab:selected {{
    background: {PANEL};
    border-bottom: 2px solid {BRAND};
    color: {INK};
    font-weight: 700;
}}
QTabBar::tab:hover:!selected {{ color: {INK}; }}
/* Focus underlines the label rather than recolouring it: the accent already
   means "this is the live tab", and two reds side by side said nothing. */
QTabBar::tab:focus {{ text-decoration: underline; }}

/* Buttons. Square, 1px edge, no gradient. The plain button is the common
   case; primary is ink; "go" is the accent and there is one per screen. */
QPushButton {{
    background: {PANEL};
    border: 1px solid {LINE if not dark else "#3C464E"};
    border-radius: 0;
    padding: 8px 15px;
    font-weight: 600;
    min-height: 24px;
}}
QPushButton:hover {{ background: {LINE2}; border-color: {INK3}; }}
QPushButton:pressed {{ background: {LINE}; }}
QPushButton:disabled {{
    color: {c["PRIMARY_OFF_TEXT"]}; background: {LINE2}; border-color: {LINE};
}}
/* Keyboard focus must be visible on buttons too, not only in text boxes —
   otherwise tabbing through the screen leaves no trace of where you are. */
QPushButton:focus {{
    border: 2px solid {BRAND};
    padding: 7px 14px;
}}
QCheckBox:focus, QRadioButton:focus {{ color: {BRAND}; }}
QCheckBox::indicator {{
    width: 17px; height: 17px; border-radius: 0;
    border: 1px solid {c["FIELD_BORDER"]}; background: {PANEL};
}}
QCheckBox::indicator:checked {{ background: {INK}; border-color: {INK}; }}
QCheckBox::indicator:focus {{ border: 2px solid {BRAND}; }}
/* Toggle buttons (the work-queue filters) must show which one is active. */
QPushButton:checked {{
    background: {INK};
    border-color: {INK};
    color: {ON_INK};
}}
QPushButton:checked:hover {{ background: {INK2}; border-color: {INK2}; }}
QPushButton[kind="primary"] {{
    background: {INK}; border-color: {INK}; color: {ON_INK};
}}
QPushButton[kind="primary"]:hover {{ background: {INK2}; border-color: {INK2}; }}
QPushButton[kind="primary"]:disabled {{
    background: {c["PRIMARY_OFF"]}; border-color: {c["PRIMARY_OFF"]};
    color: {c["PRIMARY_OFF_TEXT"]};
}}
QPushButton[kind="go"] {{
    background: {ACCENT_INK}; border-color: {ACCENT_INK}; color: {ON_ACCENT};
    font-weight: 800;
}}
QPushButton[kind="go"]:hover {{
    background: {BRAND_DARK}; border-color: {BRAND_DARK};
}}
QPushButton[kind="go"]:disabled {{
    background: {c["GO_OFF"]}; border-color: {c["GO_OFF"]};
    color: {c["GO_OFF_TEXT"]};
}}
/* Quiet buttons are secondary actions, so they are ink with an underline --
   if every link on the screen were accent, the accent would stop meaning
   "this is the one". */
QPushButton[kind="quiet"] {{
    background: transparent; border-color: transparent; color: {INK2};
    padding: 6px 8px; text-decoration: underline;
}}
QPushButton[kind="quiet"]:hover {{ color: {ACCENT_INK}; background: transparent; }}
/* The panel buttons: a chosen panel is filled ink, an unchosen one is paper
   with a hairline. No colour needed to tell them apart. */
QPushButton[kind="panel"] {{
    background: {PANEL};
    border: 1px solid {LINE if not dark else "#3C464E"};
    color: {INK};
    padding: 10px 14px;
    font-weight: 600;
    font-size: 10.5pt;
}}
QPushButton[kind="panel"]:hover {{ background: {FILL}; border-color: {INK3}; }}
QPushButton[kind="danger"] {{ color: {RED}; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QPlainTextEdit, QTextEdit {{
    background: {PANEL};
    border: 1px solid {c["FIELD_BORDER"]};
    border-radius: 0;
    padding: 6px 9px;
    selection-background-color: {BRAND};
    selection-color: {ON_ACCENT};
}}
QLineEdit:hover, QComboBox:hover {{ border-color: {INK2}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QDateEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 2px solid {BRAND};
    padding: 5px 8px;
}}
/* The result boxes carry the number that matters, so they are given the
   weight to match: bigger type in a taller box. */
QLineEdit[kind="result_entry"] {{
    font-size: 13pt;
    font-weight: 700;
    padding: 6px 9px;
    min-height: 28px;
}}
QLineEdit:read-only {{
    background: {c["READONLY_BG"]}; color: {INK2}; border-style: dashed;
}}
QLineEdit:disabled {{ background: {LINE2}; color: {INK3}; }}
QComboBox::drop-down {{ border: 0; width: 22px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {INK2};
    width: 0; height: 0; margin-right: 8px;
}}

/* Spin boxes: Fusion draws tiny unreadable arrows at this size, so the
   buttons are given real width and a drawn triangle. */
QSpinBox, QDoubleSpinBox {{ padding-right: 20px; }}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    width: 18px;
    border: 0;
    background: {LINE2};
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-position: top right;
    border-bottom: 1px solid {LINE};
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-position: bottom right;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {LINE};
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {INK2};
    width: 0; height: 0;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {INK2};
    width: 0; height: 0;
}}

/* Tables: a 2px rule under the head, hairlines between rows, no outer box. */
QTableWidget, QTableView {{
    background: {PANEL};
    border: 0;
    border-radius: 0;
    gridline-color: {LINE2};
    selection-background-color: {FILL};
    selection-color: {INK};
}}
QHeaderView::section {{
    background: {PANEL};
    border: 0;
    border-bottom: 2px solid {RULE};
    border-right: 0;
    padding: 8px 10px;
    font-size: 8.5pt;
    font-weight: 700;
    color: {INK3};
    text-transform: uppercase;
}}
QTableView::item {{ padding: 6px 8px; border-bottom: 1px solid {LINE2}; }}

/* Group boxes are sections, not cards: a 2px rule along the top with the
   name sitting on it, and no border round the rest. */
QGroupBox {{
    border: 0;
    border-top: 2px solid {RULE};
    border-radius: 0;
    margin-top: 15px;
    padding-top: 4px;
    background: {PANEL};
    font-weight: 700;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 0px;
    padding: 0 8px 0 0;
    color: {INK};
    background: {PANEL};
    font-size: 8.5pt;
    font-weight: 800;
    text-transform: uppercase;
}}

/* ── The Job screen's bands ────────────────────────────────────────────
   Four surfaces of falling weight: an ink money band, a white status rail
   and result field, and a quiet counsel column on the page ground. Named
   here rather than styled inline so that switching theme restyles them. */
#statusRail {{ background: {PANEL}; border-bottom: 2px solid {RULE}; }}
/* The left column is filled, so the screen reads as three surfaces: what you
   put in (left), what you are working on (the white field), and what the
   program has to say (the counsel column). The fill runs up through the
   status rail so the column is one panel from the top of the window down. */
#railLeft   {{ background: {BG}; border-right: 2px solid {RULE}; }}
#leftRail   {{ background: {BG}; border-right: 2px solid {RULE}; }}
#patientBlock {{ background: transparent; border-bottom: 1px solid {LINE}; }}
#testsBlock {{ background: transparent; }}
/* Fields stay paper-white against it, so a box still looks like a box. */
#leftRail QLineEdit, #leftRail QComboBox, #leftRail QSpinBox {{
    background: {PANEL};
}}
#moneyBand  {{ background: {INK}; }}
#moneyBand QLabel {{ color: {ON_INK}; }}
#resultsField {{ background: {PANEL}; border-right: 1px solid {LINE}; }}
#resultsHead {{ background: {PANEL}; border-bottom: 2px solid {RULE}; }}
#footBar    {{ background: {BG}; border-top: 2px solid {RULE}; }}
#counsel    {{ background: {BG}; border-left: 1px solid {LINE}; }}
#counselBlock {{ border-bottom: 1px solid {LINE}; }}
#groupRow   {{ background: {FILL}; }}

QLabel[role="micro"] {{
    color: {INK3}; font-size: 7.5pt; font-weight: 700; text-transform: uppercase;
}}
QLabel[role="stat"] {{ font-size: 12.5pt; font-weight: 700; }}
QLabel[role="money"] {{ font-size: 25pt; font-weight: 800; }}
QLabel[role="railvalue"] {{ font-size: 12.5pt; font-weight: 800; }}
QLabel[role="railname"] {{ font-size: 11pt; font-weight: 700; }}
QLabel[role="group"] {{
    font-size: 8pt; font-weight: 800; text-transform: uppercase; color: {INK};
}}
QLabel[role="method"] {{ color: {INK3}; font-size: 8pt; }}

/* Buttons living on the ink money band. */
#moneyBand QPushButton {{
    background: transparent; border: 1px solid {c["SCROLL"] if not dark else "#5A6670"};
    color: {ON_INK}; font-weight: 700; padding: 7px 14px;
}}
#moneyBand QPushButton:hover {{ background: {INK2}; }}
#moneyBand QPushButton[kind="primary"] {{
    background: {ON_INK}; border-color: {ON_INK}; color: {INK};
}}
#moneyBand QPushButton[kind="primary"]:hover {{ background: {LINE}; }}

QLabel[role="h1"] {{ font-size: 15pt; font-weight: 800; letter-spacing: -0.3px; }}
QLabel[role="hint"] {{ color: {INK3}; font-size: 9pt; }}
QLabel[role="field"] {{
    color: {INK3}; font-size: 8pt; font-weight: 700; text-transform: uppercase;
}}
QLabel[role="error"] {{ color: {RED}; font-weight: 700; }}
QLabel[role="ok"] {{ color: {GREEN}; font-weight: 700; }}

QStatusBar {{
    background: {PANEL}; border-top: 2px solid {RULE}; color: {INK3};
}}
QStatusBar QLabel {{ padding: 0 10px; font-size: 9pt; }}
QStatusBar::item {{ border: 0; }}

QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: {c["SCROLL"]}; border-radius: 0; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {c["SCROLL_HOVER"]}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; }}
QScrollBar::handle:horizontal {{
    background: {c["SCROLL"]}; border-radius: 0; min-width: 30px;
}}

QToolTip {{
    background: {c["TIP_BG"]}; color: {c["TIP_TEXT"]}; border: 0;
    padding: 6px 9px; border-radius: 0;
}}
QProgressBar {{
    border: 0; background: {c["TRACK"]}; border-radius: 0; height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{ background: {INK}; border-radius: 0; }}
"""


#: Kept for callers (and tests) that want the daylight sheet without asking.
STYLESHEET = stylesheet_for("light")
