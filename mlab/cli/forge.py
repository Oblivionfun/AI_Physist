"""forge: the building agent's toolkit (docs, local check, describe, submit).

Runs inside the builder sandbox. Local checks certify against a world drawn from the
priors, never the real one, so the builder cannot learn the true values.
"""

from __future__ import annotations

import argparse
import json
import runpy
import sys
import time
from pathlib import Path

import numpy as np

from mlab.catalog import JOINT_MODELS, MATERIALS, MOTOR_MODELS, SENSOR_MIN_NOISE, SPRING_MODELS
from mlab.catalog.priors import MAX_PRIOR_RATIO
from mlab.catalog.world import WORLD_PRIORS, sample_world, world_key
from mlab.construct import ConstructionError, Submission, check_device, check_task, describe_device
from mlab.construct import checks as C
from mlab.referee.certify import FAST, TEST, THRESHOLDS, certify
from mlab.referee.manual import EXAM_GOALS, PRETEST_GOALS, PROBE_EVERY

EXAMPLE = '''\
import math
from mlab.construct import Builder, Fixed, Hinge, Submission
from mlab.construct.ir import GoalDimIR, KnobIR, OutcomeIR, SetupIR, TaskIR


def build() -> Submission:
    b = Builder("toy_pendulum")                      # names: lowercase, digits, underscores
    b.base("post", "box", [0.03, 0.03, 0.3], "aluminium", (0.0, 0.0, 0.3))
    b.attach("axle", "cylinder", [0.008, 0.04], "steel", (0.0, 0.07, 0.55),
             euler=(math.pi / 2, 0.0, 0.0), to="post", joint=Fixed())
    b.attach("rod", "capsule", [0.01, 0.2], "aluminium", (0.0, 0.08, 0.35), to="axle",
             joint=Hinge(anchor=(0.0, 0.08, 0.55), axis=(0.0, 1.0, 0.0), model="bushing",
                         range=(-2.0, 2.0)))
    b.sensor("rod_angle", "joint_angle", "rod")
    task = TaskIR(
        title="Swing", goal_text="Release the rod so it ends at the target angle.",
        knobs=[KnobIR(name="start", low=0.2, high=1.5, unit="rad", description="start angle")],
        setup=[SetupIR(part="rod", value="start")], horizon=3.0,
        outcome=OutcomeIR(kind="final_joint_angle", part="rod"),
        goal_space=[GoalDimIR(low=0.1, high=1.0)], tolerance=0.05, budget=40,
        escalation=["toy example"],
    )
    return Submission(device=b.finish(), task=task)
'''


