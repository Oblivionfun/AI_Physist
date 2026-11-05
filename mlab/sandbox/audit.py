"""Canary tokens: planted in referee/builder-private files; must never appear learner-side."""

from __future__ import annotations

import secrets
from pathlib import Path

TEXT_SUFFIXES = {".py", ".md", ".json", ".jsonl", ".txt", ".csv", ".log", ""}


def make_canary(role: str) -> str:
    return f"MLAB-CANARY-{role.upper()}-{secrets.token_hex(8)}"


def scan_tree(roots: list[Path], canaries: list[str], max_bytes: int = 20_000_000) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for root in roots:
        if not root.exists():
            continue
        files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
        for f in files:
            if f.suffix not in TEXT_SUFFIXES or f.stat().st_size > max_bytes:
                continue
            try:
                text = f.read_text(errors="ignore")
            except OSError:
                continue
            for c in canaries:
                if c in text:
                    hits.append((str(f), c))
    return hits
