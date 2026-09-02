"""Every SQL statement in the program lives here.

Callers pass and receive plain dicts and dataclasses. Nothing above this module
knows that SQLite is underneath, which is what would let the storage change
later without rewriting the screens.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .. import config
from ..core import auth, billing, formula, numbering, ranges as rng, turnaround
from .connection import get

ISO = "%Y-%m-%d %H:%M:%S"


def now_str() -> str:
    return datetime.now().strftime(ISO)


def to_dt(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    for fmt in (ISO, "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    return None


def dt_str(value: Optional[datetime]) -> Optional[str]:
    return value.strftime(ISO) if value else None


@contextmanager
def transaction():
    conn = get()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _rows(sql: str, params: Sequence = ()) -> List[dict]:
    return [dict(r) for r in get().execute(sql, params).fetchall()]


def _row(sql: str, params: Sequence = ()) -> Optional[dict]:
    r = get().execute(sql, params).fetchone()
    return dict(r) if r else None


# ===========================================================================
# Settings
# ===========================================================================

def all_settings() -> Dict[str, str]:
    out = dict(config.DEFAULT_SETTINGS)
    for r in _rows("SELECT key, value FROM settings"):
        out[r["key"]] = r["value"]
    return out


def get_setting(key: str, default: str = "") -> str:
    r = _row("SELECT value FROM settings WHERE key = ?", (key,))
    if r is not None:
        return r["value"]
    return config.DEFAULT_SETTINGS.get(key, default)


def set_setting(key: str, value: str) -> None:
    with transaction() as c:
        c.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, "" if value is None else str(value)),
        )


def set_settings(values: Dict[str, str]) -> None:
    with transaction() as c:
        for k, v in values.items():
            c.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (k, "" if v is None else str(v)),
            )
    log_action("settings_changed", "settings", None, ", ".join(sorted(values)))


def ensure_defaults() -> None:
    existing = {r["key"] for r in _rows("SELECT key FROM settings")}
    missing = {k: v for k, v in config.DEFAULT_SETTINGS.items() if k not in existing}
    if missing:
        with transaction() as c:
            for k, v in missing.items():
                c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (k, v))


def setting_bool(key: str, default: bool = False) -> bool:
    default_str = "1" if default else "0"
    return str(get_setting(key, default_str)).strip() in ("1", "true", "True", "yes")


# ===========================================================================
# Audit
# ===========================================================================

def log_action(action: str, entity: str = "", entity_id: Optional[int] = None,
               detail: str = "") -> None:
    """Record a state change, and who made it."""
    user = auth.current()
    try:
        with transaction() as c:
            c.execute(
                "INSERT INTO audit_log (at, action, entity, entity_id, detail, "
                "user_id, user_name) VALUES (?,?,?,?,?,?,?)",
                (now_str(), action, entity, entity_id, detail,
                 user.id if user else None,
                 user.display_name or user.username if user else ""),
            )
    except sqlite3.Error:
        pass  # never let logging break the operation it is recording


def recent_audit(limit: int = 300) -> List[dict]:
    return _rows("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))


# ===========================================================================
# Patients
# ===========================================================================

def search_patients(term: str, limit: int = 25) -> List[dict]:
    """Find a returning patient from very little typing.

    A busy reception types three letters, or initials. All of these find
    "FARAS .M. Kutty":

        far        the start of a name
        fmk        the initials
        f.m        initials with dots
        m kutty    any word, not just the first
        43210      part of the mobile number

    Matching is done in Python rather than SQL because SQL LIKE cannot express
    "initials", and a lab's patient list is small enough that reading it is
    instant.
    """
    raw = (term or "").strip()
    if not raw:
        return _rows(
            "SELECT p.*, (SELECT MAX(j.received_at) FROM jobs j "
            "  WHERE j.patient_id = p.id) AS last_visit "
            "FROM patients p ORDER BY last_visit DESC NULLS LAST, p.name LIMIT ?",
            (limit,))

    digits = "".join(ch for ch in raw if ch.isdigit())
    needle = "".join(ch for ch in raw.lower() if ch.isalnum())
    words = [w for w in re.split(r"[^a-z0-9]+", raw.lower()) if w]

    everyone = _rows(
        "SELECT p.*, (SELECT MAX(j.received_at) FROM jobs j "
        "  WHERE j.patient_id = p.id) AS last_visit FROM patients p")

    scored = []
    for p in everyone:
        # Matched against the name as written -- FARAS .M. Kutty -- so the
        # initial counts towards "fmk" the same as it does on the report.
        name = patient_full_name(p).lower()
        parts = [w for w in re.split(r"[^a-z0-9]+", name) if w]
        initials = "".join(w[0] for w in parts)
        phone = "".join(ch for ch in (p["phone"] or "") if ch.isdigit())

        score = None
        if digits and len(digits) >= 3 and digits in phone:
            score = 0                                   # a number is exact
        elif parts and parts[0].startswith(words[0] if words else ""):
            score = 1                                   # first name matches
        elif needle and initials.startswith(needle):
            score = 2                                   # typed the initials
        elif any(w.startswith(words[0]) for w in parts) if words else False:
            score = 3                                   # any other word
        elif needle and needle in "".join(parts):
            score = 4                                   # somewhere in the name
        if score is None:
            continue
        scored.append((score, -(_recency(p.get("last_visit"))), p["name"].lower(), p))

    scored.sort(key=lambda row: row[:3])
    return [row[3] for row in scored[:limit]]


def _recency(value) -> float:
    """Newer visitors come first among equally good name matches."""
    dt = to_dt(value)
    return dt.timestamp() if dt else 0.0


def get_patient(pid: int) -> Optional[dict]:
    return _row("SELECT * FROM patients WHERE id = ?", (pid,))


def find_patient(name: str, phone: str) -> Optional[dict]:
    return _row(
        "SELECT * FROM patients WHERE lower(name) = lower(?) AND phone = ? LIMIT 1",
        ((name or "").strip(), (phone or "").strip()),
    )


PATIENT_TEXT_FIELDS = ("name", "initial", "phone", "sex", "age_unit", "dob",
                       "address", "notes")


def full_name(name: str, initial: str = "") -> str:
    """The patient's name the way the lab writes it: FARAS .M. Kutty.

    The initial sits after the first word, not at the end, because that is how
    it is said and how the printed reports have always read. With no family
    name it simply trails: FARAS .M.
    """
    name = " ".join((name or "").split())
    initial = (initial or "").strip().strip(".").upper()
    if not initial:
        return name
    if not name:
        return f".{initial}."
    first, _, rest = name.partition(" ")
    tail = f" {rest}" if rest else ""
    return f"{first} .{initial}.{tail}"


def patient_full_name(patient: dict) -> str:
    patient = patient or {}
    return full_name(patient.get("name", ""), patient.get("initial", ""))


def save_patient(data: dict) -> int:
    """Insert or update a patient.

    An update touches ONLY the keys actually supplied. Writing every column
    every time meant that saving a patient from the job screen -- which sends
    name, phone, sex and age -- wiped the address and any clinical note that had
    been recorded elsewhere.
    """
    with transaction() as c:
        if data.get("id"):
            sets, params = [], {"id": int(data["id"])}
            for key in PATIENT_TEXT_FIELDS:
                if key in data:
                    value = "" if data[key] is None else str(data[key])
                    if key == "name":
                        value = value.strip()
                    if key == "initial":
                        value = value.strip().strip(".").upper()
                    if key == "age_unit":
                        value = value or "years"
                    sets.append(f"{key} = :{key}")
                    params[key] = value
            if "age_value" in data:
                sets.append("age_value = :age_value")
                params["age_value"] = _as_number(data["age_value"])
            if sets:
                c.execute(f"UPDATE patients SET {', '.join(sets)} WHERE id = :id", params)
            return int(data["id"])

        values = {k: ("" if data.get(k) is None else str(data.get(k)))
                  for k in PATIENT_TEXT_FIELDS}
        values["name"] = values["name"].strip()
        values["age_unit"] = values["age_unit"] or "years"
        # age_value stays numeric-or-None: a patient with no age recorded is
        # valid, and 0 is a real age (a newborn), so it cannot mean "unknown".
        values["age_value"] = _as_number(data.get("age_value"))
        values["initial"] = values["initial"].strip().strip(".").upper()
        cur = c.execute(
            "INSERT INTO patients (name, initial, phone, sex, age_value, "
            "age_unit, dob, address, notes, created_at) "
            "VALUES (:name,:initial,:phone,:sex,:age_value,"
            ":age_unit,:dob,:address,:notes,:created_at)",
            {**values, "created_at": now_str()},
        )
        return int(cur.lastrowid)


def recent_patients(limit: int = 500) -> List[dict]:
    """Patients ordered by their most recent visit, newest first."""
    return _rows(
        "SELECT p.*, "
        "  (SELECT MAX(j.received_at) FROM jobs j WHERE j.patient_id = p.id) AS last_visit "
        "FROM patients p ORDER BY last_visit DESC NULLS LAST, p.name LIMIT ?",
        (limit,))


def patient_count() -> int:
    return _row("SELECT COUNT(*) AS n FROM patients")["n"]


# ===========================================================================
# Staff accounts
# ===========================================================================

def _to_user(row: Optional[dict]) -> Optional[auth.User]:
    if not row:
        return None
    return auth.User(
        id=row["id"], username=row["username"],
        display_name=row["display_name"] or "", role=row["role"],
        permissions=auth.permissions_from_text(row["permissions"]),
        active=bool(row["active"]))


def list_users(include_inactive: bool = False) -> List[auth.User]:
    sql = "SELECT * FROM users"
    if not include_inactive:
        sql += " WHERE active = 1"
    return [_to_user(r) for r in _rows(sql + " ORDER BY role DESC, username")]


def user_count() -> int:
    row = _row("SELECT COUNT(*) AS n FROM users WHERE active = 1")
    return int((row or {}).get("n") or 0)


def get_user(user_id: int) -> Optional[auth.User]:
    return _to_user(_row("SELECT * FROM users WHERE id = ?", (user_id,)))


def get_user_by_name(username: str) -> Optional[auth.User]:
    return _to_user(_row("SELECT * FROM users WHERE username = ?",
                         (auth.normalise_username(username),)))


def user_pin_hash(user_id: int) -> str:
    """The stored hash for one account.

    Deliberately not on ``auth.User``: the hash has exactly one legitimate
    use -- checking a PIN somebody just typed -- and a field that travels
    round the program on every user object gets logged, printed and compared
    by accident. The one other caller is the default-PIN check.
    """
    row = _row("SELECT pin_hash FROM users WHERE id = ?", (int(user_id),))
    return (row or {}).get("pin_hash") or ""


def create_user(username: str, display_name: str, pin: str, role: str,
                permissions) -> int:
    """Create an account. Raises PinError / ValueError with a readable message."""
    problem = auth.check_username(username)
    if problem:
        raise ValueError(problem)
    clean = auth.normalise_username(username)
    if get_user_by_name(clean):
        raise ValueError(f"There is already an account called “{clean}”.")

    pin_hash = auth.hash_pin(pin)
    with transaction() as c:
        cur = c.execute(
            "INSERT INTO users (username, display_name, role, pin_hash, "
            "permissions, active, created_at) VALUES (?,?,?,?,?,1,?)",
            (clean, (display_name or "").strip(), role, pin_hash,
             auth.permissions_to_text(permissions), now_str()))
        uid = int(cur.lastrowid)
    log_action("user_created", "user", uid, f"{clean} ({role})")
    return uid


def update_user(user_id: int, display_name: Optional[str] = None,
                role: Optional[str] = None, permissions=None,
                active: Optional[bool] = None) -> None:
    sets, params = [], {"id": int(user_id)}
    if display_name is not None:
        sets.append("display_name = :display_name")
        params["display_name"] = display_name.strip()
    if role is not None:
        sets.append("role = :role")
        params["role"] = role
    if permissions is not None:
        sets.append("permissions = :permissions")
        params["permissions"] = auth.permissions_to_text(permissions)
    if active is not None:
        sets.append("active = :active")
        params["active"] = 1 if active else 0
    if not sets:
        return
    with transaction() as c:
        c.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = :id", params)
    log_action("user_changed", "user", user_id)


def set_user_pin(user_id: int, pin: str) -> None:
    pin_hash = auth.hash_pin(pin)
    with transaction() as c:
        c.execute("UPDATE users SET pin_hash = ? WHERE id = ?", (pin_hash, user_id))
    log_action("pin_changed", "user", user_id)


def check_pin(username: str, pin: str) -> bool:
    """Does this PIN belong to this active account?

    Separate from ``sign_in`` because approving somebody else's new account is
    not the same act as taking the counter: an administrator typing their PIN
    to authorise an account must not end up signed in as a side effect of it.
    Nothing here writes — no last_login, no current user, no audit entry.
    """
    row = _row("SELECT pin_hash FROM users WHERE username = ? AND active = 1",
               (auth.normalise_username(username),))
    return bool(row) and auth.verify_pin(pin, row["pin_hash"])


def sign_in(username: str, pin: str) -> Optional[auth.User]:
    """Check a username and PIN. Returns the user, or None."""
    row = _row("SELECT * FROM users WHERE username = ? AND active = 1",
               (auth.normalise_username(username),))
    if not row or not auth.verify_pin(pin, row["pin_hash"]):
        return None
    user = _to_user(row)
    with transaction() as c:
        c.execute("UPDATE users SET last_login = ? WHERE id = ?",
                  (now_str(), user.id))
    auth.set_current(user)
    log_action("signed_in", "user", user.id, user.username)
    return user


def last_admin_standing(user_id: int) -> bool:
    """True when this is the only active admin left.

    A lab that locks itself out of its own Settings has to call someone, so
    removing or demoting the last admin is refused.
    """
    row = _row("SELECT COUNT(*) AS n FROM users "
               "WHERE active = 1 AND role = 'admin' AND id <> ?", (user_id,))
    return int((row or {}).get("n") or 0) == 0


# ===========================================================================
# Referrers
# ===========================================================================

def list_referrers(include_inactive: bool = False) -> List[dict]:
    sql = "SELECT * FROM referrers"
    if not include_inactive:
        sql += " WHERE active = 1"
    return _rows(sql + " ORDER BY name")


REFERRER_FIELDS = ("name", "qualification", "profession", "hospital", "phone",
                   "commission_percent", "active")


def save_referrer(data: dict) -> int:
    """Insert or update a referring doctor.

    Every column is filled from the payload, defaulting rather than failing:
    callers that predate the profession and hospital columns -- the quick
    "add whatever was typed" path on the job screen -- must keep working.
    """
    payload = {k: data.get(k) for k in REFERRER_FIELDS}
    payload["name"] = (payload.get("name") or "").strip()
    for key in ("qualification", "profession", "hospital", "phone"):
        payload[key] = (payload.get(key) or "").strip()
    payload["commission_percent"] = float(payload.get("commission_percent") or 0)
    payload["active"] = 1 if payload.get("active") in (None, 1, True, "1") else 0

    with transaction() as c:
        if data.get("id"):
            payload["id"] = int(data["id"])
            c.execute(
                "UPDATE referrers SET name=:name, qualification=:qualification, "
                "profession=:profession, hospital=:hospital, phone=:phone, "
                "commission_percent=:commission_percent, active=:active "
                "WHERE id=:id", payload)
            return int(data["id"])
        cur = c.execute(
            "INSERT INTO referrers (name, qualification, profession, hospital, "
            "phone, commission_percent, active) "
            "VALUES (:name,:qualification,:profession,:hospital,:phone,"
            ":commission_percent,:active)", payload)
        return int(cur.lastrowid)


def search_referrers(term: str, include_inactive: bool = False) -> List[dict]:
    """Doctors matching a name, profession, hospital or phone fragment."""
    rows = list_referrers(include_inactive=include_inactive)
    term = (term or "").strip().lower()
    if not term:
        return rows
    digits = "".join(ch for ch in term if ch.isdigit())
    out = []
    for r in rows:
        haystack = " ".join(str(r[k] or "").lower() for k in
                            ("name", "qualification", "profession", "hospital"))
        phone = "".join(ch for ch in str(r["phone"] or "") if ch.isdigit())
        if term in haystack or (digits and len(digits) >= 3 and digits in phone):
            out.append(r)
    return out


def referrer_label(r: dict) -> str:
    """How a doctor reads in a picker: name, then where to find them."""
    if not r:
        return ""
    bits = [str(r.get("name") or "").strip()]
    where = " · ".join(x for x in (str(r.get("profession") or "").strip(),
                                   str(r.get("hospital") or "").strip()) if x)
    if where:
        bits.append(f"— {where}")
    return " ".join(bits)


def jobs_per_referrer() -> Dict[int, int]:
    """How many jobs each doctor has sent — the reason to keep them on the list."""
    return {int(r["referrer_id"]): int(r["n"]) for r in _rows(
        "SELECT referrer_id, COUNT(*) AS n FROM jobs "
        "WHERE referrer_id IS NOT NULL GROUP BY referrer_id")}


def referrer_jobs(referrer_id: int, limit: int = 300) -> List[dict]:
    """The work one doctor has sent, newest first, with what it billed."""
    return _rows(
        "SELECT j.id, j.report_no, j.received_at, j.status, p.name AS patient_name, "
        "  COALESCE(b.net_paise,0) AS net_paise, "
        "  COALESCE(cm.amount_paise,0) AS commission_paise "
        "FROM jobs j JOIN patients p ON p.id = j.patient_id "
        "LEFT JOIN bills b ON b.job_id = j.id "
        "LEFT JOIN commissions cm ON cm.job_id = j.id "
        "WHERE j.referrer_id = ? "
        "ORDER BY j.received_at DESC, j.id DESC LIMIT ?",
        (int(referrer_id), limit))


def referrer_totals(referrer_id: int) -> dict:
    """Everything this doctor has sent, billed and earned.

    Commission is split into what is still owed and what has been paid, since
    "you owe Dr Mehta 4,200" is the number that settles a month end.
    """
    r = _row(
        "SELECT COUNT(*) AS jobs, COALESCE(SUM(b.net_paise),0) AS billed "
        "FROM jobs j LEFT JOIN bills b ON b.job_id = j.id "
        "WHERE j.referrer_id = ?", (int(referrer_id),)) or {}
    c = _row(
        "SELECT COALESCE(SUM(amount_paise),0) AS total, "
        " COALESCE(SUM(CASE WHEN paid_at IS NULL THEN amount_paise ELSE 0 END),0) "
        "   AS owed "
        "FROM commissions WHERE referrer_id = ?", (int(referrer_id),)) or {}
    last = _row(
        "SELECT MAX(received_at) AS d FROM jobs WHERE referrer_id = ?",
        (int(referrer_id),)) or {}
    return {
        "jobs": int(r.get("jobs") or 0),
        "billed_paise": int(r.get("billed") or 0),
        "commission_paise": int(c.get("total") or 0),
        "owed_paise": int(c.get("owed") or 0),
        "last_referral": last.get("d"),
    }


def commission_owed(referrer_id: int) -> int:
    """Commission recorded against a doctor and not yet paid, in paise."""
    row = _row("SELECT COALESCE(SUM(amount_paise),0) AS owed FROM commissions "
               "WHERE referrer_id = ? AND paid_at IS NULL", (int(referrer_id),))
    return int(row["owed"]) if row else 0


def delete_referrer(rid: int) -> None:
    """Hide a doctor rather than deleting the row.

    Old jobs point at this doctor, and so do unpaid commissions; removing the
    row outright would leave both dangling.
    """
    with transaction() as c:
        c.execute("UPDATE referrers SET active = 0 WHERE id = ?", (int(rid),))
    log_action("referrer_hidden", "referrer", rid)


# ===========================================================================
# Tests and reference ranges
# ===========================================================================

TEST_FIELDS = ("code", "name", "group_name", "unit", "decimals", "result_type",
               "options", "formula", "rate_paise", "tat_hours", "sort_order",
               "active", "specimen", "separate_report", "interpretation")


def list_tests(include_inactive: bool = False) -> List[dict]:
    sql = "SELECT * FROM tests"
    if not include_inactive:
        sql += " WHERE active = 1"
    return _rows(sql + " ORDER BY group_name, sort_order, name")


def get_test(tid: int) -> Optional[dict]:
    return _row("SELECT * FROM tests WHERE id = ?", (tid,))


def get_test_by_code(code: str) -> Optional[dict]:
    return _row("SELECT * FROM tests WHERE upper(code) = upper(?)", ((code or "").strip(),))


def search_tests(term: str, limit: int = 40) -> List[dict]:
    t = f"%{(term or '').strip()}%"
    return _rows(
        "SELECT * FROM tests WHERE active = 1 AND (name LIKE ? OR code LIKE ? "
        "OR group_name LIKE ?) ORDER BY group_name, sort_order, name LIMIT ?",
        (t, t, t, limit),
    )


def test_groups() -> List[str]:
    return [r["group_name"] for r in
            _rows("SELECT DISTINCT group_name FROM tests ORDER BY group_name")
            if r["group_name"]]


def save_test(data: dict) -> int:
    """Save a test. A bad or circular formula is rejected here, not later."""
    f = (data.get("formula") or "").strip()
    if f:
        formula.parse(f)  # raises FormulaError with a readable message
        code = (data.get("code") or "").upper()
        others = {t["code"].upper(): (t["formula"] or "")
                  for t in list_tests(include_inactive=True)
                  if (t["formula"] or "").strip() and t["id"] != data.get("id")}
        others[code] = f
        cycles = formula.check_cycles(others)
        touching = [c for c in cycles if code in c]
        if touching:
            raise formula.FormulaError(
                "this formula creates a loop: " + " -> ".join(touching[0] + [touching[0][0]])
            )

    payload = {k: data.get(k) for k in TEST_FIELDS}
    payload["code"] = (payload.get("code") or "").strip().upper()
    payload["specimen"] = (payload.get("specimen") or "").strip()
    payload["separate_report"] = 1 if payload.get("separate_report") else 0
    payload["interpretation"] = (payload.get("interpretation") or "").strip()
    with transaction() as c:
        if data.get("id"):
            c.execute(
                "UPDATE tests SET code=:code, name=:name, group_name=:group_name, "
                "unit=:unit, decimals=:decimals, result_type=:result_type, "
                "options=:options, formula=:formula, rate_paise=:rate_paise, "
                "tat_hours=:tat_hours, sort_order=:sort_order, active=:active, "
                "specimen=:specimen, separate_report=:separate_report, "
                "interpretation=:interpretation "
                "WHERE id=:id", {**payload, "id": data["id"]})
            tid = int(data["id"])
        else:
            cur = c.execute(
                "INSERT INTO tests (code,name,group_name,unit,decimals,result_type,"
                "options,formula,rate_paise,tat_hours,sort_order,active,"
                "specimen,separate_report,interpretation) "
                "VALUES (:code,:name,:group_name,:unit,:decimals,:result_type,"
                ":options,:formula,:rate_paise,:tat_hours,:sort_order,:active,"
                ":specimen,:separate_report,:interpretation)", payload)
            tid = int(cur.lastrowid)
    log_action("test_saved", "test", tid, payload["code"])
    return tid


def delete_test(tid: int) -> None:
    """Deactivate rather than delete, so old reports still render."""
    with transaction() as c:
        c.execute("UPDATE tests SET active = 0 WHERE id = ?", (tid,))
    log_action("test_deactivated", "test", tid)


def ranges_for_test(tid: int) -> List[dict]:
    return _rows("SELECT * FROM reference_ranges WHERE test_id = ? ORDER BY id", (tid,))


def all_test_ranges() -> Dict[int, List[dict]]:
    rows = _rows("SELECT * FROM reference_ranges ORDER BY test_id, id")
    out: Dict[int, List[dict]] = {}
    for r in rows:
        out.setdefault(r["test_id"], []).append(r)
    return out


def replace_ranges(tid: int, rows: Sequence[dict]) -> None:
    with transaction() as c:
        c.execute("DELETE FROM reference_ranges WHERE test_id = ?", (tid,))
        for r in rows:
            c.execute(
                "INSERT INTO reference_ranges (test_id, rule_type, low, high, "
                "text_value, sex, age_min, age_max, display_text, note) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (tid, r.get("rule_type", "range"), r.get("low"), r.get("high"),
                 r.get("text_value", ""), r.get("sex", "any"), r.get("age_min"),
                 r.get("age_max"), r.get("display_text", ""), r.get("note", "")),
            )


def range_objects(tid: int) -> List[rng.ReferenceRange]:
    return [
        rng.ReferenceRange(
            rule_type=r["rule_type"], low=r["low"], high=r["high"],
            text_value=r["text_value"], sex=r["sex"], age_min=r["age_min"],
            age_max=r["age_max"], display_text=r["display_text"], note=r["note"],
        )
        for r in ranges_for_test(tid)
    ]


# ===========================================================================
# Panels
# ===========================================================================

def list_panels(quick_only: bool = False) -> List[dict]:
    sql = "SELECT * FROM panels WHERE active = 1"
    if quick_only:
        sql += " AND quick_button = 1"
    return _rows(sql + " ORDER BY sort_order, name")


def panel_test_ids(pid: int) -> List[int]:
    return [r["test_id"] for r in _rows(
        "SELECT pt.test_id FROM panel_tests pt JOIN tests t ON t.id = pt.test_id "
        "WHERE pt.panel_id = ? ORDER BY pt.sort_order", (pid,))]


def save_panel(data: dict, test_ids: Sequence[int]) -> int:
    with transaction() as c:
        if data.get("id"):
            c.execute("UPDATE panels SET name=:name, price_paise=:price_paise, "
                      "quick_button=:quick_button, sort_order=:sort_order, "
                      "active=:active WHERE id=:id", data)
            pid = int(data["id"])
        else:
            cur = c.execute(
                "INSERT INTO panels (name, price_paise, quick_button, sort_order, active) "
                "VALUES (:name,:price_paise,:quick_button,:sort_order,:active)", data)
            pid = int(cur.lastrowid)
        c.execute("DELETE FROM panel_tests WHERE panel_id = ?", (pid,))
        for i, tid in enumerate(test_ids):
            c.execute("INSERT INTO panel_tests (panel_id, test_id, sort_order) "
                      "VALUES (?,?,?)", (pid, tid, i))
    return pid


# ===========================================================================
# Jobs
# ===========================================================================

def _allocate_report_no(conn: sqlite3.Connection) -> int:
    """Allocate inside the caller's transaction.

    A crash between allocating and committing leaves a gap in the series, which
    is harmless. Two jobs sharing a number would not be.
    """
    row = conn.execute("SELECT value FROM settings WHERE key='next_report_no'").fetchone()
    current = numbering.normalise(row[0] if row else None)
    if current is None:
        current = numbering.normalise(config.DEFAULT_SETTINGS["next_report_no"]) or 1

    used = conn.execute("SELECT MAX(report_no) AS m FROM jobs").fetchone()["m"]
    if used is not None and int(used) >= current:
        current = int(used) + 1

    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('next_report_no', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(current + 1),),
    )
    return current


def create_job(patient_id: int, test_ids: Sequence[int],
               referrer_id: Optional[int] = None,
               received: Optional[datetime] = None,
               remarks: str = "") -> int:
    received = received or datetime.now()
    patient = get_patient(patient_id) or {}
    referrer = _row("SELECT * FROM referrers WHERE id = ?", (referrer_id,)) if referrer_id else None

    tats = []
    for tid in test_ids:
        t = get_test(tid)
        if t:
            tats.append(t["tat_hours"])
    due = turnaround.due_at(received, tats)

    age_text = _age_text(patient)

    with transaction() as c:
        report_no = _allocate_report_no(c)
        cur = c.execute(
            "INSERT INTO jobs (report_no, patient_id, referrer_id, received_at, "
            "due_at, status, name_at_test, age_at_test, sex_at_test, "
            "age_value_at_test, age_unit_at_test, referrer_name, "
            "remarks, revision_no) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
            (report_no, patient_id, referrer_id, dt_str(received), dt_str(due),
             turnaround.STATUS_DRAFT, patient_full_name(patient), age_text or "",
             patient.get("sex") or "",
             _as_number(patient.get("age_value")),
             (patient.get("age_unit") or "years"),
             (referrer or {}).get("name") or "",
             remarks or ""),
        )
        job_id = int(cur.lastrowid)
        for i, tid in enumerate(test_ids):
            c.execute("INSERT OR IGNORE INTO job_tests (job_id, test_id, sort_order) "
                      "VALUES (?,?,?)", (job_id, tid, i))
    log_action("job_created", "job", job_id, f"report {report_no}")
    return job_id


def _as_number(value) -> Optional[float]:
    """A typed age of 'abc' must not crash job creation."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def age_text(patient: dict) -> str:
    """"10 Days", "3 Years" -- the age as it prints on a report."""
    return _age_text(patient)


