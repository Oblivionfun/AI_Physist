import math

from mlab.construct import Builder, Fixed, Hinge, Submission
from mlab.construct.ir import (
    GoalDimIR,
    KnobIR,
    ModifiableIR,
    OutcomeIR,
    OutcomeIR as _O,  # noqa: F401
    PhaseIR,
    SetupIR,
    TaskIR,
)


def build() -> Submission:
    b = Builder("stop_catapult")

    b.hidden(
        "ball_mass", 0.02, 0.10, "kg",
        description="mass of the sealed launch ball",
    )
    b.hidden(
        "slug_mass", 0.05, 0.25, "kg",
        description="mass of the sealed slug clamped to the arm",
    )

    # tower
    b.base("column", "box", [0.04, 0.05, 0.31], "concrete", (0.0, 0.0, 0.31))
    b.attach("axle", "cylinder", [0.008, 0.06], "steel", (0.0, 0.06, 0.62),
             euler=(math.pi / 2, 0.0, 0.0), to="column", joint=Fixed())

    # throwing arm, hinged about +y at the top of the column
    b.attach("arm", "capsule", [0.012, 0.08], "wood", (0.0, 0.1, 0.70), to="axle",
             joint=Hinge(anchor=(0.0, 0.1, 0.62), axis=(0.0, 1.0, 0.0),
                         model="bearing", range=(-0.6, 1.45)))

    # shallow cup at the arm tip: floor plus one retaining lip on the +x side
    b.attach("cup", "box", [0.022, 0.022, 0.005], "wood", (0.0, 0.1, 0.798),
             to="arm", joint=Fixed())
    b.attach("lip", "box", [0.005, 0.022, 0.018], "wood", (0.025, 0.1, 0.819),
             to="cup", joint=Fixed())

    # striker plate, offset in +y so it alone meets the stop post
    b.attach("striker", "box", [0.008, 0.045, 0.014], "wood", (0.0, 0.15, 0.72),
             to="arm", joint=Fixed())

    # sealed slug clamped to the arm
    b.attach("slug", "box", [0.022, 0.028, 0.022], "steel", (0.034, 0.1, 0.69),
             to="arm", joint=Fixed(), hidden_mass="slug_mass")

    # hard stop
    b.base("stop_post", "box", [0.02, 0.03, 0.375], "concrete", (-0.040, 0.16, 0.375))

    # sealed ball resting in the cup
    b.free("ball", "sphere", [0.016], "steel", (0.0, 0.1, 0.820),
           hidden_mass="ball_mass", carried_by="cup")

    b.motor("drive", "arm", "motor_large")
    b.sensor("arm_angle", "joint_angle", "arm")
    b.sensor("arm_rate", "joint_velocity", "arm")

    b.sensor("ball_speed", "velocity", "ball")
    b.sensor("ball_where", "position", "ball")

    b.zone("target", (-1.05, 0.1, 0.0), 0.05)

    task = TaskIR(
        title="Stop-block catapult",
        goal_text=(
            "The arm is cocked away from the stop post, then the motor drives it back. "
            "The striker slams the post, the arm halts, and the ball leaves the cup and "
            "flies over the post. Place the ball's first ground contact at the requested "
            "x coordinate (it lands on the negative-x side). Choose how far the arm is "
            "cocked and how hard the motor pushes."
        ),
        knobs=[
            KnobIR(name="cock", low=0.15, high=1.3, unit="rad",
                   description="arm start angle, cocked away from the stop post"),
            KnobIR(name="power", low=-1.0, high=-0.15, unit="command",
                   description=("motor command held during the throw; it is negative "
                                "because that is the direction that drives the arm "
                                "toward the stop post")),
        ],
        setup=[SetupIR(part="arm", value="cock")],
        phases=[PhaseIR(duration=2.0, ctrl={"drive": "power"})],
        horizon=3.0,
        outcome=OutcomeIR(kind="landing_point", part="ball", axes=["x"]),
        goal_space=[GoalDimIR(low=-1.52, high=-1.02)],
        tolerance=0.055,
        budget=80,
        escalation=["first version"],
        modifiable=[
            ModifiableIR(part="stop_post", field="posx", low=-0.070, high=-0.034),
            ModifiableIR(part="slug", field="posz", low=0.655, high=0.745),
        ],
    )
    return Submission(device=b.finish(), task=task)
