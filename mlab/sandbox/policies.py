"""Seatbelt (sandbox-exec) profiles for each role (see docs/decisions.md D-013).

Deny-list style with ordered layers, because later rules override earlier ones:
  1. allow default
  2. deny writes to $HOME and the workspace root
  3. broad allows (CLI state/caches)
  4. denies (other agents, referee, sources, chat history) -- override 3
  5. specific allows (own workspace, tmp, interpreter) -- re-open inside 4
  6. final denies (sub-trees of 5 that must stay closed)
Children inherit the profile, so the agent CLI's shell tools and MCP servers are covered.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT.parent
HOME = Path.home()
LEARNER_VENV = HOME / ".local" / "share" / "mlab" / "learner-venv"
LEARNER_PACKAGES = ["numpy", "scipy", "mujoco", "matplotlib"]
SENSITIVE_HOME = [
    HOME / ".codex",
    HOME / ".cursor" / "plans",
    HOME / "Library" / "Application Support" / "Cursor",
]
WRITABLE_HOME = [
    HOME / ".cursor",
    HOME / ".local",
    HOME / "Library" / "Caches",
    HOME / "Library" / "Application Support" / "cursor-agent",
]


def real(p: Path | str) -> str:
    return os.path.realpath(str(p))


def _q(p: Path | str) -> str:
    return '"' + real(p).replace("\\", "\\\\").replace('"', '\\"') + '"'


def snapshot_agent_history(exclude_substrings: list[str]) -> list[Path]:
    """Existing CLI chat/project dirs at launch time, i.e. other sessions' records."""
    out: list[Path] = []
    for base in (HOME / ".cursor" / "chats", HOME / ".cursor" / "projects"):
        if base.is_dir():
            for child in base.iterdir():
                if child.is_dir() and not any(s in child.name for s in exclude_substrings):
                    out.append(child)
    return out


def learner_python() -> Path:
    return LEARNER_VENV / "bin" / "python"


def ensure_learner_venv() -> Path:
    """A venv without mlab, so learner-side code cannot import referee modules."""
    py = learner_python()
    if not py.exists():
        LEARNER_VENV.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["uv", "venv", "--python", "3.12", str(LEARNER_VENV)], check=True,
                       capture_output=True)
        subprocess.run(["uv", "pip", "install", "--python", str(py), *LEARNER_PACKAGES],
                       check=True, capture_output=True)
    return py


def ancestors(path: Path) -> list[Path]:
    """Directories above `path`; agent CLIs stat each of them to resolve the working dir."""
    p = Path(real(path))
    return list(p.parents)


def _block(verb: str, paths: list[Path], literal: bool = False) -> list[str]:
    if not paths:
        return []
    kind = "literal" if literal else "subpath"
    return [f"({verb}"] + [f"  ({kind} {_q(p)})" for p in paths] + [")"]


@dataclass
class Policy:
    role: str
    deny: list[Path]
    allow_read: list[Path] = field(default_factory=list)
    allow_read_literal: list[Path] = field(default_factory=list)
    allow_rw: list[Path] = field(default_factory=list)
    final_deny: list[Path] = field(default_factory=list)
    broad_rw: list[Path] = field(default_factory=lambda: list(WRITABLE_HOME))
    deny_network: bool = False

    def render(self) -> str:
        lines = ["(version 1)", "(allow default)", f"; role: {self.role}"]
        lines.append(f"(deny file-write* (subpath {_q(HOME)}) (subpath {_q(WORKSPACE_ROOT)}))")
        lines += _block("allow file-read* file-write*", self.broad_rw)
        lines += _block("deny file-read* file-write*", self.deny)
        lines += _block("allow file-read*", self.allow_read)
        lines += _block("allow file-read*", self.allow_read_literal, literal=True)
        lines += _block("allow file-read* file-write*", self.allow_rw)
        chain = sorted({str(a) for p in self.allow_rw for a in ancestors(p)})
        lines += _block("allow file-read-metadata", [Path(c) for c in chain], literal=True)
        lines += _block("deny file-read* file-write*", self.final_deny)
        if self.deny_network:
            lines.append("(deny network*)")
        return "\n".join(lines) + "\n"

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render())
        return path


def learner_policy(run_root: Path, workspace: Path, tmpdir: Path, history: list[Path]) -> Policy:
    return Policy(
        role="learner",
        deny=[WORKSPACE_ROOT, run_root.parent, *SENSITIVE_HOME, *history],
        allow_rw=[workspace, tmpdir],
    )


def builder_policy(run_root: Path, workspace: Path, tmpdir: Path, history: list[Path]) -> Policy:
    return Policy(
        role="builder",
        deny=[WORKSPACE_ROOT, run_root.parent, *SENSITIVE_HOME, *history],
        allow_read=[PROJECT / ".venv", PROJECT / "mlab", PROJECT / "pyproject.toml"],
        allow_read_literal=[PROJECT, WORKSPACE_ROOT],
        allow_rw=[workspace, tmpdir],
        final_deny=[PROJECT / "mlab" / "agents" / "builders"],
    )


def builder_code_policy(workspace: Path, tmpdir: Path) -> Policy:
    """For running builder-written device scripts referee-side: no network, read-only."""
    return Policy(
        role="builder-code",
        deny=[WORKSPACE_ROOT, HOME / "mlab-runs", *SENSITIVE_HOME],
        allow_read=[PROJECT / ".venv", PROJECT / "mlab", workspace],
        allow_read_literal=[PROJECT, WORKSPACE_ROOT],
        allow_rw=[tmpdir],
        final_deny=[PROJECT / "mlab" / "agents" / "builders"],
        broad_rw=[],
        deny_network=True,
    )


def theory_policy(tmpdir: Path) -> Policy:
    """For running a learner's predict.py referee-side: own files only, no network."""
    return Policy(
        role="theory",
        deny=[WORKSPACE_ROOT, HOME / "mlab-runs", *SENSITIVE_HOME],
        allow_rw=[tmpdir],
        broad_rw=[],
        deny_network=True,
    )


def wrap(profile: Path, cmd: list[str]) -> list[str]:
    return ["/usr/bin/sandbox-exec", "-f", str(profile), *cmd]
