"""The layer between the screens and everything else.

Screens call these functions; they never compute a result or assemble a report
themselves. Keeping the sequence here means the same steps run whether a report
is produced from the job screen, a reprint, or a revision.
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import config
from .core import billing, formula, numbering, ranges as rng, turnaround
from .db import queries as q
from .output import receipt as rcpt, report as rpt


# ===========================================================================
# Result calculation
# ===========================================================================

def _numeric(text) -> Optional[float]:
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    if s[0] in "<>=":
        s = s[1:].strip()
    try:
        return float(s)
    except ValueError:
        return None


def recalculate(job_id: int, typed: Optional[Dict[int, str]] = None) -> Dict[int, dict]:
    """Recompute every result on a job and save it.

    typed -- {job_test_id: raw text} for values the operator has just entered
             but not yet saved. Anything absent falls back to what is stored.

    Returns {job_test_id: {value, display, range_text, flag, error}}.
    """
    job = q.get_job(job_id)
    if not job:
        return {}

    tests = q.job_tests(job_id)
    stored = q.results_for_job(job_id)
    typed = typed or {}

    # Age and sex are taken from the job's snapshot, not the patient record.
    # A patient who was 10 days old at the test is not a newborn two years
    # later, and reprinting must not quietly move the Normal Value column.
    sex = job.get("sex_at_test") or job.get("patient_sex") or ""
    age_value = job.get("age_value_at_test")
    age_unit = job.get("age_unit_at_test") or "years"
    if age_value is None:
        age_value = job.get("age_value")
        age_unit = job.get("age_unit") or "years"
    age_years = rng.age_in_years(age_value, age_unit)

    # Raw text for every test on the job.
    raw: Dict[int, str] = {}
    for t in tests:
        jt = t["job_test_id"]
        if jt in typed:
            raw[jt] = "" if typed[jt] is None else str(typed[jt])
        else:
            raw[jt] = (stored.get(jt) or {}).get("raw_value") or ""

    by_code_value: Dict[str, Optional[float]] = {}
    formulas: Dict[str, str] = {}
    code_of: Dict[int, str] = {}

    for t in tests:
        code = (t["code"] or "").upper()
        code_of[t["job_test_id"]] = code
        f = (t["formula"] or "").strip()
        if f:
            formulas[code] = f
        else:
            by_code_value[code] = _numeric(raw[t["job_test_id"]])

    derived = formula.resolve_job(formulas, by_code_value) if formulas else {}

    out: Dict[int, dict] = {}
    for t in tests:
        jt = t["job_test_id"]
        code = code_of[jt]
        is_derived = code in formulas
        decimals = int(t["decimals"] or 0)
        unit = t["unit"] or ""
        rtype = (t["result_type"] or "numeric").strip().lower()
        error = None

        if is_derived:
            dr = derived.get(code)
            value = dr.value if dr else None
            error = dr.error if dr else None
            display = f"{rng.format_value(value, decimals)}{unit}" if value is not None else ""
            raw_text = display
        elif rtype in ("text", "option"):
            raw_text = raw[jt].strip()
            value = None
            display = raw_text
        else:
            raw_text = raw[jt].strip()
            value = _numeric(raw_text)
            if raw_text and value is None:
                # Something like "haemolysed" typed into a numeric box: keep it
                # verbatim rather than discarding what the operator wrote.
                display = raw_text
            elif value is not None:
                prefix = raw_text[0] if raw_text[:1] in "<>" else ""
                display = f"{prefix}{rng.format_value(value, decimals)}{unit}"
            else:
                display = ""

        ranges = q.range_objects(t["id"])
        chosen = rng.select_range(ranges, sex, age_years)
        range_text = chosen.printed_text(unit) if chosen else ""

        compare = value if value is not None else (display or None)
        flag = rng.flag_for(compare, ranges, sex, age_years) if display else ""

        q.save_result(jt, raw_text, value, display, range_text, flag)
        out[jt] = {"value": value, "display": display, "range_text": range_text,
                   "flag": flag, "error": error, "derived": is_derived}

    _refresh_status(job_id)
    return out


def _refresh_status(job_id: int) -> None:
    """Move a job between draft / in progress / ready. Never demotes a sent one."""
    job = q.get_job(job_id)
    if not job or job["status"] == turnaround.STATUS_SENT:
        return
    complete, _missing = q.job_is_complete(job_id)
    results = q.results_for_job(job_id)
    any_entered = any((r.get("display_value") or "").strip() for r in results.values())

    if complete:
        status = turnaround.STATUS_READY
    elif any_entered:
        status = turnaround.STATUS_IN_PROGRESS
    else:
        status = turnaround.STATUS_DRAFT
    if status != job["status"]:
        q.update_job(job_id, status=status)


# ===========================================================================
# Report assembly
# ===========================================================================

def build_report_data(job_id: int) -> rpt.ReportData:
    job = q.get_job(job_id)
    if not job:
        raise ValueError("That job no longer exists.")

    settings = q.all_settings()
    tests = q.job_tests(job_id)
    results = q.results_for_job(job_id)

    show_specimen = (settings.get("print_specimen", "1") or "0").strip() not in (
        "", "0", "no", "false")

    printed = []
    for t in tests:
        if t.get("not_done"):
            continue
        r = results.get(t["job_test_id"]) or {}
        display = (r.get("display_value") or "").strip()
        if display:
            printed.append((t, r, display))

    # One specimen line under the heading when the whole group shares a
    # specimen; otherwise a line under each result. A single "Serum" over a
    # group that also contains a whole-blood HbA1c would be plainly wrong, and
    # a specimen printed wrongly is worse than one not printed at all.
    group_specimens: Dict[str, set] = {}
    for t, _r, _d in printed:
        group = (t["group_name"] or "").strip()
        group_specimens.setdefault(group, set()).add((t.get("specimen") or "").strip())

    rows: List[rpt.ReportRow] = []
    last_group = None
    for t, r, display in printed:
        group = (t["group_name"] or "").strip()
        kinds = {s for s in group_specimens.get(group, set()) if s}
        uniform = len(kinds) == 1 and len(group_specimens.get(group, set())) == 1

        if group and group != last_group:
            rows.append(rpt.ReportRow(
                description=group, is_group=True,
                specimen=(next(iter(kinds)) if show_specimen and uniform else "")))
            last_group = group
        rows.append(rpt.ReportRow(
            description=t["name"],
            observed=display,
            normal=(r.get("range_text") or "").strip(),
            flag=(r.get("flag") or ""),
            specimen=((t.get("specimen") or "").strip()
                      if show_specimen and not uniform else ""),
        ))

    received = q.to_dt(job["received_at"])
    reported = q.to_dt(job["reported_at"]) or received or datetime.now()

    collected_fmt = received.strftime("%d-%m-%Y %I:%M %p") if received else ""
    reported_fmt = reported.strftime("%d-%m-%Y %I:%M %p") if reported else ""

    inst = (settings.get("lab_institution") or (
        (settings.get("lab_name_prefix") or "").strip() + " " +
        (settings.get("lab_name") or "").strip() + " " +
        (settings.get("lab_address_1") or "").strip()
    )).strip()
    if not inst:
        inst = "MITHRA MEDICAL LABORATORY KUTTIPPALA"

    # Check if the report is exclusively for HbA1c
    is_only_hba1c = (len(rows) > 0 and all(
        ("HBA1C" in r.description.upper() or "GLYCATED" in r.description.upper()
         or "MEAN BLOOD GLUCOSE" in r.description.upper() or "MBG" in r.description.upper()
         or r.is_group) for r in rows
    ))
    fmt_type = "hba1c" if is_only_hba1c else "standard"

    interp = ""
    if is_only_hba1c:
        from .db import seed
        interp = seed.DETAILED.get("HBA1C", "")

    return rpt.ReportData(
        report_no=numbering.with_revision(job["report_no"], job["revision_no"]),
        date_text=turnaround.format_date(reported),
        collected_at_text=collected_fmt,
        reported_at_text=reported_fmt,
        name=job["name_at_test"] or job["patient_name"] or "",
        sex=job["sex_at_test"] or "",
        age=job["age_at_test"] or "",
        referred_by=job["referrer_name"] or "",
        institution=inst,
        phone=job.get("patient_phone") or "",
        rows=rows,
        remarks=job["remarks"] or "",
        revision_no=int(job["revision_no"] or 1),
        settings=settings,
        format_type=fmt_type,
        interpretation=interp,
    )


_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def pdf_filename(job: dict) -> str:
    name = _SAFE.sub("_", (job.get("name_at_test") or job.get("patient_name") or "report")).strip("_")
    when = q.to_dt(job.get("reported_at")) or q.to_dt(job.get("received_at")) or datetime.now()
    rev = int(job.get("revision_no") or 1)
    suffix = "" if rev <= 1 else f"_R{rev}"
    return f"{name}_{job.get('report_no')}{suffix}_{when.strftime('%d%b%y')}.pdf"


def patient_folder(patient_id: int) -> Path:
    p = q.get_patient(patient_id) or {}
    return config.patient_dir(patient_id, p.get("name", ""), p.get("phone", ""))


def write_patient_summary(patient_id: int) -> Path:
    """A plain-text card in the patient's named folder."""
    patient = q.get_patient(patient_id) or {}
    folder = patient_folder(patient_id)
    path = folder / "_patient details.txt"

    lines = [
        (q.get_setting("lab_name_prefix") + " " + q.get_setting("lab_name")).strip(),
        "",
        f"Name        : {patient.get('name', '')}",
        f"Mobile      : {patient.get('phone', '') or '-'}",
        f"Sex         : {patient.get('sex', '') or '-'}",
    ]
    age = q._age_text(patient)
    lines.append(f"Age         : {age or '-'}")
    if patient.get("address"):
        lines.append(f"Address     : {patient['address']}")
    if patient.get("notes"):
        lines.append(f"Notes       : {patient['notes']}")

    jobs = q.patient_jobs(patient_id)
    lines += ["", f"Visits: {len(jobs)}", "-" * 66,
              f"{'Report No':<12}{'Date':<14}{'Tests':<8}Status", "-" * 66]
    for j in jobs:
        when = turnaround.format_date(q.to_dt(j["received_at"]))
        lines.append(f"{j['report_no']:<12}{when:<14}{j['n_tests']:<8}"
                     f"{turnaround.status_label(j['status'])}")

    lines += ["", "Every report for this patient is a PDF in this folder.",
              f"Updated {turnaround.format_dt(datetime.now())}"]

    try:
        path.write_text("\n".join(lines), encoding="utf-8")
    except OSError:
        pass          # a summary that cannot be written must not stop a report
    return path


