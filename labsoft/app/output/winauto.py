"""Windows window control, used to attach the report into WhatsApp.

Only three things happen here: find the WhatsApp window, bring it to the front,
and press Ctrl+V into it. The clipboard already holds the PDF, so that paste is
the attach.

**Enter is never sent.** Pasting a file into WhatsApp opens its preview panel
with a Send button; the operator presses that. This keeps the promise that the
software prepares everything and a person decides to send.

Safety rule, and the reason this module is written defensively: keystrokes go
to whatever window has focus. Before pressing anything, the foreground window
is read back and its title checked. If WhatsApp is not genuinely in front,
nothing is pressed at all -- pasting a patient's report into the wrong
application would be far worse than making the operator press Ctrl+V.

Everything degrades to "not supported" off Windows.
"""

from __future__ import annotations

import platform
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

IS_WINDOWS = platform.system() == "Windows"

# Titles that mean "this is WhatsApp". The desktop app is just "WhatsApp"; a
# browser tab reads like "WhatsApp - Google Chrome".
_TITLE_HINTS = ("whatsapp",)

# Windows that merely mention WhatsApp but must never be typed into.
_TITLE_BLOCKLIST = ("labsoft", "notepad", "explorer", "outlook", "word", "excel")


@dataclass
class AttachResult:
    ok: bool
    reason: str = ""
    window_title: str = ""


def supported() -> bool:
    return IS_WINDOWS


# ---------------------------------------------------------------------------
# Window enumeration
# ---------------------------------------------------------------------------

def _user32():
    import ctypes

    return ctypes.WinDLL("user32", use_last_error=True)


def list_windows() -> List[Tuple[int, str]]:
    """Visible top-level windows as (hwnd, title)."""
    if not IS_WINDOWS:
        return []
    import ctypes
    from ctypes import wintypes

    u = _user32()
    found: List[Tuple[int, str]] = []

    EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _lparam):
        if not u.IsWindowVisible(hwnd):
            return True
        length = u.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        u.GetWindowTextW(hwnd, buf, length + 1)
        found.append((int(hwnd), buf.value))
        return True

    u.EnumWindows(EnumProc(callback), 0)
    return found


def looks_like_whatsapp(title: str) -> bool:
    t = (title or "").strip().lower()
    if not t:
        return False
    if any(bad in t for bad in _TITLE_BLOCKLIST):
        return False
    return any(hint in t for hint in _TITLE_HINTS)


def find_whatsapp_window() -> Optional[Tuple[int, str]]:
    for hwnd, title in list_windows():
        if looks_like_whatsapp(title):
            return hwnd, title
    return None


def wait_for_whatsapp(timeout: float = 25.0,
                      poll: float = 0.4) -> Optional[Tuple[int, str]]:
    """WhatsApp can take several seconds to start from cold."""
    deadline = time.monotonic() + max(0.0, timeout)
    while True:
        hit = find_whatsapp_window()
        if hit:
            return hit
        if time.monotonic() >= deadline:
            return None
        time.sleep(poll)


# ---------------------------------------------------------------------------
# Focus
# ---------------------------------------------------------------------------

def foreground_title() -> str:
    if not IS_WINDOWS:
        return ""
    import ctypes

    u = _user32()
    hwnd = u.GetForegroundWindow()
    if not hwnd:
        return ""
    length = u.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    u.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def focus_window(hwnd: int) -> bool:
    """Bring a window to the front and confirm it got there.

    Windows refuses SetForegroundWindow from a process that is not already in
    front, so the calling thread is briefly attached to the target's input
    queue -- the documented way to ask legitimately.
    """
    if not IS_WINDOWS:
        return False
    import ctypes

    u = _user32()
    SW_RESTORE = 9

    try:
        if u.IsIconic(hwnd):
            u.ShowWindow(hwnd, SW_RESTORE)

        current = u.GetForegroundWindow()
        this_thread = ctypes.windll.kernel32.GetCurrentThreadId()
        target_thread = u.GetWindowThreadProcessId(current, None) if current else 0

        attached = False
        if target_thread and target_thread != this_thread:
            attached = bool(u.AttachThreadInput(this_thread, target_thread, True))
        try:
            u.BringWindowToTop(hwnd)
            u.SetForegroundWindow(hwnd)
        finally:
            if attached:
                u.AttachThreadInput(this_thread, target_thread, False)
    except OSError:
        return False

    time.sleep(0.35)
    return bool(u.GetForegroundWindow() == hwnd)


# ---------------------------------------------------------------------------
# Keystrokes
# ---------------------------------------------------------------------------

VK_CONTROL = 0x11
VK_V = 0x56
KEYEVENTF_KEYUP = 0x0002


def _send_key(vk: int, up: bool = False) -> None:
    import ctypes

    _user32().keybd_event(vk, 0, KEYEVENTF_KEYUP if up else 0, 0)


def press_ctrl_v() -> None:
    if not IS_WINDOWS:
        return
    _send_key(VK_CONTROL)
    time.sleep(0.03)
    _send_key(VK_V)
    time.sleep(0.05)
    _send_key(VK_V, up=True)
    time.sleep(0.03)
    _send_key(VK_CONTROL, up=True)


# ---------------------------------------------------------------------------
# The one function the rest of the program calls
# ---------------------------------------------------------------------------

def paste_into_whatsapp(timeout: float = 25.0,
                        settle: float = 1.4) -> AttachResult:
    """Focus WhatsApp and paste whatever is on the clipboard.

    Returns a result rather than raising: failing to attach automatically is a
    small inconvenience, and the operator can still paste by hand.
    """
    if not IS_WINDOWS:
        return AttachResult(False, "Automatic attaching only works on Windows.")

    hit = wait_for_whatsapp(timeout)
    if not hit:
        return AttachResult(
            False,
            "WhatsApp did not appear, so nothing was pasted. Open the chat and "
            "press Ctrl+V yourself.")

    hwnd, title = hit
    if not focus_window(hwnd):
        return AttachResult(
            False,
            "WhatsApp could not be brought to the front, so nothing was pasted. "
            "Click on the WhatsApp window and press Ctrl+V.",
            title)

    # Give the chat time to finish opening and put the cursor in the message box.
    time.sleep(max(0.0, settle))

    # Last check before any key is pressed. If anything else has taken focus in
    # the meantime -- a notification, an update prompt -- the paste is abandoned
    # rather than sent into an unknown window.
    front = foreground_title()
    if not looks_like_whatsapp(front):
        return AttachResult(
            False,
            f"Another window ({front or 'unknown'}) took focus, so nothing was "
            f"pasted. Click on WhatsApp and press Ctrl+V.",
            front)

    press_ctrl_v()
    return AttachResult(True, "", front)
