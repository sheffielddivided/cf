"""Phase 3: positions (PIP/DIP/BIS), episodes and the quarterly summary draft."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
import pytest

from pipeline import episodes, phase3
from pipeline import summary as quarterly
from pipeline.model import quarter_range
from pipeline.sources import positions as pos

FX = Path(__file__).parent / "fixtures"


# ------------------------------------------------------------------------------ positions


def test_iso2_skips_aggregates():
    assert pos.iso2("NOR") == "NO"
    assert pos.iso2("G001") is None  # world
    assert pos.iso2("GX031") is None  # IMF aggregate


def test_pip_values_in_usd_bn():
    v = pos.pip_values((FX / "pip.csv").read_text())
    assert v[("USA", "CAN", "2025-S2")] == pytest.approx(1879.249)
    assert v[("USA", "G001", "2025-S2")] == pytest.approx(19189.0, rel=1e-3)
    assert pos.common_period(v) == "2025-S2"


def test_dip_values_directions():
    v = pos.dip_values((FX / "dip.csv").read_text())
    assert v[("USA", "in", "CAN", "2024")] == pytest.approx(732.91)
    assert any(k[1] == "out" for k in v)


def test_bis_values_skip_series_rows():
    v = pos.bis_values((FX / "bis_lbs.csv").read_text())
    assert v[("CN", "liabilities", "2025-Q1")] == pytest.approx(147.4)  # USD mn -> bn
    assert all(q for (_, _, q) in v)


def test_bis_key():
    assert pos.bis_key(["US", "NO"]).endswith(".A.US+NO.N")


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if request.url.host == "stats.bis.org":
        return httpx.Response(200, text=(FX / "bis_lbs.csv").read_text())
    if "/PIP/" in path:
        return httpx.Response(200, text=(FX / "pip.csv").read_text())
    if "/DIP/" in path:
        return httpx.Response(200, text=(FX / "dip.csv").read_text())
    return httpx.Response(500)


def test_holdings_shape():
    warnings: list[str] = []
    countries = ["USA", "CHN", "NOR"]
    h = phase3.holdings(countries, {"USA": "US", "CHN": "CN", "NOR": "NO"}, warnings,
                        transport=httpx.MockTransport(_handler))
    assert warnings == []
    usa = h["countries"]["USA"]
    assert usa["pip_assets"]["period"] == "2025-S2"
    top = [t["iso3"] for t in usa["pip_assets"]["top"]]
    assert top[0] == "CYM" and "G001" not in top and "GX031" not in top
    assert usa["dip_in"]["period"] == "2024"
    # CHN is held by USA (reporter) in the matrix and in held_by
    assert h["countries"]["CHN"]["pip_held_by"]["top"][0]["iso3"] == "USA"
    m = h["pip_matrix"]
    assert m["usd_bn"][0][1] == pytest.approx(319.6)
    assert m["usd_bn"][1][0] is None  # missing stays null, never 0
    assert h["countries"]["CHN"]["bis"]["claims"]


def test_holdings_never_fatal():
    warnings: list[str] = []
    h = phase3.holdings(["USA"], {"USA": "US"}, warnings,
                        transport=httpx.MockTransport(lambda r: httpx.Response(400)))
    assert h is None
    assert warnings and all(w.startswith("beholdninger") for w in warnings)


# ------------------------------------------------------------------------------ episodes


def _df(values: dict[str, list[float]], periods: list[str], country: str = "AAA") -> pd.DataFrame:
    rows = []
    for side, vals in values.items():
        for p, v in zip(periods, vals, strict=True):
            for m in episodes.COMPONENTS:
                rows.append({"country": country, "side": side, "measure": m, "freq": "Q",
                             "period": p, "value_raw": None if v is None else v / 3 * 1e9})
    return pd.DataFrame(rows)


def test_episode_detects_surge_and_respects_last_common():
    periods = quarter_range("2010-Q1", "2026-Q2")
    rng = np.random.default_rng(1)
    base = list(100 + rng.normal(0, 5, len(periods)))
    surge = base.copy()
    for i in range(len(periods) - 2, len(periods)):  # big jump in 2026-Q1 and 2026-Q2
        surge[i] += 120
    df = _df({"liabilities": surge, "assets": base}, periods)
    out = episodes.compute(df, ["AAA"], "2026-Q2")
    inflow = out["countries"]["AAA"]["inflows"]
    assert inflow["periods"][-1] == "2026-Q2"
    assert any(e["type"] == "inflow_surge" for e in inflow["episodes"])
    assert {"country": "AAA", "type": "inflow_surge"}.items() <= out["active"][0].items()
    # cut-off: with an earlier last common quarter the surge is not seen
    early = episodes.compute(df, ["AAA"], "2025-Q4")
    assert early["countries"]["AAA"]["inflows"]["periods"][-1] == "2025-Q4"
    assert not early["active"]


def test_episode_gap_is_not_zero():
    periods = quarter_range("2010-Q1", "2026-Q2")
    vals: list[float | None] = [100.0] * len(periods)
    vals[30] = None
    s = episodes.gross(_df({"liabilities": vals}, periods), "AAA", "liabilities")
    assert pd.isna(s[periods[30]]) and len(s) == len(periods)


def test_short_series_skipped():
    periods = quarter_range("2022-Q1", "2026-Q2")
    df = _df({"liabilities": [1.0] * len(periods)}, periods)
    assert episodes.compute(df, ["AAA"], "2026-Q2")["countries"] == {}


# ------------------------------------------------------------------------------ summary


def _site(tmp: Path) -> Path:
    site = tmp / "data"
    (site / "country").mkdir(parents=True)
    w = ["2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2"]
    (site / "meta.json").write_text(json.dumps({"countries": [
        {"iso3": "USA", "name_nb": "USA", "name_en": "United States"},
        {"iso3": "NOR", "name_nb": "Norge", "name_en": "Norway"},
        {"iso3": "RUS", "name_nb": "Russland", "name_en": "Russia"},
    ]}))

    def row(c, usd, pct):
        return {"country": c, "in_top20": True,
                "values": {"fa_ex_reserves": {"4q": {"usd": usd, "pct": pct}}}}

    (site / "ranking.json").write_text(json.dumps({
        "last_common_quarter": "2026-Q2", "windows": {"4q": w},
        "rows": [row("USA", -1000.0, -3.3), row("NOR", 50.0, 10.0), row("RUS", None, None)],
    }))
    periods = ["2025-Q2", *w]
    (site / "country" / "NOR.json").write_text(json.dumps({
        "periods": periods, "series": {"fa_ex_reserves": {"net": [20, 20, 10, 10, 10]}}}))
    (site / "episodes.json").write_text(json.dumps({"active": [
        {"country": "USA", "type": "outflow_retrenchment", "start": "2026-Q1"}]}))
    return site


def test_summary_draft_nb(tmp_path):
    md = quarterly.draft(_site(tmp_path), "nb", "2026-11-22")
    assert md.startswith("## Kapitalstrømmer: oppsummering for 2. kvartal 2026")
    assert "Norge hadde størst netto innstrømning" not in md  # lead names the top inflow
    assert "hadde Norge størst netto innstrømning, +50,0 mrd. USD" in md
    assert "USA hadde størst netto utstrømning, −1 000,0 mrd. USD" in md
    assert "brå nedgang i utstrømning (siden 1. kvartal 2026)" in md
    assert "Ikke rapportert for perioden: Russland." in md
    assert "| Norge | +50,0 | +50,0 | +0,0 |" not in md
    assert "| Norge | +60,0 | +50,0 | −10,0 |" in md  # change vs four quarters ending 2026-Q1
    assert "kapitalflukt" not in md.lower()
    assert "Source: International Monetary Fund" not in md  # nb text uses "Kilde:"
    assert "Kilde: International Monetary Fund, Balance of Payments (BOP)" in md


def test_summary_draft_en(tmp_path):
    md = quarterly.draft(_site(tmp_path), "en", "2026-11-22")
    assert "summary for Q2 2026" in md
    assert "Norway had the largest net inflow, USD +50.0 bn (+10.0% of GDP)" in md
    assert "outflow retrenchment (since Q1 2026)" in md
