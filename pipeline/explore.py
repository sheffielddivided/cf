"""Phase 0: explore the IMF and OECD SDMX APIs and save everything we get back.

The goal is evidence, not data: which endpoints answer, in which formats, what the
BOP data structure looks like, and which codes exist. Every response is saved gzip'ed
with a manifest, so the findings can be inspected offline and reviewed in git.
Nothing here is used by the production pipeline.
"""

from __future__ import annotations

import csv
import gzip
import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

from .sdmx import (
    COUNTRY_DIM_HINTS,
    DATA_CSV_V1,
    DATA_CSV_V2,
    DATA_JSON_V2,
    FREQ_DIM_IDS,
    STRUCTURE_JSON_V1,
    STRUCTURE_JSON_V2,
    SdmxClient,
    Structure,
    build_key,
    localized_name,
    parse_structure,
)

log = logging.getLogger(__name__)

IMF_V3 = "https://api.imf.org/external/sdmx/3.0"
IMF_V21 = "https://api.imf.org/external/sdmx/2.1"
OECD = "https://sdmx.oecd.org/public/rest"

SAMPLE_START = "2023-Q1"


@dataclass
class FetchRecord:
    name: str
    url: str
    accept: str | None
    status: int | None = None
    content_type: str | None = None
    bytes: int = 0
    file: str | None = None
    error: str | None = None
    seconds: float = 0.0


def _ext(content_type: str | None) -> str:
    ct = (content_type or "").lower()
    if "json" in ct:
        return "json"
    if "xml" in ct:
        return "xml"
    if "csv" in ct:
        return "csv"
    if "html" in ct:
        return "html"
    return "txt"


class Recorder:
    def __init__(self, out: Path) -> None:
        self.out = out
        self.raw = out / "raw"
        self.raw.mkdir(parents=True, exist_ok=True)
        self.records: list[FetchRecord] = []

    def fetch(
        self,
        client: SdmxClient,
        name: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        accept: str | None = None,
    ) -> httpx.Response | None:
        url = str(httpx.URL(client.url(path), params=params))
        rec = FetchRecord(name=name, url=url, accept=accept)
        t0 = time.monotonic()
        try:
            resp = client.get(path, params=params, accept=accept)
        except Exception as exc:  # noqa: BLE001 - we want every failure in the manifest
            rec.error = f"{type(exc).__name__}: {exc}"
            rec.seconds = round(time.monotonic() - t0, 2)
            self.records.append(rec)
            log.error("%-32s FAILED %s", name, rec.error)
            return None
        rec.seconds = round(time.monotonic() - t0, 2)
        rec.status = resp.status_code
        rec.content_type = resp.headers.get("content-type")
        rec.bytes = len(resp.content)
        fname = f"{name}.{_ext(rec.content_type)}.gz"
        (self.raw / fname).write_bytes(gzip.compress(resp.content))
        rec.file = f"raw/{fname}"
        self.records.append(rec)
        log.info("%-32s %s %8d B  %s", name, rec.status, rec.bytes, rec.content_type)
        return resp

    def first_json(self, attempts: list[tuple[SdmxClient, str, str, dict | None, str]]) -> Any:
        """Try several (client, name, path, params, accept) until one returns JSON."""
        for client, name, path, params, accept in attempts:
            resp = self.fetch(client, name, path, params=params, accept=accept)
            if resp is None or resp.status_code != 200:
                continue
            try:
                return resp.json()
            except ValueError:
                log.warning("%s: 200 but not JSON (%s)", name, resp.headers.get("content-type"))
        return None

    def write_manifest(self) -> None:
        (self.out / "manifest.json").write_text(
            json.dumps([asdict(r) for r in self.records], indent=2, ensure_ascii=False)
        )


# ----------------------------------------------------------------------------- helpers


def write_dataflows(doc: Any, path: Path) -> list[dict[str, str]]:
    s = parse_structure(doc)
    rows = [
        {
            "agency": f.get("agencyID", ""),
            "id": f.get("id", ""),
            "version": str(f.get("version", "")),
            "name": localized_name(f),
        }
        for f in s.dataflows
    ]
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["agency", "id", "version", "name"], delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    return rows


def write_structure_summary(s: Structure, out: Path, prefix: str) -> None:
    """One markdown overview + one TSV of codes per dimension."""
    lines = [
        f"# {prefix}: struktur",
        "",
        "| Pos | Dimensjon | Kodeliste | Antall koder |",
        "| --- | --- | --- | --- |",
    ]
    for d in s.dimensions:
        codes = s.codes(d)
        lines.append(f"| {d.position} | `{d.id}` | `{d.codelist}` | {len(codes)} |")
        with (out / f"{prefix}_codes_{d.id}.tsv").open("w", newline="") as fh:
            w = csv.writer(fh, delimiter="\t")
            w.writerow(["code", "name"])
            w.writerows(sorted(codes.items()))
    lines += ["", "Attributter: " + ", ".join(f"`{a}`" for a in s.attributes)]
    (out / f"{prefix}_structure.md").write_text("\n".join(lines) + "\n")


def sample_values(s: Structure, country: str = "USA", freq: str = "Q") -> dict[str, str]:
    """Pick dimension values for a sample query: one country, one frequency."""
    values: dict[str, str] = {}
    cdim = s.find_dimension(*COUNTRY_DIM_HINTS)
    if cdim:
        codes = s.codes(cdim)
        for candidate in (country, country[:2], "US"):
            if not codes or candidate in codes:
                values[cdim.id] = candidate
                break
    fdim = s.find_dimension(*FREQ_DIM_IDS)
    if fdim:
        values[fdim.id] = freq
    return values


