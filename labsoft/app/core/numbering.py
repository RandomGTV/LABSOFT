"""Report number formatting and validation.

The lab's series is a plain incrementing integer (its current book is around
51358). Allocation itself happens inside the database transaction that creates
the job, so a crash between allocating and saving leaves a gap rather than a
duplicate. A gap is a curiosity; a duplicate report number is a real problem
when a result is later questioned.
"""

from __future__ import annotations

import re
from typing import Optional

__all__ = ["normalise", "next_number", "format_number", "is_valid", "with_revision"]

_NUM_RE = re.compile(r"^\s*(\d{1,12})\s*$")


def is_valid(value) -> bool:
    return normalise(value) is not None


def normalise(value) -> Optional[int]:
    """Accept an int or a typed string; return the integer, or None."""
    if value is None:
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    m = _NUM_RE.match(str(value))
    if not m:
        return None
    n = int(m.group(1))
    return n if n > 0 else None


def next_number(current: Optional[int]) -> int:
    n = normalise(current)
    return 1 if n is None else n + 1


def format_number(value, prefix: str = "", width: int = 0) -> str:
    """Printed form. Default is the bare number, matching the lab's report."""
    n = normalise(value)
    if n is None:
        return ""
    body = str(n).zfill(max(0, int(width or 0)))
    return f"{prefix}{body}"


def with_revision(report_no, revision: int) -> str:
    """Revision 1 prints plainly; later revisions are marked."""
    base = format_number(report_no)
    try:
        r = int(revision or 1)
    except (TypeError, ValueError):
        r = 1
    return base if r <= 1 else f"{base} / R{r}"
