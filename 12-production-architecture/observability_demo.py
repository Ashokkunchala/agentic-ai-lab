"""Lesson 12: the production surface — observability and evaluation.

Everything else in this repository is a demo. This file is the part you would
actually operate. It runs one incident-response agent four times, then shows
the three signals that make it debuggable and the scorecard that proves it did
not regress.

```text
logs    -> what happened, in order       (append-only JSONL)
metrics -> is the system healthy         (counters + timing aggregates)
traces  -> where did the time go         (nested spans with parents)
evals   -> did the behaviour survive     (pass rate over cases)
```

Note the order of the imports in this file. Runtime first, then observability,
then the assertion helpers. In a service you wire them the other way round and
regret it.

Run:
    python 12-production-architecture/observability_demo.py
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Sequence

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.evaluation import Case, score  # noqa: E402
from shared.loop import AgentLoop  # noqa: E402
from shared.models import Action, Goal  # noqa: E402
from shared.observability import JsonlLogger, Metrics, Tracer, new_run_id  # noqa: E402
from shared.policy import ApprovalGate, PolicyEngine, Risk  # noqa: E402
from shared.state import AgentState, Status  # noqa: E402
from shared.tooling import Tool, ToolRegistry  # noqa: E402


class ServiceInput(BaseModel):
    service: str = Field(default="checkout", min_length=1)


class DeployInput(BaseModel):
    image: str = Field(min_length=1)
    confirm: bool = Field(default=False)


CLUSTER = {"desired": 4, "running": 1, "pending": 3, "image": "v1.0.0", "deploys": 0}


def service_status(service: str = "checkout") -> dict[str, Any]:
    return {"service": service, "desired": CLUSTER["desired"], "running": CLUSTER["running"], "pending": CLUSTER["pending"]}


def task_stop_reasons(service: str = "checkout") -> dict[str, Any]:
    return {"service": service, "reasons": ["CannotPullContainerError"], "distinct": ["CannotPullContainerError"]}


def read_logs(service: str = "checkout") -> dict[str, Any]:
    return {"service": service, "lines": ["ERROR manifest unknown for image v1.0.0"]}


def deploy_image(image: str, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return {"applied": False, "reason": "confirm must be true"}
    CLUSTER["deploys"] += 1
    CLUSTER["running"] = CLUSTER["desired"]
    CLUSTER["image"] = image
    return {"applied": True, "image": image, "running": CLUSTER["running"]}


def build_registry() -> ToolRegistry:
    return ToolRegistry().register_all(
        [
            Tool("service_status", "READ", ServiceInput, service_status, Risk.READ),
            Tool("task_stop_reasons", "READ", ServiceInput, task_stop_reasons, Risk.READ),
            Tool("read_logs", "READ", ServiceInput, read_logs, Risk.READ),
            Tool("deploy_image", "WRITE, double gated", DeployInput, deploy_image, Risk.WRITE),
        ]
    )


def incident_planner(state: AgentState, tools: Sequence[dict[str, object]]) -> Action:
    """Evidence, then deploy. The order is the runbook, not a preference."""
    used = [o.tool for o in state.observations if o.tool]
    for tool_name in ("service_status", "task_stop_reasons", "read_logs"):
        if tool_name not in used:
            return Action(name=tool_name, arguments={"service": "checkout"}, rationale="evidence before mutation")
    if "deploy_image" not in used:
        return Action(
            name="deploy_image",
            arguments={"image": "v1.0.1", "confirm": True},
            rationale="previous image is known good",
        )
    return Action(name="finish", rationale="change applied; verify next")


def verify_incident(state: AgentState) -> bool:
    """Record the criterion, then answer. The state dump proves it later."""
    deploys = state.observations_of("deploy_image")
    output = deploys[-1].output if deploys and isinstance(deploys[-1].output, dict) else {}
    applied = output.get("applied") is True
    all_tasks_running = applied and output.get("running") == CLUSTER["desired"]
    state.remember("criteria", {"tasks_running": all_tasks_running})
    return bool(state.goal_met(state.goal.success_criteria))


def build_agent(run_id: str, logger: JsonlLogger, metrics: Metrics, tracer: Tracer, budget: Any = None) -> AgentLoop:
    kwargs: dict[str, Any] = {}
    if budget is not None:
        kwargs["budget"] = budget
    return AgentLoop(
        planner=incident_planner,
        registry=build_registry(),
        policy=PolicyEngine(),
        approvals=ApprovalGate(approver=lambda tool, args: "oncall"),
        goal=Goal(
            objective="resolve the checkout deployment failure",
            max_steps=6,
            success_criteria=["tasks_running"],
        ),
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        run_id=run_id,
        verifier=verify_incident,
        **kwargs,
    )


def demo_one_run() -> None:
    print("=== one instrumented run ===")
    run_id = new_run_id("incident")
    logger = JsonlLogger(echo=False)
    metrics = Metrics()
    tracer = Tracer()

    agent = build_agent(run_id, logger, metrics, tracer)
    result = agent.run()

    print(f"  run id      : {result.run_id}")
    print(f"  status      : {result.state.status.value}")
    print(f"  stop reason : {result.stop_reason}")
    print(f"  steps       : {result.state.step}")
    print(f"  approvals   : {result.approved}")

    print("\n  --- logs: ordered, replayable ---")
    for record in logger.records:
        extra = record.get("tool") or record.get("decision") or record.get("reason", "")
        print(f"    step {record.get('step', '-')!s:<3} {record['event']:<18} {extra}")

    print("\n  --- metrics: health, not history ---")
    snapshot = metrics.snapshot()
    print(f"    counters        : {snapshot['counters']}")
    print(f"    tool latency ms : {snapshot['timers_ms_mean']}")
    print(f"    tool p95 ms     : {snapshot['timers_ms_p95']}")
    print(f"    success rate    : {snapshot['tool_success_rate']:.0%}")

    print("\n  --- traces: nested spans ---")
    for span in tracer.run_trace(run_id):
        depth = 1 if span["parent_id"] else 0
        duration = span["duration_ms"]
        print(
            f"    {'  ' * depth}{span['name']:<8} "
            f"{(f'{duration:.3f}ms' if duration is not None else '-'):>10}"
            + (f"  error={span['error_type']}" if span["error_type"] else "")
        )

    print("\n  --- state dump: everything needed to explain the run ---")
    print(f"    {json.dumps(result.state.as_dict(), default=str)}")


def demo_evals() -> None:
    print("\n=== evaluation: does the behaviour still hold? ===")

    def factory() -> AgentLoop:
        return build_agent(new_run_id("eval"), JsonlLogger(), Metrics(), Tracer())

    def tight_factory() -> AgentLoop:
        from shared.budget import Budget

        return build_agent(
            new_run_id("eval-tight"),
            JsonlLogger(),
            Metrics(),
            Tracer(),
            budget=Budget(max_steps=2, max_consecutive_failures=5),
        )

    cases = [
        Case(
            name="happy-path-with-approval",
            script=["service_status", "task_stop_reasons", "read_logs", "deploy_image", "finish"],
            arguments={"deploy_image": {"image": "v1.0.1", "confirm": True}},
            expect_tools=("service_status", "task_stop_reasons", "read_logs", "deploy_image"),
            expect_status=Status.COMPLETED,
            expect_stop_contains="goal verified",
        ),
        Case(
            name="investigate-only-does-not-claim-success",
            script=["service_status", "task_stop_reasons", "read_logs", "finish"],
            forbid_tools=("deploy_image",),
            expect_status=Status.FAILED,
            expect_stop_contains="verification failed",
        ),
        Case(
            name="unknown-tool-is-observed-not-crashed",
            script=["service_status", "delete_everything", "service_status", "finish"],
            forbid_tools=("delete_everything",),
            expect_status=Status.FAILED,
            expect_stop_contains="verification failed",
        ),
        Case(
            name="tight-budget-stops-a-runaway",
            script=["service_status", "task_stop_reasons", "read_logs", "deploy_image", "finish"],
            expect_status=Status.BUDGET_EXHAUSTED,
            expect_stop_contains="budget exhausted",
            factory=tight_factory,
        ),
    ]
    print(score(cases, factory).render())
    print("\n  case 2 is the one people get wrong. An investigation that stopped")
    print("  short of applying a change must NOT report success, so the expected")
    print("  status is FAILED. `forbid_tools` is the assertion that catches a")
    print("  policy regression; case 4 shows a budget is a real control.")
    print("  case 3 shows a hallucinated tool name becomes an observation,")
    print("  never an exception that kills the run.")


def demo_slo_view() -> None:
    print("\n=== the four numbers worth an alert ===")
    logger = JsonlLogger()
    metrics = Metrics()
    tracer = Tracer()
    runs = [build_agent(new_run_id("slo"), logger, metrics, tracer).run() for _ in range(5)]

    completed = sum(1 for r in runs if r.state.status is Status.COMPLETED)
    steps = [r.state.step for r in runs]
    print(f"  success rate     : {completed}/{len(runs)}")
    print(f"  steps per run    : {steps} (mean {sum(steps) / len(steps):.1f})")
    print(f"  tool success rate: {metrics.success_rate():.0%}")
    print(f"  events logged    : {len(logger.records)}")
    print("\n  alert when: success rate drops, steps per task climbs, or a")
    print("  destructive tool is approved by someone who has never approved")
    print("  one before. that last one is a policy signal, not a metric.")


if __name__ == "__main__":
    print("Production surface: logs, metrics, traces, evals.\n")
    demo_one_run()
    demo_evals()
    demo_slo_view()