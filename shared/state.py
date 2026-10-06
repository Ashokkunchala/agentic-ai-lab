"""Agent state and its lifecycle.

Two ideas carry the weight here:

1. `Status` is an enum with declared legal transitions. A runtime that can move
   from COMPLETED back to RUNNING has no lifecycle, it just has a string.
2. `history` is append-only. Anything that would need to edit a past event is a
   design error, because that is the audit trail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable

from .budget import Budget
from .models import Goal, Observation

class Status(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    BUDGET_EXHAUSTED = "budget_exhausted"


TERMINAL_STATUSES = frozenset(
    {Status.COMPLETED, Status.FAILED, Status.BUDGET_EXHAUSTED}
)

ALLOWED_TRANSITIONS: dict[Status, frozenset[Status]] = {
    Status.PENDING: frozenset({Status.RUNNING, Status.FAILED}),
    Status.RUNNING: frozenset(
        {
            Status.WAITING_APPROVAL,
            Status.COMPLETED,
            Status.FAILED,
            Status.BUDGET_EXHAUSTED,
        }
    ),
    Status.WAITING_APPROVAL: frozenset({Status.RUNNING, Status.FAILED}),
    Status.COMPLETED: frozenset(),
    Status.FAILED: frozenset(),
    Status.BUDGET_EXHAUSTED: frozenset(),
}


class IllegalTransition(RuntimeError):
    """Raised when a caller tries to move a run backwards or out of a terminal state."""


@dataclass
class AgentState:
    goal: Goal
    status: Status = Status.PENDING
    step: int = 0
    observations: list[Observation] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    budget: Budget = field(default_factory=Budget)
    history: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str | None = None

    def __post_init__(self) -> None:
        # The goal and the budget must agree. The stricter of the two wins, so a
        # generous goal cannot widen a budget the caller already set.
        self.budget.max_steps = min(self.budget.max_steps, self.goal.max_steps)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def transition(self, target: Status, reason: str = "") -> None:
        if target not in ALLOWED_TRANSITIONS[self.status]:
            raise IllegalTransition(f"{self.status.value} -> {target.value} is not allowed")
        self.status = target
        if reason:
            self.stop_reason = reason
            self.record("stop", status=target.value, reason=reason)

    def record(self, event: str, **data: Any) -> None:
        self.history.append({"event": event, "step": self.step, **data})

    def next_step(self) -> int:
        self.step += 1
        return self.step

    def add_observation(self, observation: Observation) -> None:
        self.observations.append(observation)
        self.record("observation", **observation.model_dump(exclude={"output"}))

    def last_observation_for(self, tool_name: str) -> Observation | None:
        for observation in reversed(self.observations):
            if observation.tool == tool_name:
                return observation
        return None

    def observations_of(self, tool_name: str) -> list[Observation]:
        return [o for o in self.observations if o.tool == tool_name]

    def remember(self, key: str, value: Any) -> None:
        self.memory[key] = value

    def recall(self, key: str, default: Any = None) -> Any:
        return self.memory.get(key, default)

    def goal_met(self, criteria: Iterable[str]) -> bool:
        """True when every success criterion appears satisfied in memory.

        Deliberately dumb: the runtime records criteria outcomes under
        `criteria` in memory, and this only aggregates them. Smarter
        verification is a lesson, not a hidden default.
        """
        recorded = self.memory.get("criteria", {})
        return bool(list(criteria)) and all(recorded.get(name) for name in criteria)

    def transcript(self, limit: int = 20) -> list[str]:
        return [o.summary() for o in self.observations[-limit:]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal.objective,
            "status": self.status.value,
            "step": self.step,
            "stop_reason": self.stop_reason,
            "budget": self.budget.as_dict(),
            "observations": len(self.observations),
            "criteria_met": self.goal_met(self.goal.success_criteria),
        }


def initial_state(goal: Goal, budget: Budget | None = None) -> AgentState:
    """Build a runnable state. Passing `budget` is how a caller keeps custom
    limits; without it the state gets a default `Budget` sized to the goal."""
    state = AgentState(goal=goal, budget=budget or Budget())
    state.transition(Status.RUNNING)
    state.record("start", goal=goal.objective, max_steps=goal.max_steps)
    return state