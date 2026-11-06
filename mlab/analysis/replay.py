"""Post-run replay: re-simulate recorded actions on the true instance and render them.

Runs referee-side after a run; replays are deterministic re-simulations without actuation
noise, so they show the intended action, not the exact noisy trial.
"""

from __future__ import annotations

import json
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image, ImageDraw

from mlab.construct import Submission, compile_device
from mlab.construct.compile import CompiledDevice
from mlab.construct.geometry import part_aabb
from mlab.sim.runner import simulate

WIDTH, HEIGHT = 560, 360
FPS = 25


def certified_submission(root: Path, round_index: int) -> Submission | None:
    summary = json.loads((root / "referee" / "summary.json").read_text())
    r = next((x for x in summary["rounds"] if x["round"] == round_index), None)
    if r is None or r.get("status") != "ok":
        return None
    attempt = next(a["attempt"] for a in r["attempts"] if a["passed"])
    path = root / "referee" / "submissions" / f"r{round_index}_a{attempt}.json"
    return Submission.model_validate_json(path.read_text())


def instance_device(root: Path, round_index: int, label: str, sub: Submission) -> CompiledDevice:
    thetas = json.loads((root / "referee" / "instances" / f"r{round_index}.json").read_text())
    return compile_device(sub.device, thetas[label])


def _moving_parts(sub: Submission) -> list:
    """Parts that can move: jointed or free parts and everything fixed onto them."""
    parts = {p.name: p for p in sub.device.parts}

    def moves(p) -> bool:
        while p.mount.kind == "fixed" and p.mount.parent is not None:
            p = parts[p.mount.parent]
        return p.mount.kind in ("hinge", "slide", "free")

    return [p for p in sub.device.parts if moves(p)]


def _goal_points(sub: Submission) -> list[np.ndarray]:
    task = sub.task
    if task.outcome.kind not in ("landing_point", "final_position"):
        return []
    axes = {"x": 0, "y": 1, "z": 2}
    base = np.asarray(sub.device.part(task.outcome.part).pos, dtype=float)
    points = []
    for corner in (0, 1):
        p = base.copy()
        if task.outcome.kind == "landing_point":
            p[2] = 0.0
        for a, g in zip(task.outcome.axes, task.goal_space, strict=True):
            p[axes[a]] = g.low if corner == 0 else g.high
        points.append(p)
    return points


def _camera(sub: Submission, extra: list[np.ndarray] | None = None) -> mujoco.MjvCamera:
    """Three-quarter view framing the moving mechanism (and `extra` points, e.g. the goals)."""
    focus = _moving_parts(sub) or sub.device.parts
    lo = np.min([part_aabb(p)[0] for p in focus], axis=0)
    hi = np.max([part_aabb(p)[1] for p in focus], axis=0)
    for point in extra or []:
        lo, hi = np.minimum(lo, point), np.maximum(hi, point)
    cam = mujoco.MjvCamera()
    cam.lookat[:] = (lo + hi) / 2
    cam.distance = float(1.15 * np.max(hi - lo) + 0.3)
    cam.azimuth = -125.0
    cam.elevation = -18.0
    return cam


def _marker(scene: mujoco.MjvScene, pos, rgba, radius: float = 0.02) -> None:
    if scene.ngeom >= scene.maxgeom:
        return
    mujoco.mjv_initGeom(scene.geoms[scene.ngeom], mujoco.mjtGeom.mjGEOM_SPHERE,
                        np.array([radius, 0, 0]), np.asarray(pos, dtype=float), np.eye(3).ravel(),
                        np.asarray(rgba, dtype=np.float32))
    scene.ngeom += 1


def _pin(scene: mujoco.MjvScene, pos, rgba, height: float = 0.12) -> None:
    """A thin vertical pin standing on `pos`, visible even where it overlaps a goal marker."""
    if scene.ngeom >= scene.maxgeom:
        return
    centre = np.asarray(pos, dtype=float) + np.array([0.0, 0.0, height / 2])
    mujoco.mjv_initGeom(scene.geoms[scene.ngeom], mujoco.mjtGeom.mjGEOM_CYLINDER,
                        np.array([0.006, height / 2, 0]), centre, np.eye(3).ravel(),
                        np.asarray(rgba, dtype=np.float32))
    scene.ngeom += 1


