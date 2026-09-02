"""Users, PINs and permissions.

PINs are salted and hashed with PBKDF2-HMAC-SHA256 from the standard library.
Nothing here stores a PIN that could be read back: a lab PC gets shared,
borrowed and occasionally stolen, and the database file is a plain file anyone
can copy.

Permissions are per person, not per role. "Admin" is simply an account that
holds every permission, so a lab can have a senior technician who bills and
edits tests but cannot change the report letterhead.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

# --------------------------------------------------------------------------
# Permissions
# --------------------------------------------------------------------------

P_RESULTS = "results"        # register patients and enter results
P_SEND = "send"              # produce and send reports
P_BILL = "bill"              # make bills and take payments
P_MONEY = "money"            # billing ledger, dues, commissions, summaries
P_TESTS = "tests"            # the Tests master, panels, referring doctors
P_SETTINGS = "settings"      # lab details, report layout, backups
P_DELETE = "delete"          # delete jobs, restore backups
P_USERS = "users"            # add and edit staff

ALL_PERMISSIONS = [P_RESULTS, P_SEND, P_BILL, P_MONEY, P_TESTS,
                   P_SETTINGS, P_DELETE, P_USERS]

PERMISSION_LABELS = {
    P_RESULTS: "Register patients and enter results",
    P_SEND: "Make and send reports",
    P_BILL: "Make bills and take payments",
    P_MONEY: "See the billing ledger, dues and summaries",
    P_TESTS: "Edit the Tests master, panels and doctors",
    P_SETTINGS: "Change Settings and the report layout",
    P_DELETE: "Delete jobs and restore backups",
    P_USERS: "Add and edit staff accounts",
}

# Two or three words each, for the summary column in the staff list. The long
# labels above read as sentences and cannot be joined with commas.
PERMISSION_SHORT = {
    P_RESULTS: "results",
    P_SEND: "reports",
    P_BILL: "billing",
    P_MONEY: "money",
    P_TESTS: "tests master",
    P_SETTINGS: "settings",
    P_DELETE: "delete",
    P_USERS: "staff",
}

# What a new staff account starts with: enough to do the day's work.
STAFF_DEFAULT = [P_RESULTS, P_SEND, P_BILL]

ROLE_ADMIN = "admin"
ROLE_STAFF = "staff"


@dataclass
class User:
    id: Optional[int] = None
    username: str = ""
    display_name: str = ""
    role: str = ROLE_STAFF
    permissions: Set[str] = field(default_factory=set)
    active: bool = True

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    def can(self, permission: str) -> bool:
        """An admin can do everything; everyone else holds named permissions."""
        if not self.active:
            return False
        if self.is_admin:
            return True
        return permission in self.permissions

    @property
    def label(self) -> str:
        who = self.display_name.strip() or self.username
        return f"{who} ({'Admin' if self.is_admin else 'Staff'})"


# --------------------------------------------------------------------------
# PINs
# --------------------------------------------------------------------------

ITERATIONS = 120_000
MIN_PIN = 4
MAX_PIN = 32


#: PINs nobody may choose. 1598 is on the list because it was LabSoft's own
#: master PIN, printed on the sign-in screen of the web application and in the
#: error message of the desktop one. Anyone who ever saw this program knows it.
KNOWN_DEFAULTS = ("1234", "0000", "1111", "9999",
                  "12345", "123456", "1212", "4321")


class PinError(ValueError):
    """Raised with a message written for the person choosing the PIN."""


def check_pin_quality(pin: str) -> str:
    """Return a complaint about the PIN, or '' when it is acceptable.

    Deliberately mild. A lab technician typing this thirty times a day will
    write a long password on a sticky note beside the screen, which is worse
    than a short PIN they remember.
    """
    pin = (pin or "").strip()
    if len(pin) < MIN_PIN:
        return f"The PIN must be at least {MIN_PIN} characters."
    if len(pin) > MAX_PIN:
        return f"The PIN must be {MAX_PIN} characters or fewer."
    if pin in KNOWN_DEFAULTS:
        return "That PIN is too well known. Please choose another."
    return ""


def hash_pin(pin: str, salt: Optional[bytes] = None) -> str:
    """Return 'pbkdf2$iterations$salt$hash', all hex."""
    problem = check_pin_quality(pin)
    if problem:
        raise PinError(problem)
    # Hash what check_pin_quality checked, and what the sign-in screen sends.
    # It hashed the raw string while both of those strip it, so a PIN set as
    # "7391 " could never afterwards be typed in.
    pin = (pin or "").strip()
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_pin(pin: str, stored: str) -> bool:
    """Constant-time check of a typed PIN against the stored hash."""
    pin = (pin or "").strip()
    if not stored or not pin:
        return False
    try:
        scheme, iterations, salt_hex, digest_hex = stored.split("$")
        if scheme != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", pin.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
    except (ValueError, TypeError):
        return False
    # compare_digest, not ==, so the time taken cannot reveal how much matched.
    return hmac.compare_digest(digest.hex(), digest_hex)


# --------------------------------------------------------------------------
# Usernames
# --------------------------------------------------------------------------

_USERNAME = re.compile(r"^[a-z0-9._-]{2,24}$")


def normalise_username(name: str) -> str:
    return re.sub(r"\s+", "", (name or "").strip().lower())


def check_username(name: str) -> str:
    """Return a complaint, or '' when acceptable."""
    clean = normalise_username(name)
    if not clean:
        return "Please type a username."
    if not _USERNAME.match(clean):
        return ("A username can use letters, numbers, dot, dash and underscore, "
                "and must be 2 to 24 characters long.")
    return ""


# --------------------------------------------------------------------------
# Serialising permissions
# --------------------------------------------------------------------------

def permissions_to_text(permissions) -> str:
    return ",".join(sorted(p for p in permissions if p in ALL_PERMISSIONS))


def permissions_from_text(text: str) -> Set[str]:
    return {p.strip() for p in (text or "").split(",")
            if p.strip() in ALL_PERMISSIONS}


# --------------------------------------------------------------------------
# The signed-in user
# --------------------------------------------------------------------------

_current: Optional[User] = None


def set_current(user: Optional[User]) -> None:
    global _current
    _current = user


def current() -> Optional[User]:
    return _current


def can(permission: str) -> bool:
    """True when the signed-in person may do this.

    With nobody signed in this returns True, so the program still works for a
    single-operator lab that has not created any accounts.
    """
    if _current is None:
        return True
    return _current.can(permission)


def who() -> str:
    return _current.label if _current else "no sign-in"
