"""Read a run directory as one stream of observatory events.

The scanner only reads, so it can follow a live run: the channel log and agent transcripts
are append-only and are tailed by byte offset; everything else appears as write-once files,
except notebooks, which are rewritten and diffed by section.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from mlab.construct.ir import Submission
from mlab.referee.channel import verify
from observatory.scene import device_scene

TAG = re.compile(r"^v(\d+)_([a-z0-9]+)_s(\d+)$")
NOTE_HEADER = re.compile(r"session (v\d+_[a-z0-9]+_s\d+)")
VERDICT = re.compile(
    r"^(?P<code>C[0-9*]\w*)\s+(?P<title>[^:]+):\s+(?P<decision>[A-Z_]+)"
    r"(?: value=(?P<value>-?\d+(?:\.\d+)?(?:e[-+]?\d+)?))?"
    r"(?: threshold=(?P<threshold>-?\d+(?:\.\d+)?(?:e[-+]?\d+)?))?\.?\s*(?P<detail>.*)$"
)
ANSWER = re.compile(r"\./lab answer\s+(?:'([^']*)'|\"((?:[^\"\\]|\\.)*)\"|(\S+))")
TEXT_LIMIT = 700
TOOL_OUT_LIMIT = 400


class Event(BaseModel):
    seq: int = 0
    ts: float
    kind: str
    round: int | None = None
    label: str | None = None
    agent: str | None = None
    truth: bool = False
    data: dict[str, Any] = {}


def parse_verdicts(report: str) -> list[dict]:
    out = []
    for line in report.splitlines():
        m = VERDICT.match(line.strip())
        if not m:
            continue
        out.append(
            {
                "code": m["code"],
                "title": m["title"].strip(),
                "decision": m["decision"].lower(),
                "value": float(m["value"]) if m["value"] else None,
                "threshold": float(m["threshold"]) if m["threshold"] else None,
                "detail": m["detail"].strip(),
            }
        )
    return out


def check_summary(stdout: str) -> dict | None:
    """Outcome of a builder's local `forge check`, or None if the output is not one."""
    lines = [ln for ln in stdout.splitlines() if not ln.startswith("[time]")]
    text = "\n".join(lines)
    if "CONSTRUCTION REJECTED" in text:
        detail = next((ln for ln in lines if ln.startswith("[")), "")
        return {"result": "construction_rejected", "verdicts": [], "detail": detail[:300]}
    if "Traceback (most recent call last)" in text:
        last = next((ln for ln in reversed(lines) if ln.strip()), "")
        return {"result": "error", "verdicts": [], "detail": last.strip()[:300]}
    for head in ("CERTIFIED", "REJECTED"):
        if any(ln.strip() == head for ln in lines):
            return {"result": head.lower(), "verdicts": parse_verdicts(text), "detail": ""}
    return None


def _clip(text: str, limit: int = TEXT_LIMIT) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


@dataclass
class _Tail:
    offset: int = 0
    partial: bytes = b""

    def read_lines(self, path: Path) -> list[str]:
        try:
            size = path.stat().st_size
        except OSError:
            return []
        if size < self.offset:
            self.offset, self.partial = 0, b""
        if size == self.offset:
            return []
        with path.open("rb") as f:
            f.seek(self.offset)
            chunk = f.read(size - self.offset)
        self.offset = size
        data = self.partial + chunk
        lines = data.split(b"\n")
        self.partial = lines.pop()
        return [ln.decode(errors="ignore") for ln in lines if ln.strip()]


@dataclass
class _Transcript:
    agent: str
    session: str
    round: int | None
    label: str | None
    workspace: str | None
    tail: _Tail = field(default_factory=_Tail)
    thought: list[str] = field(default_factory=list)
    started: dict[str, dict] = field(default_factory=dict)
    answers: int = 0
    ended: float | None = None
    last_ts: float = 0.0


