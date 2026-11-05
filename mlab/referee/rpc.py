"""Unix-socket JSON RPC exposing one LearnerSession to the sandboxed learner.

One JSON request per connection: {"token", "method", "args"}. The token is a capability for
exactly the learner methods below; error messages are sanitized (no tracebacks, no paths).
"""

from __future__ import annotations

import json
import secrets
import socketserver
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from mlab.referee.session import ProtocolError

LEARNER_METHODS = {
    "card": (),
    "status": (),
    "current_goal": (),
    "answer": ("knobs",),
    "experiment": ("knobs", "prediction"),
    "probe": (),
    "probe_result": ("prediction",),
    "finish_lab": (),
    "submit_theory": ("code", "belief"),
    "field_report": ("tickets",),
}
MAX_REQUEST = 1_000_000


class _Server(socketserver.UnixStreamServer):
    allow_reuse_address = True


class LabServer:
    def __init__(self, lab, token: str | None = None, on_call: Callable[[str, dict, bool], None] | None = None):
        self.lab = lab
        self.token = token or secrets.token_hex(16)
        self.on_call = on_call
        self.dir = Path(tempfile.mkdtemp(prefix="mlab-", dir="/private/tmp"))
        self.dir.chmod(0o700)
        self.socket_path = self.dir / "lab.sock"
        self._lock = threading.Lock()
        self._server: _Server | None = None
        self._thread: threading.Thread | None = None

    def handle(self, raw: bytes) -> dict:
        try:
            req = json.loads(raw.decode())
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"ok": False, "error": "request must be one JSON object"}
        if not isinstance(req, dict) or not secrets.compare_digest(str(req.get("token", "")), self.token):
            return {"ok": False, "error": "invalid token"}
        method = req.get("method")
        if method not in LEARNER_METHODS:
            return {"ok": False, "error": f"unknown method; available: {sorted(LEARNER_METHODS)}"}
        args = req.get("args") or {}
        if not isinstance(args, dict) or set(args) - set(LEARNER_METHODS[method]):
            return {"ok": False, "error": f"{method} accepts arguments {list(LEARNER_METHODS[method])}"}
        with self._lock:
            try:
                result = getattr(self.lab, method)(**args)
                ok, reply = True, {"ok": True, "result": result}
            except ProtocolError as exc:
                ok, reply = False, {"ok": False, "error": str(exc)}
            except (TypeError, ValueError, ValidationError) as exc:
                ok, reply = False, {"ok": False, "error": f"invalid arguments: {str(exc).splitlines()[0][:200]}"}
        if self.on_call:
            self.on_call(method, args, ok)
        return reply

    def start(self) -> None:
        outer = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self) -> None:
                raw = self.rfile.readline(MAX_REQUEST)
                reply = outer.handle(raw)
                self.wfile.write((json.dumps(reply, default=str) + "\n").encode())

        self._server = _Server(str(self.socket_path), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        self.socket_path.unlink(missing_ok=True)
        try:
            self.dir.rmdir()
        except OSError:
            pass

    def client_config(self, session_tag: str) -> dict:
        return {"socket": str(self.socket_path), "token": self.token, "session": session_tag}
