"""Leak scanner for builder-written text that reaches the learner.

The builder never knows the sampled values, so numeric matches are coincidences or attempts
to smuggle hints; both are rejected. Numbers that are public anyway (bounds, sizes, ranges)
are exempt.
"""

from __future__ import annotations

import re

from mlab.construct.checks import Issue
from mlab.construct.ir import Submission

NUMBER = re.compile(r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?")
FORBIDDEN = re.compile(
    r"\b(oracle|hidden value|true value|ground truth|theta|answer is|the solution is|"
    r"secret|referee seed)\b",
    re.IGNORECASE,
)
RELATIVE_MATCH = 0.05
SCALES = (1.0, 1000.0, 0.001, 100.0)


def builder_texts(sub: Submission) -> dict[str, str]:
    texts = {"title": sub.task.title, "goal_text": sub.task.goal_text}
    for k in sub.task.knobs:
        texts[f"knob {k.name}"] = k.description
    for h in sub.device.hidden:
        texts[f"hidden {h.name}"] = h.description
    return texts


def public_numbers(sub: Submission) -> set[float]:
    nums: set[float] = {sub.task.tolerance, sub.task.horizon, float(sub.task.budget)}
    for k in sub.task.knobs:
        nums.update({k.low, k.high})
    for g in sub.task.goal_space:
        nums.update({g.low, g.high})
    for h in sub.device.hidden:
        nums.update({h.low, h.high})
    for p in sub.device.parts:
        nums.update(p.shape.size)
        nums.update(p.pos)
    return nums


def scan(sub: Submission, secret_values: list[float]) -> list[Issue]:
    issues: list[Issue] = []
    public = public_numbers(sub)
    for field, text in builder_texts(sub).items():
        if FORBIDDEN.search(text):
            issues.append(Issue("leak", f"{field}: contains a forbidden phrase "
                                f"('{FORBIDDEN.search(text).group(0)}')"))
        for token in NUMBER.findall(text):
            x = float(token)
            if any(abs(x - p) <= 1e-9 * max(1.0, abs(p)) for p in public):
                continue
            for v in secret_values:
                if v == 0:
                    continue
                for s in SCALES:
                    if abs(x - v * s) <= RELATIVE_MATCH * abs(v * s):
                        issues.append(Issue("leak", f"{field}: the number {token} is within "
                                            f"{RELATIVE_MATCH:.0%} of a hidden quantity; remove it"))
                        break
                else:
                    continue
                break
    return issues
