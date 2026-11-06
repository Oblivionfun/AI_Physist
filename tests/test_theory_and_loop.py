import json
import re
from pathlib import Path

import numpy as np

from fixtures.devices import pendulum_striker
from mlab.agents.builders.reference import ReferenceBuilder
from mlab.catalog import sample_world
from mlab.construct import compile_device
from mlab.orchestrator import Orchestrator, RecordedBuilder, RunConfig, offline_learner
from mlab.referee.channel import verify
from mlab.referee.theory_eval import QuerySet, build_query_sets, run_theory, score
from mlab.referee.theta import twin_instances

ROOT = Path(__file__).resolve().parents[1]


def test_theory_runs_isolated_and_survives_errors():
    code = ("def predict(knobs, visible):\n"
            "    if knobs['k'] < 0:\n"
            "        raise ValueError('nope')\n"
            "    return [knobs['k'] * 2]\n")
    out = run_theory(code, [{"knobs": {"k": 1.0}, "visible": {}}, {"knobs": {"k": -1.0}, "visible": {}}])
    assert out == [[2.0], None]
    assert run_theory("def predict(:\n", [{"knobs": {}, "visible": {}}]) is None


def test_score_counts_hits_against_tolerance():
    qs = QuerySet("t", [{}, {}, {}], [[0.0], [1.0], None])
    s = score(qs, [[0.01], [1.5], [3.0]], tolerance=0.1)
    assert s.n == 2 and s.hit_rate == 0.5


def test_modified_query_set_changes_ground_truth():
    sub = pendulum_striker.submission()
    world = sample_world(np.random.default_rng(7))
    theta = twin_instances(world, sub.device, np.random.default_rng(1))[0]
    dev = compile_device(sub.device, theta)
    lab = [{"pull_back": v} for v in np.linspace(0.3, 1.2, 10)]
    sets = build_query_sets(sub, dev, lab, np.random.default_rng(2), n=4)
    names = [s.name for s in sets]
    assert names[0] == "in_distribution" and any(n.startswith("modified") for n in names)
    base = sets[0]
    mod = next(s for s in sets if s.name.startswith("modified"))
    assert [q["knobs"] for q in base.queries] == [q["knobs"] for q in mod.queries]
    assert base.queries[0]["visible"] != mod.queries[0]["visible"]


def test_offline_loop_runs_one_round(tmp_path):
    cfg = RunConfig(run_id="t", rounds=1, seed=3, profile="test", runs_dir=tmp_path)
    summary = Orchestrator(cfg, ReferenceBuilder(), offline_learner(3), log=lambda *_: None).run()
    assert summary["rounds"][0]["round"] == 1
    ok, n = verify(tmp_path / "t" / "public" / "channel.jsonl")
    assert ok and n >= 1
    assert (tmp_path / "t" / "referee" / "secrets.json").exists()
    assert not list((tmp_path / "t" / "public").rglob("secrets*"))


def test_rerun_reuses_world_devices_and_instances(tmp_path):
    src = RunConfig(run_id="src", rounds=1, seed=5, profile="test", runs_dir=tmp_path)
    Orchestrator(src, ReferenceBuilder(), offline_learner(5), log=lambda *_: None).run()
    secrets = json.loads((tmp_path / "src" / "referee" / "secrets.json").read_text())
    again = RunConfig(run_id="again", rounds=1, seed=secrets["seed"], profile="test",
                      runs_dir=tmp_path, instances_from=tmp_path / "src")
    summary = Orchestrator(again, RecordedBuilder(tmp_path / "src"), offline_learner(9),
                           log=lambda *_: None).run()
    assert summary["rounds"][0]["status"] == "ok"
    for name in ("secrets.json", "instances/r1.json"):
        a = json.loads((tmp_path / "src" / "referee" / name).read_text())
        b = json.loads((tmp_path / "again" / "referee" / name).read_text())
        assert a.get("world", a) == b.get("world", b) if name == "secrets.json" else a == b


def test_learner_side_code_has_no_device_specifics():
    """AGENTS.md red line 1: learner-side code must be device-agnostic."""
    names = set()
    for f in (ROOT / "fixtures" / "devices").glob("*.py"):
        names.update(re.findall(r'"([a-z_]{4,})"', f.read_text()))
    for f in (ROOT / "mlab" / "agents" / "builders").glob("*.py"):
        names.update(re.findall(r'"([a-z_]{4,})"', f.read_text()))
    generic = {"hinge", "slide", "fixed", "free", "base", "position", "velocity", "joint_angle",
               "joint_velocity", "landing_point", "final_position", "max_height", "steel", "wood",
               "aluminium", "rubber", "concrete", "sphere", "capsule", "cylinder", "trigger",
               "other", "phase", "exam", "pretest", "goal", "knobs", "name", "outcome", "theory",
               "final_joint_angle", "bearing", "bushing", "rail", "linear", "baseline", "prior",
               "support", "overlap", "anchor", "detached", "density"}
    device_terms = names - generic
    learner_files = list((ROOT / "mlab" / "agents" / "learners").glob("*.py"))
    for f in learner_files:
        text = f.read_text()
        hits = sorted(t for t in device_terms if re.search(rf"\b{t}\b", text))
        assert not hits, f"{f.name} mentions device-specific terms {hits}"
