"""Static description of a submitted device for the 3D view: parts at their rest poses."""

from __future__ import annotations

from mlab.construct.geometry import euler_to_mat, mat_to_quat
from mlab.construct.ir import DeviceIR, Submission
from mlab.construct.modify import mod_key


def moving_parts(device: DeviceIR) -> set[str]:
    """Parts that can move: jointed or free parts and everything fixed onto them."""
    parts = {p.name: p for p in device.parts}

    def moves(name: str) -> bool:
        p = parts[name]
        while p.mount.kind == "fixed" and p.mount.parent is not None:
            p = parts[p.mount.parent]
        return p.mount.kind in ("hinge", "slide", "free")

    return {name for name in parts if moves(name)}


def xyzw(wxyz) -> list[float]:
    """MuJoCo quaternions are (w, x, y, z); three.js expects (x, y, z, w)."""
    return [float(wxyz[1]), float(wxyz[2]), float(wxyz[3]), float(wxyz[0])]


def device_scene(sub: Submission) -> dict:
    device, task = sub.device, sub.task
    moving = moving_parts(device)
    parts = []
    for p in device.parts:
        parts.append(
            {
                "name": p.name,
                "shape": p.shape.kind,
                "size": [float(s) for s in p.shape.size],
                "material": p.material,
                "hidden": p.hidden_mass is not None,
                "hidden_mass": p.hidden_mass,
                "moving": p.name in moving,
                "mount": p.mount.kind,
                "pos": [float(v) for v in p.pos],
                "quat": xyzw(mat_to_quat(euler_to_mat(p.euler))),
            }
        )
    out = task.outcome
    return {
        "name": device.name,
        "parts": parts,
        "outcome": {
            "kind": out.kind,
            "part": out.part,
            "axes": list(out.axes),
            "base": [float(v) for v in device.part(out.part).pos],
        },
        "goal_space": [[g.low, g.high] for g in task.goal_space],
        "tolerance": task.tolerance,
        "budget": task.budget,
        "horizon": task.horizon,
        "knobs": [k.model_dump() for k in task.knobs],
        "sensors": [s.model_dump() for s in device.sensors],
        "hidden": [h.name for h in device.hidden],
        "modifiable": [{"key": mod_key(m), **m.model_dump()} for m in task.modifiable],
        "title": task.title,
        "escalation": list(task.escalation),
    }
