import pytest

from pipeline.coverage import (
    SeriesCoverage,
    last_common_quarter,
    q_index,
    q_label,
    top_n_by_gdp,
)


def test_quarter_roundtrip():
    assert q_label(q_index("2026-Q2")) == "2026-Q2"
    assert q_index("2026-Q1") - q_index("2025-Q4") == 1
    with pytest.raises(ValueError):
        q_index("2026")


def test_series_coverage_counts_gaps():
    c = SeriesCoverage.from_periods(["2025-Q1", "2025-Q2", "2025-Q4", "2025-Q2"])
    assert (c.first, c.last, c.count, c.gaps) == ("2025-Q1", "2025-Q4", 3, 1)
    assert SeriesCoverage.from_periods([]).last is None


def test_last_common_quarter_uses_80_percent():
    latest = {
        "A": "2026-Q2", "B": "2026-Q2", "C": "2026-Q2", "D": "2026-Q2",
        "E": "2026-Q1",
    }
    q, behind = last_common_quarter(latest)
    assert q == "2026-Q2" and behind == ["E"]

    latest["D"] = "2025-Q4"
    q, behind = last_common_quarter(latest)  # need 4 of 5: A, B, C and E reach 2026-Q1
    assert q == "2026-Q1" and behind == ["D"]


def test_last_common_quarter_counts_missing_countries():
    q, behind = last_common_quarter({"A": "2026-Q2", "B": None, "C": None})
    assert q is None and behind == ["A", "B", "C"]


def test_top_n_by_gdp_skips_aggregates():
    gdp = {("USA", 2025): 30000.0, ("G163", 2025): 17000.0, ("EUR", 2025): 25000.0,
           ("CHN", 2025): 19000.0, ("USA", 2024): 29000.0, ("NOR", 2025): 500.0}
    assert top_n_by_gdp(gdp, 2025, 2) == [("USA", 30000.0), ("CHN", 19000.0)]
