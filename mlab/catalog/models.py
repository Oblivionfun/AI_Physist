from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

JointKind = Literal["hinge", "slide"]


@dataclass(frozen=True)
class JointModel:
    """A bearing or rail type; damping and friction loss are hidden world properties."""

    name: str
    kind: JointKind
    description: str


@dataclass(frozen=True)
class SpringModel:
    """A spring type; stiffness is a hidden world property."""

    name: str
    kind: JointKind
    description: str


@dataclass(frozen=True)
class MotorModel:
    """A motor type; gain (torque or force per unit command) is a hidden world property."""

    name: str
    kind: JointKind
    description: str


JOINT_MODELS: dict[str, JointModel] = {
    "bearing": JointModel("bearing", "hinge", "ball-bearing pivot, low loss"),
    "bushing": JointModel("bushing", "hinge", "plain bushing pivot, higher loss"),
    "rail": JointModel("rail", "slide", "linear guide rail"),
}

SPRING_MODELS: dict[str, SpringModel] = {
    "torsion_soft": SpringModel("torsion_soft", "hinge", "soft torsion spring"),
    "torsion_stiff": SpringModel("torsion_stiff", "hinge", "stiff torsion spring"),
    "coil_soft": SpringModel("coil_soft", "slide", "soft compression coil"),
    "coil_stiff": SpringModel("coil_stiff", "slide", "stiff compression coil"),
}

MOTOR_MODELS: dict[str, MotorModel] = {
    "motor_small": MotorModel("motor_small", "hinge", "small geared DC motor"),
    "motor_large": MotorModel("motor_large", "hinge", "large geared DC motor"),
    "linear_actuator": MotorModel("linear_actuator", "slide", "voice-coil linear actuator"),
}

# Sensor noise floors (standard deviation); builders may only ask for noisier sensors.
SENSOR_MIN_NOISE: dict[str, float] = {
    "joint_angle": 0.002,
    "joint_velocity": 0.01,
    "position": 0.002,
    "velocity": 0.01,
}

OUTCOME_NOISE: dict[str, float] = {
    "position": 0.003,
    "angle": 0.003,
}