def report_path_for(job: dict) -> Path:
    """Where a job's PDF belongs: in its patient's named folder."""
    folder = config.patient_dir(job["patient_id"],
                                job.get("name_at_test") or job.get("patient_name", ""),
                                job.get("patient_phone", ""))
    when = q.to_dt(job.get("reported_at")) or q.to_dt(job.get("received_at")) \
        or datetime.now()
    rev = int(job.get("revision_no") or 1)
    suffix = "" if rev <= 1 else f" R{rev}"
    return folder / f"Report_{job['report_no']}{suffix}.pdf"


def detailed_tests(job_id: int) -> List[dict]:
    """Tests on this job that are issued on their own sheet."""
    results = q.results_for_job(job_id)
    out = []
    for t in q.job_tests(job_id):
        if t.get("not_done") or not t.get("separate_report"):
            continue
        r = results.get(t["job_test_id"]) or {}
        if (r.get("display_value") or "").strip():
            out.append(t)
    return out


def build_detail_data(job_id: int, test: dict) -> rpt.ReportData:
    """A single-test sheet, with its interpretation printed underneath."""
    data = build_report_data(job_id)
    results = q.results_for_job(job_id)
    r = results.get(test["job_test_id"]) or {}

    rows = [rpt.ReportRow(description=(test["group_name"] or "").strip(),
                          is_group=True,
                          specimen=(test.get("specimen") or "").strip()),
            rpt.ReportRow(description=test["name"],
                          observed=(r.get("display_value") or "").strip(),
                          normal=(r.get("range_text") or "").strip(),
                          flag=(r.get("flag") or ""))]

    # Anything calculated from this test belongs on the same sheet -- an HbA1c
    # report without the estimated average glucose beside it is half a report.
    for other in q.job_tests(job_id):
        if other["id"] == test["id"] or other.get("not_done"):
            continue
        formula_text = (other.get("formula") or "").strip()
        if not formula_text:
            continue
        if test["code"].upper() not in formula.codes_used_safe(formula_text):
            continue
        other_r = results.get(other["job_test_id"]) or {}
        if (other_r.get("display_value") or "").strip():
            rows.append(rpt.ReportRow(
                description=other["name"],
                observed=other_r["display_value"].strip(),
                normal=(other_r.get("range_text") or "").strip(),
                flag=(other_r.get("flag") or "")))

    data.rows = rows
    data.title = f"{test['name']} — Detailed Report"
    data.interpretation = (test.get("interpretation") or "").strip()

    if test["code"].upper() == "HBA1C":
        data.format_type = "hba1c"
        data.title = ""
        if not data.interpretation:
            from .db import seed
            data.interpretation = seed.DETAILED.get("HBA1C", "")

    return data


