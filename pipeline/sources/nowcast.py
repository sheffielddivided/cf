"""High-frequency indicators for the "nåkast" tab: US TIC (monthly), euro area ECB (monthly),
Japan MOF (weekly). These are partial and preliminary, never mixed into the main ranking.

Every parser returns a dict with three aligned series, all in the source currency (bn):
  nonres   = non-residents' net purchases in the economy        (positive = inflow)
  res      = residents' net purchases abroad                     (positive = outflow)
  net      = net inflow = nonres - res                           (site sign: positive = inflow)
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date

TIC_T1 = "https://treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table1.txt"
TIC_T2 = "https://treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table2.txt"
ECB_BASE = "https://data-api.ecb.europa.eu/service"
ECB_KEY = "M.N.U2.W1.S1.S1.T.A+L+N.FA.D+P+O+F.F+F7._Z+T.EUR._T._X+M+T.N.ALL"
MOF_WEEK = ("https://www.mof.go.jp/policy/international_policy/reference/"
            "itn_transactions_in_securities/week.csv")


def _series(periods: list[str], nonres: dict, res: dict, net: dict | None = None) -> dict:
    periods = sorted(p for p in periods if p in nonres or p in res or (net and p in net))
    n = net or {p: nonres[p] - res[p] for p in periods if p in nonres and p in res}
    r2 = lambda v: None if v is None else round(v, 3)  # noqa: E731
    return {
        "periods": periods,
        "nonres": [r2(nonres.get(p)) for p in periods],
        "res": [r2(res.get(p)) for p in periods],
        "net": [r2(n.get(p)) for p in periods],
    }


# ------------------------------------------------------------------------------ US TIC

def _tic_grand_total(text: str, column: str) -> dict[str, float]:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("country\t"))
    reader = csv.DictReader(io.StringIO("\n".join(lines[start:])), delimiter="\t")
    out = {}
    for r in reader:
        if (r.get("country_code") or "").strip() != "99996":
            continue
        try:
            out[r["date"].strip()] = float((r.get(column) or "").replace(",", "")) / 1000
        except ValueError:  # "n.a." and blanks: not reported, never zero
            continue
    return out


def parse_tic(table1: str, table2: str) -> dict:
    """Table 1: foreigners' net purchases of US long-term securities (inflow).
    Table 2: US residents' net purchases of foreign long-term securities (outflow)."""
    nonres = _tic_grand_total(table1, "for_lt_total_net")
    res = _tic_grand_total(table2, "us_lt_total_net")
    return _series(sorted(set(nonres) | set(res)), nonres, res)


# ------------------------------------------------------------------------------ ECB

def parse_ecb(text: str) -> dict:
    """Euro area monthly BOP: net financial account excl. reserves = D + P + O + F7 (BPM6),
    flipped to inflow sign; gross sides from assets/liabilities of D + P + O."""
    net_bpm6: dict[str, float] = {}
    assets: dict[str, float] = {}
    liab: dict[str, float] = {}
    counts: dict[str, int] = {}
    for r in csv.DictReader(io.StringIO(text)):
        v = (r.get("OBS_VALUE") or "").strip()
        if not v:
            continue
        p, entry = r["TIME_PERIOD"], r["ACCOUNTING_ENTRY"]
        func, instr = r["FUNCTIONAL_CAT"], r["INSTR_ASSET"]
        val = float(v) / 1000  # EUR millions -> bn
        if entry == "N" and ((func in "DPO" and instr == "F") or (func == "F" and instr == "F7")):
            net_bpm6[p] = net_bpm6.get(p, 0.0) + val
            counts[p] = counts.get(p, 0) + 1
        elif entry == "A" and func in "DPO" and instr == "F":
            assets[p] = assets.get(p, 0.0) + val
        elif entry == "L" and func in "DPO" and instr == "F":
            liab[p] = liab.get(p, 0.0) + val
    complete = [p for p, c in counts.items() if c == 4]  # D, P, O and F7 all present
    net = {p: -net_bpm6[p] for p in complete}
    return _series(complete, liab, assets, net)


# ------------------------------------------------------------------------------ Japan MOF

WEEK_RE = re.compile(r"^(\d{4})\D+(\d{1,2})\D+(\d{1,2})\D+?(\d{1,2})\D+(\d{1,2})\s*$")


def _num(s: str) -> float | None:
    s = s.replace(",", "").replace("　", "").strip()
    return float(s) if s not in {"", "-", "…"} else None


def _week_end(label: str) -> str | None:
    """'2026．11．8〜11．14' -> '2026-11-14' (handles year change)."""
    label = label.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    m = WEEK_RE.match(label.strip())
    if not m:
        return None
    y, m1, _d1, m2, d2 = (int(x) for x in m.groups())
    year = y + 1 if m2 < m1 else y
    return date(year, m2, d2).isoformat()


def parse_mof(raw: bytes) -> dict:
    """Weekly ITS: columns 7 (assets: equity + long-term debt, net) and 18 (liabilities: same).
    Net = acquisition - disposition; unit 100 million yen -> bn yen (/10)."""
    text = raw.decode("shift_jis", errors="replace")
    res: dict[str, float] = {}
    nonres: dict[str, float] = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 19:
            continue
        end = _week_end(row[0])
        if not end:
            continue
        a, liab = _num(row[7]), _num(row[18])
        if a is not None:
            res[end] = a / 10
        if liab is not None:
            nonres[end] = liab / 10
    return _series(sorted(set(res) | set(nonres)), nonres, res)
