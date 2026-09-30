from dataclasses import dataclass, field
from typing import Any

@dataclass
class AgentState:
    goal: str
    step: int = 0
    status: str = "running"
    history: list[dict[str, Any]] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)

    def record(self, event: str, **data: Any) -> None:
        self.history.append({"event": event, "step": self.step, **data})
