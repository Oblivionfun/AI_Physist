"""Local live viewer: token-gated HTTP and server-sent events on 127.0.0.1.

Both agents may use the network (their CLIs call model APIs), so whatever this server listens
on is reachable from inside their sandboxes. Every data request must therefore carry a token
that exists only in this process, in the user's terminal, and in a file under the runs
directory, which both sandboxes deny (D-023).
"""

from __future__ import annotations

import hmac
import json
import mimetypes
import os
import re
import secrets
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from observatory.events import Event
from observatory.feed import KINDS, RunFeed

RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
POLL_S = 1.0
HEARTBEAT_S = 15.0
LIVE_WINDOW_S = 15 * 60


def scan_for_tokens(roots: list[Path], tokens: list[str]) -> list[str]:
    hits = []
    for root in roots:
        files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
        for path in files:
            if path.suffix in (".pyc",) or ".venv" in path.parts:
                continue
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            if any(t in text for t in tokens):
                hits.append(str(path))
    return hits


class Observatory:
    def __init__(self, runs_dir: Path, recorded_dir: Path, web_dist: Path, token: str):
        self.runs_dir = Path(runs_dir)
        self.cache_root = self.runs_dir / "_viz"
        self.recorded_dir = Path(recorded_dir)
        self.web_dist = Path(web_dist)
        self.token = token
        self.feeds: dict[str, RunFeed] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=1)
        self._jobs: dict[tuple, Future] = {}
        self._audited: set[str] = set()

    def run_dir(self, run_id: str) -> Path | None:
        if not RUN_ID.match(run_id) or run_id.startswith("_"):
            return None
        path = self.runs_dir / run_id
        return path if (path / "referee").is_dir() else None

    def feed(self, run_id: str) -> RunFeed | None:
        with self._lock:
            if run_id in self.feeds:
                return self.feeds[run_id]
            root = self.run_dir(run_id)
            if root is None:
                return None
            feed = RunFeed(root, self.cache_root)
            feed.poll()
            self.feeds[run_id] = feed
        self._maybe_audit(feed)
        return feed

    def runs(self) -> list[dict]:
        out = []
        if not self.runs_dir.is_dir():
            return out
        now = time.time()
        for path in sorted(self.runs_dir.iterdir()):
            if not path.is_dir() or path.name.startswith("_") or not (path / "referee").is_dir():
                continue
            ended = (path / "referee" / "summary.json").exists()
            recent = _latest_mtime(path)
            out.append(
                {
                    "run_id": path.name,
                    "ended": ended,
                    "last_activity": recent,
                    "live": not ended and now - recent < LIVE_WINDOW_S,
                }
            )
        return out

    def poll_loop(self, stop: threading.Event) -> None:
        while not stop.wait(POLL_S):
            for feed in list(self.feeds.values()):
                if feed.ended:
                    continue
                try:
                    feed.poll()
                except Exception as exc:  # noqa: BLE001 - one bad file must not stop the stream
                    print(f"[observatory] poll {feed.run_id}: {exc}", flush=True)
                self._maybe_audit(feed)

    def _maybe_audit(self, feed: RunFeed) -> None:
        """After a run ends, no viewer token may appear on either agent's side."""
        if not feed.ended or feed.run_id in self._audited:
            return
        self._audited.add(feed.run_id)
        tokens = issued_tokens(self.cache_root)
        root = feed.root
        transcripts = root / "referee" / "transcripts"
        sides = [
            root / "builder",
            root / "learner",
            *transcripts.glob("builder_*.jsonl"),
            *transcripts.glob("learner_*.jsonl"),
        ]
        hits = scan_for_tokens([p for p in sides if p.exists()], tokens)
        feed.append(
            Event(
                ts=time.time(),
                kind="audit",
                data={"viewer_tokens": len(tokens), "hits": hits, "clean": not hits},
            )
        )

    def curves(self, feed: RunFeed, r: int, knob: str | None) -> dict | None:
        """Curves take seconds to compute; the first request starts the job and returns None."""
        key = (feed.run_id, r, knob, feed.curves_signature(r))
        job = self._jobs.get(key)
        if job is None:
            job = self._jobs[key] = self._pool.submit(feed.curves, r, knob)
        return job.result() if job.done() else None


def issued_tokens(cache_root: Path) -> list[str]:
    path = cache_root / "tokens.jsonl"
    if not path.exists():
        return []
    return [json.loads(ln)["token"] for ln in path.read_text().splitlines() if ln.strip()]


def record_token(cache_root: Path, token: str, port: int) -> Path:
    cache_root.mkdir(parents=True, exist_ok=True)
    os.chmod(cache_root, 0o700)
    history = cache_root / "tokens.jsonl"
    with history.open("a") as f:
        f.write(json.dumps({"token": token, "port": port, "issued": time.time()}) + "\n")
    os.chmod(history, 0o600)
    current = cache_root / "server.json"
    current.write_text(json.dumps({"port": port, "pid": os.getpid(), "token": token}))
    os.chmod(current, 0o600)
    return current


def _latest_mtime(root: Path) -> float:
    candidates = [root / "public" / "channel.jsonl", root / "referee" / "transcripts"]
    transcripts = root / "referee" / "transcripts"
    if transcripts.is_dir():
        candidates += list(transcripts.glob("*.jsonl"))
    times = [p.stat().st_mtime for p in candidates if p.exists()]
    return max(times, default=root.stat().st_mtime)


