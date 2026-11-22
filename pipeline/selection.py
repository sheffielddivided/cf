"""The country selection: top N by GDP in the reference year, locked per reference year.

Reference year = last complete year with data (see model.reference_year). The selection is
stored in data/processed/selection.json and only recomputed when the reference year changes.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .coverage import top_n_by_gdp


@dataclass
class Selection:
    reference_year: int
    countries: list[str]
    gdp_usd_bn: dict[str, float]

    @classmethod
    def compute(cls, gdp: dict[tuple[str, int], float], year: int, n: int = 20) -> Selection:
        top = top_n_by_gdp(gdp, year, n)
        return cls(year, [c for c, _ in top], {c: round(v, 1) for c, v in top})

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n")

    @classmethod
    def load(cls, path: Path) -> Selection | None:
        if not path.exists():
            return None
        d = json.loads(path.read_text())
        return cls(int(d["reference_year"]), list(d["countries"]), dict(d["gdp_usd_bn"]))
