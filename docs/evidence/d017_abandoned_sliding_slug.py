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


def build() -> Submission:
    b = Builder("sliding_slug_catapult")

    b.hidden(
        "ball_mass", 0.015, 0.13, "kg",
        description="mass of the sealed launch ball",
    )
    b.hidden(
        "slug_mass", 0.04, 0.32, "kg",
        description="mass of the sealed slug that rides the arm rail",
    )

    # tower
    b.base("column", "box", [0.04, 0.05, 0.31], "concrete", (0.0, 0.0, 0.31))
    b.attach("axle", "cylinder", [0.008, 0.06], "steel", (0.0, 0.06, 0.62),
             euler=(math.pi / 2, 0.0, 0.0), to="column", joint=Fixed())

    # throwing arm, hinged about +y at the top of the column, with a torsion spring
    b.attach("arm", "capsule", [0.012, 0.08], "wood", (0.0, 0.1, 0.70), to="axle",
             joint=Hinge(anchor=(0.0, 0.1, 0.62), axis=(0.0, 1.0, 0.0),
                         model="bearing", spring=Spring("torsion_soft", rest=-0.3),
                         range=(-0.6, 1.45)))

    # shallow cup at the arm tip: floor plus one retaining lip on the +x side
    b.attach("cup", "box", [0.022, 0.022, 0.005], "wood", (0.0, 0.1, 0.798),
             to="arm", joint=Fixed())
    b.attach("lip", "box", [0.005, 0.022, 0.018], "wood", (0.025, 0.1, 0.819),
             to="cup", joint=Fixed())

    # striker plate, offset in +y so it alone meets the stop post
    b.attach("striker", "box", [0.008, 0.045, 0.014], "wood", (0.0, 0.15, 0.710),
             to="arm", joint=Fixed())

    # sealed slug on a rail along the arm; the clamp is released during the throw
    b.attach("slug", "box", [0.022, 0.028, 0.022], "steel", (0.034, 0.1, 0.700),
             to="arm", hidden_mass="slug_mass",
             joint=Slide(anchor=(0.014, 0.1, 0.700), axis=(0.0, 0.0, 1.0),
                         range=(-0.045, 0.045), model="rail"))
    b.latch("clamp", "slug")

    # hard stop
    b.base("stop_post", "box", [0.02, 0.03, 0.375], "concrete", (-0.040, 0.16, 0.375))

    # sealed ball resting in the cup
    b.free("ball", "sphere", [0.016], "steel", (0.0, 0.1, 0.820),
           hidden_mass="ball_mass", carried_by="cup")

    b.motor("drive", "arm", "motor_large")
    b.sensor("arm_angle", "joint_angle", "arm")
    b.sensor("arm_rate", "joint_velocity", "arm")
    b.sensor("slug_where", "joint_angle", "slug")
    b.sensor("ball_where", "position", "ball")

    b.zone("target", (-1.05, 0.1, 0.0), 0.05)

    task = TaskIR(
        title="Catapult with a releasing slug",
        goal_text=(
            "The arm is cocked away from the stop post against a torsion spring and the "
            "sealed slug is clamped on the arm rail, then the motor drives the arm back. "
            "After the chosen dwell the clamp opens and the slug is free to run along "
            "the rail while the arm is still swinging. The striker then slams the post, "
            "the arm halts, and the ball leaves the cup and flies over the post. Place "
            "the ball's first ground contact at the requested x coordinate (it lands on "
            "the negative-x side). If the clamp opens only after the striker has already "
            "landed, the slug never moves at all."
        ),
        knobs=[
            KnobIR(name="cock", low=0.15, high=1.40, unit="rad",
                   description="arm start angle, cocked away from the stop post"),
            KnobIR(name="power", low=-1.0, high=-0.12, unit="command",
                   description=("motor command held throughout the throw; it is negative "
                                "because that is the direction that drives the arm "
                                "toward the stop post")),
            KnobIR(name="shift", low=-0.045, high=0.045, unit="m",
                   description=("where the slug is clamped on the rail before the run; "
                                "positive is out towards the cup, negative is in "
                                "towards the hinge")),
            KnobIR(name="dwell", low=0.05, high=0.60, unit="s",
                   description=("how long the clamp stays shut after the motor starts; "
                                "the clamp opens at the end of this dwell and the slug "
                                "is free from then on")),
        ],
        setup=[SetupIR(part="arm", value="cock"), SetupIR(part="slug", value="shift")],
        phases=[
            PhaseIR(duration="dwell", ctrl={"drive": "power"}),
            PhaseIR(duration=1.6, ctrl={"drive": "power"}, release=["clamp"]),
        ],
        horizon=4.0,
        outcome=OutcomeIR(kind="landing_point", part="ball", axes=["x"]),
        goal_space=[GoalDimIR(low=-1.62, high=-1.02)],
        tolerance=0.055,
        budget=72,
        escalation=[
            "piecewise mechanics: the slug clamp is released during the throw, so the "
            "slug runs along the rail under centrifugal and gravity load and the arm's "
            "inertia changes while it swings; rail dry friction and damping now enter "
            "the outcome",
            "a release boundary: if the dwell outlasts the swing the clamp opens after "
            "the striker impact and the slug never moves, so the outcome depends on the "
            "dwell only on one side of a threshold the learner has to locate, and that "
            "threshold itself depends on the hidden masses and the motor gain",
            "path dependence: the outcome is no longer a function of the end state of a "
            "single hold, it depends on when during the swing the inertia changes",
            "more knobs: four instead of three, and shift now interacts with dwell "
            "because a slug clamped at the outer end has nowhere left to run",
            "wider sealed-mass ranges, so the hidden quantities move the outcome "
            "further and the prior alone is of less use",
        ],
        modifiable=[
            ModifiableIR(part="stop_post", field="posx", low=-0.070, high=-0.034),
            ModifiableIR(part="striker", field="posz", low=0.690, high=0.730),
        ],
    )
    return Submission(device=b.finish(), task=task)
