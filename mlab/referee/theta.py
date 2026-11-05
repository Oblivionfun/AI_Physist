"""Hidden-parameter bookkeeping. Only referee code may hold true values."""

from __future__ import annotations

import numpy as np

from mlab.catalog.priors import Prior, nominal_value, sample_prior
from mlab.catalog.world import WORLD_PRIORS
from mlab.construct.compile import used_world_keys
from mlab.construct.ir import DeviceIR


def hidden_priors(device: DeviceIR) -> dict[str, Prior]:
    """Every unknown that can influence this device: used world properties + device hidden."""
    priors: dict[str, Prior] = {k: WORLD_PRIORS[k] for k in sorted(used_world_keys(device))}
    for h in device.hidden:
        priors[h.name] = h
    return priors


def instance_theta(world: dict[str, float], device: DeviceIR, rng: np.random.Generator) -> dict[str, float]:
    theta = dict(world)
    for h in device.hidden:
        theta[h.name] = sample_prior(h, rng)
    return theta


def twin_instances(world: dict[str, float], device: DeviceIR,
                   rng: np.random.Generator) -> list[dict[str, float]]:
    """Two instances whose device-specific unknowns are antithetic (half a prior width apart
    in unit coordinates), so the swap test always compares genuinely different devices."""
    a, b = dict(world), dict(world)
    for h in device.hidden:
        u = float(rng.uniform())
        a[h.name] = h.from_unit(u)
        b[h.name] = h.from_unit((u + 0.5) % 1.0)
    return [a, b]


def prior_instance(world: dict[str, float], device: DeviceIR, rng: np.random.Generator) -> dict[str, float]:
    """A hypothetical instance with every relevant unknown redrawn from its prior."""
    theta = dict(world)
    for key, prior in hidden_priors(device).items():
        theta[key] = sample_prior(prior, rng)
    return theta


def nominal_instance(device: DeviceIR) -> dict[str, float]:
    theta = {k: nominal_value(p) for k, p in WORLD_PRIORS.items()}
    for h in device.hidden:
        theta[h.name] = nominal_value(h)
    return theta


def to_unit(theta: dict[str, float], priors: dict[str, Prior]) -> np.ndarray:
    return np.array([priors[k].to_unit(theta[k]) for k in priors])


def with_unit(base: dict[str, float], priors: dict[str, Prior], u: np.ndarray) -> dict[str, float]:
    theta = dict(base)
    for k, ui in zip(priors, u, strict=True):
        theta[k] = priors[k].from_unit(float(ui))
    return theta
