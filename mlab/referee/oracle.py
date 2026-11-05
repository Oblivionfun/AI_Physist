"""Generic privileged solver: given true parameters, search knob space for a goal.

It never sees anything the builder wrote except the declarative task, so the existence
certificate does not depend on builder-supplied solution code.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.stats import qmc

from mlab.construct.compile import CompiledDevice
from mlab.construct.ir import TaskIR
from mlab.sim.runner import simulate

INVALID_DISTANCE = 1e3


def unit_to_knobs(task: TaskIR, u: np.ndarray) -> dict[str, float]:
    u = np.clip(u, 0.0, 1.0)
    return {k.name: float(k.low + ui * (k.high - k.low)) for k, ui in zip(task.knobs, u, strict=True)}


def knobs_to_unit(task: TaskIR, knobs: dict[str, float]) -> np.ndarray:
    return np.array([(knobs[k.name] - k.low) / (k.high - k.low) for k in task.knobs])


def sobol_points(d: int, n: int, rng: np.random.Generator) -> np.ndarray:
    m = int(np.ceil(np.log2(max(2, n))))
    sampler = qmc.Sobol(d=d, scramble=True, seed=rng)
    return sampler.random_base2(m)[:n]


def usable(status: str, outcome) -> bool:
    return outcome is not None and status == "ok"


class GenericOracle:
    def __init__(
        self,
        dev: CompiledDevice,
        task: TaskIR,
        rng: np.random.Generator,
        table_per_dim: int = 48,
        refine_evals: int = 40,
    ):
        self.dev = dev
        self.task = task
        self.refine_evals = refine_evals
        d = len(task.knobs)
        self.points = sobol_points(d, table_per_dim * d, rng)
        outs = []
        self.statuses: list[str] = []
        for u in self.points:
            r = simulate(dev, task, unit_to_knobs(task, u))
            self.statuses.append(r.status)
            outs.append(r.outcome if usable(r.status, r.outcome) else None)
        dim = len(task.goal_space)
        self.outcomes = np.array([o if o is not None else np.full(dim, np.nan) for o in outs])
        self.sim_count = len(self.points)

    def unstable_fraction(self) -> float:
        return sum(s == "unstable" for s in self.statuses) / max(1, len(self.statuses))

    def _distance(self, u: np.ndarray, goal: np.ndarray) -> float:
        self.sim_count += 1
        r = simulate(self.dev, self.task, unit_to_knobs(self.task, u))
        if not usable(r.status, r.outcome):
            return INVALID_DISTANCE
        return float(np.linalg.norm(r.outcome - goal))

    def solve(self, goal: np.ndarray) -> dict[str, float]:
        dist = np.linalg.norm(self.outcomes - goal, axis=1)
        dist = np.where(np.isnan(dist), np.inf, dist)
        order = np.argsort(dist)
        best_u = self.points[order[0]].copy()
        best_d = float(dist[order[0]])
        if best_d <= 0.2 * self.task.tolerance or self.refine_evals <= 0:
            return unit_to_knobs(self.task, best_u)
        d = len(self.task.knobs)
        simplex = np.vstack([best_u] + [np.clip(best_u + 0.04 * np.eye(d)[i], 0, 1) for i in range(d)])
        res = minimize(
            lambda u: self._distance(u, goal),
            best_u,
            method="Nelder-Mead",
            options={
                "maxfev": self.refine_evals,
                "initial_simplex": simplex,
                "xatol": 1e-4,
                "fatol": 0.05 * self.task.tolerance,
            },
        )
        if res.fun < best_d:
            best_u = np.clip(res.x, 0, 1)
        return unit_to_knobs(self.task, best_u)

    def fixed_action_coverage(self, goals: np.ndarray) -> float:
        """Largest fraction of goals one single action reaches (noise-free)."""
        tol = self.task.tolerance
        best = 0.0
        for o in self.outcomes:
            if np.any(np.isnan(o)):
                continue
            frac = float(np.mean(np.linalg.norm(goals - o, axis=1) <= tol))
            best = max(best, frac)
        return best
