"""Observatory: event scanner on a growing run directory, re-simulation, server access control."""

import base64
import http.client
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import numpy as np
import pytest

from fixtures.devices import spring_launcher
from mlab.catalog import sample_world
from mlab.construct import compile_device
from mlab.referee.manual import build_card
from mlab.referee.theta import twin_instances
from mlab.sim.runner import simulate
from observatory.bake import POS_SCALE, Baker
from observatory.events import RunScanner, check_summary, parse_verdicts
from observatory.export import export_run
from observatory.server import Observatory, make_handler, scan_for_tokens

REJECTED = (
    "REJECTED\nC0 physics: PASS value=0.000 threshold=0.02. stable\n"
    "C1 existence: FAIL value=0.292 threshold=0.8. oracle hit 14/48 goals"
)
CERTIFIED = (
    "CERTIFIED\nC0 physics: PASS value=0.000 threshold=0.02. stable\n"
    "C3 learnability (gray-box reference learner): WARN value=0.400 threshold=0.7. low"
)


def _json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def _line(path: Path, obj, newline: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(obj) + ("\n" if newline else ""))


def _tool(ms: int, command: str, stdout: str) -> dict:
    return {
        "type": "tool_call",
        "subtype": "completed",
        "call_id": f"c{ms}",
        "timestamp_ms": ms,
        "tool_call": {
            "shellToolCall": {
                "args": {"command": command},
                "result": {"success": {"stdout": stdout, "exitCode": 0}},
            }
        },
    }


@pytest.fixture()
def run(tmp_path):
    root = tmp_path / "runs" / "obs-test"
    sub = spring_launcher.submission()
    world = sample_world(np.random.default_rng(0))
    thetas = twin_instances(world, sub.device, np.random.default_rng(1))
    _json(root / "referee" / "secrets.json", {"seed": 0, "world": world, "canary": "x"})
    _json(root / "referee" / "submissions" / "r1_a1.json", sub.model_dump())
    _json(root / "referee" / "certificates" / "r1_a1.json", {"report": REJECTED, "stats": {}})
    (root / "builder" / "inbox").mkdir(parents=True)
    (root / "builder" / "inbox" / "round01_call01.md").write_text("go")
    return root, sub, thetas


def _certify(root: Path, sub, thetas) -> None:
    _json(root / "referee" / "submissions" / "r1_a2.json", sub.model_dump())
    _json(root / "referee" / "certificates" / "r1_a2.json", {"report": CERTIFIED, "stats": {}})
    _json(root / "referee" / "instances" / "r1.json", {"A": thetas[0], "B": thetas[1]})
    _json(root / "public" / "cards" / "v1.json", build_card(sub, 1).model_dump())


def test_verdict_and_local_check_parsing():
    v = parse_verdicts(REJECTED)
    assert [x["decision"] for x in v] == ["pass", "fail"]
    assert v[0]["threshold"] == 0.02 and v[1]["value"] == 0.292 and "14/48" in v[1]["detail"]
    assert parse_verdicts(CERTIFIED)[1]["decision"] == "warn"
    assert check_summary("[time] 3 min\nCONSTRUCTION REJECTED\n[shape] too small")["result"] == (
        "construction_rejected"
    )
    assert check_summary(CERTIFIED)["result"] == "certified"
    assert check_summary("hello") is None


