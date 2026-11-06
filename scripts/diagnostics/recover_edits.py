"""Recover a file as an agent left it after a given edit, from a cursor-agent stream-json
transcript (each completed edit event carries the full file content after the edit).

    uv run python scripts/diagnostics/recover_edits.py \
        ~/mlab-runs/demo-1/referee/transcripts/builder_call03.jsonl --list
    uv run python scripts/diagnostics/recover_edits.py \
        ~/mlab-runs/demo-1/referee/transcripts/builder_call03.jsonl 1007 sliding_slug.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def events(transcript: Path) -> list[dict]:
    return [json.loads(line) for line in transcript.read_text().splitlines()
            if line.strip().startswith("{")]


def after_edit(rows: list[dict], index: int) -> str:
    call_id = rows[index]["call_id"]
    for e in rows[index:]:
        if e.get("subtype") == "completed" and e.get("call_id") == call_id:
            return e["tool_call"]["editToolCall"]["result"]["success"]["afterFullFileContent"]
    raise SystemExit(f"event {index} has no completed edit result")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("transcript", type=Path)
    ap.add_argument("index", type=int, nargs="?")
    ap.add_argument("out", type=Path, nargs="?")
    ap.add_argument("--list", action="store_true", help="list edit events")
    args = ap.parse_args()
    rows = events(args.transcript)
    if args.list or args.index is None:
        for i, e in enumerate(rows):
            if e.get("type") == "tool_call" and e.get("subtype") == "started":
                edit = e["tool_call"].get("editToolCall")
                if edit:
                    print(i, edit["args"]["path"], len(edit["args"].get("streamContent", "")))
        return
    text = after_edit(rows, args.index)
    if args.out:
        args.out.write_text(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
