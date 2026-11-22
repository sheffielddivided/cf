import pytest

from pipeline.normalize import to_inflow_sign, to_usd_bn


def test_net_financial_account_is_flipped():
    # BPM6: +100 = net lending abroad (outflow) -> site: -100
    assert to_inflow_sign("fa_ex_reserves", "net", 100.0) == -100.0
    assert to_inflow_sign("fa_total", "net", -250.0) == 250.0


def test_liabilities_keep_sign_assets_flip():
    assert to_inflow_sign("portfolio", "liabilities", 40.0) == 40.0
    assert to_inflow_sign("portfolio", "assets", 30.0) == -30.0


def test_sides_add_up_to_net():
    assets, liabilities = 30.0, 40.0
    net_bpm6 = assets - liabilities
    assert to_inflow_sign("fdi", "net", net_bpm6) == pytest.approx(
        to_inflow_sign("fdi", "assets", assets) + to_inflow_sign("fdi", "liabilities", liabilities)
    )


def test_non_financial_measures_unchanged():
    assert to_inflow_sign("current_account", "net", 12.5) == 12.5
    assert to_inflow_sign("gdp_usd", "net", 27000.0) == 27000.0


def test_missing_stays_missing():
    assert to_inflow_sign("fdi", "net", None) is None
    assert to_usd_bn(None, 6) is None


def test_unknown_side_rejected():
    with pytest.raises(ValueError):
        to_inflow_sign("fdi", "gross", 1.0)


def test_to_usd_bn():
    assert to_usd_bn(1500.0, 6) == pytest.approx(1.5)
    assert to_usd_bn(2.0, 9) == pytest.approx(2.0)
    with pytest.raises(ValueError):
        to_usd_bn(1.0, 6, currency="EUR")