def _age_text(patient: dict) -> str:
    v = _as_number(patient.get("age_value"))
    if v is None:
        return ""
    unit = (patient.get("age_unit") or "years").strip().lower()
    n = int(v) if v == int(v) else v
    label = {"years": "Years", "months": "Months", "days": "Days"}.get(unit, unit.title())
    return f"{n} {label}"


def get_job(job_id: int) -> Optional[dict]:
    return _row(
        "SELECT j.*, p.name AS patient_name, p.phone AS patient_phone, "
        "p.sex AS patient_sex, p.age_value, p.age_unit, p.address "
        "FROM jobs j JOIN patients p ON p.id = j.patient_id WHERE j.id = ?",
        (job_id,),
    )


def update_job(job_id: int, **fields) -> None:
    if not fields:
        return
    # Anything not named here is silently ignored, so a column added later has
    # to be added here as well: extra_pdfs was being written and thrown away,
    # which left the detail sheets unfindable after the job was closed.
    # age_*_at_test belong here for the same reason name_at_test does: the
    # report prints the age the patient was ON THE DAY, and the reference
    # range is chosen by it. Leaving them out meant a corrected age reached
    # the screen and the patient record but never the report -- a 10-day-old
    # whose age was mistyped as 30 years had their haemoglobin flagged HIGH
    # against the adult range.
    allowed = {"age_at_test", "age_value_at_test", "age_unit_at_test",
               "referrer_id", "referrer_name", "status", "remarks", "reported_at",
               "sent_at", "sent_via", "pdf_path", "extra_pdfs", "due_at",
               "received_at", "name_at_test", "age_at_test", "sex_at_test"}
    sets = {k: v for k, v in fields.items() if k in allowed}
    if not sets:
        return
    clause = ", ".join(f"{k} = :{k}" for k in sets)
    with transaction() as c:
        c.execute(f"UPDATE jobs SET {clause} WHERE id = :id", {**sets, "id": job_id})

    # The referring doctor drives the commission, so changing one must move the
    # money too. Otherwise the ledger shows the new doctor while the old one is
    # still owed the payment.
    if "referrer_id" in sets:
        bill = get_bill(job_id)
        _sync_commission(job_id, int(bill["net_paise"]) if bill else 0)


