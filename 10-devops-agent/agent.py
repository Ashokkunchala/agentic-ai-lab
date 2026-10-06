"""Lesson 10: a DevOps agent, evidence before mutation.

The runbook is the specification and the code walks it:

```text
observe -> hypothesise -> validate -> propose -> APPROVE -> apply -> verify
```

Two rules this file exists to enforce:

1. **Evidence before mutation.** No tool with WRITE or DESTRUCTIVE risk is
   reachable until the read-only observations exist and a human approved.
2. **Dry run is the default.** Every mutating tool requires an explicit
   `confirm=true` argument in addition to passing policy. Two independent
   gates, because a misconfigured policy should not be the only thing standing
   between a model and production.

Risk levels come from `shared.policy.Risk`, so there is one vocabulary across
the whole repository. `docs/CHARTS.md` has the risk matrix.

Run:
    python 10-devops-agent/agent.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.planner import ECS_INCIDENT_PLAN  # noqa: E402
from shared.policy import Decision, PolicyEngine, Risk  # noqa: E402
from shared.tooling import Tool, ToolRegistry  # noqa: E402

# Fake cluster state so the lesson has no AWS dependency and no credentials.
CLUSTER = {
    "service": "checkout",
    "desired": 4,
    "running": 1,
    "pending": 3,
    "deployment": "image:v2.14.0",
    "previous": "image:v2.13.4",
    "target_health": {"healthy": 1, "unhealthy": 3},
    "task_stop_reasons": ["CannotPullContainerError", "CannotPullContainerError", "ResourceInitializationError"],
    "log_tail": [
        "ERROR failed to pull image v2.14.0: manifest unknown",
        "ERROR failed to pull image v2.14.0: manifest unknown",
        "INFO  previous image v2.13.4 started successfully",
    ],
    "apply_count": 0,
}


class ServiceInput(BaseModel):
    service: str = Field(default="checkout", min_length=1)


class LinesInput(BaseModel):
    lines: int = Field(default=10, ge=1, le=500)


class RollbackInput(BaseModel):
    service: str = Field(default="checkout", min_length=1)
    confirm: bool = Field(default=False, description="Must be true. The second gate.")


def get_service_status(service: str = "checkout") -> dict[str, Any]:
    return {
        "service": service,
        "desired": CLUSTER["desired"],
        "running": CLUSTER["running"],
        "pending": CLUSTER["pending"],
        "deployment": CLUSTER["deployment"],
        "previous": CLUSTER["previous"],
    }


def get_target_group_health(service: str = "checkout") -> dict[str, Any]:
    return {"target_group": f"tg-{service}", **CLUSTER["target_health"]}


def get_task_stop_reasons(service: str = "checkout") -> dict[str, Any]:
    reasons = CLUSTER["task_stop_reasons"]
    return {"service": service, "reasons": reasons, "distinct": sorted(set(reasons))}


def read_log_lines(service: str = "checkout", lines: int = 10) -> dict[str, Any]:
    return {"service": service, "lines": CLUSTER["log_tail"][:lines]}


def diagnose(evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Turn observations into one falsifiable hypothesis.

    A hypothesis that cannot be wrong is not a hypothesis. This one names the
    image tag, the failing step and the rollback that would fix it.
    """
    reasons = set(evidence.get("stop_reasons", {}).get("distinct", []))
    logs = " ".join(evidence.get("logs", {}).get("lines", []))
    image = CLUSTER["deployment"]
    previous = CLUSTER["previous"]

    if "CannotPullContainerError" in reasons and "manifest unknown" in logs:
        return {
            "hypothesis": f"deployment {image} was never published to the registry",
            "evidence": [
                f"stop reasons: {sorted(reasons)}",
                f"log line: {logs.splitlines()[0] if logs else 'n/a'}",
                f"previous deployment {previous} started successfully",
            ],
            "falsified_if": "the image exists in the registry and tasks start cleanly",
            "proposed_change": f"roll {service_or_default()} back to {previous}",
            "risk": Risk.WRITE.value,
            "rollback": f"redeploy {image} after the registry push is fixed",
        }
    return {
        "hypothesis": "insufficient evidence to name a cause",
        "evidence": sorted(reasons),
        "falsified_if": "n/a",
        "proposed_change": "collect more evidence; do not mutate",
        "risk": Risk.READ.value,
        "rollback": "n/a",
    }


def service_or_default() -> str:
    return str(CLUSTER["service"])


