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
    b = Builder("ramp_launcher")

    b.hidden(
        "ball_mass",
        0.3,
        0.9,
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

    # Take-off ramp hinged at the far end of the rail, locked at the chosen tilt.
    # At tilt 0 its top face is flush with the rail top, so the ball runs straight on.
    b.attach(
        "ramp",
        "box",
        [0.06, 0.13, 0.008],
        "wood",
        (0.0, 0.33, 0.512),
        to="track",
        joint=Hinge(
            anchor=(0.0, 0.20, 0.52),
            axis=(1.0, 0.0, 0.0),
            model="bearing",
            range=(0.0, 0.55),
        ),
    )

    # Separate stand beside the rail carries the sliding plunger. The spring rests
    # short of the forward end-stop, so the plunger decelerates and hands the ball
    # off smoothly before it ever reaches the stop.
    b.base("stand", "box", [0.04, 0.03, 0.29], "aluminium", (0.16, 0.105, 0.29))
    b.attach(
        "plunger",
        "box",
        [0.075, 0.03, 0.008],
        "wood",
        (0.045, 0.105, 0.545),
        to="stand",
        joint=Slide(
            anchor=(0.12, 0.105, 0.545),
            axis=(0.0, 1.0, 0.0),
            range=(-0.34, 0.0),
            model="rail",
            spring=Spring(model="coil_stiff", rest=-0.10),
        ),
    )

    b.free(
        "ball",
        "sphere",
        [0.025],
        "steel",
        (0.0, 0.16, 0.545),
        hidden_mass="ball_mass",
        carried_by="plunger",
    )

    b.motor("drive", "plunger", "linear_actuator")
    b.latch("hold", "plunger")
    b.latch("tilt_lock", "ramp")

    b.sensor("plunger_x", "joint_angle", "plunger")
    b.sensor("plunger_v", "joint_velocity", "plunger")
    b.sensor("ball_v", "velocity", "ball")
    b.sensor("ball_p", "position", "ball")

    task = TaskIR(
        title="Ramp launcher",
        goal_text=(
            "A latched plunger on a rail is pressed back against a coil spring with a "
            "ball resting against its face. When the drive phase starts the latch "
            "opens and the spring, helped by the linear actuator, throws the plunger "
            "forward; past the spring's rest point the plunger slows, the ball runs "
            "on alone, climbs the locked take-off ramp at the end of the rail and "
            "flies to the floor. Climbing the ramp costs speed but adds launch angle "
            "and height. Choose pull-back, actuator command and ramp tilt so the ball "
            "first touches the floor at the target distance measured along +y from "
            "the centre of the table."
        ),
        knobs=[
            KnobIR(
                name="pullback",
                low=-0.32,
                high=-0.12,
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
                high=0.6,
                unit="-",
                description=(
                    "command held on the linear actuator during the drive phase; it "
                    "pushes the plunger forward alongside the spring"
                ),
            ),
            KnobIR(
                name="tilt",
                low=0.0,
                high=0.5,
                unit="rad",
                description=(
                    "angle at which the take-off ramp is locked before the run; 0 "
                    "leaves it flush with the rail, larger values raise its far end "
                    "so the ball must run uphill before it leaves"
                ),
            ),
        ],
        setup=[
            SetupIR(part="plunger", value="pullback"),
            SetupIR(part="ramp", value="tilt"),
        ],
        phases=[
            PhaseIR(duration=0.5, ctrl={"drive": "drive"}, release=["hold"]),
            PhaseIR(duration=2.5, ctrl={}),
        ],
        horizon=3.0,
        outcome=OutcomeIR(kind="landing_point", part="ball", axes=["y"]),
        goal_space=[GoalDimIR(low=0.75, high=1.48)],
        tolerance=0.05,
        budget=50,
        escalation=[
            "new mechanism: a hinged take-off ramp locked at a chosen angle sits "
            "between the rolling ball and free flight",
            "third knob (ramp tilt) that interacts with the energy knobs instead of "
            "adding an independent axis",
            "sign reversal: raising the ramp lengthens a fast shot but shortens a slow "
            "one, so the useful direction of the tilt knob depends on the hidden mass "
            "and the spring",
            "a stall cliff: below a tilt-dependent speed the ball fails to crest the "
            "ramp and never leaves the device",
            "budget cut from 70 to 50 experiments while the action space gained a "
            "dimension",
            "modifiable ramp length changes launch point, climb loss and launch height "
            "at once",
        ],
        modifiable=[
            ModifiableIR(part="ramp", field="size1", low=0.13, high=0.30),
        ],
    )
    return Submission(device=b.finish(), task=task)
