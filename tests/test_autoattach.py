"""Automatic attaching, and the guards that stop it going wrong.

Keystrokes go wherever focus is. Pasting a patient's report into the wrong
application would be worse than making the operator press Ctrl+V, so the rule
is: verify WhatsApp is genuinely in front, or press nothing at all.
"""

from __future__ import annotations

import inspect

import pytest

from app.output import winauto


# --------------------------------------------------------- window recognition

@pytest.mark.parametrize("title", [
    "WhatsApp",
    "whatsapp",
    "WhatsApp - Google Chrome",
    "(2) WhatsApp — Mozilla Firefox",
    "WhatsApp Business",
])
def test_whatsapp_windows_are_recognised(title):
    assert winauto.looks_like_whatsapp(title)


@pytest.mark.parametrize("title", [
    "",
    None,
    "Notepad",
    "Documents",
    "LabSoft — New MITHRA",
    "Microsoft Excel - patients.xlsx",
    # Named so it cannot be confused with the real thing.
    "LabSoft — whatsapp settings",
    "Outlook - whatsapp invoice",
])
def test_other_windows_are_never_typed_into(title):
    assert not winauto.looks_like_whatsapp(title)


def test_labsofts_own_window_is_blocked_even_when_it_says_whatsapp():
    """The Settings screen has WhatsApp in its text; it must never be pasted into."""
    assert not winauto.looks_like_whatsapp("LabSoft — WhatsApp")


# ------------------------------------------------------------- the safety rule

def test_nothing_is_pressed_when_whatsapp_never_appears(monkeypatch):
    pressed = []
    monkeypatch.setattr(winauto, "IS_WINDOWS", True)
    monkeypatch.setattr(winauto, "wait_for_whatsapp", lambda timeout=0, poll=0: None)
    monkeypatch.setattr(winauto, "press_ctrl_v", lambda: pressed.append(1))

    result = winauto.paste_into_whatsapp(timeout=0)
    assert not result.ok
    assert pressed == [], "keys were sent with no WhatsApp window present"
    assert "Ctrl+V" in result.reason


def test_nothing_is_pressed_when_the_window_will_not_come_forward(monkeypatch):
    pressed = []
    monkeypatch.setattr(winauto, "IS_WINDOWS", True)
    monkeypatch.setattr(winauto, "wait_for_whatsapp", lambda *a, **k: (1, "WhatsApp"))
    monkeypatch.setattr(winauto, "focus_window", lambda hwnd: False)
    monkeypatch.setattr(winauto, "press_ctrl_v", lambda: pressed.append(1))

    result = winauto.paste_into_whatsapp(timeout=0)
    assert not result.ok and pressed == []


def test_nothing_is_pressed_when_another_window_steals_focus(monkeypatch):
    """The dangerous case: WhatsApp came forward, then something else took over."""
    pressed = []
    monkeypatch.setattr(winauto, "IS_WINDOWS", True)
    monkeypatch.setattr(winauto, "wait_for_whatsapp", lambda *a, **k: (1, "WhatsApp"))
    monkeypatch.setattr(winauto, "focus_window", lambda hwnd: True)
    monkeypatch.setattr(winauto, "foreground_title", lambda: "Windows Update")
    monkeypatch.setattr(winauto, "press_ctrl_v", lambda: pressed.append(1))

    result = winauto.paste_into_whatsapp(timeout=0, settle=0)
    assert not result.ok
    assert pressed == [], "the report was pasted into Windows Update"
    assert "Windows Update" in result.reason


def test_paste_happens_when_whatsapp_is_genuinely_in_front(monkeypatch):
    pressed = []
    monkeypatch.setattr(winauto, "IS_WINDOWS", True)
    monkeypatch.setattr(winauto, "wait_for_whatsapp", lambda *a, **k: (1, "WhatsApp"))
    monkeypatch.setattr(winauto, "focus_window", lambda hwnd: True)
    monkeypatch.setattr(winauto, "foreground_title", lambda: "WhatsApp")
    monkeypatch.setattr(winauto, "press_ctrl_v", lambda: pressed.append(1))

    result = winauto.paste_into_whatsapp(timeout=0, settle=0)
    assert result.ok and pressed == [1]


def test_enter_is_never_sent():
    """Sending must stay a human decision. Only Ctrl+V is ever pressed."""
    source = inspect.getsource(winauto)
    assert "VK_RETURN" not in source
    assert "0x0D" not in source
    for name in dir(winauto):
        assert "enter" not in name.lower() or name.startswith("_")


def test_only_ctrl_v_is_defined():
    source = inspect.getsource(winauto)
    assert source.count("def press_") == 1, "only one key combination may exist"


def test_unsupported_platform_degrades_quietly(monkeypatch):
    monkeypatch.setattr(winauto, "IS_WINDOWS", False)
    result = winauto.paste_into_whatsapp(timeout=0)
    assert not result.ok
    assert "Windows" in result.reason


def test_helpers_are_safe_off_windows(monkeypatch):
    monkeypatch.setattr(winauto, "IS_WINDOWS", False)
    assert winauto.list_windows() == []
    assert winauto.find_whatsapp_window() is None
    assert winauto.foreground_title() == ""
    assert winauto.focus_window(1) is False
    winauto.press_ctrl_v()          # must not raise


def test_failure_always_explains_the_manual_route(monkeypatch):
    monkeypatch.setattr(winauto, "IS_WINDOWS", True)
    monkeypatch.setattr(winauto, "wait_for_whatsapp", lambda *a, **k: None)
    reason = winauto.paste_into_whatsapp(timeout=0).reason
    assert "Ctrl+V" in reason


# ------------------------------------------------------------------- settings

def test_auto_attach_is_on_by_default():
    from app import config

    assert config.DEFAULT_SETTINGS["auto_attach"] == "1"


def test_settings_screen_can_turn_it_off(tmp_path, monkeypatch):
    monkeypatch.setenv("LABSOFT_HOME", str(tmp_path))
    from PyQt6.QtWidgets import QApplication
    from app.db import connection, queries as q

    connection.close()
    connection.connect(do_backup=False)
    q.ensure_defaults()
    QApplication.instance() or QApplication([])

    from app.ui.settings_screen import SettingsScreen

    screen = SettingsScreen()
    assert screen.auto_attach_check.isChecked()
    screen.auto_attach_check.setChecked(False)
    assert screen.collect()["auto_attach"] == "0"
    screen.deleteLater()
    connection.close()
