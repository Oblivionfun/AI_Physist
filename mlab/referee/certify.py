"""Solvability certificates C0-C3 (see docs/decisions.md D-007).

C0  physical validity: construction rules, numerical stability, no passive energy gain, and
    timestep convergence of the actions that solve the task (checked after C1, because
    chaotic regions elsewhere in knob space are legitimate physics, not artefacts).
C1  existence: the privileged oracle hits goals under actuation noise.
C1b robustness: oracle solutions survive +-1 % knob perturbations (PHYRE "stable" solves).
C2  necessity: prior-nominal parameters and the single best fixed action both fail.
C3  identifiability: (a) posterior predictive uncertainty after a budget of probes is below
    half the tolerance; (b) a gray-box reference learner succeeds within budget; (c) every
    declared modifiable dimension moves outcomes enough to separate physical models from curve
    fits that ignore it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from mlab.catalog.priors import Prior
from mlab.construct.checks import check_device, check_task
from mlab.construct.compile import CompiledDevice, compile_device
from mlab.construct.ir import PhaseIR, Submission, TaskIR
from mlab.construct.modify import mod_key, visible_params
from mlab.referee.modification import DISCRIMINATION, modification_effect, modified_value
from mlab.referee.oracle import GenericOracle, knobs_to_unit, sobol_points, unit_to_knobs, usable
from mlab.referee.reference import FitBudget, gray_box_fit
from mlab.referee.stats import decide, point_decision, wilson
from mlab.referee.theta import (
    hidden_priors,
    instance_theta,
    nominal_instance,
    prior_instance,
    to_unit,
    with_unit,
)
from mlab.sim.observe import feature_vector
from mlab.sim.runner import simulate, succeeded

THRESHOLDS = {
    "C1": 0.8,
    "C1b": 0.6,
    "C2_nominal": 0.3,
    "C2_fixed": 0.3,
    "C3_predictive": 0.5,
    "C3_reference": 0.7,
    "C3_modification": DISCRIMINATION,
    "C0_energy": 0.02,
    "C0_dt": 1.0,
}


@dataclass(frozen=True)
class CertProfile:
    n_instances: int = 3
    n_goals: int = 8
    n_reps: int = 2
    extra_goal_rounds: int = 2
    table_per_dim: int = 48
    refine_evals: int = 40
    act_noise: float = 0.005
    robust_step: float = 0.01
    fisher_probes: int = 16
    fisher_step: float = 0.05
    reference_instances: int = 2
    reference_extra_fits: int = 2
    reference_max_keys: int = 4
    reference_fit: FitBudget = field(default_factory=FitBudget)
    coverage_goals: int = 256
    physics_samples: int = 3
    prior_draws: int = 24
    goals_per_draw: int = 4


FULL = CertProfile()
FAST = CertProfile(
    n_instances=2,
    n_goals=6,
    n_reps=1,
    extra_goal_rounds=1,
    table_per_dim=24,
    refine_evals=20,
    fisher_probes=8,
    reference_instances=1,
    reference_extra_fits=1,
    coverage_goals=256,
    physics_samples=2,
    prior_draws=16,
)
TEST = CertProfile(
    n_instances=2,
    n_goals=4,
    n_reps=1,
    extra_goal_rounds=0,
    table_per_dim=16,
    refine_evals=15,
    fisher_probes=6,
    reference_instances=1,
    reference_extra_fits=0,
    reference_max_keys=2,
    reference_fit=FitBudget(search_points=8, search_subset=6, fit_subset=8, refine_starts=1,
                            refine_evals=12),
    coverage_goals=256,
    physics_samples=1,
    prior_draws=8,
)


@dataclass
class Verdict:
    code: str
    title: str
    decision: str
    value: float | None
    threshold: float | None
    detail: str

    @property
    def passed(self) -> bool:
        return self.decision == "pass"

    def line(self) -> str:
        val = "" if self.value is None else f" value={self.value:.3f}"
        thr = "" if self.threshold is None else f" threshold={self.threshold:g}"
        return f"{self.code} {self.title}: {self.decision.upper()}{val}{thr}. {self.detail}"


@dataclass
class Certificate:
    verdicts: list[Verdict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    seconds: float = 0.0

    @property
    def passed(self) -> bool:
        return bool(self.verdicts) and all(v.passed for v in self.verdicts)

    @property
    def first_failure(self) -> Verdict | None:
        return next((v for v in self.verdicts if not v.passed), None)

    def report(self) -> str:
        head = "CERTIFIED" if self.passed else "REJECTED"
        return "\n".join([head] + [v.line() for v in self.verdicts])


def passive_task(task: TaskIR) -> TaskIR:
    phases = [PhaseIR(duration=p.duration, ctrl={}, release=p.release) for p in task.phases]
    return task.model_copy(update={"phases": phases})


def _goals(task: TaskIR, n: int, rng: np.random.Generator) -> np.ndarray:
    lo = np.array([g.low for g in task.goal_space])
    hi = np.array([g.high for g in task.goal_space])
    return lo + rng.uniform(size=(n, len(lo))) * (hi - lo)


class Certifier:
    def __init__(self, submission: Submission, world: dict[str, float], rng: np.random.Generator,
                 profile: CertProfile = FULL):
        self.sub = submission
        self.device = submission.device
        self.task = submission.task
        self.world = world
        self.rng = rng
        self.p = profile
        self.priors: dict[str, Prior] = hidden_priors(self.device)
        self.cert = Certificate()
        self.sims = 0

    def _add(self, *args) -> Verdict:
        v = Verdict(*args)
        self.cert.verdicts.append(v)
        return v

    def run(self, stop_on_fail: bool = True) -> Certificate:
        t0 = time.time()
        try:
            self._run(stop_on_fail)
        finally:
            self.cert.seconds = time.time() - t0
            self.cert.stats["simulations"] = self.sims
        return self.cert

    def _run(self, stop_on_fail: bool) -> None:
        issues, _ = check_device(self.device)
        issues += check_task(self.device, self.task)
        if issues:
            self._add("C0", "construction rules", "fail", float(len(issues)), 0.0,
                      "; ".join(str(i) for i in issues))
            return
        self._add("C0", "construction rules", "pass", None, None, "all construction checks passed")

        self.instances = [instance_theta(self.world, self.device, self.rng)
                          for _ in range(self.p.n_instances)]
        self.devs = [compile_device(self.device, th) for th in self.instances]
        self.oracles = [
            GenericOracle(d, self.task, self.rng, self.p.table_per_dim, self.p.refine_evals)
            for d in self.devs
        ]
        steps = [self._c0_physics, self._c1_existence, self._c0_timestep, self._c1b_robustness,
                 self._c2_nominal, self._c2_fixed, self._c3_modification, self._c3_predictive,
                 self._c3_reference]
        for step in steps:
            verdict = step()
            if stop_on_fail and not verdict.passed:
                break
        self.sims += sum(o.sim_count for o in self.oracles)

    def _c0_physics(self) -> Verdict:
        unstable = max(o.unstable_fraction() for o in self.oracles)
        if unstable > 0:
            return self._add("C0", "numerical stability", "fail", unstable, 0.0,
                             f"{unstable:.0%} of sampled actions made the simulation diverge; "
                             "check for very light parts, extreme stiffness or tiny clearances")
        passive = passive_task(self.task)
        worst_gain = 0.0
        for dev in self.devs:
            for u in self.rng.uniform(size=(self.p.physics_samples, len(self.task.knobs))):
                r = simulate(dev, passive, unit_to_knobs(self.task, u), early_stop=False)
                self.sims += 1
                total = r.energy[:, 0] + r.energy[:, 1]
                scale = max(float(np.max(r.energy[:, 1])), 0.01)
                worst_gain = max(worst_gain, (float(np.max(total)) - float(total[0])) / scale)
        if worst_gain > THRESHOLDS["C0_energy"]:
            return self._add("C0", "passive energy", "fail", worst_gain, THRESHOLDS["C0_energy"],
                             "with all motors off the mechanical energy increased; the device "
                             "creates energy, which is not physical")
        return self._add("C0", "physics", "pass", worst_gain, THRESHOLDS["C0_energy"],
                         f"stable for all sampled actions; passive energy gain {worst_gain:.3%} of "
                         "peak kinetic energy")

    def _c0_timestep(self) -> Verdict:
        worst, mismatch = 0.0, False
        for dev, sols in zip(self.devs, self.solutions, strict=True):
            for _, knobs in sols[: self.p.physics_samples]:
                a = simulate(dev, self.task, knobs)
                b = simulate(dev, self.task, knobs, timestep=dev.model.opt.timestep / 2)
                self.sims += 2
                if usable(a.status, a.outcome) != usable(b.status, b.outcome):
                    mismatch = True
                elif usable(a.status, a.outcome):
                    worst = max(worst, float(np.linalg.norm(a.outcome - b.outcome)))
        ratio = worst / self.task.tolerance
        decision = "fail" if mismatch or ratio > THRESHOLDS["C0_dt"] else "pass"
        detail = f"halving the timestep moves solving outcomes by {ratio:.2f} x tolerance"
        if decision == "fail":
            detail += ("; the solution relies on numerical artefacts (typically violent impacts, "
                       "tumbling, or near-singular contacts): make the relevant motion gentler")
        return self._add("C0", "timestep convergence", decision, ratio, THRESHOLDS["C0_dt"], detail)

    def _eval(self, dev: CompiledDevice, knobs: dict, goal: np.ndarray, reps: int) -> int:
        hits = 0
        for _ in range(reps):
            r = simulate(dev, self.task, knobs, rng=self.rng, act_noise=self.p.act_noise)
            hits += succeeded(r, goal, self.task.tolerance)
        self.sims += reps
        return hits

    def _c1_existence(self) -> Verdict:
        self.solutions: list[list[tuple[np.ndarray, dict]]] = [[] for _ in self.devs]
        k = n = 0
        decision = "gray"
        for round_i in range(1 + self.p.extra_goal_rounds):
            for i, (dev, oracle) in enumerate(zip(self.devs, self.oracles, strict=True)):
                for goal in _goals(self.task, self.p.n_goals, self.rng):
                    knobs = oracle.solve(goal)
                    self.solutions[i].append((goal, knobs))
                    k += self._eval(dev, knobs, goal, self.p.n_reps)
                    n += self.p.n_reps
            decision = decide(k, n, THRESHOLDS["C1"], at_least=True)
            if decision != "gray":
                break
        if decision == "gray":
            decision = point_decision(k, n, THRESHOLDS["C1"], at_least=True)
        lo, hi = wilson(k, n)
        self.cert.stats["oracle_success"] = k / n
        detail = (f"privileged oracle hit {k}/{n} goals under actuation noise "
                  f"(95% CI {lo:.2f}-{hi:.2f})")
        if decision == "fail":
            misses = [g for sols in self.solutions for g, _ in sols][:3]
            detail += ("; some goals are unreachable for parts of the prior, e.g. goals "
                       f"{[np.round(g, 3).tolist() for g in misses]}. Shrink the goal space, widen "
                       "the knob ranges, or narrow the hidden priors")
        return self._add("C1", "existence", decision, k / n, THRESHOLDS["C1"], detail)

    def _c1b_robustness(self) -> Verdict:
        k = n = 0
        step = self.p.robust_step
        for dev, sols in zip(self.devs, self.solutions, strict=True):
            for goal, knobs in sols:
                r = simulate(dev, self.task, knobs)
                self.sims += 1
                if not succeeded(r, goal, self.task.tolerance):
                    continue
                u = knobs_to_unit(self.task, knobs)
                for j in range(len(u)):
                    for sign in (-1, 1):
                        uu = u.copy()
                        uu[j] = np.clip(uu[j] + sign * step, 0, 1)
                        rr = simulate(dev, self.task, unit_to_knobs(self.task, uu))
                        self.sims += 1
                        k += succeeded(rr, goal, self.task.tolerance)
                        n += 1
        if n == 0:
            return self._add("C1b", "robustness", "fail", 0.0, THRESHOLDS["C1b"],
                             "no noise-free oracle solution to perturb")
        decision = point_decision(k, n, THRESHOLDS["C1b"], at_least=True)
        return self._add("C1b", "robustness", decision, k / n, THRESHOLDS["C1b"],
                         f"{k}/{n} neighbours (+-{step:.0%} of each knob range) still succeed"
                         + ("" if decision == "pass" else "; the task is knife-edge: enlarge the "
                            "tolerance or make the outcome less sensitive to the knobs"))

    def _c2_nominal(self) -> Verdict:
        """Necessity is a property of the design, so it is judged over the prior: every
        relevant unknown is redrawn. The run's own world is reported separately."""
        nominal = nominal_instance(self.device)
        oracle = GenericOracle(compile_device(self.device, nominal), self.task, self.rng,
                               self.p.table_per_dim, self.p.refine_evals)
        k = n = 0
        for _ in range(self.p.prior_draws):
            dev = compile_device(self.device, prior_instance(self.world, self.device, self.rng))
            for goal in _goals(self.task, self.p.goals_per_draw, self.rng):
                k += self._eval(dev, oracle.solve(goal), goal, 1)
                n += 1
        run_k = run_n = 0
        for dev, sols in zip(self.devs, self.solutions, strict=True):
            for goal, _ in sols:
                run_k += self._eval(dev, oracle.solve(goal), goal, 1)
                run_n += 1
        self.sims += oracle.sim_count
        decision = decide(k, n, THRESHOLDS["C2_nominal"], at_least=False)
        borderline = decision == "gray"
        if borderline:
            decision = point_decision(k, n, THRESHOLDS["C2_nominal"], at_least=False)
        lo, hi = wilson(k, n)
        self.cert.stats["nominal_success"] = k / n
        self.cert.stats["nominal_success_this_world"] = run_k / run_n
        return self._add("C2", "necessity (nominal parameters)", decision, k / n,
                         THRESHOLDS["C2_nominal"],
                         f"over the prior, solving with prior-centre parameters hits {k}/{n} goals "
                         f"(95% CI {lo:.2f}-{hi:.2f}; in this run's world: {run_k}/{run_n})"
                         + (" BORDERLINE: the interval straddles the threshold, so the referee's "
                            "decision can go either way; add margin" if borderline else "")
                         + ("" if decision == "pass" else "; the hidden quantities barely matter, "
                            "so no learning is needed: make the outcome depend on them more"))

    def _c2_fixed(self) -> Verdict:
        goals = _goals(self.task, self.p.coverage_goals, self.rng)
        cover = float(np.mean([o.fixed_action_coverage(goals) for o in self.oracles]))
        decision = "pass" if cover <= THRESHOLDS["C2_fixed"] else "fail"
        self.cert.stats["fixed_action_coverage"] = cover
        return self._add("C2", "necessity (single fixed action)", decision, cover,
                         THRESHOLDS["C2_fixed"],
                         f"the best single action reaches {cover:.0%} of goals"
                         + ("" if decision == "pass" else "; widen the goal space or tighten the "
                            "tolerance so different goals need different actions"))

    def _feature_values(self, theta: dict, knob_list: list[dict], outcome_only: bool):
        dev = compile_device(self.device, theta)
        vals, sigs, masks = [], [], []
        for knobs in knob_list:
            r = simulate(dev, self.task, knobs)
            v, s, m = feature_vector(r.times, r.traces, r.outcome, r.status, self.device, self.task)
            if outcome_only:
                dim = len(self.task.goal_space)
                v, s, m = v[:dim], s[:dim], m[:dim]
            vals.append(v)
            sigs.append(s)
            masks.append(m)
        self.sims += len(knob_list)
        return np.concatenate(vals), np.concatenate(sigs), np.concatenate(masks)

    def _jacobian(self, theta: dict, keys: list[str], knob_list: list[dict], outcome_only: bool):
        sub = {k: self.priors[k] for k in keys}
        u0 = to_unit(theta, sub)
        h = self.p.fisher_step
        cols = []
        sigma = None
        for i in range(len(keys)):
            up, dn = u0.copy(), u0.copy()
            up[i] = min(1.0, u0[i] + h)
            dn[i] = max(0.0, u0[i] - h)
            vp, sp, mp = self._feature_values(with_unit(theta, sub, up), knob_list, outcome_only)
            vm, _, mm = self._feature_values(with_unit(theta, sub, dn), knob_list, outcome_only)
            sigma = sp
            cols.append(np.where(mp & mm, (vp - vm) / (up[i] - dn[i]), 0.0))
        return np.stack(cols, axis=1), sigma

    def _c3_predictive(self) -> Verdict:
        keys = list(self.priors)
        dev0 = self.devs[0]
        theta = dev0.theta
        d = len(self.task.knobs)
        probes = [unit_to_knobs(self.task, u) for u in sobol_points(d, self.p.fisher_probes, self.rng)]
        jac, sigma = self._jacobian(theta, keys, probes, outcome_only=False)
        jw = jac / sigma[:, None]
        fim = jw.T @ jw * (self.task.budget / len(probes))
        cov = np.linalg.inv(fim + 12.0 * np.eye(len(keys)))
        goal_knobs = [kn for _, kn in self.solutions[0]][: self.p.n_goals]
        jo, _ = self._jacobian(theta, keys, goal_knobs, outcome_only=True)
        dim = len(self.task.goal_space)
        stds = []
        for g in range(len(goal_knobs)):
            jg = jo[g * dim : (g + 1) * dim]
            stds.append(float(np.sqrt(np.trace(jg @ cov @ jg.T))))
        ratio = float(np.median(stds)) / self.task.tolerance
        relevance = np.sqrt(np.diag(fim))
        order = np.argsort(-relevance)
        self.relevant = [keys[i] for i in order if relevance[i] >= 0.02 * relevance[order[0]]]
        self.relevant = self.relevant[: self.p.reference_max_keys]
        prior_spread = []
        for g in range(len(goal_knobs)):
            jg = jo[g * dim : (g + 1) * dim]
            prior_spread.append(float(np.sqrt(np.trace(jg @ jg.T) / 12.0)))
        self.cert.stats.update(
            predictive_std_over_tol=ratio,
            prior_std_over_tol=float(np.median(prior_spread)) / self.task.tolerance,
            relevant_parameters=self.relevant,
        )
        decision = "pass" if ratio <= THRESHOLDS["C3_predictive"] else "fail"
        return self._add("C3", "identifiability (posterior predictive)", decision, ratio,
                         THRESHOLDS["C3_predictive"],
                         f"after {self.task.budget} experiments the outcome uncertainty is "
                         f"{ratio:.2f} x tolerance (before experiments: "
                         f"{self.cert.stats['prior_std_over_tol']:.2f} x)"
                         + ("" if decision == "pass" else "; the interface does not reveal the "
                            "hidden quantities well enough: add informative sensors, lower their "
                            "noise, or raise the budget"))

    def _c3_modification(self) -> Verdict:
        thr = THRESHOLDS["C3_modification"]
        if not self.task.modifiable:
            return self._add("C3", "modification test", "pass", None, thr,
                             "no modifiable dimensions declared: theories will not be tested on "
                             "modified devices")
        effects = modification_effect(self.sub, self.devs[0], self.rng)
        self.sims += 6 * (1 + len(effects))
        self.cert.stats["modification_effect_over_tol"] = effects
        vis = visible_params(self.device, self.task)
        tested = {mod_key(m): modified_value(m, vis[mod_key(m)]) for m in self.task.modifiable}
        inert = {k: v for k, v in effects.items() if v is None or v < thr}
        known = [v for v in effects.values() if v is not None]
        worst = min(known) if known else None
        if inert:
            parts = [f"'{k}' at its tested value {tested[k]:.4g} "
                     + ("gives no valid outcome" if v is None else f"moves outcomes by {v:.2f} x tolerance")
                     for k, v in inert.items()]
            return self._add("C3", "modification test", "fail", worst, thr,
                             "; ".join(parts) + ": a theory that ignores the modification would "
                             "score as well as one that models it. The referee tests each dimension "
                             "80% of the way to its farther bound; choose a range where it stays "
                             "consequential there, or drop it")
        return self._add("C3", "modification test", "pass", worst, thr,
                         f"every modifiable dimension moves outcomes by at least {worst:.2f} x "
                         "tolerance at its tested value")

    def _reference_fit(self, dev: CompiledDevice, nominal: dict[str, float]) -> tuple[int, int, dict]:
        """One independent gray-box learner: its own experiments, fit, and exam goals."""
        base = dict(dev.theta)
        for key in self.priors:
            base[key] = nominal[key]
        fit = gray_box_fit(dev, self.task, self.priors, self.relevant, base, self.rng,
                           self.p.act_noise, self.task.budget, self.p.reference_fit)
        self.sims += fit.sims
        oracle = GenericOracle(compile_device(self.device, fit.theta_hat), self.task, self.rng,
                               self.p.table_per_dim, self.p.refine_evals)
        goals = _goals(self.task, self.p.n_goals, self.rng)
        hits = sum(self._eval(dev, oracle.solve(goal), goal, 1) for goal in goals)
        self.sims += oracle.sim_count
        return hits, len(goals), fit.unit_error

    def _c3_reference(self) -> Verdict:
        """Planned fits first; while the pooled result is inconclusive (its Wilson interval
        straddles the threshold), add independent fits up to the profile's cap (D-020)."""
        thr = THRESHOLDS["C3_reference"]
        nominal = nominal_instance(self.device)
        planned = min(self.p.reference_instances, len(self.devs))
        k = n = 0
        errors, per_fit = [], []
        decision = "gray"
        while len(per_fit) < planned or (
                decision == "gray" and len(per_fit) < planned + self.p.reference_extra_fits):
            hits, m, err = self._reference_fit(self.devs[len(per_fit) % len(self.devs)], nominal)
            per_fit.append(f"{hits}/{m}")
            errors.append(err)
            k, n = k + hits, n + m
            if len(per_fit) >= planned:
                decision = decide(k, n, thr, at_least=True)
        extra = len(per_fit) - planned
        if decision == "gray":
            decision = point_decision(k, n, thr, at_least=True)
        self.cert.stats["reference_success"] = k / n
        self.cert.stats["reference_fit_hits"] = per_fit
        self.cert.stats["reference_unit_error"] = errors
        return self._add("C3", "learnability (gray-box reference learner)", decision, k / n, thr,
                         f"a learner that knows the structure but not the values, using only the "
                         f"public interface and {self.task.budget} experiments, hit {k}/{n} goals "
                         f"(independent fits: {', '.join(per_fit)}"
                         + (f"; {extra} added because the result was inconclusive" if extra else "")
                         + "; goals within one fit share its errors)")


def certify(submission: Submission, world: dict[str, float], rng: np.random.Generator,
            profile: CertProfile = FULL, stop_on_fail: bool = True) -> Certificate:
    return Certifier(submission, world, rng, profile).run(stop_on_fail)
