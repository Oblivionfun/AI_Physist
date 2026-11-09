"""Referee meta-evaluation: labeled good designs must certify, labeled cheats must fail at
the expected certificate. Any change to certificate rules must keep this file green."""

import numpy as np
import pytest

from fixtures.devices import pendulum_striker, spring_launcher
from fixtures.devices.cheats import CERTIFICATE_CHEATS, gated_ramp
from mlab.catalog import sample_world
from mlab.referee.certify import FAST, FULL, TEST, Certificate, Verdict, certify


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


def test_identifiable_three_knob_device_certifies(world):
    """Positive control for the 'unidentifiable within budget' cheat: the same device with its
    sensors and budget passes the identifiability gate."""
    cert = certify(gated_ramp(), world, np.random.default_rng(3), TEST)
    assert cert.passed, cert.report()


def test_a_warning_does_not_block_certification():
    warn = Verdict("C3", "learnability (gray-box reference learner)", "warn", 0.4, 0.7, "low")
    cert = Certificate(verdicts=[Verdict("C0", "physics", "pass", 0.0, 0.02, ""), warn])
    assert cert.passed and cert.first_failure is None and "WARN" in warn.line()


@pytest.mark.slow
@pytest.mark.parametrize("seed", [7, 8])
@pytest.mark.parametrize("module", [pendulum_striker, spring_launcher])
def test_good_fixtures_certify_full(module, seed):
    world = sample_world(np.random.default_rng(seed))
    cert = certify(module.submission(), world, np.random.default_rng(1), FULL)
    assert cert.passed, cert.report()