def set_job_tests(job_id: int, test_ids: Sequence[int]) -> None:
    """Replace the test list, keeping results for tests that stay."""
    keep = set(int(t) for t in test_ids)
    with transaction() as c:
        existing = {r["test_id"]: r["id"] for r in
                    c.execute("SELECT id, test_id FROM job_tests WHERE job_id = ?",
                              (job_id,)).fetchall()}
        for tid, jt_id in existing.items():
            if tid not in keep:
                c.execute("DELETE FROM job_tests WHERE id = ?", (jt_id,))
        for i, tid in enumerate(test_ids):
            if tid in existing:
                c.execute("UPDATE job_tests SET sort_order = ? WHERE id = ?",
                          (i, existing[tid]))
            else:
                c.execute("INSERT INTO job_tests (job_id, test_id, sort_order) "
                          "VALUES (?,?,?)", (job_id, tid, i))
        tats = [r["tat_hours"] for r in c.execute(
            "SELECT t.tat_hours FROM job_tests jt JOIN tests t ON t.id = jt.test_id "
            "WHERE jt.job_id = ?", (job_id,)).fetchall()]
        received = to_dt(c.execute("SELECT received_at FROM jobs WHERE id = ?",
                                   (job_id,)).fetchone()["received_at"])
        if received:
            c.execute("UPDATE jobs SET due_at = ? WHERE id = ?",
                      (dt_str(turnaround.due_at(received, tats)), job_id))


