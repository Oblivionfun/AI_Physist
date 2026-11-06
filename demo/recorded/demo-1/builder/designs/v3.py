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
    b = Builder("wide_mass_catapult")

    b.hidden(
        "ball_mass", 0.02, 0.10, "kg",
        description="mass of the sealed launch ball",
    )
    b.hidden(
        "slug_mass", 0.05, 0.25, "kg",
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
        title="Sprung stop-block catapult",
        goal_text=(
            "The arm is cocked away from the stop post against a torsion spring and the "
            "sealed slug is clamped somewhere on the arm rail, then the motor drives the "
            "arm back for a burst of the chosen length. When the burst ends the motor is "
            "off and the arm coasts on the spring alone until the striker slams the post, "
            "the arm halts, and the ball leaves the cup and flies over the post. Place "
            "the ball's first ground contact at the requested x coordinate (it lands on "
            "the negative-x side). A short burst hands the rest of the throw to the "
            "spring."
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
        ],
        setup=[SetupIR(part="arm", value="cock"), SetupIR(part="slug", value="shift")],
        phases=[PhaseIR(duration=2.0, ctrl={"drive": "power"})],
        horizon=3.2,
        outcome=OutcomeIR(kind="landing_point", part="ball", axes=["x"]),
        goal_space=[GoalDimIR(low=-1.52, high=-1.02)],
        tolerance=0.048,
        budget=62,
        escalation=[
            "tighter tolerance: 0.048 instead of 0.055, so the landing point has to be "
            "placed in a window about a seventh narrower and the hidden masses have to "
            "be pinned down correspondingly better before any goal can be aimed at",
            "the publicly modifiable dimensions span wider ranges than before, both the "
            "stop post offset and the striker height, so a model has to extrapolate "
            "further from the geometry it was identified on",
        ],
        modifiable=[
            ModifiableIR(part="stop_post", field="posx", low=-0.080, high=-0.030),
            ModifiableIR(part="striker", field="posz", low=0.684, high=0.736),
        ],
    )
    return Submission(device=b.finish(), task=task)
