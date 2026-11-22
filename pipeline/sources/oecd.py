"""OECD balance of payments (DSD_BOP@DF_BOP) — used only as a cross-check against IMF.

Codes verified against OECD data in phase 0 (USA 2026-Q2: FA net = -371 772 m USD, identical
to IMF FAB). Values are in millions (UNIT_MULT 6), BPM6 sign.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable

from ..sdmx import SdmxClient

OECD_BASE = "https://sdmx.oecd.org/public/rest"
FLOW = "OECD.SDD.TPS,DSD_BOP@DF_BOP,"
SOURCE = "OECD_BOP"
URL = "https://data-explorer.oecd.org/"

# our measure -> OECD MEASURE (accounting entry N = net, transactions, quarterly, USD)
MEASURES = {"fa_total": "FA", "fdi": "FA_D_F", "portfolio": "FA_P_F", "other_inv": "FA_O_F"}
# IMF country code -> OECD REF_AREA, where they differ
AREA = {"G163": "EA20"}


def oecd_key(areas: Iterable[str]) -> str:
    codes = "+".join(AREA.get(a, a) for a in areas)
    return f"{codes}.WXD.{'+'.join(MEASURES.values())}.N.T.Q.USD_EXC.N"


def fetch_csv(client: SdmxClient, areas: list[str], start: str) -> tuple[int, str]:
    resp = client.get(f"data/{FLOW}/{oecd_key(areas)}",
                      params={"startPeriod": start, "format": "csvfile"})
    return resp.status_code, resp.text if resp.status_code == 200 else ""


def values(text: str) -> dict[tuple[str, str, str], float]:
    """(IMF country code, our measure, period) -> USD bn, BPM6 sign."""
    back = {v: k for k, v in AREA.items()}
    measure = {v: k for k, v in MEASURES.items()}
    out: dict[tuple[str, str, str], float] = {}
    for r in csv.DictReader(io.StringIO(text)):
        if r.get("ACCOUNTING_ENTRY") != "N" or r.get("UNIT_MEASURE") != "USD_EXC":
            continue
        if r.get("ADJUSTMENT", "N") != "N" or r.get("MEASURE") not in measure:
            continue
        v = (r.get("OBS_VALUE") or "").strip()
        if not v:
            continue
        mult = int(r.get("UNIT_MULT") or 6)
        out[(back.get(r["REF_AREA"], r["REF_AREA"]), measure[r["MEASURE"]], r["TIME_PERIOD"])] = (
            float(v) * 10 ** (mult - 9)
        )
    return out
