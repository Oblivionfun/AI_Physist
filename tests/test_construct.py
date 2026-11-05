import numpy as np
import pytest

from fixtures.devices import pendulum_striker, spring_launcher
from fixtures.devices.cheats import CONSTRUCTION_CHEATS
from mlab.construct import (
    ConstructionError,
    check_device,
    check_task,
    compile_device,
    describe_device,
)
from mlab.construct.checks import nominal_theta


@pytest.mark.parametrize("module", [pendulum_striker, spring_launcher])
def test_good_fixtures_build_and_validate(module):
    sub = module.submission()
    issues, compiled = check_device(sub.device)
    assert issues == []
    assert compiled is not None
    assert check_task(sub.device, sub.task) == []


@pytest.mark.parametrize("cheat", CONSTRUCTION_CHEATS, ids=lambda c: c.name)
def test_construction_cheats_are_rejected(cheat):
    with pytest.raises(ConstructionError) as err:
        cheat.attempt()
    codes = {i.code for i in err.value.issues}
    assert cheat.expected_code in codes, err.value


def test_rejected_call_leaves_device_unchanged():
    b = pendulum_striker.build_device()
    before = b.device.model_dump()
    with pytest.raises(ConstructionError):
        b.free("intruder", "box", [0.03, 0.03, 0.03], "steel", (0.0, 0.0, 0.17))
    assert b.device.model_dump() == before
    assert b.log[-1]["ok"] is False


def test_description_never_contains_hidden_values():
    sub = pendulum_striker.submission()
    theta = nominal_theta(sub.device)
    theta["head_mass"] = 1.23456
    compile_device(sub.device, theta)
    text = describe_device(sub.device)
    assert "1.23456" not in text and "1.235" not in text
    assert "sealed, mass unknown (between 0.5 and 2.5 kg)" in text


def test_compiled_names_are_neutral():
    sub = spring_launcher.submission()
    xml = compile_device(sub.device, nominal_theta(sub.device)).xml
    for p in sub.device.parts:
        assert f'"{p.name}"' not in xml
    assert "plunger" not in xml and "ball" not in xml


def test_fixed_parts_share_a_weld_and_pins_exclude_only_their_parent():
    sub = pendulum_striker.submission()
    dev = compile_device(sub.device, nominal_theta(sub.device))
    m = dev.model
    assert m.body_weldid[dev.part_body["head"]] == m.body_weldid[dev.part_body["arm"]]
    assert m.nexclude == 1
    assert np.isclose(m.opt.timestep, 0.001)
