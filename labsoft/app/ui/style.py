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
"""

from __future__ import annotations

from typing import Dict

LIGHT: Dict[str, str] = {
    "BRAND": "#0F5C73",
    "BRAND_DARK": "#0A4356",
    "BRAND_SOFT": "#E6F1F4",
    "RED": "#C1121F",
    "GREEN": "#16703F",
    "AMBER": "#8A5A00",
    "BLUE": "#1A5FB4",
    "INK": "#141719",
    "INK2": "#4A5157",
    "INK3": "#616A72",
    "LINE": "#C3CBD2",
    "LINE2": "#EDF0F3",
    "BG": "#F4F6F8",
    "PANEL": "#FFFFFF",
    # Extras the stylesheet needs but nothing else refers to by name.
    "FIELD_BORDER": "#88929B",
    "READONLY_BG": "#F2F5F7",
    "HEADER_BG": "#FAFBFC",
    "SCROLL": "#C7CFD6",
    "SCROLL_HOVER": "#A9B4BD",
    "PANEL_BTN_BORDER": "#C4DCE4",
    "PANEL_BTN_HOVER": "#D5E8EE",
    "PRIMARY_OFF": "#9FB6BE",
    "PRIMARY_OFF_TEXT": "#EEF3F5",
    "GO_HOVER": "#14603A",
    "GO_OFF": "#A8CBB8",
    "GO_OFF_TEXT": "#F0F6F2",
    "TRACK": "#E3E8EC",
    "TIP_BG": "#141719",
    "TIP_TEXT": "#FFFFFF",
}

# Dark theme. Backgrounds are a desaturated slate rather than black — pure
# black with white text strobes badly on a cheap monitor. Every foreground
# here clears 4.5:1 against the surface it sits on.
DARK: Dict[str, str] = {
    "BRAND": "#5FC6DE",
    "BRAND_DARK": "#8AD8EA",
    "BRAND_SOFT": "#204450",
    "RED": "#FF8A8A",
    "GREEN": "#6FD79B",
    "AMBER": "#F0C066",
    "BLUE": "#8AB6F5",
    "INK": "#EEF2F5",
    "INK2": "#C3CBD2",
    "INK3": "#A6B0B9",
    "LINE": "#3C464E",
    "LINE2": "#2A333A",
    "BG": "#141A1F",
    "PANEL": "#1C242A",
    "FIELD_BORDER": "#6C7880",
    "READONLY_BG": "#232C33",
    "HEADER_BG": "#222B32",
    "SCROLL": "#414C55",
    "SCROLL_HOVER": "#586570",
    "PANEL_BTN_BORDER": "#2F5A68",
    "PANEL_BTN_HOVER": "#27505E",
    "PRIMARY_OFF": "#3A505A",
    "PRIMARY_OFF_TEXT": "#96A6AE",
    "GO_HOVER": "#8BE3B1",
    "GO_OFF": "#33513F",
    "GO_OFF_TEXT": "#9BB3A4",
    "TRACK": "#2A333A",
    "TIP_BG": "#EEF2F5",
    "TIP_TEXT": "#141A1F",
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
    c = THEMES[normalise_theme(name)]
    dark = normalise_theme(name) == "dark"
    on_brand = c["BG"] if dark else "#FFFFFF"

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

    return f"""
QWidget {{
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 11pt;
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
    border: 1px solid {LINE};
    selection-background-color: {BRAND_SOFT};
    selection-color: {INK};
    outline: 0;
}}
QListWidget, QListView, QTreeView {{
    background: {PANEL};
    color: {INK};
    border: 1px solid {LINE};
    border-radius: 5px;
}}
QListWidget::item {{ padding: 6px 8px; }}
QListWidget::item:selected {{ background: {BRAND_SOFT}; color: {INK}; }}
QListWidget::item:hover {{ background: {LINE2}; }}
QMenu {{ background: {PANEL}; color: {INK}; border: 1px solid {LINE}; }}
QMenu::item:selected {{ background: {BRAND_SOFT}; }}

QTabWidget::pane {{
    border: 1px solid {LINE};
    background: {PANEL};
    border-radius: 6px;
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    padding: 9px 20px;
    margin-right: 2px;
    border: 1px solid transparent;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: {INK2};
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background: {PANEL};
    border-color: {LINE};
    border-bottom-color: {PANEL};
    color: {BRAND};
}}
QTabBar::tab:hover:!selected {{ background: {LINE2}; }}

QPushButton {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    min-height: 24px;
}}
QPushButton:hover {{ background: {LINE2}; }}
QPushButton:pressed {{ background: {LINE}; }}
QPushButton:disabled {{ color: {INK3}; background: {LINE2}; }}
/* Keyboard focus must be visible on buttons too, not only in text boxes —
   otherwise tabbing through the screen leaves no trace of where you are. */