def generate_pdf(job_id: int, mark_reported: bool = True) -> Path:
    """Produce the PDF. Always includes the letterhead.

    The print-header setting controls paper only: a PDF sent on WhatsApp with a
    blank top, waiting for preprinted stationery that will never be under it,
    is not a usable document.
    """
    job = q.get_job(job_id)
    if not job:
        raise ValueError("That job no longer exists.")

    if mark_reported and not job.get("reported_at"):
        q.update_job(job_id, reported_at=q.now_str())
        job = q.get_job(job_id)

    data = build_report_data(job_id)
    path = report_path_for(job)
    rpt.write_pdf(data, path)

    # Keep the by-month copy as well: it is how the lab finds "everything from
    # last March" without opening thirty patient folders.
    try:
        month = config.report_month_dir(q.to_dt(job["received_at"]) or datetime.now())
        shutil.copy2(path, month / pdf_filename(job))
    except OSError:
        pass

    # Detailed tests get their own sheet as well as their line on the main
    # report, because that is how the lab hands them over.
    extras: List[str] = []
    for test in (detailed_tests(job_id)
                 if q.setting_bool("separate_detail_reports") else []):
        try:
            detail_path = path.with_name(
                f"{path.stem} — {_SAFE.sub(' ', test['name']).strip()}.pdf")
            rpt.write_pdf(build_detail_data(job_id, test), detail_path)
            extras.append(str(detail_path))
        except Exception:
            # A failed extra sheet must never cost the lab the main report.
            q.log_action("detail_report_failed", "job", job_id, test["code"])

    write_patient_summary(job["patient_id"])

    q.update_job(job_id, pdf_path=str(path), extra_pdfs="\n".join(extras))
    q.log_action("report_generated", "job", job_id,
                 path.name + (f" (+{len(extras)} detailed)" if extras else ""))
    return path


