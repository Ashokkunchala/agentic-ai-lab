"""Evaluation: how you know the agent is not just confidently wrong.

A demo proves the loop *can* work. Evaluation proves it *keeps* working after
you change a prompt, a model or a tool. Three checks per case:

* `expect_tools` — the tools that must appear somewhere in the run.
* `forbid_tools` — tools that must never appear. This is the safety net, and
  it is the check people skip.
* `expect_status` — the terminal status the run must reach.

The harness is deterministic by construction: it takes a factory that builds a
loop, so a test supplies a scripted planner and no network is involved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

from .loop import AgentLoop, LoopResult
from .state import Status

LoopFactory = Callable[[], AgentLoop]


@dataclass(frozen=True)
class Case:
    name: str
    script: Sequence[str]
    expect_tools: tuple[str, ...] = ()
    forbid_tools: tuple[str, ...] = ()
    expect_status: Status = Status.COMPLETED
    expect_stop_contains: str = ""
    arguments: dict[str, dict[str, object]] = field(default_factory=dict)
    factory: LoopFactory | None = None
    """Optional per-case agent factory. Use it to vary budgets or policy."""


@dataclass
class Scorecard:
    cases: list[dict[str, object]] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for row in self.cases if row["passed"])

    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def ok(self) -> bool:
        return self.passed == self.total

    @property
    def pass_rate(self) -> float:
        return round(self.passed / self.total, 4) if self.total else 0.0

    def failures(self) -> list[dict[str, object]]:
        return [row for row in self.cases if not row["passed"]]

    def render(self) -> str:
        lines = [f"{'case':<28} {'result':<8} detail"]
        for row in self.cases:
            lines.append(f"{str(row['case']):<28} {str(row['result']):<8} {row['detail']}")
        lines.append(f"\n{self.passed}/{self.total} passed ({self.pass_rate:.0%})")
        return "\n".join(lines)


def run_case(factory: LoopFactory, case: Case) -> dict[str, object]:
    """Build a loop from the factory, force a scripted run, then assert."""
    loop = factory()
    _apply_script(loop, case)
    result: LoopResult = loop.run()
    return grade(case, result)


def _apply_script(loop: AgentLoop, case: Case) -> None:
    """Replace the planner with a scripted one so the case is reproducible.

    Mutating `loop.planner` rather than the factory is deliberate: it lets a
    single factory build several differently scripted cases. An explicitly
    supplied `verifier` is left alone — otherwise the harness would be testing
    its own predicate instead of the agent's.
    """
    from .model import ScriptedModel

    script: list[dict[str, object]] = []
    for name in case.script:
        script.append({"name": name, "arguments": case.arguments.get(name, {})})
    model = ScriptedModel(script)  # type: ignore[arg-type]
    loop.planner = lambda _state, _tools: model.propose(  # type: ignore[assignment]
        _state.goal, _state.observations, _tools
    )
    if loop.verifier is None:
        loop.verifier = lambda state: bool(state.observations) and all(
            o.success for o in state.observations
        )


def grade(case: Case, result: LoopResult) -> dict[str, object]:
    used = [o.tool for o in result.observations if o.tool]
    problems: list[str] = []

    missing = [t for t in case.expect_tools if t not in used]
    if missing:
        problems.append(f"missing tools: {missing}")

    forbidden = [t for t in case.forbid_tools if t in used]
    if forbidden:
        problems.append(f"forbidden tools used: {forbidden}")

    if result.state.status is not case.expect_status:
        problems.append(f"status {result.state.status.value} != {case.expect_status.value}")

    if case.expect_stop_contains and case.expect_stop_contains not in result.stop_reason:
        problems.append(f"stop reason missing {case.expect_stop_contains!r}")

    detail = "; ".join(problems) if problems else result.stop_reason
    return {
        "case": case.name,
        "passed": not problems,
        "result": "PASS" if not problems else "FAIL",
        "detail": detail,
        "steps": result.state.step,
        "tools": used,
        "stop_reason": result.stop_reason,
    }


def score(cases: Sequence[Case], factory: LoopFactory | None = None) -> Scorecard:
    """Grade every case. A case's own `factory` wins over the shared one."""
    rows: list[dict[str, object]] = []
    for case in cases:
        builder = case.factory or factory
        if builder is None:
            raise ValueError(f"case {case.name!r} has no factory and none was supplied")
        rows.append(run_case(builder, case))
    return Scorecard(cases=rows)