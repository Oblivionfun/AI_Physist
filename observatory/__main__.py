"""observatory serve | export <run_id> | index"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from observatory.export import export_run, write_index
from observatory.server import serve

PROJECT = Path(__file__).resolve().parents[1]
RECORDED = PROJECT / "demo" / "recorded"
WEB_DIST = PROJECT / "web" / "dist"


def runs_dir() -> Path:
    return Path(os.environ.get("MLAB_RUNS_DIR", Path.home() / "mlab-runs"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="observatory", description="Read-only web viewer for mlab runs (live or recorded)."
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="token-gated local server: live runs and recorded bundles")
    s.add_argument("--port", type=int, default=0, help="0 picks a free port")
    e = sub.add_parser("export", help="write the static bundle of a finished run")
    e.add_argument("run_ids", nargs="+")
    e.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="bundle directory (default demo/recorded/<run_id>/viz; one run only)",
    )
    sub.add_parser("index", help="rebuild demo/recorded/viz-index.json")
    args = ap.parse_args(argv)

    if args.cmd == "serve":
        serve(runs_dir(), RECORDED, WEB_DIST, args.port)
    elif args.cmd == "export":
        if args.dest is not None and len(args.run_ids) > 1:
            ap.error("--dest takes a single run id")
        for run_id in args.run_ids:
            root = runs_dir() / run_id
            if not (root / "referee").is_dir():
                ap.error(f"no run directory {root}")
            dest = args.dest or RECORDED / run_id / "viz"
            export_run(root, dest, runs_dir() / "_viz")
        print(f"index: {write_index(RECORDED)}")
    else:
        print(f"index: {write_index(RECORDED)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
