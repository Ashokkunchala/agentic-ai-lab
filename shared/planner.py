"""Planning as a dependency graph.

A plan is a set of named steps with declared dependencies. Two properties
matter, and both are cheap to test:

1. `topological_order` is deterministic — the same plan always yields the same
   sequence, so a run can be replayed.
2. A dependency cycle raises. Silently emitting a partial order is how agents
   "finish" plans they never started.

This is deliberately *not* an LLM planner. See `docs/FROM-SCRATCH-TO-PRODUCTION.md`
for how a model-generated plan gets validated before it reaches this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class PlanError(ValueError):
    """Raised for an unknown dependency or a dependency cycle."""


@dataclass
class PlanStep:
    name: str
    depends_on: list[str] = field(default_factory=list)
    completed: bool = False
    output: object = None

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "depends_on": list(self.depends_on),
            "completed": self.completed,
        }


@dataclass
class Plan:
    steps: dict[str, PlanStep] = field(default_factory=dict)

    def add(self, step: PlanStep) -> PlanStep:
        if step.name in self.steps:
            raise PlanError(f"duplicate step: {step.name}")
        self.steps[step.name] = step
        return step

    def runnable(self) -> list[PlanStep]:
        """Steps whose dependencies are all complete, in insertion order."""
        return [
            step
            for step in self.steps.values()
            if not step.completed
            and all(self.steps[dep].completed for dep in step.depends_on)
        ]

    def blocked(self) -> list[PlanStep]:
        ready = {step.name for step in self.runnable()}
        return [step for step in self.steps.values() if not step.completed and step.name not in ready]

    def complete(self, name: str, output: object = None) -> None:
        step = self.steps.get(name)
        if step is None:
            raise PlanError(f"unknown step: {name}")
        step.completed = True
        step.output = output

    @property
    def done(self) -> bool:
        return all(step.completed for step in self.steps.values())

    def order(self) -> list[str]:
        return topological_order(self.steps)

    def as_rows(self) -> list[dict[str, object]]:
        return [step.as_dict() for step in self.steps.values()]


def topological_order(steps: dict[str, PlanStep]) -> list[str]:
    """Deterministic Kahn's algorithm with an explicit cycle error.

    Ties are broken by insertion order, which is what makes replays match.
    """
    pending = {name: [d for d in step.depends_on] for name, step in steps.items()}
    for name, deps in pending.items():
        for dep in deps:
            if dep not in steps:
                raise PlanError(f"{name} depends on unknown step: {dep}")

    order: list[str] = []
    while pending:
        ready = [name for name, deps in pending.items() if not deps]
        if not ready:
            stuck = ", ".join(sorted(pending))
            raise PlanError(f"dependency cycle among: {stuck}")
        for name in ready:
            order.append(name)
            del pending[name]
        for deps in pending.values():
            for name in ready:
                if name in deps:
                    deps.remove(name)
    return order


def linear_plan(*names: str) -> Plan:
    """Convenience for lessons: a simple chain of steps."""
    plan = Plan()
    previous: list[str] = []
    for name in names:
        plan.add(PlanStep(name=name, depends_on=list(previous)))
        previous = [name]
    return plan


ECS_INCIDENT_PLAN = linear_plan(
    "observe_service",
    "observe_target_group",
    "read_task_failures",
    "read_logs",
    "form_hypothesis",
    "propose_change",
    "await_approval",
    "apply_change",
    "verify_health",
)