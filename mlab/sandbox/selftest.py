"""Verify the sandbox profiles deny and allow exactly what the design says (D-013).

Runs real processes under sandbox-exec against a throwaway run directory with canaries.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from mlab.sandbox.audit import make_canary
from mlab.sandbox.policies import (
    HOME,
    PROJECT,
    WORKSPACE_ROOT,
    builder_policy,
    ensure_learner_venv,
    learner_policy,
    theory_policy,
    wrap,
)

BUILDER_PYTHON = str(PROJECT / ".venv" / "bin" / "python")


@dataclass
class Check:
    role: str
    name: str
    expect_ok: bool
    ok: bool
    detail: str

    @property
    def passed(self) -> bool:
        return self.ok == self.expect_ok


def _run(profile: Path, cmd: list[str], cwd: Path) -> tuple[bool, str]:
    proc = subprocess.run(wrap(profile, cmd), capture_output=True, text=True, timeout=60,
                          check=False, cwd=cwd)
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()[-200:]


PYTHON = {"learner": "", "builder": BUILDER_PYTHON, "theory": ""}


def _py(role: str, code: str) -> list[str]:
    return [PYTHON[role], "-c", code]


def _read(role: str, path: Path) -> list[str]:
    return _py(role, f"print(open({str(path)!r}).read()[:40])")


def _listdir(role: str, path: Path) -> list[str]:
    return _py(role, f"import os; print(len(os.listdir({str(path)!r})))")


def _write(role: str, path: Path) -> list[str]:
    return _py(role, f"open({str(path)!r}, 'w').write('probe')")


def run_selftest(keep: bool = False) -> list[Check]:
    learner_py = str(ensure_learner_venv())
    PYTHON["learner"] = PYTHON["theory"] = learner_py
    (HOME / "mlab-runs").mkdir(exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="selftest-", dir=HOME / "mlab-runs"))
    run_root = base / "run"
    learner_ws, builder_ws = run_root / "learner", run_root / "builder"
    referee = run_root / "referee"
    for d in (learner_ws, builder_ws, referee):
        d.mkdir(parents=True, exist_ok=True)
    canary_ref, canary_build = make_canary("referee"), make_canary("builder")
    (referee / "secrets.json").write_text(f'{{"canary": "{canary_ref}"}}')
    (builder_ws / "device.py").write_text(f"# {canary_build}\n")
    (learner_ws / "notebook.md").write_text("learner notes\n")
    fake_history = HOME / ".cursor" / "chats" / f"selftest-{canary_build[-8:]}"
    fake_history.mkdir(parents=True, exist_ok=True)
    (fake_history / "store.txt").write_text(canary_build)
    tmp = Path(tempfile.mkdtemp(prefix="mlab-tmp-"))
    shared_note = Path("/private/tmp") / f"selftest-note-{canary_build[-8:]}.txt"
    shared_note.write_text(canary_build)
    user_tmp_note = Path(tempfile.gettempdir()) / f"selftest-note-{canary_build[-8:]}.txt"
    user_tmp_note.write_text(canary_build)
    checks: list[Check] = []

    cwd = {"learner": learner_ws, "builder": builder_ws, "theory": tmp}

    def check(role: str, name: str, profile: Path, cmd: list[str], expect_ok: bool) -> None:
        ok, detail = _run(profile, cmd, cwd[role])
        checks.append(Check(role, name, expect_ok, ok, detail))

    try:
        r = "learner"
        lp = learner_policy(run_root, learner_ws, tmp, [fake_history]).write(base / "learner.sb")
        check(r, "read own notebook", lp, _read(r, learner_ws / "notebook.md"), True)
        check(r, "write own workspace", lp, _write(r, learner_ws / "x.txt"), True)
        check(r, "numpy/scipy/mujoco import", lp,
              _py(r, "import numpy, scipy, mujoco; print('ok')"), True)
        check(r, "import mlab (referee code)", lp, _py(r, "import mlab"), False)
        check(r, "read referee secrets", lp, _read(r, referee / "secrets.json"), False)
        check(r, "read builder workspace", lp, _read(r, builder_ws / "device.py"), False)
        check(r, "read project source", lp, _read(r, PROJECT / "mlab" / "orchestrator.py"), False)
        check(r, "read test fixtures", lp, _listdir(r, PROJECT / "fixtures"), False)
        check(r, "read other agents' plans", lp, _listdir(r, WORKSPACE_ROOT), False)
        check(r, "read earlier agent chat", lp, _read(r, fake_history / "store.txt"), False)
        if (HOME / ".codex").exists():
            check(r, "read ~/.codex", lp, _listdir(r, HOME / ".codex"), False)
        if (HOME / ".cursor" / "plans").exists():
            check(r, "read ~/.cursor/plans", lp, _listdir(r, HOME / ".cursor" / "plans"), False)
        check(r, "write builder workspace", lp, _write(r, builder_ws / "hint.txt"), False)
        check(r, "write home", lp, _write(r, HOME / "mlab-selftest-probe.txt"), False)
        check(r, "resolve own workspace path", lp,
              _py(r, f"import os; print(os.path.realpath({str(learner_ws)!r}))"), True)
        check(r, "list run directory", lp, _listdir(r, run_root), False)
        check(r, "read note in /tmp", lp, _read(r, shared_note), False)
        check(r, "read note in user TMPDIR", lp, _read(r, user_tmp_note), False)
        check(r, "write own private tmp", lp, _write(r, tmp / "scratch.txt"), True)

        r = "builder"
        bp = builder_policy(run_root, builder_ws, tmp, [fake_history]).write(base / "builder.sb")
        check(r, "import construction API", bp,
              _py(r, "import mlab.construct, mlab.referee.certify; print('ok')"), True)
        check(r, "write own workspace", bp, _write(r, builder_ws / "y.txt"), True)
        check(r, "read learner notebook", bp, _read(r, learner_ws / "notebook.md"), False)
        check(r, "read referee secrets", bp, _read(r, referee / "secrets.json"), False)
        check(r, "read test fixtures", bp, _listdir(r, PROJECT / "fixtures"), False)
        check(r, "read reference designs", bp,
              _read(r, PROJECT / "mlab" / "agents" / "builders" / "reference.py"), False)
        check(r, "read earlier agent chat", bp, _read(r, fake_history / "store.txt"), False)
        check(r, "write learner workspace", bp, _write(r, learner_ws / "hint.txt"), False)
        check(r, "write note to /tmp", bp, _write(r, Path("/private/tmp") / "builder-hint.txt"), False)
        check(r, "write note to user TMPDIR", bp,
              _write(r, Path(tempfile.gettempdir()) / "builder-hint.txt"), False)

        r = "theory"
        tp = theory_policy(tmp).write(base / "theory.sb")
        check(r, "compute in own tmp", tp, _py(r, "import numpy; print(numpy.ones(2).sum())"), True)
        check(r, "read run directory", tp, _read(r, referee / "secrets.json"), False)
        check(r, "network", tp, _py(
            r, "import socket; s=socket.create_connection(('1.1.1.1', 80), timeout=3); print('net')"),
            False)
    finally:
        shutil.rmtree(fake_history, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)
        shared_note.unlink(missing_ok=True)
        user_tmp_note.unlink(missing_ok=True)
        if not keep:
            shutil.rmtree(base, ignore_errors=True)
    return checks


def main() -> int:
    if sys.platform != "darwin":
        print("sandbox selftest requires macOS sandbox-exec")
        return 2
    checks = run_selftest()
    for c in checks:
        mark = "PASS" if c.passed else "FAIL"
        want = "allowed" if c.expect_ok else "denied"
        print(f"[{mark}] {c.role:8s} {c.name:34s} expected {want}")
        if not c.passed:
            print(f"        {c.detail}")
    failed = [c for c in checks if not c.passed]
    print(f"{len(checks) - len(failed)}/{len(checks)} checks passed")
    return 1 if failed else 0
