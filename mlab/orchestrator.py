"""Round loop. The orchestrator is referee-side: it alone holds the world, the instances and
the construction records, and it is the only component that talks to both agents."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np

from mlab.agents.lab_api import LabAPI, LocalLab
from mlab.agents.learners.scripted import ScriptedAgent, SurrogateLearner
from mlab.catalog.world import sample_world
from mlab.construct.compile import compile_device
from mlab.construct.ir import Submission
from mlab.referee.certify import FAST, FULL, TEST, Certificate, Verdict, certify
from mlab.referee.changelog import changelog
from mlab.referee.channel import ChannelLog
from mlab.referee.leak import scan
from mlab.referee.manual import build_card
from mlab.referee.metrics import compute_metrics
from mlab.referee.modification import modification_effect
from mlab.referee.report import build_report
from mlab.referee.session import LearnerSession
from mlab.referee.theory_eval import build_query_sets, run_theory, score
from mlab.referee.theta import hidden_priors, twin_instances
from mlab.sandbox.audit import make_canary, scan_tree
from mlab.sandbox.policies import ensure_learner_venv

PROFILES = {"full": FULL, "fast": FAST, "test": TEST}


class BuilderAgent(Protocol):
    name: str

    def propose(self, round_index: int, report: dict | None, rejection: str | None) -> Submission | None: ...


class LearnerAgent(Protocol):
    name: str

    def run(self, lab: LabAPI) -> None: ...
    def fork(self) -> LearnerAgent: ...


def default_runs_dir() -> Path:
    return Path(os.environ.get("MLAB_RUNS_DIR", Path.home() / "mlab-runs"))


@dataclass
class RunConfig:
    run_id: str
    rounds: int = 3
    seed: int = 0
    profile: str = "fast"
    max_builder_attempts: int = 3
    act_noise: float = 0.005
    runs_dir: Path = field(default_factory=default_runs_dir)
    blackbox_control: bool = True
    sandbox_theories: bool = False
    instances_from: Path | None = None

    @property
    def root(self) -> Path:
        return Path(self.runs_dir) / self.run_id


@dataclass
class RunDirs:
    root: Path

    def __post_init__(self) -> None:
        for sub in ("referee/submissions", "referee/certificates", "referee/sessions", "referee/instances",
                    "referee/transcripts", "referee/profiles", "builder", "learner",
                    "public/cards", "public/reports"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    @property
    def referee(self) -> Path:
        return self.root / "referee"

    @property
    def public(self) -> Path:
        return self.root / "public"


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _write(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _signature(sub: Submission) -> str:
    t = sub.task
    return json.dumps([[(k.name, k.low, k.high) for k in t.knobs], t.outcome.model_dump()])


class TheoryRunner:
    def __init__(self, sandboxed: bool):
        self.sandboxed = sandboxed
        self.python = str(ensure_learner_venv()) if sandboxed else None

    def __call__(self, code: str, queries: list[dict]) -> list | None:
        return run_theory(code, queries, python=self.python, sandboxed=self.sandboxed)

    def hit_rate(self, code: str | None, qs, tol: float) -> float | None:
        if code is None or not qs.queries:
            return None
        return score(qs, self(code, qs.queries), tol).hit_rate


def _flush_print(*args) -> None:
    print(*args, flush=True)


class Orchestrator:
    def __init__(self, config: RunConfig, builder: BuilderAgent, learner: LearnerAgent,
                 log=_flush_print):
        self.cfg = config
        self.builder = builder
        self.learner = learner
        self.log = log
        self.dirs = RunDirs(Path(config.runs_dir) / config.run_id)
        seeds = np.random.SeedSequence(config.seed).spawn(6)
        self.rng_world, self.rng_cert, self.rng_inst, self.rng_sess, self.rng_eval, self.rng_ctrl = (
            np.random.default_rng(s) for s in seeds
        )
        self.world = sample_world(self.rng_world)
        self.canaries = {role: make_canary(role) for role in ("referee", "builder", "learner")}
        _write(self.dirs.referee / "secrets.json", {"seed": config.seed, "world": self.world,
                                                    "canary": self.canaries["referee"]})
        (self.dirs.root / "builder" / ".canary").write_text(self.canaries["builder"])
        (self.dirs.root / "learner" / ".canary").write_text(self.canaries["learner"])
        self.channel = ChannelLog(self.dirs.public / "channel.jsonl")
        self.profile = PROFILES[config.profile]
        self.theory = TheoryRunner(config.sandbox_theories)

    def _referee_gate(self, r: int, attempt: int, sub: Submission, thetas: list[dict]) -> Certificate:
        secrets = [v for th in thetas for k, v in th.items() if k in hidden_priors(sub.device)]
        leaks = scan(sub, secrets)
        recorded = getattr(self.builder, "recorded_certificate", None)
        cert = recorded(r) if callable(recorded) else None
        if cert is None:
            cert = certify(sub, self.world, self.rng_cert, self.profile)
        if leaks:
            cert.verdicts.insert(0, Verdict("C0", "leak scan", "fail", float(len(leaks)), 0.0,
                                            "; ".join(str(i) for i in leaks)))
        _write(self.dirs.referee / "certificates" / f"r{r}_a{attempt}.json",
               {"report": cert.report(), "stats": cert.stats, "seconds": cert.seconds})
        return cert

    def _session(self, label: str, sub: Submission, dev, theta, card, agent: LearnerAgent):
        sess = LearnerSession(sub, dev, card, self.rng_sess, self.cfg.act_noise)
        t0 = time.time()
        agent.run(LocalLab(sess))
        seconds = time.time() - t0
        rec = sess.record
        self.channel.append(3, "session_summary", {
            "instance": label, "calls": len(rec.calls), "experiments": len(rec.lab),
            "theory_sha": _sha(rec.theory_code or ""), "tickets": [t.model_dump() for t in rec.tickets],
        })
        qsets = build_query_sets(sub, dev, [x.knobs for x in rec.lab], self.rng_eval)
        scores = [score(q, self.theory(rec.theory_code, q.queries), sub.task.tolerance)
                  if rec.theory_code else score(q, None, sub.task.tolerance) for q in qsets]
        metrics = compute_metrics(label, sess, scores, hidden_priors(sub.device), theta)
        last_invalid = getattr(agent, "last_invalid", None)
        metrics.invalid = last_invalid() if callable(last_invalid) else None
        return sess, qsets, metrics, seconds

    def run(self) -> dict:
        report_dict: dict | None = None
        prev_sub: Submission | None = None
        prev_theory: str | None = None
        version = 0
        rounds = []
        twin_sessions: list[dict] = []
        for r in range(1, self.cfg.rounds + 1):
            rejection: str | None = None
            sub: Submission | None = None
            cert: Certificate | None = None
            thetas: list[dict] = []
            attempts = []
            invalid: str | None = None
            for attempt in range(1, self.cfg.max_builder_attempts + 1):
                cand = self.builder.propose(r, report_dict, rejection)
                if cand is None:
                    last_invalid = getattr(self.builder, "last_invalid", None)
                    invalid = last_invalid() if callable(last_invalid) else None
                    break
                _write(self.dirs.referee / "submissions" / f"r{r}_a{attempt}.json", cand.model_dump())
                self.channel.append(1, "submission", {"round": r, "attempt": attempt,
                                                      "device": cand.device.name, "sha": _sha(cand.model_dump())})
                thetas = twin_instances(self.world, cand.device, self.rng_inst)
                cert = self._referee_gate(r, attempt, cand, thetas)
                attempts.append({"attempt": attempt, "passed": cert.passed,
                                 "first_failure": None if cert.passed else cert.first_failure.line(),
                                 "seconds": round(cert.seconds, 1)})
                self.log(f"[round {r}] attempt {attempt}: {'CERTIFIED' if cert.passed else 'REJECTED'}"
                         f" ({cert.seconds:.0f}s)" + ("" if cert.passed else f" - {cert.first_failure.line()}"))
                if cert.passed:
                    sub = cand
                    break
                rejection = cert.report()
                self.channel.append(4, "rejection", {"round": r, "attempt": attempt, "report": rejection})
            if sub is None or cert is None:
                if invalid:
                    rounds.append({"round": r, "status": "invalid_infrastructure",
                                   "attempts": attempts, "invalid": invalid})
                    self.log(f"[round {r}] INVALID: the builder session was lost ({invalid})")
                else:
                    rounds.append({"round": r, "status": "builder_failed", "attempts": attempts})
                    self.log(f"[round {r}] builder failed to produce a certified device")
                continue

            version += 1
            recorded = (self.cfg.instances_from / "referee" / "instances" / f"r{r}.json"
                        if self.cfg.instances_from else None)
            if recorded is not None and recorded.exists():
                saved = json.loads(recorded.read_text())
                thetas = [saved["A"], saved["B"]]
            _write(self.dirs.referee / "instances" / f"r{r}.json", {"A": thetas[0], "B": thetas[1]})
            card = build_card(sub, version, changelog(prev_sub, sub))
            _write(self.dirs.public / "cards" / f"v{version}.json", card.model_dump())
            self.channel.append(5, "task_card", {"version": version, "changelog": card.changelog,
                                                 "sha": _sha(card.model_dump())})
            devs = [compile_device(sub.device, th) for th in thetas]
            twin = self.learner.fork()
            sess_a, qs_a, m_a, sec_a = self._session("A", sub, devs[0], thetas[0], card, self.learner)
            sess_b, qs_b, m_b, sec_b = self._session("B", sub, devs[1], thetas[1], card, twin)
            twin_sessions.extend(getattr(twin, "history", []))
            tol = sub.task.tolerance
            code_a, code_b = sess_a.record.theory_code, sess_b.record.theory_code
            hr = self.theory.hit_rate
            swap: dict = {
                "A_on_A": hr(code_a, qs_a[0], tol), "B_on_B": hr(code_b, qs_b[0], tol),
                "A_on_B": hr(code_a, qs_b[0], tol), "B_on_A": hr(code_b, qs_a[0], tol),
            }
            if not sub.device.hidden:
                swap["note"] = ("not informative: the device has no device-specific hidden "
                                "quantity, so both instances share identical physics")
            old = None
            if prev_theory is not None and prev_sub is not None and _signature(prev_sub) == _signature(sub):
                old = hr(prev_theory, qs_a[0], tol)
            controls: dict = {"modification_effect_over_tol": modification_effect(sub, devs[0], self.rng_ctrl)}
            if self.cfg.blackbox_control:
                ctrl = LearnerSession(sub, devs[0], card, self.rng_ctrl, self.cfg.act_noise)
                SurrogateLearner(self.rng_ctrl, use_memory=False).run(LocalLab(ctrl))
                controls["blackbox_exam_success"] = sum(
                    a.success for a in ctrl.record.attempts if a.phase == "exam") / len(ctrl.exam_goals)
            report = build_report(r, version, cert, [m_a, m_b], swap, old, controls)
            if not sub.device.hidden:
                report.guidance += (" The device declares no device-specific hidden quantity, so "
                                    "every instance is identical; add one (e.g. a sealed mass) so "
                                    "that each instance must be identified anew.")
            report_dict = report.model_dump()
            self.channel.append(4, "round_report", report_dict)
            _write(self.dirs.public / "reports" / f"r{r}.json", report_dict)
            for label, sess in (("A", sess_a), ("B", sess_b)):
                _write(self.dirs.referee / "sessions" / f"r{r}_{label}.json", {
                    "attempts": [a.__dict__ for a in sess.record.attempts],
                    "lab": [x.__dict__ for x in sess.record.lab],
                    "theory_code": sess.record.theory_code,
                    "belief": sess.record.belief.model_dump() if sess.record.belief else None,
                    "calls": sess.record.calls,
                })
            rounds.append({
                "round": r, "status": "ok", "version": version, "device": sub.device.name,
                "attempts": attempts, "metrics": [m_a.to_dict(), m_b.to_dict()],
                "swap": swap, "old_theory": old, "controls": controls,
                "learner_seconds": [round(sec_a, 1), round(sec_b, 1)],
            })
            lost = [f"{m.label}: {m.invalid}" for m in (m_a, m_b) if m.invalid]
            self.log(f"[round {r}] v{version} {sub.device.name}: pretest {m_a.pretest_rate:.0%}/"
                     f"{m_b.pretest_rate:.0%}, exam {m_a.exam_rate:.0%}/{m_b.exam_rate:.0%}, swap {swap}, "
                     f"controls {controls}" + (f", INVALID sessions {lost}" if lost else ""))
            prev_sub, prev_theory = sub, code_a
        summary = {"run_id": self.cfg.run_id, "builder": self.builder.name,
                   "learner": self.learner.name, "profile": self.cfg.profile, "rounds": rounds,
                   "isolation_audit": self.audit()}
        for agent, key in ((self.builder, "builder_sessions"), (self.learner, "learner_sessions")):
            if hasattr(agent, "history"):
                summary[key] = agent.history
        if twin_sessions:
            summary["learner_twin_sessions"] = twin_sessions
        _write(self.dirs.referee / "summary.json", summary)
        return summary

    def audit(self) -> dict:
        """Canaries planted in each private area must not appear in the other agent's files."""
        transcripts = self.dirs.referee / "transcripts"
        learner_side = [self.dirs.root / "learner", *transcripts.glob("learner_*.jsonl")]
        builder_side = [self.dirs.root / "builder", *transcripts.glob("builder_*.jsonl")]
        learner_hits = scan_tree(learner_side, [self.canaries["referee"], self.canaries["builder"]])
        builder_hits = scan_tree(builder_side, [self.canaries["referee"], self.canaries["learner"]])
        return {"learner_side_hits": learner_hits, "builder_side_hits": builder_hits,
                "clean": not learner_hits and not builder_hits}


