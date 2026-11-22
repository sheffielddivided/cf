"""Phase 2 sources, tested against trimmed real files fetched 22.11.2026."""

from pathlib import Path

import pytest

from pipeline.sources import nowcast, oecd

FX = Path(__file__).parent / "fixtures"


def test_tic_grand_totals_and_net():
    s = nowcast.parse_tic((FX / "slt_table1.txt").read_text(), (FX / "slt_table2.txt").read_text())
    i = s["periods"].index("2026-09")
    assert s["nonres"][i] == pytest.approx(186.707)  # foreigners' net purchases (inflow)
    assert s["res"][i] == pytest.approx(31.389)      # US residents' net purchases abroad
    assert s["net"][i] == pytest.approx(155.318)
    assert s["periods"] == sorted(s["periods"])


def test_ecb_net_excludes_reserves_and_flips_sign():
    s = nowcast.parse_ecb((FX / "ecb_bps.csv").read_text())
    i = s["periods"].index("2026-09")
    # BPM6 net: D 35 795.0 + P -28 147.4 + O 33 772.1 + F7 2 902.4 = 44 322.0 m EUR (lending)
    assert s["net"][i] == pytest.approx(-44.322, abs=0.001)
    # liabilities D+P+O = -2 844.9 + 38 627.0 - 74 183.6
    assert s["nonres"][i] == pytest.approx(-38.4015, abs=0.001)


def test_mof_weekly():
    s = nowcast.parse_mof((FX / "mof_week.csv").read_bytes())
    i = s["periods"].index("2026-11-14")
    assert s["res"][i] == pytest.approx(-77.6)     # -776 hundred-million yen subtotal (assets)
    assert s["nonres"][i] == pytest.approx(426.0)  # 4 260 (liabilities subtotal)
    assert s["net"][i] == pytest.approx(503.6)


@pytest.mark.parametrize(
    ("label", "end"),
    [("2026．11．8〜11．14", "2026-11-14"), ("2025．12．28〜1．3", "2026-01-03"), ("Period", None)],
)
def test_mof_week_labels(label, end):
    assert nowcast._week_end(label) == end


def test_oecd_key_and_values():
    assert oecd.oecd_key(["USA", "G163"]).startswith("USA+EA20.WXD.FA+FA_D_F+FA_P_F+FA_O_F.N.T.Q")
    text = (
        "REF_AREA,MEASURE,ACCOUNTING_ENTRY,UNIT_MEASURE,ADJUSTMENT,TIME_PERIOD,OBS_VALUE,UNIT_MULT\n"
        "USA,FA,N,USD_EXC,N,2026-Q2,-371772,6\n"
        "USA,FA,N,XDC,N,2026-Q2,-1,6\n"
        "EA20,FA_P_F,N,USD_EXC,N,2026-Q2,1500,6\n"
    )
    v = oecd.values(text)
    assert v == {("USA", "fa_total", "2026-Q2"): pytest.approx(-371.772),
                 ("G163", "portfolio", "2026-Q2"): pytest.approx(1.5)}
