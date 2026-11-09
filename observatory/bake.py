"""Referee-side re-simulation for the viewer: 3D replays, true responses and theory curves.

Replays are noise-free: they show the intended action on the true instance, not the exact
noisy trial the learner saw (the viewer overlays the learner's observed outcome).
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np

from mlab.construct.compile import CompiledDevice, compile_device
from mlab.construct.ir import Submission
from mlab.construct.modify import apply_modification, mod_key, visible_params
from mlab.referee.modification import modified_value
from mlab.referee.theory_eval import run_theory
from mlab.sandbox.policies import ensure_learner_venv
from mlab.sim.runner import simulate
from observatory.scene import moving_parts

FPS = 30.0
# int16 counts per metre: +-6.5 m at 0.2 mm resolution.
POS_SCALE = 5000.0
SLICE_POINTS = 36
MOD_VALUES = 4


def _key(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:16]


class Baker:
    def __init__(self, root: Path, cache: Path):
        self.root = Path(root)
        self.cache = Path(cache)
        self._subs: dict[int, Submission] = {}
        self._devs: dict[tuple, CompiledDevice] = {}

    def submission(self, r: int) -> Submission | None:
        """The certified submission of round r (the attempt whose certificate passed)."""
        if r in self._subs:
            return self._subs[r]
        for cert in sorted((self.root / "referee" / "certificates").glob(f"r{r}_a*.json")):
            if json.loads(cert.read_text()).get("report", "").startswith("CERTIFIED"):
                path = self.root / "referee" / "submissions" / cert.name
                self._subs[r] = Submission.model_validate_json(path.read_text())
                return self._subs[r]
        return None

    def theta(self, r: int, label: str) -> dict | None:
        path = self.root / "referee" / "instances" / f"r{r}.json"
        return json.loads(path.read_text()).get(label) if path.exists() else None

    def device(
        self, r: int, label: str, mod: tuple[str, float] | None = None
    ) -> CompiledDevice | None:
        key = (r, label, mod)
        if key in self._devs:
            return self._devs[key]
        sub, theta = self.submission(r), self.theta(r, label)
        if sub is None or theta is None:
            return None
        ir = sub.device
        if mod is not None:
            m = next(x for x in sub.task.modifiable if mod_key(x) == mod[0])
            ir = apply_modification(ir, m, mod[1])
        self._devs[key] = compile_device(ir, theta)
        return self._devs[key]

    def replay(self, r: int, label: str, knobs: dict[str, float]) -> dict | None:
        sub, dev = self.submission(r), self.device(r, label)
        if sub is None or dev is None:
            return None
        cached = self._cache_get("replay", r, label, knobs)
        if cached is not None:
            return cached
        names = sorted(moving_parts(sub.device))
        bodies = [dev.part_body[n] for n in names]
        frames: list[np.ndarray] = []

        def grab(data: mujoco.MjData) -> None:
            frame = np.concatenate([data.xpos[bodies], data.xquat[bodies][:, [1, 2, 3, 0]]], axis=1)
            frames.append(frame)

        try:
            stop = simulate(dev, sub.task, knobs, early_stop=True)
            simulate(dev, sub.task, knobs, sample_hz=FPS, early_stop=False, on_sample=grab)
        except ValueError:
            return None
        arr = np.stack(frames) if frames else np.zeros((0, len(names), 7))
        q = np.empty_like(arr)
        q[..., :3] = np.round(arr[..., :3] * POS_SCALE)
        q[..., 3:] = np.round(arr[..., 3:] * 32767)
        q = np.clip(q, -32768, 32767).astype("<i2")
        out = {
            "fps": FPS,
            "parts": names,
            "frames": int(arr.shape[0]),
            "pos_scale": POS_SCALE,
            "data": base64.b64encode(q.tobytes()).decode(),
            "outcome": None if stop.outcome is None else [float(v) for v in stop.outcome],
            "status": stop.status,
            "t_outcome": float(stop.t_end),
        }
        self._cache_put(out, "replay", r, label, knobs)
        return out

    def curves(
        self,
        r: int,
        knobs_used: list[dict],
        theories: dict[str, str | None],
        knob_name: str | None = None,
    ) -> dict | None:
        """True outcome along one knob, the others at the learner's median setting, on both
        instances and on each declared modification, with each learner theory alongside.

        `knobs_used`: the learner's exam answers if any (they trace its controller), else its
        experiments; the default slice is the knob they vary most."""
        sub = self.submission(r)
        if sub is None or self.theta(r, "A") is None:
            return None
        cached = self._cache_get("curves", r, knobs_used, theories, knob_name)
        if cached is not None:
            return cached
        task = sub.task
        names = [k.name for k in task.knobs]
        if knobs_used:
            arr = np.array([[kn[n] for n in names] for kn in knobs_used])
            spread = arr.std(axis=0) / np.array([k.high - k.low for k in task.knobs])
            j = names.index(knob_name) if knob_name in names else int(np.argmax(spread))
            fixed = {n: float(np.median(arr[:, i])) for i, n in enumerate(names)}
        else:
            j = names.index(knob_name) if knob_name in names else 0
            fixed = {k.name: (k.low + k.high) / 2 for k in task.knobs}
        knob = task.knobs[j]
        xs = np.linspace(knob.low, knob.high, SLICE_POINTS).tolist()
        grid = [{**fixed, knob.name: x} for x in xs]
        vis = visible_params(sub.device, task)

        variants: list[dict] = [{"key": None, "value": None, "visible": vis}]
        for m in task.modifiable:
            key = mod_key(m)
            test = modified_value(m, vis[key])
            values = sorted(
                {
                    *np.linspace(m.low, m.high, MOD_VALUES).round(6).tolist(),
                    round(vis[key], 6),
                    round(test, 6),
                }
            )
            for v in values:
                variants.append(
                    {
                        "key": key,
                        "value": v,
                        "visible": {**vis, key: v},
                        "current": abs(v - vis[key]) < 1e-9,
                        "test": abs(v - test) < 1e-9,
                    }
                )

        python = str(ensure_learner_venv())
        for var in variants:
            mod = None if var["key"] is None else (var["key"], var["value"])
            var["truth"] = {}
            for label in ("A", "B"):
                dev = self.device(r, label, mod)
                var["truth"][label] = None if dev is None else [_outcome(dev, sub, g) for g in grid]
        queries = [{"knobs": g, "visible": var["visible"]} for var in variants for g in grid]
        for var in variants:
            var["theory"] = {}
        for label, code in theories.items():
            preds = run_theory(code, queries, python=python, sandboxed=True) if code else None
            for i, var in enumerate(variants):
                chunk = None if preds is None else preds[i * len(grid) : (i + 1) * len(grid)]
                var["theory"][label] = chunk
        out = {
            "knob": knob.name,
            "knobs": names,
            "xs": xs,
            "fixed": fixed,
            "variants": variants,
            "tolerance": task.tolerance,
            "goal_space": [[g.low, g.high] for g in task.goal_space],
        }
        self._cache_put(out, "curves", r, knobs_used, theories, knob_name)
        return out

    def _cache_path(self, *key) -> Path:
        return self.cache / "bake" / f"{key[0]}_{_key(*key)}.json"

    def _cache_get(self, *key) -> dict | None:
        path = self._cache_path(*key)
        if path.exists():
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                return None
        return None

    def _cache_put(self, value: dict, *key) -> None:
        path = self._cache_path(*key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(value))
        tmp.replace(path)


def _outcome(dev: CompiledDevice, sub: Submission, knobs: dict) -> list[float] | None:
    try:
        r = simulate(dev, sub.task, knobs, early_stop=True)
    except ValueError:
        return None
    return None if r.outcome is None else [float(v) for v in r.outcome]
