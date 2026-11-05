import numpy as np

from fixtures.devices import pendulum_striker, spring_launcher
from mlab.construct import compile_device
from mlab.construct.checks import nominal_theta
from mlab.sim import prepare, simulate
from mlab.sim.runner import knob_values


def _dev(module, **overrides):
    sub = module.submission()
    theta = nominal_theta(sub.device)
    theta.update(overrides)
    return sub, compile_device(sub.device, theta)


def test_simulation_is_deterministic_without_noise():
    sub, dev = _dev(pendulum_striker)
    a = simulate(dev, sub.task, {"pull_back": 0.9})
    b = simulate(dev, sub.task, {"pull_back": 0.9})
    assert a.status == "ok"
    assert np.array_equal(a.outcome, b.outcome)


def test_setup_sets_joint_and_latch_holds_it():
    sub, dev = _dev(spring_launcher)
    data = prepare(dev, sub.task, knob_values(sub.task, {"compression": -0.1}))
    adr = dev.model.jnt_qposadr[dev.part_joint["plunger"]]
    assert np.isclose(data.qpos[adr], -0.1)
    assert bool(data.eq_active[dev.latch_eq["trigger"]])


def test_latch_release_launches_the_ball():
    sub, dev = _dev(spring_launcher)
    r = simulate(dev, sub.task, {"compression": -0.12})
    assert r.status == "ok"
    assert r.outcome[0] > 0.4


def test_outcome_depends_on_hidden_quantities():
    sub, light = _dev(pendulum_striker, head_mass=0.6)
    _, heavy = _dev(pendulum_striker, head_mass=2.4)
    a = simulate(light, sub.task, {"pull_back": 1.0}).outcome[0]
    b = simulate(heavy, sub.task, {"pull_back": 1.0}).outcome[0]
    assert b - a > 0.1


def test_knob_bounds_are_enforced():
    sub, dev = _dev(pendulum_striker)
    try:
        simulate(dev, sub.task, {"pull_back": 3.0})
    except ValueError as exc:
        assert "outside" in str(exc)
    else:
        raise AssertionError("out-of-range knob accepted")
