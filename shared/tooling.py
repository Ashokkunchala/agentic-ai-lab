"""Tool registry: the only path from intent to effect.

Design rules, each of which exists because its absence caused a real failure
mode in systems like this:

* A tool is a *name plus a schema plus a declared risk*. Anything that reaches
  `handler` has already been validated.
* Registration is duplicate-rejecting. Last-write-wins registries hide shadowing
  bugs until someone debugs the wrong tool.
* Exceptions from a handler become `ToolResult(success=False)`. The loop needs
  to *observe* a failure and decide what to do; it should not unwind.
* `describe()` emits provider-ready schemas so a model never guesses argument
  names.

Tools are declared explicitly rather than via a decorator. A decorator that
infers a schema from a signature is clever, and clever is the enemy here: you
cannot read the contract off the page.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from .policy import Risk


@dataclass(frozen=True)
class ToolResult:
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0


class ToolNotFound(KeyError):
    """Raised for an unknown tool name. The loop converts this into an observation."""


class DuplicateTool(ValueError):
    """Raised when a second tool tries to claim an existing name."""


class EmptyInput(BaseModel):
    """Schema for tools that take no arguments."""


@dataclass
class Tool:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[..., Any]
    risk: Risk = Risk.READ

    def run(self, arguments: dict[str, Any]) -> ToolResult:
        started = time.perf_counter()
        try:
            validated = self.input_model.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult(
                success=False,
                error=f"invalid arguments for {self.name}: {_first_problem(exc)}",
                duration_ms=(time.perf_counter() - started) * 1000,
            )
        try:
            output = self.handler(**validated.model_dump())
        except Exception as exc:  # noqa: BLE001 - a tool must not crash the loop
            return ToolResult(
                success=False,
                error=f"{type(exc).__name__}: {exc}",
                duration_ms=(time.perf_counter() - started) * 1000,
            )
        return ToolResult(
            success=True,
            output=output,
            duration_ms=(time.perf_counter() - started) * 1000,
        )

    def schema(self) -> dict[str, Any]:
        return self.input_model.model_json_schema()

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "risk": self.risk.value,
            "parameters": self.schema(),
        }


def _first_problem(exc: ValidationError) -> str:
    problems = exc.errors()
    if not problems:
        return "unknown validation error"
    first = problems[0]
    location = ".".join(str(part) for part in first.get("loc", ())) or "<root>"
    return f"{location}: {first.get('msg', 'invalid')}"


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        if tool.name in self._tools:
            raise DuplicateTool(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool
        return tool

    def register_all(self, tools: list[Tool]) -> ToolRegistry:
        """Register many tools at once. Returns self so calls can be chained."""
        for item in tools:
            self.register(item)
        return self

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFound(f"unknown tool: {name}") from exc

    def find(self, name: str) -> Tool | None:
        """Non-raising lookup, for callers that treat absence as a normal outcome."""
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def describe(self) -> list[dict[str, Any]]:
        return [self._tools[name].describe() for name in self.names()]

    def by_risk(self, risk: Risk) -> list[Tool]:
        return [self._tools[name] for name in self.names() if self._tools[name].risk is risk]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: object) -> bool:
        return name in self._tools