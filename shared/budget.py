"""Budgets: the difference between a demo and a system you can leave running.

Autonomy without limits is an outage. Every limit here is checked *before* the
action that would consume it, so the loop always stops cleanly with a reason
instead of tripping an exception halfway through a write.

`exhausted_reason()` is the single source of truth for "why did we stop".
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


class BudgetExhausted(RuntimeError):
    """Raised only by the charging helpers, never by `exhausted_reason()`."""


@dataclass
class Budget:
    max_steps: int = 8
    max_tool_calls: int = 24
    max_retries_per_tool: int = 2
    max_consecutive_failures: int = 3
    max_seconds: float | None = None
    max_cost_usd: float | None = None
    steps: int = 0
    tool_calls: int = 0
    cost_usd: float = 0.0
    consecutive_failures: int = 0
    retries: dict[str, int] = field(default_factory=dict)
    _started_at: float = field(default_factory=time.monotonic)

    def elapsed(self) -> float:
        return time.monotonic() - self._started_at

    def exhausted_reason(self) -> str | None:
        """Return the first limit that is spent, or None when work may continue."""
        if self.steps >= self.max_steps:
            return f"step budget exhausted ({self.steps}/{self.max_steps})"
        if self.tool_calls >= self.max_tool_calls:
            return f"tool-call budget exhausted ({self.tool_calls}/{self.max_tool_calls})"
        if self.consecutive_failures >= self.max_consecutive_failures:
            return (
                f"stalled: {self.consecutive_failures} consecutive failures "
                f"(limit {self.max_consecutive_failures})"
            )
        if self.max_seconds is not None and self.elapsed() >= self.max_seconds:
            return f"time budget exhausted ({self.elapsed():.2f}s/{self.max_seconds}s)"
        if self.max_cost_usd is not None and self.cost_usd >= self.max_cost_usd:
            return f"cost budget exhausted (${self.cost_usd:.4f}/${self.max_cost_usd})"
        return None

    def record_outcome(self, success: bool) -> None:
        """Track progress so a loop that cannot advance stops early.

        Without this, an agent blocked by policy or by a persistently failing
        tool burns its entire step budget before anyone notices it was stuck.
        This is the difference between "failed after 3 attempts" and "failed
        after 500 identical attempts".
        """
        if success:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1

    def charge_step(self) -> None:
        reason = self.exhausted_reason()
        if reason:
            raise BudgetExhausted(reason)
        self.steps += 1

    def charge_tool_call(self) -> None:
        if self.tool_calls >= self.max_tool_calls:
            raise BudgetExhausted("tool-call budget exhausted")
        self.tool_calls += 1

    def charge_cost(self, usd: float) -> None:
        self.cost_usd = round(self.cost_usd + usd, 6)

    def retry_allowed(self, tool_name: str) -> bool:
        return self.retries.get(tool_name, 0) < self.max_retries_per_tool

    def charge_retry(self, tool_name: str) -> None:
        self.retries[tool_name] = self.retries.get(tool_name, 0) + 1

    def as_dict(self) -> dict[str, object]:
        return {
            "steps": f"{self.steps}/{self.max_steps}",
            "tool_calls": f"{self.tool_calls}/{self.max_tool_calls}",
            "retries": dict(sorted(self.retries.items())),
            "consecutive_failures": f"{self.consecutive_failures}/{self.max_consecutive_failures}",
            "elapsed_seconds": round(self.elapsed(), 3),
            "cost_usd": round(self.cost_usd, 6),
        }