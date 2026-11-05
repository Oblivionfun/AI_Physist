import numpy as np
import pytest
from pydantic import ValidationError

from mlab.catalog import WORLD_PRIORS, Prior, sample_world
from mlab.catalog.priors import MAX_PRIOR_RATIO


def test_world_sampling_is_seeded_and_within_priors():
    a = sample_world(np.random.default_rng(5))
    b = sample_world(np.random.default_rng(5))
    assert a == b
    for key, value in a.items():
        p = WORLD_PRIORS[key]
        assert p.low <= value <= p.high


def test_every_world_prior_respects_ratio_cap():
    for key, p in WORLD_PRIORS.items():
        if p.low > 0:
            assert p.high / p.low <= MAX_PRIOR_RATIO, key


def test_inflated_prior_is_rejected():
    with pytest.raises(ValidationError):
        Prior(low=0.1, high=5.0)


def test_unit_mapping_roundtrip():
    p = Prior(low=0.2, high=1.6, scale="log")
    for v in (0.2, 0.5, 1.6):
        assert abs(p.from_unit(p.to_unit(v)) - v) < 1e-12
