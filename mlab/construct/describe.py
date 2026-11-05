"""Natural-language description of a device; hidden values are never printed."""

from __future__ import annotations

from mlab.catalog.materials import MATERIALS
from mlab.construct.geometry import part_aabb, shape_volume
from mlab.construct.ir import DeviceIR, PartIR


def _v(x) -> str:
    return "(" + ", ".join(f"{float(c):.3f}" for c in x) + ")"


def _shape(p: PartIR) -> str:
    s = p.shape.size
    if p.shape.kind == "box":
        return f"box {2 * s[0]:.3f} x {2 * s[1]:.3f} x {2 * s[2]:.3f} m"
    if p.shape.kind == "sphere":
        return f"sphere radius {s[0]:.3f} m"
    return f"{p.shape.kind} radius {s[0]:.3f} m, length {2 * s[1]:.3f} m"


def _mass(p: PartIR, device: DeviceIR) -> str:
    if p.hidden_mass is not None:
        h = next((h for h in device.hidden if h.name == p.hidden_mass), None)
        rng = f"between {h.low:g} and {h.high:g} kg" if h else "unknown"
        return f"sealed, mass unknown ({rng})"
    return f"mass {MATERIALS[p.material].density * shape_volume(p.shape):.3f} kg"


def describe_part(p: PartIR, device: DeviceIR) -> str:
    lo, hi = part_aabb(p)
    head = (
        f"- {p.name}: {_shape(p)}, {p.material}, {_mass(p, device)}; centre {_v(p.pos)}, "
        f"orientation (rx, ry, rz) {_v(p.euler)} rad; extent {_v(lo)}..{_v(hi)}"
    )
    m = p.mount
    if m.kind == "base":
        tail = "rests on the ground, fixed in place"
    elif m.kind == "fixed":
        tail = f"rigidly fixed to '{m.parent}'"
    elif m.kind == "free":
        tail = "loose (free body)"
        if m.carried_by:
            tail += f", carried by '{m.carried_by}' when it is set up"
    else:
        tail = (
            f"{m.kind} joint to '{m.parent}' at {_v(m.anchor or (0, 0, 0))}, axis "
            f"{_v(m.axis or (0, 0, 0))}, {m.joint_model} model"
        )
        if m.range is not None:
            unit = "rad" if m.kind == "hinge" else "m"
            tail += f", end stops [{m.range[0]:.3f}, {m.range[1]:.3f}] {unit}"
        if m.spring is not None:
            tail += f", {m.spring.model} spring relaxed at {m.spring.rest:.3f}"
    return f"{head}; {tail}"


def describe_device(device: DeviceIR) -> str:
    lines = [
        (
            f"Device '{device.name}' ({len(device.parts)} parts). Coordinates in metres, "
            "z up, ground at z=0. Joint coordinates are 0 in the pose described here."
        )
    ]
    lines.append("Parts:")
    lines.extend(describe_part(p, device) for p in device.parts)
    if device.actuators:
        lines.append("Actuators (command in [-1, 1]):")
        lines.extend(f"- {a.name}: {a.model} driving '{a.part}'" for a in device.actuators)
    if device.latches:
        lines.append("Latches (hold the joint at its starting value until released):")
        lines.extend(f"- {latch.name}: locks '{latch.part}'" for latch in device.latches)
    if device.sensors:
        lines.append("Sensors (Gaussian noise, standard deviation):")
        lines.extend(
            f"- {s.name}: {s.kind} of '{s.part}', noise {s.noise:g}" for s in device.sensors
        )
    if device.zones:
        lines.append("Visual markers:")
        lines.extend(f"- {z.name}: at {_v(z.pos)}, radius {z.size[0]:.3f} m" for z in device.zones)
    return "\n".join(lines)
