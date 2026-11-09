"""Static bundle of a finished run for the web front end (no server needed to view it).

The bundle reveals hidden truth (world values, instance parameters, true outcomes), so it is
only written for finished runs, into `demo/recorded/<run_id>/viz/`, which neither agent can
read.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from observatory.feed import RunFeed

BUNDLE_VERSION = 1


def _write(path: Path, obj) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text)
    return len(text)


def export_run(root: Path, dest: Path, cache_root: Path, log=print) -> dict:
    feed = RunFeed(root, cache_root)
    feed.poll()
    if not feed.ended:
        raise SystemExit(
            f"run '{feed.run_id}' has not finished (no referee/summary.json); a live "
            "run is viewed through `observatory serve`, never exported"
        )
    t0 = time.time()
    size = _write(dest / "events.json", [e.model_dump() for e in feed.events])
    replays: dict[str, str] = {}
    curves: dict[str, dict[str, str]] = {}
    for r in feed.rounds():
        for label in ("A", "B"):
            reps = feed.session_replays(r, label)
            if reps:
                rel = f"replays/r{r}_{label}.json"
                size += _write(dest / rel, reps)
                replays[f"{r}:{label}"] = rel
        default = feed.curves(r)
        if default is None:
            continue
        curves[str(r)] = {"default": default["knob"]}
        for knob in feed.knob_names(r):
            c = default if knob == default["knob"] else feed.curves(r, knob)
            if c is not None:
                rel = f"curves/r{r}_{knob}.json"
                size += _write(dest / rel, c)
                curves[str(r)][knob] = rel
        log(f"  round {r}: replays and curves done ({time.time() - t0:.0f}s)")
    end = next(e for e in reversed(feed.events) if e.kind == "run_end").data
    manifest = {
        "version": BUNDLE_VERSION,
        "run_id": feed.run_id,
        "generated": time.time(),
        "events": "events.json",
        "replays": replays,
        "curves": curves,
        "builder": end.get("builder"),
        "learner": end.get("learner"),
        "rerun_of": _rerun_of(end.get("builder")),
        "rounds": [
            {"round": x["round"], "status": x["status"], "device": x.get("device")}
            for x in end.get("rounds") or []
        ],
    }
    size += _write(dest / "manifest.json", manifest)
    log(f"exported {feed.run_id}: {len(feed.events)} events, {size / 1e6:.1f} MB -> {dest}")
    return manifest


def _rerun_of(builder: str | None) -> str | None:
    """Runs made with `mlab rerun-learner` replay the certified designs of a source run."""
    if builder and builder.startswith("recorded:"):
        return builder.removeprefix("recorded:")
    return None


def write_index(recorded: Path) -> Path:
    runs = []
    for manifest in sorted(recorded.glob("*/viz/manifest.json")):
        m = json.loads(manifest.read_text())
        runs.append(
            {
                "run_id": m["run_id"],
                "path": f"{manifest.parent.parent.name}/viz",
                "builder": m.get("builder"),
                "learner": m.get("learner"),
                "rerun_of": m.get("rerun_of"),
                "rounds": m.get("rounds", []),
            }
        )
    path = recorded / "viz-index.json"
    _write(path, {"runs": runs})
    return path
