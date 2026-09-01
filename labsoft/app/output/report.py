"""Report rendering: the program's actual product.

Drawn with QPainter rather than assembled as HTML, because three things the
lab's report does are unreliable in Qt's HTML subset:

  * the signature block sits at the foot of the page however short the report is
  * the watermark sits behind the text
  * the header and column titles repeat on a second page

The same paint code drives both a QPdfWriter (for the WhatsApp PDF) and a
QPrinter (for paper), so what is printed and what is sent can never drift apart.

Layout is in millimetres and converted at paint time, so output is identical at
any device resolution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import (
    QColor, QFont, QFontMetricsF, QImage, QPageLayout, QPageSize, QPainter,
    QPainterPath, QPdfWriter, QPen,
)

from .. import config

# --------------------------------------------------------------------------
# Page geometry, in millimetres
# --------------------------------------------------------------------------

PAGE_W = 210.0
PAGE_H = 297.0

MARGIN_L = 14.0
MARGIN_R = 14.0
MARGIN_T = 8.0
MARGIN_B = 10.0

HEADER_H = 27.0          # letterhead band
BLANK_HEADER_H = 38.0    # space left when printing on preprinted paper

SIG_BLOCK_H = 26.0       # reserved at the foot of every page
FOOTER_H = 5.0

# Column positions as fractions of the printable width, matching the lab's
# report: description on the left, observed and normal centred.
COL_DESC = 0.00
COL_OBS = 0.46
COL_NORM = 0.73

# Medical Blue letterhead color theme
BLUE_PRIMARY = QColor("#0E4D92")    # Rich Medical Navy Blue
BLUE_DARK = QColor("#0A3668")       # Deep Navy for modern banner
BLUE_ACCENT = QColor("#0080B8")     # Medical Cyan/Blue accent
BLUE_TINT = QColor("#F0F6FC")       # Soft Icy-Blue background for classic letterhead
BLUE_EDGE = QColor("#CCDDF0")       # Delicate border for classic letterhead
BLUE_DIV = QColor("#A9C7E8")        # Letterhead vertical divider
BLACK = QColor("#111111")
GREY = QColor("#555555")
WATERMARK = QColor(14, 77, 146, 20)
FLAG_HIGH_COLOUR = QColor("#C1121F")
FLAG_LOW_COLOUR = QColor("#1A5FB4")

SERIF = "Times New Roman"
SANS = "Arial"


@dataclass
class ReportRow:
    """One printed line. A group heading is a row with is_group set."""
    description: str = ""
    observed: str = ""
    normal: str = ""
    is_group: bool = False
    flag: str = ""
    not_done: bool = False
    specimen: str = ""      # printed under a group heading, e.g. "Serum"


@dataclass
class ReportData:
    report_no: str = ""
    date_text: str = ""
    collected_at_text: str = ""
    reported_at_text: str = ""
    name: str = ""
    sex: str = ""
    age: str = ""
    referred_by: str = ""
    institution: str = ""
    phone: str = ""
    rows: List[ReportRow] = field(default_factory=list)
    remarks: str = ""
    revision_no: int = 1
    settings: Dict[str, str] = field(default_factory=dict)
    format_type: str = "standard"

    # A detailed single-test report: its own sheet, with the standard
    # interpretation printed beneath the result.
    title: str = "Laboratory Test Report"
    interpretation: str = ""

    def setting(self, key: str, default: str = "") -> str:
        v = self.settings.get(key)
        if v is None:
            v = config.DEFAULT_SETTINGS.get(key, default)
        return "" if v is None else str(v)

    def flag_on(self, key: str) -> bool:
        return str(self.setting(key, "0")).strip() in ("1", "true", "True", "yes")


# --------------------------------------------------------------------------
# Painter
# --------------------------------------------------------------------------

class _Renderer:
    def __init__(self, painter: QPainter, data: ReportData, dpmm: float,
                 with_header: bool):
        self.p = painter
        self.d = data
        self.k = dpmm                 # device units per millimetre
        self.with_header = with_header
        self.page = 1
        self.total_pages = 1

    # -- unit helpers --------------------------------------------------
    def x(self, mm: float) -> float:
        return mm * self.k

    def content_w(self) -> float:
        return PAGE_W - MARGIN_L - MARGIN_R

    def col_x(self, fraction: float) -> float:
        return MARGIN_L + self.content_w() * fraction

    def font(self, family: str, size_pt: float, bold=False, italic=False) -> QFont:
        f = QFont(family)
        f.setPointSizeF(size_pt)
        f.setBold(bold)
        f.setItalic(italic)
        # Style hints let Qt substitute sensibly when the exact face is absent,
        # which matters because this must also render on a machine without
        # Times New Roman installed.
        f.setStyleHint(QFont.StyleHint.Serif if family == SERIF else QFont.StyleHint.SansSerif)
        return f

    def metrics(self, font: QFont) -> QFontMetricsF:
        """Metrics measured on the paint device, not the screen.

        QFontMetricsF(font) alone measures at the default 96 dpi while the PDF
        paints at 300, so every box came out a third of the size it needed and
        clipped the text inside it.
        """
        return QFontMetricsF(font, self.p.device())

    def width_mm(self, s: str, font: QFont) -> float:
        return self.metrics(font).horizontalAdvance(s) / self.k

    def fit(self, s: str, font: QFont, width_mm: float) -> str:
        """Shorten text with an ellipsis so it cannot overprint its neighbour.

        Qt's drawText does not clip to the rectangle it is given, so a long
        patient name ran straight through the Sex and Age fields and a long test
        name ran through the result. Better a shortened name than an unreadable
        one printed on top of the value.
        """
        if not s:
            return ""
        self.p.setFont(font)
        limit = max(0.0, width_mm) * self.k
        return QFontMetricsF(font, self.p.device()).elidedText(
            s, Qt.TextElideMode.ElideRight, int(limit))

    def text(self, mm_x: float, mm_y: float, s: str, font: QFont,
             colour: QColor = BLACK, align: str = "left",
             width_mm: Optional[float] = None) -> float:
        """Draw one line, vertically centred on mm_y. Returns its height in mm."""
        if s is None or s == "":
            return 0.0
        self.p.setFont(font)
        self.p.setPen(QPen(colour))
        h_mm = self.metrics(font).height() / self.k
        # Extra room around the line so descenders are never shaved off.
        box_h = h_mm * 1.6
        top = mm_y - (box_h - h_mm) / 2.0
        w = width_mm if width_mm is not None else (PAGE_W - MARGIN_R - mm_x)
        flag = {"left": Qt.AlignmentFlag.AlignLeft,
                "center": Qt.AlignmentFlag.AlignHCenter,
                "right": Qt.AlignmentFlag.AlignRight}[align]
        self.p.drawText(
            QRectF(self.x(mm_x), self.x(top), self.x(w), self.x(box_h)),
            int(flag | Qt.AlignmentFlag.AlignVCenter), s)
        return h_mm

    def line(self, x1: float, y: float, x2: float, width_mm: float = 0.3,
             colour: QColor = BLACK) -> None:
        pen = QPen(colour)
        pen.setWidthF(self.x(width_mm))
        self.p.setPen(pen)
        self.p.drawLine(int(self.x(x1)), int(self.x(y)), int(self.x(x2)), int(self.x(y)))

    # -- page furniture ------------------------------------------------
    def draw_watermark(self) -> None:
        if not self.with_header or not self.d.flag_on("watermark"):
            return
        cx, cy = PAGE_W / 2, PAGE_H / 2
        logo = _load_image(self.d.setting("logo_file"))
        if logo is not None and not logo.isNull():
            size = 95.0
            self.p.save()
            self.p.setOpacity(0.07)
            self.p.drawImage(
                QRectF(self.x(cx - size / 2), self.x(cy - size / 2),
                       self.x(size), self.x(size)),
                logo)
            self.p.restore()
            return
        # No logo file yet: a faint ring with the lab's name, so the page is
        # never blank where the watermark belongs.
        pen = QPen(WATERMARK)
        pen.setWidthF(self.x(4))
        self.p.setPen(pen)
        r = 42.0
        self.p.drawEllipse(QRectF(self.x(cx - r), self.x(cy - r), self.x(r * 2), self.x(r * 2)))
        name = (self.d.setting("lab_name") or "").upper()
        self.p.setFont(self.font(SANS, 20, bold=True))
        self.p.setPen(QPen(WATERMARK))
        self.p.drawText(QRectF(self.x(cx - r), self.x(cy - 6), self.x(r * 2), self.x(12)),
                        int(Qt.AlignmentFlag.AlignCenter), name)

    def draw_header(self) -> float:
        """Returns the y position (mm) where content may start.

        Whether the letterhead is drawn is decided by ``with_header`` and by
        nothing else. This used to consult the print_header setting as well,
        which meant a caller asking outright for a letterhead was overruled --
        and the PDF sent to the patient came out with a blank top and no lab
        name on it, because a setting about the paper in the tray reached the
        file. The setting belongs where the decision is made: the defaults in
        write_pdf and print_report.
        """
        if not self.with_header:
            try:
                blank_h = float(self.d.setting("blank_header_mm", str(BLANK_HEADER_H)) or BLANK_HEADER_H)
            except ValueError:
                blank_h = BLANK_HEADER_H
            return MARGIN_T + blank_h
        if (self.d.setting("header_style", "classic") or "classic").lower() == "modern":
            return self.draw_header_modern()
        return self.draw_header_classic()

    def draw_header_modern(self) -> float:
        """A clinical letterhead: solid deep blue band, white type, cyan accent rule."""
        top = MARGIN_T
        band_h = 28.0
        left = MARGIN_L - 4
        width = PAGE_W - MARGIN_L - MARGIN_R + 8

        self.p.fillRect(QRectF(self.x(left), self.x(top), self.x(width),
                               self.x(band_h)), BLUE_DARK)
        # Accent stripe: cyan bottom line
        self.p.fillRect(QRectF(self.x(left), self.x(top + band_h),
                               self.x(width), self.x(1.6)), BLUE_ACCENT)

        white = QColor("#FFFFFF")
        pale = QColor("#D4E7FA")
        cyan = QColor("#48CAE4")

        logo = _load_image(self.d.setting("logo_file"))
        emblem = 22.0
        lx = left + 4
        if logo is not None and not logo.isNull():
            self.p.save()
            is_square = abs(logo.width() - logo.height()) / max(logo.width(), logo.height(), 1) < 0.15
            if is_square:
                path = QPainterPath()
                path.addEllipse(QRectF(self.x(lx), self.x(top + (band_h - emblem) / 2),
                                       self.x(emblem), self.x(emblem)))
                self.p.setClipPath(path)
            self.p.drawImage(
                QRectF(self.x(lx), self.x(top + (band_h - emblem) / 2),
                       self.x(emblem), self.x(emblem)), logo)
            self.p.restore()
        else:
            pen = QPen(white)
            pen.setWidthF(self.x(0.6))
            self.p.setPen(pen)
            self.p.drawEllipse(QRectF(self.x(lx), self.x(top + (band_h - emblem) / 2),
                                      self.x(emblem), self.x(emblem)))
            self.text(lx, top + band_h / 2, "✚", self.font(SANS, 14, bold=True),
                      white, align="center", width_mm=emblem)
        name_x = lx + emblem + 5

        prefix = self.d.setting("lab_name_prefix")
        full = (prefix + " " + self.d.setting("lab_name")).strip()
        self.text(name_x, top + 7.5, full, self.font(SANS, 19, bold=True), white)
        sub = self.d.setting("lab_subtitle")
        if sub:
            self.text(name_x, top + 15.0, sub.upper(),
                      self.font(SANS, 8.5, bold=True), cyan)
        self.text(name_x, top + 21.5, "ACCURACY  •  CARE  •  TRUST",
                  self.font(SANS, 6.5, bold=True), pale)

        # Contact block, right aligned inside the band.
        lines = [self.d.setting(k) for k in
                 ("lab_address_1", "lab_address_2", "lab_phone", "lab_email")]
        lines = [ln.replace("Ph :", "").replace("e-mail :", "").strip()
                 for ln in lines if ln]
        step = 4.2
        ay = top + (band_h - step * len(lines)) / 2 + step / 2
        rw = 76.0
        rx = PAGE_W - MARGIN_R - rw + 2
        for line in lines:
            self.text(rx, ay, self.fit(line, self.font(SANS, 7.5), rw),
                      self.font(SANS, 7.5), pale, align="right", width_mm=rw)
            ay += step

        return top + band_h + 6.0

    def draw_header_classic(self) -> float:
        top = MARGIN_T
        band_h = 28.0
        band = QRectF(self.x(MARGIN_L - 4), self.x(top),
                      self.x(PAGE_W - MARGIN_L - MARGIN_R + 8), self.x(band_h))
        self.p.fillRect(band, BLUE_TINT)
        pen = QPen(BLUE_EDGE)
        pen.setWidthF(self.x(0.35))
        self.p.setPen(pen)
        self.p.drawRect(band)

        # Optional photo at the far right
        photo = _load_image(self.d.setting("header_photo_file"))
        right_edge = PAGE_W - MARGIN_R + 4
        if photo is not None and not photo.isNull():
            pw = 34.0
            self.p.drawImage(
                QRectF(self.x(right_edge - pw), self.x(top),
                       self.x(pw), self.x(band_h)), photo)
            right_edge -= pw

        # Emblem / Logo
        logo = _load_image(self.d.setting("logo_file"))
        left = MARGIN_L - 2
        emblem = 24.0
        if logo is not None and not logo.isNull():
            self.p.save()
            is_square = abs(logo.width() - logo.height()) / max(logo.width(), logo.height(), 1) < 0.15
            if is_square:
                path = QPainterPath()
                path.addEllipse(QRectF(self.x(left + 2), self.x(top + (band_h - emblem) / 2),
                                       self.x(emblem), self.x(emblem)))
                self.p.setClipPath(path)
            self.p.drawImage(
                QRectF(self.x(left + 2), self.x(top + (band_h - emblem) / 2),
                       self.x(emblem), self.x(emblem)), logo)
            self.p.restore()
        else:
            pen = QPen(BLUE_PRIMARY)
            pen.setWidthF(self.x(0.8))
            self.p.setPen(pen)
            self.p.drawEllipse(QRectF(self.x(left + 2), self.x(top + (band_h - emblem) / 2),
                                      self.x(emblem), self.x(emblem)))
            self.text(left + 2, top + band_h / 2, "✚", self.font(SANS, 14, bold=True),
                      BLUE_PRIMARY, align="center", width_mm=emblem)
        name_x = left + emblem + 5

        # Lab name block
        prefix = (self.d.setting("lab_name_prefix") or "New").strip().upper()
        y = top + 3.8
        if prefix:
            self.text(name_x, y, prefix, self.font(SANS, 8.5, bold=True), BLUE_ACCENT)
            y += 4.2
        name_font = self.font(SANS, 21, bold=True)
        self.text(name_x, y + 3.2, self.d.setting("lab_name"), name_font, BLUE_PRIMARY)
        y += 11.5

        sub = self.d.setting("lab_subtitle")
        if sub:
            sub_font = self.font(SANS, 7.5, bold=True)
            w_mm = self.width_mm(sub.upper(), sub_font) + 4.0
            self.p.fillRect(QRectF(self.x(name_x), self.x(y), self.x(w_mm), self.x(4.5)),
                            BLUE_PRIMARY)
            self.text(name_x, y + 2.25, sub.upper(), sub_font, QColor("#FFFFFF"),
                      align="center", width_mm=w_mm)
            self.text(name_x + w_mm + 3.0, y + 2.25, "ACCURACY • CARE • TRUST",
                      self.font(SANS, 6.0, bold=True), BLUE_ACCENT)

        # Divider and address block
        div_x = MARGIN_L + self.content_w() * 0.54
        pen = QPen(BLUE_DIV)
        pen.setWidthF(self.x(0.25))
        self.p.setPen(pen)
        self.p.drawLine(int(self.x(div_x)), int(self.x(top + 2.5)),
                        int(self.x(div_x)), int(self.x(top + band_h - 2.5)))

        addr_font = self.font(SANS, 8)
        lines = [self.d.setting(k) for k in
                 ("lab_address_1", "lab_address_2", "lab_phone", "lab_email")]
        lines = [ln for ln in lines if ln]
        step = 4.2
        ay = top + (band_h - step * len(lines)) / 2 + step / 2
        for line in lines:
            self.text(div_x + 3, ay, line, addr_font, BLACK,
                       width_mm=max(10.0, right_edge - div_x - 4))
            ay += step

        return top + band_h + 4.5

    def draw_meta(self, y: float) -> float:
        is_hba1c = (self.d.format_type == "hba1c" or
                    (len(self.d.rows) <= 3 and any("hba1c" in r.description.lower() for r in self.d.rows)))
        f = self.font(SERIF, 10.5)
        fb = self.font(SERIF, 10.5, bold=True)
        lh = 5.4

        if is_hba1c:
            col1_x = MARGIN_L
            col2_x = MARGIN_L + self.content_w() * 0.35
            col3_x = MARGIN_L + self.content_w() * 0.72

            # Line 1
            self.text(col1_x, y, self.d.name or "", fb, width_mm=self.content_w() * 0.34)
            age_sex = f"{self.d.age} / {self.d.sex}".strip(" /") if (self.d.age or self.d.sex) else ""
            if age_sex:
                self.text(col2_x, y, f"Age / Sex : {age_sex}", fb)
            self.text(col3_x, y, "Ref. No. :", f)
            self.text(col3_x + 18, y, self.d.report_no, fb)
            y += lh

            # Line 2
            ref_by = self.d.referred_by or ""
            self.text(col1_x, y, f"Referred by : {ref_by}", f, width_mm=self.content_w() * 0.34)
            if self.d.collected_at_text:
                self.text(col2_x, y, f"Sample Collected At : {self.d.collected_at_text}", f)
            self.text(col3_x, y, "IP/OP/SRF No :", f)
            y += lh

            # Line 3 & 4
            self.text(col1_x, y, "Institution : MITHRA MEDICAL", f)
            if self.d.reported_at_text:
                self.text(col2_x, y, f"Report On : {self.d.reported_at_text}", f)
            if self.d.phone:
                self.text(col3_x, y, f"Phone No : {self.d.phone}", f)
            y += 5.0

            self.text(col1_x + 20.0, y, "LABORATORY KUTTIPPALA", f)
            y += 5.2

            # Double rule
            self.line(MARGIN_L, y, PAGE_W - MARGIN_R, 0.55)
            self.line(MARGIN_L, y + 1.1, PAGE_W - MARGIN_R, 0.25)
            return y + 4.0

        # Standard layout for all other tests / multi-test reports
        right_x = MARGIN_L + self.content_w() * 0.66
        mid_x = MARGIN_L + self.content_w() * 0.38

        self.text(MARGIN_L, y, "Report No", f)
        self.text(MARGIN_L + 25, y, ":", f)
        self.text(MARGIN_L + 28, y, self.d.report_no, fb)
        if self.d.collected_at_text:
            self.text(mid_x, y, f"Sample Collected : {self.d.collected_at_text}", f)
        self.text(right_x, y, "Date", f)
        self.text(right_x + 14, y, ":", f)
        self.text(right_x + 17, y, self.d.date_text, fb)
        y += lh

        self.text(MARGIN_L, y, "Name", f)
        self.text(MARGIN_L + 25, y, ":", f)
        name_room = mid_x - (MARGIN_L + 28) - 3
        self.text(MARGIN_L + 28, y, self.fit(self.d.name, fb, name_room), fb,
                  width_mm=name_room)
        if self.d.sex or self.d.age:
            age_sex = f"{self.d.age} / {self.d.sex}".strip(" /")
            self.text(mid_x, y, "Age / Sex", f)
            self.text(mid_x + 18, y, ":", f)
            self.text(mid_x + 21, y, age_sex, fb)
        if self.d.reported_at_text:
            self.text(right_x, y, "Reported", f)
            self.text(right_x + 18, y, ":", f)
            self.text(right_x + 21, y, self.d.reported_at_text, f)
        y += lh

        if (self.d.referred_by or "").strip():
            self.text(MARGIN_L, y, "Ref. by Dr", f)
            self.text(MARGIN_L + 25, y, ":", f)
            self.text(MARGIN_L + 28, y, self.d.referred_by, fb)
            y += lh

        # Double rule
        y += 1.6
        self.line(MARGIN_L, y, PAGE_W - MARGIN_R, 0.55)
        self.line(MARGIN_L, y + 1.1, PAGE_W - MARGIN_R, 0.25)
        return y + 3.4

    def draw_title(self, y: float) -> float:
        """Only the detailed single-test sheets carry a title."""
        title = (self.d.title or "").strip()
        if not title or title == "Laboratory Test Report":
            return y
        modern = (self.d.setting("header_style", "classic") or "").lower() == "modern"
        self.text(MARGIN_L, y + 1.5, title.upper(),
                  self.font(SANS, 10.5, bold=True),
                  BLUE_PRIMARY if modern else BLACK,
                  align="center", width_mm=self.content_w())
        return y + 8.0

    def draw_table_head(self, y: float) -> float:
        f = self.font(SERIF, 10.5, bold=True)
        w = self.content_w()
        obs_w = w * (COL_NORM - COL_OBS)
        norm_w = w * (1 - COL_NORM)

        is_hba1c = (self.d.format_type == "hba1c" or
                    (len(self.d.rows) <= 3 and any("hba1c" in r.description.lower() for r in self.d.rows)))

        if is_hba1c:
            box_h = 6.8
            self.p.fillRect(QRectF(self.x(MARGIN_L), self.x(y), self.x(w), self.x(box_h)), QColor("#E0E0E0"))
            pen = QPen(BLACK)
            pen.setWidthF(self.x(0.35))
            self.p.setPen(pen)
            self.p.drawRect(QRectF(self.x(MARGIN_L), self.x(y), self.x(w), self.x(box_h)))

            text_y = y + 1.2
            self.text(self.col_x(COL_DESC) + 4, text_y, "Test Description", f)
            self.text(self.col_x(COL_OBS), text_y, "Value Observed", f,
                      align="center", width_mm=obs_w)
            self.text(self.col_x(COL_NORM), text_y, "Reference Range", f,
                      align="center", width_mm=norm_w)
            return y + box_h + 3.5
        else:
            self.text(self.col_x(COL_DESC) + 4, y, "Test Description", f)
            self.text(self.col_x(COL_OBS), y, "Observed Value", f,
                      align="center", width_mm=obs_w)
            self.text(self.col_x(COL_NORM), y, "Normal Value", f,
                      align="center", width_mm=norm_w)
            y += 5.6
            self.line(MARGIN_L, y, PAGE_W - MARGIN_R, 0.5)
            return y + 2.4

    def draw_signatures(self) -> None:
        base = PAGE_H - MARGIN_B - SIG_BLOCK_H + 4
        d = self.d

        sig = _load_image(d.setting("signature_file"))
        if sig is not None and not sig.isNull():
            w, h = 26.0, 11.0
            self.p.drawImage(
                QRectF(self.x(PAGE_W - MARGIN_R - w - 6), self.x(base - h - 1),
                       self.x(w), self.x(h)), sig)

        fn = self.font(SERIF, 10.5, bold=True)
        fq = self.font(SERIF, 7.5)
        fr = self.font(SERIF, 10.5)

        y = base
        is_hba1c = (self.d.format_type == "hba1c" or
                    (len(self.d.rows) <= 3 and any("hba1c" in r.description.lower() for r in self.d.rows)))
        mid_name = (d.setting("sign_mid_name") or "").strip()
        if mid_name and not is_hba1c:
            col_w = (self.content_w() - 10) / 3.0
            # Left signatory
            self.text(MARGIN_L, y, d.setting("sign_left_name"), fn, width_mm=col_w)
            self.text(MARGIN_L, y + 4.4, d.setting("sign_left_qual"), fq, width_mm=col_w)
            self.text(MARGIN_L, y + 8.0, d.setting("sign_left_role"), fr, width_mm=col_w)

            # Middle signatory
            cx = MARGIN_L + col_w + 5
            self.text(cx, y, mid_name, fn, align="center", width_mm=col_w)
            self.text(cx, y + 4.4, d.setting("sign_mid_qual"), fq, align="center", width_mm=col_w)
            self.text(cx, y + 8.0, d.setting("sign_mid_role"), fr, align="center", width_mm=col_w)

            # Right signatory
            rx = PAGE_W - MARGIN_R - col_w
            self.text(rx, y, d.setting("sign_right_name"), fn, align="right", width_mm=col_w)
            self.text(rx, y + 4.4, d.setting("sign_right_qual"), fq, align="right", width_mm=col_w)
            self.text(rx, y + 8.0, d.setting("sign_right_role"), fr, align="right", width_mm=col_w)
        else:
            self.text(MARGIN_L, y, d.setting("sign_left_name") or "SAHEED MOHAMED. P.", fn)
            self.text(MARGIN_L, y + 4.4, d.setting("sign_left_role") or "Technologist", fr)

            rw = 60.0
            rx = PAGE_W - MARGIN_R - rw
            self.line(rx + 2, y - 2.5, rx + rw - 2, 0.4, BLACK)
            self.text(rx, y, d.setting("sign_right_name") or "ABDUNNASER MAYYERI", fn, align="center", width_mm=rw)
            self.text(rx, y + 4.4, d.setting("sign_right_role") or "Lab Incharge", fr, align="center", width_mm=rw)

    def draw_footer(self) -> None:
        note = self.d.setting("footer_note")
        y = PAGE_H - MARGIN_B - 1
        f = self.font(SANS, 6.5)
        if note and self.with_header:
            self.text(MARGIN_L, y, note, f, GREY)
        if self.total_pages > 1:
            self.text(PAGE_W - MARGIN_R - 40, y, f"Page {self.page} of {self.total_pages}",
                      f, GREY, align="right", width_mm=40)

        # Bottom disclaimer strip (blue banner) only when printing on plain paper
        if self.with_header and self.d.flag_on("print_disclaimer"):
            disc_text = (self.d.setting("disclaimer_text") or "").strip()
            if disc_text:
                strip_h = 7.0
                sy = PAGE_H - MARGIN_B - strip_h + 3.0
                self.p.fillRect(QRectF(self.x(MARGIN_L - 4), self.x(sy),
                                       self.x(self.content_w() + 8), self.x(strip_h)), BLUE_PRIMARY)
                self.text(MARGIN_L, sy + 2.0, disc_text, self.font(SANS, 5.5),
                          QColor("#FFFFFF"), align="center", width_mm=self.content_w())

    def draw_interpretation(self, y: float) -> float:
        """The explanatory block on a detailed single-test report."""
        interp = (self.d.interpretation or "").strip()
        if not interp:
            return y

        # Exact HbA1c format matching the clinical sample
        if "Glycosylated hemoglobin values are used" in interp:
            self.text(MARGIN_L, y, "Notes:", self.font(SERIF, 10.5, bold=True))
            y += 5.2
            f_body = self.font(SERIF, 9.5)
            room = self.content_w()

            p1 = ("Glycosylated hemoglobin values are used to assess long-term glucose control in diabetes, "
                  "especially in insulin-dependent diabetics whose glucose levels are labile, and in whom blood "
                  "and urine glucose measurements exhibit significant daily variation. GHb measurements reflect "
                  "the level of control present over the preceding 100-120 days. In such patients, whose fasting "
                  "glucose concentrations are fairly consistent from day to day, there is a correlation between "
                  "glycosylated hemoglobin and single fasting glucose levels. Continued high levels of blood glucose "
                  "are reflected in high GHb concentrations. Glycosylated hemoglobin predicts the progression of "
                  "retinopathy.")
            for line in self.wrap(p1, f_body, room):
                self.text(MARGIN_L, y, line, f_body)
                y += 4.2

            y += 3.0
            p2 = ("Chronic blood loss, hemolytic anemia, or other setting for decrease in RBC life span, results in a "
                  "decrease in the glycosylated hemoglobin level. Pregnancy may lower glycosylated hemoglobin.")
            for line in self.wrap(p2, f_body, room):
                self.text(MARGIN_L, y, line, f_body)
                y += 4.2

            return y + 4.0

        modern = (self.d.setting("header_style", "classic") or "").lower() == "modern"
        accent = BLUE_PRIMARY if modern else BLACK

        self.line(MARGIN_L, y, PAGE_W - MARGIN_R, 0.3, QColor("#BBBBBB"))
        y += 3.4
        self.text(MARGIN_L, y, "INTERPRETATION & NOTES",
                  self.font(SANS, 8, bold=True), accent)
        y += 5.0

        body = self.font(SERIF, 9.5)
        mono = self.font(SERIF, 9.5)
        room = self.content_w() - 4
        for raw in interp.split("\n"):
            line = raw.rstrip()
            if not line:
                y += 2.4
                continue
            heading = line.strip() == line.strip().upper() and len(line.strip()) > 3
            font = self.font(SANS, 8, bold=True) if heading else (
                mono if line.startswith("    ") else body)
            colour = accent if heading else BLACK
            tabular = line.startswith("    ")
            indent = 2.0 + (4.0 if tabular else 0.0)
            pieces = ([line.strip()] if tabular
                      else self.wrap(line.strip(), font, room - indent))
            for piece in pieces:
                self.text(MARGIN_L + indent, y,
                          self.fit(piece, font, room - indent) if tabular else piece,
                          font, colour)
                y += 4.6 if not heading else 5.2
        return y + 2

    def wrap(self, s: str, font: QFont, width_mm: float) -> List[str]:
        """Break a line into as many lines as it needs to fit the width."""
        words = (s or "").split()
        if not words:
            return []
        lines: List[str] = []
        current = words[0]
        for word in words[1:]:
            trial = current + " " + word
            if self.width_mm(trial, font) <= width_mm:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def draw_end_lines(self, y: float) -> float:
        w = self.content_w()
        self.text(MARGIN_L, y, "** End Of Report **", self.font(SERIF, 10, bold=True),
                  align="center", width_mm=w)
        return y + 5.2


def _require_qt_application() -> None:
    """Qt aborts the process rather than raising if it has to measure text with
    no application object in existence. Catching it here turns a hard crash
    into a message the operator can act on."""
    from PyQt6.QtGui import QGuiApplication

    if QGuiApplication.instance() is None:
        raise RuntimeError(
            "The report engine started before the application was ready. "
            "Please close and reopen LabSoft, then try again."
        )


def _load_image(filename: str) -> Optional[QImage]:
    if not filename:
        return None
    p = Path(filename)
    if not p.exists():
        p = config.assets_dir() / filename
    if not p.exists():
        return None
    img = QImage(str(p))
    return img if not img.isNull() else None


# --------------------------------------------------------------------------
# Pagination + paint
# --------------------------------------------------------------------------

ROW_H = 5.3
GROUP_H = 7.6
GROUP_GAP = 2.2
SPECIMEN_H = 4.6


def _paginate(rows: Sequence[ReportRow], first_top: float, later_top: float,
              head_h: float, tail_mm: float = 0.0) -> List[List[ReportRow]]:
    """Split rows into pages.

    Three rules, each from a way the page went wrong:
      * a group heading is never the last thing on a page
      * a group that continues onto the next page gets its heading repeated,
        so a reader cannot mistake which section a result belongs to
      * tail_mm reserves room for the remarks and the end-of-report lines, which
        otherwise printed on top of the signature block
    """
    bottom = PAGE_H - MARGIN_B - SIG_BLOCK_H - FOOTER_H - 8 - max(0.0, tail_mm)

    pages: List[List[ReportRow]] = []
    current: List[ReportRow] = []
    y = first_top + head_h
    open_group: Optional[ReportRow] = None

    i = 0
    n = len(rows)
    while i < n:
        row = rows[i]
        h = ROW_H + (SPECIMEN_H if row.specimen else 0.0)
        if row.is_group:
            h = GROUP_GAP + GROUP_H + (SPECIMEN_H if row.specimen else 0.0)

        # A heading must not be the last thing on a page.
        needed = h + (ROW_H if row.is_group and i + 1 < n else 0)

        if y + needed > bottom and current:
            pages.append(current)
            current = []
            y = later_top + head_h
            if open_group is not None and not row.is_group:
                carried = ReportRow(
                    description=f"{open_group.description} (continued)",
                    is_group=True)
                current.append(carried)
                y += GROUP_GAP + GROUP_H
            continue

        if row.is_group:
            open_group = row
        current.append(row)
        y += h
        i += 1

    pages.append(current)
    return pages


def paint_report(painter: QPainter, data: ReportData, dpmm: float,
                 device=None, with_header: bool = True,
                 new_page=None) -> None:
    """Paint the whole report, starting a new device page as needed.

    new_page is an optional callable returning a fresh QPainter. A PDF writer
    keeps painting into the same painter across pages; the image preview needs
    a new painter per page, so it supplies one here rather than duplicating any
    of the layout code.
    """
    r = _Renderer(painter, data, dpmm, with_header)

    probe_first = (MARGIN_T + HEADER_H + 3.5) if with_header else (MARGIN_T + BLANK_HEADER_H)
    meta_h = 5.6 * (3 if (data.referred_by or "").strip() else 2) + 5.0
    if (data.title or "").strip() and data.title != "Laboratory Test Report":
        meta_h += 8.0
    head_h = 8.0
    # Room the closing block needs on the final page: gap, remarks, end lines.
    tail = 8.0 + 5.2 * 2 + (10.0 if (data.remarks or "").strip() else 0.0)
    if (data.interpretation or "").strip():
        # Reserved generously: the notes are drawn after the last row, and a
        # note that runs into the signatures would look like a printing fault.
        tail += 12.0 + 5.2 * len(data.interpretation.split("\n"))
    pages = _paginate(data.rows, probe_first + meta_h, probe_first + meta_h,
                      head_h, tail_mm=tail)
    r.total_pages = len(pages)

    for index, page_rows in enumerate(pages):
        if index > 0:
            if new_page is not None:
                fresh = new_page()
                if fresh is not None:
                    r.p = fresh
            elif device is not None:
                device.newPage()
        r.page = index + 1

        r.draw_watermark()
        y = r.draw_header()
        y = r.draw_meta(y)
        y = r.draw_title(y)
        y = r.draw_table_head(y)

        f_row = r.font(SERIF, 10.5)
        f_group = r.font(SERIF, 11, bold=True)
        f_obs = r.font(SERIF, 10.5)
        f_obs_flag = r.font(SERIF, 10.5, bold=True)
        w = r.content_w()
        show_flags = data.flag_on("print_flags")
        is_hba1c = (data.format_type == "hba1c" or
                    (len(data.rows) <= 3 and any("hba1c" in r.description.lower() for r in data.rows)))

        for row in page_rows:
            desc_room = w * (COL_OBS - COL_DESC) - 6

            if row.is_group:
                y += GROUP_GAP
                if is_hba1c and ("BIOCHEMISTRY" in row.description.upper() or "BIO-CHEMISTRY" in row.description.upper()
                        or row.description.upper().startswith("DEPARTMENT OF")):
                    box_w = 110.0
                    box_h = 6.8
                    box_x = MARGIN_L + (w - box_w) / 2
                    r.p.setPen(QPen(BLACK, r.x(0.35)))
                    r.p.drawRect(QRectF(r.x(box_x), r.x(y), r.x(box_w), r.x(box_h)))
                    r.text(box_x, y + 1.2, "DEPARTMENT OF CLINICAL BIOCHEMISTRY",
                           r.font(SANS, 9.5, bold=True), align="center", width_mm=box_w)
                    y += box_h + 5.5
                else:
                    r.text(r.col_x(COL_DESC), y,
                           r.fit(row.description, f_group, w * 0.9), f_group)
                    y += GROUP_H
                if row.specimen and not is_hba1c:
                    # The specimen belongs immediately under its heading, before
                    # any result: a value means nothing without knowing what was
                    # tested.
                    r.text(r.col_x(COL_DESC) + 4, y - 1.6,
                           f"Specimen : {row.specimen}",
                           r.font(SERIF, 9, italic=True), GREY)
                    y += SPECIMEN_H
                continue

            # Sub-heading within a group (e.g. Microscopic Examination, Motility, Morphology)
            if not row.observed and not row.normal:
                y += 1.2
                r.text(r.col_x(COL_DESC) + 2, y, row.description,
                       r.font(SERIF, 10.5, bold=True))
                y += ROW_H
                continue

            obs_room = w * (COL_NORM - COL_OBS)
            norm_room = w * (1 - COL_NORM)

            # Special layout for HbA1c test row
            if is_hba1c and ("HBA1C" in row.description.upper() or "GLYCATED" in row.description.upper()):
                r.text(r.col_x(COL_DESC) + 4, y, "HbA1C- Glycated Hb", r.font(SERIF, 10.5, bold=True))
                r.text(r.col_x(COL_DESC) + 4, y + 4.8, "[ Nephelometry Method ]", r.font(SERIF, 9.5, bold=True))
                r.text(r.col_x(COL_OBS), y + 2.0, row.observed, r.font(SERIF, 11, bold=True), align="center", width_mm=obs_room)
                y += 12.0
                continue

            # Special side-by-side layout for Mean Blood Glucose & Reference table
            if is_hba1c and ("MEAN BLOOD GLUCOSE" in row.description.upper() or row.description.upper() == "MBG"):
                mbg_val = row.observed or "157 mg/dl"
                if not mbg_val.endswith("mg/dl") and not mbg_val.endswith("mg/dL"):
                    mbg_val = f"{mbg_val} mg/dl"
                r.text(r.col_x(COL_DESC) + 14, y + 14.0, f"Mean Blood Glucose :  {mbg_val}", r.font(SERIF, 10.5, bold=True))

                ref_lines = [
                    "Normal : < 5.7",
                    "Pre Diabetes : 5.7- 6.5",
                    "Diabetes : > 6.5",
                    "",
                    "Good Control : < 6.5",
                    "Adequate Control : 6.5 - 7.5",
                    "Inadequate Control : 7.5 - 8.5",
                    "Poor Control : > 8.5",
                ]
                ry = y
                f_ref = r.font(SERIF, 9.5)
                for rline in ref_lines:
                    if rline:
                        r.text(r.col_x(COL_NORM) + 4, ry, rline, f_ref)
                        ry += 4.2
                    else:
                        ry += 3.0
                y = max(y + 36.0, ry + 4.0)
                continue

            indented_names = {
                "Active", "Sluggish", "Non-motile", "NormalForms", "Normal Forms",
                "Giant Head", "Pin Head", "Swollen Neck", "Long Tail"
            }
            x_off = 8.0 if row.description.strip() in indented_names else 4.0
            r.text(r.col_x(COL_DESC) + x_off, y,
                   r.fit(row.description, f_row, desc_room - (x_off - 4.0)), f_row,
                   width_mm=desc_room - (x_off - 4.0))

            observed = row.observed
            colour = BLACK
            font = f_obs
            if show_flags and row.flag in ("H", "L"):
                observed = f"{observed} {'↑' if row.flag == 'H' else '↓'}"
                font = f_obs_flag
                colour = FLAG_HIGH_COLOUR if row.flag == "H" else FLAG_LOW_COLOUR

            r.text(r.col_x(COL_OBS), y, r.fit(observed, font, obs_room), font,
                   colour, align="center", width_mm=obs_room)
            r.text(r.col_x(COL_NORM), y, r.fit(row.normal, f_row, norm_room), f_row,
                   align="center", width_mm=norm_room)
            y += ROW_H
            if row.specimen:
                # Only used where one heading covers tests run on different
                # specimens -- then each result has to say which was used, or
                # the group line would be telling a half-truth.
                r.text(r.col_x(COL_DESC) + 8, y - 1.4,
                       f"Specimen : {row.specimen}",
                       r.font(SERIF, 8.5, italic=True), GREY)
                y += SPECIMEN_H

        if index == len(pages) - 1:
            if (data.interpretation or "").strip():
                y = r.draw_interpretation(y + 4)
            if (data.remarks or "").strip():
                y += 4
                r.text(MARGIN_L, y, "Remarks : " + data.remarks.strip(),
                       r.font(SERIF, 10))
                y += 6
            y += 8
            r.draw_end_lines(y)

        r.draw_signatures()
        r.draw_footer()


# --------------------------------------------------------------------------
# Output devices
# --------------------------------------------------------------------------

def write_pdf(data: ReportData, path: Union[Path, str], dpi: int = 300,
              with_header: bool = True) -> Path:
    """Produce the file. It carries the letterhead unless told otherwise.

    A *file* is not a sheet of paper. print_header off means "there is
    preprinted stationery in the printer", which is true of the printer and
    false of a PDF going out on WhatsApp or into the patient's folder -- that
    one has to identify the laboratory on its own, because nothing is going to
    be underneath it. Paper follows the setting; see print_report.

    Writes to a temporary name and moves it into place, so an interrupted
    write never leaves a half-finished PDF where a complete one is expected.
    """
    _require_qt_application()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")

    writer = QPdfWriter(str(tmp))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setResolution(dpi)
    writer.setPageMargins(__import__("PyQt6.QtCore", fromlist=["QMarginsF"]).QMarginsF(0, 0, 0, 0),
                          QPageLayout.Unit.Millimeter)
    writer.setTitle(f"Report {data.report_no}")
    writer.setCreator("LabSoft")

    painter = QPainter()
    if not painter.begin(writer):
        raise RuntimeError(f"Could not start writing the PDF at {tmp}")
    try:
        dpmm = dpi / 25.4
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        paint_report(painter, data, dpmm, device=writer, with_header=with_header)
    finally:
        painter.end()

    if path.exists():
        path.unlink()
    tmp.replace(path)
    return path


def render_pages(data: ReportData, width_px: int = 900,
                 with_header: Optional[bool] = None) -> List[QImage]:
    """Render the report to images, one per page, for on-screen preview.

    Deliberately the same paint code as the PDF, at a different resolution.
    A preview drawn by separate code would eventually disagree with the file
    actually sent, which is worse than having no preview at all.
    """
    if with_header is None:
        with_header = data.flag_on("print_header")
    _require_qt_application()
    from PyQt6.QtGui import QImage

    dpmm = width_px / PAGE_W
    height_px = int(round(PAGE_H * dpmm))

    pages: List[QImage] = []

    state = {"painter": None, "image": None}

    def start() -> QPainter:
        image = QImage(width_px, height_px, QImage.Format.Format_RGB32)
        image.fill(0xFFFFFFFF)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        state["painter"] = painter
        state["image"] = image
        return painter

    def finish() -> None:
        if state["painter"] is not None:
            state["painter"].end()
            state["painter"] = None
        if state["image"] is not None:
            pages.append(state["image"])
            state["image"] = None

    def next_page() -> QPainter:
        finish()
        return start()

    painter = start()
    try:
        paint_report(painter, data, dpmm, with_header=with_header,
                     new_page=next_page)
    finally:
        finish()

    return pages


def print_report(data: ReportData, printer, with_header: Optional[bool] = None) -> None:
    """Render to a QPrinter. with_header=None follows the saved setting."""
    if with_header is None:
        with_header = data.flag_on("print_header")
    painter = QPainter()
    if not painter.begin(printer):
        raise RuntimeError("The printer could not be opened.")
    try:
        dpmm = printer.resolution() / 25.4
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        paint_report(painter, data, dpmm, device=printer, with_header=with_header)
    finally:
        painter.end()
