# ruff: noqa: E501  (prose templates)
"""Phase 3: data-driven quarterly summary (draft). Generated from the exported site files,
descriptive only (no interpretation, no "capital flight"), reviewed by a human in a PR."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .coverage import q_index, q_label

MAIN = "fa_ex_reserves"

T = {
    "nb": {
        "title": "Kapitalstrømmer: oppsummering for {q}",
        "draft": "_Laget automatisk {date} fra IMF-data og gjennomgått av et menneske før publisering._",
        "lead_in": "Siste fire kvartaler ({w}) hadde {top} størst netto innstrømning, {v} ({p} av BNP).",
        "lead_out": "{bot} hadde størst netto utstrømning, {v} ({p} av BNP).",
        "h_in": "Størst netto innstrømning, siste fire kvartaler",
        "h_out": "Størst netto utstrømning, siste fire kvartaler",
        "h_change": "Størst endring fra forrige firekvartalsperiode",
        "change_intro": "Endring i netto kapitalstrøm ekskl. reserver sammenlignet med de fire kvartalene som sluttet ett kvartal tidligere.",
        "h_ep": "Uvanlige bevegelser",
        "ep_none": "Ingen land er i en episode med uvanlige brutto kapitalstrømmer i {q}.",
        "ep_intro": "Episoder etter Forbes og Warnock (2012): endringen i brutto strømmer over fire kvartaler er mer enn to standardavvik fra snittet de siste fem årene.",
        "h_quality": "Datakvalitet",
        "missing": "Ikke rapportert for perioden: {c}.",
        "cross": "Kryssjekk mot OECD: {n} avvik over 5 %.",
        "rev": "Ved siste oppdatering: {new} nye, {rev} reviderte og {rem} fjernede observasjoner.",
        "col": ("Land", "Mrd. USD", "% av BNP"), "col_change": ("Land", "Før", "Nå", "Endring"),
        "src": "Kilde: International Monetary Fund, Balance of Payments (BOP). Beregninger: cf.",
        "ep": {"inflow_surge": "kraftig økning i innstrømning", "inflow_stop": "brå stopp i innstrømning",
               "outflow_surge": "kraftig økning i utstrømning",
               "outflow_retrenchment": "brå nedgang i utstrømning"},
        "since": "siden",
    },
    "en": {
        "title": "Capital flows: summary for {q}",
        "draft": "_Generated automatically on {date} from IMF data and reviewed by a human before publication._",
        "lead_in": "Over the last four quarters ({w}), {top} had the largest net inflow, {v} ({p} of GDP).",
        "lead_out": "{bot} had the largest net outflow, {v} ({p} of GDP).",
        "h_in": "Largest net inflow, last four quarters",
        "h_out": "Largest net outflow, last four quarters",
        "h_change": "Largest change from the previous four-quarter period",
        "change_intro": "Change in net capital flow excl. reserves compared with the four quarters ending one quarter earlier.",
        "h_ep": "Unusual movements",
        "ep_none": "No country is in an episode of unusual gross capital flows in {q}.",
        "ep_intro": "Episodes after Forbes and Warnock (2012): the four-quarter change in gross flows is more than two standard deviations from its five-year mean.",
        "h_quality": "Data quality",
        "missing": "Not reported for the period: {c}.",
        "cross": "Cross-check against the OECD: {n} differences above 5%.",
        "rev": "In the latest update: {new} new, {rev} revised and {rem} removed observations.",
        "col": ("Country", "USD bn", "% of GDP"), "col_change": ("Country", "Before", "Now", "Change"),
        "src": "Source: International Monetary Fund, Balance of Payments (BOP). Calculations: cf.",
        "ep": {"inflow_surge": "inflow surge", "inflow_stop": "inflow stop",
               "outflow_surge": "outflow surge", "outflow_retrenchment": "outflow retrenchment"},
        "since": "since",
    },
}


def _q(p: str, lang: str) -> str:
    y, q = p.split("-Q")
    return f"{q}. kvartal {y}" if lang == "nb" else f"Q{q} {y}"


def _n(v: float | None, lang: str, digits: int = 1, sign: bool = True) -> str:
    if v is None:
        return "–"
    s = f"{v:+,.{digits}f}" if sign else f"{v:,.{digits}f}"
    if lang == "nb":
        s = s.replace(",", " ").replace(".", ",").replace("-", "−")
    return s


def _usd(v: float, lang: str) -> str:
    return f"{_n(v, lang)} mrd. USD" if lang == "nb" else f"USD {_n(v, lang)} bn"


def _pct(v: float | None, lang: str) -> str:
    return f"{_n(v, lang)} %" if lang == "nb" else f"{_n(v, lang)}%"


def _load(site: Path, name: str) -> Any:
    p = site / name
    return json.loads(p.read_text()) if p.exists() else None


def draft(site: Path, lang: str, today: str) -> str:
    t = T[lang]
    meta, ranking = _load(site, "meta.json"), _load(site, "ranking.json")
    episodes, cross, rev = _load(site, "episodes.json"), _load(site, "crosscheck.json"), _load(site, "revisions.json")
    names = {c["iso3"]: c[f"name_{lang}"] for c in meta["countries"]}
    q = ranking["last_common_quarter"]
    w = ranking["windows"]["4q"]
    window = f"{_q(w[0], lang)} – {_q(w[-1], lang)}"

    rows = [r for r in ranking["rows"] if r["in_top20"]]
    vals = [(r["country"], r["values"][MAIN]["4q"]["usd"], r["values"][MAIN]["4q"]["pct"]) for r in rows]
    present = sorted([v for v in vals if v[1] is not None], key=lambda v: -v[1])
    missing = [names.get(c, c) for c, v, _ in vals if v is None]
    top, bot = present[0], present[-1]

    out = [f"# {t['title'].format(q=_q(q, lang))}", "", t["draft"].format(date=today), "",
           t["lead_in"].format(w=window, top=names[top[0]], v=_usd(top[1], lang), p=_pct(top[2], lang))
           + " " + t["lead_out"].format(bot=names[bot[0]], v=_usd(bot[1], lang), p=_pct(bot[2], lang)), ""]

    def table(title: str, items: list[tuple[str, float, float | None]]) -> None:
        a, b, c = t["col"]
        out.extend([f"## {title}", "", f"| {a} | {b} | {c} |", "| --- | ---: | ---: |"])
        out.extend(f"| {names[k]} | {_n(v, lang)} | {_n(p, lang)} |" for k, v, p in items)
        out.append("")

    table(t["h_in"], [v for v in present if v[1] > 0][:5])
    table(t["h_out"], list(reversed([v for v in present if v[1] < 0]))[:5])

    # change vs the four quarters ending one quarter earlier (from the country files)
    prev = [q_label(q_index(p) - 1) for p in w]
    changes = []
    for c, now, _ in present:
        f = site / "country" / f"{c}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        series = dict(zip(d["periods"], d["series"].get(MAIN, {}).get("net", []), strict=False))
        if all(series.get(p) is not None for p in prev):
            before = sum(series[p] for p in prev)
            changes.append((c, before, now, now - before))
    changes = [x for x in changes if abs(x[3]) >= 0.05]
    changes.sort(key=lambda x: -abs(x[3]))
    if changes:
        a, b, c2, dlt = t["col_change"]
        out.extend([f"## {t['h_change']}", "", t["change_intro"], "",
                    f"| {a} | {b} | {c2} | {dlt} |", "| --- | ---: | ---: | ---: |"])
        out.extend(f"| {names[k]} | {_n(b4, lang)} | {_n(n, lang)} | {_n(ch, lang)} |"
                   for k, b4, n, ch in changes[:5])
        out.append("")

    out.extend([f"## {t['h_ep']}", ""])
    active = (episodes or {}).get("active", [])
    if active:
        out.extend([t["ep_intro"], ""])
        out.extend(f"- {names.get(e['country'], e['country'])}: {t['ep'][e['type']]} "
                   f"({t['since']} {_q(e['start'], lang)})" for e in active)
    else:
        out.append(t["ep_none"].format(q=_q(q, lang)))
    out.append("")

    out.extend([f"## {t['h_quality']}", ""])
    if missing:
        out.append(f"- {t['missing'].format(c=', '.join(missing))}")
    if cross:
        out.append(f"- {t['cross'].format(n=len(cross.get('flagged', [])))}")
    if rev:
        lt = rev["latest"]
        out.append(f"- {t['rev'].format(new=lt['new'], rev=lt['revised'], rem=lt['removed'])}")
    out.extend(["", t["src"], ""])
    return "\n".join(out)