def job_tests(job_id: int) -> List[dict]:
    return _rows(
        "SELECT jt.id AS job_test_id, jt.not_done, jt.sort_order, t.* "
        "FROM job_tests jt JOIN tests t ON t.id = jt.test_id "
        "WHERE jt.job_id = ? ORDER BY jt.sort_order, t.group_name, t.sort_order",
        (job_id,),
    )


def set_not_done(job_test_id: int, flag: bool) -> None:
    with transaction() as c:
        c.execute("UPDATE job_tests SET not_done = ? WHERE id = ?",
                  (1 if flag else 0, job_test_id))


def delete_job(job_id: int) -> None:
    job = get_job(job_id)
    with transaction() as c:
        c.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    log_action("job_deleted", "job", job_id,
               f"report {job.get('report_no')}" if job else "")


# ---------------------------------------------------------------- queue

def list_jobs(scope: str = "today", term: str = "", limit: int = 500) -> List[dict]:
    where: List[str] = []
    params: List = []
    term = (term or "").strip()

    if term:
        t = f"%{term}%"
        where.append("(p.name LIKE ? OR p.phone LIKE ? OR CAST(j.report_no AS TEXT) LIKE ?)")
        params += [t, t, t]
    elif scope == "today":
        where.append("date(j.received_at) = date('now','localtime')")
    elif scope == "pending":
        where.append("j.status IN ('draft','in_progress')")
    elif scope == "overdue":
        where.append("j.status IN ('draft','in_progress') AND j.due_at < datetime('now','localtime')")
    elif scope == "ready":
        where.append("j.status = 'ready'")
    elif scope == "unpaid":
        where.append(
            "EXISTS (SELECT 1 FROM bills b WHERE b.job_id = j.id AND b.net_paise > "
            "COALESCE((SELECT SUM(amount_paise) FROM payments pm WHERE pm.bill_id = b.id),0))")

    sql = (
        "SELECT j.*, p.name AS patient_name, p.phone AS patient_phone, "
        "  (SELECT COUNT(*) FROM job_tests jt WHERE jt.job_id = j.id) AS n_tests, "
        # LEFT JOIN: a test marked "not done" has no results row, but it has
        # been dealt with and must count towards progress.
        "  (SELECT COUNT(*) FROM job_tests jt LEFT JOIN results r ON r.job_test_id = jt.id "
        "     WHERE jt.job_id = j.id "
        "       AND (COALESCE(r.display_value,'') <> '' OR jt.not_done = 1)) AS n_done, "
        "  (SELECT GROUP_CONCAT(t.name, ', ') FROM job_tests jt "
        "     JOIN tests t ON t.id = jt.test_id WHERE jt.job_id = j.id) AS test_names, "
        "  b.net_paise AS net_paise, "
        "  COALESCE((SELECT SUM(amount_paise) FROM payments pm WHERE pm.bill_id = b.id),0) AS paid_paise "
        "FROM jobs j JOIN patients p ON p.id = j.patient_id "
        "LEFT JOIN bills b ON b.job_id = j.id "
    )
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY j.received_at DESC, j.id DESC LIMIT ?"
    params.append(limit)
    return _rows(sql, params)