# ---------------------------------------------------------------------------- explore


def explore_imf(rec: Recorder) -> None:
    with SdmxClient(IMF_V3) as c3, SdmxClient(IMF_V21) as c21:
        flows_doc = rec.first_json(
            [
                (c3, "imf3_dataflows", "structure/dataflow/*/*/+", None, STRUCTURE_JSON_V2),
                (c3, "imf3_dataflows_all", "structure/dataflow", None, STRUCTURE_JSON_V2),
                (c21, "imf21_dataflows", "dataflow/all/all/latest", None, STRUCTURE_JSON_V1),
            ]
        )
        flows: list[dict[str, str]] = []
        if flows_doc is not None:
            flows = write_dataflows(flows_doc, rec.out / "imf_dataflows.tsv")
            log.info("IMF dataflows: %d", len(flows))

        bop_doc = rec.first_json(
            [
                (c3, "imf3_bop_structure", "structure/dataflow/IMF.STA/BOP/+",
                 {"references": "all"}, STRUCTURE_JSON_V2),
                (c3, "imf3_bop_dsd", "structure/datastructure/IMF.STA/DSD_BOP/+",
                 {"references": "children"}, STRUCTURE_JSON_V2),
                (c21, "imf21_bop_structure", "dataflow/IMF.STA/BOP/latest",
                 {"references": "all"}, STRUCTURE_JSON_V1),
            ]
        )
        if bop_doc is None:
            log.error("IMF BOP structure: no JSON response")
        else:
            s = parse_structure(bop_doc)
            write_structure_summary(s, rec.out, "imf_bop")
            vals = sample_values(s)
            log.info("IMF BOP dims: %s; sample %s", [d.id for d in s.dimensions], vals)
            key3 = build_key(s.dimensions, vals, "*")
            key21 = build_key(s.dimensions, vals, "")
            rec.fetch(c3, "imf3_bop_usa_q_csv", f"data/dataflow/IMF.STA/BOP/+/{key3}",
                      params={"c[TIME_PERIOD]": f"ge:{SAMPLE_START}"}, accept=DATA_CSV_V2)
            rec.fetch(c3, "imf3_bop_usa_q_json", f"data/dataflow/IMF.STA/BOP/+/{key3}",
                      params={"c[TIME_PERIOD]": f"ge:{SAMPLE_START}", "attributes": "all"},
                      accept=DATA_JSON_V2)
            rec.fetch(c21, "imf21_bop_usa_q_csv", f"data/IMF.STA,BOP/{key21}",
                      params={"startPeriod": SAMPLE_START}, accept=DATA_CSV_V1)

        # GDP candidates (WEO for annual USD GDP, national accounts for quarterly)
        wanted = [f for f in flows if f["id"] in {"WEO", "QNEA", "ANEA", "NEA"}]
        for f in wanted[:4]:
            agency, fid = f["agency"], f["id"]
            doc = rec.first_json(
                [(c3, f"imf3_{fid.lower()}_structure", f"structure/dataflow/{agency}/{fid}/+",
                  {"references": "all"}, STRUCTURE_JSON_V2)]
            )
            if doc is None:
                continue
            s = parse_structure(doc)
            write_structure_summary(s, rec.out, f"imf_{fid.lower()}")
            freq = "A" if fid in {"WEO", "ANEA"} else "Q"
            vals = sample_values(s, freq=freq)
            key3 = build_key(s.dimensions, vals, "*")
            rec.fetch(c3, f"imf3_{fid.lower()}_usa_csv", f"data/dataflow/{agency}/{fid}/+/{key3}",
                      params={"c[TIME_PERIOD]": "ge:2022"}, accept=DATA_CSV_V2)


def explore_oecd(rec: Recorder) -> None:
    flow_id = "DSD_BOP@DF_BOP"
    with SdmxClient(OECD) as co:
        flows_doc = rec.first_json(
            [(co, "oecd_dataflows", "dataflow/all", None, STRUCTURE_JSON_V1)]
        )
        agency = "OECD.SDD.TPS"
        if flows_doc is not None:
            rows = write_dataflows(flows_doc, rec.out / "oecd_dataflows.tsv")
            agency = next((r["agency"] for r in rows if r["id"] == flow_id), agency)
        doc = rec.first_json(
            [(co, "oecd_bop_structure", f"dataflow/{agency}/{flow_id}/latest",
              {"references": "all"}, STRUCTURE_JSON_V1)]
        )
        if doc is None:
            log.error("OECD BOP structure: no JSON response")
            return
        s = parse_structure(doc)
        write_structure_summary(s, rec.out, "oecd_bop")
        vals = sample_values(s)
        key = build_key(s.dimensions, vals, "")
        rec.fetch(co, "oecd_bop_usa_q_csv", f"data/{agency},{flow_id},/{key}",
                  params={"startPeriod": SAMPLE_START, "dimensionAtObservation": "AllDimensions",
                          "format": "csvfilewithlabels"})


def explore(out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    rec = Recorder(out)
    for step in (explore_imf, explore_oecd):
        try:
            step(rec)
        except Exception:  # noqa: BLE001 - keep going, record in log
            log.exception("%s crashed", step.__name__)
    rec.write_manifest()
    return out / "manifest.json"
