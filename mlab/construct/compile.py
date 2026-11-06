"""DeviceIR + theta -> MJCF XML -> MjModel.

Every part becomes its own MuJoCo body; `fixed` parts are jointless children, so a rigid
assembly shares one weld and never self-collides. MuJoCo's global parent filter is disabled
because it does not apply when the parent is welded to the world; instead each hinge/slide
part excludes contacts only with the part its pin passes through. Emitted MJCF names are
neutral indices; the mapping back to part names stays inside the referee.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import mujoco
import numpy as np

from mlab.catalog.materials import GROUND_MATERIAL, MATERIALS
from mlab.catalog.world import world_key
from mlab.construct.geometry import euler_to_mat, mat_to_quat
from mlab.construct.ir import DeviceIR, PartIR

TIMESTEP = 0.001
GRAVITY = 9.81
HINGE_ARMATURE = 1e-4
SLIDE_ARMATURE = 1e-3
LATCH_SOLREF = "0.004 1"
TORSIONAL_FRICTION = 0.005


@dataclass
class CompiledDevice:
    ir: DeviceIR
    theta: dict[str, float]
    xml: str
    model: mujoco.MjModel
    part_body: dict[str, int] = field(default_factory=dict)
    part_geom: dict[str, int] = field(default_factory=dict)
    part_joint: dict[str, int] = field(default_factory=dict)
    actuator_id: dict[str, int] = field(default_factory=dict)
    latch_eq: dict[str, int] = field(default_factory=dict)
    latch_joint: dict[str, int] = field(default_factory=dict)
    ground_geom: int = 0
    body_parts: dict[int, list[str]] = field(default_factory=dict)


def _fmt(values: np.ndarray | list[float] | tuple[float, ...]) -> str:
    return " ".join(f"{float(v):.8g}" for v in values)


def root_of(device: DeviceIR, part_name: str) -> str:
    """Follow fixed mounts up to the part that defines the rigid body."""
    part = device.part(part_name)
    seen = {part_name}
    while part.mount.kind == "fixed":
        assert part.mount.parent is not None
        part = device.part(part.mount.parent)
        if part.name in seen:
            raise ValueError(f"fixed-mount cycle through '{part.name}'")
        seen.add(part.name)
    return part.name


def used_world_keys(device: DeviceIR) -> set[str]:
    keys = {world_key("friction", GROUND_MATERIAL)}
    has_sphere = False
    for p in device.parts:
        keys.add(world_key("friction", p.material))
        if p.shape.kind == "sphere":
            has_sphere = True
            keys.add(world_key("rolling", p.material))
        m = p.mount
        if m.kind in ("hinge", "slide") and m.joint_model:
            keys.add(world_key("damping", m.joint_model))
            keys.add(world_key("frictionloss", m.joint_model))
        if m.spring is not None:
            keys.add(world_key("stiffness", m.spring.model))
    if has_sphere:
        keys.add(world_key("rolling", GROUND_MATERIAL))
    for a in device.actuators:
        keys.add(world_key("gain", a.model))
    return keys


def _geom_element(part: PartIR, theta: dict[str, float]):
    mat = MATERIALS[part.material]
    slide = theta[world_key("friction", part.material)]
    rolling = theta.get(world_key("rolling", part.material), 1e-4)
    attrs = {
        "type": part.shape.kind,
        "size": _fmt(part.shape.size),
        "rgba": _fmt(mat.rgba),
        "friction": _fmt([slide, TORSIONAL_FRICTION, rolling]),
        "condim": "6" if part.shape.kind == "sphere" else "3",
    }
    if part.hidden_mass is not None:
        attrs["mass"] = f"{theta[part.hidden_mass]:.8g}"
        attrs["rgba"] = "0.35 0.22 0.45 1"
    else:
        attrs["density"] = f"{mat.density:.8g}"
    return attrs


def compile_device(device: DeviceIR, theta: dict[str, float]) -> CompiledDevice:
    children: dict[str | None, list[str]] = {}
    for p in device.parts:
        parent = p.mount.parent if p.mount.kind in ("fixed", "hinge", "slide") else None
        children.setdefault(parent, []).append(p.name)

    mj = ET.Element("mujoco", model="device")
    ET.SubElement(mj, "compiler", angle="radian", inertiafromgeom="true", autolimits="true")
    option = ET.SubElement(
        mj, "option", timestep=f"{TIMESTEP}", integrator="implicitfast", gravity=f"0 0 {-GRAVITY}"
    )
    ET.SubElement(option, "flag", energy="enable", filterparent="disable")
    visual = ET.SubElement(mj, "visual")
    ET.SubElement(visual, "global", offwidth="1280", offheight="720")
    ET.SubElement(visual, "headlight", ambient="0.45 0.45 0.45", diffuse="0.6 0.6 0.6",
                  specular="0.1 0.1 0.1")
    asset = ET.SubElement(mj, "asset")
    ET.SubElement(asset, "texture", name="grid", type="2d", builtin="checker", width="256",
                  height="256", rgb1="0.62 0.62 0.6", rgb2="0.55 0.55 0.53")
    ET.SubElement(asset, "material", name="groundmat", texture="grid", texrepeat="10 10")
    ET.SubElement(asset, "texture", name="sky", type="skybox", builtin="gradient", width="64",
                  height="64", rgb1="0.85 0.9 0.95", rgb2="0.55 0.65 0.75")
    world = ET.SubElement(mj, "worldbody")
    ET.SubElement(world, "light", pos="0 -2 4", dir="0 0.4 -1", directional="true")
    ground_friction = theta[world_key("friction", GROUND_MATERIAL)]
    ground_rolling = theta.get(world_key("rolling", GROUND_MATERIAL), 1e-4)
    ET.SubElement(
        world,
        "geom",
        name="ground",
        type="plane",
        size="20 20 0.1",
        material="groundmat",
        friction=_fmt([ground_friction, TORSIONAL_FRICTION, ground_rolling]),
    )
    for z in device.zones:
        ET.SubElement(
            world,
            "site",
            name=f"z_{z.name}",
            type="cylinder",
            pos=_fmt(z.pos),
            size=_fmt([z.size[0], z.size[1]]),
            rgba="0.1 0.8 0.3 0.35",
        )

    body_names: dict[str, str] = {}
    joint_names: dict[str, str] = {}
    geom_names: dict[str, str] = {}
    counter = {"b": 0, "g": 0, "j": 0}

    def next_name(prefix: str) -> str:
        name = f"{prefix}{counter[prefix]}"
        counter[prefix] += 1
        return name

    def emit(parent_el: ET.Element, part_name: str, parent_pos: np.ndarray, parent_rot: np.ndarray):
        part = device.part(part_name)
        pos = np.asarray(part.pos, dtype=float)
        rot = euler_to_mat(part.euler)
        rel_pos = parent_rot.T @ (pos - parent_pos)
        rel_rot = parent_rot.T @ rot
        bname = next_name("b")
        body_names[part_name] = bname
        body = ET.SubElement(
            parent_el, "body", name=bname, pos=_fmt(rel_pos), quat=_fmt(mat_to_quat(rel_rot))
        )
        mount = part.mount
        if mount.kind == "free":
            jname = next_name("j")
            joint_names[part_name] = jname
            ET.SubElement(body, "freejoint", name=jname)
        elif mount.kind in ("hinge", "slide"):
            assert mount.anchor is not None and mount.axis is not None and mount.joint_model
            jname = next_name("j")
            joint_names[part_name] = jname
            anchor_local = rot.T @ (np.asarray(mount.anchor) - pos)
            axis = np.asarray(mount.axis, dtype=float)
            axis_local = rot.T @ (axis / np.linalg.norm(axis))
            jattrs = {
                "name": jname,
                "type": mount.kind,
                "pos": _fmt(anchor_local),
                "axis": _fmt(axis_local),
                "damping": f"{theta[world_key('damping', mount.joint_model)]:.8g}",
                "frictionloss": f"{theta[world_key('frictionloss', mount.joint_model)]:.8g}",
                "armature": f"{HINGE_ARMATURE if mount.kind == 'hinge' else SLIDE_ARMATURE}",
            }
            if mount.spring is not None:
                jattrs["stiffness"] = f"{theta[world_key('stiffness', mount.spring.model)]:.8g}"
                jattrs["springref"] = f"{mount.spring.rest:.8g}"
            if mount.range is not None:
                jattrs["range"] = _fmt(mount.range)
            ET.SubElement(body, "joint", **jattrs)
        gname = next_name("g")
        geom_names[part_name] = gname
        ET.SubElement(body, "geom", name=gname, **_geom_element(part, theta))
        for child in children.get(part_name, []):
            emit(body, child, pos, rot)

    for root_name in children.get(None, []):
        emit(world, root_name, np.zeros(3), np.eye(3))

    pin_pairs = [
        (p.name, p.mount.parent) for p in device.parts if p.mount.kind in ("hinge", "slide")
    ]
    if pin_pairs:
        contact_el = ET.SubElement(mj, "contact")
        for child, parent in pin_pairs:
            ET.SubElement(
                contact_el, "exclude", body1=body_names[parent], body2=body_names[child]
            )

    if device.actuators:
        act_el = ET.SubElement(mj, "actuator")
        for i, a in enumerate(device.actuators):
            ET.SubElement(
                act_el,
                "motor",
                name=f"a{i}",
                joint=joint_names[root_of(device, a.part)],
                gear=f"{theta[world_key('gain', a.model)]:.8g}",
                ctrlrange="-1 1",
            )
    if device.latches:
        eq_el = ET.SubElement(mj, "equality")
        for i, latch in enumerate(device.latches):
            ET.SubElement(
                eq_el,
                "joint",
                name=f"e{i}",
                joint1=joint_names[root_of(device, latch.part)],
                polycoef="0 0 0 0 0",
                solref=LATCH_SOLREF,
            )

    xml = ET.tostring(mj, encoding="unicode")
    model = mujoco.MjModel.from_xml_string(xml)

    out = CompiledDevice(ir=device, theta=dict(theta), xml=xml, model=model)
    out.ground_geom = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "ground")
    for part in device.parts:
        root = root_of(device, part.name)
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_names[part.name])
        out.part_body[part.name] = bid
        out.body_parts.setdefault(bid, []).append(part.name)
        out.part_geom[part.name] = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_GEOM, geom_names[part.name]
        )
        if root in joint_names:
            out.part_joint[part.name] = mujoco.mj_name2id(
                model, mujoco.mjtObj.mjOBJ_JOINT, joint_names[root]
            )
    for i, a in enumerate(device.actuators):
        out.actuator_id[a.name] = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"a{i}")
    for i, latch in enumerate(device.latches):
        out.latch_eq[latch.name] = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_EQUALITY, f"e{i}")
        out.latch_joint[latch.name] = out.part_joint[latch.part]
    return out