QPushButton:focus {{
    border: 2px solid {BRAND};
    padding: 7px 15px;
}}
QCheckBox:focus, QRadioButton:focus {{ color: {BRAND}; }}
QCheckBox::indicator {{ width: 18px; height: 18px; }}
QTabBar::tab:focus {{ color: {BRAND}; text-decoration: underline; }}
/* Toggle buttons (the work-queue filters) must show which one is active. */
QPushButton:checked {{
    background: {BRAND};
    border-color: {BRAND};
    color: {on_brand};
}}
QPushButton:checked:hover {{ background: {BRAND_DARK}; }}
QPushButton[kind="primary"] {{
    background: {BRAND}; border-color: {BRAND}; color: {on_brand};
}}
QPushButton[kind="primary"]:hover {{ background: {BRAND_DARK}; }}
QPushButton[kind="primary"]:disabled {{
    background: {c["PRIMARY_OFF"]}; border-color: {c["PRIMARY_OFF"]};
    color: {c["PRIMARY_OFF_TEXT"]};
}}
QPushButton[kind="go"] {{
    background: {GREEN}; border-color: {GREEN}; color: {on_brand};
}}
QPushButton[kind="go"]:hover {{ background: {c["GO_HOVER"]}; }}
QPushButton[kind="go"]:disabled {{
    background: {c["GO_OFF"]}; border-color: {c["GO_OFF"]}; color: {c["GO_OFF_TEXT"]};
}}
QPushButton[kind="quiet"] {{
    background: transparent; border-color: transparent; color: {BRAND};
    padding: 6px 10px;
}}
QPushButton[kind="quiet"]:hover {{ background: {BRAND_SOFT}; }}
QPushButton[kind="panel"] {{
    background: {BRAND_SOFT};
    border: 1px solid {c["PANEL_BTN_BORDER"]};
    border-radius: 14px;
    color: {BRAND_DARK if not dark else INK};
    padding: 7px 14px;
    font-size: 10pt;
    font-weight: 600;
}}
QPushButton[kind="panel"]:hover {{
    background: {c["PANEL_BTN_HOVER"]};
    border-color: {BRAND};
}}
QPushButton[kind="danger"] {{ color: {RED}; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QPlainTextEdit, QTextEdit {{
    background: {PANEL};
    border: 1px solid {c["FIELD_BORDER"]};
    border-radius: 5px;
    padding: 6px 9px;
    selection-background-color: {BRAND};
    selection-color: {on_brand};
}}
QLineEdit[kind="result_entry"] {{
    font-size: 10.5pt;
    font-weight: 700;
    padding: 5px 8px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QDateEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 2px solid {BRAND};
    padding: 5px 8px;
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
    border-top-right-radius: 4px;
    border-bottom: 1px solid {LINE};
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-position: bottom right;
    border-bottom-right-radius: 4px;
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

QTableWidget, QTableView {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 6px;
    gridline-color: {LINE2};
    selection-background-color: {BRAND_SOFT};
    selection-color: {INK};
}}
QTableWidget::item:hover:!selected, QTableView::item:hover:!selected {{
    background: {LINE2};
}}
QHeaderView::section {{
    background: {c["HEADER_BG"]};
    border: 0;
    border-bottom: 1px solid {LINE};
    border-right: 1px solid {LINE2};
    padding: 8px 10px;
    font-size: 9pt;
    font-weight: 700;
    color: {INK3};
    text-transform: uppercase;
}}
QTableView::item {{ padding: 5px 8px; }}

QGroupBox {{
    border: 1px solid {LINE};
    border-radius: 6px;
    margin-top: 14px;
    background: {PANEL};
    font-weight: 700;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {BRAND};
    font-size: 9.5pt;
}}

QLabel[role="h1"] {{ font-size: 15pt; font-weight: 700; }}
QLabel[role="hint"] {{ color: {INK3}; font-size: 9.5pt; }}
QLabel[role="field"] {{ color: {INK3}; font-size: 9pt; font-weight: 700; }}
QLabel[role="error"] {{ color: {RED}; font-weight: 600; }}
QLabel[role="ok"] {{ color: {GREEN}; font-weight: 600; }}
QLabel[role="pill_draft"] {{
    background: {LINE2}; color: {INK2}; border-radius: 11px; padding: 3px 10px; font-weight: 700; font-size: 8.5pt;
}}
QLabel[role="pill_prog"] {{
    background: {"#38301E" if dark else "#FDF5E3"}; color: {c["AMBER"]}; border-radius: 11px; padding: 3px 10px; font-weight: 700; font-size: 8.5pt;
}}
QLabel[role="pill_ready"] {{
    background: {"#1F3229" if dark else "#EAF5EE"}; color: {GREEN}; border-radius: 11px; padding: 3px 10px; font-weight: 700; font-size: 8.5pt;
}}
QLabel[role="pill_sent"] {{
    background: {BRAND_SOFT}; color: {BRAND_DARK if not dark else INK}; border-radius: 11px; padding: 3px 10px; font-weight: 700; font-size: 8.5pt;
}}

QStatusBar {{
    background: {c["HEADER_BG"]}; border-top: 1px solid {LINE}; color: {INK3};
}}
QStatusBar QLabel {{ padding: 0 10px; font-size: 9.5pt; }}

QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: {c["SCROLL"]}; border-radius: 6px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {c["SCROLL_HOVER"]}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; }}
QScrollBar::handle:horizontal {{
    background: {c["SCROLL"]}; border-radius: 6px; min-width: 30px;
}}

QToolTip {{
    background: {c["TIP_BG"]}; color: {c["TIP_TEXT"]}; border: 0;
    padding: 6px 9px; border-radius: 4px;
}}
QProgressBar {{
    border: 0; background: {c["TRACK"]}; border-radius: 4px; height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{ background: {BRAND}; border-radius: 4px; }}
"""


#: Kept for callers (and tests) that want the daylight sheet without asking.
STYLESHEET = stylesheet_for("light")
