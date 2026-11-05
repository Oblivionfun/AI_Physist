"""Builder-facing construction API.

Each call validates the candidate device immediately (geometry, support, joints, catalog
models, interpenetration via MuJoCo contacts). Rejected calls leave the device unchanged
and raise ConstructionError with actionable messages. Every call is appended to `log`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import ValidationError

from mlab.catalog.models import SENSOR_MIN_NOISE
from mlab.catalog.priors import NamedPrior
from mlab.construct.checks import ConstructionError, Issue, check_device
from mlab.construct.describe import describe_device, describe_part
from mlab.construct.ir import (
    ActuatorIR,
    DeviceIR,
    LatchIR,
    MountIR,
    PartIR,
    SensorIR,
    ShapeIR,
    SpringIR,
    Vec3,
    ZoneIR,
)


@dataclass(frozen=True)
class Fixed:
    pass


@dataclass(frozen=True)
class Spring:
    model: str
    rest: float = 0.0


@dataclass(frozen=True)
class Hinge:
    anchor: Vec3
    axis: Vec3
    model: str = "bearing"
    spring: Spring | None = None
    range: tuple[float, float] | None = None


@dataclass(frozen=True)
class Slide:
    anchor: Vec3
    axis: Vec3
    range: tuple[float, float]
    model: str = "rail"
    spring: Spring | None = None


Joint = Fixed | Hinge | Slide


class Builder:
    def __init__(self, name: str):
        self._device = DeviceIR(name=name)
        self.log: list[dict] = []

    @property
    def device(self) -> DeviceIR:
        return self._device.model_copy(deep=True)

    def _commit(self, op: str, args: dict, candidate: DeviceIR, summary: str) -> str:
        issues, _ = check_device(candidate)
        if issues:
            self.log.append({"op": op, "args": args, "ok": False, "issues": [str(i) for i in issues]})
            raise ConstructionError(issues)
        self._device = candidate
        self.log.append({"op": op, "args": args, "ok": True})
        return summary

    def _with_part(self, part: PartIR) -> DeviceIR:
        cand = self._device.model_copy(deep=True)
        if cand.has_part(part.name):
            raise ConstructionError([Issue("name", f"part name '{part.name}' is already used")])
        cand.parts.append(part)
        return cand

    def hidden(
        self,
        name: str,
        low: float,
        high: float,
        unit: str,
        scale: Literal["linear", "log"] = "linear",
        description: str = "",
    ) -> str:
        args = {"name": name, "low": low, "high": high, "unit": unit, "scale": scale,
                "description": description}
        try:
            prior = NamedPrior(**args)
        except ValidationError as exc:
            issues = [Issue("prior", e["msg"]) for e in exc.errors()]
            self.log.append({"op": "hidden", "args": args, "ok": False,
                             "issues": [str(i) for i in issues]})
            raise ConstructionError(issues) from None
        cand = self._device.model_copy(deep=True)
        cand.hidden.append(prior)
        return self._commit("hidden", prior.model_dump(), cand, f"declared hidden '{name}'")

    def base(
        self,
        name: str,
        shape: str,
        size: list[float],
        material: str,
        pos: Vec3,
        euler: Vec3 = (0.0, 0.0, 0.0),
    ) -> str:
        part = PartIR(
            name=name,
            shape=ShapeIR(kind=shape, size=list(size)),
            material=material,
            pos=pos,
            euler=euler,
            mount=MountIR(kind="base"),
        )
        cand = self._with_part(part)
        return self._commit("base", part.model_dump(), cand, describe_part(part, cand))

    def attach(
        self,
        name: str,
        shape: str,
        size: list[float],
        material: str,
        pos: Vec3,
        *,
        to: str,
        joint: Joint,
        euler: Vec3 = (0.0, 0.0, 0.0),
        hidden_mass: str | None = None,
    ) -> str:
        if isinstance(joint, Fixed):
            mount = MountIR(kind="fixed", parent=to)
        elif isinstance(joint, Hinge):
            mount = MountIR(
                kind="hinge",
                parent=to,
                anchor=joint.anchor,
                axis=joint.axis,
                joint_model=joint.model,
                spring=SpringIR(model=joint.spring.model, rest=joint.spring.rest)
                if joint.spring
                else None,
                range=joint.range,
            )
        else:
            mount = MountIR(
                kind="slide",
                parent=to,
                anchor=joint.anchor,
                axis=joint.axis,
                joint_model=joint.model,
                spring=SpringIR(model=joint.spring.model, rest=joint.spring.rest)
                if joint.spring
                else None,
                range=joint.range,
            )
        part = PartIR(
            name=name,
            shape=ShapeIR(kind=shape, size=list(size)),
            material=material,
            pos=pos,
            euler=euler,
            hidden_mass=hidden_mass,
            mount=mount,
        )
        cand = self._with_part(part)
        return self._commit("attach", part.model_dump(), cand, describe_part(part, cand))

    def free(
        self,
        name: str,
        shape: str,
        size: list[float],
        material: str,
        pos: Vec3,
        euler: Vec3 = (0.0, 0.0, 0.0),
        hidden_mass: str | None = None,
        carried_by: str | None = None,
    ) -> str:
        part = PartIR(
            name=name,
            shape=ShapeIR(kind=shape, size=list(size)),
            material=material,
            pos=pos,
            euler=euler,
            hidden_mass=hidden_mass,
            mount=MountIR(kind="free", carried_by=carried_by),
        )
        cand = self._with_part(part)
        return self._commit("free", part.model_dump(), cand, describe_part(part, cand))

    def motor(self, name: str, part: str, model: str) -> str:
        cand = self._device.model_copy(deep=True)
        act = ActuatorIR(name=name, part=part, model=model)
        cand.actuators.append(act)
        return self._commit("motor", act.model_dump(), cand, f"motor '{name}' drives '{part}'")

    def latch(self, name: str, part: str) -> str:
        cand = self._device.model_copy(deep=True)
        latch = LatchIR(name=name, part=part)
        cand.latches.append(latch)
        return self._commit("latch", latch.model_dump(), cand, f"latch '{name}' locks '{part}'")

    def sensor(self, name: str, kind: str, part: str, noise: float | None = None) -> str:
        cand = self._device.model_copy(deep=True)
        sensor = SensorIR(
            name=name, kind=kind, part=part, noise=noise if noise is not None else SENSOR_MIN_NOISE[kind]
        )
        cand.sensors.append(sensor)
        return self._commit("sensor", sensor.model_dump(), cand, f"sensor '{name}' on '{part}'")

    def zone(self, name: str, pos: Vec3, radius: float, half_height: float = 0.002) -> str:
        cand = self._device.model_copy(deep=True)
        zone = ZoneIR(name=name, pos=pos, size=(radius, half_height))
        cand.zones.append(zone)
        return self._commit("zone", zone.model_dump(), cand, f"marker '{name}' placed")

    def query(self) -> str:
        return describe_device(self._device)

    def finish(self) -> DeviceIR:
        return self.device
