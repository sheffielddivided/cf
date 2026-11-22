"""Phase 3: bilateral POSITIONS (stocks, never flows).

- IMF PIP (formerly CPIS): portfolio investment positions by counterpart economy, semiannual.
- IMF DIP (formerly CDIS): direct investment positions by counterpart economy, annual.
- BIS locational banking statistics: cross-border bank claims on / liabilities to a country.

Codes verified against IMF.STA:PIP / IMF.STA:DIP and BIS:WS_LBS_D_PUB structures on 22.11.2026.
"""

from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from collections.abc import Iterable

import pycountry

from ..sdmx import DATA_CSV_V2, SdmxClient

IMF_V3 = "https://api.imf.org/external/sdmx/3.0"
BIS_V2 = "https://stats.bis.org/api/v2"

PIP_INDICATOR = "P_TOTINV_P_USD"  # total portfolio investment, positions, USD
DIP_OUT = "OTWD_D_NETAL_FALL_ALL"  # outward DI, net (assets less liabilities), all instruments
DIP_IN = "INWD_D_NETLA_FALL_ALL"  # inward DI, net (liabilities less assets), all instruments

_ISO3 = re.compile(r"^[A-Z]{3}$")


def iso2(code3: str) -> str | None:
    """ISO alpha-2 for a real economy; None for aggregates such as G001 or GX031."""
    if not _ISO3.match(code3):
        return None
    c = pycountry.countries.get(alpha_3=code3)
    return c.alpha_2 if c else None


def _csv(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def _get(client: SdmxClient, path: str, params: dict[str, str]) -> str:
    resp = client.get(path, params=params, accept=DATA_CSV_V2)
    if resp.status_code == 404:
        return ""
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} for {path[:80]}")
    return resp.text


# ------------------------------------------------------------------------------ IMF PIP


def pip_key(reporters: str, counterparts: str) -> str:
    return f"{reporters}.A.{PIP_INDICATOR}.S1.S1.{counterparts}.S"


def fetch_pip(client: SdmxClient, countries: list[str], start: str = "2023-S1") -> tuple[str, str]:
    """(our countries' holdings everywhere, everyone's holdings in our countries)."""
    ours = "+".join(countries)
    path = "data/dataflow/IMF.STA/PIP/+/"
    params = {"c[TIME_PERIOD]": f"ge:{start}"}
    return (
        _get(client, path + pip_key(ours, "*"), params),
        _get(client, path + pip_key("*", ours), params),
    )


def pip_values(text: str) -> dict[tuple[str, str, str], float]:
    """(holder, issuer, period) -> USD bn. World total kept under issuer 'G001'."""
    out: dict[tuple[str, str, str], float] = {}
    for r in _csv(text):
        if r.get("INDICATOR") != PIP_INDICATOR or r.get("ACCOUNTING_ENTRY") != "A":
            continue
        if r.get("SECTOR") != "S1" or r.get("COUNTERPART_SECTOR") != "S1":
            continue
        v = (r.get("OBS_VALUE") or "").strip()
        if v:
            out[(r["COUNTRY"], r["COUNTERPART_COUNTRY"], r["TIME_PERIOD"])] = float(v) / 1e9
    return out


def common_period(values: dict[tuple[str, str, str], float], share: float = 0.8) -> str | None:
    """Latest period reported by at least `share` of the reporters seen in the busiest period."""
    reporters: dict[str, set[str]] = defaultdict(set)
    for holder, _issuer, period in values:
        reporters[period].add(holder)
    if not reporters:
        return None
    most = max(len(s) for s in reporters.values())
    ok = [p for p, s in reporters.items() if len(s) >= share * most]
    return max(ok) if ok else None


# ------------------------------------------------------------------------------ IMF DIP


def fetch_dip(client: SdmxClient, countries: list[str], start: str = "2021") -> str:
    key = f"{'+'.join(countries)}.O.{DIP_OUT}+{DIP_IN}.*.A"
    return _get(client, f"data/dataflow/IMF.STA/DIP/+/{key}", {"c[TIME_PERIOD]": f"ge:{start}"})


def dip_values(text: str) -> dict[tuple[str, str, str, str], float]:
    """(reporter, 'out'|'in', counterpart, year) -> USD bn (reported data only)."""
    out: dict[tuple[str, str, str, str], float] = {}
    for r in _csv(text):
        ind = r.get("INDICATOR")
        if ind not in (DIP_OUT, DIP_IN) or r.get("DV_TYPE", "O") != "O":
            continue
        v = (r.get("OBS_VALUE") or "").strip()
        if v:
            direction = "out" if ind == DIP_OUT else "in"
            out[(r["COUNTRY"], direction, r["COUNTERPART_COUNTRY"], r["TIME_PERIOD"])] = (
                float(v) / 1e9
            )
    return out


# ------------------------------------------------------------------------------ BIS LBS


def bis_key(iso2_codes: Iterable[str]) -> str:
    """All reporting banks' cross-border claims (C) and liabilities (L), all instruments,
    all currencies, all sectors, amounts outstanding, vis-à-vis the given countries."""
    return f"Q.S.C+L.A.TO1.A.5J.A.5A.A.{'+'.join(iso2_codes)}.N"


def fetch_bis(client: SdmxClient, iso2_codes: list[str], start: str = "2020-Q1") -> str:
    return _get(
        client,
        f"data/dataflow/BIS/WS_LBS_D_PUB/+/{bis_key(iso2_codes)}",
        {"c[TIME_PERIOD]": f"ge:{start}"},
    )


def bis_values(text: str) -> dict[tuple[str, str, str], float]:
    """(counterpart ISO2, 'claims'|'liabilities', quarter) -> USD bn."""
    out: dict[tuple[str, str, str], float] = {}
    for r in _csv(text):
        if (
            not r.get("TIME_PERIOD")
            or r.get("L_MEASURE") != "S"
            or r.get("L_POSITION") not in ("C", "L")
        ):
            continue
        v = (r.get("OBS_VALUE") or "").strip()
        if not v:
            continue
        mult = int(r.get("UNIT_MULT") or 6)
        side = "claims" if r["L_POSITION"] == "C" else "liabilities"
        out[(r["L_CP_COUNTRY"], side, r["TIME_PERIOD"])] = float(v) * 10 ** (mult - 9)
    return out
