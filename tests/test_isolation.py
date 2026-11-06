"""Isolation plumbing without an LLM: the sandboxed lab client can drive a session through the
RPC, cannot read referee or builder files, and cannot call non-learner methods."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

from fixtures.devices import spring_launcher
from mlab.agents.lab_api import LocalLab
from mlab.agents.prompts import NAMES, digest, recorded
from mlab.catalog import sample_world
from mlab.construct import compile_device
from mlab.referee.manual import build_card
from mlab.referee.rpc import LabServer
from mlab.referee.session import LearnerSession
from mlab.referee.theory_eval import run_theory
from mlab.referee.theta import twin_instances
from mlab.sandbox.policies import PROJECT, ensure_learner_venv, learner_policy, wrap

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="needs sandbox-exec")


def test_prompts_are_frozen():
    hashes = recorded()
    for name in NAMES:
        assert digest(name) == hashes[name], f"prompt {name} changed without updating hashes.json"


@pytest.fixture()
def served_lab():
    sub = spring_launcher.submission()
    world = sample_world(np.random.default_rng(7))
    dev = compile_device(sub.device, twin_instances(world, sub.device, np.random.default_rng(1))[0])
    sess = LearnerSession(sub, dev, build_card(sub, 1), np.random.default_rng(2))
    server = LabServer(LocalLab(sess))
    server.start()
    yield sess, server
    server.stop()


def test_rpc_rejects_bad_token_and_unknown_methods(served_lab):
    _, server = served_lab
    assert server.handle(b'{"token": "x", "method": "card"}')["error"] == "invalid token"
    bad = json.dumps({"token": server.token, "method": "results"}).encode()
    assert "unknown method" in server.handle(bad)["error"]
    extra = json.dumps({"token": server.token, "method": "status", "args": {"x": 1}}).encode()
    assert not server.handle(extra)["ok"]


def test_sandboxed_lab_client_drives_session_but_cannot_read_secrets(served_lab):
    sess, server = served_lab
    runs = Path.home() / "mlab-runs"
    runs.mkdir(exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="isotest-", dir=runs))
    ws, ref = base / "learner", base / "referee"
    ws.mkdir()
    ref.mkdir()
    (ref / "secrets.json").write_text('{"x": 1}')
    tmp = Path(tempfile.mkdtemp(prefix="mlab-tmp-"))
    try:
        py = str(ensure_learner_venv())
        shutil.copy(PROJECT / "mlab" / "cli" / "lab.py", ws / "lab.py")
        (ws / ".lab.json").write_text(json.dumps(server.client_config("t")))
        profile = learner_policy(base, ws, tmp, [], socket_dir=server.dir).write(base / "learner.sb")

        def run(*args):
            return subprocess.run(wrap(profile, [py, "lab.py", *args]), cwd=ws, capture_output=True,
                                  text=True, timeout=120, check=False)

        assert run("card").returncode == 0
        for _ in range(3):
            assert run("answer", '{"compression": -0.08}').returncode == 0
        out = run("exp", '{"compression": -0.1}', "[0.6]")
        assert out.returncode == 0, out.stdout + out.stderr
        assert (ws / "data" / "t" / "exp_000.json").exists()
        assert len(sess.record.lab) == 1
        leak = subprocess.run(wrap(profile, [py, "-c", f"open({str(ref / 'secrets.json')!r}).read()"]),
                              cwd=ws, capture_output=True, text=True, check=False)
        assert leak.returncode != 0
    finally:
        shutil.rmtree(base, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def test_sandboxed_theory_cannot_read_run_files():
    runs = Path.home() / "mlab-runs"
    runs.mkdir(exist_ok=True)
    secret = Path(tempfile.mkdtemp(prefix="isotest-", dir=runs)) / "secret.txt"
    secret.write_text("42")
    code = (f"def predict(knobs, visible):\n"
            f"    return [float(open({str(secret)!r}).read())]\n")
    try:
        out = run_theory(code, [{"knobs": {}, "visible": {}}], python=str(ensure_learner_venv()),
                         sandboxed=True)
        assert out == [None]
        ok = run_theory("def predict(knobs, visible):\n    return [1.5]\n",
                        [{"knobs": {}, "visible": {}}], python=str(ensure_learner_venv()),
                        sandboxed=True)
        assert ok == [[1.5]]
    finally:
        shutil.rmtree(secret.parent, ignore_errors=True)
