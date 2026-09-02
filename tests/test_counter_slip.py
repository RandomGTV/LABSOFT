"""The 80mm counter slip: its figures, and what it does not say.

The slip this covers replaces one that read ``charged_paise`` and
``paid_paise`` off the bill row. The bills table has neither column, so both
reads fell through to their defaults and every slip printed "Amount Paid"
equal to the total and "Balance Due ₹0.00" whatever was actually owed. The
first test here is that failure, held shut.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture()
def lab(tmp_path, monkeypatch):
    monkeypatch.setenv("LABSOFT_HOME", str(tmp_path))
    from app.core import auth
    from app.db import connection, queries as q, seed

    auth.set_current(None)
    connection.close()
    connection.connect(do_backup=False)
    q.ensure_defaults()
    seed.seed_all()
    yield q
    auth.set_current(None)
    connection.close()


@pytest.fixture()
def billed_job(lab):
    """A job charged ₹230, discounted 10%, with ₹200 taken. ₹7 is owed."""
    from app import services

    pid = lab.save_patient({"name": "Faras M Kutty", "phone": "98470 22118",
                            "sex": "Male", "age_value": 41,
                            "age_unit": "years"})
    jid = lab.create_job(pid, [t["id"] for t in lab.list_tests()[:3]])
    lab.save_bill(jid, services.suggest_bill_items(jid), "percent", 10)
    lab.add_payment(jid, 20000, "cash")
    return lab, jid


# ===========================================================================
# The figures
# ===========================================================================

def test_the_slip_and_the_ledger_agree(billed_job):
    from app import services

    lab, jid = billed_job
    money = lab.job_money(jid)
    totals = services.build_bill_data(jid).totals()

    assert totals.gross_paise == money["gross_paise"]
    assert totals.discount_paise == money["discount_paise"]
    assert totals.net_paise == money["net_paise"]
    assert totals.paid_paise == money["paid_paise"]
    assert totals.balance_paise == money["balance_paise"]


def test_a_part_paid_bill_does_not_read_as_settled(billed_job):
    """The exact failure: paid defaulted to the total, balance to zero."""
    lab, jid = billed_job
    money = lab.job_money(jid)

    assert money["paid_paise"] == 20000
    assert money["net_paise"] == 20700
    assert money["balance_paise"] == 700
    assert money["paid_paise"] != money["net_paise"]


def test_job_money_matches_the_billing_ledger_row(billed_job):
    lab, jid = billed_job
    row = next(r for r in lab.ledger() if r["job_id"] == jid)
    money = lab.job_money(jid)
    for field in ("gross_paise", "discount_paise", "net_paise", "paid_paise",
                  "balance_paise"):
        assert money[field] == row[field], field


def test_an_unbilled_job_is_worth_nothing_rather_than_erroring(lab):
    pid = lab.save_patient({"name": "Nobody", "phone": "98470 00000"})
    jid = lab.create_job(pid, [t["id"] for t in lab.list_tests()[:1]])
    money = lab.job_money(jid)
    assert money["billed"] is False
    assert money["net_paise"] == 0 and money["paid_paise"] == 0


# ===========================================================================
# What is printed on it
# ===========================================================================

def test_the_slip_renders_at_80mm(billed_job):
    from app import services
    from app.output import receipt

    _lab, jid = billed_job
    image = receipt.render_slip(services.build_bill_data(jid), 420)
    assert image.width() == 420
    assert image.height() > 200          # it drew something, not a blank strip


def test_the_slip_claims_no_tax(billed_job):
    """This laboratory issues no tax invoice, so the slip does not say it does.

    Checked by painting the slip through a recording painter and reading back
    every string it drew, which is the only way to know what is on the paper.
    """
    from PyQt6.QtGui import QImage, QPainter
    from app import services
    from app.output import receipt

    _lab, jid = billed_job
    drawn = []

    class Spy(QPainter):
        def drawText(self, *args):       # noqa: N802 - Qt naming
            for a in args:
                if isinstance(a, str):
                    drawn.append(a)
            return super().drawText(*args)

    image = QImage(420, 1400, QImage.Format.Format_RGB32)
    image.fill(0xFFFFFFFF)
    p = Spy(image)
    try:
        receipt.paint_slip(p, services.build_bill_data(jid), 420 / receipt.SLIP_W)
    finally:
        p.end()

    printed = " ".join(drawn).lower()
    assert printed, "the slip drew no text at all"
    for word in ("tax", "gst", "invoice"):
        assert word not in printed, f"the slip still says {word!r}: {printed[:300]}"
    assert "cash receipt" in printed