def rollback_to_previous(service: str = "checkout", confirm: bool = False) -> dict[str, Any]:
    """WRITE risk, and gated twice: policy approval *and* confirm=true."""
    if not confirm:
        return {
            "applied": False,
            "reason": "refused: confirm must be true. This tool defaults to doing nothing.",
        }
    CLUSTER["apply_count"] += 1
    return {
        "applied": True,
        "service": service,
        "deployment": CLUSTER["previous"],
        "apply_count": CLUSTER["apply_count"],
        "note": "in-memory only; this lesson never calls AWS",
    }


def verify_service_health(service: str = "checkout") -> dict[str, Any]:
    healthy = CLUSTER["apply_count"] > 0
    return {
        "service": service,
        "deployment": CLUSTER["deployment"] if not healthy else CLUSTER["previous"],
        "running": CLUSTER["desired"] if healthy else CLUSTER["running"],
        "healthy": healthy,
    }


def build_registry() -> ToolRegistry:
    return ToolRegistry().register_all(
        [
            Tool("service_status", "READ. Desired/running/pending and deployment.", ServiceInput, get_service_status, Risk.READ),
            Tool("target_group_health", "READ. Target health counts.", ServiceInput, get_target_group_health, Risk.READ),
            Tool("task_stop_reasons", "READ. Why tasks stopped.", ServiceInput, get_task_stop_reasons, Risk.READ),
            Tool("read_logs", "READ. Recent log lines.", LinesInput, read_log_lines, Risk.READ),
            Tool("rollback", "WRITE. Roll back to the previous task definition.", RollbackInput, rollback_to_previous, Risk.WRITE),
            Tool("verify_health", "READ. Post-change health.", ServiceInput, verify_service_health, Risk.READ),
        ]
    )


def observe(registry: ToolRegistry) -> dict[str, dict[str, Any]]:
    print("=== observe: read-only evidence first ===")
    evidence: dict[str, dict[str, Any]] = {}
    calls = [
        ("status", "service_status", {"service": "checkout"}),
        ("health", "target_group_health", {"service": "checkout"}),
        ("stop_reasons", "task_stop_reasons", {"service": "checkout"}),
        ("logs", "read_logs", {"lines": 5}),
    ]
    for key, name, arguments in calls:
        result = registry.get(name).run(arguments)
        evidence[key] = result.output or {}
        print(f"  {name:<20} risk={registry.get(name).risk.value:<5} {'ok' if result.success else 'ERROR'}  {result.output}")
    return evidence


def check_policy() -> None:
    print("\n=== policy: what each tool is allowed to do unattended ===")
    registry = build_registry()
    policy = PolicyEngine()
    for name in registry.names():
        tool = registry.get(name)
        verdict = policy.evaluate(name, tool.risk)
        marker = {
            Decision.ALLOW: "runs unattended",
            Decision.REQUIRE_APPROVAL: "NEEDS A HUMAN",
            Decision.DENY: "blocked",
        }[verdict.decision]
        print(f"  {name:<20} risk={tool.risk.value:<11} {marker:<14} ({verdict.reason})")


def show_plan() -> None:
    print("\n=== the plan, as a dependency graph ===")
    for row in ECS_INCIDENT_PLAN.as_rows():
        deps = ", ".join(row["depends_on"]) or "-"
        print(f"  {row['name']:<22} <- {deps}")


def propose_and_gate(registry: ToolRegistry, evidence: dict[str, dict[str, Any]]) -> None:
    print("\n=== propose: one falsifiable hypothesis ===")
    finding = diagnose(evidence)
    for key in ("hypothesis", "evidence", "falsified_if", "proposed_change", "risk", "rollback"):
        value = finding[key]
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value)
        print(f"  {key:<16}: {value}")

    print("\n=== gate 1: policy ===")
    verdict = PolicyEngine().evaluate("rollback", Risk.WRITE)
    print(f"  rollback -> {verdict.decision.value}: {verdict.reason}")

    print("\n=== gate 2: the tool's own confirm flag ===")
    result = registry.get("rollback").run({"service": "checkout"})
    print(f"  confirm omitted -> {result.output}")

    print("\n=== after approval + confirm, the change applies ===")
    approved = registry.get("rollback").run({"service": "checkout", "confirm": True})
    print(f"  confirm=true     -> {approved.output}")

    print("\n=== verify: behaviour, not exit code ===")
    health = registry.get("verify_health").run({"service": "checkout"})
    print(f"  verify_health -> {health.output}")
    print("\n  before the change: running=1/4 unhealthy=3 -> 'applied' with exit 0 would")
    print("  have been a false success. Verify the user-facing state instead.")


if __name__ == "__main__":
    print("DevOps agent lesson: evidence before mutation, twice-gated writes.\n")
    registry = build_registry()
    evidence = observe(registry)
    check_policy()
    show_plan()
    propose_and_gate(registry, evidence)