def _outcome_point(sub: Submission, values) -> np.ndarray | None:
    """Where an outcome (or goal) of a positional task lies in the world, for a marker."""
    task = sub.task
    if values is None or task.outcome.kind not in ("landing_point", "final_position"):
        return None
    axes = {"x": 0, "y": 1, "z": 2}
    pos = np.array([0.0, 0.0, 0.005])
    if task.outcome.kind == "final_position" and "z" not in task.outcome.axes:
        pos[2] = sub.device.part(task.outcome.part).pos[2]
    for a, v in zip(task.outcome.axes, values, strict=True):
        pos[axes[a]] = float(v)
    return pos


GOAL_RGBA = (0.1, 0.85, 0.3, 0.9)
OUTCOME_RGBA = (1.0, 0.55, 0.1, 0.9)


def render_action(sub: Submission, dev: CompiledDevice, knobs: dict, goal: list[float] | None,
                  caption: str, out: Path) -> Path:
    """Green ball: the goal. Orange pin: where the outcome was measured (for a landing point,
    the first touch of the ground; the part may bounce or roll on afterwards)."""
    renderer = mujoco.Renderer(dev.model, HEIGHT, WIDTH)
    cam = _camera(sub, _goal_points(sub))
    frames: list[Image.Image] = []
    result = simulate(dev, sub.task, knobs)
    goal_pos = _outcome_point(sub, goal)
    outcome_pos = _outcome_point(sub, result.outcome)

    def grab(data: mujoco.MjData) -> None:
        renderer.update_scene(data, camera=cam)
        if goal_pos is not None:
            _marker(renderer.scene, goal_pos, GOAL_RGBA)
        if outcome_pos is not None:
            _pin(renderer.scene, outcome_pos, OUTCOME_RGBA)
        img = Image.fromarray(renderer.render())
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, WIDTH, 22), fill=(255, 255, 255))
        draw.text((6, 5), f"{caption}   t={data.time:.2f}s", fill=(0, 0, 0))
        frames.append(img)

    simulate(dev, sub.task, knobs, sample_hz=FPS, early_stop=True, on_sample=grab)
    if frames:
        draw = ImageDraw.Draw(frames[-1])
        outcome = None if result.outcome is None else [round(float(v), 3) for v in result.outcome]
        text = f"outcome (orange pin) {outcome}, status {result.status}"
        if goal is not None and result.outcome is not None:
            miss = float(np.linalg.norm(np.asarray(result.outcome) - np.asarray(goal)))
            verdict = "HIT" if miss <= sub.task.tolerance else "MISS"
            text += f"; goal (green) {np.round(goal, 3).tolist()}: {verdict}"
        draw.rectangle((0, HEIGHT - 22, WIDTH, HEIGHT), fill=(255, 255, 255))
        draw.text((6, HEIGHT - 17), text, fill=(0, 0, 0))
        frames += [frames[-1]] * FPS
    out.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(1000 / FPS), loop=0,
                   optimize=True)
    renderer.close()
    return out


def snapshot(sub: Submission, dev: CompiledDevice, out: Path) -> Path:
    renderer = mujoco.Renderer(dev.model, HEIGHT, WIDTH)
    data = mujoco.MjData(dev.model)
    mujoco.mj_forward(dev.model, data)
    renderer.update_scene(data, camera=_camera(sub))
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(renderer.render()).save(out)
    renderer.close()
    return out


def replay_round(root: Path, round_index: int, dest: Path) -> list[Path]:
    """Device snapshot, the learner's first experiment, one failed and one hit exam answer."""
    sub = certified_submission(root, round_index)
    if sub is None:
        return []
    outputs = []
    dev = instance_device(root, round_index, "A", sub)
    outputs.append(snapshot(sub, dev, dest / f"r{round_index}_device.png"))
    sess_path = root / "referee" / "sessions" / f"r{round_index}_A.json"
    if not sess_path.exists():
        return outputs
    sess = json.loads(sess_path.read_text())
    if sess["lab"]:
        first = sess["lab"][0]
        outputs.append(render_action(sub, dev, first["knobs"], None,
                                     f"round {round_index} lab experiment #0 knobs {first['knobs']}",
                                     dest / f"r{round_index}_lab0.gif"))
    exam = [a for a in sess["attempts"] if a["phase"] == "exam"]
    for want, tag in ((False, "miss"), (True, "hit")):
        a = next((x for x in exam if x["success"] is want), None)
        if a is not None:
            outputs.append(render_action(
                sub, dev, a["knobs"], a["goal"],
                f"round {round_index} exam, recorded {tag} (noise-free replay)",
                dest / f"r{round_index}_exam_{tag}.gif"))
    return outputs
