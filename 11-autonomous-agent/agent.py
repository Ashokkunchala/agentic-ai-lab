"""Lesson 11: bounded autonomy.

Lesson 08 said a budget is a cost. This lesson shows what happens without one,
then makes every limit real.

Seven controls, all enforced in code rather than described in a README:

| control       | where                    |
|---------------|--------------------------|
| step budget   | `Budget.max_steps`       |
| tool calls    | `Budget.max_tool_calls`  |
| retries/tool  | `Budget.max_retries_per_tool` |
| stall guard   | `Budget.max_consecutive_failures` |
| time budget   | `Budget.max_seconds`     |
| cost budget   | `Budget.max_cost_usd`    |
| approvals     | `PolicyEngine` + `ApprovalGate` |

The naive run at the top of this file is the version that ships by accident:
a loop that retries forever and bills you while it does.

Run:
    python 11-autonomous-agent/agent.py
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Sequence

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.budget import Budget  # noqa: E402
from shared.loop import AgentLoop  # noqa: E402
from shared.models import Action, Goal  # noqa: E402
from shared.observability import JsonlLogger, Metrics, Tracer  # noqa: E402
from shared.policy import ApprovalGate, PolicyEngine, Risk  # noqa: E402
from shared.state import AgentState  # noqa: E402
from shared.tooling import Tool, ToolRegistry  # noqa: E402


class FlakyInput(BaseModel):
    """A tool that fails on purpose, to exercise the retry and stall guards."""

    mode: str = Field(default="always_fail", pattern="^(always_fail|fail_then_succeed|always_succeed)$")


class Flaky:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.attempts = 0

    def call(self, mode: str = "always_fail") -> dict[str, Any]:
        self.attempts += 1
        if self.mode == "always_fail":
            raise TimeoutError(f"upstream timed out (attempt {self.attempts})")
        if self.mode == "fail_then_succeed" and self.attempts < 2:
            raise TimeoutError(f"upstream timed out (attempt {self.attempts})")
        return {"attempts": self.attempts, "status": "ok"}


def naive_unbounded_run() -> int:
    """What 'no limits' looks like. Returns the attempt count, then gives up.

    This is the anti-pattern in miniature: an unbounded retry loop against a
    service that will never recover. In production this is a bill and an alert.
    """
    flaky = Flaky("always_fail")
    attempts = 0
    while attempts < 50:
        attempts += 1
        try:
            flaky.call()
            break
        except TimeoutError:
            pass
    print(f"  attempts made: {attempts}, result: still failing")
    print("  stopped only because this file hard-coded 50.")
    print("  a real loop has no such number, so it retries until someone notices.")
    return attempts


def build_registry(flaky: Flaky) -> ToolRegistry:
    return ToolRegistry().register_all(
        [
            Tool("flaky_call", "Calls a service that may fail.", FlakyInput, flaky.call, Risk.READ),
        ]
    )


def run_bounded(
    *,
    mode: str,
    max_steps: int,
    max_retries: int,
    max_consecutive_failures: int,
    max_seconds: float | None = None,
    max_cost_usd: float | None = None,
    verbose: bool = True,
) -> tuple[Any, Any, Any]:
    flaky = Flaky(mode)
    registry = build_registry(flaky)
    budget = Budget(
        max_steps=max_steps,
        max_tool_calls=max_steps * 2,
        max_retries_per_tool=max_retries,
        max_consecutive_failures=max_consecutive_failures,
        max_seconds=max_seconds,
        max_cost_usd=max_cost_usd,
    )
    logger = JsonlLogger()
    metrics = Metrics()
    tracer = Tracer()

    def planner(state: AgentState, tools: Sequence[dict[str, object]]) -> Action:
        if any(o.success for o in state.observations):
            return Action(name="finish", rationale="the service responded successfully")
        return Action(name="flaky_call", arguments={"mode": mode}, rationale="keep trying")

    loop = AgentLoop(
        planner=planner,
        registry=registry,
        policy=PolicyEngine(),
        goal=Goal(objective=f"get a success from a service in mode={mode}", max_steps=max_steps),
        budget=budget,
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        verifier=lambda state: any(o.success for o in state.observations),
    )
    result = loop.run()
    if verbose:
        print(f"  {result.summary()}")
        print(f"  attempts at the tool: {flaky.attempts}")
        print(f"  budget: {budget.as_dict()}")
    return result, metrics, logger


def demo_limits() -> None:
    print("\n=== 1. no limits: the anti-pattern ===")
    naive_unbounded_run()

    print("\n=== 2. retries per tool stop a hopeless tool ===")
    print(" always_fail, max_retries=2:")
    run_bounded(mode="always_fail", max_steps=10, max_retries=2, max_consecutive_failures=10)

    print("\n=== 3. a transient failure is survivable ===")
    print(" fail_then_succeed, max_retries=3:")
    run_bounded(mode="fail_then_succeed", max_steps=10, max_retries=3, max_consecutive_failures=3)

    print("\n=== 4. the stall guard catches what retries do not ===")
    print(" always_fail, max_retries=99 but stall limit 3:")
    run_bounded(mode="always_fail", max_steps=50, max_retries=99, max_consecutive_failures=3)

    print("\n=== 5. the step ceiling is the outer bound ===")
    print(" always_succeed but never finishes, max_steps=4:")
    flaky = Flaky("always_succeed")
    registry = build_registry(flaky)
    budget = Budget(max_steps=4, max_consecutive_failures=5)

    def forever(state: AgentState, tools: Sequence[dict[str, object]]) -> Action:
        return Action(name="flaky_call", arguments={"mode": "always_succeed"})

    loop = AgentLoop(
        planner=forever,
        registry=registry,
        policy=PolicyEngine(),
        goal=Goal(objective="never terminates on its own", max_steps=4),
        budget=budget,
    )
    result = loop.run()
    print(f"  {result.summary()}")

    print("\n=== 6. every run leaves an audit trail ===")
    with tempfile.TemporaryDirectory() as folder:
        result, metrics, logger = run_bounded(
            mode="fail_then_succeed", max_steps=6, max_retries=3, max_consecutive_failures=3, verbose=False
        )
        path = Path(folder) / "run.jsonl"
        persisted = JsonlLogger(path)
        for record in logger.records:
            persisted.emit(record.pop("event"), **record)
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        print(f"  events written: {len(lines)}")
        print(f"  event kinds   : {sorted({json.loads(line)['event'] for line in lines})}")
        print(f"  counters      : {metrics.snapshot()['counters']}")
        print(f"  tool success  : {metrics.success_rate():.0%}")


if __name__ == "__main__":
    print("Bounded autonomy: every limit here is enforced, not documented.\n")
    demo_limits()