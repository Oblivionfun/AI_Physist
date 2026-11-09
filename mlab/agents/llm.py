"""LLM-driven builder and learner. Each session is a fresh CLI chat inside its own sandbox;
explicit files in the agent's workspace are its only memory."""

from __future__ import annotations

import json
import shutil
import stat
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from mlab.agents.backend import AgentResult, CursorAgentBackend, agent_env
from mlab.agents.lab_api import LabAPI
from mlab.agents.prompts import load
from mlab.construct.ir import Submission
from mlab.referee.report import RoundReport
from mlab.referee.rpc import LabServer
from mlab.sandbox.policies import (
    PROJECT,
    builder_policy,
    ensure_learner_venv,
    learner_policy,
    snapshot_agent_history,
)

LAB_CLIENT = PROJECT / "mlab" / "cli" / "lab.py"
LEARNER_NUDGE = ("Your session is not finished: `./lab status` is not 'done' yet. Continue the "
                 "protocol from where you are and finish it.")
BUILDER_NUDGE = ("No submission was found in outbox/ and your session time is almost over. "
                 "Submit your best design now with `./forge submit device.py`; a rejected submission "
                 "still returns a detailed report, an empty one ends the round.")
RECONNECT = ("The connection to the model service dropped and has been restored. Check where you "
             "are and continue from there.")
MIN_NUDGE_SECONDS = 180
INFRA_WAITS = (30.0, 90.0, 240.0)


def _drive(first: Callable[[float], AgentResult], follow: Callable[[str, str, float], AgentResult],
           finished: Callable[[], bool], nudge: str, max_nudges: int, deadline: float,
           log: Callable[[str], None]) -> list[AgentResult]:
    """Run a session to completion: nudge an agent that stopped early (at most max_nudges
    times), and retry after infrastructure failures (network, service) with back-off without
    spending nudges. follow(prompt, session_id, timeout) resumes; first(timeout) starts anew."""
    runs = [first(deadline - time.time())]
    nudges = retries = 0
    while not finished() and deadline - time.time() > MIN_NUDGE_SECONDS:
        last = runs[-1]
        if last.infra_error:
            if retries >= len(INFRA_WAITS):
                break
            wait = min(INFRA_WAITS[retries], deadline - time.time() - MIN_NUDGE_SECONDS)
            retries += 1
            log(f"infrastructure error ({last.infra_error}); retry {retries} in {wait:.0f}s")
            time.sleep(max(0.0, wait))
            left = deadline - time.time()
            runs.append(follow(RECONNECT, last.session_id, left) if last.session_id else first(left))
            continue
        if nudges >= max_nudges or not last.session_id:
            break
        nudges += 1
        log("not finished, nudging")
        runs.append(follow(nudge, last.session_id, deadline - time.time()))
    return runs


def invalid_reason(runs: list[AgentResult], finished: bool) -> str | None:
    """A session that ended unfinished because of infrastructure failures carries no evidence
    about the agent and must not be scored as the agent's failure."""
    errors = [r.infra_error for r in runs if r.infra_error]
    if finished or not errors:
        return None
    return f"infrastructure: {errors[-1]}"