def queue_counts() -> Dict[str, int]:
    """The numbers along the top of the work queue.

    ``waiting`` and ``in_progress`` split ``pending`` in two, because "nothing
    typed yet" and "half typed" are different problems at the bench: the first
    is waiting for a sample, the second is waiting for a person.
    """
    q = _row(
        "SELECT "
        " (SELECT COUNT(*) FROM jobs WHERE date(received_at)=date('now','localtime')) AS today, "
        " (SELECT COUNT(*) FROM jobs WHERE status IN ('draft','in_progress')) AS pending, "
        " (SELECT COUNT(*) FROM jobs WHERE status='draft') AS waiting, "
        " (SELECT COUNT(*) FROM jobs WHERE status='in_progress') AS in_progress, "
        " (SELECT COUNT(*) FROM jobs WHERE status IN ('draft','in_progress') "
        "   AND due_at < datetime('now','localtime')) AS overdue, "
        " (SELECT COUNT(*) FROM jobs WHERE status='ready') AS ready, "
        " (SELECT COUNT(*) FROM jobs) AS total"
    )
    return {k: int(v or 0) for k, v in (q or {}).items()}


def oldest_overdue_at() -> Optional[str]:
    """When the longest-waiting late job was due, or None if nothing is late.

    "2 overdue" tells the operator there is a problem; "oldest 1h 12m" tells
    them how big it is, which is what decides whether it can wait.
    """
    r = _row(
        "SELECT MIN(due_at) AS d FROM jobs "
        "WHERE status IN ('draft','in_progress') "
        "  AND due_at < datetime('now','localtime')")
    return (r or {}).get("d")