def offline_learner(seed: int) -> ScriptedAgent:
    return ScriptedAgent(SurrogateLearner(np.random.default_rng(seed)))


class RecordedBuilder:
    """Re-submits the certified designs of an earlier run, round by round, so that another
    learner can be compared on identical devices (and, via instances_from, identical
    instances)."""

    def __init__(self, source: Path):
        self.source = source
        self.name = f"recorded:{source.name}"
        self.summary = json.loads((source / "referee" / "summary.json").read_text())

    def propose(self, round_index: int, report: dict | None, rejection: str | None) -> Submission | None:
        if rejection is not None:
            return None
        r = next((x for x in self.summary["rounds"] if x["round"] == round_index), None)
        if r is None or r.get("status") != "ok":
            return None
        attempt = next(a["attempt"] for a in r["attempts"] if a["passed"])
        path = self.source / "referee" / "submissions" / f"r{round_index}_a{attempt}.json"
        return Submission.model_validate_json(path.read_text())

    def recorded_certificate(self, round_index: int) -> Certificate | None:
        """Certification is stochastic; a device certified in the source run is not re-drawn."""
        r = next((x for x in self.summary["rounds"] if x["round"] == round_index), None)
        if r is None or r.get("status") != "ok":
            return None
        attempt = next(a["attempt"] for a in r["attempts"] if a["passed"])
        data = json.loads((self.source / "referee" / "certificates"
                           / f"r{round_index}_a{attempt}.json").read_text())
        cert = Certificate(stats=data.get("stats", {}))
        cert.verdicts.append(Verdict("C*", "recorded certificate", "pass", None, None,
                                     f"certified in run {self.source.name}, attempt {attempt}"))
        return cert