class RunScanner:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.run_id = self.root.name
        self.events: list[Event] = []
        self._seen: set[Path] = set()
        self._mtimes: dict[Path, float] = {}
        self._channel = _Tail()
        self._transcripts: dict[Path, _Transcript] = {}
        self._certified_rounds: list[int] = []
        self._version_round: dict[int, int] = {}
        self._pretest_goals: dict[int, int] = {}
        self._notes: dict[tuple[str, str], str] = {}
        self._exp_seen: set[tuple[int, str, int]] = set()
        self._summaries = 0
        self._ended = False

    @property
    def ended(self) -> bool:
        return self._ended

    def poll(self) -> list[Event]:
        new: list[Event] = []
        if not self.events:
            new += self._start()
        new += self._write_once("referee/submissions", self._submission)
        new += self._write_once("referee/certificates", self._certificate)
        new += self._write_once("referee/instances", self._instances)
        new += self._write_once("public/cards", self._card, key=_version_key)
        new += self._channel_events()
        new += self._transcript_events()
        new += self._experiments()
        new += self._write_once("referee/sessions", self._session_final)
        new += self._notebooks()
        if not self._ended:
            new += self._summary()
        new.sort(key=lambda e: e.ts)
        for e in new:
            e.seq = len(self.events)
            self.events.append(e)
        return new

    def scan_all(self) -> list[Event]:
        self.poll()
        return self.events

    def round_of_version(self, version: int) -> int | None:
        return self._version_round.get(version)

    # sources

    def _start(self) -> list[Event]:
        secrets = self.root / "referee" / "secrets.json"
        if not secrets.exists():
            return []
        ts = secrets.stat().st_mtime
        out = [Event(ts=ts, kind="run", data={"run_id": self.run_id})]
        world = (_read_json(secrets) or {}).get("world")
        if world:
            out.append(Event(ts=ts, kind="world", truth=True, data={"theta": world}))
        return out

    def _write_once(self, rel: str, handler, key=None) -> list[Event]:
        folder = self.root / rel
        if not folder.is_dir():
            return []
        out: list[Event] = []
        for path in sorted(folder.glob("*.json"), key=key or (lambda p: p.name)):
            if path in self._seen:
                continue
            data = _read_json(path)
            if data is None:
                continue
            self._seen.add(path)
            out += handler(path, data)
        return out

    def _channel_events(self) -> list[Event]:
        path = self.root / "public" / "channel.jsonl"
        out = []
        for line in self._channel.read_lines(path):
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = e.get("payload") or {}
            r = payload.get("round") if isinstance(payload, dict) else None
            summary = (
                {k: v for k, v in payload.items() if k != "report"}
                if isinstance(payload, dict)
                else {}
            )
            if e["kind"] == "round_report":
                summary = {"round": r, "version": payload.get("device_version")}
            out.append(
                Event(
                    ts=e["ts"],
                    kind="channel",
                    round=r,
                    data={
                        "seq": e["seq"],
                        "route": e["route"],
                        "channel": e["channel"],
                        "kind": e["kind"],
                        "hash": e["hash"],
                        "prev": e["prev"],
                        "summary": summary,
                    },
                )
            )
            if e["kind"] == "round_report":
                out.append(Event(ts=e["ts"], kind="report", round=r, data={"report": payload}))
            elif e["kind"] == "session_summary":
                # Every certified round runs exactly two sessions (A, then B), in order.
                i = self._summaries // 2
                self._summaries += 1
                rr = self._certified_rounds[i] if i < len(self._certified_rounds) else None
                out.append(
                    Event(
                        ts=e["ts"],
                        kind="session_end",
                        round=rr,
                        label=payload.get("instance"),
                        data=payload,
                    )
                )
        return out

    def _submission(self, path: Path, data: dict) -> list[Event]:
        r, attempt = _round_attempt(path.stem)
        try:
            sub = Submission.model_validate(data)
        except ValueError:
            return []
        return [
            Event(
                ts=path.stat().st_mtime,
                kind="submission",
                round=r,
                agent="builder",
                data={"attempt": attempt, "device": sub.device.name, "scene": device_scene(sub)},
            )
        ]

    def _certificate(self, path: Path, data: dict) -> list[Event]:
        r, attempt = _round_attempt(path.stem)
        report = data.get("report", "")
        passed = report.startswith("CERTIFIED")
        if passed:
            self._certified_rounds.append(r)
        stats = {
            k: v
            for k, v in (data.get("stats") or {}).items()
            if isinstance(v, (int, float, str, list, dict))
        }
        return [
            Event(
                ts=path.stat().st_mtime,
                kind="certificate",
                round=r,
                data={
                    "attempt": attempt,
                    "passed": passed,
                    "verdicts": parse_verdicts(report),
                    "seconds": data.get("seconds"),
                    "stats": stats,
                },
            )
        ]

    def _instances(self, path: Path, data: dict) -> list[Event]:
        r = int(path.stem.lstrip("r"))
        return [Event(ts=path.stat().st_mtime, kind="instances", round=r, truth=True, data=data)]

    def _card(self, path: Path, data: dict) -> list[Event]:
        version = int(data.get("version", path.stem.lstrip("v")))
        assigned = set(self._version_round.values())
        r = next((x for x in self._certified_rounds if x not in assigned), None)
        if r is None:
            self._seen.discard(path)
            return []
        self._version_round[version] = r
        self._pretest_goals[version] = int((data.get("protocol") or {}).get("pretest_goals", 3))
        return [Event(ts=path.stat().st_mtime, kind="card", round=r, data={"card": data})]

    def _transcript_events(self) -> list[Event]:
        folder = self.root / "referee" / "transcripts"
        if not folder.is_dir():
            return []
        out = []
        for path in sorted(folder.glob("*.jsonl")):
            state = self._transcripts.get(path) or self._open_transcript(path)
            if state is None:
                continue
            for line in state.tail.read_lines(path):
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                out += self._transcript_line(state, e)
        return out

    def _open_transcript(self, path: Path) -> _Transcript | None:
        stem = path.stem
        if stem.startswith("builder_call"):
            call = stem.removeprefix("builder_")
            inbox = next((self.root / "builder" / "inbox").glob(f"round*_{call}.md"), None)
            r = int(inbox.name[5:7]) if inbox else None
            state = _Transcript("builder", call, r, None, None)
        elif stem.startswith("learner_"):
            tag = stem.removeprefix("learner_")
            m = TAG.match(tag)
            if not m:
                return None
            r = self._version_round.get(int(m[1]))
            if r is None:
                return None
            ws = m[2]
            state = _Transcript("learner", tag, r, "A" if ws == "main" else "B", ws)
        else:
            return None
        self._transcripts[path] = state
        return state

    def _base(self, state: _Transcript, e: dict, kind: str, **data) -> Event:
        ms = e.get("timestamp_ms")
        if ms:
            state.last_ts = max(state.last_ts, ms / 1000)
        return Event(
            ts=ms / 1000 if ms else state.last_ts,
            kind=kind,
            round=state.round,
            label=state.label,
            agent=state.agent,
            data={"session": state.session, **data},
        )

    def _transcript_line(self, state: _Transcript, e: dict) -> list[Event]:
        kind, sub = e.get("type"), e.get("subtype")
        if kind == "system" and sub == "init":
            if not state.last_ts:
                state.last_ts = _created(
                    self.root / "referee" / "transcripts" / f"{state.agent}_{state.session}.jsonl"
                )
            return [self._base(state, e, "agent_start", model=e.get("model"))]
        if kind == "thinking" and sub == "delta":
            state.thought.append(e.get("text") or "")
            return []
        if kind == "thinking" and sub == "completed":
            text, state.thought = "".join(state.thought), []
            return [self._base(state, e, "thought", text=_clip(text))] if text.strip() else []
        if kind == "assistant":
            parts = (e.get("message") or {}).get("content") or []
            text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
            return [self._base(state, e, "say", text=_clip(text, 1600))] if text.strip() else []
        if kind == "tool_call" and sub == "started":
            state.started[e.get("call_id", "")] = e
            return []
        if kind == "tool_call" and sub == "completed":
            return self._tool(state, e)
        if kind == "result":
            ev = self._base(
                state,
                e,
                "agent_end",
                ok=not e.get("is_error"),
                seconds=(e.get("duration_ms") or 0) / 1000,
            )
            state.ended = ev.ts
            return [ev]
        return []

    def _tool(self, state: _Transcript, e: dict) -> list[Event]:
        tc = e.get("tool_call") or {}
        if not tc:
            return []
        name = next(iter(tc))
        body = tc[name] or {}
        args = body.get("args") or {}
        result = body.get("result") or {}
        ok_part = result.get("success")
        res = ok_part or result.get("failure") or {}
        stdout = (res.get("stdout") or "") if isinstance(res, dict) else ""
        command = args.get("command") or args.get("path") or args.get("pattern") or ""
        tool = name.removesuffix("ToolCall")
        # Experiment output duplicates the experiment event, which carries the full data.
        shown = "" if re.search(r"\./lab (exp|probe-result)\b", str(command)) else stdout
        out = [
            self._base(
                state,
                e,
                "tool",
                tool=tool,
                command=_clip(str(command), 240),
                ok=ok_part is not None and res.get("exitCode", 0) in (0, None),
                output=_clip(shown, TOOL_OUT_LIMIT),
            )
        ]
        if state.agent == "builder" and tool == "shell" and "forge" in command:
            check = check_summary(stdout)
            if check is not None and "check" in command:
                out.append(self._base(state, e, "check", **check))
        if state.agent == "learner" and tool == "shell" and "./lab" in command:
            out += self._lab_command(state, e, command, stdout)
        return out

    def _lab_command(self, state: _Transcript, e: dict, command: str, stdout: str) -> list[Event]:
        out = []
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("{") and '"goal"' in line:
                g = _loads(line)
                if isinstance(g, dict) and "goal" in g:
                    out.append(
                        self._base(
                            state,
                            e,
                            "goal",
                            phase=g.get("phase"),
                            index=g.get("index"),
                            goal=g.get("goal"),
                        )
                    )
        recorded = stdout.count('"recorded": true')
        if recorded:
            version = int(TAG.match(state.session)[1])
            n_pre = self._pretest_goals.get(version, 3)
            for m in list(ANSWER.finditer(command))[:recorded]:
                raw = m[1] or (m[2].encode().decode("unicode_escape") if m[2] else m[3])
                knobs = _loads(raw) if raw else None
                if not isinstance(knobs, dict) and raw and state.workspace:
                    knobs = _read_json(self.root / "learner" / state.workspace / raw)
                i = state.answers
                phase, index = ("pretest", i) if i < n_pre else ("exam", i - n_pre)
                state.answers += 1
                out.append(
                    self._base(
                        state,
                        e,
                        "answer",
                        phase=phase,
                        index=index,
                        knobs=knobs if isinstance(knobs, dict) else None,
                    )
                )
        if "submit-theory" in command and '"next_phase": "exam"' in stdout:
            out.append(self._theory(state, e, command))
        return out

    def _theory(self, state: _Transcript, e: dict, command: str) -> Event:
        final = self.root / "referee" / "sessions" / f"r{state.round}_{state.label}.json"
        if final.exists():
            data = _read_json(final) or {}
            return self._base(
                state,
                e,
                "theory",
                code=data.get("theory_code"),
                belief=data.get("belief"),
                source="referee",
            )
        ws = self.root / "learner" / (state.workspace or "")
        m = re.search(r"submit-theory\s+(\S+)(?:\s+--belief\s+(\S+))?", command)
        code_path = ws / (m[1] if m else "predict.py")
        belief_path = ws / m[2] if m and m[2] else None
        code = code_path.read_text() if code_path.is_file() else None
        belief = _read_json(belief_path) if belief_path else None
        return self._base(state, e, "theory", code=code, belief=belief, source="workspace")

    def _experiments(self) -> list[Event]:
        base = self.root / "learner"
        if not base.is_dir():
            return []
        out = []
        for ws_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            data_dir = ws_dir / "data"
            if not data_dir.is_dir():
                continue
            for sess in sorted(p for p in data_dir.iterdir() if p.is_dir()):
                m = TAG.match(sess.name)
                if not m or m[2] != ws_dir.name:
                    continue
                r = self._version_round.get(int(m[1]))
                if r is None:
                    continue
                label = "A" if ws_dir.name == "main" else "B"
                for path in sorted(sess.glob("exp_*.json")):
                    if path in self._seen:
                        continue
                    obs = _read_json(path)
                    if obs is None:
                        continue
                    self._seen.add(path)
                    self._exp_seen.add((r, label, int(obs["index"])))
                    out.append(
                        Event(
                            ts=path.stat().st_mtime,
                            kind="experiment",
                            round=r,
                            label=label,
                            agent="learner",
                            data={"session": sess.name, **obs},
                        )
                    )
                res = sess / "results.json"
                if res.exists() and res not in self._seen:
                    data = _read_json(res)
                    if data is not None:
                        self._seen.add(res)
                        out.append(
                            Event(
                                ts=res.stat().st_mtime,
                                kind="results",
                                round=r,
                                label=label,
                                agent="learner",
                                data={"session": sess.name, **data},
                            )
                        )
        return out

    def _session_final(self, path: Path, data: dict) -> list[Event]:
        r_text, label = path.stem.split("_")
        r = int(r_text.lstrip("r"))
        ts = path.stat().st_mtime
        out = [Event(ts=ts, kind="session_final", round=r, label=label, truth=True, data=data)]
        for x in data.get("lab", []):
            if (r, label, int(x["index"])) in self._exp_seen:
                continue
            self._exp_seen.add((r, label, int(x["index"])))
            out.append(
                Event(
                    ts=ts,
                    kind="experiment",
                    round=r,
                    label=label,
                    agent="learner",
                    data={
                        "index": x["index"],
                        "probe": x["probe"],
                        "knobs": x["knobs"],
                        "prediction": x["prediction"],
                        "outcome": x["observed_outcome"],
                        "status": x["status"],
                        "times": [],
                        "traces": {},
                        "synthetic": True,
                    },
                )
            )
        return out

    def _notebooks(self) -> list[Event]:
        base = self.root / "learner"
        if not base.is_dir():
            return []
        out = []
        ends = {s.session: s.ended for s in self._transcripts.values() if s.agent == "learner"}
        for ws_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            path = ws_dir / "notebook.md"
            if not path.exists():
                continue
            mtime = path.stat().st_mtime
            if self._mtimes.get(path) == mtime:
                continue
            self._mtimes[path] = mtime
            for tag, text in _note_sections(path.read_text(errors="ignore")):
                m = TAG.match(tag)
                if not m or m[2] != ws_dir.name or self._notes.get((ws_dir.name, tag)) == text:
                    continue
                self._notes[(ws_dir.name, tag)] = text
                r = self._version_round.get(int(m[1]))
                out.append(
                    Event(
                        ts=ends.get(tag) or mtime,
                        kind="note",
                        round=r,
                        label="A" if ws_dir.name == "main" else "B",
                        agent="learner",
                        data={"session": tag, "workspace": ws_dir.name, "text": text},
                    )
                )
        return out

    def _summary(self) -> list[Event]:
        path = self.root / "referee" / "summary.json"
        data = _read_json(path) if path.exists() else None
        if data is None:
            return []
        self._ended = True
        channel = self.root / "public" / "channel.jsonl"
        ok, n = verify(channel) if channel.exists() else (False, 0)
        keep = ("run_id", "builder", "learner", "profile", "rounds", "isolation_audit")
        return [
            Event(
                ts=path.stat().st_mtime,
                kind="run_end",
                data={**{k: data.get(k) for k in keep}, "chain_ok": ok, "chain_entries": n},
            )
        ]


def _round_attempt(stem: str) -> tuple[int, int]:
    r, a = stem.split("_")
    return int(r.lstrip("r")), int(a.lstrip("a"))


def _version_key(path: Path) -> int:
    try:
        return int(path.stem.lstrip("v"))
    except ValueError:
        return 0


def _loads(text: str) -> Any | None:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def _note_sections(text: str) -> list[tuple[str, str]]:
    """Notebook sections headed '## <date> — <device>, session <tag>'."""
    out = []
    for block in re.split(r"(?m)^## ", text)[1:]:
        header, _, body = block.partition("\n")
        m = NOTE_HEADER.search(header)
        if m:
            out.append((m[1], f"## {header}\n{body}".strip()))
    return out


def _created(path: Path) -> float:
    try:
        st = path.stat()
    except OSError:
        return 0.0
    return float(getattr(st, "st_birthtime", st.st_mtime))
