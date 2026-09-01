"""Safe formula evaluation for derived test results.

Formulas are written using test codes, e.g.:
    TP - ALB
    TC - HDL - TG/5
    round((A + B) / 2, 1)

This module deliberately does NOT use eval() or exec(). Expressions are
tokenised and parsed into an AST by hand, and only the node types listed
below can ever be produced. There is no way to reach attributes, imports,
function calls beyond the whitelist, or any Python object.

Public API
----------
parse(text)                  -> Expr        (raises FormulaError)
codes_used(text)             -> set[str]
evaluate(text, values)       -> float | None
resolve_job(tests, values)   -> dict[code, float|None]
check_cycles(tests)          -> list[list[str]]   (empty when clean)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set

__all__ = [
    "FormulaError",
    "parse",
    "codes_used",
    "evaluate",
    "resolve_job",
    "check_cycles",
    "describe",
    "FUNCTIONS",
]


class FormulaError(ValueError):
    """Raised for any malformed formula. Message names the problem and position."""

    def __init__(self, message: str, position: int | None = None):
        self.position = position
        if position is not None:
            message = f"{message} (at character {position + 1})"
        super().__init__(message)


# --------------------------------------------------------------------------
# Whitelisted functions. Nothing else is callable, ever.
# --------------------------------------------------------------------------

def _fn_round(x: float, digits: float = 0) -> float:
    return round(x, int(digits))


def _fn_log(x: float) -> float:
    import math

    if x <= 0:
        raise FormulaError("log() needs a value greater than zero")
    return math.log10(x)


def _fn_ln(x: float) -> float:
    import math

    if x <= 0:
        raise FormulaError("ln() needs a value greater than zero")
    return math.log(x)


def _fn_sqrt(x: float) -> float:
    import math

    if x < 0:
        raise FormulaError("sqrt() needs a value of zero or more")
    return math.sqrt(x)


FUNCTIONS: Dict[str, tuple[Callable[..., float], int, int]] = {
    # name: (implementation, min args, max args)
    "round": (_fn_round, 1, 2),
    "min": (lambda *a: min(a), 2, 8),
    "max": (lambda *a: max(a), 2, 8),
    "abs": (lambda x: abs(x), 1, 1),
    "sqrt": (_fn_sqrt, 1, 1),
    "log": (_fn_log, 1, 1),
    "ln": (_fn_ln, 1, 1),
}


# --------------------------------------------------------------------------
# Tokeniser
# --------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r"""
    (?P<space>\s+)
  | (?P<number>\d+\.\d+|\d+\.(?!\.)|\.\d+|\d+)
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>\*\*|[+\-*/()^,])
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class _Tok:
    kind: str
    text: str
    pos: int


def _tokenise(text: str) -> List[_Tok]:
    toks: List[_Tok] = []
    i = 0
    n = len(text)
    while i < n:
        m = _TOKEN_RE.match(text, i)
        if not m:
            raise FormulaError(f"I don't understand the character {text[i]!r}", i)
        kind = m.lastgroup
        assert kind is not None
        if kind != "space":
            toks.append(_Tok(kind, m.group(), i))
        i = m.end()
    return toks


# --------------------------------------------------------------------------
# AST
# --------------------------------------------------------------------------

class Expr:
    """Base class. Only the four subclasses below can ever be constructed."""

    def eval(self, values: Dict[str, Optional[float]]) -> Optional[float]:
        raise NotImplementedError

    def codes(self) -> Set[str]:
        raise NotImplementedError

    def text(self) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class Num(Expr):
    value: float

    def eval(self, values):
        return self.value

    def codes(self):
        return set()

    def text(self):
        v = self.value
        return str(int(v)) if v == int(v) else str(v)


@dataclass(frozen=True)
class Code(Expr):
    name: str

    def eval(self, values):
        # A missing or blank input yields None, which propagates upward so the
        # derived test stays blank. Substituting 0 here would print a wrong
        # number on a medical report, which is worse than printing nothing.
        return values.get(self.name)

    def codes(self):
        return {self.name}

    def text(self):
        return self.name


