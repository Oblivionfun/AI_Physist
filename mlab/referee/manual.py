"""Task card generation. Structural content comes from the construction record, never from
builder prose; the only builder-written fields are title, goal text and knob descriptions,
and those pass the leak scanner."""

from __future__ import annotations

from mlab.catalog.world import WORLD_PRIORS
from mlab.construct.compile import used_world_keys
from mlab.construct.describe import describe_device
from mlab.construct.ir import Submission
from mlab.construct.modify import current_value, mod_key
from mlab.referee.protocol import (
    KnobSpec,
    ModifiableSpec,
    OutcomeSpec,
    ProtocolSpec,
    SensorSpec,
    TaskCard,
    UnknownSpec,
)
from mlab.sim.observe import outcome_noise

TRACE_HZ = 25.0
PRETEST_GOALS = 3
EXAM_GOALS = 8
PROBE_EVERY = 10

RULES = """\
Protocol (enforced by the lab tool):
1. Pretest: you get {pretest} goals one at a time and must choose knob values for each
   before running any experiment on this device. Results are revealed only at the end.
2. Lab: up to {budget} experiments. Every experiment requires your prediction of the
   outcome before you see the result. Every {probe}th experiment is chosen by the referee:
   you are told the knob values, you predict, then you see the result.
3. Theory: submit predict.py defining predict(knobs: dict, visible: dict) -> list[float],
   your model of the outcome. `visible` holds the modifiable dimensions listed below; the
   referee may evaluate your model with different values for them, without letting you
   experiment. Also submit your estimates of the unknown quantities with 90% intervals.
4. Exam: {exam} goals one at a time, one attempt each, no experiments. Results are
   revealed only at the end.
5. Field report: optional tickets about the interface (bugs, ambiguity, suspected
   unsolvability). Tickets go to the device builder; they cannot contain answers.
Outcome is a failure if the run status is not "ok" (e.g. the part never landed, or was
still moving at the end of the run)."""


def _outcome_text(sub: Submission) -> str:
    out = sub.task.outcome
    axes = ", ".join(out.axes)
    if out.kind == "landing_point":
        return f"the {axes} coordinate(s) of '{out.part}' at the moment it first touches the ground"
    if out.kind == "final_position":
        return (f"the {axes} coordinate(s) of '{out.part}' once it has come to rest (it must be at "
                f"rest by the end of the {sub.task.horizon:g} s run)")
    if out.kind == "max_height":
        return f"the highest z coordinate reached by '{out.part}' during the run"
    return f"the joint coordinate of '{out.part}' at the end of the run"


def unknown_specs(sub: Submission) -> list[UnknownSpec]:
    specs = []
    for key in sorted(used_world_keys(sub.device)):
        p = WORLD_PRIORS[key]
        specs.append(UnknownSpec(name=key, description=p.description, low=p.low, high=p.high,
                                 unit=p.unit))
    for h in sub.device.hidden:
        specs.append(UnknownSpec(name=h.name, description=h.description or "device-specific",
                                 low=h.low, high=h.high, unit=h.unit))
    return specs


def build_card(sub: Submission, version: int, changelog: list[str] | None = None,
               disclose_unknowns: bool = True) -> TaskCard:
    task, device = sub.task, sub.device
    manual = describe_device(device)
    manual += (
        "\nPhysics: rigid bodies with soft contacts, gravity 9.81 m/s^2 along -z. Contact "
        "friction between two surfaces is the larger of their two coefficients. Parts made of "
        "the same material share the same (unknown) friction everywhere in this world."
    )
    if task.setup:
        manual += "\nBefore each run: " + "; ".join(
            f"joint of '{s.part}' is set to "
            + (f"knob '{s.value}'" if isinstance(s.value, str) else f"{s.value:g}")
            for s in task.setup
        )
    if task.phases:
        lines = []
        for i, ph in enumerate(task.phases):
            dur = f"knob '{ph.duration}'" if isinstance(ph.duration, str) else f"{ph.duration:g} s"
            cmds = ", ".join(
                f"{a} = " + (f"knob '{v}'" if isinstance(v, str) else f"{v:g}")
                for a, v in ph.ctrl.items()
            )
            rel = f"; release {', '.join(ph.release)} at start" if ph.release else ""
            lines.append(f"phase {i}: lasts {dur}; commands [{cmds or 'none'}]{rel}")
        manual += "\nAction program (then all commands 0 until the end): " + " | ".join(lines)
    return TaskCard(
        version=version,
        title=task.title,
        goal_text=task.goal_text,
        manual=manual,
        knobs=[KnobSpec(name=k.name, low=k.low, high=k.high, unit=k.unit,
                        description=k.description) for k in task.knobs],
        sensors=[SensorSpec(name=s.name, kind=s.kind, part=s.part, noise=s.noise,
                            rate_hz=TRACE_HZ) for s in device.sensors],
        unknowns=unknown_specs(sub) if disclose_unknowns else [],
        outcome=OutcomeSpec(
            kind=task.outcome.kind, part=task.outcome.part, axes=list(task.outcome.axes),
            description=_outcome_text(sub), noise=outcome_noise(task),
            goal_space=[(g.low, g.high) for g in task.goal_space], tolerance=task.tolerance,
        ),
        modifiable=[ModifiableSpec(name=mod_key(m), current=current_value(device, m), low=m.low,
                                   high=m.high) for m in task.modifiable],
        protocol=ProtocolSpec(pretest_goals=PRETEST_GOALS, budget=task.budget,
                              probe_every=PROBE_EVERY, exam_goals=EXAM_GOALS, horizon=task.horizon),
        rules=RULES.format(pretest=PRETEST_GOALS, budget=task.budget, probe=PROBE_EVERY,
                           exam=EXAM_GOALS),
        changelog=changelog or [],
    )
