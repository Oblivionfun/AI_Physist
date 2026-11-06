"""How reliable is the C3 gray-box reference learner on a recorded device? (D-017)

Repeats the reference fit with independent seeds on one instance of a certified submission
and reports the hit rate of each fit. Operator tool: it reads referee files.

    uv run python scripts/diagnostics/c3_reference_variance.py demo-1 3 --seeds 8
    uv run python scripts/diagnostics/c3_reference_variance.py demo-1 3 --keys 3 \
        --fit 16,8,12,1,24          # the FAST budget before D-017
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import time
from pathlib import Path

import numpy as np

from mlab.analysis.replay import certified_submission, instance_device
from mlab.construct.compile import compile_device
from mlab.referee.certify import FAST, FULL, _goals
from mlab.referee.oracle import GenericOracle
from mlab.referee.reference import FitBudget, gray_box_fit
from mlab.referee.theta import hidden_priors, nominal_instance
from mlab.sim.runner import simulate, succeeded


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_id")
    ap.add_argument("round", type=int)
    ap.add_argument("--instance", default="A")
    ap.add_argument("--profile", choices=["fast", "full"], default="fast")
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--keys", type=int, help="number of relevant parameters to fit")
    ap.add_argument("--fit", help="FitBudget as search_points,search_subset,fit_subset,starts,evals")
    ap.add_argument("--runs-dir", default=str(Path.home() / "mlab-runs"))
    args = ap.parse_args()

    root = Path(args.runs_dir) / args.run_id
    prof = {"fast": FAST, "full": FULL}[args.profile]
    if args.keys:
        prof = dataclasses.replace(prof, reference_max_keys=args.keys)
    if args.fit:
        prof = dataclasses.replace(prof, reference_fit=FitBudget(*map(int, args.fit.split(","))))
    sub = certified_submission(root, args.round)
    cert = json.loads(next((root / "referee" / "certificates").glob(f"r{args.round}_a*.json")).read_text())
    keys = cert["stats"]["relevant_parameters"][: prof.reference_max_keys]
    dev = instance_device(root, args.round, args.instance, sub)
    task = sub.task
    priors = hidden_priors(sub.device)
    base = dict(dev.theta) | {k: v for k, v in nominal_instance(sub.device).items() if k in priors}
    print(f"round {args.round} instance {args.instance}: keys {keys}, budget {task.budget}, "
          f"tolerance {task.tolerance}, fit {prof.reference_fit}")

    rates = []
    for seed in range(args.seeds):
        rng = np.random.default_rng(1000 + seed)
        t0 = time.time()
        fit = gray_box_fit(dev, task, priors, keys, base, rng, prof.act_noise, task.budget,
                           prof.reference_fit)
        oracle = GenericOracle(compile_device(sub.device, fit.theta_hat), task, rng,
                               prof.table_per_dim, prof.refine_evals)
        goals = _goals(task, prof.n_goals, rng)
        hits = sum(succeeded(simulate(dev, task, oracle.solve(g), rng=rng, act_noise=prof.act_noise),
                             g, task.tolerance) for g in goals)
        rates.append(hits / len(goals))
        err = {k: round(v, 2) for k, v in fit.unit_error.items()}
        print(f"  seed {seed}: hits {hits}/{len(goals)}, unit error {err} ({time.time() - t0:.0f}s)",
              flush=True)
    print(f"mean {np.mean(rates):.3f}, worst {min(rates):.3f}, "
          f"fits >= 0.7: {sum(r >= 0.7 for r in rates)}/{len(rates)}")


if __name__ == "__main__":
    main()