def patient_money(patient_id: int) -> dict:
    """What this patient has been charged, has paid, and still owes.

    Summed over every bill on every one of their jobs, so a person who has
    been in nine times is one figure at the counter rather than nine.
    """
    r = _row(
        "SELECT COALESCE(SUM(b.net_paise),0) AS billed, "
        " COALESCE(SUM((SELECT COALESCE(SUM(pm.amount_paise),0) FROM payments pm "
        "                WHERE pm.bill_id = b.id)),0) AS paid "
        "FROM bills b JOIN jobs j ON j.id = b.job_id "
        "WHERE j.patient_id = ?", (patient_id,)) or {}
    billed = int(r.get("billed") or 0)
    paid = int(r.get("paid") or 0)
    return {"billed_paise": billed, "paid_paise": paid,
            "outstanding_paise": max(0, billed - paid)}


def patient_jobs(patient_id: int) -> List[dict]:
    return _rows(
        "SELECT j.*, (SELECT COUNT(*) FROM job_tests jt WHERE jt.job_id=j.id) AS n_tests "
        "FROM jobs j WHERE j.patient_id = ? ORDER BY j.received_at DESC, j.id DESC", (patient_id,))


def previous_results(patient_id: int, test_id: int, before_job: Optional[int] = None,
                     limit: int = 6) -> List[dict]:
    sql = ("SELECT j.report_no, j.received_at, r.display_value, r.flag "
           "FROM jobs j JOIN job_tests jt ON jt.job_id = j.id "
           "JOIN results r ON r.job_test_id = jt.id "
           "WHERE j.patient_id = ? AND jt.test_id = ? AND r.display_value <> '' ")
    params: List = [patient_id, test_id]
    if before_job:
        sql += "AND j.id <> ? "
        params.append(before_job)
    # j.id breaks the tie when two jobs share a received_at to the second,
    # which happens routinely when a patient is registered twice in a minute.
    sql += "ORDER BY j.received_at DESC, j.id DESC LIMIT ?"
    params.append(limit)
    return _rows(sql, params)


# ===========================================================================
# Results
# ===========================================================================

def results_for_job(job_id: int) -> Dict[int, dict]:
    rows = _rows(
        "SELECT r.* FROM results r JOIN job_tests jt ON jt.id = r.job_test_id "
        "WHERE jt.job_id = ?", (job_id,))
    return {r["job_test_id"]: r for r in rows}


def save_result(job_test_id: int, raw_value: str, computed: Optional[float],
                display: str, range_text: str, flag: str) -> None:
    with transaction() as c:
        c.execute(
            "INSERT INTO results (job_test_id, raw_value, computed_value, "
            "display_value, range_text, flag, entered_at) VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(job_test_id) DO UPDATE SET raw_value=excluded.raw_value, "
            "computed_value=excluded.computed_value, display_value=excluded.display_value, "
            "range_text=excluded.range_text, flag=excluded.flag, entered_at=excluded.entered_at",
            (job_test_id, raw_value, computed, display, range_text, flag, now_str()),
        )


def job_is_complete(job_id: int) -> Tuple[bool, List[str]]:
    """Every test must have a value or be marked not done. Returns (ok, missing)."""
    rows = _rows(
        "SELECT t.name, t.result_type, jt.not_done, COALESCE(r.display_value,'') AS dv "
        "FROM job_tests jt JOIN tests t ON t.id = jt.test_id "
        "LEFT JOIN results r ON r.job_test_id = jt.id WHERE jt.job_id = ?", (job_id,))
    missing = [r["name"] for r in rows if not r["not_done"]
               and (r.get("result_type") or "").strip().lower() != "heading"
               and not r["dv"].strip()]
    return (len(rows) > 0 and not missing), missing


def job_progress(job_id: int) -> Tuple[int, int]:
    """(done, total) where a test marked not done counts as dealt with."""
    row = _row(
        "SELECT COUNT(*) AS total, "
        " SUM(CASE WHEN jt.not_done = 1 OR t.result_type = 'heading' "
        "          OR COALESCE(r.display_value,'') <> '' "
        "     THEN 1 ELSE 0 END) AS done "
        "FROM job_tests jt JOIN tests t ON t.id = jt.test_id "
        "LEFT JOIN results r ON r.job_test_id = jt.id "
        "WHERE jt.job_id = ?", (job_id,))
    return int((row or {}).get("done") or 0), int((row or {}).get("total") or 0)


# ===========================================================================
# Billing
# ===========================================================================

def get_bill(job_id: int) -> Optional[dict]:
    return _row("SELECT * FROM bills WHERE job_id = ?", (job_id,))


