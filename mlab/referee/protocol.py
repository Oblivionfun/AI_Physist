"""Schemas of everything that crosses an agent boundary. Nothing else may cross."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TicketCategory = Literal["interface_bug", "ambiguous_spec", "suspected_unsolvable", "too_easy", "other"]


class KnobSpec(BaseModel):
    name: str
    low: float
    high: float
    unit: str
    description: str


class SensorSpec(BaseModel):
    name: str
    kind: str
    part: str
    noise: float
    rate_hz: float


class UnknownSpec(BaseModel):
    name: str
    description: str
    low: float
    high: float
    unit: str
    scope: str = "world"


class ModifiableSpec(BaseModel):
    name: str
    current: float
    low: float
    high: float


class OutcomeSpec(BaseModel):
    kind: str
    part: str
    axes: list[str]
    description: str
    noise: float
    goal_space: list[tuple[float, float]]
    tolerance: float


class ProtocolSpec(BaseModel):
    pretest_goals: int
    budget: int
    probe_every: int
    exam_goals: int
    horizon: float


class TaskCard(BaseModel):
    version: int
    title: str
    goal_text: str
    manual: str
    knobs: list[KnobSpec]
    sensors: list[SensorSpec]
    unknowns: list[UnknownSpec]
    outcome: OutcomeSpec
    modifiable: list[ModifiableSpec]
    protocol: ProtocolSpec
    rules: str
    changelog: list[str] = []


class BeliefEntry(BaseModel):
    value: float
    low: float
    high: float


class Belief(BaseModel):
    estimates: dict[str, BeliefEntry] = {}


class FieldTicket(BaseModel):
    category: TicketCategory
    text: str = Field(max_length=280)


class ExperimentObs(BaseModel):
    index: int
    probe: bool
    knobs: dict[str, float]
    prediction: list[float]
    outcome: list[float] | None
    status: str
    times: list[float]
    traces: dict[str, list]
