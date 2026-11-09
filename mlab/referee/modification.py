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
# A modification that turns a valid outcome into none (or back) changes the answer entirely; it
# is counted as this many tolerances rather than dropped as missing data (D-022).
KIND_CHANGE = 10.0


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
    """Median outcome change over paired queries, in tolerances (None if no pair has an outcome
    on either side)."""
    diffs = []
    for a, b in zip(base, moved, strict=True):
        if a is None and b is None:
            continue
        if a is None or b is None:
            diffs.append(KIND_CHANGE)
        else:
            diffs.append(float(np.linalg.norm(np.asarray(a) - np.asarray(b))) / tolerance)
    return float(np.median(diffs)) if diffs else None


def modification_effect(sub: Submission, dev: CompiledDevice, rng: np.random.Generator,
                        n: int = 6, knob_list: list[dict] | None = None) -> dict[str, float | None]:
    """Effect of each declared modification at its test value, over `knob_list` (default: n
    random knob settings)."""
    task = sub.task
    names = [k.name for k in task.knobs]
    vis = visible_params(sub.device, task)
    if knob_list is None:
        knob_list = [dict(zip(names, [k.low + rng.uniform() * (k.high - k.low) for k in task.knobs],
                              strict=True)) for _ in range(n)]
    base = outcomes(dev, task, knob_list)
    out: dict[str, float | None] = {}
    for mod in task.modifiable:
        value = modified_value(mod, vis[mod_key(mod)])
        mdev = compile_device(apply_modification(sub.device, mod, value), dev.theta)
        out[mod_key(mod)] = effect_over_tol(base, outcomes(mdev, task, knob_list), task.tolerance)
    return out
