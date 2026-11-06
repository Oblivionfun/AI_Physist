"""Gray-box reference learner: knows the structure, not the parameters.

It experiments only through the public interface (commanded knobs in, noisy outcome and
sensor traces out) within the learner's budget, then fits parameters by simulation: a coarse
quasi-random search over the relevant unknowns followed by Nelder-Mead refinement. Contacts
make the objective non-smooth, so no gradients are used. Its success shows the hidden
information is recoverable in budget; it is an upper reference, not a model of the LLM.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from mlab.catalog.priors import Prior
from mlab.construct.compile import CompiledDevice, compile_device
from mlab.construct.ir import TaskIR
from mlab.referee.oracle import sobol_points, unit_to_knobs
from mlab.referee.theta import to_unit, with_unit
from mlab.sim.observe import feature_vector, observe, residuals
from mlab.sim.runner import simulate


@dataclass(frozen=True)
class FitBudget:
    """Compute budget of the parameter fit (simulations, not experiments). Below roughly
    3 x 80 Nelder-Mead evaluations the fit fails on identifiable devices often enough to make
    C3 a coin flip (D-017)."""

    search_points: int = 32
    search_subset: int = 12
    fit_subset: int = 20
    refine_starts: int = 3
    refine_evals: int = 80


@dataclass
class ReferenceFit:
    theta_hat: dict[str, float]
    keys: list[str]
    unit_error: dict[str, float]
    cost: float
    sims: int


def gray_box_fit(
    true_dev: CompiledDevice,
    task: TaskIR,
    priors: dict[str, Prior],
    keys: list[str],
    base_theta: dict[str, float],
    rng: np.random.Generator,
    act_noise: float,
    budget: int,
    fit: FitBudget,
) -> ReferenceFit:
    d = len(task.knobs)
    design = [unit_to_knobs(task, u) for u in sobol_points(d, budget, rng)]
    observed = []
    for knobs in design:
        r = simulate(true_dev, task, knobs, rng=rng, act_noise=act_noise)
        o = observe(r, true_dev.ir, task, rng)
        observed.append(feature_vector(o.times, o.traces, o.outcome, o.status, true_dev.ir, task))
    sims = [budget]
    sub = {k: priors[k] for k in keys}

    def cost(u: np.ndarray, idx: np.ndarray) -> float:
        theta = with_unit(base_theta, sub, np.clip(u, 0.0, 1.0))
        dev = compile_device(true_dev.ir, theta)
        total = 0.0
        for i in idx:
            r = simulate(dev, task, design[i])
            f = feature_vector(r.times, r.traces, r.outcome, r.status, dev.ir, task)
            res = residuals(f, observed[i])
            total += float(np.sum(np.log1p(res**2)))
        sims[0] += len(idx)
        return total

    order = rng.permutation(budget)
    search_idx = order[: min(fit.search_subset, budget)]
    fit_idx = order[: min(fit.fit_subset, budget)]
    candidates = sobol_points(len(keys), fit.search_points, rng)
    scored = sorted(((cost(u, search_idx), tuple(u)) for u in candidates), key=lambda t: t[0])
    best_u, best_c = np.array(scored[0][1]), np.inf
    for _, start in scored[: fit.refine_starts]:
        start = np.array(start)
        n = len(keys)
        simplex = np.vstack([start] + [np.clip(start + 0.08 * np.eye(n)[i], 0, 1) for i in range(n)])
        res = minimize(
            lambda u: cost(u, fit_idx),
            start,
            method="Nelder-Mead",
            options={"maxfev": fit.refine_evals, "initial_simplex": simplex, "xatol": 1e-3},
        )
        if res.fun < best_c:
            best_u, best_c = np.clip(res.x, 0.0, 1.0), float(res.fun)
    theta_hat = with_unit(base_theta, sub, best_u)
    true_u = to_unit(true_dev.theta, sub)
    err = {k: float(abs(best_u[i] - true_u[i])) for i, k in enumerate(keys)}
    return ReferenceFit(theta_hat=theta_hat, keys=keys, unit_error=err, cost=best_c, sims=sims[0])
