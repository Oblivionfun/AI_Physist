"""Referee meta-evaluation: labeled good designs must certify, labeled cheats must fail at
the expected certificate. Any change to certificate rules must keep this file green."""

import numpy as np
import pytest

from fixtures.devices import pendulum_striker, spring_launcher
from fixtures.devices.cheats import CERTIFICATE_CHEATS
from mlab.catalog import sample_world
from mlab.referee.certify import FAST, FULL, TEST, certify


@pytest.fixture(scope="module")
def world():
    return sample_world(np.random.default_rng(7))


@pytest.mark.parametrize("cheat", CERTIFICATE_CHEATS, ids=lambda c: c.name)
def test_certificate_cheats_fail_at_expected_gate(cheat, world):
    cert = certify(cheat.submission(), world, np.random.default_rng(3), TEST)
    assert not cert.passed, cert.report()
    assert cert.first_failure.code in cheat.expected_codes, cert.report()
    assert cheat.expected_check in cert.first_failure.title, cert.report()


def test_spring_launcher_certifies(world):
    cert = certify(spring_launcher.submission(), world, np.random.default_rng(1), FAST)
    assert cert.passed, cert.report()


@pytest.mark.slow
@pytest.mark.parametrize("seed", [7, 8])
@pytest.mark.parametrize("module", [pendulum_striker, spring_launcher])
def test_good_fixtures_certify_full(module, seed):
    world = sample_world(np.random.default_rng(seed))
    cert = certify(module.submission(), world, np.random.default_rng(1), FULL)
    assert cert.passed, cert.report()
