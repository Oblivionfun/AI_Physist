"""Per-instance learning metrics, computed by the referee from ground truth only."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field

import numpy as np

from mlab.catalog.priors import Prior
from mlab.referee.session import LearnerSession
from mlab.referee.theory_eval import TheoryScore


@dataclass
class InstanceMetrics:
    label: str
    pretest_hits: int
    pretest_n: int
    exam_hits: int
    exam_n: int
    exam_miss_over_tol: list[float | None]
    exam_status: dict[str, int]
    experiments_used: int
    budget: int
    self_pred_err: list[tuple[int, float | None]]
    probe_pred_err: list[tuple[int, float | None]]
    theory: dict[str, dict] = field(default_factory=dict)
    belief: dict[str, dict] = field(default_factory=dict)
    tickets: list[dict] = field(default_factory=list)
    invalid: str | None = None
    outcome_kind_misses: int = 0

    @property
    def exam_rate(self) -> float:
        return self.exam_hits / self.exam_n if self.exam_n else 0.0

    @property
    def pretest_rate(self) -> float:
        return self.pretest_hits / self.pretest_n if self.pretest_n else 0.0

    def pred_trend(self) -> tuple[float | None, float | None]:
        errs = [e for _, e in self.self_pred_err if e is not None]
        if len(errs) < 6:
            return (None, None)
        third = max(1, len(errs) // 3)
        return (float(np.median(errs[:third])), float(np.median(errs[-third:])))

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(exam_rate=self.exam_rate, pretest_rate=self.pretest_rate,
                 pred_trend=self.pred_trend())
        return d


def _pred_err(pred: list[float] | None, truth: list[float] | None, tol: float) -> float | None:
    """None predicts no valid outcome: correct (0) when the run had none; a mismatch in kind
    has no distance and is counted separately (outcome_kind_misses)."""
    if pred is None or truth is None:
        return 0.0 if pred is None and truth is None else None
    return float(np.linalg.norm(np.asarray(pred) - np.asarray(truth))) / tol


def compute_metrics(label: str, session: LearnerSession, theory: list[TheoryScore],
                    priors: dict[str, Prior], true_theta: dict[str, float]) -> InstanceMetrics:
    tol = session.task.tolerance
    rec = session.record
    pre = [a for a in rec.attempts if a.phase == "pretest"]
    exam = [a for a in rec.attempts if a.phase == "exam"]
    misses = []
    for a in exam:
        misses.append(None if a.outcome is None
                      else float(np.linalg.norm(np.asarray(a.outcome) - np.asarray(a.goal))) / tol)
    exam_n = len(session.exam_goals)
    belief: dict[str, dict] = {}
    if rec.belief is not None:
        for key, entry in rec.belief.estimates.items():
            if key not in priors or key not in true_theta:
                continue
            p, truth = priors[key], true_theta[key]
            belief[key] = {
                "unit_error": abs(p.to_unit(min(max(entry.value, p.low), p.high)) - p.to_unit(truth)),
                "covered": bool(entry.low <= truth <= entry.high),
                "relative_error": abs(entry.value - truth) / abs(truth) if truth else None,
            }
    return InstanceMetrics(
        label=label,
        pretest_hits=sum(a.success for a in pre),
        pretest_n=len(session.pretest_goals),
        exam_hits=sum(a.success for a in exam),
        exam_n=exam_n,
        exam_miss_over_tol=misses,
        exam_status=dict(Counter(a.status for a in exam)),
        experiments_used=len(rec.lab),
        budget=session.task.budget,
        self_pred_err=[(r.index, _pred_err(r.prediction, r.true_outcome, tol))
                       for r in rec.lab if not r.probe],
        probe_pred_err=[(r.index, _pred_err(r.prediction, r.true_outcome, tol))
                        for r in rec.lab if r.probe],
        theory={s.name: {"hit_rate": s.hit_rate, "mean_abs_over_tol": s.mean_abs_over_tol,
                         "n": s.n, "answered": s.answered, "note": s.note,
                         "effect_over_tol": s.effect_over_tol, "discriminating": s.discriminating}
                for s in theory},
        belief=belief,
        tickets=[t.model_dump() for t in rec.tickets],
        outcome_kind_misses=sum((r.prediction is None) != (r.true_outcome is None) for r in rec.lab),
    )


def failure_tags(m: InstanceMetrics) -> list[str]:
    if m.invalid:
        return ["invalid_session"]
    tags = []
    if m.experiments_used >= m.budget:
        tags.append("budget_exhausted")
    if m.exam_n and m.exam_rate <= m.pretest_rate:
        tags.append("no_improvement_over_pretest")
    bad_status = sum(v for k, v in m.exam_status.items() if k != "ok")
    if bad_status:
        tags.append(f"exam_runs_not_ok:{bad_status}")
    ind = m.theory.get("in_distribution", {})
    ext = m.theory.get("extrapolation", {})
    if ind.get("hit_rate") is not None and ind["hit_rate"] >= 0.7:
        if ext.get("hit_rate") is not None and ext["hit_rate"] < 0.5:
            tags.append("extrapolation_fail")
        for name, s in m.theory.items():
            if (name.startswith("modified") and s.get("discriminating", True)
                    and s.get("hit_rate") is not None and s["hit_rate"] < 0.5):
                tags.append("modification_fail")
                break
    elif ind.get("hit_rate") is not None:
        tags.append("theory_inaccurate")
    if m.theory and all(s.get("answered", 0) == 0 for s in m.theory.values() if s.get("n")):
        tags.append("theory_not_executable")
    return tags
