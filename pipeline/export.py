"""Export small JSON/CSV files for the static site (site/public/data/)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .coverage import q_index
from .model import MAIN, pct_of_gdp, quarter_range, window

# Measures offered in the site's "kapitaltype" control, plus the reserve toggle's partner.
RANKING_MEASURES = ["fa_ex_reserves", "fa_total", "fdi", "portfolio", "other_inv"]
COUNTRY_MEASURES = [
    "fa_ex_reserves", "fa_total", "fdi", "portfolio", "portfolio_equity", "portfolio_debt",
    "other_inv", "derivatives", "reserves", "current_account", "capital_account",
    "errors_omissions",
]
HEATMAP_QUARTERS = 40
IMF_BOP_URL = "https://data.imf.org/en/datasets/IMF.STA:BOP"
IMF_WEO_URL = "https://data.imf.org/en/datasets/IMF.RES:WEO"


def _r(x: float | None, nd: int = 2) -> float | None:
    return None if x is None or pd.isna(x) else round(float(x), nd)


def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")


def _values(df: pd.DataFrame, country: str, measure: str, side: str = "net") -> dict[str, float]:
    sub = df[(df.country == country) & (df.measure == measure) & (df.side == side)
             & df.value.notna()]
    return dict(zip(sub.period, sub.value, strict=True))


def _status(df: pd.DataFrame, country: str, periods: list[str]) -> str:
    sub = df[(df.country == country) & (df.measure == MAIN) & (df.side == "net")
             & df.period.isin(periods)]
    if sub.value.isna().any() or len(sub) < len(periods):
        return "missing"
    return "derived" if (sub.obs_status == "derived").any() else "reported"


def country_notes(df: pd.DataFrame, country: str, meta: dict[str, Any], gdp, last_q) -> list[str]:
    notes = []
    if meta.get("financial_centre"):
        notes.append("financial_centre")
    derived = df[(df.country == country) & (df.obs_status == "derived")]
    if not derived.empty:
        notes.append("derived_main")
    if not _values(df, country, "derivatives"):
        notes.append("no_derivatives")
    if last_q:
        eo = pct_of_gdp(_values(df, country, "errors_omissions"), window(last_q), gdp, country)
        if eo is not None and abs(eo) > 1.0:
            notes.append("large_errors_omissions")
    return notes


def export_all(
    out: Path,
    df: pd.DataFrame,
    *,
    gdp: dict[tuple[str, int], float],
    countries: list[str],
    names: dict[str, dict[str, Any]],
    top: list[str],
    last_common: str,
    ref_year: int,
    latest: dict[str, str | None],
    data_updated_at: str,
    warnings: list[str],
) -> None:
    q4 = window(last_common)
    year_q = [f"{ref_year}-Q{i}" for i in range(1, 5)]
    first_q = min(df[df.freq == "Q"].period, key=q_index)

    # ---------------------------------------------------------------- ranking.json
    rows = []
    for c in countries:
        vals: dict[str, Any] = {}
        for m in RANKING_MEASURES:
            v = _values(df, c, m)
            entry = {}
            for name, periods in (("q", [last_common]), ("4q", q4), ("year", year_q)):
                total = sum(v[p] for p in periods) if all(p in v for p in periods) else None
                entry[name] = {"usd": _r(total), "pct": _r(pct_of_gdp(v, periods, gdp, c))}
            lq = max(v, key=q_index) if v else None
            entry["latest"] = {
                "period": lq,
                "usd": _r(v.get(lq)) if lq else None,
                "pct": _r(pct_of_gdp(v, [lq], gdp, c)) if lq else None,
            }
            vals[m] = entry
        rows.append({
            "country": c,
            "in_top20": c in top,
            "status": {"q": _status(df, c, [last_common]), "4q": _status(df, c, q4),
                       "year": _status(df, c, year_q)},
            "values": vals,
        })
    _write(out / "ranking.json", {
        "last_common_quarter": last_common,
        "reference_year": ref_year,
        "windows": {"q": [last_common], "4q": q4, "year": year_q},
        "rows": rows,
    })

    # ---------------------------------------------------------------- country/<ISO3>.json
    for c in countries:
        lq = latest.get(c)
        own = df[(df.country == c) & (df.freq == "Q")].period
        periods = quarter_range(first_q, max(own, key=q_index)) if len(own) else []
        series: dict[str, dict[str, list]] = {}
        keys: dict[str, dict[str, str]] = {}
        for m in COUNTRY_MEASURES:
            for side in ("net", "assets", "liabilities"):
                sub = df[(df.country == c) & (df.measure == m) & (df.side == side)]
                if sub.empty:
                    continue
                v = dict(zip(sub.period, sub.value, strict=True))
                series.setdefault(m, {})[side] = [_r(v.get(p)) for p in periods]
                keys.setdefault(m, {})[side] = sub.series_key.iloc[-1]
        main = _values(df, c, MAIN)
        derived = sorted(df[(df.country == c) & (df.obs_status == "derived")].period,
                         key=q_index)
        _write(out / "country" / f"{c}.json", {
            "country": c,
            "in_top20": c in top,
            "periods": periods,
            "latest": lq,
            "series": series,
            "pct_gdp_4q": {MAIN: [
                _r(pct_of_gdp(main, window(p), gdp, c)) if q_index(p) >= q_index(first_q) + 3
                else None for p in periods
            ]},
            "gdp_usd_bn": {str(y): _r(v, 1) for (cc, y), v in sorted(gdp.items())
                           if cc == c and periods
                           and int(first_q[:4]) <= y <= int(periods[-1][:4])},
            "gdp_estimate_from": ref_year + 1,
            "derived_periods": derived,
            "series_keys": keys,
            "notes": country_notes(df, c, names.get(c, {}), gdp, lq),
        })
        # CSV download: tidy rows for this country
        sub = df[df.country == c][["country", "period", "measure", "side", "value", "value_raw",
                                   "obs_status", "series_key"]]
        (out / "download").mkdir(parents=True, exist_ok=True)
        sub.to_csv(out / "download" / f"{c}.csv", index=False, float_format="%.6g")

    # ---------------------------------------------------------------- heatmap.json
    hm_periods = window(last_common, HEATMAP_QUARTERS)
    _write(out / "heatmap.json", {
        "measure": MAIN,
        "periods": hm_periods,
        "rows": [
            {
                "country": c,
                "usd": [_r(_values(df, c, MAIN).get(p)) for p in hm_periods],
                "pct": [_r(pct_of_gdp(_values(df, c, MAIN), [p], gdp, c)) for p in hm_periods],
            }
            for c in countries
        ],
    })

    # ---------------------------------------------------------------- meta.json
    _write(out / "meta.json", {
        "data_updated_at": data_updated_at,
        "last_common_quarter": last_common,
        "reference_year": ref_year,
        "top20": top,
        "countries": [
            {"iso3": c, "name_nb": names.get(c, {}).get("name_nb", c),
             "name_en": names.get(c, {}).get("name_en", c), "in_top20": c in top,
             "aggregate": bool(names.get(c, {}).get("aggregate")),
             "financial_centre": bool(names.get(c, {}).get("financial_centre")),
             "iso_num": names.get(c, {}).get("iso_num"),
             "latest": latest.get(c)}
            for c in countries
        ],
        "sources": [
            {"id": "IMF_BOP",
             "citation": f"Source: International Monetary Fund, Balance of Payments (BOP), "
                         f"{IMF_BOP_URL}",
             "url": IMF_BOP_URL},
            {"id": "IMF_WEO",
             "citation": "Source: International Monetary Fund, World Economic Outlook (WEO), "
                         f"{IMF_WEO_URL}",
             "url": IMF_WEO_URL},
        ],
        "warnings": warnings,
    })
