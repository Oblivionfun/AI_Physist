"""One learner instance: the protocol state machine enforced by the referee.

pretest -> lab -> theory -> exam -> report -> done

Every lab experiment needs a prediction first; every `probe_every`-th experiment is chosen
by the referee. Pretest and exam results are withheld until the session ends, so they
cannot be used as free experiments.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from mlab.construct.compile import CompiledDevice
from mlab.construct.ir import Submission
from mlab.referee.manual import EXAM_GOALS, PRETEST_GOALS, PROBE_EVERY, TRACE_HZ
from mlab.referee.oracle import sobol_points, unit_to_knobs
from mlab.referee.protocol import Belief, ExperimentObs, FieldTicket, TaskCard
from mlab.sim.observe import observe
from mlab.sim.runner import knob_values, simulate, succeeded

PHASES = ("pretest", "lab", "theory", "exam", "report", "done")
MAX_THEORY_BYTES = 200_000


class ProtocolError(Exception):
    pass


@dataclass
class Attempt:
    phase: str
    index: int
    goal: list[float]
    knobs: dict[str, float]
    outcome: list[float] | None
    observed: list[float] | None
    status: str
    success: bool


@dataclass
class LabRecord:
    index: int
    probe: bool
    knobs: dict[str, float]
    prediction: list[float]
    true_outcome: list[float] | None
    observed_outcome: list[float] | None
    status: str


@dataclass
class SessionRecord:
    attempts: list[Attempt] = field(default_factory=list)
    lab: list[LabRecord] = field(default_factory=list)
    theory_code: str | None = None
    belief: Belief | None = None
    tickets: list[FieldTicket] = field(default_factory=list)
    calls: list[dict] = field(default_factory=list)


class LearnerSession:
    def __init__(
        self,
        sub: Submission,
        dev: CompiledDevice,
        card: TaskCard,
        rng: np.random.Generator,
        act_noise: float = 0.005,
        observation_dev: CompiledDevice | None = None,
    ):
        """`observation_dev` (negative control only): lab observations come from a different
        instance than the one examined, so learning from them should not help."""
        self.sub = sub
        self.task = sub.task
        self.dev = dev
        self.obs_dev = observation_dev or dev
        self.card = card
        self.rng = rng
        self.act_noise = act_noise
        self.phase = "pretest"
        self.record = SessionRecord()
        d = len(self.task.knobs)
        lo = np.array([g.low for g in self.task.goal_space])
        hi = np.array([g.high for g in self.task.goal_space])
        self.pretest_goals = (lo + rng.uniform(size=(PRETEST_GOALS, len(lo))) * (hi - lo)).tolist()
        self.exam_goals = (lo + rng.uniform(size=(EXAM_GOALS, len(lo))) * (hi - lo)).tolist()
        n_probes = self.task.budget // PROBE_EVERY
        self.probe_knobs = [unit_to_knobs(self.task, u) for u in sobol_points(d, max(1, n_probes), rng)]
        self.goal_cursor = 0
        self.pending_probe: dict[str, float] | None = None

    def _log(self, call: str, **kw) -> None:
        self.record.calls.append({"call": call, "phase": self.phase, **kw})

    def _require(self, *phases: str) -> None:
        if self.phase not in phases:
            raise ProtocolError(f"not allowed in phase '{self.phase}' (allowed: {', '.join(phases)})")

    def status(self) -> dict:
        used = len(self.record.lab)
        info = {
            "phase": self.phase,
            "experiments_used": used,
            "budget": self.task.budget,
            "probe_due": self._probe_due(),
        }
        if self.phase in ("pretest", "exam"):
            goals = self.pretest_goals if self.phase == "pretest" else self.exam_goals
            info["goals_answered"] = self.goal_cursor
            info["goals_total"] = len(goals)
        return info

    def _probe_due(self) -> bool:
        return self.phase == "lab" and (len(self.record.lab) + 1) % PROBE_EVERY == 0 and (
            len(self.record.lab) < self.task.budget
        )

    def current_goal(self) -> dict:
        self._require("pretest", "exam")
        goals = self.pretest_goals if self.phase == "pretest" else self.exam_goals
        return {"phase": self.phase, "index": self.goal_cursor, "goal": goals[self.goal_cursor],
                "remaining": len(goals) - self.goal_cursor}

    def answer(self, knobs: dict[str, float]) -> dict:
        self._require("pretest", "exam")
        goals = self.pretest_goals if self.phase == "pretest" else self.exam_goals
        try:
            values = knob_values(self.task, knobs)
        except ValueError as exc:
            raise ProtocolError(str(exc)) from None
        goal = np.asarray(goals[self.goal_cursor])
        r = simulate(self.dev, self.task, values, rng=self.rng, act_noise=self.act_noise)
        ok = succeeded(r, goal, self.task.tolerance)
        obs = observe(r, self.dev.ir, self.task, self.rng)
        self.record.attempts.append(Attempt(
            phase=self.phase, index=self.goal_cursor, goal=goal.tolist(), knobs=values,
            outcome=None if r.outcome is None else r.outcome.tolist(), observed=obs.outcome,
            status=r.status, success=ok,
        ))
        self._log("answer", index=self.goal_cursor, knobs=values)
        self.goal_cursor += 1
        if self.goal_cursor >= len(goals):
            self.goal_cursor = 0
            self.phase = "lab" if self.phase == "pretest" else "report"
        return {"recorded": True, "next_phase": self.phase,
                "note": "results are revealed when the session ends"}

    def _run_experiment(self, values: dict[str, float], prediction: list[float], probe: bool) -> dict:
        dim = len(self.task.goal_space)
        if len(prediction) != dim or not all(np.isfinite(prediction)):
            raise ProtocolError(f"prediction must be {dim} finite number(s)")
        r = simulate(self.obs_dev, self.task, values, rng=self.rng, act_noise=self.act_noise)
        obs = observe(r, self.obs_dev.ir, self.task, self.rng)
        step = max(1, round(50.0 / TRACE_HZ))
        index = len(self.record.lab)
        self.record.lab.append(LabRecord(
            index=index, probe=probe, knobs=values, prediction=[float(p) for p in prediction],
            true_outcome=None if r.outcome is None else r.outcome.tolist(),
            observed_outcome=obs.outcome, status=r.status,
        ))
        self._log("experiment", index=index, probe=probe, knobs=values, prediction=prediction)
        return ExperimentObs(
            index=index, probe=probe, knobs=values, prediction=[float(p) for p in prediction],
            outcome=obs.outcome, status=obs.status, times=obs.times[::step],
            traces={k: v[::step] for k, v in obs.traces.items()},
        ).model_dump()

    def experiment(self, knobs: dict[str, float], prediction: list[float]) -> dict:
        self._require("lab")
        if len(self.record.lab) >= self.task.budget:
            raise ProtocolError("experiment budget exhausted; call finish_lab()")
        if self._probe_due():
            raise ProtocolError("a referee probe is due: call probe() to get its knobs, then "
                                "probe_result(prediction)")
        try:
            values = knob_values(self.task, knobs)
        except ValueError as exc:
            raise ProtocolError(str(exc)) from None
        return self._run_experiment(values, prediction, probe=False)

    def probe(self) -> dict:
        self._require("lab")
        if not self._probe_due():
            raise ProtocolError("no probe is due")
        if self.pending_probe is None:
            self.pending_probe = self.probe_knobs[(len(self.record.lab) // PROBE_EVERY) % len(self.probe_knobs)]
        return {"knobs": self.pending_probe}

    def probe_result(self, prediction: list[float]) -> dict:
        self._require("lab")
        if self.pending_probe is None:
            raise ProtocolError("call probe() first")
        knobs, self.pending_probe = self.pending_probe, None
        return self._run_experiment(knobs, prediction, probe=True)

    def finish_lab(self) -> dict:
        self._require("lab")
        if self.pending_probe is not None:
            raise ProtocolError("answer the pending probe first")
        self.phase = "theory"
        self._log("finish_lab", used=len(self.record.lab))
        return {"next_phase": self.phase}

    def submit_theory(self, code: str, belief: dict | None) -> dict:
        self._require("theory")
        if len(code.encode()) > MAX_THEORY_BYTES:
            raise ProtocolError(f"predict.py larger than {MAX_THEORY_BYTES} bytes")
        if "def predict" not in code:
            raise ProtocolError("predict.py must define predict(knobs, visible)")
        self.record.theory_code = code
        self.record.belief = Belief.model_validate(belief or {})
        self.phase = "exam"
        self.goal_cursor = 0
        self._log("submit_theory", bytes=len(code))
        return {"next_phase": self.phase}

    def field_report(self, tickets: list[dict]) -> dict:
        self._require("report")
        self.record.tickets = [FieldTicket.model_validate(t) for t in tickets[:10]]
        self.phase = "done"
        self._log("field_report", n=len(self.record.tickets))
        return {"next_phase": self.phase, "results": self.results()}

    def results(self) -> dict:
        """Revealed to the learner only once the session is done."""
        self._require("done")
        return {
            phase: [
                {"goal": a.goal, "knobs": a.knobs, "observed_outcome": a.observed,
                 "status": a.status, "success": a.success}
                for a in self.record.attempts if a.phase == phase
            ]
            for phase in ("pretest", "exam")
        }
