"""Model adapters.

A model is an interchangeable component behind three methods, nothing more.
That boundary is the whole point: the runtime is testable without a network
call, and swapping providers is a config change rather than a rewrite.

The lesson rule: **never** let a model's raw text reach an executor. It becomes
an `Action`, which policy checks, which the loop validates.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Protocol, Sequence, runtime_checkable

from pydantic import ValidationError

from .models import Action, Goal, Observation
from .tooling import ToolRegistry


@runtime_checkable
class ModelAdapter(Protocol):
    """Anything that can turn context into a proposed action."""

    name: str

    def propose(
        self,
        goal: Goal,
        observations: Sequence[Observation],
        tools: Sequence[dict[str, Any]],
    ) -> Action: ...

    def verify(
        self,
        goal: Goal,
        observations: Sequence[Observation],
    ) -> bool: ...


def _render_context(goal: Goal, observations: Sequence[Observation]) -> str:
    lines = [f"GOAL: {goal.objective}"]
    if goal.success_criteria:
        lines.append("SUCCESS CRITERIA: " + "; ".join(goal.success_criteria))
    if observations:
        lines.append("OBSERVED SO FAR:")
        lines += [f"  {o.summary()}" for o in observations]
    else:
        lines.append("OBSERVED SO FAR: (nothing yet)")
    return "\n".join(lines)


class EchoModel:
    """Deterministic adapter. No API key, no network, no randomness."""

    name = "echo"

    def propose(
        self,
        goal: Goal,
        observations: Sequence[Observation],
        tools: Sequence[dict[str, Any]],
    ) -> Action:
        return Action(
            name="finish",
            rationale="EchoModel never acts; it only reports, so the loop can be traced.",
        )

    def verify(self, goal: Goal, observations: Sequence[Observation]) -> bool:
        return False


class ScriptedModel:
    """Replays a fixed list of actions, then verifies.

    This is the adapter that makes the runtime testable and the lessons
    reproducible: an evaluation harness asserts on behaviour, not on prose.
    """

    def __init__(self, script: Iterable[str | dict[str, Any]], verify_after: bool = True) -> None:
        self._script: list[dict[str, Any]] = []
        for item in script:
            self._script.append({"name": item, "arguments": {}} if isinstance(item, str) else dict(item))
        self._cursor = 0
        self._verify_after = verify_after

    @property
    def exhausted(self) -> bool:
        return self._cursor >= len(self._script)

    def propose(
        self,
        goal: Goal,
        observations: Sequence[Observation],
        tools: Sequence[dict[str, Any]],
    ) -> Action:
        if self._cursor >= len(self._script):
            return Action(name="finish", rationale="script exhausted")
        entry = self._script[self._cursor]
        self._cursor += 1
        return Action(
            name=entry["name"],
            arguments=dict(entry.get("arguments", {})),
            rationale=entry.get("rationale", "scripted"),
        )

    def verify(self, goal: Goal, observations: Sequence[Observation]) -> bool:
        if not self._verify_after:
            return False
        if goal.success_criteria:
            return all(o.success for o in observations)
        return bool(observations) and all(o.success for o in observations)


class FirstToolModel:
    """Always proposes one named tool with fixed arguments. Useful in tests."""

    name = "first-tool"

    def __init__(self, tool_name: str, arguments: dict[str, Any] | None = None) -> None:
        self.tool_name = tool_name
        self.arguments = arguments or {}

    def propose(
        self,
        goal: Goal,
        observations: Sequence[Observation],
        tools: Sequence[dict[str, Any]],
    ) -> Action:
        if observations:
            return Action(name="finish", rationale="already acted once")
        return Action(name=self.tool_name, arguments=dict(self.arguments))

    def verify(self, goal: Goal, observations: Sequence[Observation]) -> bool:
        return bool(observations) and observations[-1].success


class TranscriptModel:
    """Base class for adapters that talk to a real provider.

    Subclasses implement `call(prompt) -> str` and are responsible for auth.
    The base class owns prompt assembly and JSON decoding, so a provider
    adapter stays under twenty lines.
    """

    name = "transcript"

    def build_prompt(
        self,
        goal: Goal,
        observations: Sequence[Observation],
        tools: Sequence[dict[str, Any]],
    ) -> str:
        tool_lines = "\n".join(
            f"- {t['name']}(risk={t['risk']}): {t['description']} {json.dumps(t['parameters'])}"
            for t in tools
        )
        return (
            f"{_render_context(goal, observations)}\n\n"
            f"AVAILABLE TOOLS:\n{tool_lines or '- none'}\n\n"
            'Reply with JSON only: {"name": "<tool|finish>", "arguments": {}, "rationale": ""}'
        )

    def call(self, prompt: str) -> str:  # pragma: no cover - needs a provider
        raise NotImplementedError("subclasses implement call()")

    def propose(
        self,
        goal: Goal,
        observations: Sequence[Observation],
        tools: Sequence[dict[str, Any]],
    ) -> Action:
        raw = self.call(self.build_prompt(goal, observations, tools))
        return parse_action(raw)

    def verify(self, goal: Goal, observations: Sequence[Observation]) -> bool:
        prompt = (
            f"{_render_context(goal, observations)}\n\n"
            'Did the goal succeed? Reply with JSON only: {"met": true|false}'
        )
        raw = self.call(prompt)
        try:
            return bool(json.loads(raw).get("met"))
        except (ValueError, AttributeError):
            return False


def parse_action(raw: str) -> Action:
    """Turn provider text into an `Action`, or a safe `finish` if it is unusable.

    Never raises. A malformed model reply must not be able to stop the run.
    """
    try:
        return Action.model_validate(json.loads(raw))
    except (ValueError, ValidationError, TypeError):
        return Action(name="finish", rationale=f"unparseable model reply: {raw[:80]}")


def tools_for_prompt(registry: ToolRegistry) -> list[dict[str, Any]]:
    """Convenience for lessons that want the provider-facing tool list."""
    return registry.describe()