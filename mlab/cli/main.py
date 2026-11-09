"""`mlab` entry point: run the loop, self-test the sandbox, verify logs."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from mlab.agents.backend import CursorAgentBackend
from mlab.agents.builders.reference import ReferenceBuilder
from mlab.agents.llm import LLMBuilder, LLMLearner
from mlab.orchestrator import (
    Orchestrator,
    RecordedBuilder,
    RunConfig,
    RunDirs,
    default_runs_dir,
    offline_learner,
)
from mlab.referee.channel import verify
from mlab.sandbox.selftest import main as selftest_main


def _log(message: str) -> None:
    print(message, flush=True)


def _keep_awake() -> None:
    """Prevent idle sleep for the lifetime of this process (macOS). A closed lid on battery
    still forces sleep; sessions that span a sleep are detected and marked invalid (D-019)."""
    if sys.platform == "darwin" and shutil.which("caffeinate"):
        subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])


def _run(args: argparse.Namespace) -> int:
    run_id = args.run_id or time.strftime("run-%Y%m%d-%H%M%S")
    llm = args.builder == "cursor" or args.learner == "cursor"
    if llm:
        _keep_awake()
    cfg = RunConfig(run_id=run_id, rounds=args.rounds, seed=args.seed, profile=args.profile,
                    max_builder_attempts=args.max_attempts, sandbox_theories=llm,
                    runs_dir=Path(args.runs_dir) if args.runs_dir else default_runs_dir())
    dirs = RunDirs(cfg.root)
    transcripts, profiles = dirs.referee / "transcripts", dirs.referee / "profiles"
    if args.builder == "cursor":
        builder = LLMBuilder(CursorAgentBackend(args.builder_model, timeout=args.timeout),
                             cfg.root, transcripts, profiles, cert_profile=args.profile, log=_log)
    else:
        builder = ReferenceBuilder()
    if args.learner == "cursor":
        learner = LLMLearner(CursorAgentBackend(args.learner_model, timeout=args.timeout),
                             cfg.root, cfg.root / "learner" / "main", transcripts, profiles,
                             log=_log)
    else:
        learner = offline_learner(args.seed)
    orch = Orchestrator(cfg, builder, learner)
    summary = orch.run()
    print(json.dumps({"run_dir": str(orch.dirs.root), "isolation_audit": summary["isolation_audit"],
                      "rounds": [{k: r.get(k) for k in ("round", "status", "device", "swap", "controls")}
                                 for r in summary["rounds"]]}, indent=2, default=str))
    return 0


def _rerun(args: argparse.Namespace) -> int:
    runs_dir = Path(args.runs_dir) if args.runs_dir else default_runs_dir()
    source = runs_dir / args.source
    secrets = json.loads((source / "referee" / "secrets.json").read_text())
    src_summary = json.loads((source / "referee" / "summary.json").read_text())
    cfg = RunConfig(run_id=args.run_id, rounds=len(src_summary["rounds"]), seed=secrets["seed"],
                    profile=src_summary["profile"], max_builder_attempts=1,
                    sandbox_theories=args.learner == "cursor", runs_dir=runs_dir,
                    instances_from=source)
    dirs = RunDirs(cfg.root)
    if args.learner == "cursor":
        _keep_awake()
        learner = LLMLearner(CursorAgentBackend(args.learner_model, timeout=args.timeout), cfg.root,
                             cfg.root / "learner" / "main", dirs.referee / "transcripts",
                             dirs.referee / "profiles", log=_log, amnesic=args.amnesic)
    else:
        learner = offline_learner(secrets["seed"])
    summary = Orchestrator(cfg, RecordedBuilder(source), learner).run()
    print(json.dumps({"run_dir": str(cfg.root), "rounds": [
        {k: r.get(k) for k in ("round", "status", "device", "swap")} for r in summary["rounds"]]},
        indent=2, default=str))
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
    run.add_argument("--builder", choices=["reference", "cursor"], default="reference")
    run.add_argument("--learner", choices=["scripted", "cursor"], default="scripted")
    run.add_argument("--builder-model", default="claude-opus-5-thinking-high")
    run.add_argument("--learner-model", default="gpt-5.6-sol-high")
    run.add_argument("--max-attempts", type=int, default=3)
    run.add_argument("--timeout", type=float, default=2700.0, help="seconds per agent session")
    run.add_argument("--runs-dir")
    run.set_defaults(func=_run)
    rr = sub.add_parser("rerun-learner", help="another learner on a finished run's devices/instances")
    rr.add_argument("source", help="run id whose certified devices and instances are reused")
    rr.add_argument("--run-id", required=True)
    rr.add_argument("--learner", choices=["scripted", "cursor"], default="cursor")
    rr.add_argument("--learner-model", default="gpt-5.3-codex")
    rr.add_argument("--amnesic", action="store_true", help="wipe the learner's memory every session")
    rr.add_argument("--timeout", type=float, default=2400.0)
    rr.add_argument("--runs-dir")
    rr.set_defaults(func=_rerun)
    ver = sub.add_parser("verify-log", help="verify the hash chain of a run's channel log")
    ver.add_argument("run_id")
    ver.add_argument("--runs-dir")
    ver.set_defaults(func=_verify)
    st = sub.add_parser("selftest", help="verify sandbox profiles deny/allow as designed")
    st.set_defaults(func=lambda _a: selftest_main())
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
