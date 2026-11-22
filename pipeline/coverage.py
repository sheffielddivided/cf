"""Phase 0 coverage matrix: which countries and series exist, from when, with which gaps."""

from __future__ import annotations

import csv
import gzip
import json
import logging
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .sdmx import SdmxClient
from .sources import imf

log = logging.getLogger(__name__)

# Columns shown in the coverage matrix, in order.
MATRIX_COLUMNS: list[tuple[str, str, str]] = [
    ("fa_ex_reserves", "net", "FA ekskl. res."),
    ("fa_total", "net", "FA totalt"),
    ("fdi", "net", "FDI"),
    ("portfolio", "net", "Portefølje"),
    ("other_inv", "net", "Annen inv."),
    ("derivatives", "net", "Derivater"),
    ("reserves", "net", "Reserver"),
    ("portfolio", "liabilities", "Port. gjeld (L)"),
    ("current_account", "net", "Driftsbalanse"),
    ("errors_omissions", "net", "Feil/utel."),
]

QUARTER_RE = re.compile(r"^(\d{4})-Q([1-4])$")
COUNTRY_RE = re.compile(r"^[A-Z]{3}$")
NON_COUNTRY_CODES = {"EUR", "WLD"}  # WEO three-letter aggregates


def q_index(period: str) -> int:
    m = QUARTER_RE.match(period)
    if not m:
        raise ValueError(f"not a quarter: {period!r}")
    return int(m.group(1)) * 4 + int(m.group(2)) - 1


def q_label(index: int) -> str:
    return f"{index // 4}-Q{index % 4 + 1}"


@dataclass
class SeriesCoverage:
    first: str | None
    last: str | None
    count: int
    gaps: int

    @classmethod
    def from_periods(cls, periods: Iterable[str]) -> SeriesCoverage:
        idx = sorted({q_index(p) for p in periods})
        if not idx:
            return cls(None, None, 0, 0)
        return cls(q_label(idx[0]), q_label(idx[-1]), len(idx), idx[-1] - idx[0] + 1 - len(idx))


