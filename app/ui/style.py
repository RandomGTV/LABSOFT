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

Built to match the LabSoft web application in this folder, token for token,
so the two never disagree about what the program looks like:

  * a clinical navy and slate palette -- ``#0A3668`` for the action, sky
    ``#0284C7`` / cyan ``#38BDF8`` for emphasis, ``#DC2626`` for the live tab
    and for danger
  * soft corners: 4px on controls, 6px on panels
  * hairline ``#CBD5E1`` rules divide sections
  * Archivo, shipped in ``assets/fonts`` -- the web app asks for it too, and
    the lab PC has no internet to fetch it with

Where the web app's own value fails WCAG AA as text -- its ``#059669`` green
at 3.77:1, its ``#CBD5E1`` input border at 1.48:1 -- the nearest darker step
of the same hue is used instead, and the difference is noted at the value.
"""

from __future__ import annotations

from typing import Dict

LIGHT: Dict[str, str] = {
    # The marker: the underline on the live tab, the focus ring, and the fill
    # behind Sign out. White on it is 4.83:1, so it may carry words.
    "BRAND": "#DC2626",
    "BRAND_DARK": "#062344",
    "BRAND_SOFT": "#FEF2F2",
    # The primary action colour -- the navy the web app fills its main button
    # with. White on it is 12:1, so it carries words anywhere.
    "ACCENT_INK": "#0A3668",
    # Danger as *text* needs 4.5:1, which #DC2626 misses on every red tint it
    # would sit on, so written warnings use the darker step.
    "RED": "#B91C1C",
    "GREEN": "#047857",
    "AMBER": "#B45309",
    "BLUE": "#0369A1",
    "INK": "#0F172A",
    "INK2": "#334155",
    "INK3": "#64748B",
    "LINE": "#CBD5E1",
    "LINE2": "#E2E8F0",
    "BG": "#F8FAFC",
    "PANEL": "#FFFFFF",
    # Extras the stylesheet needs but nothing else refers to by name.
    # The web app draws input edges in #CBD5E1, which is 1.48:1 against paper
    # -- a box whose edge you cannot find. This is the same hue, dark enough
    # to see.
    "FIELD_BORDER": "#8494A8",
    "READONLY_BG": "#F1F5F9",
    "HEADER_BG": "#F1F5F9",
    "SCROLL": "#CBD5E1",
    "SCROLL_HOVER": "#94A3B8",
    "PANEL_BTN_BORDER": "#CBD5E1",
    "PANEL_BTN_HOVER": "#F1F5F9",
    "PRIMARY_OFF": "#E2E8F0",
    # 4.61:1 on its own fill. A disabled button is exempt from the contrast
    # rule, but "Check & make report" starts disabled and is the whole point
    # of the Job screen: nobody can wait for a button they cannot read.
    "PRIMARY_OFF_TEXT": "#5C6B7F",
    "GO_HOVER": "#062344",
    "GO_OFF": "#E2E8F0",
    "GO_OFF_TEXT": "#5C6B7F",
    "TRACK": "#E2E8F0",
    # The surface a printed page is previewed against. Deliberately darker
    # than the page in both themes, so white paper has an edge.
    "PAPER_MOUNT": "#6E7781",
    # The "you still owe this" colour ON the navy money band. It cannot be
    # BRAND: BRAND is red by day but cyan by night, and the band is filled
    # with ACCENT_INK which is that same cyan -- so at night the Discount and
    # Outstanding figures were painted cyan on cyan, 1.00:1, invisible.
    # The money band across the Job screen, and what sits on it. Its own pair
    # rather than ACCENT_INK: the accent is navy by day and cyan by NIGHT, so
    # the band became a full-width slab of bright cyan in the dark theme --
    # the brightest thing on a screen meant for a lab bench with the lights
    # off -- and the figures painted on it disappeared into it.
    "MONEY_BAND": "#0A3668",
    "ON_MONEY": "#FFFFFF",
    "MONEY_ALERT": "#FCA5A5",
    "TIP_BG": "#0F172A",
    "TIP_TEXT": "#F8FAFC",
    "FILL": "#F1F5F9",          # a filled surface that is not a card
    "RULE": "#CBD5E1",          # the rule between sections
    "ON_INK": "#FFFFFF",        # text on an ink-filled control
    "ON_ACCENT": "#FFFFFF",     # text on the navy
    # The bar across the top of the window. It gets its own pair rather than
    # borrowing INK/ON_INK, because INK inverts between the themes and a bar
    # that turned white at night would be the brightest thing in a dark room.
    "BAR": "#0A1929",
    "ON_BAR": "#FFFFFF",
    "BAR_MUTED": "#94A3B8",
    # Trouble, and the tint behind it. Separate from BRAND because BRAND is
    # red by day and cyan by night: a late row tinted with BRAND would come
    # out the same colour as "in progress" the moment the lights went off.
    "ALERT": "#B91C1C",
    "ALERT_SOFT": "#FEF2F2",
    # The sign-in panel. Its own pair, because the accent is navy by day and
    # cyan by night, and a full field of cyan at 3 a.m. is a torch.
    "HERO": "#0A3668",
    "ON_HERO": "#FFFFFF",
    "HERO_MUTED": "#A9C2DE",
}

# Dark theme. Backgrounds are a desaturated slate rather than black — pure
# black with white text strobes badly on a cheap monitor. Every foreground
# here clears 4.5:1 against the surface it sits on.
DARK: Dict[str, str] = {
    # The web app's night mode, measured: a deep slate ground, cyan where the
    # day theme is navy, and every foreground clearing 4.5:1 on the surface
    # it actually sits on.
    "BRAND": "#38BDF8",
    "BRAND_DARK": "#7DD3FC",
    "BRAND_SOFT": "#0C2D48",
    "ACCENT_INK": "#38BDF8",
    "RED": "#F87171",
    "GREEN": "#34D399",
    "AMBER": "#FBBF24",
    "BLUE": "#38BDF8",
    "INK": "#F8FAFC",
    "INK2": "#CBD5E1",
    "INK3": "#94A3B8",
    "LINE": "#334155",
    # A step above PANEL (#1E293B), not equal to it. At #1E293B every hairline
    # in the night theme -- the rule between table rows, the edge of a card,
    # the line under a section -- was drawn in exactly the colour behind it,
    # so the dark tables had no row separation at all.
    "LINE2": "#2C3B52",
    "BG": "#0B1120",
    "PANEL": "#1E293B",
    "FIELD_BORDER": "#7C8CA3",
    "READONLY_BG": "#0F172A",
    "HEADER_BG": "#0F172A",
    "SCROLL": "#334155",
    "SCROLL_HOVER": "#475569",
    "PANEL_BTN_BORDER": "#334155",
    "PANEL_BTN_HOVER": "#0F172A",
    "PRIMARY_OFF": "#1E293B",
    "PRIMARY_OFF_TEXT": "#8A9AAF",
    "GO_HOVER": "#7DD3FC",
    "GO_OFF": "#1E293B",
    "GO_OFF_TEXT": "#8A9AAF",
    "TRACK": "#0F172A",
    "PAPER_MOUNT": "#111A28",
    "MONEY_BAND": "#102A43",
    "ON_MONEY": "#F8FAFC",
    "MONEY_ALERT": "#FCA5A5",
    "TIP_BG": "#F8FAFC",
    "TIP_TEXT": "#0B1120",
    "FILL": "#0F172A",
    "RULE": "#334155",
    "ON_INK": "#0B1120",
    "ON_ACCENT": "#0B1120",
    "BAR": "#060C16",
    "ON_BAR": "#F8FAFC",
    "BAR_MUTED": "#94A3B8",
    "ALERT": "#F87171",
    "ALERT_SOFT": "#3B0A0A",
    # Lifted a step off the night ground (#0B1120) so the two panels of the
    # sign-in screen read as two panels. Still 13.99:1 under white.
    "HERO": "#102A43",
    "ON_HERO": "#F8FAFC",
    "HERO_MUTED": "#93AFC9",
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
    "H": ("#FEE2E2", "#B91C1C"),
    "L": ("#E0F2FE", "#0369A1"),
    "A": ("#FEF3C7", "#B45309"),
    "N": ("#ECFDF5", "#047857"),
}
FLAG_FILL_DARK = {
    "H": ("#450A0A", "#7F1D1D"),
    "L": ("#082F49", "#0C4A6E"),
    "A": ("#451A03", "#78350F"),
    "N": ("#064E3B", "#065F46"),
}

#: The four job states, drawn the same way as the flags.
STATUS_FILL_LIGHT = {
    "draft":  ("#475569", "#F1F5F9", "#CBD5E1"),
    "prog":   ("#0369A1", "#E0F2FE", "#7DD3FC"),
    "ready":  ("#B45309", "#FEF3C7", "#FCD34D"),
    "sent":   ("#047857", "#ECFDF5", "#6EE7B7"),
}
STATUS_FILL_DARK = {
    "draft":  ("#94A3B8", "#0F172A", "#334155"),
    "prog":   ("#38BDF8", "#082F49", "#0C4A6E"),
    "ready":  ("#FBBF24", "#451A03", "#78350F"),
    "sent":   ("#34D399", "#064E3B", "#065F46"),
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


_CHEVRONS: Dict[str, str] = {}


def _cached_drawing(key: str, draw) -> str:
    """Draw a small icon once, keep it on disk, and return a QSS-safe path.

    Qt stylesheets can only put a *file* in ``image:``; they cannot draw. Every
    small mark the sheet needs -- the dropdown chevron, the spin arrows, the
    tick in a checkbox -- comes through here.
    """
    if key in _CHEVRONS:
        return _CHEVRONS[key]
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QImage, QPainter

        from .. import config

        folder = config.data_dir() / "ui"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{key.replace('#', '')}.png"

        if not path.exists():
            scale = 2
            img = QImage(10 * scale, 10 * scale,
                         QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.transparent)
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            draw(p, scale)
            p.end()
            if not img.save(str(path)):
                _CHEVRONS[key] = ""
                return ""
        # Backslashes are escapes inside a Qt stylesheet url(), so a Windows
        # path has to go in with forward slashes.
        _CHEVRONS[key] = str(path).replace("\\", "/")
    except Exception:
        _CHEVRONS[key] = ""
    return _CHEVRONS[key]


def tick_icon(colour: str) -> str:
    """The tick inside a ticked checkbox.

    Without it a ticked box differs from an unticked one only by its fill, so
    "print the watermark" on and off looked like two shades of the same
    square. A tick is the mark people actually look for.
    """
    def draw(p, scale):
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QColor, QPen

        pen = QPen(QColor(colour))
        pen.setWidthF(1.9 * scale)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawPolyline([QPointF(2.1 * scale, 5.2 * scale),
                        QPointF(4.2 * scale, 7.3 * scale),
                        QPointF(8.0 * scale, 3.0 * scale)])

    return _cached_drawing(f"tick-{colour.lower()}", draw)


def chevron_icon(colour: str, up: bool = False) -> str:
    """A small chevron, drawn once and cached on disk.

    Qt stylesheets do not honour the CSS "zero-size box with borders" triangle
    trick used for ``QComboBox::down-arrow``: it paints the whole border box
    instead, which is why every dropdown in the program showed a small filled
    rectangle where its arrow should be. Drawing a real image and pointing the
    rule at it is the only way to get a chevron out of QSS.

    Returns a path safe to drop into ``image: url(...)``, or "" if it could not
    be drawn -- the caller then leaves the arrow out rather than showing the
    rectangle again.
    """
    key = f"{colour.lower()}-{'up' if up else 'down'}"
    if key in _CHEVRONS:
        return _CHEVRONS[key]

    try:
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QColor, QImage, QPainter, QPen

        from .. import config

        folder = config.data_dir() / "ui"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"chevron-{key.lstrip('#')}.png"

        if not path.exists():
            # 2x for crispness on a scaled display; the rule sizes it down.
            size, scale = 10, 2
            img = QImage(size * scale, size * scale,
                         QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.transparent)
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            pen = QPen(QColor(colour))
            pen.setWidthF(1.8 * scale)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            high, low = (7.0, 4.0) if up else (4.0, 7.0)
            p.drawPolyline([QPointF(2.0 * scale, high * scale),
                            QPointF(5.0 * scale, low * scale),
                            QPointF(8.0 * scale, high * scale)])
            p.end()
            if not img.save(str(path)):
                _CHEVRONS[key] = ""
                return ""
        # Backslashes are escapes inside a Qt stylesheet url(), so a Windows
        # path has to go in with forward slashes.
        _CHEVRONS[key] = str(path).replace("\\", "/")
    except Exception:
        _CHEVRONS[key] = ""
    return _CHEVRONS[key]


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
    ON_ACCENT = c["ON_ACCENT"]
    ACCENT_INK = c["ACCENT_INK"]
    BAR = c["BAR"]
    ON_BAR = c["ON_BAR"]
    BAR_MUTED = c["BAR_MUTED"]
    ALERT = c["ALERT"]
    ALERT_SOFT = c["ALERT_SOFT"]
    HERO = c["HERO"]
    ON_HERO = c["ON_HERO"]
    HERO_MUTED = c["HERO_MUTED"]
    FONT = FONT_STACK
    CHEVRON = chevron_icon(INK2)
    CHEVRON_UP = chevron_icon(INK2, up=True)
    TICK = tick_icon(c["ON_ACCENT"])

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
    border-radius: 8px;
}}
QListWidget::item {{ padding: 7px 9px; }}
QListWidget::item:selected {{ background: {FILL}; color: {INK}; }}
QListWidget::item:hover {{ background: {LINE2}; }}
QMenu {{ background: {PANEL}; color: {INK}; border: 1px solid {INK}; }}
QMenu::item {{ padding: 7px 16px; }}
QMenu::item:selected {{ background: {FILL}; }}

/* ── The application bar ───────────────────────────────────────────────
   44px of filled ink across the top: the name of the program, the name of
   the laboratory, and who is signed in. It is furniture, so it is the one
   surface that does not change when the theme does -- only its own pair. */
#appBar {{ background: {BAR}; }}
#appBar QLabel {{ color: {ON_BAR}; background: transparent; }}
#appBar QLabel[role="wordmark"] {{
    font-size: 11pt; font-weight: 800; letter-spacing: 2px;
}}
#appBar QLabel[role="barmuted"] {{
    color: {BAR_MUTED}; font-size: 8pt; font-weight: 600; letter-spacing: 1px;
}}
#appBar QLabel[role="baruser"] {{ font-size: 9pt; font-weight: 700; }}
#appBar QPushButton {{
    background: transparent; border: 1px solid {BAR_MUTED}; color: {ON_BAR};
    padding: 4px 11px; font-weight: 700; font-size: 8.5pt; min-height: 0;
}}
#appBar QPushButton:hover {{ border-color: {ON_BAR}; }}
#appBar QPushButton:focus {{ border: 2px solid {BRAND}; padding: 3px 10px; }}
/* Sign out is the one destructive thing on the bar, so it wears the red.
   ALERT, not BRAND: BRAND is red by day but cyan by night, which painted
   Sign out the same colour as Save settings and Open · Space -- the one
   button you must not press by accident, dressed as the one you must. */
#appBar QPushButton[kind="danger"] {{
    background: {ALERT}; border-color: {ALERT}; color: {c["ON_INK"] if dark else "#FFFFFF"};
}}
#appBar QPushButton[kind="danger"]:hover {{
    background: {"#FCA5A5" if dark else "#B91C1C"};
    border-color: {"#FCA5A5" if dark else "#B91C1C"};
}}

/* The function-key strip under the tabs. */
#keyStrip {{ background: {BAR}; }}
#keyStrip QLabel[role="keyname"] {{ background: transparent; }}
#keyStrip QLabel[role="keycap"] {{
    color: #FFFFFF; background: {ACCENT_INK if not dark else "#0C4A6E"};
    font-size: 7.5pt; font-weight: 800; padding: 2px 6px; border-radius: 6px;
}}
#keyStrip QLabel[role="keyname"] {{
    color: {BAR_MUTED}; font-size: 8pt; font-weight: 600;
}}
/* The square beside the signed-in name: somebody is signed in and the
   database is open. Solid, because at 9px a border is most of the shape. */
#signedInDot {{ background: {GREEN}; border: 0; }}

/* Tabs: a 2px rule runs the width of the bar, and the live tab is the one
   carrying the accent. */
QTabBar {{ background: {BG}; }}
QTabWidget::pane {{
    border: 0;
    border-top: 1px solid {RULE};
    background: {PANEL};
    border-radius: 0;
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    padding: 9px 12px 7px 12px;
    font-size: 9.5pt;
    margin: 0;
    border: 0;
    border-bottom: 3px solid transparent;
    border-radius: 0;
    color: {INK2};
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background: {PANEL};
    border-bottom: 3px solid {BRAND};
    color: {ACCENT_INK};
    font-weight: 800;
}}
QTabBar::tab:hover:!selected {{ color: {INK}; }}
/* Focus underlines the label rather than recolouring it: the accent already
   means "this is the live tab", and two reds side by side said nothing. */
QTabBar::tab:focus {{ text-decoration: underline; }}

/* Buttons. A 1px edge and a 4px corner, no gradient. The plain button is the
   common case; primary and "go" are both the navy, and there is one of those
   per screen. */
QPushButton {{
    background: {PANEL};
    border: 1px solid {LINE if not dark else "#3C464E"};
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
    min-height: 22px;
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
    padding: 9px 17px;
}}
QCheckBox:focus, QRadioButton:focus {{ color: {BRAND}; }}
/* A rounded square with a tick in it, not a circle. At 17px a border-radius
   of 8 is a circle, so every checkbox in the program -- six of them on the
   Settings page alone -- was drawn as a radio button, which says "one of
   these" when it means "on or off". */
/* The row a checkbox occupies is what you actually have to hit, and at 19px
   it was under the 24px minimum -- nine of them on the Settings page. */
QCheckBox {{ min-height: 28px; spacing: 9px; }}
QCheckBox::indicator {{
    width: 17px; height: 17px; border-radius: 5px;
    border: 1px solid {c["FIELD_BORDER"]}; background: {PANEL};
}}
QCheckBox::indicator:hover {{ border-color: {INK2}; }}
QCheckBox::indicator:checked {{
    background: {ACCENT_INK}; border-color: {ACCENT_INK};
    {f"image: url({TICK});" if TICK else ""}
}}
QCheckBox::indicator:focus {{ border: 2px solid {BRAND}; }}
/* Toggle buttons (the work-queue filters) must show which one is active. */
QPushButton:checked {{
    background: {ACCENT_INK};
    border-color: {ACCENT_INK};
    color: {ON_ACCENT};
}}
QPushButton:checked:hover {{
    background: {BRAND_DARK}; border-color: {BRAND_DARK};
}}
QPushButton[kind="primary"] {{
    background: {ACCENT_INK}; border-color: {ACCENT_INK}; color: {ON_ACCENT};
    font-weight: 700;
}}
QPushButton[kind="primary"]:hover {{
    background: {BRAND_DARK}; border-color: {BRAND_DARK};
}}
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
    border-radius: 8px;
    padding: 9px 13px;
    min-height: 20px;
    selection-background-color: {BRAND};
    selection-color: {ON_ACCENT};
}}
QLineEdit:hover, QComboBox:hover {{ border-color: {INK2}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QDateEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 2px solid {BRAND};
    padding: 8px 12px;
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
QComboBox::drop-down {{ border: 0; width: 26px; }}
/* A drawn chevron, not the CSS border triangle -- see chevron_icon(). */
QComboBox::down-arrow {{
    {f"image: url({CHEVRON});" if CHEVRON else "image: none;"}
    width: 10px; height: 10px; margin-right: 9px;
}}

/* Spin boxes: Fusion draws tiny unreadable arrows at this size, so the
   buttons are given real width and a drawn triangle. */
QSpinBox, QDoubleSpinBox {{ padding-right: 20px; }}
/* QDateEdit is not a QSpinBox -- both descend from QAbstractSpinBox -- so it
   has to be named, or Windows draws its steppers itself and the date fields
   on Billing end up wearing a different decade from everything beside them. */
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
    subcontrol-origin: border;
    width: 20px;
    border: 0;
    background: {LINE2};
}}
QAbstractSpinBox::up-button {{
    subcontrol-position: top right;
    border-bottom: 1px solid {LINE};
    border-top-right-radius: 8px;
}}
QAbstractSpinBox::down-button {{
    subcontrol-position: bottom right;
    border-bottom-right-radius: 8px;
}}
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{
    background: {LINE};
}}
/* Drawn chevrons again, for the same reason as the combo box: the CSS
   triangle trick paints its whole border box, so every spin box in the
   program showed two small filled rectangles instead of arrows. */
QAbstractSpinBox::up-arrow {{
    {f"image: url({CHEVRON_UP});" if CHEVRON_UP else "image: none;"}
    width: 9px; height: 9px;
}}
QAbstractSpinBox::down-arrow {{
    {f"image: url({CHEVRON});" if CHEVRON else "image: none;"}
    width: 9px; height: 9px;
}}
/* A date field with a calendar popup has one drop-down, not a pair of
   steppers, so it gets the combo box's treatment rather than the spin box's. */
QAbstractSpinBox::drop-down {{ border: 0; width: 26px; }}

/* Tables: a 2px rule under the head, hairlines between rows, no outer box. */
QTableWidget, QTableView {{
    background: {PANEL};
    border: 0;
    border-radius: 8px;
    gridline-color: transparent;
    selection-background-color: {FILL};
    selection-color: {INK};
}}
QHeaderView::section {{
    background: {PANEL};
    border: 0;
    border-bottom: 1px solid {LINE2};
    border-right: 0;
    padding: 12px 12px;
    font-size: 9pt;
    font-weight: 600;
    color: {INK3};
}}
QTableView::item {{ padding: 10px 12px; border: 0; }}
QTableView::item:hover {{ background: {FILL}; }}

/* Group boxes are cards, the way the web application draws a settings
   section: paper on the page ground, a hairline round it, and the name in
   the accent above the fields. */
/* A settings section. The heading sits *above* a plain card rather than in a
   notch cut through its border: the notched box with a tiny coloured caption
   is the single most dated thing a Qt form can wear, and it made Settings
   look a decade older than every other screen. */
QGroupBox {{
    border: 1px solid {LINE2};
    border-radius: 14px;
    margin-top: 30px;
    padding: 22px 20px 18px 20px;
    background: {PANEL};
    font-size: 13pt;
    font-weight: 700;
}}
/* The heading's weight has to be set on the box, because Qt draws the title
   with the box's own font; the children are put back to reading size here. */
QGroupBox > QWidget, QGroupBox QLabel, QGroupBox QLineEdit, QGroupBox QComboBox,
QGroupBox QCheckBox, QGroupBox QPlainTextEdit, QGroupBox QPushButton {{
    font-size: 10.5pt;
    font-weight: 400;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 2px;
    top: 4px;
    padding: 0;
    color: {INK};
    background: transparent;
    font-size: 13pt;
    font-weight: 700;
}}
/* The band across the top of a dialog: its name, and one line saying what
   it is for. Separated by a rule rather than a box, because a dialog is
   already a box. */
#dialogHeader {{ border-bottom: 1px solid {LINE}; background: transparent; }}
#dialogHeader QLabel {{ background: transparent; }}
#settingsScroll > QWidget > QWidget {{ background: {BG}; }}

/* ── The Job screen's bands ────────────────────────────────────────────
   Four surfaces of falling weight: an ink money band, a white status rail
   and result field, and a quiet counsel column on the page ground. Named
   here rather than styled inline so that switching theme restyles them. */
#statusRail {{ background: {PANEL}; border-bottom: 1px solid {RULE}; }}
/* The left column is filled, so the screen reads as three surfaces: what you
   put in (left), what you are working on (the white field), and what the
   program has to say (the counsel column). The fill runs up through the
   status rail so the column is one panel from the top of the window down. */
#railLeft   {{ background: {BG}; border-right: 1px solid {RULE}; }}
#leftRail   {{ background: {BG}; border-right: 1px solid {RULE}; }}
#patientBlock {{ background: transparent; border-bottom: 1px solid {LINE}; }}
#testsBlock {{ background: transparent; }}
/* Fields stay paper-white against it, so a box still looks like a box. */
#leftRail QLineEdit, #leftRail QComboBox, #leftRail QSpinBox {{
    background: {PANEL};
}}
#moneyBand  {{ background: {c["MONEY_BAND"]}; }}
#moneyBand QLabel {{ color: {c["ON_MONEY"]}; }}
#resultsField {{ background: {PANEL}; border-right: 1px solid {LINE}; }}
#resultsHead {{ background: {PANEL}; border-bottom: 1px solid {RULE}; }}
#footBar    {{ background: {PANEL}; border-top: 1px solid {LINE2}; }}
/* A result outside the panic limits. The only place on the Job screen where
   the accent fills a whole band, because it is the only thing on it that
   must stop the operator rather than inform them. */
#panicBanner {{
    background: {ALERT_SOFT};
    border-top: 1px solid {ALERT};
    border-bottom: 2px solid {ALERT};
}}
#panicBanner QLabel {{ background: transparent; }}
QLabel[role="panic"] {{
    color: {ALERT}; font-weight: 800; font-size: 8.5pt;
}}
#counsel    {{ background: {BG}; border-left: 1px solid {LINE}; }}
#counselBlock {{ border-bottom: 1px solid {LINE}; }}
#groupRow   {{ background: {FILL}; }}

/* ── The Work queue's board ────────────────────────────────────────────
   A filter bar on paper, a strip of scopes on the ground, the board itself,
   and a foot bar. Every row of the board is drawn by BoardDelegate, which
   reads these same tokens at paint time, so a theme change carries. */
#filterBar {{ background: {PANEL}; border-bottom: 1px solid {LINE2}; }}
/* The Patients register: a column of paper against the page, with its own
   heading block above the list. */
#register {{ background: {PANEL}; border-right: 1px solid {LINE2}; }}
#registerHead {{ background: {PANEL}; border-bottom: 1px solid {LINE2}; }}
#registerList {{ background: {PANEL}; border: 0; }}
/* The patient's name, set at the size the artboard gives it. */
QLabel[role="person"] {{
    font-size: 22pt; font-weight: 800; letter-spacing: -0.5px; color: {INK};
}}
QLabel[role="figure"] {{ font-size: 13pt; font-weight: 800; color: {INK}; }}
QLabel[role="figure"][alert="true"] {{ color: {ALERT}; }}
#scopeStrip {{ background: {PANEL}; border-bottom: 1px solid {LINE2}; }}
/* The same chips inline in a filter bar rather than in a row of their own,
   so they carry no rule under them. */
#periodStrip {{ background: transparent; border: 0; }}
#boardTable {{ background: {PANEL}; border: 0; }}
/* No dotted focus rectangle. Qt draws one round the current cell whatever the
   sheet says about ::item, and on a read-only list it reads as an editable
   box -- it was sitting over "Blood Sugar F & PP" the moment the Bill dialog
   opened, and round the first report number on the Billing ledger. */
QTableView, QTableWidget, QListView, QListWidget, QTreeView {{ outline: 0; }}
/* No font rules here on purpose: a stylesheet cannot set letter-spacing, and
   whatever it does set would override the font the header is given in code. */
#boardTable QHeaderView::section {{
    background: {PANEL};
    color: {INK3};
    border: 0;
    border-bottom: 1px solid {LINE2};
    padding: 0 22px 0 0;
    font-size: 9pt;
    font-weight: 600;
}}
/* The scope chips are the tabs of the board: chosen is filled ink, the rest
   are quiet text. No colour, because the accent belongs to Open. */
#scopeStrip QPushButton, #periodStrip QPushButton {{
    background: transparent; border: 1px solid transparent; color: {INK3};
    padding: 6px 16px; font-weight: 600; font-size: 10pt; min-height: 20px;
    border-radius: 999px;
}}
#scopeStrip QPushButton:hover, #periodStrip QPushButton:hover {{ color: {INK}; background: {LINE2}; }}
#scopeStrip QPushButton:checked, #periodStrip QPushButton:checked {{
    background: {ACCENT_INK}; border-color: {ACCENT_INK}; color: {ON_ACCENT};
    border-radius: 999px;
}}
#scopeStrip QPushButton:focus, #periodStrip QPushButton:focus {{ border: 2px solid {BRAND}; padding: 3px 11px; }}

/* A field label. Sentence case at a readable size, not 7.5pt small caps:
   the caps were half the reason the program looked a decade old, and the
   same label style now runs from the sign-in card through every screen. */
QLabel[role="micro"], QLabel[role="field"] {{
    color: {INK2}; font-size: 10pt; font-weight: 600; letter-spacing: 0;
}}
/* The four numbers over the board. The label is small and quiet, the number
   is the largest thing on the screen after the patient's name, and the note
   under it says what the number means without needing a legend. */
QLabel[role="statlabel"] {{
    color: {INK3}; font-size: 9pt; font-weight: 600;
}}
QLabel[role="statvalue"] {{ font-size: 21pt; font-weight: 700; color: {INK}; }}
/* A figure block on the day book: a 2px rule down its left side instead of a
   card, so eight of them read as one row rather than eight boxes. */
#statBlock {{ border-left: 2px solid {RULE}; background: transparent; }}
#statBlock QLabel {{ background: transparent; }}
QLabel[role="statvalue"][alert="true"] {{ color: {ALERT}; }}
QLabel[role="statnote"] {{ color: {INK3}; font-size: 8.5pt; }}
QLabel[role="foot"] {{ color: {INK3}; font-size: 9.5pt; }}
QLabel[role="stat"] {{ font-size: 12.5pt; font-weight: 700; }}
QLabel[role="money"] {{ font-size: 25pt; font-weight: 800; }}
QLabel[role="railvalue"] {{ font-size: 12.5pt; font-weight: 800; }}
QLabel[role="railname"] {{ font-size: 11pt; font-weight: 700; }}
QLabel[role="group"] {{
    font-size: 10.5pt; font-weight: 700; color: {INK};
}}
QLabel[role="method"] {{ color: {INK3}; font-size: 8pt; }}

/* Buttons living on the ink money band. */
#moneyBand QPushButton {{
    background: transparent; border: 1px solid {c["BAR_MUTED"]};
    color: {c["ON_MONEY"]}; font-weight: 700; padding: 7px 14px;
}}
#moneyBand QPushButton:hover {{ background: rgba(255, 255, 255, 0.12); }}
#moneyBand QPushButton[kind="primary"] {{
    background: {c["ON_MONEY"]}; border-color: {c["ON_MONEY"]};
    color: {c["MONEY_BAND"]};
}}
#moneyBand QPushButton[kind="primary"]:hover {{ background: {LINE2}; }}

QLabel[role="h1"] {{ font-size: 17pt; font-weight: 700; letter-spacing: -0.4px; }}
QLabel[role="hint"] {{ color: {INK3}; font-size: 9.5pt; }}
QLabel[role="error"] {{ color: {RED}; font-weight: 700; }}
QLabel[role="ok"] {{ color: {GREEN}; font-weight: 700; }}

/* ── Settings ──────────────────────────────────────────────────────────
   A rail of sections down the left, and one section at a time on the right.
   The rail is furniture, so it is flat with a single edge rather than a
   rounded list box floating inside the page. */
#settingsRail {{
    background: {PANEL};
    border: 0;
    border-right: 1px solid {LINE2};
    border-radius: 0;
    outline: 0;
    padding: 10px 0;
}}
#settingsRail::item {{
    padding: 11px 14px 11px 20px;
    color: {INK2};
    border-left: 3px solid transparent;
}}
#settingsRail::item:hover {{ background: {FILL}; color: {INK}; }}
#settingsRail::item:selected {{
    background: {FILL};
    color: {INK};
    border-left: 3px solid {ACCENT_INK};
    font-weight: 700;
}}
/* A block on a settings page that is a thing rather than a field -- one
   image, or the cloud copy. */
#imageCard {{
    background: {PANEL}; border: 1px solid {LINE2}; border-radius: 12px;
}}
#imageCard QLabel {{ background: transparent; }}
#settingsScroll, #settingsHost {{ background: {BG}; border: 0; }}
/* Said of an image the settings point at but the assets folder does not
   have: a filename that resolves to nothing is worth saying in red. */
QLabel[role="hint"][missing="true"] {{ color: {ALERT}; font-weight: 600; }}

/* The mount a printed document is previewed on. A receipt is white paper in
   both themes, so the paper stays white and the surface under it darkens --
   the opposite of the old slip preview, which recoloured the paper and left
   black ink on it. */
#slipScroll {{ background: {c["PAPER_MOUNT"]}; border: 1px solid {LINE2};
              border-radius: 10px; }}
#slipMount {{ background: {c["PAPER_MOUNT"]}; border: 0; }}
#slipMount QLabel {{ background: transparent; }}

/* ── Signing in ────────────────────────────────────────────────────────
   Two panels across the screen. The left is deep navy and carries the
   laboratory's name; the right is the ordinary page ground with one white
   card on it. Everything is named so the night theme repaints it too --
   the old sign-in screen hardcoded its own greys and stayed daylight for
   ever. */
#signInWindow {{ background: {BG}; }}
#hero {{ background: {HERO}; border: 0; }}
#hero QLabel {{ background: transparent; color: {ON_HERO}; }}
#heroRule {{ background: {HERO_MUTED}; border: 0; max-height: 1px; }}
#hero QLabel[role="herowordmark"] {{
    color: {HERO_MUTED}; font-size: 10pt; font-weight: 800; letter-spacing: 4px;
}}
/* The laboratory's name is the largest thing on the screen and the only
   place a serif-weight size is warranted. Tight tracking keeps a long name
   on two lines rather than three. */
#hero QLabel[role="heroname"] {{
    font-size: 38pt; font-weight: 800; letter-spacing: -1.4px; line-height: 108%;
}}
#hero QLabel[role="herosub"] {{
    color: {HERO_MUTED}; font-size: 12pt; font-weight: 600; letter-spacing: 0.6px;
}}
#hero QLabel[role="heroblurb"] {{
    color: {HERO_MUTED}; font-size: 11pt; font-weight: 400; line-height: 150%;
}}
#hero QLabel[role="herolabel"] {{
    color: {HERO_MUTED}; font-size: 8pt; font-weight: 700; letter-spacing: 1.4px;
}}
#hero QLabel[role="herofact"] {{ font-size: 12pt; font-weight: 700; }}

#signInSide {{ background: {BG}; border: 0; }}
/* One card, floated on the ground. 16px of radius, a hairline instead of a
   heavy border, and the drop shadow comes from elevate() in widgets.py --
   Qt's stylesheets have no box-shadow. */
#signInCard {{
    background: {PANEL}; border: 1px solid {LINE2}; border-radius: 16px;
}}
#signInCard QLabel {{ background: transparent; }}
#signInCard QLabel[role="cardtitle"] {{
    font-size: 24pt; font-weight: 700; letter-spacing: -0.8px; color: {INK};
}}
#signInCard QLabel[role="hint"] {{ color: {INK3}; font-size: 9.5pt; }}
#cardRule {{ background: {LINE2}; border: 0; max-height: 1px; }}
/* The PIN box. Four characters, centred, widely spaced: the shape of the
   field says how much to type without a label saying "4 digits". */
#pinField {{
    font-size: 20pt; font-weight: 700; letter-spacing: 10px;
    padding: 0 8px 0 18px; border-radius: 10px;
}}
#signInCard QLineEdit, #signInCard QComboBox {{
    border-radius: 10px; font-size: 11pt; padding: 0 12px;
}}
#signInCard QPushButton[kind="primary"] {{
    border-radius: 10px; font-size: 11.5pt; font-weight: 700;
}}
#signInCard QPushButton[kind="quiet"] {{ font-size: 10pt; }}

QStatusBar {{
    background: {PANEL}; border-top: 1px solid {RULE}; color: {INK3};
}}
QStatusBar QLabel {{ padding: 0 10px; font-size: 9pt; }}
QStatusBar::item {{ border: 0; }}

QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: {c["SCROLL"]}; border-radius: 6px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {c["SCROLL_HOVER"]}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; }}
QScrollBar::handle:horizontal {{
    background: {c["SCROLL"]}; border-radius: 6px; min-width: 30px;
}}

QToolTip {{
    background: {c["TIP_BG"]}; color: {c["TIP_TEXT"]}; border: 0;
    padding: 6px 9px; border-radius: 8px;
}}
QProgressBar {{
    border: 0; background: {c["TRACK"]}; border-radius: 6px; height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{ background: {ACCENT_INK}; border-radius: 6px; }}
"""


#: Kept for callers (and tests) that want the daylight sheet without asking.
STYLESHEET = stylesheet_for("light")
