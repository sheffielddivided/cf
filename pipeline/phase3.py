"""Phase 3 additions to `pipeline update`: positions ("who owns what") and flow episodes.

Positions (IMF PIP/DIP, BIS) are stocks and are exported separately from all flow data.
Like phase 2, nothing here may stop the main pipeline: failures become warnings and the
previous file is kept.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from .sdmx import SdmxClient
from .sources import positions as pos

log = logging.getLogger(__name__)
TOP = 10


def _top(pairs: dict[str, float], n: int = TOP) -> list[dict[str, Any]]:
    rows = sorted(((k, v) for k, v in pairs.items() if pos.iso2(k)), key=lambda kv: -kv[1])
    return [{"iso3": k, "iso2": pos.iso2(k), "usd_bn": round(v, 1)} for k, v in rows[:n]]


def holdings(
    countries: list[str], iso2_of: dict[str, str], warnings: list[str], transport=None
) -> dict[str, Any] | None:
    """Build holdings.json; None if every source failed."""
    out: dict[str, Any] = {"countries": {c: {} for c in countries}}
    ok = False

    # ---------------------------------------------------------------- portfolio (PIP)
    try:
        with SdmxClient(pos.IMF_V3, transport=transport) as c:
            abroad_text, held_text = pos.fetch_pip(c, countries)
        abroad = pos.pip_values(abroad_text)
        held = pos.pip_values(held_text)
        period = pos.common_period(held) or pos.common_period(abroad)
        for x in countries:
            # latest period in which x reports a world total
            own = sorted(p for (h, i, p) in abroad if h == x and i == "G001")
            p_x = own[-1] if own else None
            entry = out["countries"][x]
            if p_x:
                entry["pip_assets"] = {
                    "period": p_x,
                    "world": round(abroad[(x, "G001", p_x)], 1),
                    "top": _top({i: v for (h, i, p), v in abroad.items() if h == x and p == p_x}),
                }
            if period:
                holders = {
                    h: v for (h, i, p), v in held.items() if i == x and p == period and h != x
                }
                if holders:
                    entry["pip_held_by"] = {
                        "period": period,
                        "reporters_total": round(
                            sum(v for k, v in holders.items() if pos.iso2(k)), 1
                        ),
                        "top": _top(holders),
                    }
        if period:
            matrix = [
                [
                    round(v, 1) if (v := abroad.get((h, i, period))) is not None else None
                    for i in countries
                ]
                for h in countries
            ]
            out["pip_matrix"] = {
                "period": period,
                "holders": countries,
                "issuers": countries,
                "usd_bn": matrix,
            }
        ok = True
    except Exception as exc:  # noqa: BLE001 - positions must never stop the pipeline
        log.warning("PIP failed: %s", exc)
        warnings.append(f"beholdninger: IMF PIP utilgjengelig ({exc})")

    # ---------------------------------------------------------------- direct investment (DIP)
    try:
        with SdmxClient(pos.IMF_V3, transport=transport) as c:
            dip = pos.dip_values(pos.fetch_dip(c, countries))
        years: dict[str, list[str]] = defaultdict(list)
        for rep, _d, cp, y in dip:
            if cp == "G001":
                years[rep].append(y)
        for x in countries:
            if not years.get(x):
                continue
            y = max(years[x])
            for d in ("out", "in"):
                world = dip.get((x, d, "G001", y))
                if world is None:
                    continue
                out["countries"][x][f"dip_{d}"] = {
                    "period": y,
                    "world": round(world, 1),
                    "top": _top(
                        {
                            cp: v
                            for (rep, dd, cp, yy), v in dip.items()
                            if rep == x and dd == d and yy == y
                        }
                    ),
                }
        ok = True
    except Exception as exc:  # noqa: BLE001
        log.warning("DIP failed: %s", exc)
        warnings.append(f"beholdninger: IMF DIP utilgjengelig ({exc})")

    # ---------------------------------------------------------------- banks (BIS LBS)
    try:
        codes = {x: iso2_of[x] for x in countries if iso2_of.get(x)}
        with SdmxClient(pos.BIS_V2, transport=transport) as c:
            bis = pos.bis_values(pos.fetch_bis(c, sorted(set(codes.values()))))
        back = {v: k for k, v in codes.items()}
        series: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
        for (cp, side, q), v in bis.items():
            if cp in back:
                series[back[cp]][side][q] = v
        for x, sides in series.items():
            qs = sorted(set(sides["claims"]) | set(sides["liabilities"]))[-24:]
            out["countries"][x]["bis"] = {
                "periods": qs,
                "claims": [
                    round(sides["claims"][q], 1) if q in sides["claims"] else None for q in qs
                ],
                "liabilities": [
                    round(sides["liabilities"][q], 1) if q in sides["liabilities"] else None
                    for q in qs
                ],
            }
        ok = True
    except Exception as exc:  # noqa: BLE001
        log.warning("BIS failed: %s", exc)
        warnings.append(f"beholdninger: BIS utilgjengelig ({exc})")

    return out if ok else None