def last_common_quarter(
    latest: dict[str, str | None], share: float = 0.8
) -> tuple[str | None, list[str]]:
    """Newest quarter that at least `share` of the countries have reached.

    Returns the quarter and the countries that have NOT reached it.
    """
    have = sorted((q_index(v) for v in latest.values() if v), reverse=True)
    need = int(-(-share * len(latest) // 1))  # ceil
    if len(have) < need or need == 0:
        return None, sorted(latest)
    q = have[need - 1]
    behind = sorted(c for c, v in latest.items() if not v or q_index(v) < q)
    return q_label(q), behind


def top_n_by_gdp(
    gdp: dict[tuple[str, int], float], year: int, n: int = 20
) -> list[tuple[str, float]]:
    rows = [
        (c, v) for (c, y), v in gdp.items()
        if y == year and COUNTRY_RE.match(c) and c not in NON_COUNTRY_CODES
    ]
    return sorted(rows, key=lambda r: r[1], reverse=True)[:n]


# ------------------------------------------------------------------------------ run


def run(out: Path, series_map_path: Path, countries_path: Path, reference_year: int) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    smap = imf.load_series_map(series_map_path)
    cfg = yaml.safe_load(countries_path.read_text())
    names = {c["iso3"]: c["name_nb"] for c in cfg["countries"]}
    retrieved_at = datetime.now(UTC).isoformat(timespec="seconds")
    log_rows: list[dict[str, Any]] = []

    with SdmxClient(imf.IMF_V3) as client:
        status, weo_rows = imf.fetch_weo_gdp(client, smap["imf_weo"])
        log_rows.append({"query": "WEO NGDPD", "status": status, "rows": len(weo_rows)})
        gdp = imf.gdp_by_country_year(weo_rows)
        top = top_n_by_gdp(gdp, reference_year)
        top_codes = [c for c, _ in top]
        for c, _ in top:
            names.setdefault(c, c)

        ea = smap.get("country_codes", {}).get("EA", "G163")
        names[ea] = "Euroområdet"
        wanted = list(dict.fromkeys(top_codes + list(names)))

        observations: list[dict[str, Any]] = []
        for country in wanted:
            for freq, start in (("Q", "2010-Q1"), ("A", "2010")):
                status, rows = imf.fetch_bop_rows(
                    client, country, smap["imf_bop"], freq=freq, start=start
                )
                log_rows.append({"query": f"BOP {country} {freq}", "status": status,
                                 "rows": len(rows)})
                observations.extend(
                    imf.bop_observations(rows, smap["imf_bop"], country=country,
                                         retrieved_at=retrieved_at)
                )
                log.info("BOP %s %s: HTTP %s, %d rows", country, freq, status, len(rows))

    # ---------------------------------------------------------------- coverage
    q_periods: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    a_periods: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for o in observations:
        if o["value_raw"] is None:
            continue
        key = (o["country"], o["measure"], o["side"])
        (q_periods if o["freq"] == "Q" else a_periods)[key].append(o["period"])

    cov = {k: SeriesCoverage.from_periods(v) for k, v in q_periods.items()}
    empty = SeriesCoverage(None, None, 0, 0)
    main_latest = {c: cov.get((c, "fa_ex_reserves", "net"), empty).last for c in top_codes}
    common, behind = last_common_quarter(main_latest)

    # ---------------------------------------------------------------- write files
    with gzip.open(out / "observations.csv.gz", "wt", newline="") as fh:
        if observations:
            w = csv.DictWriter(fh, fieldnames=list(observations[0]))
            w.writeheader()
            w.writerows(observations)
    with (out / "coverage.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["country", "measure", "side", "first_q", "last_q", "n_q", "gaps_q",
                    "last_a"])
        keys = sorted(set(cov) | set(a_periods))
        for k in keys:
            c = cov.get(k) or SeriesCoverage(None, None, 0, 0)
            last_a = max(a_periods[k]) if a_periods.get(k) else ""
            w.writerow([*k, c.first or "", c.last or "", c.count, c.gaps, last_a])
    with (out / "gdp_ranking.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "country", f"gdp_usd_bn_{reference_year}"])
        for i, (c, v) in enumerate(top_n_by_gdp(gdp, reference_year, 30), start=1):
            w.writerow([i, c, round(v, 1)])
    (out / "fetch_log.json").write_text(json.dumps(log_rows, indent=1))

    md = render_markdown(
        cov=cov, a_periods=a_periods, top=top, names=names, wanted=wanted,
        common=common, behind=behind, reference_year=reference_year, retrieved_at=retrieved_at,
        extra=[c for c in wanted if c not in top_codes],
    )
    path = out / "COVERAGE.md"
    path.write_text(md)
    return path


def render_markdown(
    *, cov, a_periods, top, names, wanted, common, behind, reference_year, retrieved_at, extra
) -> str:
    def cell(country: str, measure: str, side: str) -> str:
        c = cov.get((country, measure, side))
        if c and c.last:
            gap = f" ({c.gaps} hull)" if c.gaps else ""
            return f"{c.first}–{c.last}{gap}"
        if a_periods.get((country, measure, side)):
            return f"kun år, til {max(a_periods[(country, measure, side)])}"
        return "—"

    lines = [
        "# Dekningsmatrise (fase 0)",
        "",
        f"Generert {retrieved_at} fra IMF BOP (SDMX 3.0) og IMF WEO. Kvartalsdata fra 2010-K1.",
        "Cellene viser første–siste kvartal med verdi, og antall manglende kvartaler i mellom.",
        "«—» betyr ikke rapportert.",
        "",
        f"## Topp 20 etter BNP i {reference_year} (IMF WEO, NGDPD)",
        "",
        "| # | Land | BNP mrd. USD |",
        "| --- | --- | --- |",
    ]
    for i, (c, v) in enumerate(top, start=1):
        lines.append(f"| {i} | {names.get(c, c)} (`{c}`) | {v:,.0f} |".replace(",", " "))
    lines += [
        "",
        "## Siste felles kvartal",
        "",
        f"Hovedmålet (FA ekskl. reserver) for topp 20: **{common or 'ikke bestemt'}** "
        "(nyeste kvartal minst 80 % av landene har).",
        "",
        "Ligger bak: " + (", ".join(f"{names.get(c, c)}" for c in behind) or "ingen") + ".",
        "",
        "## Matrise",
        "",
        "| Land | " + " | ".join(h for _, _, h in MATRIX_COLUMNS) + " |",
        "| --- | " + " | ".join("---" for _ in MATRIX_COLUMNS) + " |",
    ]
    for c in wanted:
        tag = "" if c not in extra else " *"
        row = [f"{names.get(c, c)} (`{c}`){tag}"]
        row += [cell(c, m, s) for m, s, _ in MATRIX_COLUMNS]
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "\\* utenfor topp 20 (kandidat, ekstraland eller aggregat).", ""]
    return "\n".join(lines)
