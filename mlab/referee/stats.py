from __future__ import annotations

import math
from typing import Literal

Decision = Literal["pass", "fail", "gray"]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def decide(k: int, n: int, threshold: float, at_least: bool) -> Decision:
    """Three-way decision on a success rate against a threshold using a Wilson interval."""
    lo, hi = wilson(k, n)
    if at_least:
        if lo >= threshold:
            return "pass"
        if hi < threshold:
            return "fail"
    else:
        if hi <= threshold:
            return "pass"
        if lo > threshold:
            return "fail"
    return "gray"


def point_decision(k: int, n: int, threshold: float, at_least: bool) -> Decision:
    p = k / n if n else 0.0
    ok = p >= threshold if at_least else p <= threshold
    return "pass" if ok else "fail"
