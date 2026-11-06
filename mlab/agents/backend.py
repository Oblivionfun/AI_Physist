"""Agent CLI backends. Each session runs inside a sandbox-exec profile with the CLI's own
sandbox disabled (nested Seatbelt is not permitted, see D-013)."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from mlab.sandbox.policies import wrap


@dataclass
class AgentResult:
    exit_code: int | None
    seconds: float
    session_id: str | None
    final: str
    timed_out: bool
    tool_calls: int
    usage: dict = field(default_factory=dict)


def agent_env(workspace: Path, tmpdir: Path, extra_path: list[Path]) -> dict[str, str]:
    home = str(Path.home())
    path = [str(p) for p in extra_path] + [f"{home}/.local/bin", "/opt/homebrew/bin", "/usr/bin",
                                           "/bin", "/usr/sbin", "/sbin"]
    return {
        "HOME": home,
        "USER": os.environ.get("USER", ""),
        "LOGNAME": os.environ.get("LOGNAME", ""),
        "PATH": ":".join(path),
        "LANG": "en_US.UTF-8",
        "TERM": "xterm-256color",
        "SHELL": "/bin/zsh",
        "TMPDIR": str(tmpdir) + "/",
        "PWD": str(workspace),
    }


def _pump(stream, path: Path) -> None:
    with path.open("ab") as f:
        for chunk in iter(lambda: stream.readline(), b""):
            f.write(chunk)
            f.flush()


def parse_stream(transcript: Path) -> tuple[str | None, str, int, dict]:
    session_id, final, tools, usage = None, "", 0, {}
    if not transcript.exists():
        return session_id, final, tools, usage
    for line in transcript.read_text(errors="ignore").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        session_id = e.get("session_id", session_id)
        if e.get("type") == "tool_call" and e.get("subtype") == "started":
            tools += 1
        if e.get("type") == "result":
            final = e.get("result", "") or ""
            usage = e.get("usage", {}) or {}
    return session_id, final, tools, usage


class CursorAgentBackend:
    def __init__(self, model: str, binary: str = "cursor-agent", timeout: float = 2700.0):
        self.model = model
        self.binary = binary
        self.timeout = timeout

    @property
    def name(self) -> str:
        return f"cursor-agent:{self.model}"

    def run(self, prompt: str, workspace: Path, profile: Path, transcript: Path,
            env: dict[str, str], resume: str | None = None,
            timeout: float | None = None) -> AgentResult:
        limit = self.timeout if timeout is None else timeout
        cmd = [self.binary, "-p", "--output-format", "stream-json", "--model", self.model,
               "--workspace", str(workspace), "--trust", "--force", "--sandbox", "disabled"]
        if resume:
            cmd += ["--resume", resume]
        cmd.append(prompt)
        transcript.parent.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        timed_out = False
        # The agent's stdio must be pipes: its runtime stats stdio at start-up, and a file in a
        # directory the sandbox denies (the referee area) makes it abort.
        proc = subprocess.Popen(wrap(profile, cmd), cwd=workspace, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, start_new_session=True)
        pumps = [
            threading.Thread(target=_pump, args=(proc.stdout, transcript), daemon=True),
            threading.Thread(target=_pump, args=(proc.stderr, transcript.with_suffix(".stderr")),
                             daemon=True),
        ]
        for p in pumps:
            p.start()
        try:
            code = proc.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                code = proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                code = proc.wait()
        for p in pumps:
            p.join(timeout=10)
        session_id, final, tools, usage = parse_stream(transcript)
        return AgentResult(code, time.time() - t0, session_id, final, timed_out, tools, usage)
