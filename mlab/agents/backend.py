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

# stderr markers of failures outside the agent's control (network, service availability).
TRANSIENT_ERRORS = ("[unavailable]", "[resource_exhausted]", "ENOTFOUND", "EAI_AGAIN",
                    "ECONNRESET", "ECONNREFUSED", "ETIMEDOUT", "socket hang up",
                    "RetriableError", "Connection stalled")
# Wall-clock time beyond monotonic time means the machine slept: subprocess timeouts do not
# advance during sleep on macOS, and the agent loses its connection.
SLEEP_TOLERANCE_S = 60.0


@dataclass
class AgentResult:
    exit_code: int | None
    seconds: float
    session_id: str | None
    final: str
    timed_out: bool
    tool_calls: int
    usage: dict = field(default_factory=dict)
    infra_error: str | None = None


def infra_error(exit_code: int | None, timed_out: bool, stderr: str,
                slept_s: float = 0.0) -> str | None:
    if slept_s > SLEEP_TOLERANCE_S:
        return f"the machine slept for {slept_s:.0f}s during the session"
    if timed_out or exit_code in (0, None):
        return None
    return next((line.strip()[:200] for line in stderr.splitlines()
                 if any(m in line for m in TRANSIENT_ERRORS)), None)


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
        # zsh writes here-documents under TMPPREFIX (default /tmp/zsh), which the sandbox closes.
        "TMPPREFIX": str(tmpdir) + "/zsh",
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
        err_path = transcript.with_suffix(".stderr")
        err_offset = err_path.stat().st_size if err_path.exists() else 0
        t0, m0 = time.time(), time.monotonic()
        timed_out = False
        # The agent's stdio must be pipes: its runtime stats stdio at start-up, and a file in a
        # directory the sandbox denies (the referee area) makes it abort.
        proc = subprocess.Popen(wrap(profile, cmd), cwd=workspace, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, start_new_session=True)
        pumps = [
            threading.Thread(target=_pump, args=(proc.stdout, transcript), daemon=True),
            threading.Thread(target=_pump, args=(proc.stderr, err_path), daemon=True),
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
        stderr = ""
        if err_path.exists():
            with err_path.open("rb") as f:
                f.seek(err_offset)
                stderr = f.read().decode(errors="ignore")
        wall = time.time() - t0
        slept = wall - (time.monotonic() - m0)
        return AgentResult(code, wall, session_id, final, timed_out, tools, usage,
                           infra_error(code, timed_out, stderr, slept))
