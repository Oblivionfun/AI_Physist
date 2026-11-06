"""Scripted reference builder: a fixed curriculum written by the system author.

It exists only for offline reproduction and CI of the whole loop. It is never the builder of
a demo run (AGENTS.md red line 1); demo devices come from the LLM building agent.
"""

from __future__ import annotations

import math

from mlab.construct import Builder, Fixed, Hinge, Slide, Spring, Submission
from mlab.construct.ir import (
    GoalDimIR,
    KnobIR,
    ModifiableIR,
    OutcomeIR,
    PhaseIR,
    SetupIR,
    TaskIR,
)


def ball_launcher(budget: int) -> Submission:
    b = Builder("ball_launcher")
    b.base("deck", "box", [0.4, 0.1, 0.15], "wood", (0.0, 0.0, 0.15))
    b.attach("housing", "box", [0.03, 0.04, 0.03], "steel", (-0.07, 0.0, 0.33), to="deck",
             joint=Fixed())
    b.attach("plunger", "box", [0.03, 0.03, 0.02], "steel", (-0.01, 0.0, 0.325), to="housing",
             joint=Slide(anchor=(-0.04, 0.0, 0.325), axis=(1.0, 0.0, 0.0), range=(-0.15, 0.08),
                         spring=Spring("coil_stiff")))
    b.latch("trigger", "plunger")
    b.free("ball", "sphere", [0.02], "steel", (0.045, 0.0, 0.32))
    b.sensor("plunger_pos", "joint_angle", "plunger")
    b.sensor("ball_pos", "position", "ball", noise=0.003)
    task = TaskIR(
        title="Land the ball on a spot",
        goal_text="Cock the plunger and release it so that the ball rolls off the deck and first "
        "touches the ground at the target x position.",
        knobs=[KnobIR(name="compression", low=-0.14, high=-0.02, unit="m",
                      description="plunger position when cocked (negative = compressed)")],
        setup=[SetupIR(part="plunger", value="compression")],
        phases=[PhaseIR(duration=0.05, release=["trigger"])],
        horizon=2.0,
        outcome=OutcomeIR(kind="landing_point", part="ball", axes=["x"]),
        goal_space=[GoalDimIR(low=0.55, high=0.68)],
        tolerance=0.015,
        budget=budget,
        escalation=["baseline: one spring launcher"],
        modifiable=[ModifiableIR(part="ball", field="posx", low=0.045, high=0.1)],
    )
    return Submission(device=b.finish(), task=task)


def sealed_pendulum(budget: int) -> Submission:
    b = Builder("sealed_pendulum")
    b.hidden("head_mass", 0.5, 2.5, "kg", description="sealed striker head")
    b.base("table", "box", [0.6, 0.15, 0.09], "wood", (0.33, 0.0, 0.09))
    b.base("post", "box", [0.03, 0.03, 0.4], "aluminium", (-0.3, 0.0, 0.4))
    b.attach("axle", "cylinder", [0.01, 0.045], "steel", (-0.3, 0.075, 0.76),
             euler=(math.pi / 2, 0.0, 0.0), to="post", joint=Fixed())
    b.attach("arm", "capsule", [0.012, 0.24], "aluminium", (-0.3, 0.08, 0.52), to="axle",
             joint=Hinge(anchor=(-0.3, 0.08, 0.76), axis=(0.0, 1.0, 0.0), range=(-0.6, 1.7)))
    b.attach("head", "box", [0.04, 0.04, 0.04], "steel", (-0.3, 0.08, 0.235), to="arm",
             joint=Fixed(), hidden_mass="head_mass")
    b.free("block", "box", [0.025, 0.025, 0.02], "aluminium", (-0.23, 0.08, 0.2))
    b.sensor("arm_angle", "joint_angle", "arm", noise=0.003)
    b.sensor("block_pos", "position", "block", noise=0.003)
    task = TaskIR(
        title="Strike the block to a spot",
        goal_text="Pull the pendulum back and let it go so that the struck block comes to rest "
        "with its centre at the target x position.",
        knobs=[KnobIR(name="pull_back", low=0.2, high=1.3, unit="rad",
                      description="arm angle before release")],
        setup=[SetupIR(part="arm", value="pull_back")],
        horizon=4.0,
        outcome=OutcomeIR(kind="final_position", part="block", axes=["x"]),
        goal_space=[GoalDimIR(low=0.05, high=0.3)],
        tolerance=0.025,
        budget=budget,
        escalation=["new mechanism: impact transfer", "device-specific hidden mass",
                    "smaller budget"],
        modifiable=[ModifiableIR(part="block", field="posx", low=-0.232, high=-0.10)],
    )
    return Submission(device=b.finish(), task=task)


class ReferenceBuilder:
    """Adapts minimally to reports: harder next design when the learner is above the band,
    more budget when below it, and a narrower goal space when certification fails."""

    name = "reference"

    def __init__(self) -> None:
        self.stage = 0
        self.budgets = [40, 24]
        self.designs = [ball_launcher, sealed_pendulum]

    def propose(self, round_index: int, report: dict | None, rejection: str | None) -> Submission:
        if report is not None and rejection is None:
            exam = sum(i["exam_success"] for i in report["instances"]) / max(1, len(report["instances"]))
            if exam > 0.8 and self.stage < len(self.designs) - 1:
                self.stage += 1
            elif exam < 0.3:
                self.budgets[self.stage] = min(80, self.budgets[self.stage] + 10)
        sub = self.designs[self.stage](self.budgets[self.stage])
        if rejection is not None:
            failed = next((line for line in rejection.splitlines() if "FAIL" in line), "")
            g = sub.task.goal_space[0]
            mid, half = (g.low + g.high) / 2, (g.high - g.low) / 2
            if failed.startswith("C1 "):
                sub.task.goal_space = [GoalDimIR(low=mid - 0.7 * half, high=mid + 0.7 * half)]
            elif failed.startswith("C2"):
                sub.task.tolerance = max(0.01, sub.task.tolerance * 0.7)
            elif failed.startswith("C1b") or "timestep" in failed:
                sub.task.tolerance = sub.task.tolerance * 1.3
        return sub
