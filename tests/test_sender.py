import pytest

from app.output.sender import format_message, normalise_phone


@pytest.mark.parametrize("raw,expected", [
    ("9876543210", "919876543210"),
    ("98765 43210", "919876543210"),
    ("+91 98765 43210", "919876543210"),
    ("+91-98765-43210", "919876543210"),
    ("098765 43210", "919876543210"),
    ("919876543210", "919876543210"),
    ("0091 9876543210", "919876543210"),
])
def test_indian_numbers_normalise(raw, expected):
    assert normalise_phone(raw) == expected


@pytest.mark.parametrize("raw", ["", None, "abc", "12345", "0", "98765"])
def test_incomplete_numbers_are_refused(raw):
    """Sending a patient's report to a wrong number is the worst failure
    this program could have, so a short number is never dialled."""
    assert normalise_phone(raw) is None


def test_other_country_code():
    assert normalise_phone("5551234567", country_code="1") == "15551234567"


def test_message_template_filled():
    msg = format_message(
        "Dear {name},\nReport No {report_no}, {date}. Call {phone}.",
        name="FARAS .M.", report_no="51359", date="18-08-2026", phone="0712 234 5678")
    assert "Dear FARAS .M." in msg
    assert "Report No 51359, 18-08-2026" in msg


def test_unknown_placeholder_is_left_visible_not_fatal():
    msg = format_message("Hello {name}, see {whatever}", name="X")
    assert msg == "Hello X, see {whatever}"


def test_empty_template_is_safe():
    assert format_message("", name="X") == ""
    assert format_message(None, name="X") == ""
