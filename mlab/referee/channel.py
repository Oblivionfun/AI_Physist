"""Append-only, hash-chained log of every message that crosses an agent boundary."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

CHANNELS = {
    1: "builder->referee",
    2: "referee->learner",
    3: "learner->referee",
    4: "referee->builder",
    5: "builder->learner (via referee)",
}


def _digest(entry: dict) -> str:
    body = json.dumps(entry, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(body.encode()).hexdigest()


class ChannelLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.prev = "0" * 64
        self.seq = 0
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                e = json.loads(line)
                self.prev, self.seq = e["hash"], e["seq"] + 1

    def append(self, channel: int, kind: str, payload) -> dict:
        if channel not in CHANNELS:
            raise ValueError(f"unknown channel {channel}")
        entry = {
            "seq": self.seq,
            "ts": round(time.time(), 3),
            "channel": channel,
            "route": CHANNELS[channel],
            "kind": kind,
            "payload": payload,
            "prev": self.prev,
        }
        entry["hash"] = _digest(entry)
        with self.path.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        self.prev, self.seq = entry["hash"], self.seq + 1
        return entry


def verify(path: Path) -> tuple[bool, int]:
    prev = "0" * 64
    n = 0
    for line in Path(path).read_text().splitlines():
        e = json.loads(line)
        h = e.pop("hash")
        if e["prev"] != prev or _digest(e) != h:
            return False, n
        prev, n = h, n + 1
    return True, n
