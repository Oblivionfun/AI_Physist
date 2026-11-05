import numpy as np
import pytest

from fixtures.devices import pendulum_striker, spring_launcher
from mlab.catalog import sample_world
from mlab.construct import compile_device
from mlab.referee.manual import build_card
from mlab.referee.session import LearnerSession, ProtocolError
from mlab.referee.theta import twin_instances


@pytest.fixture()
def session():
    sub = spring_launcher.submission()
    world = sample_world(np.random.default_rng(7))
    theta = twin_instances(world, sub.device, np.random.default_rng(1))[0]
    dev = compile_device(sub.device, theta)
    return LearnerSession(sub, dev, build_card(sub, 1), np.random.default_rng(2))


def _finish_pretest(s: LearnerSession) -> None:
    while s.phase == "pretest":
        s.answer({"compression": -0.08})


def test_no_experiments_before_pretest(session):
    with pytest.raises(ProtocolError):
        session.experiment({"compression": -0.08}, [0.6])
    assert session.current_goal()["remaining"] == 3


def test_pretest_results_are_withheld(session):
    reply = session.answer({"compression": -0.08})
    assert "outcome" not in reply and "success" not in reply


def test_prediction_is_mandatory_and_shaped(session):
    _finish_pretest(session)
    with pytest.raises(ProtocolError):
        session.experiment({"compression": -0.08}, [])
    obs = session.experiment({"compression": -0.08}, [0.6])
    assert obs["prediction"] == [0.6] and obs["index"] == 0


def test_probe_every_tenth_experiment(session):
    _finish_pretest(session)
    for _ in range(9):
        session.experiment({"compression": -0.08}, [0.6])
    assert session.status()["probe_due"]
    with pytest.raises(ProtocolError):
        session.experiment({"compression": -0.08}, [0.6])
    knobs = session.probe()["knobs"]
    obs = session.probe_result([0.6])
    assert obs["probe"] and obs["knobs"] == knobs


def test_budget_is_enforced(session):
    _finish_pretest(session)
    while len(session.record.lab) < session.task.budget:
        if session.status()["probe_due"]:
            session.probe()
            session.probe_result([0.6])
        else:
            session.experiment({"compression": -0.08}, [0.6])
    with pytest.raises(ProtocolError):
        session.experiment({"compression": -0.08}, [0.6])


def test_exam_forbids_experiments_and_results_come_last(session):
    _finish_pretest(session)
    session.finish_lab()
    session.submit_theory("def predict(knobs, visible):\n    return [0.6]\n", None)
    with pytest.raises(ProtocolError):
        session.experiment({"compression": -0.08}, [0.6])
    while session.phase == "exam":
        session.answer({"compression": -0.08})
    with pytest.raises(ProtocolError):
        session.results()
    done = session.field_report([{"category": "other", "text": "fine"}])
    assert len(done["results"]["exam"]) == 8
    assert all("observed_outcome" in r for r in done["results"]["exam"])


def test_theory_must_define_predict(session):
    _finish_pretest(session)
    session.finish_lab()
    with pytest.raises(ProtocolError):
        session.submit_theory("x = 1\n", None)


def test_twins_differ_in_device_unknowns():
    sub = pendulum_striker.submission()
    world = sample_world(np.random.default_rng(7))
    a, b = twin_instances(world, sub.device, np.random.default_rng(3))
    prior = sub.device.hidden[0]
    assert abs(prior.to_unit(a["head_mass"]) - prior.to_unit(b["head_mass"])) == pytest.approx(0.5)
    assert all(a[k] == b[k] for k in world)
