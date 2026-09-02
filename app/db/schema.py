"""Database schema and forward-only migrations.

Adding a column later means appending a new entry to MIGRATIONS. The program
records the applied version, takes a backup before touching anything, and
applies only what is missing. Existing data is never dropped.
"""

from __future__ import annotations

import sqlite3
from typing import Callable, List, Optional, Tuple

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS patients (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    phone       TEXT DEFAULT '',
    sex         TEXT DEFAULT '',
    age_value   REAL,
    age_unit    TEXT DEFAULT 'years',
    dob         TEXT DEFAULT '',
    address     TEXT DEFAULT '',
    notes       TEXT DEFAULT '',
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_patients_name  ON patients(name);
CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients(phone);

CREATE TABLE IF NOT EXISTS referrers (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    qualification       TEXT DEFAULT '',
    phone               TEXT DEFAULT '',
    commission_percent  REAL NOT NULL DEFAULT 0,
    active              INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS tests (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    code         TEXT NOT NULL UNIQUE,
    name         TEXT NOT NULL,
    group_name   TEXT NOT NULL DEFAULT '',
    unit         TEXT DEFAULT '',
    decimals     INTEGER NOT NULL DEFAULT 1,
    result_type  TEXT NOT NULL DEFAULT 'numeric',   -- numeric | text | option
    options      TEXT DEFAULT '',                   -- 'Positive|Negative'
    formula      TEXT DEFAULT '',
    rate_paise   INTEGER NOT NULL DEFAULT 0,
    tat_hours    REAL NOT NULL DEFAULT 24,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    active       INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_tests_group ON tests(group_name, sort_order);

CREATE TABLE IF NOT EXISTS reference_ranges (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id       INTEGER NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    rule_type     TEXT NOT NULL DEFAULT 'range',    -- range | max | min | text
    low           REAL,
    high          REAL,
    text_value    TEXT DEFAULT '',
    sex           TEXT NOT NULL DEFAULT 'any',      -- M | F | any
    age_min       REAL,
    age_max       REAL,
    display_text  TEXT DEFAULT '',
    note          TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_ranges_test ON reference_ranges(test_id);

CREATE TABLE IF NOT EXISTS panels (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    price_paise   INTEGER,                          -- NULL = sum of members
    quick_button  INTEGER NOT NULL DEFAULT 0,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    active        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS panel_tests (
    panel_id    INTEGER NOT NULL REFERENCES panels(id) ON DELETE CASCADE,
    test_id     INTEGER NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (panel_id, test_id)
);

CREATE TABLE IF NOT EXISTS jobs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    report_no     INTEGER NOT NULL,
    patient_id    INTEGER NOT NULL REFERENCES patients(id),
    referrer_id   INTEGER REFERENCES referrers(id),
    received_at   TEXT NOT NULL,
    due_at        TEXT,
    reported_at   TEXT,
    status        TEXT NOT NULL DEFAULT 'draft',
    name_at_test  TEXT NOT NULL DEFAULT '',
    age_at_test   TEXT NOT NULL DEFAULT '',
    sex_at_test   TEXT NOT NULL DEFAULT '',
    referrer_name TEXT NOT NULL DEFAULT '',
    remarks       TEXT DEFAULT '',
    revision_no   INTEGER NOT NULL DEFAULT 1,
    sent_at       TEXT,
    sent_via      TEXT DEFAULT '',
    pdf_path      TEXT DEFAULT ''
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_reportno ON jobs(report_no, revision_no);
CREATE INDEX IF NOT EXISTS idx_jobs_patient  ON jobs(patient_id);
CREATE INDEX IF NOT EXISTS idx_jobs_received ON jobs(received_at);
CREATE INDEX IF NOT EXISTS idx_jobs_status   ON jobs(status);

CREATE TABLE IF NOT EXISTS job_tests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    test_id     INTEGER NOT NULL REFERENCES tests(id),
    sort_order  INTEGER NOT NULL DEFAULT 0,
    not_done    INTEGER NOT NULL DEFAULT 0,
    UNIQUE (job_id, test_id)
);
CREATE INDEX IF NOT EXISTS idx_jobtests_job ON job_tests(job_id);
CREATE INDEX IF NOT EXISTS idx_jobtests_test ON job_tests(test_id);

CREATE TABLE IF NOT EXISTS results (
    job_test_id     INTEGER PRIMARY KEY REFERENCES job_tests(id) ON DELETE CASCADE,
    raw_value       TEXT DEFAULT '',
    computed_value  REAL,
    display_value   TEXT DEFAULT '',
    range_text      TEXT DEFAULT '',
    flag            TEXT DEFAULT '',
    entered_at      TEXT
);

CREATE TABLE IF NOT EXISTS bills (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          INTEGER NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    gross_paise     INTEGER NOT NULL DEFAULT 0,
    discount_type   TEXT NOT NULL DEFAULT 'percent',
    discount_value  REAL NOT NULL DEFAULT 0,
    discount_paise  INTEGER NOT NULL DEFAULT 0,
    net_paise       INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    note            TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS bill_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id     INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    label       TEXT NOT NULL,
    test_id     INTEGER,
    panel_id    INTEGER,
    rate_paise  INTEGER NOT NULL DEFAULT 0,
    qty         INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_billitems_bill ON bill_items(bill_id);

CREATE TABLE IF NOT EXISTS payments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id       INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    amount_paise  INTEGER NOT NULL DEFAULT 0,
    mode          TEXT NOT NULL DEFAULT 'cash',
    paid_at       TEXT NOT NULL,
    note          TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_payments_bill ON payments(bill_id);

CREATE TABLE IF NOT EXISTS commissions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id        INTEGER NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    referrer_id   INTEGER NOT NULL REFERENCES referrers(id),
    base_paise    INTEGER NOT NULL DEFAULT 0,
    percent       REAL NOT NULL DEFAULT 0,
    amount_paise  INTEGER NOT NULL DEFAULT 0,
    paid_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_commissions_ref ON commissions(referrer_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    at          TEXT NOT NULL,
    action      TEXT NOT NULL,
    entity      TEXT DEFAULT '',
    entity_id   INTEGER,
    detail      TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_audit_at ON audit_log(at);
"""


def _m001(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_V1)


def _m002(conn: sqlite3.Connection) -> None:
    """Store the patient's age numerically on the job.

    Reference ranges depend on age, and jobs previously kept only the printed
    text ("31 Years"). Selecting ranges from the patient's *current* age meant a
    report reprinted later could silently show a different Normal Value column
    than the one originally issued.
    """
    cols = {r[1] for r in conn.execute("PRAGMA table_info(jobs)")}
    if "age_value_at_test" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN age_value_at_test REAL")
    if "age_unit_at_test" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN age_unit_at_test TEXT DEFAULT 'years'")

    # Backfill from the text already stored, e.g. "31 Years" -> 31, years.
    for row in conn.execute(
            "SELECT id, age_at_test FROM jobs WHERE age_value_at_test IS NULL").fetchall():
        value, unit = _parse_age_text(row[1])
        if value is not None:
            conn.execute(
                "UPDATE jobs SET age_value_at_test = ?, age_unit_at_test = ? WHERE id = ?",
                (value, unit, row[0]))


def _parse_age_text(text) -> Tuple[Optional[float], str]:
    import re

    if not text:
        return None, "years"
    m = re.match(r"\s*(\d+(?:\.\d+)?)\s*([A-Za-z]*)", str(text))
    if not m:
        return None, "years"
    unit = (m.group(2) or "years").lower()
    if unit.startswith("m"):
        unit = "months"
    elif unit.startswith("d"):
        unit = "days"
    else:
        unit = "years"
    return float(m.group(1)), unit


# Append-only. Never edit or reorder an existing entry: labs in the field have
# already applied it, and the version number is how the program knows.
def _m003(conn: sqlite3.Connection) -> None:
    """Staff accounts with per-person permissions, and who did what."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT NOT NULL UNIQUE,
        display_name  TEXT NOT NULL DEFAULT '',
        role          TEXT NOT NULL DEFAULT 'staff',
        pin_hash      TEXT NOT NULL DEFAULT '',
        permissions   TEXT NOT NULL DEFAULT '',
        active        INTEGER NOT NULL DEFAULT 1,
        created_at    TEXT NOT NULL DEFAULT '',
        last_login    TEXT
    );
    """)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(audit_log)")}
    if "user_id" not in cols:
        conn.execute("ALTER TABLE audit_log ADD COLUMN user_id INTEGER")
    if "user_name" not in cols:
        conn.execute("ALTER TABLE audit_log ADD COLUMN user_name TEXT DEFAULT ''")

    # This read has to happen on every start, not only on the one where the
    # audit column was missing. Indented one level deeper it ran on a fresh
    # database and never again, so the second start -- and every start after
    # it -- raised NameError on jcols and killed the program before a window
    # could appear.
    jcols = {r[1] for r in conn.execute("PRAGMA table_info(jobs)")}
    if "created_by" not in jcols:
        conn.execute("ALTER TABLE jobs ADD COLUMN created_by TEXT DEFAULT ''")

    # No account is created here. A migration that seeds "admin" with a fixed
    # PIN gives every installation of this program the same working password,
    # holding every permission there is -- and it is invisible, so nobody
    # thinks to change it. The administrator is created on first run instead,
    # by the person who will use it, with a PIN only they have chosen.


def _m004(conn: sqlite3.Connection) -> None:
    """Specimen type, and tests that are issued as their own report.

    A pathology report has to say what was tested -- serum, plasma, whole blood,
    urine -- because the same analyte read from the wrong specimen means
    something different. It was missing entirely.
    """
    cols = {r[1] for r in conn.execute("PRAGMA table_info(tests)")}
    if "specimen" not in cols:
        conn.execute("ALTER TABLE tests ADD COLUMN specimen TEXT DEFAULT ''")
    if "separate_report" not in cols:
        conn.execute("ALTER TABLE tests ADD COLUMN separate_report INTEGER NOT NULL DEFAULT 0")
    if "interpretation" not in cols:
        conn.execute("ALTER TABLE tests ADD COLUMN interpretation TEXT DEFAULT ''")

    jcols = {r[1] for r in conn.execute("PRAGMA table_info(jobs)")}
    if "extra_pdfs" not in jcols:
        conn.execute("ALTER TABLE jobs ADD COLUMN extra_pdfs TEXT DEFAULT ''")


def _m005(conn: sqlite3.Connection) -> None:
    """The patient's initial, and who the referring doctor actually is.

    Names here are written FARAS .M. Kutty -- the initial is part of how a
    person is identified, and two patients sharing a first and family name are
    told apart by it. It was being typed into the middle of the name box, where
    nothing could search on it.

    Doctors gain a profession and a hospital, because "Dr. S. Mehta" on its own
    is not enough to ring the right person back about a critical result.
    """
    pcols = {r[1] for r in conn.execute("PRAGMA table_info(patients)")}
    if "initial" not in pcols:
        conn.execute("ALTER TABLE patients ADD COLUMN initial TEXT DEFAULT ''")

    rcols = {r[1] for r in conn.execute("PRAGMA table_info(referrers)")}
    if "profession" not in rcols:
        conn.execute("ALTER TABLE referrers ADD COLUMN profession TEXT DEFAULT ''")
    if "hospital" not in rcols:
        conn.execute("ALTER TABLE referrers ADD COLUMN hospital TEXT DEFAULT ''")


MIGRATIONS: List[Tuple[int, str, Callable[[sqlite3.Connection], None]]] = [
    (1, "initial schema", _m001),
    (2, "store age numerically on the job", _m002),
    (3, "staff accounts and audit attribution", _m003),
    (4, "specimen type and standalone detailed reports", _m004),
    (5, "patient initial, and the doctor's profession and hospital", _m005),
]

LATEST_VERSION = max(v for v, _n, _f in MIGRATIONS)


def current_version(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return 0
    return int(row[0]) if row else 0


def apply_migrations(conn: sqlite3.Connection) -> int:
    """Bring the database up to LATEST_VERSION. Returns the version applied."""
    version = current_version(conn)
    for number, _name, fn in MIGRATIONS:
        if number > version:
            fn(conn)
            conn.execute("DELETE FROM schema_version")
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (number,))
            conn.commit()
            version = number
    return version
