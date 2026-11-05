from __future__ import annotations

import numpy as np

from mlab.catalog.materials import MATERIALS
from mlab.catalog.models import JOINT_MODELS, MOTOR_MODELS, SPRING_MODELS
from mlab.catalog.priors import Prior, sample_prior


def world_key(kind: str, name: str) -> str:
    return f"{kind}.{name}"


def _build_world_priors() -> dict[str, Prior]:
    sliding = {
        "steel": (0.15, 0.45),
        "aluminium": (0.20, 0.55),
        "wood": (0.25, 0.65),
        "rubber": (0.60, 1.20),
        "concrete": (0.40, 0.90),
    }
    priors: dict[str, Prior] = {}
    for mat, (lo, hi) in sliding.items():
        priors[world_key("friction", mat)] = Prior(
            low=lo, high=hi, unit="-", description=f"sliding friction coefficient of {mat}"
        )
    for mat in MATERIALS:
        priors[world_key("rolling", mat)] = Prior(
            low=2e-4,
            high=1.5e-3,
            scale="log",
            unit="m",
            description=f"rolling resistance length of {mat}",
        )

    joint_loss = {
        "bearing": ((0.002, 0.015), (0.0005, 0.004)),
        "bushing": ((0.015, 0.12), (0.004, 0.03)),
        "rail": ((0.1, 0.8), (0.05, 0.4)),
    }
    for name, ((dlo, dhi), (flo, fhi)) in joint_loss.items():
        unit_d = "N*m*s/rad" if JOINT_MODELS[name].kind == "hinge" else "N*s/m"
        unit_f = "N*m" if JOINT_MODELS[name].kind == "hinge" else "N"
        priors[world_key("damping", name)] = Prior(
            low=dlo, high=dhi, scale="log", unit=unit_d, description=f"{name} viscous damping"
        )
        priors[world_key("frictionloss", name)] = Prior(
            low=flo, high=fhi, scale="log", unit=unit_f, description=f"{name} dry friction"
        )

    stiffness = {
        "torsion_soft": (0.5, 3.0, "N*m/rad"),
        "torsion_stiff": (3.0, 20.0, "N*m/rad"),
        "coil_soft": (40.0, 250.0, "N/m"),
        "coil_stiff": (250.0, 1500.0, "N/m"),
    }
    for name, (lo, hi, unit) in stiffness.items():
        assert name in SPRING_MODELS
        priors[world_key("stiffness", name)] = Prior(
            low=lo, high=hi, scale="log", unit=unit, description=f"{name} stiffness"
        )

    gains = {
        "motor_small": (0.3, 1.2, "N*m"),
        "motor_large": (1.5, 6.0, "N*m"),
        "linear_actuator": (5.0, 30.0, "N"),
    }
    for name, (lo, hi, unit) in gains.items():
        assert name in MOTOR_MODELS
        priors[world_key("gain", name)] = Prior(
            low=lo, high=hi, unit=unit, description=f"{name} output per unit command"
        )
    return priors


WORLD_PRIORS: dict[str, Prior] = _build_world_priors()


def sample_world(rng: np.random.Generator) -> dict[str, float]:
    """Draw theta_world once per run; only the referee ever holds the result."""
    return {key: sample_prior(prior, rng) for key, prior in sorted(WORLD_PRIORS.items())}