def job_money(job_id: int) -> dict:
    """What one job is worth, counted exactly as the Billing ledger counts it.

    The POS receipt used to read ``charged_paise`` and ``paid_paise`` off the
    bill row. Neither column exists — the bill holds gross/discount/net, and
    what has been paid is the sum of the payments table — so both reads fell
    back to their defaults and every slip printed "fully paid, balance
    ₹0.00" no matter what was actually owed. One query now, shared, so the
    slip and the ledger cannot disagree again.
    """
    row = _row(
        "SELECT COALESCE(b.id, 0) AS bill_id, "
        "  COALESCE(b.gross_paise, 0) AS gross_paise, "
        "  COALESCE(b.discount_paise, 0) AS discount_paise, "
        "  COALESCE(b.net_paise, 0) AS net_paise, "
        "  COALESCE(b.discount_type, '') AS discount_type, "
        "  COALESCE((SELECT SUM(amount_paise) FROM payments pm "
        "            WHERE pm.bill_id = b.id), 0) AS paid_paise "
        "FROM jobs j LEFT JOIN bills b ON b.job_id = j.id WHERE j.id = ?",
        (job_id,))
    money = dict(row or {"bill_id": 0, "gross_paise": 0, "discount_paise": 0,
                         "net_paise": 0, "discount_type": "", "paid_paise": 0})
    money["balance_paise"] = int(money["net_paise"]) - int(money["paid_paise"])
    money["billed"] = bool(money["bill_id"])
    return money


def bill_items(bill_id: int) -> List[dict]:
    return _rows("SELECT * FROM bill_items WHERE bill_id = ? ORDER BY id", (bill_id,))


def bill_payments(bill_id: int) -> List[dict]:
    return _rows("SELECT * FROM payments WHERE bill_id = ? ORDER BY id", (bill_id,))


def save_bill(job_id: int, items: Sequence[dict], discount_type: str,
              discount_value: float, note: str = "") -> int:
    line_items = [billing.LineItem(i["label"], int(i["rate_paise"]), int(i.get("qty", 1)))
                  for i in items]
    totals = billing.compute_totals(line_items, discount_type, discount_value)

    with transaction() as c:
        existing = c.execute("SELECT id FROM bills WHERE job_id = ?", (job_id,)).fetchone()
        if existing:
            bill_id = int(existing["id"])
            c.execute("UPDATE bills SET gross_paise=?, discount_type=?, discount_value=?, "
                      "discount_paise=?, net_paise=?, note=? WHERE id=?",
                      (totals.gross_paise, discount_type, discount_value,
                       totals.discount_paise, totals.net_paise, note, bill_id))
            c.execute("DELETE FROM bill_items WHERE bill_id = ?", (bill_id,))
        else:
            cur = c.execute(
                "INSERT INTO bills (job_id, gross_paise, discount_type, discount_value, "
                "discount_paise, net_paise, created_at, note) VALUES (?,?,?,?,?,?,?,?)",
                (job_id, totals.gross_paise, discount_type, discount_value,
                 totals.discount_paise, totals.net_paise, now_str(), note))
            bill_id = int(cur.lastrowid)
        for i in items:
            c.execute("INSERT INTO bill_items (bill_id, label, test_id, panel_id, "
                      "rate_paise, qty) VALUES (?,?,?,?,?,?)",
                      (bill_id, i["label"], i.get("test_id"), i.get("panel_id"),
                       int(i["rate_paise"]), int(i.get("qty", 1))))

    _sync_commission(job_id, totals.net_paise)
    log_action("bill_saved", "job", job_id, billing.format_rupees(totals.net_paise))
    return bill_id


def add_payment(bill_id: int, amount_paise: int, mode: str = "cash", note: str = "") -> None:
    with transaction() as c:
        c.execute("INSERT INTO payments (bill_id, amount_paise, mode, paid_at, note) "
                  "VALUES (?,?,?,?,?)", (bill_id, int(amount_paise), mode, now_str(), note))
    log_action("payment_added", "bill", bill_id, billing.format_rupees(amount_paise))


def delete_payment(payment_id: int) -> None:
    with transaction() as c:
        c.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
    log_action("payment_deleted", "payment", payment_id)


def bill_totals(job_id: int) -> billing.BillTotals:
    bill = get_bill(job_id)
    if not bill:
        return billing.BillTotals()
    pays = [billing.Payment(int(p["amount_paise"]), p["mode"])
            for p in bill_payments(bill["id"])]
    paid = sum(p.amount_paise for p in pays)
    return billing.BillTotals(
        gross_paise=int(bill["gross_paise"]),
        discount_paise=int(bill["discount_paise"]),
        net_paise=int(bill["net_paise"]),
        paid_paise=paid,
        balance_paise=int(bill["net_paise"]) - paid,
    )


def _sync_commission(job_id: int, net_paise: int) -> None:
    job = _row("SELECT referrer_id FROM jobs WHERE id = ?", (job_id,))
    if not job or not job["referrer_id"]:
        with transaction() as c:
            c.execute("DELETE FROM commissions WHERE job_id = ?", (job_id,))
        return
    ref = _row("SELECT * FROM referrers WHERE id = ?", (job["referrer_id"],))
    if not ref:
        return
    pct = float(ref["commission_percent"] or 0)
    amount = billing.commission_for(net_paise, pct)
    with transaction() as c:
        c.execute(
            "INSERT INTO commissions (job_id, referrer_id, base_paise, percent, amount_paise) "
            "VALUES (?,?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET "
            "referrer_id=excluded.referrer_id, base_paise=excluded.base_paise, "
            "percent=excluded.percent, amount_paise=excluded.amount_paise",
            (job_id, ref["id"], net_paise, pct, amount))


def ledger(date_from: Optional[datetime] = None, date_to: Optional[datetime] = None,
           unpaid_only: bool = False, referrer_id: Optional[int] = None) -> List[dict]:
    where = ["1=1"]
    params: List = []
    if date_from:
        where.append("date(j.received_at) >= date(?)")
        params.append(dt_str(date_from))
    if date_to:
        where.append("date(j.received_at) <= date(?)")
        params.append(dt_str(date_to))
    if referrer_id:
        where.append("j.referrer_id = ?")
        params.append(referrer_id)

    sql = (
        "SELECT j.id AS job_id, j.report_no, j.received_at, "
        "  j.name_at_test AS patient_name, p.phone AS patient_phone, "
        "  j.referrer_name, b.id AS bill_id, "
        "  COALESCE(b.gross_paise,0) AS gross_paise, "
        "  COALESCE(b.discount_paise,0) AS discount_paise, "
        "  COALESCE(b.net_paise,0) AS net_paise, "
        "  COALESCE((SELECT SUM(amount_paise) FROM payments pm WHERE pm.bill_id=b.id),0) AS paid_paise, "
        "  COALESCE(cm.amount_paise,0) AS commission_paise "
        "FROM jobs j JOIN patients p ON p.id = j.patient_id "
        "LEFT JOIN bills b ON b.job_id = j.id "
        "LEFT JOIN commissions cm ON cm.job_id = j.id "
        "WHERE " + " AND ".join(where) + " ORDER BY j.received_at DESC, j.id DESC"
    )
    rows = _rows(sql, params)
    for r in rows:
        r["balance_paise"] = int(r["net_paise"]) - int(r["paid_paise"])
    if unpaid_only:
        rows = [r for r in rows if r["balance_paise"] > 0]
    return rows