def report_files(job_id: int) -> List[Path]:
    """Everything produced for a job: the main report plus any detail sheets."""
    job = q.get_job(job_id) or {}
    paths = []
    if job.get("pdf_path"):
        paths.append(Path(job["pdf_path"]))
    for line in (job.get("extra_pdfs") or "").split("\n"):
        if line.strip():
            paths.append(Path(line.strip()))
    return [p for p in paths if p.exists()]


def verify_job(job_id: int) -> Tuple[bool, List[str], Optional[Path]]:
    """The gate before a report can leave the lab.

    Returns (ok, missing_test_names, pdf_path). Nothing is generated while any
    test is neither filled in nor marked not done.
    """
    recalculate(job_id)
    complete, missing = q.job_is_complete(job_id)
    if not complete:
        return False, missing, None
    path = generate_pdf(job_id)
    q.update_job(job_id, status=turnaround.STATUS_READY)
    return True, [], path


def create_revision(job_id: int, reason: str = "") -> int:
    """Amend a report that has already gone out.

    The original row, its results and its PDF are all left untouched; a new job
    carries the same report number with a higher revision. A lab that silently
    rewrites an issued result has nothing to show when one is questioned.
    """
    job = q.get_job(job_id)
    if not job:
        raise ValueError("That job no longer exists.")

    tests = q.job_tests(job_id)
    results = q.results_for_job(job_id)

    # Count from the highest revision of this report number, not from the job
    # being amended. Amending the original twice otherwise tries to create
    # revision 2 a second time and hits the unique index.
    highest = q._row(
        "SELECT MAX(revision_no) AS m FROM jobs WHERE report_no = ?",
        (job["report_no"],)) or {}
    next_rev = int(highest.get("m") or job["revision_no"] or 1) + 1

    with q.transaction() as c:
        cur = c.execute(
            "INSERT INTO jobs (report_no, patient_id, referrer_id, received_at, "
            "due_at, reported_at, status, name_at_test, age_at_test, sex_at_test, "
            "referrer_name, remarks, revision_no) "
            "VALUES (?,?,?,?,?,NULL,?,?,?,?,?,?,?)",
            (job["report_no"], job["patient_id"], job["referrer_id"],
             job["received_at"], job["due_at"], turnaround.STATUS_IN_PROGRESS,
             job["name_at_test"], job["age_at_test"], job["sex_at_test"],
             job["referrer_name"], job["remarks"], next_rev))
        new_id = int(cur.lastrowid)
        for t in tests:
            c.execute("INSERT INTO job_tests (job_id, test_id, sort_order, not_done) "
                      "VALUES (?,?,?,?)",
                      (new_id, t["id"], t["sort_order"], t.get("not_done", 0)))

    new_tests = {t["id"]: t["job_test_id"] for t in q.job_tests(new_id)}
    for t in tests:
        old = results.get(t["job_test_id"])
        if old and new_tests.get(t["id"]):
            q.save_result(new_tests[t["id"]], old["raw_value"], old["computed_value"],
                          old["display_value"], old["range_text"], old["flag"])

    q.log_action("revision_created", "job", new_id,
                 f"report {job['report_no']} revision {next_rev}: {reason}".strip())
    return new_id


