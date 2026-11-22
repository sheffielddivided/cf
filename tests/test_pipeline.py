"""End-to-end test of `pipeline update` against a fake IMF API, plus model unit tests."""

import json
import shutil
from datetime import date
from pathlib import Path

import httpx
import pandas as pd
import pytest
import yaml

from pipeline import checks, model
from pipeline.update import run

ROOT = Path(__file__).resolve().parents[1]

# Consistent BPM6 data (bn USD): D + P + F7 + O + R = FAB; CA + KA + EO = FAB.
SERIES = {
    ("NNAFANIL_T", "D_F"): 1.0, ("A_NFA_T", "D_F"): 4.0, ("L_NIL_T", "D_F"): 3.0,
    ("NNAFANIL_T", "P_F"): 2.0, ("A_NFA_T", "P_F"): 5.0, ("L_NIL_T", "P_F"): 3.0,
    ("A_NFA_T", "P_F5"): 1.0, ("L_NIL_T", "P_F5"): 1.0,
    ("A_NFA_T", "P_F3"): 4.0, ("L_NIL_T", "P_F3"): 2.0,
    ("NNAFANIL_T", "F_F7"): 0.5,
    ("NNAFANIL_T", "O_F"): -1.0, ("A_NFA_T", "O_F"): 1.0, ("L_NIL_T", "O_F"): 2.0,
    ("A_T", "R_F"): 0.5, ("NNAFANIL_T", "RUE"): 0.5,
    ("NNAFANIL_T", "FAB"): 3.0, ("NNAFANIL_T", "FABXRRI"): 2.5,
    ("NETCD_T", "CAB"): 2.0, ("NETCD_T", "KAB"): 0.2, ("NETCD_T", "EO"): 0.8,
}
SCALE = {"USA": 100.0, "CHN": -50.0, "DEU": -20.0, "RUS": 10.0, "NOR": -5.0}
GDP = {"USA": 30000.0, "CHN": 19000.0, "DEU": 5000.0, "RUS": 2500.0, "NOR": 500.0}
HEADER = ("STRUCTURE,STRUCTURE_ID,ACTION,COUNTRY,BOP_ACCOUNTING_ENTRY,INDICATOR,UNIT,"
          "FREQUENCY,TIME_PERIOD,OBS_VALUE,STATUS\n")


def quarters(last="2026-Q2"):
    return model.quarter_range("2010-Q1", last)


def bop_csv(country: str) -> str:
    lines = [HEADER]
    last = "2026-Q1" if country == "RUS" else "2026-Q2"
    for p in quarters(last):
        for (entry, ind), v in SERIES.items():
            if country == "RUS" and ind in {"FABXRRI", "RUE"} and p >= "2022":
                continue  # like the real data: no FABXRRI for Russia from 2022
            value = v * SCALE[country] * 1e9
            lines.append(f"dataflow,IMF.STA:BOP(21.0.0),R,{country},{entry},{ind},USD,Q,{p},"
                         f"{value:.0f},\n")
    return "".join(lines)


def weo_csv() -> str:
    lines = ["COUNTRY,INDICATOR,FREQUENCY,TIME_PERIOD,OBS_VALUE\n"]
    for c, v in GDP.items():
        for y in range(2008, 2031):
            lines.append(f"{c},NGDPD,A,{y},{v * 1e9:.0f}\n")
    return "".join(lines)


