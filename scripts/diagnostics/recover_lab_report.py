"""Recover the referee's end-of-session results (`lab report`) from learner transcripts.

The report is computed by the referee and shown to the learner when its session ends, so the
transcript keeps an authentic copy even if the orchestrator crashed before saving the session.

    uv run python scripts/diagnostics/recover_lab_report.py \
        ~/mlab-runs/demo-3/referee/transcripts/learner_v3_main_s3.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def lab_report(transcript: Path) -> dict | None:
    found = None
    for line in transcript.read_text().splitlines():
        if not line.strip().startswith("{"):
            continue
        e = json.loads(line)
        if e.get("type") != "tool_call" or e.get("subtype") != "completed":
            continue
        shell = e["tool_call"].get("shellToolCall")
        if not shell or "lab report" not in shell.get("args", {}).get("command", ""):
            continue
        result = shell.get("result", {})
        stdout = (result.get("success") or result.get("failure") or {}).get("stdout", "")
        if "{" in stdout:
            found = json.loads(stdout[stdout.index("{"):]).get("results")
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("transcripts", type=Path, nargs="+")
    args = ap.parse_args()
    for t in args.transcripts:
        results = lab_report(t)
        if results is None:
            print(f"{t.name}: no lab report found")
            continue
        for phase in ("pretest", "exam"):
            attempts = results.get(phase, [])
            knobs = sorted({json.dumps(a["knobs"], sort_keys=True) for a in attempts})
            print(f"{t.name} {phase}: {sum(a['success'] for a in attempts)}/{len(attempts)} hits; "
                  f"{len(knobs)} distinct knob settings")
            for a in attempts:
                print(f"    goal {a['goal']} knobs {a['knobs']} observed {a['observed_outcome']} "
                      f"status {a['status']} success {a['success']}")


if __name__ == "__main__":
    main()
