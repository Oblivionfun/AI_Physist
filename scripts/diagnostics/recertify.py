"""Certify a device file in the world of a recorded run, with the current or the pre-D-017
reference-learner budget. Operator tool: it reads the run's secret world.

Device files are builder-written code and this script runs outside any sandbox, so a file is
refused unless it only imports construction modules and calls no file, process or eval builtins.

    uv run python scripts/diagnostics/recertify.py sliding_slug.py demo-1 --profile fast --seeds 1 2 3
    uv run python scripts/diagnostics/recertify.py sliding_slug.py demo-1 --profile pre-d017-fast
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import json
import time
from pathlib import Path

import numpy as np

from mlab.cli.forge import load
from mlab.referee.certify import FAST, FULL, certify
from mlab.referee.reference import FitBudget

ALLOWED_IMPORTS = {"math", "numpy", "mlab.construct", "mlab.construct.ir", "__future__"}
FORBIDDEN_CALLS = {"open", "exec", "eval", "compile", "__import__", "getattr", "globals", "vars"}


def audit_device_file(path: Path) -> list[str]:
    problems = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            problems += [f"import {a.name}" for a in node.names if a.name not in ALLOWED_IMPORTS]
        elif isinstance(node, ast.ImportFrom) and node.module not in ALLOWED_IMPORTS:
            problems.append(f"from {node.module} import ...")
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id in FORBIDDEN_CALLS):
            problems.append(f"call {node.func.id}() at line {node.lineno}")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            problems.append(f"dunder attribute {node.attr} at line {node.lineno}")
    return problems


PROFILES = {
    "fast": FAST,
    "full": FULL,
    "pre-d017-fast": dataclasses.replace(FAST, reference_max_keys=3,
                                         reference_fit=FitBudget(16, 8, 12, 1, 24)),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("device", type=Path)
    ap.add_argument("run_id")
    ap.add_argument("--profile", choices=sorted(PROFILES), default="fast")
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--keys", type=int, help="override the number of parameters the reference fits")
    ap.add_argument("--fit", help="FitBudget as search_points,search_subset,fit_subset,starts,evals")
    ap.add_argument("--runs-dir", type=Path, default=Path.home() / "mlab-runs")
    args = ap.parse_args()
    problems = audit_device_file(args.device)
    if problems:
        raise SystemExit(f"refusing to execute {args.device} outside a sandbox: {problems}")
    world = json.loads((args.runs_dir / args.run_id / "referee" / "secrets.json").read_text())["world"]
    sub = load(str(args.device))
    profile = PROFILES[args.profile]
    if args.keys:
        profile = dataclasses.replace(profile, reference_max_keys=args.keys)
    if args.fit:
        profile = dataclasses.replace(profile, reference_fit=FitBudget(*map(int, args.fit.split(","))))
    for seed in args.seeds:
        t0 = time.time()
        cert = certify(sub, world, np.random.default_rng(seed), profile, stop_on_fail=False)
        print(f"{args.device.name} {args.profile} keys {profile.reference_max_keys} seed {seed}: "
              f"{'CERTIFIED' if cert.passed else 'REJECTED'} ({time.time() - t0:.0f}s), "
              f"relevant {cert.stats.get('relevant_parameters')}")
        for v in cert.verdicts:
            if not v.passed or v.title.startswith("learnability"):
                print("   ", v.line())


if __name__ == "__main__":
    main()
