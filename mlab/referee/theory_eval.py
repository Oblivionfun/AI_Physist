"""Evaluate a learner's executable theory (predict.py) against ground truth.

The theory runs in a separate interpreter (`-I`: no user site, no environment), fed queries
on stdin. In isolated runs the command is wrapped by the theory sandbox profile, because an
executable submission could otherwise read referee files.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from mlab.construct.compile import CompiledDevice, compile_device
from mlab.construct.ir import Submission
from mlab.construct.modify import apply_modification, mod_key, visible_params
from mlab.referee.oracle import usable
from mlab.sim.runner import simulate

RUNNER = """\
import json, sys, importlib.util
spec = importlib.util.spec_from_file_location("learner_theory", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
out = []
for q in json.load(sys.stdin):
    try:
        y = mod.predict(dict(q["knobs"]), dict(q["visible"]))
        y = list(y) if isinstance(y, (list, tuple)) else [y]
        out.append([float(v) for v in y])
    except Exception:
        out.append(None)
json.dump(out, sys.stdout)
"""


@dataclass
class QuerySet:
    name: str
    queries: list[dict]
    truths: list[list[float] | None]
    note: str = ""


@dataclass
class TheoryScore:
    name: str
    n: int
    answered: int
    hit_rate: float | None
    mean_abs_over_tol: float | None
    mean_signed_over_tol: list[float] | None
    note: str = ""
    errors: list[float | None] = field(default_factory=list)


def run_theory(code: str, queries: list[dict], python: str | None = None,
               wrapper: list[str] | None = None, timeout: float = 120.0) -> list | None:
    with tempfile.TemporaryDirectory(prefix="mlab_theory_") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "predict.py").write_text(code)
        (tmp_path / "runner.py").write_text(RUNNER)
        cmd = [python or sys.executable, "-I", str(tmp_path / "runner.py"), str(tmp_path / "predict.py")]
        if wrapper:
            cmd = wrapper + cmd
        try:
            proc = subprocess.run(cmd, input=json.dumps(queries), capture_output=True, text=True,
                                  timeout=timeout, cwd=tmp, check=False)
        except subprocess.TimeoutExpired:
            return None
        if proc.returncode != 0:
            return None
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return None
        return out if isinstance(out, list) and len(out) == len(queries) else None


def _truths(dev: CompiledDevice, sub: Submission, knob_list: list[dict]) -> list[list[float] | None]:
    out = []
    for knobs in knob_list:
        r = simulate(dev, sub.task, knobs)
        out.append(r.outcome.tolist() if usable(r.status, r.outcome) else None)
    return out


def explored_box(sub: Submission, lab_knobs: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    names = [k.name for k in sub.task.knobs]
    if not lab_knobs:
        mid = np.array([(k.low + k.high) / 2 for k in sub.task.knobs])
        return mid, mid
    arr = np.array([[kn[n] for n in names] for kn in lab_knobs])
    return arr.min(axis=0), arr.max(axis=0)


def build_query_sets(sub: Submission, dev: CompiledDevice, lab_knobs: list[dict],
                     rng: np.random.Generator, n: int = 8) -> list[QuerySet]:
    task = sub.task
    names = [k.name for k in task.knobs]
    lo_all = np.array([k.low for k in task.knobs])
    hi_all = np.array([k.high for k in task.knobs])
    lo, hi = explored_box(sub, lab_knobs)
    vis = visible_params(sub.device, task)
    sets: list[QuerySet] = []

    inside = [dict(zip(names, (lo + rng.uniform(size=len(names)) * (hi - lo)).tolist(), strict=True))
              for _ in range(n)]
    sets.append(QuerySet("in_distribution",
                         [{"knobs": k, "visible": vis} for k in inside], _truths(dev, sub, inside)))

    span = hi_all - lo_all
    room_low, room_high = lo - lo_all, hi_all - hi
    outside = []
    if np.any(np.maximum(room_low, room_high) > 0.05 * span):
        for _ in range(n):
            point = lo + rng.uniform(size=len(names)) * (hi - lo)
            j = int(np.argmax(np.maximum(room_low, room_high) / span))
            if room_high[j] >= room_low[j]:
                point[j] = hi[j] + rng.uniform(0.2, 1.0) * room_high[j]
            else:
                point[j] = lo[j] - rng.uniform(0.2, 1.0) * room_low[j]
            outside.append(dict(zip(names, point.tolist(), strict=True)))
        sets.append(QuerySet("extrapolation", [{"knobs": k, "visible": vis} for k in outside],
                             _truths(dev, sub, outside)))
    else:
        sets.append(QuerySet("extrapolation", [], [], note="exploration covered the whole range"))

    for mod in task.modifiable:
        now = vis[mod_key(mod)]
        far = mod.low if abs(now - mod.low) > abs(mod.high - now) else mod.high
        value = now + 0.8 * (far - now)
        mdev = compile_device(apply_modification(sub.device, mod, value), dev.theta)
        mvis = dict(vis)
        mvis[mod_key(mod)] = value
        sets.append(QuerySet(f"modified {mod_key(mod)}={value:.4g}",
                             [{"knobs": k, "visible": mvis} for k in inside],
                             _truths(mdev, sub, inside)))
    return sets


def modification_effect(sub: Submission, dev: CompiledDevice, rng: np.random.Generator,
                        n: int = 6) -> dict[str, float | None]:
    """How much each public modification moves outcomes (in tolerances). Below ~1.5 the
    modification test cannot discriminate physical understanding from curve fitting."""
    task = sub.task
    names = [k.name for k in task.knobs]
    vis = visible_params(sub.device, task)
    knob_list = [dict(zip(names, [k.low + rng.uniform() * (k.high - k.low) for k in task.knobs],
                          strict=True)) for _ in range(n)]
    base = _truths(dev, sub, knob_list)
    out: dict[str, float | None] = {}
    for mod in task.modifiable:
        now = vis[mod_key(mod)]
        far = mod.low if abs(now - mod.low) > abs(mod.high - now) else mod.high
        mdev = compile_device(apply_modification(sub.device, mod, now + 0.8 * (far - now)), dev.theta)
        moved = _truths(mdev, sub, knob_list)
        diffs = [float(np.linalg.norm(np.asarray(a) - np.asarray(b))) / task.tolerance
                 for a, b in zip(base, moved, strict=True) if a is not None and b is not None]
        out[mod_key(mod)] = float(np.median(diffs)) if diffs else None
    return out


def score(qs: QuerySet, predictions: list | None, tolerance: float) -> TheoryScore:
    n = len(qs.queries)
    if n == 0:
        return TheoryScore(qs.name, 0, 0, None, None, None, note=qs.note)
    errors: list[float | None] = []
    signed = []
    hits = answered = valid = 0
    for i, truth in enumerate(qs.truths):
        pred = None if predictions is None else predictions[i]
        if truth is None:
            errors.append(None)
            continue
        valid += 1
        if pred is None or len(pred) != len(truth) or not np.all(np.isfinite(pred)):
            errors.append(None)
            continue
        answered += 1
        diff = np.asarray(pred) - np.asarray(truth)
        e = float(np.linalg.norm(diff)) / tolerance
        errors.append(e)
        signed.append(diff / tolerance)
        hits += e <= 1.0
    if valid == 0:
        return TheoryScore(qs.name, n, 0, None, None, None, note="no valid ground truth")
    return TheoryScore(
        name=qs.name, n=valid, answered=answered, hit_rate=hits / valid,
        mean_abs_over_tol=float(np.mean([e for e in errors if e is not None])) if answered else None,
        mean_signed_over_tol=np.mean(signed, axis=0).tolist() if signed else None,
        errors=errors,
    )
