"""`mlab` entry point: run the loop, inspect runs."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from mlab.agents.builders.reference import ReferenceBuilder
from mlab.orchestrator import Orchestrator, RunConfig, default_runs_dir, offline_learner
from mlab.referee.channel import verify


def _run(args: argparse.Namespace) -> int:
    run_id = args.run_id or time.strftime("run-%Y%m%d-%H%M%S")
    cfg = RunConfig(run_id=run_id, rounds=args.rounds, seed=args.seed, profile=args.profile,
                    runs_dir=Path(args.runs_dir) if args.runs_dir else default_runs_dir())
    if args.builder != "reference" or args.learner != "scripted":
        print("only --builder reference --learner scripted is available offline", file=sys.stderr)
        return 2
    orch = Orchestrator(cfg, ReferenceBuilder(), offline_learner(args.seed))
    summary = orch.run()
    print(json.dumps({"run_dir": str(orch.dirs.root), "rounds": [
        {k: r.get(k) for k in ("round", "status", "device", "swap", "controls")}
        for r in summary["rounds"]]}, indent=2, default=str))
    return 0


def _verify(args: argparse.Namespace) -> int:
    path = Path(args.runs_dir or default_runs_dir()) / args.run_id / "public" / "channel.jsonl"
    ok, n = verify(path)
    print(f"channel log {'intact' if ok else 'BROKEN'}: {n} entries verified")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mlab")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="run builder/learner rounds")
    run.add_argument("--run-id")
    run.add_argument("--rounds", type=int, default=3)
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--profile", choices=["full", "fast", "test"], default="fast")
    run.add_argument("--builder", default="reference")
    run.add_argument("--learner", default="scripted")
    run.add_argument("--runs-dir")
    run.set_defaults(func=_run)
    ver = sub.add_parser("verify-log", help="verify the hash chain of a run's channel log")
    ver.add_argument("run_id")
    ver.add_argument("--runs-dir")
    ver.set_defaults(func=_verify)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
