"""Billing arithmetic.

Every amount in this module is an integer number of PAISE. Rupees are floats,
and floats do not add up: 0.1 + 0.2 is not 0.3, so a day's takings computed in
float rupees drifts and a dues list stops reconciling. Money is converted to
rupees only at the moment it is displayed or printed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable, List, Optional, Sequence

__all__ = [
    "to_paise", "to_rupees", "format_rupees", "amount_in_words",
    "LineItem", "Payment", "BillTotals",
    "compute_totals", "commission_for", "DISCOUNT_PERCENT", "DISCOUNT_FLAT",
]

DISCOUNT_PERCENT = "percent"
DISCOUNT_FLAT = "flat"


def to_paise(rupees) -> int:
    """Convert a rupee amount (number or typed string) to whole paise.

    Conversion goes through Decimal, not float. Typing 1.005 into a rate box
    must become 101 paise, but float(1.005) is really 1.00499999999999989, so
    multiplying by 100 and rounding gives 100 -- a paisa lost on every such
    rate, which compounds across a month of bills.
    """
    if rupees is None or rupees == "":
        return 0
    if isinstance(rupees, int) and not isinstance(rupees, bool):
        return rupees * 100
    if isinstance(rupees, float):
        # repr() of a float gives the shortest string that round-trips, which
        # is the number the operator actually typed.
        d = Decimal(repr(rupees))
    else:
        s = str(rupees).strip().replace(",", "").replace("₹", "").replace(" ", "")
        if not s:
            return 0
        try:
            d = Decimal(s)
        except (InvalidOperation, ValueError):
            return 0
    try:
        return int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, OverflowError, ValueError):
        return 0


def to_rupees(paise: int) -> float:
    return round(int(paise) / 100.0, 2)


def format_rupees(paise: int, symbol: bool = True) -> str:
    """Indian grouping: 1,84,300.00 rather than 184,300.00."""
    neg = paise < 0
    p = abs(int(paise))
    whole, frac = divmod(p, 100)
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    out = f"{s}.{frac:02d}"
    if symbol:
        out = "₹" + out
    if neg:
        out = "-" + out
    return out


_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
         "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
         "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
         "Eighty", "Ninety"]


def _two_digits(n: int) -> str:
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (" " + _ONES[ones] if ones else "")


def _three_digits(n: int) -> str:
    hundreds, rest = divmod(n, 100)
    parts = []
    if hundreds:
        parts.append(_ONES[hundreds] + " Hundred")
    if rest:
        parts.append(_two_digits(rest))
    return " ".join(parts)


def amount_in_words(paise: int) -> str:
    """The rupee amount written out, Indian style, for a receipt.

    Lakh and crore, not million: a receipt that reads "one million rupees" is
    not a receipt anyone here would accept. Paise are named separately because
    rounding them into the rupees would make the words disagree with the
    figure printed beside them.
    """
    paise = int(paise)
    sign = "Minus " if paise < 0 else ""
    rupees, sub = divmod(abs(paise), 100)

    if rupees == 0:
        words = "Zero"
    else:
        crore, rest = divmod(rupees, 10_000_000)
        lakh, rest = divmod(rest, 100_000)
        thousand, rest = divmod(rest, 1_000)
        chunks = []
        if crore:
            chunks.append(_three_digits(crore) + " Crore")
        if lakh:
            chunks.append(_three_digits(lakh) + " Lakh")
        if thousand:
            chunks.append(_three_digits(thousand) + " Thousand")
        if rest:
            chunks.append(_three_digits(rest))
        words = " ".join(chunks)

    out = f"{sign}Rupees {words}"
    if sub:
        out += f" and {_two_digits(sub)} Paise"
    return out + " only"


@dataclass
class LineItem:
    label: str
    rate_paise: int
    qty: int = 1
    test_id: Optional[int] = None
    panel_id: Optional[int] = None

    @property
    def amount_paise(self) -> int:
        return int(self.rate_paise) * max(1, int(self.qty))


@dataclass
class Payment:
    amount_paise: int
    mode: str = "cash"
    note: str = ""


@dataclass
class BillTotals:
    gross_paise: int = 0
    discount_paise: int = 0
    net_paise: int = 0
    paid_paise: int = 0
    balance_paise: int = 0

    @property
    def is_paid(self) -> bool:
        return self.balance_paise <= 0

    @property
    def is_overpaid(self) -> bool:
        return self.balance_paise < 0


def compute_totals(
    items: Sequence[LineItem],
    discount_type: str = DISCOUNT_PERCENT,
    discount_value: float = 0.0,
    payments: Sequence[Payment] = (),
) -> BillTotals:
    """Gross, discount, net, paid and balance for one bill.

    A percentage discount is applied to the gross and rounded to whole paise.
    Both discount types are clamped so a bill can never go negative and a
    mistyped 1000% discount cannot turn into money owed to the patient.
    """
    gross = sum(li.amount_paise for li in items)

    dt = (discount_type or DISCOUNT_PERCENT).strip().lower()
    if dt == DISCOUNT_FLAT:
        discount = to_paise(discount_value)
    else:
        discount = _percent_of(gross, discount_value)

    discount = max(0, min(discount, gross))
    net = gross - discount
    paid = sum(int(p.amount_paise) for p in payments)

    return BillTotals(
        gross_paise=gross,
        discount_paise=discount,
        net_paise=net,
        paid_paise=paid,
        balance_paise=net - paid,
    )


def commission_for(net_paise: int, percent: float) -> int:
    """Referring doctor's share of the net bill, in paise."""
    return _percent_of(max(0, int(net_paise)), percent)


def _percent_of(base_paise: int, percent) -> int:
    """A clamped percentage of a paise amount, rounded half up, as an integer.

    Percentages outside 0-100 are clamped rather than rejected, so a mistyped
    figure produces a sane bill instead of a negative one.
    """
    try:
        pct = Decimal(str(percent if percent not in (None, "") else 0))
    except (InvalidOperation, ValueError):
        return 0
    pct = max(Decimal(0), min(Decimal(100), pct))
    try:
        return int(
            (Decimal(int(base_paise)) * pct / Decimal(100)).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
    except (InvalidOperation, OverflowError, ValueError):
        return 0
