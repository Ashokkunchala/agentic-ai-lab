"""Lesson 03: the hardened loop.

Compare against `naive.py` in this folder. Same goal, same tools, but:

```text
decide() -> Action                    one decision per step
Action == "finish" -> verify(state)   verification is a CHECK, not a step
Action == <tool>   -> policy -> approval -> execute -> Observation
```

Terminal decisions now cost exactly one step, so `max_steps` means what a
reader thinks it means. Every exit is labelled: completed, failed, budget
exhausted, or waiting on a human.

Read `shared/loop.py` after running this. The docstring there explains each
decision this file depends on.

Run:
    python 03-agent-loop/agent.py
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Sequence

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.loop import AgentLoop  # noqa: E402
from shared.models import Action, Goal  # noqa: E402
from shared.policy import ApprovalGate, PolicyEngine, Risk  # noqa: E402
from shared.state import AgentState  # noqa: E402
from shared.tooling import EmptyInput, Tool, ToolRegistry  # noqa: E402


class StepInput(BaseModel):
    count: int = Field(default=1, ge=1, le=100)


class RecordInput(BaseModel):
    key: str = Field(min_length=1)
    value: str = Field(min_length=1)


class Counter:
    """Stand-in for a real service. Keeps the lesson free of side effects."""

    def __init__(self) -> None:
        self.total = 0
        self.notes: dict[str, str] = {}

    def step(self, count: int = 1) -> dict[str, Any]:
        self.total += count
        return {"total": self.total}

    def record(self, key: str, value: str) -> dict[str, Any]:
        self.notes[key] = value
        return {"key": key, "value": value, "note_count": len(self.notes)}

    def check() -> dict[str, Any]:
        return {"total": self.total, "note_count": len(self.notes), "ready": self.total >= 3}


def build_registry(counter: Counter) -> ToolRegistry:
    return ToolRegistry().register_all(
        [
            Tool("step", "Advance the counter. This mutates state.", StepInput, counter.step, Risk.WRITE),
            Tool("record", "Store a note. This writes data.", RecordInput, counter.record, Risk.WRITE),
            Tool("check", "Read the counter without changing it.", EmptyInput, counter.check, Risk.READ),
        ]
    )


def make_planner(target: int) -> Any:
    """Deterministic stand-in for a model.

    A real planner is an LLM that reads state and emits an `Action`. Swapping
    this function for a `TranscriptModel` subclass is the only change lesson 12
    needs.
    """
    cursor = {"recorded": False}

    def planner(state: AgentState, tools: Sequence[dict[str, object]]) -> Action:
        total = state.memory.get("total", 0)
        if total >= target:
            return Action(name="finish", rationale=f"target {target} reached at total={total}")
        if not cursor["recorded"]:
            cursor["recorded"] = True
            return Action(name="record", arguments={"key": "run", "value": "lesson-03"}, rationale="capture provenance first")
        return Action(name="step", arguments={"count": 1}, rationale=f"total {total} below target {target}")

    return planner


def fold_observations(state: AgentState) -> None:
    """Reduce raw observations into the few facts the planner actually needs.

    Without this the planner would re-read every observation on every step, and
    the prompt would grow without bound. In production this is where a state
    reducer, a summariser or a structured-output parser belongs.
    """
    for observation in state.observations:
        if not observation.success or not isinstance(observation.output, dict):
            continue
        if observation.tool == "step":
            state.remember("total", observation.output.get("total", state.recall("total", 0)))
        elif observation.tool == "record":
            state.remember("note", observation.output.get("value"))


def run_once(target: int, max_steps: int, approver: Any, policy: PolicyEngine) -> Any:
    counter = Counter()
    registry = build_registry(counter)
    goal = Goal(
        objective=f"advance the counter to {target}",
        max_steps=max_steps,
        success_criteria=["total_at_target"],
    )

    inner = make_planner(target)

    def planner(state: AgentState, tools: Sequence[dict[str, object]]) -> Action:
        fold_observations(state)
        return inner(state, tools)

    loop = AgentLoop(
        planner=planner,
        registry=registry,
        policy=policy,
        approvals=ApprovalGate(approver=approver),
        goal=goal,
        verifier=lambda state: state.recall("total", 0) >= target,
    )
    return loop.run()


def auto_approve(tool: str, arguments: dict[str, object]) -> str:
    return "lesson-auto-approver"


def refuse(tool: str, arguments: dict[str, object]) -> str | None:
    print(f"  human asked to approve {tool}({arguments}) -> refused")
    return None


def show(label: str, result: Any) -> None:
    print(f"  status     : {result.state.status.value} (parked={result.parked})")
    print(f"  steps used : {result.state.step}")
    print(f"  stop reason: {result.stop_reason}")
    print(f"  approvals  : {result.approved}")
    for observation in result.observations:
        print(f"    {observation.summary()}")


def section(label: str, **kwargs: Any) -> Any:
    """Print the header before running, so approval prompts interleave correctly."""
    print(f"\n=== {label} ===")
    return show("result", run_once(**kwargs))


def main() -> None:
    print("naive.py needed target+2 steps. This needs target+1, and every exit is labelled.")

    section(
        "A: comfortable budget, 1 provenance write + 3 work steps + 1 terminal = 5",
        target=3,
        max_steps=8,
        approver=auto_approve,
        policy=PolicyEngine(),
    )

    section(
        "B: budget too small, reported honestly instead of pretending",
        target=5,
        max_steps=3,
        approver=auto_approve,
        policy=PolicyEngine(),
    )

    section(
        "C: policy denies everything, stall detected in 3 steps not 8",
        target=3,
        max_steps=8,
        approver=auto_approve,
        policy=PolicyEngine(deny={"step", "record"}),
    )

    section(
        "D: approval refused by the human, run parks and can be resumed",
        target=2,
        max_steps=8,
        approver=refuse,
        policy=PolicyEngine(),
    )


if __name__ == "__main__":
    main()