def _install_script(dst: Path, python: Path, body: str) -> None:
    dst.write_text(f"#!{python}\n{body}")
    dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class LLMLearner:
    def __init__(self, backend: CursorAgentBackend, run_root: Path, workspace: Path,
                 transcripts: Path, profiles: Path, max_nudges: int = 2, log=print,
                 amnesic: bool = False):
        """amnesic (ablation): the workspace is wiped before every session."""
        self.backend = backend
        self.run_root = run_root
        self.workspace = workspace
        self.transcripts = transcripts
        self.profiles = profiles
        self.max_nudges = max_nudges
        self.log = log
        self.amnesic = amnesic
        self.sessions = 0
        self.history: list[dict] = []

    @property
    def name(self) -> str:
        return f"llm-learner:{self.backend.name}"

    def fork(self) -> LLMLearner:
        k = len([p for p in self.workspace.parent.glob("twin*")]) + 1
        dst = self.workspace.parent / f"twin{k:02d}"
        if self.workspace.exists():
            shutil.copytree(self.workspace, dst, ignore=shutil.ignore_patterns(".lab.json"))
        twin = LLMLearner(self.backend, self.run_root, dst, self.transcripts, self.profiles,
                          self.max_nudges, self.log, self.amnesic)
        twin.sessions = self.sessions
        return twin

    def _prepare(self, tag: str, server: LabServer, deadline: float) -> Path:
        ws = self.workspace
        if self.amnesic and ws.exists():
            shutil.rmtree(ws)
        (ws / "theories").mkdir(parents=True, exist_ok=True)
        (ws / "data").mkdir(exist_ok=True)
        notebook = ws / "notebook.md"
        if not notebook.exists():
            notebook.write_text("# Notebook\n\n(no entries yet)\n")
        python = ensure_learner_venv()
        canary = self.run_root / "learner" / ".canary"
        if canary.exists():
            shutil.copy(canary, ws / ".canary")
        _install_script(ws / "lab", python, LAB_CLIENT.read_text())
        (ws / ".lab.json").write_text(json.dumps({**server.client_config(tag), "deadline": deadline}))
        return python

    def run(self, lab: LabAPI) -> None:
        self.sessions += 1
        card = lab.card()
        tag = f"v{card['version']}_{self.workspace.name}_s{self.sessions}"
        calls: list[tuple[str, bool]] = []
        server = LabServer(lab, on_call=lambda m, a, ok: calls.append((m, ok)))
        server.start()
        tmp = Path(tempfile.mkdtemp(prefix="mlab-tmp-"))
        budget = self.backend.timeout
        deadline = time.time() + budget
        try:
            python = self._prepare(tag, server, deadline)
            history = snapshot_agent_history(self.workspace)
            profile = learner_policy(self.run_root, self.workspace, tmp, history,
                                     socket_dir=server.dir).write(self.profiles / f"learner_{tag}.sb")
            env = agent_env(self.workspace, tmp, [self.workspace, python.parent])
            prompt = load("learner") + f"\nSession {tag}. Begin with `./lab card`.\n"
            transcript = self.transcripts / f"learner_{tag}.jsonl"

            def first(left: float) -> AgentResult:
                return self.backend.run(prompt, self.workspace, profile, transcript, env,
                                        timeout=min(left, 0.85 * budget))

            def follow(text: str, session: str, left: float) -> AgentResult:
                return self.backend.run(text, self.workspace, profile, transcript, env,
                                        resume=session, timeout=left)

            runs = _drive(first, follow, lambda: lab.status()["phase"] == "done", LEARNER_NUDGE,
                          self.max_nudges, deadline,
                          lambda msg: self.log(f"  learner {tag}: phase {lab.status()['phase']}, {msg}"))
        finally:
            server.stop()
            shutil.rmtree(tmp, ignore_errors=True)
            (self.workspace / ".lab.json").unlink(missing_ok=True)
        phase = lab.status()["phase"]
        invalid = invalid_reason(runs, phase == "done")
        self.history.append({
            "tag": tag, "final_phase": phase, "invalid": invalid,
            "runs": [r.__dict__ for r in runs], "rpc_calls": len(calls),
            "rpc_errors": sum(1 for _, ok in calls if not ok),
        })
        self.log(f"  learner {tag}: finished in phase {phase} after {len(calls)} lab calls, "
                 f"{sum(r.seconds for r in runs):.0f}s" + (f" - INVALID ({invalid})" if invalid else ""))

    def last_invalid(self) -> str | None:
        return self.history[-1]["invalid"] if self.history else None


