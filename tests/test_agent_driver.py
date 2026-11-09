import time

from mlab.agents import llm
from mlab.agents.backend import AgentResult, infra_error

DNS = "Error: [unavailable] getaddrinfo ENOTFOUND api2.cursor.sh"


def _result(session: str | None, error: str | None = None, code: int = 0) -> AgentResult:
    return AgentResult(code, 1.0, session, "", False, 0, {}, error)


def test_infra_error_needs_a_failed_exit_and_a_transient_marker():
    assert infra_error(1, False, DNS) is not None
    assert infra_error(1, False, "RetriableError: Connection stalled repeatedly") is not None
    assert infra_error(0, False, DNS) is None
    assert infra_error(1, True, DNS) is None
    assert infra_error(1, False, "Traceback: ValueError") is None


def test_a_session_spanning_machine_sleep_is_an_infrastructure_failure():
    assert "slept" in infra_error(0, False, "", slept_s=900.0)
    assert infra_error(0, False, "", slept_s=5.0) is None


def _drive(script: list[AgentResult], done_after: int | None, monkeypatch):
    monkeypatch.setattr(llm, "INFRA_WAITS", (0.0, 0.0, 0.0))
    calls: list[str] = []

    def first(_left):
        calls.append("first")
        return script[len(calls) - 1]

    def follow(text, _session, _left):
        calls.append("reconnect" if text == llm.RECONNECT else "nudge")
        return script[len(calls) - 1]

    def finished():
        return done_after is not None and len(calls) >= done_after

    runs = llm._drive(first, follow, finished, "nudge", 1, time.time() + 3600, lambda _m: None)
    return runs, calls


def test_driver_retries_infrastructure_failures_without_spending_nudges(monkeypatch):
    script = [_result(None, DNS, 1), _result("s1", DNS, 1), _result("s1"), _result("s1")]
    runs, calls = _drive(script, done_after=4, monkeypatch=monkeypatch)
    assert calls == ["first", "first", "reconnect", "nudge"]
    assert llm.invalid_reason(runs, finished=True) is None


def test_session_lost_to_infrastructure_is_invalid_not_a_failure(monkeypatch):
    script = [_result(None, DNS, 1)] * 4
    runs, calls = _drive(script, done_after=None, monkeypatch=monkeypatch)
    assert calls == ["first"] * 4
    assert "ENOTFOUND" in llm.invalid_reason(runs, finished=False)
