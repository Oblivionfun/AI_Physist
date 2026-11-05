"""Frozen prompts. Any change must be recorded in docs/decisions.md and hashes.json updated
(AGENTS.md red line 4); tests/test_prompts.py enforces the hashes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = ("learner", "builder")


def load(name: str) -> str:
    return (HERE / f"{name}.md").read_text()


def digest(name: str) -> str:
    return hashlib.sha256(load(name).encode()).hexdigest()


def recorded() -> dict[str, str]:
    return json.loads((HERE / "hashes.json").read_text())
