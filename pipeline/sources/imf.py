"""IMF BOP and WEO via the SDMX 3.0 API (api.imf.org)."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..normalize import to_inflow_sign, to_usd_bn
from ..sdmx import DATA_CSV_V2, SdmxClient

IMF_V3 = "https://api.imf.org/external/sdmx/3.0"
SOURCE_BOP = "IMF_BOP"
SOURCE_WEO = "IMF_WEO"


@dataclass(frozen=True)
class SeriesRef:
    measure: str
    side: str
    indicator: str
    entry: str | None = None


def load_series_map(path: Path | str = "config/series_map.yaml") -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text())


def series_refs(section: dict[str, Any]) -> list[SeriesRef]:
    refs = []
    for measure, sides in (section.get("measures") or {}).items():
        for side, spec in sides.items():
            refs.append(SeriesRef(measure, side, spec["indicator"], spec.get("entry")))
    return refs


def parse_csv(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def _float(value: str | None) -> float | None:
    if value is None or value.strip() in {"", "NaN", "NA"}:
        return None
    return float(value)


def bop_key(country: str, refs: Iterable[SeriesRef], unit: str, freq: str) -> str:
    entries = sorted({r.entry for r in refs if r.entry})
    indicators = sorted({r.indicator for r in refs})
    return ".".join([country, "+".join(entries), "+".join(indicators), unit, freq])


def fetch_bop_csv(
    client: SdmxClient,
    country: str,
    section: dict[str, Any],
    *,
    freq: str = "Q",
    start: str = "2010-Q1",
) -> tuple[int, str]:
    """Return (HTTP status, SDMX-CSV text). 404 means "no data" in SDMX."""
    refs = series_refs(section)
    key = bop_key(country, refs, section.get("unit", "USD"), freq)
    path = f"data/dataflow/{section['agency']}/{section['dataflow']}/+/{key}"
    resp = client.get(path, params={"c[TIME_PERIOD]": f"ge:{start}"}, accept=DATA_CSV_V2)
    return resp.status_code, resp.text if resp.status_code == 200 else ""


def fetch_bop_rows(
    client: SdmxClient,
    country: str,
    section: dict[str, Any],
    *,
    freq: str = "Q",
    start: str = "2010-Q1",
) -> tuple[int, list[dict[str, str]]]:
    status, text = fetch_bop_csv(client, country, section, freq=freq, start=start)
    return status, parse_csv(text) if status == 200 else []


def bop_observations(
    rows: Iterable[dict[str, str]],
    section: dict[str, Any],
    *,
    country: str,
    retrieved_at: str,
) -> Iterator[dict[str, Any]]:
    """Map raw BOP CSV rows to tidy observations (one per measure × side)."""
    lookup: dict[tuple[str, str], list[SeriesRef]] = {}
    for ref in series_refs(section):
        lookup.setdefault((ref.indicator, ref.entry or ""), []).append(ref)
    for row in rows:
        refs = lookup.get((row["INDICATOR"], row["BOP_ACCOUNTING_ENTRY"]))
        if not refs or row.get("UNIT") != "USD":
            continue
        raw = _float(row.get("OBS_VALUE"))
        for ref in refs:
            yield {
                "country": country,
                "period": row["TIME_PERIOD"],
                "freq": row["FREQUENCY"],
                "measure": ref.measure,
                "side": ref.side,
                "value_raw": raw,
                "value": to_inflow_sign(ref.measure, ref.side, to_usd_bn(raw, 0)),
                "unit": "USD_bn",
                "source": SOURCE_BOP,
                "series_key": ".".join(
                    [row["COUNTRY"], row["BOP_ACCOUNTING_ENTRY"], row["INDICATOR"],
                     row["UNIT"], row["FREQUENCY"]]
                ),
                "obs_status": "missing" if raw is None else (row.get("STATUS") or "reported"),
                "retrieved_at": retrieved_at,
            }


def fetch_weo_csv(client: SdmxClient, section: dict[str, Any]) -> tuple[int, str]:
    indicator = section["measures"]["gdp_usd"]["net"]["indicator"]
    path = f"data/dataflow/{section['agency']}/{section['dataflow']}/+/*.{indicator}.A"
    resp = client.get(path, accept=DATA_CSV_V2)
    return resp.status_code, resp.text if resp.status_code == 200 else ""


def fetch_weo_gdp(client: SdmxClient, section: dict[str, Any]) -> tuple[int, list[dict[str, str]]]:
    status, text = fetch_weo_csv(client, section)
    return status, parse_csv(text) if status == 200 else []


def gdp_by_country_year(rows: Iterable[dict[str, str]]) -> dict[tuple[str, int], float]:
    """GDP in USD bn per (country, year). WEO OBS_VALUE is in whole USD."""
    out: dict[tuple[str, int], float] = {}
    for row in rows:
        value = _float(row.get("OBS_VALUE"))
        if value is None:
            continue
        out[(row["COUNTRY"], int(row["TIME_PERIOD"]))] = value / 1e9
    return out