# ===========================================================================
# Summaries
# ===========================================================================

def day_book(day: datetime) -> dict:
    """One day's money, counted from the ledger rather than estimated.

    Every figure here is a sum over rows that exist: what was charged, what
    was taken off, what was collected, what is still owed, and what the
    referring doctors have earned. Nothing is a percentage of something else
    -- a commission the lab has not actually accrued must never appear on a
    screen headed with the day's takings.
    """
    d = day.strftime("%Y-%m-%d")
    money = _row(
        "SELECT COUNT(*) AS jobs, "
        " COALESCE(SUM(b.gross_paise),0) AS gross, "
        " COALESCE(SUM(b.discount_paise),0) AS discount, "
        " COALESCE(SUM(b.net_paise),0) AS net, "
        " COALESCE(SUM((SELECT COALESCE(SUM(pm.amount_paise),0) FROM payments pm "
        "                WHERE pm.bill_id = b.id)),0) AS paid_on_these "
        "FROM jobs j LEFT JOIN bills b ON b.job_id = j.id "
        "WHERE date(j.received_at) = ?", (d,)) or {}
    # Money that came over the counter today, whichever day the bill is from.
    # It answers "what is in the drawer", which is a different question from
    # "what did today's work earn", and both belong on the day book.
    taken = _row(
        "SELECT COALESCE(SUM(amount_paise),0) AS c FROM payments "
        "WHERE date(paid_at) = ?", (d,)) or {}
    owed = _row(
        "SELECT COALESCE(SUM(cm.amount_paise),0) AS c FROM commissions cm "
        "JOIN jobs j ON j.id = cm.job_id WHERE date(j.received_at) = ?", (d,)) or {}
    unbilled = _row(
        "SELECT COUNT(*) AS n FROM jobs j "
        "WHERE date(j.received_at) = ? "
        "  AND NOT EXISTS (SELECT 1 FROM bills b WHERE b.job_id = j.id)", (d,)) or {}
    tests = _rows(
        "SELECT t.group_name AS name, COUNT(*) AS n FROM job_tests jt "
        "JOIN tests t ON t.id = jt.test_id JOIN jobs j ON j.id = jt.job_id "
        "WHERE date(j.received_at) = ? GROUP BY t.group_name "
        "ORDER BY n DESC, t.group_name LIMIT 8", (d,))
    doctors = _rows(
        "SELECT r.name AS name, COUNT(*) AS jobs, "
        " COALESCE(SUM(cm.amount_paise),0) AS commission "
        "FROM commissions cm JOIN referrers r ON r.id = cm.referrer_id "
        "JOIN jobs j ON j.id = cm.job_id WHERE date(j.received_at) = ? "
        "GROUP BY r.id ORDER BY commission DESC, r.name LIMIT 8", (d,))

    net = int(money.get("net") or 0)
    paid_on_these = int(money.get("paid_on_these") or 0)
    return {
        "date": day,
        "jobs": int(money.get("jobs") or 0),
        "unbilled": int(unbilled.get("n") or 0),
        "gross_paise": int(money.get("gross") or 0),
        "discount_paise": int(money.get("discount") or 0),
        "net_paise": net,
        "collected_paise": int(taken.get("c") or 0),
        "outstanding_paise": max(0, net - paid_on_these),
        "commission_paise": int(owed.get("c") or 0),
        "tests": tests,
        "doctors": doctors,
    }


def day_summary(day: datetime) -> dict:
    d = day.strftime("%Y-%m-%d")
    head = _row(
        "SELECT COUNT(*) AS jobs, "
        " SUM(CASE WHEN status='sent' THEN 1 ELSE 0 END) AS sent, "
        " SUM(CASE WHEN status IN ('draft','in_progress') THEN 1 ELSE 0 END) AS pending "
        "FROM jobs WHERE date(received_at) = ?", (d,)) or {}
    money = _row(
        "SELECT COALESCE(SUM(b.net_paise),0) AS billed, "
        " COALESCE((SELECT SUM(pm.amount_paise) FROM payments pm "
        "   WHERE date(pm.paid_at) = ?),0) AS collected "
        "FROM bills b JOIN jobs j ON j.id = b.job_id WHERE date(j.received_at) = ?",
        (d, d)) or {}
    tests = _rows(
        "SELECT t.name, COUNT(*) AS n FROM job_tests jt "
        "JOIN tests t ON t.id = jt.test_id JOIN jobs j ON j.id = jt.job_id "
        "WHERE date(j.received_at) = ? GROUP BY t.id ORDER BY n DESC, t.name", (d,))
    return {
        "date": day, "jobs": int(head.get("jobs") or 0),
        "sent": int(head.get("sent") or 0), "pending": int(head.get("pending") or 0),
        "billed_paise": int(money.get("billed") or 0),
        "collected_paise": int(money.get("collected") or 0),
        "tests": tests,
    }


def month_summary(year: int, month: int) -> dict:
    start = datetime(year, month, 1)
    end = datetime(year + (month == 12), (month % 12) + 1, 1) - timedelta(seconds=1)
    a, b = dt_str(start), dt_str(end)
    by_day = _rows(
        "SELECT date(j.received_at) AS d, COUNT(*) AS jobs, "
        " COALESCE(SUM(bl.net_paise),0) AS billed "
        "FROM jobs j LEFT JOIN bills bl ON bl.job_id = j.id "
        "WHERE j.received_at BETWEEN ? AND ? GROUP BY d ORDER BY d", (a, b))
    tests = _rows(
        "SELECT t.name, COUNT(*) AS n FROM job_tests jt "
        "JOIN tests t ON t.id = jt.test_id JOIN jobs j ON j.id = jt.job_id "
        "WHERE j.received_at BETWEEN ? AND ? GROUP BY t.id ORDER BY n DESC", (a, b))
    refs = _rows(
        "SELECT r.name, COUNT(*) AS jobs, COALESCE(SUM(cm.amount_paise),0) AS commission "
        "FROM commissions cm JOIN referrers r ON r.id = cm.referrer_id "
        "JOIN jobs j ON j.id = cm.job_id WHERE j.received_at BETWEEN ? AND ? "
        "GROUP BY r.id ORDER BY commission DESC", (a, b))
    collected = _row(
        "SELECT COALESCE(SUM(amount_paise),0) AS c FROM payments WHERE paid_at BETWEEN ? AND ?",
        (a, b))["c"]
    return {
        "year": year, "month": month, "by_day": by_day, "tests": tests,
        "referrers": refs, "collected_paise": int(collected or 0),
        "billed_paise": sum(int(r["billed"]) for r in by_day),
        "jobs": sum(int(r["jobs"]) for r in by_day),
    }
