"""Phase 2 additions to `pipeline update`: OECD cross-check and nowcast sources.

Neither may stop the main pipeline: failures become warnings, and a nowcast source that
fails keeps its previous values (marked stale) so the tab does not go blank.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from .crosscheck import compare
from .model import window
from .sdmx import SdmxClient
from .sources import nowcast, oecd

log = logging.getLogger(__name__)

KEEP = {"M": 36, "W": 104}  # months / weeks shown on the site


def crosscheck(df: pd.DataFrame, countries: list[str], last_common: str, warnings: list[str],
               transport=None) -> dict[str, Any] | None:
    periods = window(last_common, 8)
    try:
        with SdmxClient(oecd.OECD_BASE, transport=transport) as c:
            status, text = oecd.fetch_csv(c, countries, periods[0])
        if status != 200:
            raise RuntimeError(f"HTTP {status}")
        result = compare(df, oecd.values(text), periods, countries)
    except Exception as exc:  # noqa: BLE001 - a cross-check must never stop the pipeline
        log.warning("OECD cross-check failed: %s", exc)
        warnings.append(f"kryssjekk: OECD utilgjengelig ({exc})")
        return None
    n = len(result["flagged"])
    if n:
        warnings.append(f"kryssjekk: {n} avvik over 5 % mellom IMF og OECD (se datakvalitet-siden)")
    return result


def _get(url: str, transport=None) -> tuple[int, bytes]:
    base, _, rest = url.rpartition("/")
    with SdmxClient(base, transport=transport) as c:
        resp = c.get(rest)
        return resp.status_code, resp.content


def _trim(s: dict, freq: str) -> dict:
    k = KEEP[freq]
    return {key: v[-k:] for key, v in s.items()}


SOURCES: dict[str, dict[str, Any]] = {
    "US_TIC": {"country": "USA", "freq": "M", "currency": "USD",
               "url": "https://home.treasury.gov/data/treasury-international-capital-tic-system",
               "citation": "Source: U.S. Department of the Treasury, Treasury International "
                           "Capital (TIC) System, SLT tables 1 and 2"},
    "EA_ECB": {"country": "G163", "freq": "M", "currency": "EUR",
               "url": "https://data.ecb.europa.eu/data/datasets/BPS",
               "citation": "Source: European Central Bank, Balance of Payments (BPS), "
                           "euro area changing composition"},
    "JP_MOF": {"country": "JPN", "freq": "W", "currency": "JPY",
               "url": "https://www.mof.go.jp/english/policy/international_policy/reference/"
                      "itn_transactions_in_securities/index.htm",
               "citation": "Source: Ministry of Finance Japan, International Transactions in "
                           "Securities (weekly, designated major investors)"},
}


def _fetch_one(sid: str, transport=None) -> dict:
    if sid == "US_TIC":
        s1, t1 = _get(nowcast.TIC_T1, transport)
        s2, t2 = _get(nowcast.TIC_T2, transport)
        if s1 != 200 or s2 != 200:
            raise RuntimeError(f"HTTP {s1}/{s2}")
        return nowcast.parse_tic(t1.decode("utf-8", "replace"), t2.decode("utf-8", "replace"))
    if sid == "EA_ECB":
        with SdmxClient(nowcast.ECB_BASE, transport=transport) as c:
            resp = c.get(f"data/BPS/{nowcast.ECB_KEY}",
                         params={"startPeriod": "2020-01", "format": "csvdata"})
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")
        return nowcast.parse_ecb(resp.text)
    if sid == "JP_MOF":
        status, raw = _get(nowcast.MOF_WEEK, transport)
        if status != 200:
            raise RuntimeError(f"HTTP {status}")
        return nowcast.parse_mof(raw)
    raise KeyError(sid)


def nowcast_data(previous: dict | None, warnings: list[str], transport=None) -> dict:
    out: dict[str, Any] = {"sources": {}}
    prev = (previous or {}).get("sources", {})
    for sid, meta in SOURCES.items():
        try:
            series = _fetch_one(sid, transport)
            if not series["periods"]:
                raise RuntimeError("ingen data i svaret")
            out["sources"][sid] = {**meta, **_trim(series, meta["freq"]), "stale": False}
        except Exception as exc:  # noqa: BLE001 - nowcast must never stop the pipeline
            log.warning("nowcast %s failed: %s", sid, exc)
            warnings.append(f"nåkast: {sid} utilgjengelig ({exc}); viser forrige tall")
            if sid in prev:
                out["sources"][sid] = {**prev[sid], "stale": True}
    return out
