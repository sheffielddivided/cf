"""IMF vs OECD cross-check (phase 2). Both report BPM6; differences usually mean one source
has not yet taken in a revision. Values are compared in USD bn, site sign (inflow positive)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .normalize import to_inflow_sign
from .sources.oecd import MEASURES

REL = 0.05
ABS_BN = 0.5


def compare(
    df: pd.DataFrame,
    oecd: dict[tuple[str, str, str], float],
    periods: list[str],
    countries: list[str],
) -> dict[str, Any]:
    imf = df[(df.side == "net") & df.measure.isin(list(MEASURES)) & df.period.isin(periods)
             & df.country.isin(countries) & df.value_raw.notna()]
    rows = []
    per_country: dict[str, dict[str, Any]] = {
        c: {"country": c, "compared": 0, "flagged": 0, "max_abs_diff": None, "missing_in_oecd": 0}
        for c in countries
    }
    for r in imf.itertuples(index=False):
        stats = per_country[r.country]
        o = oecd.get((r.country, r.measure, r.period))
        if o is None:
            stats["missing_in_oecd"] += 1
            continue
        a = to_inflow_sign(r.measure, "net", r.value_raw / 1e9)
        b = to_inflow_sign(r.measure, "net", o)
        diff = b - a
        flagged = abs(diff) > ABS_BN and abs(diff) > REL * max(abs(a), abs(b))
        stats["compared"] += 1
        stats["max_abs_diff"] = round(max(stats["max_abs_diff"] or 0.0, abs(diff)), 2)
        if flagged:
            stats["flagged"] += 1
            rows.append({"country": r.country, "measure": r.measure, "period": r.period,
                         "imf": round(a, 2), "oecd": round(b, 2), "diff": round(diff, 2)})
    rows.sort(key=lambda x: -abs(x["diff"]))
    return {
        "periods": periods,
        "threshold": {"rel": REL, "abs_bn": ABS_BN},
        "measures": list(MEASURES),
        "countries": [per_country[c] for c in countries],
        "flagged": rows,
    }
