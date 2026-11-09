"""One run as seen by the viewer: the event stream plus on-demand re-simulation."""

from __future__ import annotations

import threading
from pathlib import Path

from observatory.bake import Baker
from observatory.events import Event, RunScanner

KINDS = ("lab", "pretest", "exam")


class RunFeed:
    def __init__(self, root: Path, cache_root: Path):
        self.root = Path(root)
        self.run_id = self.root.name
        self.scanner = RunScanner(self.root)
        self.baker = Baker(self.root, Path(cache_root) / self.run_id)
        self.cond = threading.Condition()
        self._knobs: dict[tuple[int, str, str, int], dict] = {}
        self._theory: dict[tuple[int, str], str | None] = {}
        self._final: dict[tuple[int, str], dict] = {}
        self._bake_lock = threading.Lock()

    @property
    def events(self) -> list[Event]:
        return self.scanner.events

    @property
    def ended(self) -> bool:
        return self.scanner.ended

    def poll(self) -> list[Event]:
        with self.cond:
            new = self.scanner.poll()
            for e in new:
                self._index(e)
            if new:
                self.cond.notify_all()
        return new

    def append(self, e: Event) -> None:
        """An event the viewer itself produces (e.g. its token audit), after the run's own."""
        with self.cond:
            e.seq = len(self.scanner.events)
            self.scanner.events.append(e)
            self.cond.notify_all()

    def _index(self, e: Event) -> None:
        if e.round is None or e.label is None:
            return
        key = (e.round, e.label)
        if e.kind == "experiment" and isinstance(e.data.get("knobs"), dict):
            self._knobs[(*key, "lab", int(e.data["index"]))] = e.data["knobs"]
        elif e.kind == "answer" and isinstance(e.data.get("knobs"), dict):
            self._knobs[(*key, e.data["phase"], int(e.data["index"]))] = e.data["knobs"]
        elif e.kind == "theory":
            self._theory[key] = e.data.get("code")
        elif e.kind == "session_final":
            self._final[key] = e.data
            self._theory[key] = e.data.get("theory_code")
            for a in e.data.get("attempts", []):
                self._knobs[(*key, a["phase"], int(a["index"]))] = a["knobs"]

    def knobs(self, r: int, label: str, kind: str, index: int) -> dict | None:
        return self._knobs.get((r, label, kind, index))

    def replay(self, r: int, label: str, kind: str, index: int) -> dict | None:
        knobs = self.knobs(r, label, kind, index)
        if knobs is None:
            return None
        with self._bake_lock:
            return self.baker.replay(r, label, knobs)

    def session_replays(self, r: int, label: str) -> dict[str, dict]:
        keys = sorted(k for k in self._knobs if k[0] == r and k[1] == label)
        out = {}
        for _, _, kind, index in keys:
            rep = self.replay(r, label, kind, index)
            if rep is not None:
                out[f"{kind}:{index}"] = rep
        return out

    def curves(self, r: int, knob: str | None = None) -> dict | None:
        exam = [kn for (rr, _, kind, _), kn in self._knobs.items() if rr == r and kind == "exam"]
        lab = [kn for (rr, _, kind, _), kn in self._knobs.items() if rr == r and kind == "lab"]
        theories = {label: self._theory.get((r, label)) for label in ("A", "B")}
        with self._bake_lock:
            return self.baker.curves(r, exam or lab, theories, knob)

    def curves_signature(self, r: int) -> tuple:
        """Changes whenever the inputs of `curves(r)` change."""
        n_exam = sum(1 for k in self._knobs if k[0] == r and k[2] == "exam")
        n_lab = sum(1 for k in self._knobs if k[0] == r and k[2] == "lab")
        return (
            n_exam,
            0 if n_exam else n_lab // 10,
            tuple(self._theory.get((r, x)) is not None for x in ("A", "B")),
            tuple((r, x) in self._final for x in ("A", "B")),
        )

    def knob_names(self, r: int) -> list[str]:
        sub = self.baker.submission(r)
        return [] if sub is None else [k.name for k in sub.task.knobs]

    def rounds(self) -> list[int]:
        return sorted({e.round for e in self.events if e.kind == "card" and e.round is not None})