def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if "/IMF.RES/WEO/" in path:
        return httpx.Response(200, text=weo_csv())
    if "/IMF.STA/BOP/" in path:
        country = path.rsplit("/", 1)[-1].split(".")[0]
        if country in SCALE:
            return httpx.Response(200, text=bop_csv(country))
        return httpx.Response(404, text="NoResultsFound")
    return httpx.Response(500)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    shutil.copy(ROOT / "config/series_map.yaml", tmp_path / "config/series_map.yaml")
    cfg = {
        "extra": ["NOR"], "aggregates": ["EA"],
        "countries": [
            {"iso3": "USA", "name_nb": "USA", "name_en": "United States"},
            {"iso3": "CHN", "name_nb": "Kina", "name_en": "China"},
            {"iso3": "DEU", "name_nb": "Tyskland", "name_en": "Germany"},
            {"iso3": "RUS", "name_nb": "Russland", "name_en": "Russia"},
            {"iso3": "NOR", "name_nb": "Norge", "name_en": "Norway"},
        ],
    }
    (tmp_path / "config/countries.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True))
    return tmp_path


def test_update_end_to_end(repo: Path):
    rc = run(repo, today=date(2026, 11, 22), transport=httpx.MockTransport(handler))
    summary = json.loads((repo / "run/summary.json").read_text())
    assert rc == 0, summary
    assert summary["changed"] and summary["last_common_quarter"] == "2026-Q2"

    sel = json.loads((repo / "data/processed/selection.json").read_text())
    assert sel["reference_year"] == 2025
    assert sel["countries"] == ["USA", "CHN", "DEU", "RUS", "NOR"]  # top N (only 5 exist)

    site = repo / "site/public/data"
    meta = json.loads((site / "meta.json").read_text())
    assert meta["last_common_quarter"] == "2026-Q2"
    assert meta["sources"][0]["citation"].startswith(
        "Source: International Monetary Fund, Balance of Payments (BOP)")

    ranking = json.loads((site / "ranking.json").read_text())
    usa = next(r for r in ranking["rows"] if r["country"] == "USA")
    # FABXRRI = +2.5 * 100 bn per quarter in BPM6 sign = net lending -> outflow of 250/quarter
    assert usa["values"]["fa_ex_reserves"]["4q"]["usd"] == pytest.approx(-1000.0)
    # % of GDP: -1000 / 30000 * 100
    assert usa["values"]["fa_ex_reserves"]["4q"]["pct"] == pytest.approx(-3.33, abs=0.01)
    chn = next(r for r in ranking["rows"] if r["country"] == "CHN")
    assert chn["values"]["fa_ex_reserves"]["q"]["usd"] == pytest.approx(125.0)  # inflow

    # Russia: derived main measure from 2022, and missing for 2026-Q2 (not zero)
    rus = next(r for r in ranking["rows"] if r["country"] == "RUS")
    assert rus["status"]["4q"] == "missing"
    assert rus["values"]["fa_ex_reserves"]["4q"]["usd"] is None
    assert rus["values"]["fa_ex_reserves"]["latest"]["period"] == "2026-Q1"
    rus_country = json.loads((site / "country/RUS.json").read_text())
    assert "2022-Q1" in rus_country["derived_periods"]
    assert "derived_main" in rus_country["notes"]
    i = rus_country["periods"].index("2023-Q1")
    # FAB - R_F = (3.0 - 0.5) * 10 = 25 bn net lending -> -25 in site sign
    assert rus_country["series"]["fa_ex_reserves"]["net"][i] == pytest.approx(-25.0)

    # Euro area (no data in the fake API) is listed, with no values
    assert any(c["iso3"] == "G163" for c in meta["countries"])
    assert (site / "download/USA.csv").exists()
    assert not [w for w in summary["warnings"] if w.startswith(("identitet", "speiling"))]

    # A second identical run changes nothing
    before = (site / "meta.json").read_text()
    rc = run(repo, today=date(2026, 11, 29), transport=httpx.MockTransport(handler))
    summary = json.loads((repo / "run/summary.json").read_text())
    assert rc == 0 and summary["changed"] is False
    assert (site / "meta.json").read_text() == before


def test_source_error_writes_nothing(repo: Path):
    rc = run(repo, today=date(2026, 11, 22),
             transport=httpx.MockTransport(lambda r: httpx.Response(400)))
    assert rc == 2
    assert not (repo / "data/processed").exists()
    assert json.loads((repo / "run/summary.json").read_text())["status"] == "source_error"


def test_reference_year():
    assert model.reference_year("2026-Q2") == 2025
    assert model.reference_year("2026-Q4") == 2026
    assert model.reference_year("2027-Q1") == 2026


def test_pct_of_gdp_and_missing():
    gdp = {("USA", 2025): 400.0, ("USA", 2026): 800.0}
    vals = {"2025-Q4": 10.0, "2026-Q1": 20.0}
    # (10 + 20) / (100 + 200) * 100
    assert model.pct_of_gdp(vals, ["2025-Q4", "2026-Q1"], gdp, "USA") == pytest.approx(10.0)
    assert model.pct_of_gdp(vals, ["2026-Q1", "2026-Q2"], gdp, "USA") is None
    assert model.window_sum(vals, ["2025-Q4", "2026-Q2"]) is None


def test_compare_revisions():
    old = pd.DataFrame({"country": ["USA", "USA"], "measure": ["fdi", "fdi"],
                        "side": ["net", "net"], "period": ["2026-Q1", "2025-Q4"],
                        "value": [10.0, 5.0]})
    new = old.copy()
    new.loc[0, "value"] = 15.0
    new = pd.concat([new, pd.DataFrame({"country": ["USA"], "measure": ["fdi"],
                                        "side": ["net"], "period": ["2026-Q2"],
                                        "value": [1.0]})])
    stats, big = checks.compare_revisions(old, new)
    assert stats == {"new": 1, "revised": 1, "removed": 0}
    assert big == ["USA fdi/net 2026-Q1: 10.0 → 15.0"]
