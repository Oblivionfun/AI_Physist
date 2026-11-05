"""Serializable construction record (DeviceIR) and task declaration (TaskIR).

All poses are world-frame poses of the initial configuration, where every hinge and slide
coordinate is zero. Joint ranges, spring rest positions and setup values are expressed in
that joint coordinate.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from mlab.catalog.priors import NamedPrior

Name = str
NAME_PATTERN = r"^[a-z][a-z0-9_]{0,31}$"
Vec3 = tuple[float, float, float]

ShapeKind = Literal["box", "sphere", "capsule", "cylinder"]
MountKind = Literal["base", "fixed", "hinge", "slide", "free"]
SensorKind = Literal["joint_angle", "joint_velocity", "position", "velocity"]
OutcomeKind = Literal["landing_point", "final_position", "max_height", "final_joint_angle"]
Axis = Literal["x", "y", "z"]


class ShapeIR(BaseModel):
    """box: half extents (3); sphere: [radius]; capsule/cylinder: [radius, half_length] on local z."""

    kind: ShapeKind
    size: list[float]


class SpringIR(BaseModel):
    model: str
    rest: float = 0.0


class MountIR(BaseModel):
    kind: MountKind
    parent: Name | None = None
    anchor: Vec3 | None = None
    axis: Vec3 | None = None
    joint_model: str | None = None
    spring: SpringIR | None = None
    range: tuple[float, float] | None = None
    carried_by: Name | None = None


class PartIR(BaseModel):
    name: Name = Field(pattern=NAME_PATTERN)
    shape: ShapeIR
    material: str
    pos: Vec3
    euler: Vec3 = (0.0, 0.0, 0.0)
    hidden_mass: Name | None = None
    mount: MountIR


class ActuatorIR(BaseModel):
    name: Name = Field(pattern=NAME_PATTERN)
    part: Name
    model: str


class LatchIR(BaseModel):
    """Locks a hinge or slide at its value at t=0 until released by the action program."""

    name: Name = Field(pattern=NAME_PATTERN)
    part: Name


class SensorIR(BaseModel):
    name: Name = Field(pattern=NAME_PATTERN)
    kind: SensorKind
    part: Name
    noise: float


class ZoneIR(BaseModel):
    """Purely visual marker (no collision); goals are defined in the task."""

    name: Name = Field(pattern=NAME_PATTERN)
    pos: Vec3
    size: tuple[float, float]


class DeviceIR(BaseModel):
    name: Name = Field(pattern=NAME_PATTERN)
    parts: list[PartIR] = []
    actuators: list[ActuatorIR] = []
    latches: list[LatchIR] = []
    sensors: list[SensorIR] = []
    hidden: list[NamedPrior] = []
    zones: list[ZoneIR] = []

    def part(self, name: str) -> PartIR:
        for p in self.parts:
            if p.name == name:
                return p
        raise KeyError(name)

    def has_part(self, name: str) -> bool:
        return any(p.name == name for p in self.parts)


class KnobIR(BaseModel):
    name: Name = Field(pattern=NAME_PATTERN)
    low: float
    high: float
    unit: str = ""
    description: str = ""


KnobRef = float | str


class SetupIR(BaseModel):
    """Initial joint coordinate of a jointed part, e.g. how far an arm is cocked back."""

    part: Name
    value: KnobRef


class PhaseIR(BaseModel):
    duration: KnobRef
    ctrl: dict[Name, KnobRef] = {}
    release: list[Name] = []


class OutcomeIR(BaseModel):
    kind: OutcomeKind
    part: Name
    axes: list[Axis] = ["x"]


class GoalDimIR(BaseModel):
    low: float
    high: float


class ModifiableIR(BaseModel):
    """A visible dimension the referee may change publicly in counterfactual tests."""

    part: Name
    field: Literal["size0", "size1", "size2", "posx", "posy", "posz"]
    low: float
    high: float


class TaskIR(BaseModel):
    title: str = Field(max_length=80)
    goal_text: str = Field(max_length=600)
    knobs: list[KnobIR]
    setup: list[SetupIR] = []
    phases: list[PhaseIR] = []
    horizon: float
    outcome: OutcomeIR
    goal_space: list[GoalDimIR]
    tolerance: float
    budget: int = 40
    escalation: list[str] = []
    modifiable: list[ModifiableIR] = []

    def knob(self, name: str) -> KnobIR:
        for k in self.knobs:
            if k.name == name:
                return k
        raise KeyError(name)


class Submission(BaseModel):
    device: DeviceIR
    task: TaskIR
