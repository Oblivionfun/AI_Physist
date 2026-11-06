"""LLM-driven builder and learner. Each session is a fresh CLI chat inside its own sandbox;
explicit files in the agent's workspace are its only memory."""

from __future__ import annotations

import json
import shutil
import stat
import tempfile
import time
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
MIN_NUDGE_SECONDS = 180


def _install_script(dst: Path, python: Path, body: str) -> None:
    dst.write_text(f"#!{python}\n{body}")
    dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class LLMLearner:
    def __init__(self, backend: CursorAgentBackend, run_root: Path, workspace: Path,
                 transcripts: Path, profiles: Path, max_nudges: int = 2, log=print):
        self.backend = backend
        self.run_root = run_root
        self.workspace = workspace
        self.transcripts = transcripts
        self.profiles = profiles
        self.max_nudges = max_nudges
        self.log = log
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
                          self.max_nudges, self.log)
        twin.sessions = self.sessions
        return twin

    def _prepare(self, tag: str, server: LabServer, deadline: float) -> Path:
        ws = self.workspace
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
            profile = learner_policy(self.run_root, self.workspace, tmp, history).write(
                self.profiles / f"learner_{tag}.sb")
            env = agent_env(self.workspace, tmp, [self.workspace, python.parent])
            prompt = load("learner") + f"\nSession {tag}. Begin with `./lab card`.\n"
            transcript = self.transcripts / f"learner_{tag}.jsonl"
            runs: list[AgentResult] = [self.backend.run(prompt, self.workspace, profile, transcript,
                                                        env, timeout=0.85 * budget)]
            while (lab.status()["phase"] != "done" and len(runs) <= self.max_nudges
                   and runs[-1].session_id and deadline - time.time() > MIN_NUDGE_SECONDS):
                self.log(f"  learner {tag}: phase {lab.status()['phase']}, nudging")
                runs.append(self.backend.run(LEARNER_NUDGE, self.workspace, profile, transcript, env,
                                             resume=runs[-1].session_id,
                                             timeout=deadline - time.time()))
        finally:
            server.stop()
            shutil.rmtree(tmp, ignore_errors=True)
            (self.workspace / ".lab.json").unlink(missing_ok=True)
        self.history.append({
            "tag": tag, "final_phase": lab.status()["phase"],
            "runs": [r.__dict__ for r in runs], "rpc_calls": len(calls),
            "rpc_errors": sum(1 for _, ok in calls if not ok),
        })
        self.log(f"  learner {tag}: finished in phase {lab.status()['phase']} after {len(calls)} lab "
                 f"calls, {sum(r.seconds for r in runs):.0f}s")


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
            runs = [self.backend.run(prompt, ws, profile, transcript, env,
                                     timeout=(1 - self.NUDGE_RESERVE) * budget)]
            while (not out.exists() and len(runs) <= self.max_nudges and runs[-1].session_id
                   and deadline - time.time() > MIN_NUDGE_SECONDS):
                self.log(f"  builder call {self.calls}: no submission yet, nudging")
                runs.append(self.backend.run(BUILDER_NUDGE, ws, profile, transcript, env,
                                             resume=runs[-1].session_id,
                                             timeout=deadline - time.time()))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.history.append({"call": self.calls, "round": round_index, "inbox": inbox,
                             "runs": [r.__dict__ for r in runs], "submitted": out.exists()})
        self.log(f"  builder call {self.calls}: {'submitted' if out.exists() else 'no submission'} "
                 f"after {sum(r.seconds for r in runs):.0f}s")
        if not out.exists():
            return None
        try:
            return Submission.model_validate_json(out.read_text())
        except ValueError as exc:
            self.log(f"  builder call {self.calls}: invalid submission ({str(exc)[:200]})")
            return None
