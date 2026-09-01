import pytest

from app.core.formula import (
    FormulaError,
    check_cycles,
    codes_used,
    describe,
    evaluate,
    parse,
    resolve_job,
)


# ---------------------------------------------------------------- arithmetic

@pytest.mark.parametrize("expr,values,expected", [
    ("TP - ALB",              {"TP": 7.2, "ALB": 3.1},                    4.1),
    ("ALB / GLOB",            {"ALB": 3.1, "GLOB": 4.1},                  0.7560975609756098),
    ("TC - HDL - TG/5",       {"TC": 212, "HDL": 38, "TG": 180},          138.0),
    ("TC / HDL",              {"TC": 212, "HDL": 38},                     5.578947368421052),
    ("2 + 3 * 4",             {},                                          14.0),
    ("(2 + 3) * 4",           {},                                          20.0),
    ("10 - 2 - 3",            {},                                          5.0),   # left assoc
    ("100 / 10 / 2",          {},                                          5.0),   # left assoc
    ("2 ^ 3 ^ 2",             {},                                          512.0), # right assoc
    ("-5 + 8",                {},                                          3.0),
    ("--5",                   {},                                          5.0),
    ("A * -2",                {"A": 3},                                   -6.0),
    ("0.5 * X",               {"X": 8},                                    4.0),
    (".5 * X",                {"X": 8},                                    4.0),
])
def test_arithmetic(expr, values, expected):
    assert evaluate(expr, values) == pytest.approx(expected)


def test_case_insensitive_codes():
    assert evaluate("tp - alb", {"TP": 7.0, "ALB": 3.0}) == pytest.approx(4.0)
    assert evaluate("TP - ALB", {"tp": 7.0, "alb": 3.0}) == pytest.approx(4.0)


@pytest.mark.parametrize("expr,values,expected", [
    ("round(A/3, 2)",   {"A": 10},              3.33),
    ("round(A/3)",      {"A": 10},              3.0),
    ("min(A, B)",       {"A": 4, "B": 9},       4.0),
    ("max(A, B, C)",    {"A": 4, "B": 9, "C": 2}, 9.0),
    ("abs(A - B)",      {"A": 4, "B": 9},       5.0),
    ("sqrt(A)",         {"A": 16},              4.0),
    ("log(A)",          {"A": 100},             2.0),
])
def test_functions(expr, values, expected):
    assert evaluate(expr, values) == pytest.approx(expected)


# ------------------------------------------------------------ blank handling

def test_blank_input_yields_blank_not_zero():
    """The critical safety rule: a missing input must not become 0."""
    assert evaluate("TC - HDL - TG/5", {"TC": 212, "HDL": None, "TG": 180}) is None
    assert evaluate("TP - ALB", {"TP": 7.2}) is None
    assert evaluate("round(A, 1)", {"A": None}) is None
    assert evaluate("min(A, B)", {"A": 1, "B": None}) is None


def test_no_inputs_needed_still_evaluates():
    assert evaluate("2 * 3", {}) == 6.0


# ------------------------------------------------------------------ failures

def test_division_by_zero():
    with pytest.raises(FormulaError, match="division by zero"):
        evaluate("A / B", {"A": 1, "B": 0})


@pytest.mark.parametrize("expr", [
    "", "   ", "TP -", "* 3", "(2 + 3", "2 + 3)", "TP ALB", "2 @ 3",
    "round()", "round(1,2,3)", "min(1)", "TP +* ALB", ",", "()",
])
def test_malformed_rejected(expr):
    with pytest.raises(FormulaError):
        parse(expr)


def test_unknown_function_rejected():
    with pytest.raises(FormulaError, match="not an allowed function"):
        parse("frobnicate(1)")


def test_formula_length_capped():
    with pytest.raises(FormulaError, match="too long"):
        parse("1+" * 300 + "1")


# ----------------------------------------------------- no code execution ever

@pytest.mark.parametrize("expr", [
    "__import__('os').system('echo hi')",
    "open('/etc/passwd')",
    "().__class__",
    "A.__class__",
    "exec('x=1')",
    "eval('1')",
    "lambda: 1",
    "[x for x in range(3)]",
    "{'a':1}",
    "A;B",
    "A if B else C",
])
def test_no_code_execution(expr):
    """Anything resembling Python must be refused, not run."""
    with pytest.raises(FormulaError):
        parse(expr)


def test_bare_names_are_codes_not_builtins():
    """'open' with no parentheses is just a test code, and is unresolvable."""
    assert codes_used("open") == {"OPEN"}
    assert evaluate("open", {}) is None


# -------------------------------------------------------------- introspection

def test_codes_used():
    assert codes_used("TC - HDL - TG/5") == {"TC", "HDL", "TG"}
    assert codes_used("round(A + 2, 1)") == {"A"}
    assert codes_used("2 + 2") == set()


def test_describe_shows_precedence():
    assert describe("2 + 3 * 4") == "(2 + (3 * 4))"


# ------------------------------------------------------------------- cycles

def test_direct_self_reference_is_a_cycle():
    cycles = check_cycles({"A": "A + 1"})
    assert cycles and "A" in cycles[0]


def test_two_step_cycle_detected():
    cycles = check_cycles({"A": "B + 1", "B": "A - 1"})
    assert cycles
    assert set(cycles[0]) == {"A", "B"}


def test_clean_chain_has_no_cycle():
    assert check_cycles({"GLOB": "TP - ALB", "AGR": "ALB / GLOB"}) == []


# ------------------------------------------------------------- job resolution

def test_resolve_job_in_dependency_order():
    """A derived test may depend on another derived test."""
    out = resolve_job(
        {"GLOB": "TP - ALB", "AGR": "ALB / GLOB"},
        {"TP": 7.2, "ALB": 3.1},
    )
    assert out["GLOB"].value == pytest.approx(4.1)
    assert out["AGR"].value == pytest.approx(3.1 / 4.1)
    assert out["GLOB"].error is None and out["AGR"].error is None


def test_resolve_job_propagates_blank_through_chain():
    out = resolve_job({"GLOB": "TP - ALB", "AGR": "ALB / GLOB"}, {"TP": 7.2})
    assert out["GLOB"].value is None
    assert out["AGR"].value is None


def test_resolve_job_isolates_a_bad_formula():
    """One broken formula must not stop the others being calculated."""
    out = resolve_job({"GOOD": "A + B", "BAD": "A / 0"}, {"A": 2, "B": 3})
    assert out["GOOD"].value == pytest.approx(5.0)
    assert out["BAD"].value is None
    assert "division by zero" in out["BAD"].error


def test_resolve_job_reports_cycles_without_hanging():
    out = resolve_job({"A": "B + 1", "B": "A - 1"}, {})
    assert out["A"].value is None and out["B"].value is None
    assert "circular" in out["A"].error
