"""Device-agnostic scripted learners (baselines and controls).

They read only the task card and talk only to the LabAPI. Nothing here may depend on a
particular device (AGENTS.md red line 1).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
from scipy.stats import qmc

from mlab.agents.lab_api import LabAPI
from mlab.agents.learners.gp import GP

THEORY_TEMPLATE = '''\
"""Black-box surrogate: Gaussian process on knob values; ignores visible dimensions."""
import math

KNOBS = {knobs}
X = {x}
ALPHA = {alpha}
MEAN = {mean}
SCALE = {scale}
LS = {ls}


def _unit(knobs):
    return [(float(knobs[k]) - lo) / (hi - lo) for k, lo, hi in KNOBS]


def predict(knobs, visible):
    u = _unit(knobs)
    out = []
    for d in range(len(MEAN)):
        s = 0.0
        for xi, a in zip(X, ALPHA[d]):
            r2 = sum((p - q) ** 2 for p, q in zip(u, xi))
            s += a * math.exp(-0.5 * r2 / LS[d] ** 2)
        out.append(MEAN[d] + SCALE[d] * s)
    return out
'''


def _knob_bounds(card: dict) -> list[tuple[str, float, float]]:
    return [(k["name"], k["low"], k["high"]) for k in card["knobs"]]


def _to_knobs(card: dict, u: np.ndarray) -> dict[str, float]:
    return {n: float(lo + float(np.clip(ui, 0, 1)) * (hi - lo))
            for (n, lo, hi), ui in zip(_knob_bounds(card), u, strict=True)}


def _to_unit(card: dict, knobs: dict[str, float]) -> np.ndarray:
    return np.array([(knobs[n] - lo) / (hi - lo) for n, lo, hi in _knob_bounds(card)])


def _goal_mid(card: dict) -> list[float]:
    return [(lo + hi) / 2 for lo, hi in card["outcome"]["goal_space"]]


def interface_signature(card: dict) -> str:
    return json.dumps({"knobs": _knob_bounds(card), "outcome": card["outcome"]["kind"],
                       "part": card["outcome"]["part"], "axes": card["outcome"]["axes"]})


@dataclass
class Memory:
    """What a scripted learner keeps between rounds: raw data per interface signature."""

    data: dict[str, list[tuple[list[float], list[float]]]] = field(default_factory=dict)


class ScriptedAgent:
    """Wraps a scripted learner with its own memory; fork() gives an independent twin."""

    def __init__(self, impl, memory: Memory | None = None):
        self.impl = impl
        self.memory = memory if memory is not None else Memory()
        self.name = f"scripted-{impl.name}"

    def run(self, lab: LabAPI) -> None:
        self.impl.run(lab, self.memory)

    def fork(self) -> ScriptedAgent:
        twin = self.impl.fork() if hasattr(self.impl, "fork") else self.impl
        return ScriptedAgent(twin, Memory(data={k: list(v) for k, v in self.memory.data.items()}))


class NaiveLearner:
    """Floor baseline: no experiments, knob midpoints, constant theory."""

    name = "naive"

    def run(self, lab: LabAPI, memory: Memory | None = None) -> None:
        card = lab.card()
        mid = _to_knobs(card, np.full(len(card["knobs"]), 0.5))
        while lab.status()["phase"] == "pretest":
            lab.answer(mid)
        lab.finish_lab()
        const = _goal_mid(card)
        lab.submit_theory(f"def predict(knobs, visible):\n    return {const!r}\n", None)
        while lab.status()["phase"] == "exam":
            lab.answer(mid)
        lab.field_report([])


class SurrogateLearner:
    """Black-box baseline: space-filling then goal-directed active learning with a GP.

    memory_mode "prior": remembered data only informs the pretest; once this instance has
    its own data, only that is modelled (remembered data may come from a device instance with
    different unknowns). "pool" (ablation) keeps pooling remembered data into every model.
    """

    name = "surrogate"
    MIN_OWN_POINTS = 5

    def __init__(self, rng: np.random.Generator, use_memory: bool = True, memory_mode: str = "prior"):
        self.rng = rng
        self.use_memory = use_memory
        self.memory_mode = memory_mode

    def _fit(self, card: dict, xs: list, ys: list) -> list[GP] | None:
        if len(xs) < 3:
            return None
        x, y = np.array(xs), np.array(ys)
        noise = max(card["outcome"]["noise"], 1e-3)
        return [GP(x, y[:, d], noise) for d in range(y.shape[1])]

    def _predict(self, gps: list[GP] | None, card: dict, u: np.ndarray) -> tuple[list[float], float]:
        if gps is None:
            return _goal_mid(card), float("inf")
        mus, sds = zip(*(g.predict(u[None, :]) for g in gps), strict=True)
        return [float(m[0]) for m in mus], float(np.linalg.norm([s[0] for s in sds]))

    def _invert(self, gps: list[GP] | None, card: dict, goal: list[float]) -> dict[str, float]:
        d = len(card["knobs"])
        if gps is None:
            return _to_knobs(card, np.full(d, 0.5))
        cand = self.rng.uniform(size=(2048, d))
        mus = np.stack([g.predict(cand)[0] for g in gps], axis=1)
        sds = np.stack([g.predict(cand)[1] for g in gps], axis=1)
        score = np.linalg.norm(mus - np.asarray(goal), axis=1) + 0.5 * np.linalg.norm(sds, axis=1)
        return _to_knobs(card, cand[int(np.argmin(score))])

    def run(self, lab: LabAPI, memory: Memory | None = None) -> None:
        card = lab.card()
        d = len(card["knobs"])
        sig = interface_signature(card)
        prior = list(memory.data.get(sig, [])) if (memory is not None and self.use_memory) else []
        xs = [np.array(x) for x, _ in prior]
        ys = [list(y) for _, y in prior]
        gps = self._fit(card, xs, ys)
        while lab.status()["phase"] == "pretest":
            lab.answer(self._invert(gps, card, lab.current_goal()["goal"]))

        budget = card["protocol"]["budget"]
        design = qmc.LatinHypercube(d=d, seed=self.rng).random(max(2, budget // 2))
        lab_x: list[np.ndarray] = []
        lab_y: list[list[float]] = []
        goal_lo = np.array([g[0] for g in card["outcome"]["goal_space"]])
        goal_hi = np.array([g[1] for g in card["outcome"]["goal_space"]])
        step = 0

        def training() -> tuple[list, list]:
            if self.memory_mode == "pool" or len(lab_x) < self.MIN_OWN_POINTS:
                return xs + lab_x, ys + lab_y
            return lab_x, lab_y

        while lab.status()["phase"] == "lab" and lab.status()["experiments_used"] < budget:
            gps_now = self._fit(card, *training())
            if lab.status()["probe_due"]:
                knobs = lab.probe()["knobs"]
                pred, _ = self._predict(gps_now, card, _to_unit(card, knobs))
                obs = lab.probe_result(pred)
            else:
                if step < len(design):
                    u = design[step]
                elif gps_now is None:
                    u = self.rng.uniform(size=d)  # too few valid outcomes to model: keep exploring
                else:
                    cand = self.rng.uniform(size=(1024, d))
                    mus = np.stack([g.predict(cand)[0] for g in gps_now], axis=1)
                    sds = np.stack([g.predict(cand)[1] for g in gps_now], axis=1)
                    inside = np.all((mus >= goal_lo) & (mus <= goal_hi), axis=1)
                    util = np.linalg.norm(sds, axis=1) * np.where(inside, 1.0, 0.2)
                    u = cand[int(np.argmax(util))]
                step += 1
                knobs = _to_knobs(card, u)
                pred, _ = self._predict(gps_now, card, u)
                obs = lab.experiment(knobs, pred)
            if obs["outcome"] is not None and obs["status"] == "ok":
                lab_x.append(_to_unit(card, obs["knobs"]))
                lab_y.append(list(obs["outcome"]))
        lab.finish_lab()

        gps = self._fit(card, *training())
        lab.submit_theory(self._theory_code(card, gps), None)
        while lab.status()["phase"] == "exam":
            lab.answer(self._invert(gps, card, lab.current_goal()["goal"]))
        lab.field_report([])
        if memory is not None:
            memory.data[sig] = prior + [(x.tolist(), y) for x, y in zip(lab_x, lab_y, strict=True)]

    def fork(self) -> SurrogateLearner:
        return SurrogateLearner(np.random.default_rng(int(self.rng.integers(2**32))),
                                self.use_memory, self.memory_mode)

    def _theory_code(self, card: dict, gps: list[GP] | None) -> str:
        if gps is None:
            return f"def predict(knobs, visible):\n    return {_goal_mid(card)!r}\n"
        return THEORY_TEMPLATE.format(
            knobs=repr(_knob_bounds(card)),
            x=repr(gps[0].x.tolist()),
            alpha=repr([g.alpha.tolist() for g in gps]),
            mean=repr([g.mean for g in gps]),
            scale=repr([g.scale for g in gps]),
            ls=repr([g.ls for g in gps]),
        )
