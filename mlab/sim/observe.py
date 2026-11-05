"""Noisy observations as the learner sees them, and fixed-grid feature vectors for fitting."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from mlab.catalog.models import OUTCOME_NOISE
from mlab.construct.ir import DeviceIR, TaskIR
from mlab.sim.runner import RunResult

FEATURE_POINTS = 12
MISSING_PENALTY = 5.0


def outcome_noise(task: TaskIR) -> float:
    return OUTCOME_NOISE["angle"] if task.outcome.kind == "final_joint_angle" else OUTCOME_NOISE["position"]


@dataclass
class Observation:
    outcome: list[float] | None
    status: str
    times: list[float]
    traces: dict[str, list]


def observe(result: RunResult, device: DeviceIR, task: TaskIR, rng: np.random.Generator) -> Observation:
    noise = {s.name: s.noise for s in device.sensors}
    traces: dict[str, list] = {}
    for name, values in result.traces.items():
        arr = np.asarray(values, dtype=float)
        noisy = arr + rng.normal(0.0, noise[name], size=arr.shape)
        traces[name] = np.round(noisy, 5).tolist()
    outcome = None
    if result.outcome is not None:
        noisy_out = result.outcome + rng.normal(0.0, outcome_noise(task), size=result.outcome.shape)
        outcome = [round(float(v), 5) for v in noisy_out]
    return Observation(
        outcome=outcome,
        status=result.status,
        times=[round(float(t), 4) for t in result.times],
        traces=traces,
    )


def _grid_trace(times: np.ndarray, values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    if values.ndim == 1:
        values = values[:, None]
    out = np.empty((len(grid), values.shape[1]))
    for j in range(values.shape[1]):
        out[:, j] = np.interp(grid, times, values[:, j], left=values[0, j], right=values[-1, j])
    return out.ravel()


def feature_vector(
    times, traces: dict, outcome, status: str, device: DeviceIR, task: TaskIR
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (values, sigmas, mask); mask marks entries that exist (outcome may be missing)."""
    grid = np.linspace(0.0, task.horizon, FEATURE_POINTS)
    t = np.asarray(times, dtype=float)
    values: list[np.ndarray] = []
    sigmas: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    dim = 1 if task.outcome.kind in ("final_joint_angle", "max_height") else len(task.outcome.axes)
    ok = outcome is not None and status in ("ok", "unsettled")
    values.append(np.asarray(outcome, dtype=float) if ok else np.zeros(dim))
    sigmas.append(np.full(dim, outcome_noise(task)))
    masks.append(np.full(dim, ok))
    for s in device.sensors:
        arr = np.asarray(traces[s.name], dtype=float)
        g = _grid_trace(t, arr, grid)
        values.append(g)
        sigmas.append(np.full(g.shape, s.noise))
        masks.append(np.ones(g.shape, dtype=bool))
    return np.concatenate(values), np.concatenate(sigmas), np.concatenate(masks)


def residuals(sim_feat, obs_feat) -> np.ndarray:
    sv, ss, sm = sim_feat
    ov, _, om = obs_feat
    both = sm & om
    r = np.where(both, (sv - ov) / ss, 0.0)
    mismatch = sm != om
    return np.where(mismatch, MISSING_PENALTY, r)
