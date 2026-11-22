"""Phase 3: episodes of unusual gross capital flows, after Forbes & Warnock (2012).

For gross inflows (non-residents' net investment, liabilities side) and gross outflows
(residents' net investment abroad, assets side), each = direct + portfolio + other investment:

  C_t   = sum of the last four quarters
  ΔC_t  = C_t − C_{t−4}                       (year-on-year change)
  μ, σ  = rolling mean and standard deviation of ΔC over the last 20 quarters (5 years)

An episode starts when ΔC moves more than 1σ from μ, ends when it comes back within 1σ, must
reach 2σ at least once, and must last at least two quarters. Upward episodes in inflows are
"inflow surges", downward ones "inflow stops"; for outflows "outflow surges" and "outflow
retrenchments". The site describes episodes; it does not interpret them.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .coverage import q_index
from .model import quarter_range

COMPONENTS = ("fdi", "portfolio", "other_inv")
WINDOW = 20
MIN_LEN = 2
SHOW = 40  # quarters returned for charts

TYPES = {
    ("inflows", 1): "inflow_surge",
    ("inflows", -1): "inflow_stop",
    ("outflows", 1): "outflow_surge",
    ("outflows", -1): "outflow_retrenchment",
}


def gross(df: pd.DataFrame, country: str, side: str) -> pd.Series:
    """Gross flow (USD bn, BPM6 raw sign: positive = acquisition/incurrence) by quarter;
    only quarters where all three components are present."""
    sub = df[
        (df.country == country)
        & (df.side == side)
        & df.measure.isin(COMPONENTS)
        & df.value_raw.notna()
        & (df.freq == "Q")
    ]
    if sub.empty:
        return pd.Series(dtype=float)
    wide = sub.pivot(index="period", columns="measure", values="value_raw") / 1e9
    wide = wide.dropna(subset=[c for c in COMPONENTS if c in wide.columns])
    if not all(c in wide.columns for c in COMPONENTS):
        return pd.Series(dtype=float)
    s = wide[list(COMPONENTS)].sum(axis=1)
    if s.empty:
        return s
    full = quarter_range(min(s.index, key=q_index), max(s.index, key=q_index))
    return s.reindex(full)  # gaps stay NaN, never zero


def find_episodes(z: pd.Series, kind: str) -> list[dict[str, Any]]:
    out = []
    for sign in (1, -1):
        run: list[tuple[str, float]] = []
        for period, value in list(z.items()) + [("", float("nan"))]:
            inside = pd.notna(value) and sign * value > 1
            if inside:
                run.append((period, float(value)))
                continue
            if len(run) >= MIN_LEN and max(sign * v for _, v in run) > 2:
                peak = max(run, key=lambda pv: sign * pv[1])
                out.append(
                    {
                        "type": TYPES[(kind, sign)],
                        "start": run[0][0],
                        "end": run[-1][0],
                        "peak": peak[0],
                        "peak_z": round(peak[1], 2),
                    }
                )
            run = []
    return sorted(out, key=lambda e: q_index(e["start"]))


def analyse(series: pd.Series, kind: str, last_common: str) -> dict[str, Any]:
    c = series.rolling(4).sum()
    dc = c - c.shift(4)
    mu = dc.rolling(WINDOW, min_periods=WINDOW).mean()
    sd = dc.rolling(WINDOW, min_periods=WINDOW).std()
    z = (dc - mu) / sd
    eps = find_episodes(z, kind)
    shown = [p for p in dc.index if q_index(p) <= q_index(last_common)][-SHOW:]
    r = lambda v: None if pd.isna(v) else round(float(v), 2)  # noqa: E731
    return {
        "periods": shown,
        "dC": [r(dc[p]) for p in shown],
        "mu": [r(mu[p]) for p in shown],
        "sd": [r(sd[p]) for p in shown],
        "episodes": eps,
    }


def compute(df: pd.DataFrame, countries: list[str], last_common: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "method": {
            "window_quarters": WINDOW,
            "threshold_sd": 2,
            "bounds_sd": 1,
            "min_quarters": MIN_LEN,
            "components": list(COMPONENTS),
        },
        "countries": {},
        "active": [],
    }
    for c in countries:
        entry = {}
        for kind, side in (("inflows", "liabilities"), ("outflows", "assets")):
            s = gross(df, c, side)
            # Same cut-off as the ranking: nothing after the last common quarter.
            s = s[[q_index(p) <= q_index(last_common) for p in s.index]]
            if s.dropna().size < WINDOW + 8:
                continue
            entry[kind] = analyse(s, kind, last_common)
            lc = q_index(last_common)
            for e in entry[kind]["episodes"]:
                if q_index(e["start"]) <= lc <= q_index(e["end"]):
                    result["active"].append({"country": c, **e})
        if entry:
            result["countries"][c] = entry
    return result
