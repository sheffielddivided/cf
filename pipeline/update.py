"""`pipeline update`: fetch, normalise, check and export (docs/DESIGN.md, fase 1).

Exit codes: 0 = ok (data may or may not have changed), 1 = a check failed (nothing written),
2 = a source failed (nothing written). A run summary is always written to run/.
"""

from __future__ import annotations

import gzip
import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import yaml

from . import checks, episodes, phase2, phase3
from . import summary as quarterly
from .coverage import last_common_quarter
from .export import export_all
from .model import derive_main, frame, latest_period, reference_year, window
from .sdmx import SdmxClient
from .selection import Selection
from .sources import imf
from .sources import positions as pos

log = logging.getLogger(__name__)


class SourceError(RuntimeError):
    pass


def _read_json(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")


def _gz(text: str) -> bytes:
    return gzip.compress(text.encode("utf-8"), mtime=0)


def run(root: Path = Path("."), today: date | None = None, transport=None) -> int:
    today = today or datetime.now(UTC).date()
    smap = imf.load_series_map(root / "config/series_map.yaml")
    cfg = yaml.safe_load((root / "config/countries.yaml").read_text())
    names = {c["iso3"]: c for c in cfg["countries"]}
    aggregates = [smap["country_codes"][a] for a in cfg.get("aggregates", [])]
    for code in aggregates:
        names.setdefault(code, {"name_nb": "Euroområdet", "name_en": "Euro area",
                                "aggregate": True})
    extras = list(cfg.get("extra", []))
    processed = root / "data/processed"
    run_dir = root / "run"
    run_dir.mkdir(exist_ok=True)

    warnings: list[str] = []
    raw: dict[str, str] = {}
    rows: dict[str, list[dict[str, str]]] = {}
    retrieved_at = datetime.now(UTC).isoformat(timespec="seconds")

    def summary(status: str, **extra) -> None:
        (run_dir / "summary.json").write_text(json.dumps(
            {"status": status, "warnings": warnings, **extra}, indent=1, ensure_ascii=False))

    try:
        with SdmxClient(imf.IMF_V3, transport=transport) as client:
            status, text = imf.fetch_weo_csv(client, smap["imf_weo"])
            if status != 200:
                raise SourceError(f"IMF WEO NGDPD: HTTP {status}")
            raw["imf_weo_ngdpd.csv.gz"] = text
            gdp = imf.gdp_by_country_year(imf.parse_csv(text))

            def fetch(countries: list[str]) -> None:
                for c in countries:
                    if c in rows:
                        continue
                    st, txt = imf.fetch_bop_csv(client, c, smap["imf_bop"])
                    if st not in (200, 404):
                        raise SourceError(f"IMF BOP {c}: HTTP {st}")
                    log.info("BOP %s: HTTP %s", c, st)
                    raw[f"imf_bop_{c}.csv.gz"] = txt
                    rows[c] = imf.parse_csv(txt) if st == 200 else []

            def build() -> pd.DataFrame:
                recs = []
                for c, rs in rows.items():
                    recs += imf.bop_observations(rs, smap["imf_bop"], country=c,
                                                 retrieved_at=retrieved_at)
                return derive_main(frame(recs))

            prev = Selection.load(processed / "selection.json")
            sel = prev or Selection.compute(gdp, today.year - 1)
            fetch(sel.countries + extras + aggregates)
            df = build()
            latest = {c: latest_period(df, c) for c in sel.countries}
            last_common, _ = last_common_quarter(latest)
            if last_common is None:
                raise SourceError("fant ikke siste felles kvartal (for lite data)")
            ref = reference_year(last_common)
            selection_changed = prev is None or ref != prev.reference_year
            if selection_changed:
                new = Selection.compute(gdp, ref)
                if prev and new.countries != prev.countries:
                    added = sorted(set(new.countries) - set(prev.countries))
                    dropped = sorted(set(prev.countries) - set(new.countries))
                    warnings.append(f"utvalg: nytt referanseår {ref}; inn {added}, ut {dropped}")
                sel = new
                fetch(sel.countries)
                df = build()
                latest = {c: latest_period(df, c) for c in sel.countries}
                last_common, _ = last_common_quarter(latest)
    except SourceError as exc:
        log.error("%s", exc)
        summary("source_error", error=str(exc))
        return 2

    countries = list(dict.fromkeys(sel.countries + extras + aggregates))
    for c in countries:
        if c not in names:
            warnings.append(f"navn: {c} mangler i config/countries.yaml")
    all_latest = {c: latest_period(df, c) for c in countries}

    # ------------------------------------------------------------------ checks
    measures = set(smap["imf_bop"]["measures"])
    hard = checks.CheckResult()
    hard.extend(checks.check_schema(df, measures))
    hard.extend(checks.check_sign(df))
    if hard.errors:
        warnings.extend(hard.errors)
        summary("check_error", errors=hard.errors)
        return 1
    recent = set(window(last_common, 8))
    soft = checks.CheckResult()
    soft.extend(checks.check_identity(df, recent))
    soft.extend(checks.check_mirror(df, recent))
    soft.extend(checks.check_outliers(df, set(window(last_common, 4))))
    soft.extend(checks.check_freshness({c: all_latest[c] for c in sel.countries}, today))
    warnings.extend(soft.warnings)

    # ------------------------------------------------------------------ revisions
    pq = processed / "observations.parquet"
    old = pd.read_parquet(pq) if pq.exists() else None
    stats, big = checks.compare_revisions(old, df)
    if big:
        warnings.append(f"revisjon: {len(big)} store revisjoner (> 10 %), se REVISIONS.md")
    data_changed = old is None or any(stats.values()) or selection_changed

    # ------------------------------------------------------------------ phase 2 (never fatal)
    site = root / "site/public/data"
    # Aggregates are left out: IMF's and OECD's euro area differ systematically (composition
    # and compilation), so a difference there says nothing about revisions.
    cross = phase2.crosscheck(df, [c for c in countries if c not in aggregates], last_common,
                              warnings, transport=transport)
    if cross is not None:
        cross["excluded"] = [{"country": c, "reason": "aggregate"} for c in aggregates]
    prev_nowcast = _read_json(site / "nowcast.json")
    now = phase2.nowcast_data(prev_nowcast, warnings, transport=transport)

    # ------------------------------------------------------------------ phase 3 (never fatal)
    try:
        eps = episodes.compute(df, countries, last_common)
    except Exception as e:  # noqa: BLE001 - phase 3 must never stop the pipeline
        warnings.append(f"episoder: beregning feilet ({e})")
        eps = None
    plain = [c for c in countries if c not in aggregates]
    held = phase3.holdings(plain, {c: names[c].get("iso2") or pos.iso2(c) for c in plain}, warnings,
                           transport=transport)
    summary_md = (
        f"{stats['new']} nye observasjoner, {stats['revised']} reviderte, "
        f"{stats['removed']} fjernet. Siste felles kvartal {last_common}, "
        f"referanseår {sel.reference_year}."
    )
    (run_dir / "commit_message.txt").write_text(
        f"data: weekly update ({last_common})\n\n{summary_md}\n"
        + ("".join(f"- {b}\n" for b in big[:20]))
    )
    summary("ok", changed=data_changed, stats=stats, last_common_quarter=last_common,
            reference_year=sel.reference_year, big_revisions=big)
    log.info("%s", summary_md)

    # Site files are always re-exported (deterministic: git sees no change when nothing
    # changed). The "updated" date only moves when IMF data changed.
    prev_meta = _read_json(site / "meta.json") or {}
    updated = today.isoformat() if data_changed else prev_meta.get("data_updated_at",
                                                                     today.isoformat())
    if cross is not None:
        _write_json(site / "crosscheck.json", cross)
    if eps is not None:
        _write_json(site / "episodes.json", eps)
    if held is not None:
        _write_json(site / "holdings.json", held)
    _write_json(site / "nowcast.json", now)
    revisions = _read_json(site / "revisions.json")
    if data_changed or revisions is None:
        entry = {"date": today.isoformat(), "last_common_quarter": last_common, **stats}
        history = [entry] + [h for h in (revisions or {}).get("history", [])
                             if h.get("date") != entry["date"]]
        _write_json(site / "revisions.json", {
            "latest": {**entry, "changes": checks.revision_details(old, df)},
            "history": history[:52],
        })
    export_all(
        site, df, gdp=gdp, countries=countries, names=names,
        top=sel.countries, last_common=last_common, ref_year=sel.reference_year,
        latest=all_latest, data_updated_at=updated, warnings=sorted(warnings),
    )
    # Quarterly summary drafts (opened as a PR by the workflow when a new quarter arrives)
    try:
        for lang in ("nb", "en"):
            (run_dir / f"summary_{lang}.md").write_text(
                quarterly.draft(site, lang, today.isoformat()))
    except Exception as e:  # noqa: BLE001
        warnings.append(f"oppsummering: utkast feilet ({e})")
    if prev_meta.get("last_common_quarter") and prev_meta["last_common_quarter"] != last_common:
        (run_dir / "new_quarter.txt").write_text(last_common + "\n")

    if not data_changed:
        log.info("no IMF data changes; raw/processed files not rewritten")
        return 0

    # ------------------------------------------------------------------ write
    raw_dir = root / "data/raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, text in raw.items():
        (raw_dir / name).write_bytes(_gz(text))
    processed.mkdir(parents=True, exist_ok=True)
    df.to_parquet(pq, index=False)
    sel.save(processed / "selection.json")
    if big:
        rev = root / "REVISIONS.md"
        head = rev.read_text() if rev.exists() else "# Store revisjoner\n\n"
        rev.write_text(head + f"## {today.isoformat()}\n\n" + "".join(f"- {b}\n" for b in big)
                       + "\n")
    log.info("wrote data for %d countries, latest common quarter %s", len(countries),
             last_common)
    return 0
