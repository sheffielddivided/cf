"""A thin SDMX REST client (2.1 and 3.0) plus SDMX-JSON structure parsing.

Deliberately small: the IMF API is new (2025) and we want failures to be easy to see.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx

log = logging.getLogger(__name__)

USER_AGENT = "cf-global-capital-flows/0.1 (+https://github.com/sheffielddivided/cf)"

STRUCTURE_JSON_V2 = "application/vnd.sdmx.structure+json;version=2.0.0"
STRUCTURE_JSON_V1 = "application/vnd.sdmx.structure+json;version=1.0.0"
STRUCTURE_XML_V21 = "application/vnd.sdmx.structure+xml;version=2.1"
DATA_CSV_V2 = "application/vnd.sdmx.data+csv;version=2.0.0"
DATA_CSV_V1 = "application/vnd.sdmx.data+csv;version=1.0.0"
DATA_JSON_V2 = "application/vnd.sdmx.data+json;version=2.0.0"
DATA_JSON_V1 = "application/vnd.sdmx.data+json;version=1.0.0"

RETRY_STATUS = frozenset({429, 500, 502, 503, 504})

COUNTRY_DIM_HINTS = ("COUNTRY", "REF_AREA", "JURISDICTION")
FREQ_DIM_IDS = ("FREQ", "FREQUENCY")


class SdmxClient:
    """GET-only HTTP client with retry/backoff and a descriptive User-Agent."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 120.0,
        max_retries: int = 4,
        backoff: float = 2.0,
        transport: httpx.BaseTransport | None = None,
        sleep=time.sleep,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.backoff = backoff
        self._sleep = sleep
        self._http = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            transport=transport,
        )

    def __enter__(self) -> SdmxClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
        accept: str | None = None,
    ) -> httpx.Response:
        headers = {"Accept": accept} if accept else {}
        attempt = 0
        while True:
            try:
                resp = self._http.get(self.url(path), params=params, headers=headers)
            except httpx.TransportError as exc:
                if attempt >= self.max_retries:
                    raise
                wait = self.backoff * 2**attempt
                log.warning("transport error %s on %s, retry in %.0fs", exc, path, wait)
                self._sleep(wait)
                attempt += 1
                continue
            if resp.status_code in RETRY_STATUS and attempt < self.max_retries:
                wait = _retry_after(resp) or self.backoff * 2**attempt
                log.warning("HTTP %s on %s, retry in %.0fs", resp.status_code, path, wait)
                self._sleep(wait)
                attempt += 1
                continue
            return resp


def _retry_after(resp: httpx.Response) -> float | None:
    value = resp.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return min(float(value), 120.0)
    except ValueError:
        return None


# --------------------------------------------------------------------------- structure


@dataclass
class Dimension:
    id: str
    position: int
    codelist: str | None = None


@dataclass
class Structure:
    dataflows: list[dict[str, Any]] = field(default_factory=list)
    dimensions: list[Dimension] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    codelists: dict[str, dict[str, str]] = field(default_factory=dict)

    def codes(self, dim: Dimension) -> dict[str, str]:
        if not dim.codelist:
            return {}
        return self.codelists.get(dim.codelist) or self.codelists.get(
            dim.codelist.split(":")[-1], {}
        )

    def find_dimension(
        self, *hints: str, exclude: tuple[str, ...] = ("COUNTERPART",)
    ) -> Dimension | None:
        for hint in hints:
            for d in self.dimensions:
                if d.id == hint:
                    return d
        for hint in hints:
            for d in self.dimensions:
                if hint in d.id and not any(x in d.id for x in exclude):
                    return d
        return None


def localized_name(obj: Mapping[str, Any]) -> str:
    """Return the English (or first) name from an SDMX-JSON artefact."""
    name = obj.get("name")
    if isinstance(name, str):
        return name
    names = obj.get("names")
    if not isinstance(names, Mapping) and isinstance(name, Mapping):
        names = name
    if isinstance(names, Mapping) and names:
        return str(names.get("en") or next(iter(names.values())))
    return ""


def urn_ref(urn: str) -> str:
    """'urn:...Codelist=IMF.STA:CL_COUNTRY(1.0.0)' -> 'IMF.STA:CL_COUNTRY'."""
    tail = urn.split("=", 1)[-1]
    return tail.split("(", 1)[0]


def parse_structure(doc: Mapping[str, Any]) -> Structure:
    """Parse an SDMX-JSON structure message (v1.0 or v2.0) into a small model."""
    data = doc.get("data", doc)
    out = Structure(dataflows=list(data.get("dataflows") or []))

    for cl in data.get("codelists") or []:
        codes = {c["id"]: localized_name(c) for c in cl.get("codes") or []}
        out.codelists[f"{cl.get('agencyID', '')}:{cl['id']}"] = codes
        out.codelists.setdefault(cl["id"], codes)

    concept_enum: dict[str, str] = {}
    for scheme in data.get("conceptSchemes") or []:
        for concept in scheme.get("concepts") or []:
            enum = (concept.get("coreRepresentation") or {}).get("enumeration")
            if enum:
                concept_enum.setdefault(concept["id"], urn_ref(enum))

    for dsd in data.get("dataStructures") or []:
        comps = dsd.get("dataStructureComponents") or {}
        dims = (comps.get("dimensionList") or {}).get("dimensions") or []
        for i, d in enumerate(dims):
            enum = (d.get("localRepresentation") or {}).get("enumeration")
            codelist = urn_ref(enum) if enum else concept_enum.get(d["id"])
            out.dimensions.append(Dimension(d["id"], int(d.get("position", i)), codelist))
        attrs = (comps.get("attributeList") or {}).get("attributes") or []
        out.attributes = [a["id"] for a in attrs]
        break  # one DSD per dataflow

    out.dimensions.sort(key=lambda d: d.position)
    return out


def build_key(dimensions: list[Dimension], values: Mapping[str, str], wildcard: str = "") -> str:
    """Build a dot-separated series key. SDMX 2.1 wildcards with '', SDMX 3.0 with '*'."""
    return ".".join(values.get(d.id, wildcard) for d in dimensions)
