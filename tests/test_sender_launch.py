"""How the WhatsApp link is actually launched.

The original bug: the URL was passed through `cmd /c start`. In cmd, `&`
separates commands, so
    whatsapp://send?phone=919876543210&text=Dear%20FARAS
was cut in half at the `&`. Worse, cmd itself started fine, so the code
concluded it had succeeded and never fell back to WhatsApp Web.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from app.output import sender as snd


@pytest.fixture()
def pdf(tmp_path):
    p = tmp_path / "report.pdf"
    p.write_bytes(b"%PDF-1.4 test")
    return p


# ------------------------------------------------------- the launch mechanism

def test_cmd_start_is_never_used_for_urls():
    """cmd would truncate the URL at the first &."""
    source = inspect.getsource(snd)
    assert '"start"' not in source and "'start'" not in source, \
        "launching a URL through cmd start truncates it at the '&'"


def test_url_carries_both_phone_and_message():
    url = snd.desktop_url("919876543210", "Dear%20FARAS")
    assert "phone=919876543210" in url
    assert "text=Dear%20FARAS" in url
    assert url.count("&") == 1


def test_web_url_opens_the_chat_directly():
    """wa.me shows a 'Continue to Chat' page first, which is an extra click."""
    url = snd.web_url("919876543210", "hi")
    assert url.startswith("https://web.whatsapp.com/send")
    assert "phone=919876543210" in url


# ------------------------------------------------------------- fallback logic

def test_falls_back_to_web_when_the_desktop_app_is_absent(pdf, monkeypatch):
    opened = []
    monkeypatch.setattr(snd, "desktop_app_available", lambda: False)
    monkeypatch.setattr(snd, "open_url", lambda url: (opened.append(url), True)[1])
    monkeypatch.setattr(snd, "copy_file_to_clipboard", lambda p: True)

    result = snd.WhatsAppDesktopSender("91", "auto").send(pdf, "9876543210", "hello")

    assert result.ok and result.channel == "whatsapp_web"
    assert len(opened) == 1
    assert opened[0].startswith("https://web.whatsapp.com/")


def test_uses_the_desktop_app_when_it_is_present(pdf, monkeypatch):
    opened = []
    monkeypatch.setattr(snd, "desktop_app_available", lambda: True)
    monkeypatch.setattr(snd, "open_url", lambda url: (opened.append(url), True)[1])
    monkeypatch.setattr(snd, "copy_file_to_clipboard", lambda p: True)

    result = snd.WhatsAppDesktopSender("91", "auto").send(pdf, "9876543210", "hello")

    assert result.channel == "whatsapp"
    assert opened[0].startswith("whatsapp://send")


def test_web_is_tried_when_the_desktop_app_refuses_to_open(pdf, monkeypatch):
    """The case that used to fail silently: the app is registered but does nothing."""
    opened = []

    def fake_open(url):
        opened.append(url)
        return not url.startswith("whatsapp://")     # desktop refuses

    monkeypatch.setattr(snd, "desktop_app_available", lambda: True)
    monkeypatch.setattr(snd, "open_url", fake_open)
    monkeypatch.setattr(snd, "copy_file_to_clipboard", lambda p: True)

    result = snd.WhatsAppDesktopSender("91", "auto").send(pdf, "9876543210", "hello")

    assert result.channel == "whatsapp_web"
    assert len(opened) == 2


def test_nothing_opens_gives_a_useful_error(pdf, monkeypatch):
    monkeypatch.setattr(snd, "desktop_app_available", lambda: True)
    monkeypatch.setattr(snd, "open_url", lambda url: False)
    monkeypatch.setattr(snd, "copy_file_to_clipboard", lambda p: True)

    with pytest.raises(snd.SendError) as exc:
        snd.WhatsAppDesktopSender("91", "auto").send(pdf, "9876543210", "hello")

    message = str(exc.value)
    assert str(pdf) in message            # tells them where the report is
    assert "Open folder" in message       # and what to do next


def test_forced_web_mode_skips_the_desktop_app(pdf, monkeypatch):
    opened = []
    monkeypatch.setattr(snd, "desktop_app_available", lambda: True)
    monkeypatch.setattr(snd, "open_url", lambda url: (opened.append(url), True)[1])
    monkeypatch.setattr(snd, "copy_file_to_clipboard", lambda p: True)

    snd.WhatsAppDesktopSender("91", "web").send(pdf, "9876543210", "hello")
    assert all(u.startswith("https://") for u in opened)


def test_forced_desktop_mode_does_not_fall_back(pdf, monkeypatch):
    monkeypatch.setattr(snd, "desktop_app_available", lambda: True)
    monkeypatch.setattr(snd, "open_url", lambda url: False)
    monkeypatch.setattr(snd, "copy_file_to_clipboard", lambda p: True)

    with pytest.raises(snd.SendError):
        snd.WhatsAppDesktopSender("91", "desktop").send(pdf, "9876543210", "hello")


# ------------------------------------------------------------------ messaging

def test_bad_number_is_refused_before_anything_opens(pdf, monkeypatch):
    opened = []
    monkeypatch.setattr(snd, "open_url", lambda url: (opened.append(url), True)[1])

    with pytest.raises(snd.SendError, match="does not look complete"):
        snd.WhatsAppDesktopSender("91", "auto").send(pdf, "98765", "hello")
    assert opened == [], "nothing may open for an incomplete number"


def test_message_is_url_encoded(pdf, monkeypatch):
    opened = []
    monkeypatch.setattr(snd, "desktop_app_available", lambda: False)
    monkeypatch.setattr(snd, "open_url", lambda url: (opened.append(url), True)[1])
    monkeypatch.setattr(snd, "copy_file_to_clipboard", lambda p: True)

    snd.WhatsAppDesktopSender("91", "auto").send(
        pdf, "9876543210", "Dear FARAS .M.\nReport 51359 & results")

    url = opened[0]
    assert " " not in url
    assert "%26" in url, "a literal & inside the message would break the link"
    assert url.count("&") == 1, "only the parameter separator may be a bare &"


def test_clipboard_failure_is_told_to_the_operator(pdf, monkeypatch):
    monkeypatch.setattr(snd, "desktop_app_available", lambda: False)
    monkeypatch.setattr(snd, "open_url", lambda url: True)
    monkeypatch.setattr(snd, "copy_file_to_clipboard", lambda p: False)

    result = snd.WhatsAppDesktopSender("91", "auto").send(pdf, "9876543210", "hi")
    assert "Open folder" in result.manual_step


def test_success_says_where_it_opened_and_for_whom(pdf, monkeypatch):
    monkeypatch.setattr(snd, "desktop_app_available", lambda: True)
    monkeypatch.setattr(snd, "open_url", lambda url: True)
    monkeypatch.setattr(snd, "copy_file_to_clipboard", lambda p: True)

    result = snd.WhatsAppDesktopSender("91", "auto").send(pdf, "9876543210", "hi")
    assert "919876543210" in result.manual_step
    assert "Ctrl+V" in result.manual_step


def test_the_browser_never_claims_the_report_is_on_the_clipboard(pdf, monkeypatch):
    """A browser tab cannot take a file from LabSoft.

    It used to say "press Ctrl+V then Enter to attach the report" whichever
    of the two opened, so a report sent through WhatsApp Web went out as a
    message with nothing attached and LabSoft recorded it as sent.
    """
    monkeypatch.setattr(snd, "desktop_app_available", lambda: False)
    monkeypatch.setattr(snd, "open_url", lambda url: True)
    monkeypatch.setattr(snd, "copy_file_to_clipboard", lambda p: True)

    result = snd.WhatsAppDesktopSender("91", "auto").send(pdf, "9876543210", "hi")
    assert result.channel == "whatsapp_web"
    assert "Ctrl+V" not in result.manual_step
    assert "Open folder" in result.manual_step


def test_desktop_only_never_opens_the_browser(pdf, monkeypatch):
    """The default. A message with no report on it is not a sent report."""
    opened = []
    monkeypatch.setattr(snd, "desktop_app_available", lambda: False)
    monkeypatch.setattr(snd, "open_url", lambda url: opened.append(url) or True)
    monkeypatch.setattr(snd, "copy_file_to_clipboard", lambda p: True)

    with pytest.raises(snd.SendError) as caught:
        snd.WhatsAppDesktopSender("91", "desktop").send(pdf, "9876543210", "hi")
    assert opened == [], f"it opened {opened}"
    assert "not installed" in str(caught.value)
    assert str(pdf) in str(caught.value)


def test_the_default_mode_is_the_application(pdf, monkeypatch):
    from app import config

    assert config.DEFAULT_SETTINGS["whatsapp_mode"] == "desktop"
