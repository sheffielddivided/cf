"""Normalisation rules shared by the whole pipeline.

The single most important rule lives here: the site shows *net inflow* as positive,
which is the opposite of the BPM6 sign convention for the financial account.
Nothing else in the code base may flip signs.
"""

from __future__ import annotations

# Measures that are financial-account balances in BPM6 terms (net acquisition of
# assets minus net incurrence of liabilities). Their sign is flipped for display.
FINANCIAL_ACCOUNT_MEASURES: frozenset[str] = frozenset(
    {
        "fa_total",
        "fa_ex_reserves",
        "fdi",
        "portfolio",
        "portfolio_equity",
        "portfolio_debt",
        "other_inv",
        "derivatives",
        "reserves",
    }
)

SIDES: frozenset[str] = frozenset({"net", "assets", "liabilities"})


def to_inflow_sign(measure: str, side: str, value_raw: float | None) -> float | None:
    """Convert a source value (BPM6 sign) to the site's convention.

    * Financial-account **net** balances: BPM6 positive = net lending abroad (outflow),
      so the site value is ``-value_raw`` (positive = net inflow).
    * ``assets`` side (residents' net acquisition of foreign assets) is an outflow of
      capital, so it is shown as negative: ``-value_raw``.
    * ``liabilities`` side (non-residents' net investment in the economy) is an inflow,
      so it keeps its sign: ``value_raw``.
    * Everything else (current account, GDP, errors and omissions) is returned unchanged.

    Missing values stay missing (``None``); they are never turned into 0.
    """
    if side not in SIDES:
        raise ValueError(f"unknown side: {side!r}")
    if value_raw is None:
        return None
    if measure not in FINANCIAL_ACCOUNT_MEASURES:
        return value_raw
    if side == "liabilities":
        return value_raw
    return -value_raw


def to_usd_bn(value: float | None, unit_mult: int | None, *, currency: str = "USD") -> float | None:
    """Scale a USD value expressed as ``value * 10**unit_mult`` to billions of USD."""
    if value is None:
        return None
    if currency != "USD":
        raise ValueError(f"expected USD, got {currency!r}")
    mult = 0 if unit_mult is None else unit_mult
    return value * 10 ** (mult - 9)
