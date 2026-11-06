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


def _camera(sub: Submission) -> mujoco.MjvCamera:
    lo = np.min([part_aabb(p)[0] for p in sub.device.parts], axis=0)
    hi = np.max([part_aabb(p)[1] for p in sub.device.parts], axis=0)
    cam = mujoco.MjvCamera()
    cam.lookat[:] = (lo + hi) / 2
    cam.distance = float(1.15 * max(hi[0] - lo[0], hi[2] - lo[2]) + 0.45)
    cam.azimuth = -90.0
    cam.elevation = -14.0
    return cam


def _marker(scene: mujoco.MjvScene, pos, rgba, radius: float = 0.02) -> None:
    if scene.ngeom >= scene.maxgeom:
        return
    mujoco.mjv_initGeom(scene.geoms[scene.ngeom], mujoco.mjtGeom.mjGEOM_SPHERE,
                        np.array([radius, 0, 0]), np.asarray(pos, dtype=float), np.eye(3).ravel(),
                        np.asarray(rgba, dtype=np.float32))
    scene.ngeom += 1


def render_action(sub: Submission, dev: CompiledDevice, knobs: dict, goal: list[float] | None,
                  caption: str, out: Path) -> Path:
    renderer = mujoco.Renderer(dev.model, HEIGHT, WIDTH)
    cam = _camera(sub)
    frames: list[Image.Image] = []
    marker = None
    if goal is not None and sub.task.outcome.kind in ("landing_point", "final_position"):
        axes = {"x": 0, "y": 1, "z": 2}
        pos = np.array([0.0, 0.0, 0.005])
        for a, g in zip(sub.task.outcome.axes, goal, strict=True):
            pos[axes[a]] = g
        part = sub.device.part(sub.task.outcome.part)
        if "z" not in sub.task.outcome.axes and sub.task.outcome.kind == "final_position":
            pos[2] = part.pos[2]
        marker = pos

    def grab(data: mujoco.MjData) -> None:
        renderer.update_scene(data, camera=cam)
        if marker is not None:
            _marker(renderer.scene, marker, (0.1, 0.85, 0.3, 0.9))
        img = Image.fromarray(renderer.render())
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, WIDTH, 22), fill=(255, 255, 255))
        draw.text((6, 5), f"{caption}   t={data.time:.2f}s", fill=(0, 0, 0))
        frames.append(img)

    result = simulate(dev, sub.task, knobs, sample_hz=FPS, early_stop=True, on_sample=grab)
    if frames:
        draw = ImageDraw.Draw(frames[-1])
        outcome = None if result.outcome is None else [round(float(v), 3) for v in result.outcome]
        draw.text((6, HEIGHT - 18), f"outcome {outcome} status {result.status}", fill=(255, 255, 255))
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
                f"round {round_index} exam goal {np.round(a['goal'], 3).tolist()} ({tag})",
                dest / f"r{round_index}_exam_{tag}.gif"))
    return outputs
