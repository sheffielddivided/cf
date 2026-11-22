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

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    if args.command == "explore":
        from .explore import explore

        manifest = explore(args.out)
        print(f"manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
