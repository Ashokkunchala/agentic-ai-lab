"""Pydantic schemas shared by the runtime.

Every message that crosses a boundary (model -> runtime, runtime -> tool,
tool -> runtime) is one of these three shapes. That single rule is what makes
an agent auditable: a log line, a trace span and a replayed test all describe
the same three objects.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Goal(BaseModel):
    """What the agent is trying to achieve."""

    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1, description="Natural language outcome.")
    max_steps: int = Field(default=8, ge=1, le=200)
    success_criteria: list[str] = Field(
        default_factory=list,
        description="Concrete checks used to decide the goal actually succeeded.",
    )


class Action(BaseModel):
    """A proposal. The model never executes anything; it emits one of these."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(default="", description="Why this action now. Kept for audit.")


class Observation(BaseModel):
    """The result of an action becoming new state."""

    model_config = ConfigDict(extra="forbid")

    step: int = Field(ge=0)
    action: str
    tool: str | None = None
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = Field(default=0.0, ge=0.0)
    risk: str | None = None
    approved_by: str | None = None

    def summary(self, limit: int = 160) -> str:
        """One-line rendering for logs and prompts. Truncates to keep logs bounded."""
        payload = self.error if not self.success else self.output
        text = "" if payload is None else str(payload).replace("\n", " ")
        if len(text) > limit:
            text = text[: limit - 1] + "…"
        return f"{self.action} -> {'ok' if self.success else 'error'}: {text}"