@dataclass(frozen=True)
class BinOp(Expr):
    op: str
    left: Expr
    right: Expr

    def eval(self, values):
        a = self.left.eval(values)
        b = self.right.eval(values)
        if a is None or b is None:
            return None
        if self.op == "+":
            return a + b
        if self.op == "-":
            return a - b
        if self.op == "*":
            return a * b
        if self.op == "/":
            if b == 0:
                raise FormulaError("division by zero")
            return a / b
        if self.op == "^":
            # A negative base with a fractional exponent gives a complex number
            # in Python, which is not a result and used to crash the whole
            # calculation pass, taking the operator's other typed values with it.
            if a < 0 and b != int(b):
                raise FormulaError(
                    "a negative value cannot be raised to a fractional power")
            try:
                out = float(a) ** float(b)
            except (OverflowError, ValueError, ZeroDivisionError):
                raise FormulaError("the power calculation produced a number too large")
            if isinstance(out, complex) or out != out or out in (float("inf"), float("-inf")):
                raise FormulaError("the power calculation did not give a usable number")
            return out
        raise FormulaError(f"unknown operator {self.op!r}")

    def codes(self):
        return self.left.codes() | self.right.codes()

    def text(self):
        return f"({self.left.text()} {self.op} {self.right.text()})"


@dataclass(frozen=True)
class Neg(Expr):
    operand: Expr

    def eval(self, values):
        v = self.operand.eval(values)
        return None if v is None else -v

    def codes(self):
        return self.operand.codes()

    def text(self):
        return f"-{self.operand.text()}"


@dataclass(frozen=True)
class Call(Expr):
    name: str
    args: tuple

    def eval(self, values):
        vals = [a.eval(values) for a in self.args]
        if any(v is None for v in vals):
            return None
        fn, _lo, _hi = FUNCTIONS[self.name]
        try:
            return float(fn(*vals))
        except FormulaError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise FormulaError(f"{self.name}() failed: {exc}")

    def codes(self):
        out: Set[str] = set()
        for a in self.args:
            out |= a.codes()
        return out

    def text(self):
        return f"{self.name}({', '.join(a.text() for a in self.args)})"


# --------------------------------------------------------------------------
# Recursive-descent parser
#
#   expression := term (('+' | '-') term)*
#   term       := power (('*' | '/') power)*
#   power      := unary ('^' power)?          right-associative
#   unary      := ('-' | '+') unary | primary
#   primary    := NUMBER | NAME '(' args ')' | NAME | '(' expression ')'
# --------------------------------------------------------------------------

class _Parser:
    def __init__(self, toks: Sequence[_Tok], source: str):
        self.toks = toks
        self.source = source
        self.i = 0

    # -- helpers ---------------------------------------------------------
    def peek(self) -> Optional[_Tok]:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def next(self) -> _Tok:
        t = self.peek()
        if t is None:
            raise FormulaError("the formula ends unexpectedly", len(self.source))
        self.i += 1
        return t

    def accept(self, *texts: str) -> Optional[_Tok]:
        t = self.peek()
        if t is not None and t.text in texts:
            self.i += 1
            return t
        return None

    def expect(self, text: str) -> _Tok:
        t = self.accept(text)
        if t is None:
            cur = self.peek()
            pos = cur.pos if cur else len(self.source)
            found = repr(cur.text) if cur else "the end of the formula"
            raise FormulaError(f"expected {text!r} but found {found}", pos)
        return t

    # -- grammar ---------------------------------------------------------
    def parse(self) -> Expr:
        if not self.toks:
            raise FormulaError("the formula is empty")
        node = self.expression()
        left = self.peek()
        if left is not None:
            raise FormulaError(f"unexpected {left.text!r} after the formula", left.pos)
        return node

    def expression(self) -> Expr:
        node = self.term()
        while True:
            t = self.accept("+", "-")
            if t is None:
                return node
            node = BinOp(t.text, node, self.term())

    def term(self) -> Expr:
        node = self.power()
        while True:
            t = self.accept("*", "/")
            if t is None:
                return node
            node = BinOp(t.text, node, self.power())

    def power(self) -> Expr:
        node = self.unary()
        t = self.accept("^", "**")
        if t is None:
            return node
        return BinOp("^", node, self.power())  # right-associative

    def unary(self) -> Expr:
        t = self.accept("-", "+")
        if t is None:
            return self.primary()
        inner = self.unary()
        return Neg(inner) if t.text == "-" else inner

    def primary(self) -> Expr:
        t = self.next()
        if t.kind == "number":
            try:
                return Num(float(t.text))
            except ValueError:
                raise FormulaError(f"{t.text!r} is not a valid number", t.pos)
        if t.kind == "name":
            lname = t.text.lower()
            if self.peek() is not None and self.peek().text == "(":
                if lname not in FUNCTIONS:
                    allowed = ", ".join(sorted(FUNCTIONS))
                    raise FormulaError(
                        f"{t.text}() is not an allowed function. Allowed: {allowed}", t.pos
                    )
                self.expect("(")
                args: List[Expr] = []
                if self.peek() is None or self.peek().text != ")":
                    args.append(self.expression())
                    while self.accept(","):
                        args.append(self.expression())
                self.expect(")")
                _fn, lo, hi = FUNCTIONS[lname]
                if not (lo <= len(args) <= hi):
                    want = f"{lo}" if lo == hi else f"{lo} to {hi}"
                    raise FormulaError(
                        f"{lname}() takes {want} value(s), got {len(args)}", t.pos
                    )
                return Call(lname, tuple(args))
            return Code(t.text.upper())
        if t.text == "(":
            node = self.expression()
            self.expect(")")
            return node
        raise FormulaError(f"unexpected {t.text!r}", t.pos)


