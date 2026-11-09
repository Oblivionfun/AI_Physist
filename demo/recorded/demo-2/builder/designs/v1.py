from mlab.construct import Builder, Fixed, Slide, Spring, Submission
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
    b = Builder("rail_launcher")

    b.hidden(
        "ball_mass",
        0.12,
        0.6,
        "kg",
        description="sealed mass of the launched ball",
    )

    # Table carrying the launch rail.
    b.base("table", "box", [0.06, 0.20, 0.25], "concrete", (0.0, 0.0, 0.25))
    b.attach(
        "track",
        "box",
        [0.06, 0.20, 0.01],
        "wood",
        (0.0, 0.0, 0.51),
        to="table",
        joint=Fixed(),
    )

    # Separate stand beside the rail carries the sliding plunger.
    b.base("stand", "box", [0.04, 0.03, 0.29], "aluminium", (0.16, 0.09, 0.29))
    b.attach(
        "plunger",
        "box",
        [0.075, 0.03, 0.015],
        "wood",
        (0.045, 0.09, 0.545),
        to="stand",
        joint=Slide(
            anchor=(0.12, 0.09, 0.545),
            axis=(0.0, 1.0, 0.0),
            range=(-0.21, 0.0),
            model="rail",
            spring=Spring(model="coil_soft", rest=0.0),
        ),
    )

    b.free(
        "ball",
        "sphere",
        [0.025],
        "steel",
        (0.0, 0.145, 0.545),
        hidden_mass="ball_mass",
        carried_by="plunger",
    )

    b.motor("drive", "plunger", "linear_actuator")
    b.latch("hold", "plunger")

    b.sensor("plunger_x", "joint_angle", "plunger")
    b.sensor("plunger_v", "joint_velocity", "plunger")
    b.sensor("ball_v", "velocity", "ball")
    b.sensor("ball_p", "position", "ball")

    task = TaskIR(
        title="Rail launcher",
        goal_text=(
            "A latched plunger on a rail is pressed back against a coil spring with a "
            "ball resting against its face. When the drive phase starts the latch "
            "opens, the spring and the linear actuator throw the plunger forward until "
            "it reaches the end of its rail, the ball runs along the rail, leaves the "
            "open end and flies to the floor. Choose the pull-back distance and the "
            "actuator command so that the ball first touches the floor at the target "
            "distance measured along +y from the centre of the table."
        ),
        knobs=[
            KnobIR(
                name="pullback",
                low=-0.20,
                high=-0.05,
                unit="m",
                description=(
                    "plunger position on its rail before release; more negative pulls "
                    "the plunger (and the ball with it) further back and compresses "
                    "the spring more"
                ),
            ),
            KnobIR(
                name="drive",
                low=0.0,
                high=1.0,
                unit="-",
                description=(
                    "command held on the linear actuator during the drive phase; it "
                    "pushes the plunger forward alongside the spring"
                ),
            ),
        ],
        setup=[SetupIR(part="plunger", value="pullback")],
        phases=[
            PhaseIR(duration=0.5, ctrl={"drive": "drive"}, release=["hold"]),
            PhaseIR(duration=2.0, ctrl={}),
        ],
        horizon=2.5,
        outcome=OutcomeIR(kind="landing_point", part="ball", axes=["y"]),
        goal_space=[GoalDimIR(low=0.66, high=1.25)],
        tolerance=0.05,
        budget=70,
        escalation=[
            "initial version: latched spring plunger with motor-assisted stroke",
            "device-specific hidden projectile mass confounded with spring stiffness "
            "and actuator gain",
            "piecewise mechanics: latch release, plunger end-stop hand-off, rolling "
            "contact and free flight",
            "modifiable rail length changes both launch point and rolling losses",
        ],
        modifiable=[
            ModifiableIR(part="track", field="size1", low=0.18, high=0.45),
        ],
    )
    return Submission(device=b.finish(), task=task)
