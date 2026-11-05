"""Good fixture: a latched spring plunger launches a puck off the end of a deck.

Hand-written by the system author for referee meta-evaluation only. It is never shown to
the building agent or the learning agent.
"""

from __future__ import annotations

from mlab.construct import Builder, Fixed, Slide, Spring, Submission
from mlab.construct.ir import GoalDimIR, KnobIR, ModifiableIR, OutcomeIR, PhaseIR, SetupIR, TaskIR


def build_device(shift: float = 0.3) -> Builder:
    b = Builder("spring_launcher")
    b.base("deck", "box", [0.4, 0.1, 0.15], "wood", (0.0, 0.0, 0.15))
    b.attach("housing", "box", [0.03, 0.04, 0.03], "steel", (-0.37 + shift, 0.0, 0.33),
             to="deck", joint=Fixed())
    b.attach(
        "plunger", "box", [0.03, 0.03, 0.02], "steel", (-0.31 + shift, 0.0, 0.325),
        to="housing",
        joint=Slide(anchor=(-0.34 + shift, 0.0, 0.325), axis=(1.0, 0.0, 0.0), range=(-0.15, 0.08),
                    spring=Spring("coil_stiff", rest=0.0)),
    )
    b.latch("trigger", "plunger")
    b.free("ball", "sphere", [0.02], "steel", (-0.255 + shift, 0.0, 0.32))
    b.sensor("plunger_pos", "joint_angle", "plunger", noise=0.002)
    b.sensor("ball_pos", "position", "ball", noise=0.003)
    return b


def build_task(goal: tuple[float, float] = (0.55, 0.68), tolerance: float = 0.015) -> TaskIR:
    return TaskIR(
        title="Launch the ball onto a landing spot",
        goal_text="Compress the plunger, then release the trigger so the ball rolls off the "
        "end of the deck and first touches the ground at the target x position.",
        knobs=[KnobIR(name="compression", low=-0.14, high=-0.02, unit="m",
                      description="plunger position when cocked (negative = compressed)")],
        setup=[SetupIR(part="plunger", value="compression")],
        phases=[PhaseIR(duration=0.05, release=["trigger"])],
        horizon=2.0,
        outcome=OutcomeIR(kind="landing_point", part="ball", axes=["x"]),
        goal_space=[GoalDimIR(low=goal[0], high=goal[1])],
        tolerance=tolerance,
        budget=40,
        modifiable=[ModifiableIR(part="ball", field="posx", low=0.045, high=0.1)],
    )


def submission(**task_kwargs) -> Submission:
    return Submission(device=build_device().finish(), task=build_task(**task_kwargs))