# --------------------------------------------------------------------------
# Public functions
# --------------------------------------------------------------------------

def parse(text: str) -> Expr:
    """Parse a formula. Raises FormulaError with a readable message."""
    if text is None:
        raise FormulaError("the formula is empty")
    stripped = text.strip()
    if not stripped:
        raise FormulaError("the formula is empty")
    if len(stripped) > 500:
        raise FormulaError("the formula is too long (limit 500 characters)")
    return _Parser(_tokenise(stripped), stripped).parse()


def codes_used(text: str) -> Set[str]:
    """The set of test codes a formula depends on."""
    return parse(text).codes()


def describe(text: str) -> str:
    """Fully-parenthesised rendering, used to show the operator precedence."""
    return parse(text).text()


def evaluate(text: str, values: Dict[str, Optional[float]]) -> Optional[float]:
    """Evaluate a formula. Returns None if any input it needs is blank."""
    normalised = {str(k).upper(): v for k, v in values.items()}
    return parse(text).eval(normalised)


# --------------------------------------------------------------------------
# Whole-job resolution
# --------------------------------------------------------------------------

def _dependency_order(
    formulas: Dict[str, str]
) -> tuple[List[str], List[List[str]]]:
    """Kahn topological sort. Returns (order, cycles)."""
    deps: Dict[str, Set[str]] = {}
    for code, f in formulas.items():
        try:
            deps[code] = {c for c in codes_used(f) if c in formulas and c != code}
        except FormulaError:
            deps[code] = set()

    order: List[str] = []
    remaining = dict(deps)
    while remaining:
        ready = sorted(c for c, d in remaining.items() if not (d & set(remaining)))
        if not ready:
            break
        order.extend(ready)
        for c in ready:
            remaining.pop(c)

    cycles: List[List[str]] = []
    if remaining:
        seen: Set[str] = set()
        for start in sorted(remaining):
            if start in seen:
                continue
            path: List[str] = []
            node = start
            local: Set[str] = set()
            while node is not None and node not in local:
                local.add(node)
                path.append(node)
                nxt = sorted(d for d in remaining.get(node, set()) if d in remaining)
                node = nxt[0] if nxt else None
            if node is not None:
                cycle = path[path.index(node):]
                cycles.append(cycle)
            seen |= local
    return order, cycles


def check_cycles(formulas: Dict[str, str]) -> List[List[str]]:
    """Return circular dependency chains. Empty list means the set is clean.

    Called when a formula is SAVED in the Tests master, so a cycle is rejected
    at that moment rather than discovered during result entry.
    """
    single = [[c] for c, f in formulas.items() if c in codes_used_safe(f)]
    _order, cycles = _dependency_order(formulas)
    return single + cycles


def codes_used_safe(text: str) -> Set[str]:
    try:
        return codes_used(text)
    except FormulaError:
        return set()


@dataclass
class DerivedResult:
    code: str
    value: Optional[float]
    error: Optional[str] = None


def resolve_job(
    formulas: Dict[str, str],
    measured: Dict[str, Optional[float]],
) -> Dict[str, DerivedResult]:
    """Compute every derived test on a job, in dependency order.

    formulas -- {test_code: formula_text} for the derived tests on this job
    measured -- {test_code: value_or_None} for the directly-entered tests

    A test whose formula fails gets value=None and a readable error, so one
    bad formula never prevents the rest of the report from being produced.
    """
    values: Dict[str, Optional[float]] = {
        str(k).upper(): v for k, v in measured.items()
    }
    out: Dict[str, DerivedResult] = {}
    order, cycles = _dependency_order(formulas)

    in_cycle: Set[str] = {c for cyc in cycles for c in cyc}
    for code in formulas:
        if code in in_cycle:
            out[code] = DerivedResult(code, None, "circular reference between formulas")
            values[code] = None

    for code in order:
        if code in in_cycle:
            continue
        try:
            v = evaluate(formulas[code], values)
            values[code] = v
            out[code] = DerivedResult(code, v)
        except FormulaError as exc:
            values[code] = None
            out[code] = DerivedResult(code, None, str(exc))

    for code in formulas:
        if code not in out:
            out[code] = DerivedResult(code, None, "could not be calculated")
    return out
