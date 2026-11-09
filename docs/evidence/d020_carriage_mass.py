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
    b = Builder("gated_ramp_launcher")

    b.hidden(
        "ball_mass",
        0.3,
        0.9,
        "kg",
        description="sealed mass of the launched ball",
    )
    b.hidden(
        "gate_mass",
        0.02,
        0.10,
        "kg",
        description="sealed mass of the hinged gate plate at the ramp lip",
    )
    b.hidden(
        "carriage_mass",
        0.08,
        0.25,
        "kg",
        description="sealed mass of the sliding plunger carriage",
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

    # Sprung gate plate standing on the ramp lip. The ball has to shove it forward
    # over the edge before it can fly; the plate's sealed mass sets both the
    # impulse it absorbs and the inertia it opposes.
    b.attach(
        "gate",
        "box",
        [0.05, 0.005, 0.007],
        "aluminium",
        (0.0, 0.455, 0.527),
        to="ramp",
        joint=Hinge(
            anchor=(0.0, 0.455, 0.520),
            axis=(1.0, 0.0, 0.0),
            model="bearing",
            spring=Spring(model="torsion_soft", rest=0.0),
            range=(0.0, 2.0),
        ),
        hidden_mass="gate_mass",
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
        hidden_mass="carriage_mass",
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
    b.sensor("gate_a", "joint_angle", "gate")
    b.sensor("ball_v", "velocity", "ball")
    b.sensor("ball_p", "position", "ball")

    task = TaskIR(
        title="Gated ramp launcher",
        goal_text=(
            "A latched plunger is pressed back against a coil spring with a ball on "
            "its face. On release the spring and the actuator throw it forward; past "
            "the spring's rest point the plunger slows and the ball runs on alone. It "
            "climbs the locked ramp, then must shove a sprung gate plate off the ramp "
            "lip before it can fly. Climbing costs speed but buys launch angle and "
            "height; the gate takes a bite out of the shot and holds it outright if it "
            "arrives too slowly. Set pull-back, actuator command and tilt so the ball "
            "first touches the floor at the target distance along +y from the table "
            "centre."
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
                high=0.8,
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
                    "so the ball must run uphill before it reaches the gate"
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
        goal_space=[GoalDimIR(low=0.74, high=1.26)],
        tolerance=0.06,
        budget=48,
        escalation=[
            "a third device-specific hidden quantity: the sliding carriage is now "
            "sealed too, so three masses must be identified anew on every instance",
            "confounded unknowns that need designed experiments: carriage and ball "
            "mass share the launch stroke and only their sum sets the hand-off speed, "
            "while the gate barrier is paid for by the ball alone, so the two can only "
            "be separated by playing the stroke off against the gate crossing",
            "a third stall-like regime at the start of the chain: a heavy sealed "
            "carriage soaks up the stroke, so the pull-back needed before anything "
            "leaves the device is itself an instance-specific unknown",
            "smaller budget, 60 experiments down to 48, against one more unknown",
            "the reachable band is trimmed at the top, so shots now have to be aimed "
            "inside a narrower window of the device's authority",
        ],
        modifiable=[
            ModifiableIR(part="ramp", field="size1", low=0.13, high=0.34),
            ModifiableIR(part="gate", field="size2", low=0.005, high=0.013),
        ],
    )
    return Submission(device=b.finish(), task=task)