# ===========================================================================
# Billing helpers
# ===========================================================================

def suggest_bill_items(job_id: int) -> List[dict]:
    """Line items from the job's tests, collapsing whole panels to panel price."""
    tests = q.job_tests(job_id)
    remaining = {t["id"]: t for t in tests}
    items: List[dict] = []

    for panel in q.list_panels():
        member_ids = set(q.panel_test_ids(panel["id"]))
        if not member_ids or not member_ids.issubset(set(remaining)):
            continue
        price = panel["price_paise"]
        if price is None:
            price = sum(int(remaining[i]["rate_paise"]) for i in member_ids)
        items.append({"label": panel["name"], "panel_id": panel["id"],
                      "rate_paise": int(price), "qty": 1})
        for i in member_ids:
            remaining.pop(i, None)

    for t in remaining.values():
        items.append({"label": t["name"], "test_id": t["id"],
                      "rate_paise": int(t["rate_paise"] or 0), "qty": 1})
    return items


def build_bill_data(job_id: int) -> rcpt.BillData:
    """Everything the printed receipt needs, in one object.

    Falls back to the suggested charges when no bill has been saved yet, so a
    counter can print a proforma for a patient asking "how much will it be?"
    without committing anything.
    """
    job = q.get_job(job_id)
    if not job:
        raise ValueError("That job no longer exists.")

    bill = q.get_bill(job_id)
    if bill:
        lines = [rcpt.BillLine(i["label"], int(i["rate_paise"]), int(i["qty"] or 1))
                 for i in q.bill_items(bill["id"])]
        payments = [rcpt.BillPaymentLine(int(p["amount_paise"]), p["mode"] or "cash",
                                         p["paid_at"] or "")
                    for p in q.bill_payments(bill["id"])]
        discount_type = bill["discount_type"] or billing.DISCOUNT_PERCENT
        discount_value = float(bill["discount_value"] or 0)
        when = q.to_dt(bill["created_at"]) or datetime.now()
    else:
        lines = [rcpt.BillLine(i["label"], int(i["rate_paise"]), int(i.get("qty", 1)))
                 for i in suggest_bill_items(job_id)]
        payments = []
        discount_type, discount_value = billing.DISCOUNT_PERCENT, 0.0
        when = q.to_dt(job["received_at"]) or datetime.now()

    from .core import auth

    me = auth.current()
    return rcpt.BillData(
        bill_no=str(job["report_no"]),
        date_text=turnaround.format_date(when),
        name=job["name_at_test"] or job["patient_name"] or "",
        sex=job["sex_at_test"] or "",
        age=job["age_at_test"] or "",
        phone=job.get("patient_phone") or "",
        referred_by=job["referrer_name"] or "",
        lines=lines,
        payments=payments,
        discount_type=discount_type,
        discount_value=discount_value,
        settings=q.all_settings(),
        made_by=(me.display_name or me.username) if me else "",
    )


