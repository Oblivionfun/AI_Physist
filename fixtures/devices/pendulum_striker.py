"""Good fixture: a pendulum with a sealed head strikes a block that slides along a table.

Hand-written by the system author for referee meta-evaluation only. It is never shown to
the building agent or the learning agent.
"""

from __future__ import annotations

import math

from mlab.construct import Builder, Fixed, Hinge, Submission
from mlab.construct.ir import GoalDimIR, KnobIR, ModifiableIR, OutcomeIR, SetupIR, TaskIR


def build_device(head_mass: tuple[float, float] = (0.5, 2.5)) -> Builder:
    b = Builder("pendulum_striker")
    b.hidden("head_mass", head_mass[0], head_mass[1], "kg", description="sealed striker head")
    b.base("table", "box", [0.6, 0.15, 0.09], "wood", (0.33, 0.0, 0.09))
    b.base("post", "box", [0.03, 0.03, 0.4], "aluminium", (-0.3, 0.0, 0.4))
    b.attach(
        "axle", "cylinder", [0.01, 0.045], "steel", (-0.3, 0.075, 0.76),
        euler=(math.pi / 2, 0.0, 0.0), to="post", joint=Fixed(),
    )
    b.attach(
        "arm", "capsule", [0.012, 0.24], "aluminium", (-0.3, 0.08, 0.52),
        to="axle",
        joint=Hinge(anchor=(-0.3, 0.08, 0.76), axis=(0.0, 1.0, 0.0), model="bearing",
                    range=(-0.6, 1.7)),
    )
    b.attach(
        "head", "box", [0.04, 0.04, 0.04], "steel", (-0.3, 0.08, 0.235),
        to="arm", joint=Fixed(), hidden_mass="head_mass",
    )
    b.free("block", "box", [0.025, 0.025, 0.02], "aluminium", (-0.23, 0.08, 0.2))
    b.sensor("arm_angle", "joint_angle", "arm", noise=0.003)
    b.sensor("block_pos", "position", "block", noise=0.003)
    b.sensor("block_vel", "velocity", "block", noise=0.02)
    return b


def build_task(
    goal: tuple[float, float] = (0.05, 0.3),
    tolerance: float = 0.025,
    goal_text: str | None = None,
    knob_range: tuple[float, float] = (0.2, 1.3),
) -> TaskIR:
    return TaskIR(
        title="Strike the block to a target spot",
        goal_text=goal_text
        or "Pull the pendulum back and let it go so that the struck block comes to rest with "
        "its centre at the target x position on the table.",
        knobs=[KnobIR(name="pull_back", low=knob_range[0], high=knob_range[1], unit="rad",
                      description="how far the arm is pulled back before release")],
        setup=[SetupIR(part="arm", value="pull_back")],
        phases=[],
        horizon=4.0,
        outcome=OutcomeIR(kind="final_position", part="block", axes=["x"]),
        goal_space=[GoalDimIR(low=goal[0], high=goal[1])],
        tolerance=tolerance,
        budget=40,
        modifiable=[ModifiableIR(part="block", field="posx", low=-0.232, high=-0.19)],
    )


def submission(**task_kwargs) -> Submission:
    return Submission(device=build_device().finish(), task=build_task(**task_kwargs))