def docs() -> str:
    out = ["# forge documentation", "",
           ("You build a device with the construction API (python, `mlab.construct`) and declare a "
           "task. Write `device.py` defining `build() -> Submission`. Every construction call is "
           "checked immediately; a rejected call raises ConstructionError with the measured value, "
           "the limit and a fix."), "",
           "## Coordinates", ("Metres, radians, z up, ground plane at z=0. Every pose you give is the "
           "world pose of the built configuration, in which every hinge/slide coordinate is 0. "
           "euler=(rx, ry, rz) is applied as x, then y, then z (extrinsic). Capsules and cylinders "
           "lie along their local z axis. Sizes: box = half extents [x, y, z]; sphere = [radius]; "
           "capsule/cylinder = [radius, half_length]."), "",
           "## Construction calls (Builder)",
           ("- hidden(name, low, high, unit, scale='linear'|'log', description): a device-specific "
           f"unknown; max/min <= {MAX_PRIOR_RATIO:.0f}. The referee draws its value; you never see it."),
           ("- base(name, shape, size, material, pos, euler): fixed to the world; its lowest point must "
           f"be on the ground (|z| <= {C.GROUND_TOL} m)."),
           ("- attach(name, shape, size, material, pos, to=parent, joint=Fixed()|Hinge(...)|Slide(...), "
           "euler, hidden_mass=None): Fixed parts must touch their parent (gap <= "
           f"{C.TOUCH_GAP * 1000:.0f} mm) and become one rigid body with it. Hinge(anchor, axis, model, "
           "spring=Spring(model, rest), range=(lo, hi)) and Slide(anchor, axis, range, model, spring): "
           f"the anchor must lie on both parts (within {C.ANCHOR_MARGIN * 1000:.0f} mm); range must "
           "contain 0; slides need a range. A jointed part does not collide with the part its pin "
           "passes through; everything else collides."),
           ("- free(name, shape, size, material, pos, euler, hidden_mass=None, carried_by=None): a loose "
           "body (projectile, puck). carried_by=part moves it rigidly with that part when the setup "
           "changes joint coordinates (e.g. a ball in a cup on an arm)."),
           ("- motor(name, part, model); latch(name, part): a latch locks a hinge/slide at its start "
           "value until a phase releases it."),
           "- sensor(name, kind, part, noise=None): kinds joint_angle, joint_velocity (jointed parts), "
           "position, velocity (part centre). Noise floors: "
           + ", ".join(f"{k} {v}" for k, v in SENSOR_MIN_NOISE.items()) + ".",
           "- zone(name, pos, radius): visual marker only. query(): text description.",
           (f"Limits: {C.MAX_PARTS} parts, {C.MAX_ACTUATORS} actuators, {C.MAX_LATCHES} latches, "
           f"{C.MAX_SENSORS} sensors, {C.MAX_HIDDEN} hidden; half sizes {C.MIN_HALF_SIZE}-"
           f"{C.MAX_HALF_SIZE} m; part mass {C.MIN_PART_MASS}-{C.MAX_PART_MASS} kg; sealed parts "
           f"(hidden_mass) must imply density within {C.SEALED_DENSITY_RANGE} kg/m^3. You cannot set "
           "masses of ordinary parts, friction, damping, stiffness or motor strength directly: they "
           "come from the catalog below and are unknown world properties."), "",
           "## Catalog", "Materials (density kg/m^3, sliding friction prior):"]
    for m in MATERIALS.values():
        p = WORLD_PRIORS[world_key("friction", m.name)]
        note = " (bases only)" if m.ground_only else ""
        out.append(f"- {m.name}: {m.density:g}; friction {p.low}-{p.high}{note}")
    r = WORLD_PRIORS[world_key("rolling", "steel")]
    out.append(f"Rolling resistance of spheres: {r.low}-{r.high} m for every material. Contact "
               "friction between two surfaces is the larger of the two coefficients.")
    out.append("Joint models (damping, dry friction priors):")
    for j in JOINT_MODELS.values():
        d, f = WORLD_PRIORS[world_key("damping", j.name)], WORLD_PRIORS[world_key("frictionloss", j.name)]
        out.append(f"- {j.name} ({j.kind}): damping {d.low}-{d.high} {d.unit}, friction {f.low}-{f.high} {f.unit}")
    out.append("Springs (stiffness priors):")
    for s in SPRING_MODELS.values():
        p = WORLD_PRIORS[world_key("stiffness", s.name)]
        out.append(f"- {s.name} ({s.kind}): {p.low}-{p.high} {p.unit}")
    out.append("Motors (output per unit command, command in [-1, 1]):")
    for mm in MOTOR_MODELS.values():
        p = WORLD_PRIORS[world_key("gain", mm.name)]
        out.append(f"- {mm.name} ({mm.kind}): {p.low}-{p.high} {p.unit}")
    out += ["Each world property is drawn once per run and is the same in every device you build.",
            "", "## Task declaration (TaskIR)",
            ("- knobs: 1-4 scalars the learner chooses; setup: [SetupIR(part, value)] sets a joint "
            "coordinate before the run (value = number or knob name); phases: [PhaseIR(duration, "
            "ctrl={actuator: value}, release=[latch])], then all commands are 0; horizon <= 8 s."),
            ("- outcome: OutcomeIR(kind, part, axes). landing_point = position where a free part first "
            "touches the ground; final_position = position once at rest (must be at rest at the end); "
            "max_height; final_joint_angle. goal_space: one GoalDimIR per outcome dimension; "
            f"tolerance >= {C.MIN_TOLERANCE}; budget {C.BUDGET_RANGE[0]}-{C.BUDGET_RANGE[1]} experiments."),
            ("- goal_text (<= 600 chars) and knob descriptions are the only prose the learner sees from "
            "you; everything structural is generated from your construction record. Never put numbers "
            "about unknowns in prose (a leak scanner rejects them)."),
            ("- escalation: list of the dimensions in which this version is harder than the last "
            "(e.g. more unknowns, confounded unknowns needing designed experiments, fewer sensors, "
            "piecewise mechanics such as contacts/latches/stick-slip, more knobs, smaller budget, "
            "composition of earlier parts)."),
            ("- modifiable: [ModifiableIR(part, field, low, high)] visible dimensions (size0-2, posx/y/z) "
            "the referee may change publicly when testing the learner's model; the device must stay "
            "valid over the whole range. Choose dimensions that change outcomes a lot: only a learner "
            "that understood the physics can predict them."), "",
            "## Certification (run by the referee on every submission)",
            (f"C0 physics: construction rules; stable simulation; no passive energy gain (> "
            f"{THRESHOLDS['C0_energy']:.0%} of peak kinetic); timestep convergence of solving actions "
            f"(< {THRESHOLDS['C0_dt']:g} x tolerance)."),
            (f"C1 existence: a privileged solver that knows the true values hits >= {THRESHOLDS['C1']:.0%} "
            f"of goals under actuation noise; C1b: +-1% knob perturbations still hit >= "
            f"{THRESHOLDS['C1b']:.0%}."),
            (f"C2 necessity: solving with prior-centre values hits <= {THRESHOLDS['C2_nominal']:.0%} of goals "
            f"(over the prior); one fixed action reaches <= {THRESHOLDS['C2_fixed']:.0%} of goals."),
            (f"C3 identifiability: after the budget, outcome uncertainty < {THRESHOLDS['C3_predictive']:g} x "
            f"tolerance, and a gray-box learner (knows your structure, not the values) hits >= "
            f"{THRESHOLDS['C3_reference']:.0%}."),
            "Rejected submissions come back with the failing check and a suggested fix.", "",
            "## What the learner gets",
            (f"The generated manual, knobs, sensors and unknown ranges; {PRETEST_GOALS} pretest goals before "
            f"any experiment; the budget of experiments (prediction required first, every "
            f"{PROBE_EVERY}th chosen by the referee); then it submits an executable model; then "
            f"{EXAM_GOALS} exam goals, one shot each. Two twin instances whose device-specific unknowns "
            "differ are studied separately. A model-free curve-fitting baseline is run too; if it "
            "succeeds, your challenge can be brute-forced."), "",
            "## Commands",
            ("./forge docs | ./forge check device.py [--profile test|fast] | ./forge describe device.py | "
             "./forge submit device.py. Every command prints the time left in your session; a session "
             "that ends without a submission counts as a failed round."), "",
            "## Minimal example (API illustration only)",
            ("This builds without errors, but as a task it is rejected by C1: a released rod always "
            "comes to rest hanging down, so the goal angles are unreachable. Design your own device."),
            "```python", EXAMPLE, "```"]
    return "\n".join(out)