def bill_path_for(job: dict) -> Path:
    """Where a job's receipt belongs: beside its report, in the patient folder."""
    folder = config.patient_dir(job["patient_id"],
                                job.get("name_at_test") or job.get("patient_name", ""),
                                job.get("patient_phone", ""))
    when = q.to_dt(job.get("received_at")) or datetime.now()
    return folder / f"{when:%Y-%m-%d}  Bill {job['report_no']}.pdf"


def generate_bill_pdf(job_id: int) -> Path:
    """Write the receipt as a PDF and remember that it was made."""
    job = q.get_job(job_id)
    if not job:
        raise ValueError("That job no longer exists.")
    path = bill_path_for(job)
    rcpt.write_pdf(build_bill_data(job_id), path, with_header=True)
    q.log_action("bill_printed", "job", job_id, path.name)
    return path


# ===========================================================================
# Patients
# ===========================================================================

def upsert_patient(name: str, phone: str, sex: str, age_value, age_unit: str,
                   patient_id: Optional[int] = None,
                   address: Optional[str] = None,
                   initial: Optional[str] = None) -> int:
    """Reuse an existing patient with the same name and phone rather than
    creating a duplicate every visit, which is what makes history work.

    Only the fields the job screen actually collects are sent. Passing
    address="" here wiped the address on every visit, because an empty string
    is a value while an absent key is left alone.
    """
    data = {"name": (name or "").strip(), "phone": (phone or "").strip(),
            "sex": sex or "", "age_value": age_value,
            "age_unit": age_unit or "years"}
    if address is not None:
        data["address"] = address
    if initial is not None:
        data["initial"] = (initial or "").strip().strip(".").upper()
    if patient_id:
        data["id"] = patient_id
        return q.save_patient(data)
    if data["name"] and data["phone"]:
        found = q.find_patient(data["name"], data["phone"])
        if found:
            data["id"] = found["id"]
            return q.save_patient(data)
    return q.save_patient(data)
