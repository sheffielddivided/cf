"""Pure transformations on the tidy observation table (pandas).

Observation columns (see docs/DESIGN.md, Datamodell):
country, period, freq, measure, side, value_raw, value, unit, source, series_key, obs_status
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .coverage import q_index, q_label
from .normalize import to_inflow_sign, to_usd_bn

OBS_COLUMNS = [
    "country", "period", "freq", "measure", "side", "value_raw", "value", "unit",
    "source", "series_key", "obs_status",
]
KEY = ["country", "measure", "side", "period"]
MAIN = "fa_ex_reserves"
COMPONENTS = ["fdi", "portfolio", "derivatives", "other_inv", "reserves"]


def frame(records: Iterable[dict]) -> pd.DataFrame:
    df = pd.DataFrame.from_records(list(records))
    if df.empty:
        return pd.DataFrame(columns=OBS_COLUMNS)
    df = df[OBS_COLUMNS].copy()
    df["value_raw"] = pd.to_numeric(df["value_raw"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return sort(df)


def sort(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(KEY, kind="stable").reset_index(drop=True)


def net(df: pd.DataFrame, measure: str) -> pd.DataFrame:
    """Wide table of one net measure in BPM6 raw USD: index period, columns country."""
    sub = df[(df.measure == measure) & (df.side == "net") & (df.freq == "Q")]
    return sub.pivot(index="period", columns="country", values="value_raw")


def derive_main(df: pd.DataFrame) -> pd.DataFrame:
    """Fill fa_ex_reserves where IMF lacks FABXRRI but has FAB and R_F (approved rule)."""
    have = df[(df.measure == MAIN) & (df.side == "net") & df.value_raw.notna()]
    have_keys = set(zip(have.country, have.period, strict=True))
    fab = df[(df.measure == "fa_total") & (df.side == "net") & df.value_raw.notna()]
    res = df[(df.measure == "reserves") & (df.side == "net") & df.value_raw.notna()]
    merged = fab.merge(res[["country", "period", "value_raw"]], on=["country", "period"],
                       suffixes=("", "_res"))
    rows = []
    for r in merged.itertuples(index=False):
        if (r.country, r.period) in have_keys:
            continue
        raw = r.value_raw - r.value_raw_res
        rows.append({
            "country": r.country, "period": r.period, "freq": r.freq, "measure": MAIN,
            "side": "net", "value_raw": raw,
            "value": to_inflow_sign(MAIN, "net", to_usd_bn(raw, 0)), "unit": "USD_bn",
            "source": "IMF_BOP", "series_key": f"{r.series_key} − R_F", "obs_status": "derived",
        })
    if not rows:
        return df
    # drop placeholder "missing" rows that the derived values replace
    drop = {(r["country"], r["period"]) for r in rows}
    is_missing_main = (df.measure == MAIN) & (df.side == "net") & df.value_raw.isna()
    keep = ~(is_missing_main & pd.Series(list(zip(df.country, df.period, strict=True)),
                                         index=df.index).isin(drop))
    return sort(pd.concat([df[keep], pd.DataFrame(rows)], ignore_index=True))


def quarter_range(first: str, last: str) -> list[str]:
    return [q_label(i) for i in range(q_index(first), q_index(last) + 1)]


def window(end: str, n: int = 4) -> list[str]:
    e = q_index(end)
    return [q_label(i) for i in range(e - n + 1, e + 1)]


def gdp_quarter(gdp: dict[tuple[str, int], float], country: str, period: str) -> float | None:
    """A quarter's share of annual GDP (USD bn): annual / 4."""
    year = int(period[:4])
    v = gdp.get((country, year))
    return None if v is None else v / 4


def window_sum(values: dict[str, float], periods: list[str]) -> float | None:
    """Sum over periods; None if any period is missing (never treat missing as 0)."""
    out = 0.0
    for p in periods:
        v = values.get(p)
        if v is None or pd.isna(v):
            return None
        out += v
    return out


def pct_of_gdp(
    values: dict[str, float], periods: list[str], gdp: dict[tuple[str, int], float], country: str
) -> float | None:
    flow = window_sum(values, periods)
    denom = window_sum({p: gdp_quarter(gdp, country, p) for p in periods}, periods)
    if flow is None or not denom:
        return None
    return flow / denom * 100


def latest_period(df: pd.DataFrame, country: str, measure: str = MAIN) -> str | None:
    sub = df[(df.country == country) & (df.measure == measure) & (df.side == "net")
             & df.value_raw.notna()]
    if sub.empty:
        return None
    return max(sub.period, key=q_index)


def reference_year(last_common_q: str) -> int:
    """Last complete year with data: the quarter's year if it is Q4, otherwise the year before."""
    year, q = int(last_common_q[:4]), int(last_common_q[-1])
    return year if q == 4 else year - 1