class LLMBuilder:
    NUDGE_RESERVE = 0.2

    def __init__(self, backend: CursorAgentBackend, run_root: Path, transcripts: Path,
                 profiles: Path, cert_profile: str = "fast", max_nudges: int = 1, log=print):
        self.backend = backend
        self.run_root = run_root
        self.workspace = run_root / "builder"
        self.transcripts = transcripts
        self.profiles = profiles
        self.cert_profile = cert_profile
        self.max_nudges = max_nudges
        self.log = log
        self.calls = 0
        self.history: list[dict] = []

    @property
    def name(self) -> str:
        return f"llm-builder:{self.backend.name}"

    def _inbox(self, round_index: int, report: dict | None, rejection: str | None) -> str:
        if rejection is not None:
            body = ("Your last submission was REJECTED by the referee. Fix the failing check and "
                    "submit again.\n\n" + rejection)
        elif report is not None:
            body = "Report on the previous round:\n\n" + RoundReport.model_validate(report).text()
        else:
            body = "This is the first round: there is no previous report."
        name = f"round{round_index:02d}_call{self.calls:02d}.md"
        (self.workspace / "inbox" / name).write_text(body + "\n")
        return name

    def propose(self, round_index: int, report: dict | None, rejection: str | None) -> Submission | None:
        self.calls += 1
        ws = self.workspace
        for sub in ("inbox", "designs", "outbox"):
            (ws / sub).mkdir(parents=True, exist_ok=True)
        if not (ws / "design_log.md").exists():
            (ws / "design_log.md").write_text("# Design log\n")
        python = PROJECT / ".venv" / "bin" / "python"
        _install_script(ws / "forge", python, "from mlab.cli.forge import main\nraise SystemExit(main())\n")
        inbox = self._inbox(round_index, report, rejection)
        out = ws / "outbox" / "submission.json"
        out.unlink(missing_ok=True)
        budget = self.backend.timeout
        deadline = time.time() + budget
        (ws / "forge.json").write_text(json.dumps({
            "deadline": deadline - self.NUDGE_RESERVE * budget, "budget_seconds": budget,
            "profile": "fast" if self.cert_profile in ("fast", "full") else "test",
        }))
        tmp = Path(tempfile.mkdtemp(prefix="mlab-tmp-"))
        try:
            history = snapshot_agent_history(ws)
            profile = builder_policy(self.run_root, ws, tmp, history).write(
                self.profiles / f"builder_call{self.calls:02d}.sb")
            env = agent_env(ws, tmp, [ws, python.parent])
            prompt = load("builder") + f"\nRound {round_index}. Read inbox/{inbox} first.\n"
            transcript = self.transcripts / f"builder_call{self.calls:02d}.jsonl"

            def first(left: float) -> AgentResult:
                return self.backend.run(prompt, ws, profile, transcript, env,
                                        timeout=min(left, (1 - self.NUDGE_RESERVE) * budget))

            def follow(text: str, session: str, left: float) -> AgentResult:
                return self.backend.run(text, ws, profile, transcript, env, resume=session,
                                        timeout=left)

            runs = _drive(first, follow, out.exists, BUILDER_NUDGE, self.max_nudges, deadline,
                          lambda msg: self.log(f"  builder call {self.calls}: {msg}"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        invalid = invalid_reason(runs, out.exists())
        self.history.append({"call": self.calls, "round": round_index, "inbox": inbox,
                             "runs": [r.__dict__ for r in runs], "submitted": out.exists(),
                             "invalid": invalid})
        self.log(f"  builder call {self.calls}: {'submitted' if out.exists() else 'no submission'} "
                 f"after {sum(r.seconds for r in runs):.0f}s" + (f" - {invalid}" if invalid else ""))
        return self._read_submission(out)

    def last_invalid(self) -> str | None:
        return self.history[-1]["invalid"] if self.history else None

    def _read_submission(self, out: Path) -> Submission | None:
        if not out.exists():
            return None
        try:
            return Submission.model_validate_json(out.read_text())
        except ValueError as exc:
            self.log(f"  builder call {self.calls}: invalid submission ({str(exc)[:200]})")
            return None