def make_handler(obs: Observatory, port_box: list[int]):
    class Handler(BaseHTTPRequestHandler):
        server_version = "observatory"

        def log_message(self, fmt, *args) -> None:
            return

        def _send(
            self, code: int, body: bytes, ctype: str = "application/json", extra: dict | None = None
        ) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code: int = 200) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode())

        def _host_ok(self) -> bool:
            # Rejects DNS-rebinding pages that resolve their own name to 127.0.0.1.
            host = self.headers.get("Host", "")
            port = port_box[0]
            return host in (f"127.0.0.1:{port}", f"localhost:{port}")

        def _token_ok(self, query: dict) -> bool:
            given = self.headers.get("X-Observatory-Token") or (query.get("token") or [""])[0]
            return hmac.compare_digest(given.encode(), obs.token.encode())

        def do_GET(self) -> None:
            if not self._host_ok():
                self._send(421, b'{"error": "unexpected Host header"}')
                return
            url = urlparse(self.path)
            query = parse_qs(url.query)
            parts = [p for p in url.path.split("/") if p]
            if parts[:1] in (["api"], ["recorded"]):
                if not self._token_ok(query):
                    self._send(401, b'{"error": "missing or wrong observatory token"}')
                    return
                try:
                    if parts[0] == "api":
                        self._api(parts[1:], query)
                    else:
                        self._file(obs.recorded_dir, parts[1:], ctype_default="application/json")
                except BrokenPipeError:
                    pass
                except (KeyError, ValueError) as exc:
                    self._json({"error": f"bad request: {exc}"}, 400)
                return
            self._file(obs.web_dist, parts, spa=True)

        def _api(self, parts: list[str], query: dict) -> None:
            if parts == ["runs"]:
                self._json({"runs": obs.runs()})
                return
            if len(parts) < 3 or parts[0] != "runs":
                self._json({"error": "not found"}, 404)
                return
            feed = obs.feed(parts[1])
            if feed is None:
                self._json({"error": f"no run '{parts[1]}'"}, 404)
                return
            action = parts[2]
            q = {k: v[0] for k, v in query.items()}
            if action == "events":
                after = int(q.get("after", -1))
                self._json(
                    {
                        "events": [e.model_dump() for e in feed.events[after + 1 :]],
                        "ended": feed.ended,
                    }
                )
            elif action == "stream":
                self._stream(feed, int(q.get("after", -1)))
            elif action == "replay":
                kind = q.get("kind", "lab")
                if kind not in KINDS:
                    self._json({"error": f"kind must be one of {KINDS}"}, 400)
                    return
                rep = feed.replay(int(q["round"]), q["label"], kind, int(q["index"]))
                self._json(
                    rep if rep is not None else {"error": "unknown action"},
                    200 if rep is not None else 404,
                )
            elif action == "replays":
                self._json(feed.session_replays(int(q["round"]), q["label"]))
            elif action == "curves":
                c = obs.curves(feed, int(q["round"]), q.get("knob"))
                if c is None:
                    self._json({"pending": True}, 202)
                else:
                    self._json(c)
            else:
                self._json({"error": "not found"}, 404)

        def _stream(self, feed: RunFeed, after: int) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            sent = after
            while True:
                with feed.cond:
                    if len(feed.events) - 1 <= sent:
                        feed.cond.wait(timeout=HEARTBEAT_S)
                    batch = feed.events[sent + 1 :]
                if batch:
                    body = json.dumps([e.model_dump() for e in batch], ensure_ascii=False)
                    msg = f"id: {batch[-1].seq}\nevent: batch\ndata: {body}\n\n"
                    sent = batch[-1].seq
                else:
                    msg = ": ping\n\n"
                try:
                    self.wfile.write(msg.encode())
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return

        def _file(
            self,
            base: Path,
            parts: list[str],
            spa: bool = False,
            ctype_default: str = "application/octet-stream",
        ) -> None:
            base = base.resolve()
            target = (base.joinpath(*parts) if parts else base / "index.html").resolve()
            if not target.is_relative_to(base):
                self._send(404, b"not found", "text/plain")
                return
            if not target.is_file():
                if (
                    spa
                    and (base / "index.html").is_file()
                    and "." not in (parts[-1] if parts else "")
                ):
                    target = base / "index.html"
                else:
                    self._send(404, b"not found", "text/plain")
                    return
            ctype = mimetypes.guess_type(target.name)[0] or ctype_default
            self._send(200, target.read_bytes(), ctype)

    return Handler


def serve(runs_dir: Path, recorded_dir: Path, web_dist: Path, port: int = 0) -> None:
    token = secrets.token_urlsafe(32)
    obs = Observatory(runs_dir, recorded_dir, web_dist, token)
    port_box = [port]
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(obs, port_box))
    httpd.daemon_threads = True
    port_box[0] = httpd.server_address[1]
    record_token(obs.cache_root, token, port_box[0])
    stop = threading.Event()
    threading.Thread(target=obs.poll_loop, args=(stop,), daemon=True).start()
    if not (web_dist / "index.html").exists():
        print(
            f"[observatory] front end not built: run `pnpm build` in {web_dist.parent}", flush=True
        )
    print(f"[observatory] open http://127.0.0.1:{port_box[0]}/#token={token}", flush=True)
    print(
        "[observatory] the token is the only access control; do not paste it into an agent session",
        flush=True,
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        httpd.server_close()
