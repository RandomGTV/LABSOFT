"""Reference-range matching and abnormal-value flagging.

A test may carry several reference rows, chosen by the patient's sex and age.
Four rule shapes cover everything a pathology report needs:

    range   70 - 110      abnormal below low or above high
    max     < 200         abnormal above high
    min     > 40          abnormal below low
    text    Negative      abnormal when the result differs

Flags
    N  normal
    H  high
    L  low
    A  abnormal / unassessed  (no matching range, or a text mismatch)

The flag is shown on the entry screen in colour as a typing safeguard. Whether
it prints is a separate setting, currently off, because the lab's report shows
plain values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable, List, Optional, Sequence

__all__ = [
    "RULE_RANGE", "RULE_MAX", "RULE_MIN", "RULE_TEXT",
    "FLAG_NORMAL", "FLAG_HIGH", "FLAG_LOW", "FLAG_ABNORMAL", "FLAG_NONE",
    "ReferenceRange", "select_range", "flag_for", "flag_label",
    "age_in_years", "format_value", "default_display",
]

RULE_RANGE = "range"
RULE_MAX = "max"
RULE_MIN = "min"
RULE_TEXT = "text"

FLAG_NORMAL = "N"
FLAG_HIGH = "H"
FLAG_LOW = "L"
FLAG_ABNORMAL = "A"
FLAG_NONE = ""

_LABELS = {
    FLAG_NORMAL: "Normal",
    FLAG_HIGH: "High",
    FLAG_LOW: "Low",
    FLAG_ABNORMAL: "Check",
    FLAG_NONE: "",
}

# Age units accepted anywhere in the program.
_UNIT_YEARS = {"y", "yr", "yrs", "year", "years"}
_UNIT_MONTHS = {"m", "mo", "mon", "month", "months"}
_UNIT_DAYS = {"d", "day", "days"}


def age_in_years(value: Optional[float], unit: str) -> Optional[float]:
    """Normalise an age to years so ranges can be compared consistently."""
    if value is None:
        return None
    u = (unit or "years").strip().lower()
    if u in _UNIT_MONTHS:
        return float(value) / 12.0
    if u in _UNIT_DAYS:
        return float(value) / 365.25
    if u in _UNIT_YEARS:
        return float(value)
    return float(value)


@dataclass
class ReferenceRange:
    """One reference row for a test."""

    rule_type: str = RULE_RANGE
    low: Optional[float] = None
    high: Optional[float] = None
    text_value: Optional[str] = None
    sex: str = "any"          # 'M', 'F' or 'any'
    age_min: Optional[float] = None   # years, inclusive
    age_max: Optional[float] = None   # years, exclusive
    display_text: str = ""    # exactly what prints in the Normal Value column
    note: str = ""

    # -- matching ------------------------------------------------------
    def matches(self, sex: Optional[str], age_years: Optional[float]) -> bool:
        s = (self.sex or "any").strip().lower()
        if s not in ("any", ""):
            given = (sex or "").strip().lower()
            given = "m" if given.startswith("m") else "f" if given.startswith("f") else ""
            if given != s[0]:
                return False
        if self.age_min is not None or self.age_max is not None:
            if age_years is None:
                return False
            if self.age_min is not None and age_years < self.age_min:
                return False
            if self.age_max is not None and age_years >= self.age_max:
                return False
        return True

    def specificity(self) -> int:
        """Higher wins when several rows match. Narrower rows are preferred."""
        score = 0
        if (self.sex or "any").strip().lower() not in ("any", ""):
            score += 2
        if self.age_min is not None:
            score += 1
        if self.age_max is not None:
            score += 1
        return score

    # -- evaluation ----------------------------------------------------
    def flag(self, value) -> str:
        rt = (self.rule_type or RULE_RANGE).strip().lower()

        if rt == RULE_TEXT:
            if value is None or str(value).strip() == "":
                return FLAG_NONE
            expected = (self.text_value or "").strip().lower()
            if not expected:
                return FLAG_ABNORMAL
            got = str(value).strip().lower()
            return FLAG_NORMAL if got == expected else FLAG_ABNORMAL

        num = _as_number(value)
        if num is None:
            return FLAG_NONE

        if rt == RULE_MAX:
            if self.high is None:
                return FLAG_ABNORMAL
            return FLAG_HIGH if num > self.high else FLAG_NORMAL

        if rt == RULE_MIN:
            if self.low is None:
                return FLAG_ABNORMAL
            return FLAG_LOW if num < self.low else FLAG_NORMAL

        # RULE_RANGE
        if self.low is None and self.high is None:
            return FLAG_ABNORMAL
        if self.low is not None and num < self.low:
            return FLAG_LOW
        if self.high is not None and num > self.high:
            return FLAG_HIGH
        return FLAG_NORMAL

    def printed_text(self, unit: str = "") -> str:
        """What goes in the Normal Value column."""
        if self.display_text:
            return self.display_text
        return default_display(self, unit)


def default_display(rng: "ReferenceRange", unit: str = "") -> str:
    """Assemble a Normal Value string when the lab has not written one."""
    u = unit or ""
    rt = (rng.rule_type or RULE_RANGE).strip().lower()
    if rt == RULE_TEXT:
        return rng.text_value or ""
    if rt == RULE_MAX:
        return f"< {_num(rng.high)}{u}" if rng.high is not None else ""
    if rt == RULE_MIN:
        return f"> {_num(rng.low)}{u}" if rng.low is not None else ""
    if rng.low is not None and rng.high is not None:
        return f"{_num(rng.low)} - {_num(rng.high)}{u}"
    if rng.high is not None:
        return f"< {_num(rng.high)}{u}"
    if rng.low is not None:
        return f"> {_num(rng.low)}{u}"
    return ""


def select_range(
    ranges: Sequence[ReferenceRange],
    sex: Optional[str],
    age_years: Optional[float],
) -> Optional[ReferenceRange]:
    """Pick the most specific matching row, or None."""
    candidates = [r for r in ranges if r.matches(sex, age_years)]
    if not candidates:
        return None
    best = max(candidates, key=lambda r: r.specificity())
    return best


def flag_for(
    value,
    ranges: Sequence[ReferenceRange],
    sex: Optional[str] = None,
    age_years: Optional[float] = None,
) -> str:
    """Flag a result. No matching range yields 'A', never a false 'Normal'."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return FLAG_NONE
    rng = select_range(ranges, sex, age_years)
    if rng is None:
        return FLAG_ABNORMAL
    return rng.flag(value)


def flag_label(flag: str) -> str:
    return _LABELS.get(flag, "")


def format_value(value, decimals: int = 1) -> str:
    """Render a numeric result for display and printing.

    Rounds half UP, not half to even. Python's default formatting is banker's
    rounding, so a haemoglobin of 12.5 printed as "12" while 13.5 printed as
    "14" -- inconsistent, and not what anyone in a lab expects to see.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    try:
        d = max(0, int(decimals))
    except (TypeError, ValueError):
        d = 1
    try:
        quantum = Decimal(1).scaleb(-d)
        rounded = Decimal(repr(float(value))).quantize(quantum, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, OverflowError):
        return f"{float(value):.{d}f}"
    return f"{rounded:.{d}f}"


# -- internals -------------------------------------------------------------

def _as_number(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    # Results are sometimes typed as "<0.5" or ">1000"; compare on the number.
    if s[0] in "<>=":
        s = s[1:].strip()
    try:
        return float(s)
    except ValueError:
        return None


def _num(v: Optional[float]) -> str:
    if v is None:
        return ""
    f = float(v)
    return str(int(f)) if f == int(f) else f"{f:g}"
