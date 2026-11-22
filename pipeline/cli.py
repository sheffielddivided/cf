"""Command line entry point: ``uv run pipeline <command>``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_explore = sub.add_parser("explore", help="phase 0: explore IMF/OECD SDMX APIs")
    p_explore.add_argument("--out", type=Path, default=Path("data/explore"))
    p_explore.add_argument("--nowcast", action="store_true", help="phase 2: ECB, TIC and MOF")

    p_cov = sub.add_parser("coverage", help="phase 0: build the coverage matrix from IMF data")
    p_cov.add_argument("--out", type=Path, default=Path("data/explore"))
    p_cov.add_argument("--series-map", type=Path, default=Path("config/series_map.yaml"))
    p_cov.add_argument("--countries", type=Path, default=Path("config/countries.yaml"))
    p_cov.add_argument("--reference-year", type=int, default=2025)

    p_up = sub.add_parser("update", help="phase 1: fetch, normalise, check and export")
    p_up.add_argument("--root", type=Path, default=Path("."))

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    if args.command == "explore":
        from .explore import explore, explore_nowcast

        manifest = explore_nowcast(args.out) if args.nowcast else explore(args.out)
        print(f"manifest: {manifest}")
    elif args.command == "coverage":
        from .coverage import run

        path = run(args.out, args.series_map, args.countries, args.reference_year)
        print(f"coverage: {path}")
    elif args.command == "update":
        from .update import run as update

        return update(args.root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