SESSION = Path("forge.json")


def session_info() -> dict:
    """Written by the referee into the builder workspace: deadline and certification profile."""
    try:
        return json.loads(SESSION.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def time_banner() -> str:
    deadline = session_info().get("deadline")
    if not deadline:
        return ""
    left = deadline - time.time()
    if left <= 0:
        return "[time] the session deadline has passed: submit now with ./forge submit device.py"
    msg = f"[time] {left / 60:.0f} min left in this session"
    if left < 0.25 * session_info().get("budget_seconds", left * 4):
        msg += " - submit your best certified design soon (./forge submit device.py)"
    return msg


def load(path: str) -> Submission:
    ns = runpy.run_path(path)
    if "build" not in ns:
        raise SystemExit(f"{path} must define build() -> Submission")
    sub = ns["build"]()
    if not isinstance(sub, Submission):
        raise SystemExit("build() must return mlab.construct.Submission")
    return sub


def _static_issues(sub: Submission) -> list[str]:
    issues, _ = check_device(sub.device)
    issues += check_task(sub.device, sub.task)
    return [str(i) for i in issues]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="forge")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("docs")
    c = sp.add_parser("check")
    c.add_argument("path")
    c.add_argument("--profile", choices=["test", "fast"],
                   default=session_info().get("profile", "fast"),
                   help="defaults to the profile the referee uses in this run (capped at fast)")
    d = sp.add_parser("describe")
    d.add_argument("path")
    s = sp.add_parser("submit")
    s.add_argument("path")
    args = ap.parse_args(argv)
    banner = time_banner()
    if banner:
        print(banner)
    if args.cmd == "docs":
        print(docs())
        return 0
    try:
        sub = load(args.path)
    except ConstructionError as exc:
        print("CONSTRUCTION REJECTED\n" + str(exc))
        return 1
    if args.cmd == "describe":
        print(describe_device(sub.device))
        print(json.dumps(sub.task.model_dump(), indent=1))
        return 0
    issues = _static_issues(sub)
    if issues:
        print("INVALID\n" + "\n".join(issues))
        return 1
    if args.cmd == "check":
        seed = int(time.time())
        world = sample_world(np.random.default_rng(seed))
        cert = certify(sub, world, np.random.default_rng(seed + 1),
                       TEST if args.profile == "test" else FAST, stop_on_fail=False)
        print(f"(local check against a world drawn from the priors, seed {seed}; the real world "
              "differs)\n" + cert.report())
        stats = {k: v for k, v in cert.stats.items() if k != "reference_unit_error"}
        print("stats: " + json.dumps(stats, default=str))
        return 0 if cert.passed else 1
    outbox = Path("outbox")
    outbox.mkdir(exist_ok=True)
    (outbox / "submission.json").write_text(json.dumps(sub.model_dump(), indent=1))
    print("submitted outbox/submission.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
