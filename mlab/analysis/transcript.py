"""Summarize an agent CLI stream-json transcript (referee-side tooling)."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def events(path: Path):
    for line in path.read_text(errors="ignore").splitlines():
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def summarize(path: Path, width: int = 160) -> list[str]:
    out: list[str] = []
    for e in events(path):
        kind = e.get("type")
        if kind == "tool_call" and e.get("subtype") == "started":
            call = e.get("tool_call", {})
            for name, body in call.items():
                if not isinstance(body, dict):
                    continue
                args = body.get("args", {})
                text = args.get("command") or args.get("path") or json.dumps(args)[:width]
                out.append(f"[{name.replace('ToolCall', '')}] {str(text)[:width]}")
        elif kind == "assistant":
            for c in e.get("message", {}).get("content", []):
                if c.get("type") == "text" and c.get("text", "").strip():
                    out.append("  > " + c["text"].strip().replace("\n", " ")[:width])
        elif kind == "result":
            out.append(f"RESULT ({e.get('duration_ms', 0) / 1000:.0f}s): "
                       + str(e.get("result", "")).replace("\n", " ")[:width])
    return out


if __name__ == "__main__":
    lines = summarize(Path(sys.argv[1]))
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    print("\n".join(lines[-n:]))