def test_scanner_follows_a_growing_run(run):
    root, sub, thetas = run
    scanner = RunScanner(root)
    first = scanner.poll()
    kinds = [e.kind for e in first]
    assert {"run", "world", "submission", "certificate"} <= set(kinds)
    world = next(e for e in first if e.kind == "world")
    assert world.truth and "canary" not in json.dumps(world.data)
    assert scanner.poll() == []

    _certify(root, sub, thetas)
    learner = root / "referee" / "transcripts" / "learner_v1_main_s1.jsonl"
    _line(learner, {"type": "system", "subtype": "init", "model": "m"})
    _line(learner, {"type": "thinking", "subtype": "delta", "text": "try the ", "timestamp_ms": 1})
    _line(learner, {"type": "thinking", "subtype": "delta", "text": "middle", "timestamp_ms": 2})
    _line(learner, {"type": "thinking", "subtype": "completed", "timestamp_ms": 3000})
    _line(learner, _tool(4000, "./lab goal", '{"phase": "pretest", "index": 0, "goal": [0.6]}'))
    _line(
        learner,
        _tool(
            5000,
            "./lab answer '{\"compression\": -0.08}' && ./lab goal",
            '{"recorded": true, "next_phase": "pretest"}\n'
            '{"phase": "pretest", "index": 1, "goal": [0.64]}',
        ),
    )
    _line(
        learner, _tool(6000, "./lab answer '{\"compression\": -0.1}'", "ERROR: bad"), newline=False
    )
    obs = {
        "index": 0,
        "probe": False,
        "knobs": {"compression": -0.1},
        "prediction": [0.6],
        "outcome": [0.61],
        "status": "ok",
        "times": [0.0],
        "traces": {"plunger_pos": [0.0]},
    }
    _json(root / "learner" / "main" / "data" / "v1_main_s1" / "exp_000.json", obs)
    _json(root / "learner" / "twin01" / "data" / "v1_main_s1" / "exp_000.json", obs)

    second = scanner.poll()
    by = {e.kind: e for e in second}
    assert by["card"].round == 1 and by["certificate"].data["passed"]
    assert by["thought"].data["text"] == "try the middle" and by["thought"].label == "A"
    goals = [e for e in second if e.kind == "goal"]
    assert [g.data["index"] for g in goals] == [0, 1]
    answers = [e for e in second if e.kind == "answer"]
    assert len(answers) == 1 and answers[0].data["knobs"] == {"compression": -0.08}
    assert answers[0].data["phase"] == "pretest" and answers[0].round == 1
    exps = [e for e in second if e.kind == "experiment"]
    assert len(exps) == 1 and exps[0].label == "A", "copied twin data must not count twice"
    assert all(e.seq == i for i, e in enumerate(scanner.events))

    with learner.open("a") as f:
        f.write("\n")
    third = scanner.poll()
    assert [e.kind for e in third] == ["tool"], "a line is read once it is complete"


def test_replay_matches_a_direct_simulation(run, tmp_path):
    root, sub, thetas = run
    _certify(root, sub, thetas)
    knobs = {"compression": -0.1}
    rep = Baker(root, tmp_path / "cache").replay(1, "A", knobs)
    direct = simulate(compile_device(sub.device, thetas[0]), sub.task, knobs)
    assert rep["outcome"] == pytest.approx(direct.outcome.tolist())
    frames = np.frombuffer(base64.b64decode(rep["data"]), dtype="<i2").reshape(
        rep["frames"], len(rep["parts"]), 7
    )
    ball = rep["parts"].index("ball")
    assert frames[0, ball, 2] / POS_SCALE == pytest.approx(0.32, abs=0.02)
    assert np.allclose(np.linalg.norm(frames[:, :, 3:] / 32767, axis=2), 1, atol=1e-3)


def test_export_refuses_an_unfinished_run(run, tmp_path):
    root, _, _ = run
    with pytest.raises(SystemExit, match="has not finished"):
        export_run(root, tmp_path / "bundle", tmp_path / "cache", log=lambda *_: None)


def test_token_audit_finds_a_planted_token(tmp_path):
    (tmp_path / "learner").mkdir()
    (tmp_path / "learner" / "notes.md").write_text("curl localhost?token=abc123")
    assert scan_for_tokens([tmp_path / "learner"], ["abc123"]) == [
        str(tmp_path / "learner" / "notes.md")
    ]
    assert scan_for_tokens([tmp_path / "learner"], ["zzz"]) == []


def test_server_requires_token_and_local_host(run, tmp_path):
    root, _, _ = run
    obs = Observatory(root.parent, tmp_path / "recorded", tmp_path / "dist", "s3cret")
    port_box = [0]
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(obs, port_box))
    port_box[0] = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def get(path: str, host: str | None = None) -> tuple[int, bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", port_box[0], timeout=5)
        conn.request("GET", path, headers={"Host": host or f"127.0.0.1:{port_box[0]}"})
        resp = conn.getresponse()
        return resp.status, resp.read()

    try:
        assert get("/api/runs")[0] == 401
        assert get("/api/runs?token=wrong")[0] == 401
        assert get("/api/runs?token=s3cret", host="evil.example:80")[0] == 421
        code, body = get("/api/runs?token=s3cret")
        assert code == 200 and json.loads(body)["runs"][0]["run_id"] == "obs-test"
        code, body = get("/api/runs/obs-test/events?token=s3cret")
        assert code == 200 and json.loads(body)["events"][0]["kind"] == "run"
        assert get("/api/runs/..%2Fsecrets/events?token=s3cret")[0] == 404
        assert get("/recorded/../../etc/passwd?token=s3cret")[0] == 404
    finally:
        httpd.shutdown()
        httpd.server_close()
