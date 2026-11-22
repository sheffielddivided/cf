from pathlib import Path

import pytest

from pipeline.sources import imf

ROOT = Path(__file__).resolve().parents[1]

# Rows in the IMF.STA:BOP(21.0.0) SDMX-CSV 2.0 layout (columns trimmed, values illustrative).
CSV = (
    "STRUCTURE,STRUCTURE_ID,ACTION,COUNTRY,BOP_ACCOUNTING_ENTRY,INDICATOR,UNIT,FREQUENCY,"
    "TIME_PERIOD,OBS_VALUE,SCALE,STATUS\n"
    """dataflow,IMF.STA:BOP(21.0.0),R,USA,NNAFANIL_T,FABXRRI,USD,Q,2026-Q2,-375000000000,6,
dataflow,IMF.STA:BOP(21.0.0),R,USA,A_NFA_T,D_F,USD,Q,2026-Q2,100000000000,6,
dataflow,IMF.STA:BOP(21.0.0),R,USA,L_NIL_T,D_F,USD,Q,2026-Q2,137869000000,6,
dataflow,IMF.STA:BOP(21.0.0),R,USA,NETCD_T,CAB,USD,Q,2026-Q2,-260500000000,6,
dataflow,IMF.STA:BOP(21.0.0),R,USA,A_NFA_T,D1_FL,USD,Q,2026-Q2,5,6,
dataflow,IMF.STA:BOP(21.0.0),R,USA,NETCD_T,EO,USD,Q,2026-Q2,,6,
"""
)


@pytest.fixture(scope="module")
def section():
    return imf.load_series_map(ROOT / "config/series_map.yaml")["imf_bop"]


def obs(section):
    rows = imf.parse_csv(CSV)
    return {(o["measure"], o["side"]): o
            for o in imf.bop_observations(rows, section, country="USA", retrieved_at="t")}


def test_series_map_covers_design_measures(section):
    measures = {r.measure for r in imf.series_refs(section)}
    for m in ["fa_total", "fa_ex_reserves", "fdi", "portfolio", "other_inv", "derivatives",
              "reserves", "current_account", "errors_omissions"]:
        assert m in measures


def test_bop_key_uses_plus_for_multiple_codes(section):
    key = imf.bop_key("USA", imf.series_refs(section), "USD", "Q")
    country, entries, indicators, unit, freq = key.split(".")
    assert country == "USA" and unit == "USD" and freq == "Q"
    assert "NNAFANIL_T" in entries.split("+") and "FABXRRI" in indicators.split("+")


def test_observations_are_signed_and_scaled(section):
    o = obs(section)
    # BPM6 net FA of -375 bn = net borrowing from abroad -> +375 bn net inflow
    assert o[("fa_ex_reserves", "net")]["value"] == pytest.approx(375.0)
    assert o[("fa_ex_reserves", "net")]["value_raw"] == -375e9
    assert o[("fdi", "assets")]["value"] == pytest.approx(-100.0)
    assert o[("fdi", "liabilities")]["value"] == pytest.approx(137.869)
    assert o[("current_account", "net")]["value"] == pytest.approx(-260.5)


def test_unmapped_rows_ignored_and_missing_kept_as_none(section):
    o = obs(section)
    assert all(k[0] != "D1_FL" for k in o)
    eo = o[("errors_omissions", "net")]
    assert eo["value"] is None and eo["obs_status"] == "missing"


def test_gdp_by_country_year():
    rows = imf.parse_csv(
        "COUNTRY,INDICATOR,FREQUENCY,TIME_PERIOD,OBS_VALUE\n"
        "USA,NGDPD,A,2025,30000000000000\nNOR,NGDPD,A,2025,\n"
    )
    assert imf.gdp_by_country_year(rows) == {("USA", 2025): 30000.0}
