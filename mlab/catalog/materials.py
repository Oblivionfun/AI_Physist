from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    name: str
    density: float
    rgba: tuple[float, float, float, float]
    ground_only: bool = False


MATERIALS: dict[str, Material] = {
    "steel": Material("steel", 7850.0, (0.58, 0.60, 0.64, 1.0)),
    "aluminium": Material("aluminium", 2700.0, (0.78, 0.80, 0.83, 1.0)),
    "wood": Material("wood", 650.0, (0.72, 0.53, 0.32, 1.0)),
    "rubber": Material("rubber", 1100.0, (0.16, 0.16, 0.17, 1.0)),
    "concrete": Material("concrete", 2400.0, (0.55, 0.55, 0.52, 1.0), ground_only=True),
}

GROUND_MATERIAL = "concrete"
