"""Turn a pipeline run summary into GitHub Issues (one open issue per kind, updated by comment).

Usage: report_issues.py run/summary.json   (needs GH_TOKEN and the gh CLI)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

LABELS = {
    "source-down": ("b60205", "En datakilde svarte ikke"),
    "data-quality": ("d93f0b", "Advarsel eller feil fra kvalitetskontrollene"),
    "revision": ("fbca04", "Store revisjoner i kildedata"),
}


def gh(*args: str, check: bool = True) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True, check=check)
    return out.stdout.strip()


def ensure_labels() -> None:
    for name, (color, desc) in LABELS.items():
        gh("label", "create", name, "--color", color, "--description", desc, "--force",
           check=False)


def upsert(label: str, title: str, body: str) -> None:
    number = gh("issue", "list", "--label", label, "--state", "open", "--json", "number,title",
                "--jq", f'map(select(.title == "{title}")) | .[0].number // empty')
    if number:
        gh("issue", "comment", number, "--body", body)
    else:
        gh("issue", "create", "--label", label, "--title", title, "--body", body)


def bullets(items: list[str], limit: int = 50) -> str:
    lines = [f"- {i}" for i in items[:limit]]
    if len(items) > limit:
        lines.append(f"- … og {len(items) - limit} til")
    return "\n".join(lines)


def main(path: str) -> int:
    run_url = os.environ.get("RUN_URL", "")
    p = Path(path)
    if not p.exists():
        ensure_labels()
        upsert("data-quality", "Pipeline stoppet",
               f"Ingen run-oppsummering ble skrevet.\n\n{run_url}")
        return 0
    s = json.loads(p.read_text())
    ensure_labels()
    status = s.get("status")
    if status == "source_error":
        upsert("source-down", "Datakilde utilgjengelig",
               f"**{s.get('error')}**\n\nIngen data ble skrevet. Neste kjøring prøver igjen.\n\n"
               f"{run_url}")
    elif status == "check_error":
        upsert("data-quality", "Pipeline stoppet: kontroll feilet",
               f"Ingen data ble publisert.\n\n{bullets(s.get('errors', []))}\n\n{run_url}")
    elif status == "ok" and s.get("changed"):
        warnings = [w for w in s.get("warnings", []) if not w.startswith("revisjon:")]
        if warnings:
            upsert("data-quality", "Datakvalitet: advarsler",
                   f"Data for {s.get('last_common_quarter')} ble publisert med advarsler:\n\n"
                   f"{bullets(warnings)}\n\n{run_url}")
        big = s.get("big_revisions", [])
        if big:
            upsert("revision", "Store revisjoner i kildedata",
                   f"{len(big)} verdier endret seg mer enn 10 %:\n\n{bullets(big)}\n\n"
                   f"Se `REVISIONS.md`. {run_url}")
        if any(w.startswith("utvalg:") for w in s.get("warnings", [])):
            changes = [w for w in s["warnings"] if w.startswith("utvalg:")]
            upsert("data-quality", "Landutvalget er endret", f"{bullets(changes)}\n\n{run_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
