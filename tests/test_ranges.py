import pytest

from app.core.ranges import (
    FLAG_ABNORMAL, FLAG_HIGH, FLAG_LOW, FLAG_NONE, FLAG_NORMAL,
    RULE_MAX, RULE_MIN, RULE_RANGE, RULE_TEXT,
    ReferenceRange, age_in_years, default_display, flag_for, format_value,
    select_range,
)


def R(**kw):
    return ReferenceRange(**kw)


# ------------------------------------------------------------ range boundaries

@pytest.mark.parametrize("value,expected", [
    (69.9, FLAG_LOW),
    (70,   FLAG_NORMAL),   # inclusive lower bound
    (90,   FLAG_NORMAL),
    (110,  FLAG_NORMAL),   # inclusive upper bound
    (110.1, FLAG_HIGH),
])
def test_range_boundaries_inclusive(value, expected):
    r = R(rule_type=RULE_RANGE, low=70, high=110)
    assert r.flag(value) == expected


@pytest.mark.parametrize("value,expected", [
    (199.9, FLAG_NORMAL),
    (200,   FLAG_NORMAL),  # "< 200" treats exactly 200 as acceptable
    (200.1, FLAG_HIGH),
])
def test_max_rule(value, expected):
    assert R(rule_type=RULE_MAX, high=200).flag(value) == expected


@pytest.mark.parametrize("value,expected", [
    (39.9, FLAG_LOW),
    (40,   FLAG_NORMAL),
    (40.1, FLAG_NORMAL),
])
def test_min_rule(value, expected):
    assert R(rule_type=RULE_MIN, low=40).flag(value) == expected


def test_text_rule():
    r = R(rule_type=RULE_TEXT, text_value="Negative")
    assert r.flag("Negative") == FLAG_NORMAL
    assert r.flag("negative") == FLAG_NORMAL      # case-insensitive
    assert r.flag("  Negative ") == FLAG_NORMAL   # whitespace tolerant
    assert r.flag("Positive") == FLAG_ABNORMAL


def test_blank_value_is_unflagged():
    r = R(rule_type=RULE_RANGE, low=70, high=110)
    assert r.flag(None) == FLAG_NONE
    assert r.flag("") == FLAG_NONE
    assert r.flag("   ") == FLAG_NONE


def test_operator_prefixed_values_compare_on_the_number():
    r = R(rule_type=RULE_MAX, high=200)
    assert r.flag("<150") == FLAG_NORMAL
    assert r.flag(">250") == FLAG_HIGH


def test_non_numeric_value_on_numeric_rule_is_unflagged():
    r = R(rule_type=RULE_RANGE, low=70, high=110)
    assert r.flag("haemolysed") == FLAG_NONE


def test_incomplete_rule_never_reports_normal():
    """A half-configured range must not bless a value as Normal."""
    assert R(rule_type=RULE_RANGE).flag(50) == FLAG_ABNORMAL
    assert R(rule_type=RULE_MAX).flag(50) == FLAG_ABNORMAL
    assert R(rule_type=RULE_MIN).flag(50) == FLAG_ABNORMAL


# ---------------------------------------------------------------- age helpers

@pytest.mark.parametrize("value,unit,expected", [
    (31, "years", 31.0),
    (6, "months", 0.5),
    (18, "months", 1.5),
    (365.25, "days", 1.0),
    (10, "Y", 10.0),
    (None, "years", None),
])
def test_age_in_years(value, unit, expected):
    got = age_in_years(value, unit)
    if expected is None:
        assert got is None
    else:
        assert got == pytest.approx(expected)


# ------------------------------------------------------------- range matching

HB_RANGES = [
    R(rule_type=RULE_RANGE, low=12, high=16, sex="F", display_text="12 - 16g/dl"),
    R(rule_type=RULE_RANGE, low=13, high=17, sex="M", display_text="13 - 17g/dl"),
    R(rule_type=RULE_RANGE, low=11, high=14, age_max=12, display_text="11 - 14g/dl"),
]


def test_sex_specific_range_chosen():
    assert select_range(HB_RANGES, "Female", 31).display_text == "12 - 16g/dl"
    assert select_range(HB_RANGES, "Male", 31).display_text == "13 - 17g/dl"


def test_more_specific_row_wins():
    """Sex+age beats sex alone."""
    ranges = [
        R(rule_type=RULE_RANGE, low=12, high=16, sex="F", display_text="adult"),
        R(rule_type=RULE_RANGE, low=11, high=14, sex="F", age_max=12, display_text="child"),
    ]
    assert select_range(ranges, "F", 8).display_text == "child"
    assert select_range(ranges, "F", 30).display_text == "adult"


def test_age_upper_bound_is_exclusive():
    ranges = [R(rule_type=RULE_RANGE, low=11, high=14, age_max=12, display_text="child")]
    assert select_range(ranges, "F", 11.9) is not None
    assert select_range(ranges, "F", 12) is None


def test_no_matching_range_returns_none():
    ranges = [R(rule_type=RULE_RANGE, low=1, high=2, age_min=60)]
    assert select_range(ranges, "F", 31) is None


def test_flag_for_without_a_range_is_never_normal():
    """The rule that stops a false 'Normal' appearing on a report."""
    assert flag_for(95, [], "F", 31) == FLAG_ABNORMAL
    assert flag_for(95, [R(rule_type=RULE_RANGE, low=1, high=2, age_min=60)], "F", 31) == FLAG_ABNORMAL


def test_flag_for_end_to_end():
    assert flag_for(9.2, HB_RANGES, "Female", 31) == FLAG_LOW
    assert flag_for(14.0, HB_RANGES, "Female", 31) == FLAG_NORMAL
    assert flag_for(18.0, HB_RANGES, "Male", 31) == FLAG_HIGH
    assert flag_for(None, HB_RANGES, "Female", 31) == FLAG_NONE


def test_sex_missing_falls_back_to_any_row():
    ranges = [
        R(rule_type=RULE_RANGE, low=70, high=110, sex="any", display_text="70 - 110mg/dl"),
        R(rule_type=RULE_RANGE, low=1, high=2, sex="M"),
    ]
    assert select_range(ranges, None, 31).display_text == "70 - 110mg/dl"


# -------------------------------------------------------------- display text

def test_display_text_is_used_verbatim():
    """The lab's own wording prints, not a reassembled string."""
    r = R(rule_type=RULE_RANGE, low=70, high=110, display_text="70 - 110mg/dl")
    assert r.printed_text("mg/dl") == "70 - 110mg/dl"


@pytest.mark.parametrize("rng,unit,expected", [
    (R(rule_type=RULE_RANGE, low=70, high=110), "mg/dl", "70 - 110mg/dl"),
    (R(rule_type=RULE_MAX, high=200),           "mg/dl", "< 200mg/dl"),
    (R(rule_type=RULE_MIN, low=40),             "mg/dl", "> 40mg/dl"),
    (R(rule_type=RULE_TEXT, text_value="Negative"), "",  "Negative"),
    (R(rule_type=RULE_RANGE, low=3.5, high=5.2), "g/dl", "3.5 - 5.2g/dl"),
])
def test_default_display(rng, unit, expected):
    assert default_display(rng, unit) == expected


@pytest.mark.parametrize("value,decimals,expected", [
    (105, 0, "105"),
    (105.0, 1, "105.0"),
    (3.14159, 2, "3.14"),
    (0.7560975, 2, "0.76"),
    (None, 1, ""),
    ("Negative", 1, "Negative"),
])
def test_format_value(value, decimals, expected):
    assert format_value(value, decimals) == expected
