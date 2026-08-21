import pytest

from app.core.billing import (
    DISCOUNT_FLAT, DISCOUNT_PERCENT, LineItem, Payment,
    commission_for, compute_totals, format_rupees, to_paise, to_rupees,
)


# ----------------------------------------------------------------- conversion

@pytest.mark.parametrize("value,expected", [
    (100, 10000), (0, 0), (0.5, 50), (1.005, 101), (99.99, 9999),
    ("250", 25000), ("250.50", 25050), ("₹1,450", 145000),
    ("", 0), (None, 0), ("abc", 0),
])
def test_to_paise(value, expected):
    assert to_paise(value) == expected


def test_float_drift_is_avoided():
    """The reason money is stored in paise: 0.1+0.2 != 0.3 in float."""
    total = sum(to_paise(0.1) for _ in range(10))
    assert total == 100
    assert to_rupees(total) == 1.00


@pytest.mark.parametrize("paise,expected", [
    (0, "₹0.00"),
    (5000, "₹50.00"),
    (145000, "₹1,450.00"),
    (18430000, "₹1,84,300.00"),          # Indian grouping
    (100000000, "₹10,00,000.00"),
    (-30000, "-₹300.00"),
])
def test_format_rupees(paise, expected):
    assert format_rupees(paise) == expected


# --------------------------------------------------------------------- totals

def items():
    return [
        LineItem("CBC", to_paise(300)),
        LineItem("LFT", to_paise(650)),
        LineItem("Lipid Profile", to_paise(500)),
    ]


def test_gross_is_sum_of_items():
    t = compute_totals(items())
    assert t.gross_paise == to_paise(1450)
    assert t.net_paise == to_paise(1450)
    assert t.balance_paise == to_paise(1450)


def test_percent_discount():
    t = compute_totals(items(), DISCOUNT_PERCENT, 10)
    assert t.discount_paise == to_paise(145)
    assert t.net_paise == to_paise(1305)


def test_flat_discount():
    t = compute_totals(items(), DISCOUNT_FLAT, 200)
    assert t.discount_paise == to_paise(200)
    assert t.net_paise == to_paise(1250)


def test_quantity_multiplies():
    t = compute_totals([LineItem("X-ray", to_paise(150), qty=3)])
    assert t.gross_paise == to_paise(450)


def test_discount_cannot_exceed_gross():
    """A mistyped discount must not create money owed to the patient."""
    assert compute_totals(items(), DISCOUNT_FLAT, 99999).net_paise == 0
    assert compute_totals(items(), DISCOUNT_PERCENT, 1000).net_paise == 0


def test_negative_discount_ignored():
    t = compute_totals(items(), DISCOUNT_PERCENT, -20)
    assert t.discount_paise == 0
    assert t.net_paise == to_paise(1450)


def test_percent_discount_rounds_to_whole_paise():
    t = compute_totals([LineItem("T", to_paise(333))], DISCOUNT_PERCENT, 33.3)
    assert isinstance(t.discount_paise, int)
    assert t.discount_paise == 11089   # 33300 * 0.333 = 11088.9 -> 11089


# ------------------------------------------------------------------- payments

def test_partial_payment_leaves_balance():
    t = compute_totals([LineItem("Thyroid", to_paise(600))],
                       payments=[Payment(to_paise(300), "cash")])
    assert t.paid_paise == to_paise(300)
    assert t.balance_paise == to_paise(300)
    assert not t.is_paid


def test_full_payment_clears_balance():
    t = compute_totals([LineItem("Thyroid", to_paise(600))],
                       payments=[Payment(to_paise(400)), Payment(to_paise(200), "upi")])
    assert t.balance_paise == 0
    assert t.is_paid


def test_overpayment_is_visible_not_hidden():
    t = compute_totals([LineItem("Thyroid", to_paise(600))],
                       payments=[Payment(to_paise(700))])
    assert t.balance_paise == to_paise(-100)
    assert t.is_overpaid


def test_no_items_no_payments():
    t = compute_totals([])
    assert (t.gross_paise, t.net_paise, t.balance_paise) == (0, 0, 0)
    assert t.is_paid


def test_discount_then_payment_order():
    t = compute_totals(items(), DISCOUNT_PERCENT, 10,
                       payments=[Payment(to_paise(1305))])
    assert t.balance_paise == 0


# ----------------------------------------------------------------- commission

@pytest.mark.parametrize("net,pct,expected", [
    (to_paise(1305), 10, to_paise(130.5)),
    (to_paise(1000), 0,  0),
    (to_paise(1000), 100, to_paise(1000)),
    (to_paise(1000), 150, to_paise(1000)),   # clamped
    (to_paise(1000), -5, 0),                 # clamped
    (0, 10, 0),
    (to_paise(333), 7.5, 2498),              # 33300 * .075 = 2497.5 -> 2498
])
def test_commission(net, pct, expected):
    assert commission_for(net, pct) == expected


def test_commission_is_always_an_integer():
    assert isinstance(commission_for(to_paise(1305), 10), int)
