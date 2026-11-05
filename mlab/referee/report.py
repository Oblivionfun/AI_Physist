"""Round report for the builder (channel 4): aggregates only, never learner transcripts,
notebooks or code."""

from __future__ import annotations

from pydantic import BaseModel

from mlab.referee.certify import Certificate
from mlab.referee.metrics import InstanceMetrics, failure_tags

TARGET_BAND = (0.3, 0.8)


class InstanceSummary(BaseModel):
    label: str
    pretest_success: float
    exam_success: float
    experiments_used: int
    budget: int
    prediction_error_first_vs_last: tuple[float | None, float | None]
    probe_errors_over_tol: list[float | None]
    theory_hit_rates: dict[str, float | None]
    failure_tags: list[str]


class RoundReport(BaseModel):
    round: int
    device_version: int
    certificate: list[str]
    reference_learner_success: float | None
    oracle_success: float | None
    instances: list[InstanceSummary]
    learnability: float
    swap_test: dict[str, float | None | str]
    old_theory_on_new_device: float | None
    controls: dict[str, float | None | dict] = {}
    tickets: list[dict]
    guidance: str

    def text(self) -> str:
        lines = [f"Round {self.round} report (device v{self.device_version})"]
        lines += ["Certificate:"] + [f"  {c}" for c in self.certificate]
        for s in self.instances:
            lines.append(
                f"Instance {s.label}: pretest {s.pretest_success:.0%}, exam {s.exam_success:.0%}, "
                f"experiments {s.experiments_used}/{s.budget}, prediction error first->last "
                f"{s.prediction_error_first_vs_last}, theory hit rates {s.theory_hit_rates}, "
                f"tags {s.failure_tags}"
            )
        lines.append(f"Learnability p(1-p) of exam success: {self.learnability:.3f}")
        lines.append(f"Swap test (theory of one instance applied to its twin): {self.swap_test}")
        if self.old_theory_on_new_device is not None:
            lines.append(f"Previous round's theory on this device, hit rate: "
                         f"{self.old_theory_on_new_device:.0%}")
        if self.controls:
            lines.append(f"Controls: {self.controls}")
        for t in self.tickets:
            lines.append(f"Ticket [{t['category']}]: {t['text']}")
        lines.append(self.guidance)
        return "\n".join(lines)


def guidance(exam_rate: float, pretest_rate: float, reference: float | None,
             blackbox: float | None = None) -> str:
    lo, hi = TARGET_BAND
    if exam_rate > hi:
        msg = (f"Learner exam success {exam_rate:.0%} is above the target band {lo:.0%}-{hi:.0%}: "
               "the next version should be harder in a new dimension.")
    elif exam_rate < lo:
        ref = "" if reference is None else f" (the gray-box reference reached {reference:.0%})"
        msg = (f"Learner exam success {exam_rate:.0%} is below the target band{ref}: keep the "
               "challenge but check tickets for interface problems before making it harder.")
    else:
        msg = f"Learner exam success {exam_rate:.0%} is inside the target band."
    if pretest_rate >= exam_rate:
        msg += " The pretest was as good as the exam: the challenge did not require learning."
    if blackbox is not None and blackbox >= 0.8:
        msg += (f" A model-free curve-fitting baseline also reached {blackbox:.0%}: the challenge "
                "can be brute-forced; prefer changes that need physical understanding (more "
                "knobs, smaller budget, consequential modifiable dimensions).")
    return msg


def build_report(round_index: int, version: int, cert: Certificate,
                 metrics: list[InstanceMetrics], swap: dict[str, float | None | str],
                 old_theory: float | None, controls: dict | None = None) -> RoundReport:
    exam = sum(m.exam_hits for m in metrics) / max(1, sum(m.exam_n for m in metrics))
    pre = sum(m.pretest_hits for m in metrics) / max(1, sum(m.pretest_n for m in metrics))
    tickets = [t for m in metrics for t in m.tickets]
    return RoundReport(
        round=round_index,
        device_version=version,
        certificate=[v.line() for v in cert.verdicts],
        reference_learner_success=cert.stats.get("reference_success"),
        oracle_success=cert.stats.get("oracle_success"),
        instances=[
            InstanceSummary(
                label=m.label,
                pretest_success=m.pretest_rate,
                exam_success=m.exam_rate,
                experiments_used=m.experiments_used,
                budget=m.budget,
                prediction_error_first_vs_last=m.pred_trend(),
                probe_errors_over_tol=[e for _, e in m.probe_pred_err],
                theory_hit_rates={k: v["hit_rate"] for k, v in m.theory.items()},
                failure_tags=failure_tags(m),
            )
            for m in metrics
        ],
        learnability=exam * (1 - exam),
        swap_test=swap,
        old_theory_on_new_device=old_theory,
        controls=controls or {},
        tickets=tickets,
        guidance=guidance(exam, pre, cert.stats.get("reference_success"),
                          (controls or {}).get("blackbox_exam_success")),
    )
