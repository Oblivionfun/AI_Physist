"""Labeled bad designs for referee meta-evaluation.

Construction cheats must be rejected by the construction API with a specific issue code.
Certificate cheats pass construction but must fail a specific certificate.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from fixtures.devices import pendulum_striker, spring_launcher
from mlab.construct import Builder, Fixed, Hinge, Submission
from mlab.construct.ir import GoalDimIR, KnobIR, OutcomeIR, SetupIR, TaskIR


@dataclass(frozen=True)
class ConstructionCheat:
    name: str
    expected_code: str
    attempt: Callable[[], object]


@dataclass(frozen=True)
class CertificateCheat:
    name: str
    expected_codes: tuple[str, ...]
    submission: Callable[[], Submission]


def _floating_base():
    Builder("cheat").base("table", "box", [0.3, 0.1, 0.05], "wood", (0.0, 0.0, 0.4))


def _interpenetrating_block():
    b = Builder("cheat")
    b.base("table", "box", [0.3, 0.1, 0.05], "wood", (0.0, 0.0, 0.05))
    b.free("block", "box", [0.03, 0.03, 0.03], "steel", (0.0, 0.0, 0.11))


def _pin_in_mid_air():
    b = Builder("cheat")
    b.base("post", "box", [0.03, 0.03, 0.3], "aluminium", (0.0, 0.0, 0.3))
    b.attach("arm", "capsule", [0.01, 0.2], "aluminium", (0.3, 0.0, 0.4), to="post",
             joint=Hinge(anchor=(0.3, 0.0, 0.6), axis=(0.0, 1.0, 0.0)))


def _detached_fixed_part():
    b = Builder("cheat")
    b.base("post", "box", [0.03, 0.03, 0.3], "aluminium", (0.0, 0.0, 0.3))
    b.attach("bracket", "box", [0.02, 0.02, 0.02], "steel", (0.2, 0.0, 0.3), to="post",
             joint=Fixed())


def _absurd_sealed_density():
    b = Builder("cheat")
    b.hidden("m", 30.0, 60.0, "kg")
    b.base("post", "box", [0.03, 0.03, 0.3], "aluminium", (0.0, 0.0, 0.3))
    b.attach("weight", "box", [0.02, 0.02, 0.02], "steel", (0.0, 0.0, 0.62), to="post",
             joint=Fixed(), hidden_mass="m")


def _inflated_prior():
    Builder("cheat").hidden("m", 0.01, 5.0, "kg")


CONSTRUCTION_CHEATS = [
    ConstructionCheat("floating base", "support", _floating_base),
    ConstructionCheat("interpenetration", "overlap", _interpenetrating_block),
    ConstructionCheat("pin in mid air", "anchor", _pin_in_mid_air),
    ConstructionCheat("detached fixed part", "detached", _detached_fixed_part),
    ConstructionCheat("absurd sealed density", "density", _absurd_sealed_density),
    ConstructionCheat("inflated prior range", "prior", _inflated_prior),
]


def _turntable() -> Submission:
    """The outcome equals the knob: nothing hidden matters, so no learning is needed."""
    b = Builder("turntable")
    b.base("plinth", "box", [0.1, 0.1, 0.05], "wood", (0.0, 0.0, 0.05))
    b.attach("disk", "cylinder", [0.08, 0.01], "aluminium", (0.0, 0.0, 0.11), to="plinth",
             joint=Hinge(anchor=(0.0, 0.0, 0.105), axis=(0.0, 0.0, 1.0), model="bushing",
                         range=(-math.pi, math.pi)))
    b.sensor("disk_angle", "joint_angle", "disk")
    task = TaskIR(
        title="Turn the disk",
        goal_text="Set the disk so that it ends at the target angle.",
        knobs=[KnobIR(name="angle", low=-1.2, high=1.2, unit="rad")],
        setup=[SetupIR(part="disk", value="angle")],
        horizon=1.0,
        outcome=OutcomeIR(kind="final_joint_angle", part="disk"),
        goal_space=[GoalDimIR(low=-1.0, high=1.0)],
        tolerance=0.05,
    )
    return Submission(device=b.finish(), task=task)


CERTIFICATE_CHEATS = [
    CertificateCheat(
        "unreachable goals", ("C1",),
        lambda: spring_launcher.submission(goal=(1.2, 1.5)),
    ),
    CertificateCheat(
        "trivial tolerance", ("C2",),
        lambda: spring_launcher.submission(tolerance=0.2, goal=(0.5, 0.9)),
    ),
    CertificateCheat("hidden quantities irrelevant", ("C2",), _turntable),
    CertificateCheat(
        "chaotic goals off the table edge", ("C0", "C1", "C1b"),
        lambda: Submission(
            device=pendulum_striker.build_device().finish(),
            task=pendulum_striker.build_task(goal=(1.0, 1.4), knob_range=(0.2, 1.65)),
        ),
    ),
]
