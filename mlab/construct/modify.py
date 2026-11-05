"""Public counterfactual modifications of visible dimensions (used in theory evaluation)."""

from __future__ import annotations

from mlab.construct.ir import DeviceIR, ModifiableIR, TaskIR


def mod_key(mod: ModifiableIR) -> str:
    return f"{mod.part}.{mod.field}"


def current_value(device: DeviceIR, mod: ModifiableIR) -> float:
    part = device.part(mod.part)
    if mod.field.startswith("size"):
        return float(part.shape.size[int(mod.field[-1])])
    return float(part.pos["xyz".index(mod.field[-1])])


def visible_params(device: DeviceIR, task: TaskIR) -> dict[str, float]:
    return {mod_key(m): current_value(device, m) for m in task.modifiable}


def apply_modification(device: DeviceIR, mod: ModifiableIR, value: float) -> DeviceIR:
    out = device.model_copy(deep=True)
    part = out.part(mod.part)
    if mod.field.startswith("size"):
        size = list(part.shape.size)
        size[int(mod.field[-1])] = float(value)
        part.shape.size = size
    else:
        pos = list(part.pos)
        pos["xyz".index(mod.field[-1])] = float(value)
        part.pos = (pos[0], pos[1], pos[2])
    return out
