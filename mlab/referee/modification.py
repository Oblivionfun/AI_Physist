"""Public modifications of visible dimensions: where the referee tests them and how much they
matter. A modification that moves outcomes by less than C3_modification tolerances cannot tell
a physical model from a curve fit that ignores it (D-018)."""

from __future__ import annotations

import numpy as np

from mlab.construct.compile import CompiledDevice, compile_device
from mlab.construct.ir import ModifiableIR, Submission, TaskIR
from mlab.construct.modify import apply_modification, mod_key, visible_params
from mlab.referee.oracle import usable
from mlab.sim.runner import simulate

DISCRIMINATION = 1.5


def modified_value(mod: ModifiableIR, now: float) -> float:
    """The referee moves a dimension 80% of the way towards its farther bound."""
    far = mod.low if abs(now - mod.low) > abs(mod.high - now) else mod.high
    return now + 0.8 * (far - now)


def outcomes(dev: CompiledDevice, task: TaskIR, knob_list: list[dict]) -> list[list[float] | None]:
    out = []
    for knobs in knob_list:
        r = simulate(dev, task, knobs)
        out.append(r.outcome.tolist() if usable(r.status, r.outcome) else None)
    return out


def effect_over_tol(base: list[list[float] | None], moved: list[list[float] | None],
                    tolerance: float) -> float | None:
    """Median outcome change over paired queries, in tolerances."""
    diffs = [float(np.linalg.norm(np.asarray(a) - np.asarray(b))) / tolerance
             for a, b in zip(base, moved, strict=True) if a is not None and b is not None]
    return float(np.median(diffs)) if diffs else None


def modification_effect(sub: Submission, dev: CompiledDevice, rng: np.random.Generator,
                        n: int = 6) -> dict[str, float | None]:
    """Effect of each declared modification at its test value, over random knob settings."""
    task = sub.task
    names = [k.name for k in task.knobs]
    vis = visible_params(sub.device, task)
    knob_list = [dict(zip(names, [k.low + rng.uniform() * (k.high - k.low) for k in task.knobs],
                          strict=True)) for _ in range(n)]
    base = outcomes(dev, task, knob_list)
    out: dict[str, float | None] = {}
    for mod in task.modifiable:
        value = modified_value(mod, vis[mod_key(mod)])
        mdev = compile_device(apply_modification(sub.device, mod, value), dev.theta)
        out[mod_key(mod)] = effect_over_tol(base, outcomes(mdev, task, knob_list), task.tolerance)
    return out
