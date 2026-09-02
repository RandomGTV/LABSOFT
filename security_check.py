"""Find and shut down any account still using a PIN that was shipped as a default.

A migration used to create a user called ``admin`` with the PIN ``1598`` and
every permission there is. That code is gone, but the row it wrote is still
in every database created while it was there -- and the web application
prints that PIN on its own sign-in screen, so it is not a secret anywhere.

This does three things and nothing else:

  1. finds accounts whose PIN is still one of the well-known defaults
  2. shows what it found, and what each of those accounts is allowed to do
  3. once you have said so, turns them off and replaces the PIN with random
     characters nobody has, so the account cannot be used even if somebody
     switches it back on

Accounts are turned off rather than deleted, which is what the Staff screen
does too: every report, bill and change is recorded against whoever made it,
and removing the row would leave that history pointing at nobody.

An account whose PIN has been changed is left alone even if it is called
"admin" -- by then it is somebody's real account.

    python security_check.py            look, then ask
    python security_check.py --list     look only, change nothing
"""

from __future__ import annotations

import secrets
import string
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

#: PINs that have been shipped as a default at some point, and are therefore
#: public. Any account still using one can be signed into by anybody.
KNOWN_DEFAULTS = ["1598", "0000", "1234", "1111"]


def _unguessable() -> str:
    """A PIN nobody holds, so a turned-off account cannot be walked back in."""
    return "".join(secrets.choice(string.digits) for _ in range(12))


def main() -> int:
    from app.core import auth
    from app.db import connection, queries as q

    print()
    print("  LabSoft — default account check")
    print("  " + "=" * 60)
    print()

    connection.connect(do_backup=False)
    everyone = q.list_users(include_inactive=True)
    if not everyone:
        print("  There are no accounts in this database. Nothing to check.")
        print()
        return 0

    exposed = []
    for user in everyone:
        stored = q.user_pin_hash(user.id)
        for pin in KNOWN_DEFAULTS:
            if stored and auth.verify_pin(pin, stored):
                exposed.append((user, pin))
                break

    print(f"  {len(everyone)} account(s) in this database.")
    print()
    if not exposed:
        print("  None of them is using a default PIN. Nothing to do.")
        print()
        return 0

    print("  These can be signed into by anyone who knows the default PIN:")
    print()
    for user, pin in exposed:
        allowed = "everything" if user.is_admin else (
            ", ".join(sorted(user.permissions)) or "nothing")
        kind = "ADMINISTRATOR" if user.is_admin else "staff"
        state = "" if user.active else "   (already turned off)"
        print(f"    {user.username:<16} PIN {pin}   {kind}{state}")
        print(f"    {'':<16} may: {allowed}")
        print()

    if "--list" in sys.argv:
        print("  Nothing was changed (--list).")
        print()
        return 0

    # Somebody has to be left who can reach Settings and add staff.
    doomed = {u.username for u, _ in exposed}
    survivors = [u for u in everyone
                 if u.is_admin and u.active and u.username not in doomed]
    if not survivors and any(u.is_admin for u, _ in exposed):
        print("  ! The only administrator here is one of the accounts above.")
        print()
        print("  Turning it off would leave nobody able to reach Settings or")
        print("  add staff. Make your own administrator first — Staff tab,")
        print("  Create login — then run this again.")
        print()
        return 2

    if input("  Turn these off?  (type YES): ").strip() != "YES":
        print()
        print("  Nothing was changed.")
        print()
        return 1

    print()
    for user, _pin in exposed:
        q.set_user_pin(user.id, _unguessable())
        q.update_user(user.id, active=False)
        print(f"  turned off   {user.username}")

    print()
    print("  Done. Those accounts cannot sign in, and their PIN is now a")
    print("  random string nobody has — including whoever knew the default.")
    print()
    print("  What they did in the past is still recorded against them in the")
    print("  audit log. Turning off a login does not rewrite history.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
