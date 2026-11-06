"""Certify a device file in the world of a recorded run, with the current or the pre-D-017
reference-learner budget. Operator tool: it reads the run's secret world.

    uv run python scripts/diagnostics/recertify.py sliding_slug.py demo-1 --profile fast --seeds 1 2 3
    uv run python scripts/diagnostics/recertify.py sliding_slug.py demo-1 --profile pre-d017-fast
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import time
from pathlib import Path

import numpy as np

from mlab.cli.forge import load
from mlab.referee.certify import FAST, FULL, certify
from mlab.referee.reference import FitBudget

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
    ap.add_argument("--runs-dir", type=Path, default=Path.home() / "mlab-runs")
    args = ap.parse_args()
    world = json.loads((args.runs_dir / args.run_id / "referee" / "secrets.json").read_text())["world"]
    sub = load(str(args.device))
    for seed in args.seeds:
        t0 = time.time()
        cert = certify(sub, world, np.random.default_rng(seed), PROFILES[args.profile],
                       stop_on_fail=False)
        print(f"{args.device.name} {args.profile} seed {seed}: "
              f"{'CERTIFIED' if cert.passed else 'REJECTED'} ({time.time() - t0:.0f}s)")
        for v in cert.verdicts:
            if not v.passed or v.title.startswith("learnability"):
                print("   ", v.line())


if __name__ == "__main__":
    main()
