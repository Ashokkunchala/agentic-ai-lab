"""Lesson 05: a plan is a dependency graph, not a numbered list.

A numbered list cannot express "verify only after deploy, but read the logs
before either". A dependency graph can, and it gives three things for free:

* `runnable()` — exactly the steps whose dependencies are satisfied.
* `topological_order()` — a deterministic sequence, so runs can be replayed.
* cycle detection — an impossible plan fails at build time, not at 3am.

Run:
    python 05-planning/agent.py
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.planner import (  # noqa: E402
    ECS_INCIDENT_PLAN,
    Plan,
    PlanError,
    PlanStep,
    linear_plan,
    topological_order,
)


def demo_linear() -> None:
    print("=== a linear plan ===")
    plan = linear_plan("inspect", "build", "test", "deploy", "verify")
    print(f"  runnable at the start : {[s.name for s in plan.runnable()]}")
    plan.complete("inspect")
    print(f"  after 'inspect'       : {[s.name for s in plan.runnable()]}")
    plan.complete("build")
    print(f"  after 'build'         : {[s.name for s in plan.runnable()]}")
    print(f"  topological order     : {plan.order()}")


def demo_parallel() -> None:
    print("\n=== a diamond: independent work can run in parallel ===")
    plan = Plan()
    plan.add(PlanStep("prepare"))
    plan.add(PlanStep("unit_tests", depends_on=["prepare"]))
    plan.add(PlanStep("lint", depends_on=["prepare"]))
    plan.add(PlanStep("package", depends_on=["unit_tests", "lint"]))
    plan.add(PlanStep("deploy", depends_on=["package"]))

    print(f"  initial order   : {topological_order(plan.steps)}")
    print(f"  ready first     : {[s.name for s in plan.runnable()]}")
    plan.complete("prepare")
    print(f"  after prepare   : {[s.name for s in plan.runnable()]}  <- two runnable at once")
    plan.complete("unit_tests")
    plan.complete("lint")
    print(f"  after both      : {[s.name for s in plan.runnable()]}")
    plan.complete("package")
    plan.complete("deploy")
    print(f"  done            : {plan.done}")


def demo_fan_in_ordering() -> None:
    print("\n=== deterministic order, so replays match ===")
    plan = Plan()
    plan.add(PlanStep("root"))
    plan.add(PlanStep("left", depends_on=["root"]))
    plan.add(PlanStep("right", depends_on=["root"]))
    plan.add(PlanStep("merge", depends_on=["left", "right"]))
    first = topological_order(plan.steps)
    second = topological_order(plan.steps)
    print(f"  run 1: {first}")
    print(f"  run 2: {second}")
    print(f"  identical: {first == second}")


def demo_failure_modes() -> None:
    print("\n=== plans that should never be built ===")
    unknown = Plan()
    unknown.add(PlanStep("deploy", depends_on=["review_that_does_not_exist"]))
    try:
        topological_order(unknown.steps)
    except PlanError as exc:
        print(f"  unknown dependency -> {exc}")

    cyclic = Plan()
    cyclic.add(PlanStep("a", depends_on=["c"]))
    cyclic.add(PlanStep("b", depends_on=["a"]))
    cyclic.add(PlanStep("c", depends_on=["b"]))
    try:
        topological_order(cyclic.steps)
    except PlanError as exc:
        print(f"  dependency cycle   -> {exc}")

    duplicate = Plan()
    duplicate.add(PlanStep("verify"))
    try:
        duplicate.add(PlanStep("verify"))
    except PlanError as exc:
        print(f"  duplicate step     -> {exc}")


def demo_real_plan() -> None:
    print("\n=== the plan lessons 10 and 12 actually use ===")
    for row in ECS_INCIDENT_PLAN.as_rows():
        deps = ",".join(row["depends_on"]) or "-"
        print(f"  {row['name']:<22} depends on {deps}")


if __name__ == "__main__":
    demo_linear()
    demo_parallel()
    demo_fan_in_ordering()
    demo_failure_modes()
    demo_real_plan()