"""Construction-time and task-declaration checks.

Every issue carries a measured value, the threshold, and a concrete fix, because the text is
fed back verbatim to the building agent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import mujoco
import numpy as np

from mlab.catalog.materials import MATERIALS
from mlab.catalog.models import JOINT_MODELS, MOTOR_MODELS, SENSOR_MIN_NOISE, SPRING_MODELS
from mlab.catalog.priors import nominal_value
from mlab.catalog.world import WORLD_PRIORS
from mlab.construct.compile import CompiledDevice, compile_device, root_of
from mlab.construct.geometry import (
    aabb_gap,
    aabb_overlap_depth,
    expected_size_len,
    part_aabb,
    point_in_aabb,
    shape_char_size,
    shape_volume,
)
from mlab.construct.ir import DeviceIR, PartIR, TaskIR
from mlab.construct.modify import apply_modification, current_value

MIN_HALF_SIZE = 0.005
MAX_HALF_SIZE = 2.0
GROUND_TOL = 0.002
ANCHOR_MARGIN = 0.005
TOUCH_GAP = 0.002
MIN_PART_MASS = 0.002
MAX_PART_MASS = 500.0
SEALED_DENSITY_RANGE = (50.0, 20000.0)
MAX_PARTS = 30
MAX_ACTUATORS = 4
MAX_LATCHES = 3
MAX_SENSORS = 8
MAX_HIDDEN = 4
MAX_KNOBS = 4
MAX_PHASES = 6
MAX_HINGE_RANGE = 2 * math.pi
MAX_SLIDE_RANGE = 1.0
MIN_TOLERANCE = 0.01
HORIZON_RANGE = (0.2, 8.0)
BUDGET_RANGE = (10, 80)


@dataclass(frozen=True)
class Issue:
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class ConstructionError(Exception):
    def __init__(self, issues: list[Issue]):
        self.issues = issues
        super().__init__("\n".join(str(i) for i in issues))


def nominal_theta(device: DeviceIR) -> dict[str, float]:
    theta = {k: nominal_value(p) for k, p in WORLD_PRIORS.items()}
    for h in device.hidden:
        theta[h.name] = nominal_value(h)
    return theta


def _v(x) -> str:
    return "(" + ", ".join(f"{float(c):.3f}" for c in x) + ")"


def check_part(device: DeviceIR, part: PartIR) -> list[Issue]:
    issues: list[Issue] = []
    if part.material not in MATERIALS:
        issues.append(
            Issue("material", f"part '{part.name}': unknown material '{part.material}'; "
                  f"choose one of {sorted(MATERIALS)}")
        )
        return issues
    if MATERIALS[part.material].ground_only and part.mount.kind != "base":
        issues.append(
            Issue("material", f"part '{part.name}': '{part.material}' is only allowed for bases")
        )
    n = expected_size_len(part.shape.kind)
    if len(part.shape.size) != n:
        issues.append(
            Issue("shape", f"part '{part.name}': {part.shape.kind} needs {n} size values, "
                  f"got {len(part.shape.size)}")
        )
        return issues
    for s in part.shape.size:
        if not (MIN_HALF_SIZE <= s <= MAX_HALF_SIZE):
            issues.append(
                Issue("shape", f"part '{part.name}': size value {s:.4f} m outside "
                      f"[{MIN_HALF_SIZE}, {MAX_HALF_SIZE}] m (half extents / radius)")
            )
    vol = shape_volume(part.shape)
    if part.hidden_mass is not None:
        hidden = {h.name: h for h in device.hidden}
        if part.hidden_mass not in hidden:
            issues.append(
                Issue("hidden", f"part '{part.name}': hidden mass '{part.hidden_mass}' is not "
                      "declared; call hidden(...) first")
            )
        else:
            h = hidden[part.hidden_mass]
            dlo, dhi = h.low / vol, h.high / vol
            if dlo < SEALED_DENSITY_RANGE[0] or dhi > SEALED_DENSITY_RANGE[1]:
                issues.append(
                    Issue("density", f"part '{part.name}': hidden mass range [{h.low}, {h.high}] kg "
                          f"implies density [{dlo:.0f}, {dhi:.0f}] kg/m^3, outside "
                          f"{SEALED_DENSITY_RANGE}; resize the part or the mass range")
                )
    else:
        mass = MATERIALS[part.material].density * vol
        if not (MIN_PART_MASS <= mass <= MAX_PART_MASS):
            issues.append(
                Issue("mass", f"part '{part.name}': mass {mass:.4f} kg outside "
                      f"[{MIN_PART_MASS}, {MAX_PART_MASS}] kg; change size or material")
            )

    lo, hi = part_aabb(part)
    m = part.mount
    if m.kind == "base":
        if m.parent is not None:
            issues.append(Issue("mount", f"base '{part.name}' cannot have a parent"))
        if abs(lo[2]) > GROUND_TOL:
            issues.append(
                Issue("support", f"base '{part.name}': lowest point at z={lo[2]:.4f} m; a base "
                      f"must rest on the ground (|z| <= {GROUND_TOL} m). Move it by "
                      f"{-lo[2]:+.4f} m in z or attach it to another part")
            )
    else:
        if lo[2] < -GROUND_TOL:
            issues.append(
                Issue("ground", f"part '{part.name}': lowest point z={lo[2]:.4f} m is below the "
                      f"ground; raise it by at least {-lo[2]:.4f} m")
            )
    if m.kind == "free":
        if m.parent is not None:
            issues.append(Issue("mount", f"free part '{part.name}' cannot have a parent"))
        if m.carried_by is not None:
            if not device.has_part(m.carried_by):
                issues.append(Issue("mount", f"free part '{part.name}': carrier "
                                    f"'{m.carried_by}' does not exist"))
            elif device.part(m.carried_by).mount.kind == "free":
                issues.append(Issue("mount", f"free part '{part.name}': carrier must not be free"))
    if m.kind in ("fixed", "hinge", "slide"):
        if m.parent is None or not device.has_part(m.parent):
            issues.append(
                Issue("mount", f"part '{part.name}': parent '{m.parent}' does not exist; "
                      "add the parent first")
            )
            return issues
        parent = device.part(m.parent)
        plo, phi = part_aabb(parent)
        if m.kind == "fixed":
            gap = aabb_gap((lo, hi), (plo, phi))
            if gap > TOUCH_GAP:
                issues.append(
                    Issue("detached", f"part '{part.name}' is fixed to '{parent.name}' but the "
                          f"two are {gap * 1000:.1f} mm apart (max {TOUCH_GAP * 1000:.0f} mm); "
                          "move them into contact")
                )
        else:
            if m.anchor is None or m.axis is None:
                issues.append(Issue("joint", f"part '{part.name}': {m.kind} needs anchor and axis"))
                return issues
            axis = np.asarray(m.axis, dtype=float)
            if np.linalg.norm(axis) < 1e-9:
                issues.append(Issue("joint", f"part '{part.name}': joint axis must be non-zero"))
            anchor = np.asarray(m.anchor, dtype=float)
            if not point_in_aabb(anchor, plo, phi, ANCHOR_MARGIN):
                issues.append(
                    Issue("anchor", f"part '{part.name}': joint anchor {_v(anchor)} is not on "
                          f"parent '{parent.name}' (its extent is {_v(plo)}..{_v(phi)}); "
                          "the pin must pass through the parent")
                )
            if not point_in_aabb(anchor, lo, hi, ANCHOR_MARGIN):
                issues.append(
                    Issue("anchor", f"part '{part.name}': joint anchor {_v(anchor)} is not on "
                          f"the part itself (extent {_v(lo)}..{_v(hi)})")
                )
            jm = JOINT_MODELS.get(m.joint_model or "")
            if jm is None or jm.kind != m.kind:
                options = [k for k, v in JOINT_MODELS.items() if v.kind == m.kind]
                issues.append(
                    Issue("joint", f"part '{part.name}': joint model '{m.joint_model}' invalid for "
                          f"{m.kind}; choose one of {options}")
                )
            if m.spring is not None:
                sm = SPRING_MODELS.get(m.spring.model)
                if sm is None or sm.kind != m.kind:
                    options = [k for k, v in SPRING_MODELS.items() if v.kind == m.kind]
                    issues.append(
                        Issue("spring", f"part '{part.name}': spring '{m.spring.model}' invalid for "
                              f"{m.kind}; choose one of {options}")
                    )
            limit = MAX_HINGE_RANGE if m.kind == "hinge" else MAX_SLIDE_RANGE
            if m.range is not None:
                rlo, rhi = m.range
                if not (rlo <= 0.0 <= rhi) or rlo >= rhi:
                    issues.append(
                        Issue("range", f"part '{part.name}': range {m.range} must satisfy "
                              "low <= 0 <= high (the built pose is coordinate 0)")
                    )
                if rhi - rlo > limit:
                    issues.append(
                        Issue("range", f"part '{part.name}': range width {rhi - rlo:.3f} exceeds "
                              f"{limit:.3f}")
                    )
                if m.spring is not None and not (rlo <= m.spring.rest <= rhi):
                    issues.append(
                        Issue("spring", f"part '{part.name}': spring rest {m.spring.rest} outside "
                              f"range {m.range}")
                    )
            elif m.kind == "slide":
                issues.append(
                    Issue("range", f"part '{part.name}': slides need a finite range (end stops)")
                )
    return issues


def check_device_static(device: DeviceIR) -> list[Issue]:
    issues: list[Issue] = []
    names = [p.name for p in device.parts]
    if len(set(names)) != len(names):
        issues.append(Issue("name", "part names must be unique"))
    for label, items, limit in (
        ("parts", device.parts, MAX_PARTS),
        ("actuators", device.actuators, MAX_ACTUATORS),
        ("latches", device.latches, MAX_LATCHES),
        ("sensors", device.sensors, MAX_SENSORS),
        ("hidden quantities", device.hidden, MAX_HIDDEN),
    ):
        if len(items) > limit:
            issues.append(Issue("limit", f"too many {label}: {len(items)} > {limit}"))
    for p in device.parts:
        issues.extend(check_part(device, p))
    if not any(p.mount.kind == "base" for p in device.parts) and device.parts:
        issues.append(Issue("support", "the device needs at least one base resting on the ground"))
    jointed = {p.name for p in device.parts if root_mount_kind(device, p.name) in ("hinge", "slide")}
    for a in device.actuators:
        if a.part not in jointed:
            issues.append(Issue("actuator", f"actuator '{a.name}': part '{a.part}' has no hinge/slide"))
            continue
        kind = root_mount_kind(device, a.part)
        mm = MOTOR_MODELS.get(a.model)
        if mm is None or mm.kind != kind:
            options = [k for k, v in MOTOR_MODELS.items() if v.kind == kind]
            issues.append(Issue("actuator", f"actuator '{a.name}': model '{a.model}' invalid for "
                                f"{kind}; choose one of {options}"))
    for latch in device.latches:
        if latch.part not in jointed:
            issues.append(Issue("latch", f"latch '{latch.name}': part '{latch.part}' has no "
                                "hinge/slide to lock"))
    for s in device.sensors:
        if not device.has_part(s.part):
            issues.append(Issue("sensor", f"sensor '{s.name}': part '{s.part}' does not exist"))
            continue
        if s.kind.startswith("joint") and s.part not in jointed:
            issues.append(Issue("sensor", f"sensor '{s.name}': part '{s.part}' has no joint"))
        floor = SENSOR_MIN_NOISE[s.kind]
        if s.noise < floor:
            issues.append(Issue("sensor", f"sensor '{s.name}': noise {s.noise} below the floor "
                                f"{floor} for {s.kind}"))
    seen: set[str] = set()
    for group in (device.actuators, device.latches, device.sensors, device.hidden, device.zones):
        for item in group:
            if item.name in seen:
                issues.append(Issue("name", f"name '{item.name}' is used twice"))
            seen.add(item.name)
    return issues


def root_mount_kind(device: DeviceIR, part_name: str) -> str:
    return device.part(root_of(device, part_name)).mount.kind


def check_contacts(compiled: CompiledDevice) -> list[Issue]:
    """Interpenetration in the built pose, between parts of different rigid bodies."""
    device = compiled.ir
    model = compiled.model
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    geom_part = {gid: name for name, gid in compiled.part_geom.items()}
    issues: list[Issue] = []
    for i in range(data.ncon):
        c = data.contact[i]
        g1, g2 = int(c.geom1), int(c.geom2)
        if g1 not in geom_part or g2 not in geom_part:
            continue
        p1, p2 = device.part(geom_part[g1]), device.part(geom_part[g2])
        tol = max(0.001, 0.01 * min(shape_char_size(p1.shape), shape_char_size(p2.shape)))
        if c.dist < -tol:
            issues.append(
                Issue("overlap", f"parts '{p1.name}' and '{p2.name}' interpenetrate by "
                      f"{-c.dist * 1000:.1f} mm (allowed {tol * 1000:.1f} mm); move one of them "
                      f"apart by at least {(-c.dist - tol) * 1000:.1f} mm")
            )
    static_parts = [p for p in device.parts if root_mount_kind(device, p.name) == "base"]
    for i, a in enumerate(static_parts):
        for b in static_parts[i + 1:]:
            if root_of(device, a.name) == root_of(device, b.name):
                continue
            depth = aabb_overlap_depth(part_aabb(a), part_aabb(b))
            if depth > 0.005:
                issues.append(
                    Issue("overlap", f"static parts '{a.name}' and '{b.name}' overlap by about "
                          f"{depth * 1000:.0f} mm; separate them or fix one onto the other")
                )
    return issues


def check_device(device: DeviceIR) -> tuple[list[Issue], CompiledDevice | None]:
    issues = check_device_static(device)
    if issues or not device.parts:
        return issues, None
    try:
        compiled = compile_device(device, nominal_theta(device))
    except ValueError as exc:
        return [Issue("compile", f"the simulator rejected the device: {exc}")], None
    return check_contacts(compiled), compiled


def _knob_range(task: TaskIR, ref) -> tuple[float, float] | None:
    if isinstance(ref, str):
        try:
            k = task.knob(ref)
        except KeyError:
            return None
        return (k.low, k.high)
    return (float(ref), float(ref))


def outcome_dim(task: TaskIR) -> int:
    return 1 if task.outcome.kind in ("final_joint_angle", "max_height") else len(task.outcome.axes)


def check_task(device: DeviceIR, task: TaskIR) -> list[Issue]:
    issues: list[Issue] = []
    if not (1 <= len(task.knobs) <= MAX_KNOBS):
        issues.append(Issue("knob", f"need 1..{MAX_KNOBS} knobs, got {len(task.knobs)}"))
    names = [k.name for k in task.knobs]
    if len(set(names)) != len(names):
        issues.append(Issue("knob", "knob names must be unique"))
    for k in task.knobs:
        if not k.low < k.high:
            issues.append(Issue("knob", f"knob '{k.name}': low must be below high"))

    def ref_ok(ref, where: str, lo: float, hi: float) -> None:
        r = _knob_range(task, ref)
        if r is None:
            issues.append(Issue("knob", f"{where}: unknown knob '{ref}'"))
        elif r[0] < lo - 1e-9 or r[1] > hi + 1e-9:
            issues.append(Issue("knob", f"{where}: value range {r} must stay within [{lo}, {hi}]"))

    jointed = {p.name for p in device.parts if root_mount_kind(device, p.name) in ("hinge", "slide")}
    for s in task.setup:
        if s.part not in jointed:
            issues.append(Issue("setup", f"setup: part '{s.part}' has no hinge/slide"))
            continue
        rng = device.part(root_of(device, s.part)).mount.range or (-math.pi, math.pi)
        ref_ok(s.value, f"setup of '{s.part}'", rng[0], rng[1])
    if len(task.phases) > MAX_PHASES:
        issues.append(Issue("phase", f"at most {MAX_PHASES} phases"))
    actuators = {a.name for a in device.actuators}
    latches = {latch.name for latch in device.latches}
    released: set[str] = set()
    max_total = 0.0
    for i, ph in enumerate(task.phases):
        r = _knob_range(task, ph.duration)
        if r is None or r[0] <= 0:
            issues.append(Issue("phase", f"phase {i}: duration must be positive"))
        else:
            max_total += r[1]
        for act, ref in ph.ctrl.items():
            if act not in actuators:
                issues.append(Issue("phase", f"phase {i}: unknown actuator '{act}'"))
            ref_ok(ref, f"phase {i} command for '{act}'", -1.0, 1.0)
        for name in ph.release:
            if name not in latches:
                issues.append(Issue("phase", f"phase {i}: unknown latch '{name}'"))
            if name in released:
                issues.append(Issue("phase", f"latch '{name}' released twice"))
            released.add(name)
    if not (HORIZON_RANGE[0] <= task.horizon <= HORIZON_RANGE[1]):
        issues.append(Issue("horizon", f"horizon {task.horizon} s outside {HORIZON_RANGE}"))
    if max_total > task.horizon:
        issues.append(Issue("horizon", f"phases can last {max_total:.2f} s, beyond the horizon"))
    used_knobs = {s.value for s in task.setup if isinstance(s.value, str)}
    for ph in task.phases:
        if isinstance(ph.duration, str):
            used_knobs.add(ph.duration)
        used_knobs.update(v for v in ph.ctrl.values() if isinstance(v, str))
    for k in task.knobs:
        if k.name not in used_knobs:
            issues.append(Issue("knob", f"knob '{k.name}' is declared but never used"))

    out = task.outcome
    if not device.has_part(out.part):
        issues.append(Issue("outcome", f"outcome part '{out.part}' does not exist"))
    else:
        kind = root_mount_kind(device, out.part)
        if out.kind == "landing_point" and kind != "free":
            issues.append(Issue("outcome", "landing_point needs a free part (a projectile)"))
        if out.kind == "final_joint_angle" and kind not in ("hinge", "slide"):
            issues.append(Issue("outcome", "final_joint_angle needs a jointed part"))
        if out.kind in ("landing_point", "final_position"):
            if not out.axes or len(set(out.axes)) != len(out.axes):
                issues.append(Issue("outcome", "outcome axes must be non-empty and unique"))
            if out.kind == "landing_point" and "z" in out.axes:
                issues.append(Issue("outcome", "landing_point uses horizontal axes only"))
    dim = outcome_dim(task)
    if len(task.goal_space) != dim:
        issues.append(Issue("goal", f"goal space has {len(task.goal_space)} dims, outcome has {dim}"))
    if task.tolerance < MIN_TOLERANCE:
        issues.append(Issue("goal", f"tolerance {task.tolerance} below {MIN_TOLERANCE}"))
    for i, g in enumerate(task.goal_space):
        if not g.low < g.high:
            issues.append(Issue("goal", f"goal dim {i}: low must be below high"))
        elif g.high - g.low < 2 * task.tolerance:
            issues.append(Issue("goal", f"goal dim {i}: span {g.high - g.low:.3f} is below twice "
                                f"the tolerance; the task would be trivial"))
    if not (BUDGET_RANGE[0] <= task.budget <= BUDGET_RANGE[1]):
        issues.append(Issue("budget", f"budget {task.budget} outside {BUDGET_RANGE}"))
    for mod in task.modifiable:
        key = f"{mod.part}.{mod.field}"
        if not device.has_part(mod.part):
            issues.append(Issue("modifiable", f"modifiable part '{mod.part}' does not exist"))
            continue
        if mod.field.startswith("size") and int(mod.field[-1]) >= len(device.part(mod.part).shape.size):
            issues.append(Issue("modifiable", f"modifiable '{key}': shape has no such size index"))
            continue
        if not mod.low < mod.high:
            issues.append(Issue("modifiable", f"modifiable '{key}': low must be below high"))
            continue
        now = current_value(device, mod)
        if not (mod.low - 1e-9 <= now <= mod.high + 1e-9):
            issues.append(Issue("modifiable", f"modifiable '{key}': current value {now:.4f} is "
                                f"outside [{mod.low}, {mod.high}]"))
        for value in (mod.low, mod.high):
            bad = check_device_static(apply_modification(device, mod, value))
            if not bad:
                compiled = compile_device(apply_modification(device, mod, value),
                                          nominal_theta(device))
                bad = check_contacts(compiled)
            if bad:
                issues.append(Issue("modifiable", f"modifiable '{key}' = {value}: the modified "
                                    f"device is invalid ({bad[0].message}); narrow the range"))
    return issues
