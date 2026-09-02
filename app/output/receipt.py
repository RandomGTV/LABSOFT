"""The bill, as a piece of paper.

Drawn with the same painter and the same letterhead as the report, so the two
documents a patient is handed at the counter look like they came from the same
laboratory — because they did.

A receipt is a single page by design. If a bill ever grows past what one page
holds, the items are summarised rather than spilling onto a second sheet: a
two-page receipt gets separated within the hour and then nobody can prove what
was paid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import QMarginsF, QRectF, QSizeF, Qt
from PyQt6.QtGui import QColor, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter

from ..core import billing
from .report import (
    BLACK, GREY, MARGIN_B, MARGIN_L, MARGIN_R, PAGE_H, PAGE_W, SANS, SERIF,
    BLUE_DARK, BLUE_TINT, _Renderer, _require_qt_application,
)

ITEM_H = 5.6
MAX_ITEMS = 26          # what fits above the totals block on one page


@dataclass
class BillLine:
    label: str = ""
    rate_paise: int = 0
    qty: int = 1

    @property
    def amount_paise(self) -> int:
        return int(self.rate_paise) * max(1, int(self.qty))


@dataclass
class BillPaymentLine:
    amount_paise: int = 0
    mode: str = "cash"
    when: str = ""


@dataclass
class BillData:
    bill_no: str = ""
    date_text: str = ""
    name: str = ""
    sex: str = ""
    age: str = ""
    phone: str = ""
    referred_by: str = ""
    lines: List[BillLine] = field(default_factory=list)
    payments: List[BillPaymentLine] = field(default_factory=list)
    discount_type: str = billing.DISCOUNT_PERCENT
    discount_value: float = 0.0
    settings: Dict[str, str] = field(default_factory=dict)
    made_by: str = ""

    # Reused so _Renderer can read the lab's settings the same way.
    title: str = "Bill / Receipt"
    interpretation: str = ""
    report_no: str = ""
    rows: List = field(default_factory=list)
    remarks: str = ""
    revision_no: int = 1

    def setting(self, key: str, default: str = "") -> str:
        from .. import config

        v = self.settings.get(key)
        if v is None:
            v = config.DEFAULT_SETTINGS.get(key, default)
        return "" if v is None else str(v)

    def flag_on(self, key: str) -> bool:
        return str(self.setting(key, "0")).strip() in ("1", "true", "True", "yes")

    def totals(self) -> billing.BillTotals:
        return billing.compute_totals(
            [billing.LineItem(l.label, l.rate_paise, l.qty) for l in self.lines],
            self.discount_type, self.discount_value,
            [billing.Payment(p.amount_paise, p.mode) for p in self.payments])


# --------------------------------------------------------------------------
# Paint
# --------------------------------------------------------------------------

def paint_bill(painter: QPainter, data: BillData, dpmm: float,
               with_header: bool = True) -> None:
    r = _Renderer(painter, data, dpmm, with_header)
    w = r.content_w()

    # The watermark is deliberately left off a receipt: it is a money document,
    # and a pale logo behind the figures makes a photographed copy harder to read.
    y = r.draw_header()

    modern = (data.setting("header_style", "classic") or "").lower() == "modern"
    accent = BLUE_DARK if modern else BLACK

    r.text(MARGIN_L, y + 1.5, "BILL  /  RECEIPT", r.font(SANS, 11, bold=True),
           accent, align="center", width_mm=w)
    y += 9.0

    f = r.font(SERIF, 10.5)
    fb = r.font(SERIF, 10.5, bold=True)
    right_x = MARGIN_L + w * 0.62
    lh = 5.4

    def pair(x: float, caption: str, value: str, room: float) -> None:
        r.text(x, y, caption, f)
        r.text(x + 22, y, ":", f)
        r.text(x + 25, y, r.fit(value, fb, room), fb, width_mm=room)

    pair(MARGIN_L, "Bill No", data.bill_no, right_x - MARGIN_L - 28)
    pair(right_x, "Date", data.date_text, PAGE_W - MARGIN_R - right_x - 25)
    y += lh
    pair(MARGIN_L, "Name", data.name, right_x - MARGIN_L - 28)
    who = " / ".join(x for x in (data.sex, data.age) if x)
    if who:
        pair(right_x, "Sex / Age", who, PAGE_W - MARGIN_R - right_x - 25)
    y += lh
    if data.phone:
        pair(MARGIN_L, "Mobile", data.phone, right_x - MARGIN_L - 28)
    if (data.referred_by or "").strip():
        pair(right_x, "Ref. by Dr", data.referred_by,
             PAGE_W - MARGIN_R - right_x - 25)
    if data.phone or (data.referred_by or "").strip():
        y += lh

    y += 1.6
    r.line(MARGIN_L, y, PAGE_W - MARGIN_R, 0.55)
    y += 3.6

    # ---- item table -------------------------------------------------------
    col_sl = MARGIN_L
    col_item = MARGIN_L + 10
    col_rate = MARGIN_L + w * 0.60
    col_qty = MARGIN_L + w * 0.76
    col_amount = MARGIN_L + w * 0.84
    rate_room = w * 0.14
    qty_room = w * 0.07
    amount_room = PAGE_W - MARGIN_R - col_amount
    item_room = col_rate - col_item - 4

    head = r.font(SERIF, 10.5, bold=True)
    if modern:
        painter.fillRect(QRectF(r.x(MARGIN_L - 1), r.x(y - 3.2),
                                r.x(w + 2), r.x(7.0)), BLUE_TINT)
    r.text(col_sl, y, "#", head)
    r.text(col_item, y, "Description", head)
    r.text(col_rate, y, "Rate", head, align="right", width_mm=rate_room)
    r.text(col_qty, y, "Qty", head, align="right", width_mm=qty_room)
    r.text(col_amount, y, "Amount", head, align="right", width_mm=amount_room)
    y += 5.0
    r.line(MARGIN_L, y, PAGE_W - MARGIN_R, 0.35)
    y += 3.4

    body = r.font(SERIF, 10.5)
    shown = data.lines[:MAX_ITEMS]
    hidden = data.lines[MAX_ITEMS:]
    for i, line in enumerate(shown, start=1):
        r.text(col_sl, y, str(i), body)
        r.text(col_item, y, r.fit(line.label, body, item_room), body,
               width_mm=item_room)
        r.text(col_rate, y, billing.format_rupees(line.rate_paise, symbol=False),
               body, align="right", width_mm=rate_room)
        r.text(col_qty, y, str(max(1, int(line.qty))), body,
               align="right", width_mm=qty_room)
        r.text(col_amount, y,
               billing.format_rupees(line.amount_paise, symbol=False), body,
               align="right", width_mm=amount_room)
        y += ITEM_H

    if hidden:
        extra = sum(l.amount_paise for l in hidden)
        r.text(col_item, y, f"… and {len(hidden)} further items", body, GREY)
        r.text(col_amount, y, billing.format_rupees(extra, symbol=False), body,
               align="right", width_mm=amount_room)
        y += ITEM_H

    # ---- totals -----------------------------------------------------------
    t = data.totals()
    y += 2.0
    r.line(MARGIN_L, y, PAGE_W - MARGIN_R, 0.35)
    y += 4.2

    label_x = MARGIN_L + w * 0.52
    label_room = col_amount - label_x - 3

    def money(caption: str, paise: int, bold: bool = False,
              colour: QColor = BLACK) -> None:
        nonlocal y
        font = r.font(SERIF, 11 if bold else 10.5, bold=bold)
        r.text(label_x, y, caption, font, colour, align="right",
               width_mm=label_room)
        r.text(col_amount, y, billing.format_rupees(paise), font, colour,
               align="right", width_mm=amount_room)
        y += 5.4

    money("Total", t.gross_paise)
    if t.discount_paise:
        caption = "Discount"
        if (data.discount_type or "").lower() == billing.DISCOUNT_PERCENT \
                and data.discount_value:
            caption += f" ({data.discount_value:g}%)"
        money(caption, -t.discount_paise)

    # Clear space for the rule rather than drawing it back over the row above:
    # money() leaves y at the centre of the next line, and a text box is taller
    # than the gap, so a rule at y - 2 struck straight through the discount.
    y += 1.4
    r.line(label_x, y, PAGE_W - MARGIN_R, 0.3)
    y += 3.4
    money("Net payable", t.net_paise, bold=True, colour=accent)

    for p in data.payments:
        when = (p.when or "").split(" ")[0]
        money(f"Paid ({p.mode}{' ' + when if when else ''})", p.amount_paise)
    if not data.payments:
        money("Paid", 0)

    balance_colour = QColor("#B3261E") if t.balance_paise > 0 else BLACK
    money("Balance due" if t.balance_paise > 0 else "Balance",
          t.balance_paise, bold=True, colour=balance_colour)

    y += 1.0
    r.text(MARGIN_L, y, billing.amount_in_words(t.net_paise),
           r.font(SERIF, 9.5, italic=True), GREY, width_mm=w)
    y += 6.0

    if t.balance_paise > 0:
        r.text(MARGIN_L, y, "Balance to be settled before the report is issued.",
               r.font(SERIF, 9.5), QColor("#B3261E"))
    elif t.net_paise:
        r.text(MARGIN_L, y, "Paid in full. Thank you.", r.font(SERIF, 9.5), GREY)

    # ---- foot -------------------------------------------------------------
    base = PAGE_H - MARGIN_B - 20
    r.line(MARGIN_L, base, PAGE_W - MARGIN_R, 0.3, QColor("#BBBBBB"))
    small = r.font(SANS, 7)
    made = f"Prepared by {data.made_by}" if data.made_by else ""
    r.text(MARGIN_L, base + 4.5,
           "This is a computer-generated receipt." + ("   " + made if made else ""),
           small, GREY)
    r.text(MARGIN_L, base + 9.0,
           "Charges once paid are not refundable after the test has been run.",
           small, GREY)

    sig_w = 60.0
    sig_x = PAGE_W - MARGIN_R - sig_w
    r.line(sig_x, base + 12.0, PAGE_W - MARGIN_R, 0.3, QColor("#999999"))
    r.text(sig_x, base + 15.5, "Authorised signatory", small, GREY,
           align="right", width_mm=sig_w)


# --------------------------------------------------------------------------
# Output devices
# --------------------------------------------------------------------------

def write_pdf(data: BillData, path: Path, dpi: int = 300,
              with_header: bool = True) -> Path:
    _require_qt_application()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")

    writer = QPdfWriter(str(tmp))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setResolution(dpi)
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    writer.setTitle(f"Bill {data.bill_no}")
    writer.setCreator("LabSoft")

    painter = QPainter()
    if not painter.begin(writer):
        raise RuntimeError(f"Could not start writing the bill at {tmp}")
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        paint_bill(painter, data, dpi / 25.4, with_header=with_header)
    finally:
        painter.end()

    if path.exists():
        path.unlink()
    tmp.replace(path)
    return path


def render_pages(data: BillData, width_px: int = 900,
                 with_header: bool = True) -> List[QImage]:
    """The receipt as one image, for the on-screen preview."""
    _require_qt_application()

    dpmm = width_px / PAGE_W
    image = QImage(width_px, int(round(PAGE_H * dpmm)), QImage.Format.Format_RGB32)
    image.fill(0xFFFFFFFF)
    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        paint_bill(painter, data, dpmm, with_header=with_header)
    finally:
        painter.end()
    return [image]


def print_bill(data: BillData, printer, with_header: Optional[bool] = None) -> None:
    if with_header is None:
        with_header = data.flag_on("print_header")
    painter = QPainter()
    if not painter.begin(printer):
        raise RuntimeError("The printer could not be opened.")
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        paint_bill(painter, data, printer.resolution() / 25.4,
                   with_header=with_header)
    finally:
        painter.end()


# ==========================================================================
# The 80mm counter slip
# ==========================================================================
#
# A different document from the A4 bill above, not a shrunk copy of it. A
# thermal roll is 80mm wide with about 72mm of printable paper, has no colour,
# and is cut to whatever length the content needs rather than to a page.
#
# The slip this replaces was built as HTML in the preview dialog, with the
# figures read from columns the bills table does not have and the colours
# hardcoded to black -- so it printed the wrong totals in the daylight theme
# and was invisible in the night one. There is one renderer now, and what the
# preview shows is what the printer is handed.

SLIP_W = 80.0                  # the paper
SLIP_MARGIN = 4.0              # unprintable edge on a typical 80mm head
SLIP_LH = 4.2                  # a line of body text
SLIP_MONO = "Consolas"         # falls back through the style hint below


def _slip_content_w() -> float:
    return SLIP_W - 2 * SLIP_MARGIN


class _Slip:
    """A tiny painter for the roll. Millimetres in, device units out."""

    def __init__(self, painter: QPainter, dpmm: float):
        self.p = painter
        self.k = dpmm
        self.y = SLIP_MARGIN

    def font(self, size_pt: float, bold: bool = False):
        from PyQt6.QtGui import QFont

        f = QFont(SLIP_MONO)
        f.setPointSizeF(size_pt)
        f.setBold(bold)
        # Fixed pitch: a column of rupees on a receipt has to line up, and a
        # proportional face on a 72mm roll never does.
        f.setStyleHint(QFont.StyleHint.TypeWriter)
        f.setFixedPitch(True)
        return f

    def _metrics(self, font):
        from PyQt6.QtGui import QFontMetricsF

        return QFontMetricsF(font, self.p.device())

    def fit(self, s: str, font, width_mm: float) -> str:
        if not s:
            return ""
        return self._metrics(font).elidedText(
            s, Qt.TextElideMode.ElideRight, int(max(0.0, width_mm) * self.k))

    def line_of(self, s: str, font, align: str = "left",
                x: float = None, width: float = None,
                colour: QColor = BLACK, advance: float = None) -> None:
        from PyQt6.QtGui import QPen

        x = SLIP_MARGIN if x is None else x
        width = _slip_content_w() if width is None else width
        self.p.setFont(font)
        self.p.setPen(QPen(colour))
        h = self._metrics(font).height() / self.k
        flag = {"left": Qt.AlignmentFlag.AlignLeft,
                "center": Qt.AlignmentFlag.AlignHCenter,
                "right": Qt.AlignmentFlag.AlignRight}[align]
        self.p.drawText(
            QRectF(x * self.k, self.y * self.k, width * self.k, h * 1.5 * self.k),
            int(flag | Qt.AlignmentFlag.AlignVCenter), s)
        self.y += advance if advance is not None else h * 1.25

    def pair(self, left: str, right: str, font, bold_right: bool = False,
             right_font=None) -> None:
        """A caption on the left and a figure hard against the right edge."""
        rf = right_font or font
        w = _slip_content_w()
        self.p.setFont(font)
        h = self._metrics(font).height() / self.k
        self.line_of(self.fit(left, font, w * 0.62), font, advance=0)
        self.line_of(right, rf, align="right", advance=h * 1.25)

    def rule(self, dashed: bool = True) -> None:
        from PyQt6.QtGui import QPen

        pen = QPen(BLACK)
        pen.setWidthF(max(1.0, 0.25 * self.k))
        if dashed:
            pen.setDashPattern([3, 3])
        self.p.setPen(pen)
        # Set clear of the line above it: at 0.8mm the rule was printing
        # through the descenders of the row before it.
        y = (self.y + 1.6) * self.k
        self.p.drawLine(int(SLIP_MARGIN * self.k), int(y),
                        int((SLIP_W - SLIP_MARGIN) * self.k), int(y))
        self.y += 4.0

    def gap(self, mm: float = 1.6) -> None:
        self.y += mm


def paint_slip(painter: QPainter, data: BillData, dpmm: float) -> float:
    """Draw the counter slip. Returns the height used, in millimetres."""
    s = _Slip(painter, dpmm)
    totals = data.totals()

    name = f"{data.setting('lab_name_prefix')} {data.setting('lab_name')}".strip()
    s.line_of(s.fit(name or "Laboratory", s.font(11, bold=True), _slip_content_w()),
              s.font(11, bold=True), align="center")
    for extra in (data.setting("lab_address_1"), data.setting("lab_address_2"),
                  data.setting("lab_phone")):
        if extra.strip():
            s.line_of(s.fit(extra.strip(), s.font(7), _slip_content_w()),
                      s.font(7), align="center")
    s.gap(1.0)
    # No "TAX INVOICE". This laboratory does not issue one, and printing the
    # words on a slip that carries no tax number is a claim it cannot support.
    s.line_of("CASH RECEIPT", s.font(9, bold=True), align="center")
    s.rule()

    body = s.font(8)
    bodyb = s.font(8, bold=True)
    s.pair("Bill no", data.bill_no, body, right_font=bodyb)
    s.pair("Date", data.date_text, body)
    s.pair("Patient", s.fit(data.name, bodyb, _slip_content_w() * 0.55), body,
           right_font=bodyb)
    who = " / ".join(x for x in (data.sex, data.age) if x)
    if who:
        s.pair("Sex / Age", who, body)
    if (data.referred_by or "").strip():
        s.pair("Ref. by", s.fit(data.referred_by, body, _slip_content_w() * 0.55),
               body)
    s.rule()

    s.pair("Item", "Amount", bodyb)
    s.rule()
    for item in data.lines:
        label = item.label if item.qty <= 1 else f"{item.label} x{item.qty}"
        s.pair(s.fit(label, body, _slip_content_w() * 0.62),
               billing.format_rupees(item.amount_paise, symbol=False), body)
    s.rule()

    s.pair("Gross", billing.format_rupees(totals.gross_paise, symbol=False), body)
    if totals.discount_paise:
        s.pair("Discount",
               "-" + billing.format_rupees(totals.discount_paise, symbol=False), body)
    s.pair("NET PAYABLE",
           billing.format_rupees(totals.net_paise, symbol=False),
           s.font(9.5, bold=True))
    s.pair("Paid", billing.format_rupees(totals.paid_paise, symbol=False), body)
    s.pair("Balance", billing.format_rupees(totals.balance_paise, symbol=False),
           bodyb)
    s.rule()

    for pay in data.payments:
        s.line_of(f"{billing.format_rupees(pay.amount_paise, symbol=False)}"
                  f"  {(pay.mode or 'cash').title()}"
                  f"  {(pay.when or '')[:16]}", s.font(7))
    if data.payments:
        s.gap(0.8)

    if data.made_by:
        s.line_of(f"Billed by {data.made_by}", s.font(7), align="center")
    s.line_of("Thank you, and keep well.", s.font(8), align="center")
    s.gap(6.0)                      # room for the cutter
    return s.y


def slip_height_mm(data: BillData, dpmm: float = 12.0) -> float:
    """How long the roll has to be. Measured by painting it and throwing it away."""
    _require_qt_application()

    probe = QImage(int(SLIP_W * dpmm), int(600 * dpmm), QImage.Format.Format_RGB32)
    probe.fill(0xFFFFFFFF)
    painter = QPainter(probe)
    try:
        return paint_slip(painter, data, dpmm)
    finally:
        painter.end()


def render_slip(data: BillData, width_px: int = 420) -> QImage:
    """The slip as one image, at the width the preview shows it."""
    _require_qt_application()

    dpmm = width_px / SLIP_W
    height = slip_height_mm(data, dpmm)
    image = QImage(width_px, int(round(height * dpmm)), QImage.Format.Format_RGB32)
    image.fill(0xFFFFFFFF)
    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        paint_slip(painter, data, dpmm)
    finally:
        painter.end()
    return image


def print_slip(data: BillData, printer) -> None:
    """Send the slip to a thermal printer at its own resolution."""
    dpmm = printer.resolution() / 25.4
    painter = QPainter()
    if not painter.begin(printer):
        raise RuntimeError("The printer could not be opened.")
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        paint_slip(painter, data, dpmm)
    finally:
        painter.end()


def write_slip_pdf(data: BillData, path: Path, dpi: int = 300) -> Path:
    """The slip as a PDF on 80mm paper, for a lab with no thermal printer."""
    _require_qt_application()

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    height = max(60.0, slip_height_mm(data))
    writer = QPdfWriter(str(path))
    writer.setResolution(dpi)
    writer.setPageSize(QPageSize(QSizeF(SLIP_W, height), QPageSize.Unit.Millimeter,
                                 "Slip", QPageSize.SizeMatchPolicy.ExactMatch))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    painter = QPainter(writer)
    try:
        paint_slip(painter, data, writer.resolution() / 25.4)
    finally:
        painter.end()
    return path
