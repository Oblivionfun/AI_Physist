"""Structural changelog between device versions, generated from construction records.

It tells the learner what changed (parts, joints, sensors, interface) but never any value
that the builder could not have published in the manual anyway."""

from __future__ import annotations

from mlab.construct.ir import Submission


def _part_sig(p) -> str:
    m = p.mount
    sealed = " sealed" if p.hidden_mass else ""
    return f"{p.shape.kind} {p.material}{sealed} {m.kind}" + (f" to {m.parent}" if m.parent else "")


def changelog(prev: Submission | None, new: Submission) -> list[str]:
    if prev is None:
        return ["first version"]
    out: list[str] = []
    if prev.device.name != new.device.name:
        out.append(f"new device '{new.device.name}' replaces '{prev.device.name}'")
    old = {p.name: p for p in prev.device.parts}
    cur = {p.name: p for p in new.device.parts}
    for n in sorted(cur.keys() - old.keys()):
        out.append(f"part added: {n} ({_part_sig(cur[n])})")
    for n in sorted(old.keys() - cur.keys()):
        out.append(f"part removed: {n}")
    for n in sorted(cur.keys() & old.keys()):
        if cur[n].model_dump() != old[n].model_dump():
            out.append(f"part changed: {n}")
    for label, a, b in (
        ("sensor", prev.device.sensors, new.device.sensors),
        ("actuator", prev.device.actuators, new.device.actuators),
        ("latch", prev.device.latches, new.device.latches),
    ):
        an, bn = {x.name for x in a}, {x.name for x in b}
        out += [f"{label} added: {n}" for n in sorted(bn - an)]
        out += [f"{label} removed: {n}" for n in sorted(an - bn)]
    pk = [(k.name, k.low, k.high) for k in prev.task.knobs]
    nk = [(k.name, k.low, k.high) for k in new.task.knobs]
    if pk != nk:
        out.append(f"knobs changed: {[k[0] for k in nk]}")
    if prev.task.outcome != new.task.outcome:
        out.append("outcome definition changed")
    if prev.task.budget != new.task.budget:
        out.append(f"experiment budget {prev.task.budget} -> {new.task.budget}")
    if prev.task.tolerance != new.task.tolerance:
        out.append(f"tolerance {prev.task.tolerance:g} -> {new.task.tolerance:g}")
    return out or ["no structural change"]
