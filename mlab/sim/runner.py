"""Execute an action (knob values) on a compiled device and compute the public outcome."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import mujoco
import numpy as np

from mlab.construct.compile import CompiledDevice
from mlab.construct.geometry import mat_to_quat
from mlab.construct.ir import KnobRef, TaskIR

AXIS_INDEX = {"x": 0, "y": 1, "z": 2}
SETTLE_SPEED = 0.05
REST_SPEED = 0.01
REST_TIME = 0.25
MAX_QVEL = 1e3
LANDING_MIN_TIME = 0.02


@dataclass
class RunResult:
    outcome: np.ndarray | None
    status: str
    times: np.ndarray
    traces: dict[str, np.ndarray]
    t_end: float
    energy: np.ndarray = field(default_factory=lambda: np.zeros((0, 2)))
    """Columns: potential (gravity + springs), kinetic."""


def knob_values(task: TaskIR, knobs: dict[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k in task.knobs:
        if k.name not in knobs:
            raise ValueError(f"missing knob '{k.name}'")
        v = float(knobs[k.name])
        if not np.isfinite(v) or v < k.low - 1e-9 or v > k.high + 1e-9:
            raise ValueError(f"knob '{k.name}'={v} outside [{k.low}, {k.high}]")
        out[k.name] = min(max(v, k.low), k.high)
    extra = set(knobs) - {k.name for k in task.knobs}
    if extra:
        raise ValueError(f"unknown knobs {sorted(extra)}")
    return out


def _resolve(ref: KnobRef, values: dict[str, float]) -> float:
    return values[ref] if isinstance(ref, str) else float(ref)


def _body_pose(data: mujoco.MjData, bid: int) -> tuple[np.ndarray, np.ndarray]:
    return data.xpos[bid].copy(), data.xmat[bid].reshape(3, 3).copy()


def _geom_velocity(model, data, gid: int, buf: np.ndarray) -> np.ndarray:
    mujoco.mj_objectVelocity(model, data, mujoco.mjtObj.mjOBJ_GEOM, gid, buf, 0)
    return buf[3:6]


def prepare(dev: CompiledDevice, task: TaskIR, values: dict[str, float]) -> mujoco.MjData:
    """Reset, apply setup coordinates, move carried loose parts, engage latches."""
    model = dev.model
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    carried = []
    for p in dev.ir.parts:
        if p.mount.kind == "free" and p.mount.carried_by:
            carrier_bid = dev.part_body[p.mount.carried_by]
            carried.append((p.name, carrier_bid, *_body_pose(data, carrier_bid)))
    for s in task.setup:
        jid = dev.part_joint[s.part]
        data.qpos[model.jnt_qposadr[jid]] = _resolve(s.value, values)
    mujoco.mj_forward(model, data)
    for name, carrier_bid, p0, r0 in carried:
        p1, r1 = _body_pose(data, carrier_bid)
        delta = r1 @ r0.T
        jid = dev.part_joint[name]
        adr = model.jnt_qposadr[jid]
        pos = data.qpos[adr : adr + 3].copy()
        quat = data.qpos[adr + 3 : adr + 7].copy()
        rot = np.zeros(9)
        mujoco.mju_quat2Mat(rot, quat)
        new_rot = delta @ rot.reshape(3, 3)
        data.qpos[adr : adr + 3] = p1 + delta @ (pos - p0)
        data.qpos[adr + 3 : adr + 7] = mat_to_quat(new_rot)
    for name, eq in dev.latch_eq.items():
        jid = dev.latch_joint[name]
        model.eq_data[eq, :] = 0.0
        model.eq_data[eq, 0] = data.qpos[model.jnt_qposadr[jid]]
        data.eq_active[eq] = 1
    mujoco.mj_forward(model, data)
    return data


def simulate(
    dev: CompiledDevice,
    task: TaskIR,
    knobs: dict[str, float],
    *,
    rng: np.random.Generator | None = None,
    act_noise: float = 0.0,
    sample_hz: float = 50.0,
    timestep: float | None = None,
    early_stop: bool = True,
    on_sample: Callable[[mujoco.MjData], None] | None = None,
) -> RunResult:
    values = knob_values(task, knobs)
    if rng is not None and act_noise > 0:
        for k in task.knobs:
            jitter = rng.normal(0.0, act_noise * (k.high - k.low))
            values[k.name] = float(np.clip(values[k.name] + jitter, k.low, k.high))

    model = dev.model
    base_dt = model.opt.timestep
    if timestep is not None:
        model.opt.timestep = timestep
    try:
        return _run(dev, task, values, sample_hz, early_stop, on_sample)
    finally:
        model.opt.timestep = base_dt


def _run(
    dev: CompiledDevice, task: TaskIR, values: dict[str, float], sample_hz: float, early_stop: bool,
    on_sample: Callable[[mujoco.MjData], None] | None = None,
) -> RunResult:
    model = dev.model
    data = prepare(dev, task, values)
    dt = model.opt.timestep

    events: list[tuple[float, dict[str, float], list[str]]] = []
    t_cursor = 0.0
    for ph in task.phases:
        ctrl = {a: _resolve(v, values) for a, v in ph.ctrl.items()}
        events.append((t_cursor, ctrl, list(ph.release)))
        t_cursor += _resolve(ph.duration, values)
    events.append((t_cursor, {}, []))
    phases_end = t_cursor

    out = task.outcome
    gid = dev.part_geom[out.part]
    axes = [AXIS_INDEX[a] for a in out.axes]
    rbound = float(model.geom_rbound[gid])
    vel_buf = np.zeros(6)

    sensor_specs = []
    for s in dev.ir.sensors:
        if s.kind in ("joint_angle", "joint_velocity"):
            jid = dev.part_joint[s.part]
            adr = model.jnt_qposadr[jid] if s.kind == "joint_angle" else model.jnt_dofadr[jid]
            sensor_specs.append((s.name, s.kind, int(adr)))
        else:
            sensor_specs.append((s.name, s.kind, dev.part_geom[s.part]))
    traces: dict[str, list] = {name: [] for name, _, _ in sensor_specs}
    times: list[float] = []
    energy: list[tuple[float, float]] = []

    def sample() -> None:
        if on_sample is not None:
            on_sample(data)
        times.append(float(data.time))
        energy.append((float(data.energy[0]), float(data.energy[1])))
        for name, kind, idx in sensor_specs:
            if kind == "joint_angle":
                traces[name].append(float(data.qpos[idx]))
            elif kind == "joint_velocity":
                traces[name].append(float(data.qvel[idx]))
            elif kind == "position":
                traces[name].append(data.geom_xpos[idx].copy())
            else:
                traces[name].append(_geom_velocity(model, data, idx, vel_buf).copy())

    def touching_ground() -> bool:
        if data.ncon == 0:
            return False
        pairs = data.contact.geom[: data.ncon]
        g = dev.ground_geom
        hit = ((pairs[:, 0] == gid) & (pairs[:, 1] == g)) | ((pairs[:, 1] == gid) & (pairs[:, 0] == g))
        return bool(np.any(hit))

    n_steps = round(task.horizon / dt)
    sample_every = max(1, round(1.0 / (sample_hz * dt)))
    next_event = 0
    status = "ok"
    landing: np.ndarray | None = None
    started_on_ground = touching_ground()
    max_height = float(data.geom_xpos[gid][2])
    rest_since: float | None = None
    sample()

    step = 0
    while step < n_steps:
        while next_event < len(events) and events[next_event][0] <= data.time + 1e-9:
            _, ctrl, release = events[next_event]
            data.ctrl[:] = 0.0
            for act, v in ctrl.items():
                data.ctrl[dev.actuator_id[act]] = v
            for name in release:
                data.eq_active[dev.latch_eq[name]] = 0
            next_event += 1
        fine = out.kind == "landing_point" and landing is None and (
            float(data.geom_xpos[gid][2]) - rbound
            < 0.02 + abs(float(_geom_velocity(model, data, gid, vel_buf)[2])) * sample_every * dt
        )
        n = 1 if fine else min(sample_every - (step % sample_every), n_steps - step)
        if next_event < len(events):
            steps_to_event = max(1, round((events[next_event][0] - data.time) / dt))
            n = min(n, steps_to_event)
        mujoco.mj_step(model, data, nstep=n)
        step += n

        if not np.all(np.isfinite(data.qpos)) or np.max(np.abs(data.qvel)) > MAX_QVEL:
            status = "unstable"
            break
        z = float(data.geom_xpos[gid][2])
        max_height = max(max_height, z)
        if out.kind == "landing_point" and landing is None and data.time >= LANDING_MIN_TIME:
            on_ground = touching_ground()
            if on_ground and not started_on_ground:
                landing = data.geom_xpos[gid].copy()
            elif not on_ground:
                started_on_ground = False
        if step % sample_every == 0:
            sample()
        if early_stop and data.time > phases_end + 0.05:
            if out.kind == "landing_point" and landing is not None and data.time > 0.0:
                break
            if out.kind in ("final_position", "final_joint_angle"):
                if float(data.energy[1]) < 1e-6 or np.max(np.abs(data.qvel)) < REST_SPEED:
                    rest_since = data.time if rest_since is None else rest_since
                    if data.time - rest_since >= REST_TIME:
                        break
                else:
                    rest_since = None
    if not times or times[-1] < data.time - 1e-9:
        sample()

    outcome: np.ndarray | None
    if status != "ok":
        outcome = None
    elif out.kind == "landing_point":
        outcome = landing[axes] if landing is not None else None
        if outcome is None:
            status = "no_landing"
    elif out.kind == "final_position":
        outcome = data.geom_xpos[gid][axes].copy()
        speed = float(np.linalg.norm(_geom_velocity(model, data, gid, vel_buf)))
        if speed > SETTLE_SPEED:
            status = "unsettled"
    elif out.kind == "max_height":
        outcome = np.array([max_height])
    else:
        jid = dev.part_joint[out.part]
        outcome = np.array([float(data.qpos[model.jnt_qposadr[jid]])])

    return RunResult(
        outcome=outcome,
        status=status,
        times=np.asarray(times),
        traces={k: np.asarray(v) for k, v in traces.items()},
        t_end=float(data.time),
        energy=np.asarray(energy),
    )


def succeeded(result: RunResult, goal: np.ndarray, tolerance: float) -> bool:
    if result.status != "ok" or result.outcome is None:
        return False
    return bool(np.linalg.norm(result.outcome - goal) <= tolerance)
