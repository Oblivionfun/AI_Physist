"""The learner-facing lab interface. Scripted learners use LocalLab in-process; LLM learners
reach the same methods through the `lab` CLI over a unix socket."""

from __future__ import annotations

from typing import Protocol

from mlab.referee.session import LearnerSession


class LabAPI(Protocol):
    def card(self) -> dict: ...
    def status(self) -> dict: ...
    def current_goal(self) -> dict: ...
    def answer(self, knobs: dict[str, float]) -> dict: ...
    def experiment(self, knobs: dict[str, float], prediction: list[float]) -> dict: ...
    def probe(self) -> dict: ...
    def probe_result(self, prediction: list[float]) -> dict: ...
    def finish_lab(self) -> dict: ...
    def submit_theory(self, code: str, belief: dict | None) -> dict: ...
    def field_report(self, tickets: list[dict]) -> dict: ...


class LocalLab:
    def __init__(self, session: LearnerSession):
        self._s = session

    def card(self) -> dict:
        return self._s.card.model_dump()

    def status(self) -> dict:
        return self._s.status()

    def current_goal(self) -> dict:
        return self._s.current_goal()

    def answer(self, knobs: dict[str, float]) -> dict:
        return self._s.answer(knobs)

    def experiment(self, knobs: dict[str, float], prediction: list[float]) -> dict:
        return self._s.experiment(knobs, prediction)

    def probe(self) -> dict:
        return self._s.probe()

    def probe_result(self, prediction: list[float]) -> dict:
        return self._s.probe_result(prediction)

    def finish_lab(self) -> dict:
        return self._s.finish_lab()

    def submit_theory(self, code: str, belief: dict | None) -> dict:
        return self._s.submit_theory(code, belief)

    def field_report(self, tickets: list[dict]) -> dict:
        return self._s.field_report(tickets)
