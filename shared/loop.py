"""The agent loop.

This module is the answer to a question the earlier version of this repository
got wrong: *how do you stop, and how do you know you succeeded?*

The old loop treated `verify` as an **action**. The decision function returned
"verify", the loop checked a flag that only `execute()` could set, so the check
happened one iteration too late. Every goal therefore cost two steps, and a
reachable goal at `target == max_steps` died with "step budget exhausted".

The fix is structural, not a bigger number:

```text
decide() -> Action              one decision per step
Action.name == "finish" -> verify(state) -> COMPLETED | FAILED
Action.name == <tool>   -> policy -> approve -> tool -> Observation
```

Verification is a **check on state**, never a step in the loop. A terminal
decision consumes exactly one step, so `max_steps` means what a reader thinks
it means.

Every exit is labelled: completed, failed, budget exhausted, or waiting on a
human. There is no path that returns without saying why.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol, Sequence

from .budget import Budget, BudgetExhausted
from .models import Action, Goal, Observation
from .observability import JsonlLogger, Metrics, Tracer, new_run_id
from .policy import ApprovalGate, Decision, PolicyEngine, Risk
from .state import AgentState, Status, initial_state
from .tooling import Tool, ToolRegistry, ToolResult

TERMINAL_ACTIONS = frozenset({"finish", "done", "final", "complete"})


class Planner(Protocol):
    """Anything that turns state into one proposed action."""

    def __call__(self, state: AgentState, tools: Sequence[dict[str, object]]) -> Action: ...


class Verifier(Protocol):
    """Anything that answers: did the goal actually succeed?"""

    def __call__(self, state: AgentState) -> bool: ...


@dataclass
class LoopResult:
    run_id: str
    state: AgentState
    observations: list[Observation]
    stop_reason: str
    approved: list[dict[str, object]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.state.status is Status.COMPLETED

    @property
    def parked(self) -> bool:
        """True when the run stopped for a human and can be resumed later."""
        return self.state.status is Status.WAITING_APPROVAL

    def summary(self) -> str:
        return (
            f"{self.run_id} {self.state.status.value} after {self.state.step} step(s): "
            f"{self.stop_reason}"
        )


class AgentLoop:
    """Observe -> decide -> policy -> act -> verify, with a budget on every step.

    Injectable collaborators are the reason this class is testable: pass a
    `ScriptedModel`-shaped planner and the whole runtime becomes deterministic.
    """

    def __init__(
        self,
        planner: Planner,
        registry: ToolRegistry,
        *,
        policy: PolicyEngine | None = None,
        approvals: ApprovalGate | None = None,
        goal: Goal | None = None,
        state: AgentState | None = None,
        budget: Budget | None = None,
        logger: JsonlLogger | None = None,
        metrics: Metrics | None = None,
        tracer: Tracer | None = None,
        verifier: Verifier | None = None,
        run_id: str | None = None,
    ) -> None:
        if state is None:
            if goal is None:
                raise ValueError("provide either goal or state")
            if budget is not None:
                goal.max_steps = min(goal.max_steps, budget.max_steps)
            state = initial_state(goal, budget)
        self.state = state
        self.planner = planner
        self.registry = registry
        self.policy = policy or PolicyEngine()
        self.approvals = approvals or ApprovalGate()
        self.verifier = verifier
        self.logger = logger or JsonlLogger()
        self.metrics = metrics or Metrics()
        self.tracer = tracer or Tracer()
        self.run_id = run_id or new_run_id("run")

    # ------------------------------------------------------------------ run

    def run(self) -> LoopResult:
        with self.tracer.span("run", self.run_id, step=0, goal=self.state.goal.objective):
            try:
                return self._drive()
            except BudgetExhausted as exc:
                return self._stop(Status.BUDGET_EXHAUSTED, str(exc))
            except Exception as exc:  # noqa: BLE001 - always exit with a reason
                self.logger.emit("run.error", run_id=self.run_id, error=f"{type(exc).__name__}: {exc}")
                return self._stop(Status.FAILED, f"{type(exc).__name__}: {exc}")

    def _drive(self) -> LoopResult:
        while True:
            reason = self.state.budget.exhausted_reason()
            if reason:
                return self._stop(Status.BUDGET_EXHAUSTED, reason)

            self.state.budget.charge_step()
            step = self.state.next_step()
            self.logger.emit("step.begin", run_id=self.run_id, step=step)

            action = self._decide(step)
            self.state.record("decision", name=action.name, rationale=action.rationale)

            if action.name in TERMINAL_ACTIONS:
                return self._finish(step)

            observation, park_reason = self._act(step, action)
            self.state.add_observation(observation)
            self.state.budget.record_outcome(observation.success)

            if park_reason is not None:
                # A human said no, or nobody was available. Park the run with a
                # labelled reason instead of retrying the same blocked action.
                return self._stop(Status.WAITING_APPROVAL, park_reason)

            if not observation.success and not self.state.budget.retry_allowed(
                action.name
            ):
                return self._stop(
                    Status.FAILED,
                    f"retry budget exhausted for {action.name}: {observation.error}",
                )

    # -------------------------------------------------------------- stages

    def _decide(self, step: int) -> Action:
        with self.tracer.span("decide", self.run_id, step) as span:
            action = self.planner(self.state, self.registry.describe())
            span.attributes["action"] = action.name
            self.metrics.increment("decisions")
            return action

    def _act(self, step: int, action: Action) -> tuple[Observation, str | None]:
        """Execute one proposed action. Returns `(observation, park_reason)`.

        `park_reason` is non-None only when a human must decide before this
        action can proceed. It is returned rather than raised so the caller
        decides whether to park, fail, or hand the run to another process.
        """
        tool = self.registry.find(action.name)
        if tool is None:
            return (
                self._observe(
                    step,
                    action,
                    ToolResult(
                        success=False,
                        error=f"unknown tool: {action.name}; available: {self.registry.names()}",
                    ),
                ),
                None,
            )

        with self.tracer.span("policy", self.run_id, step, tool=tool.name, risk=tool.risk.value):
            verdict = self.policy.evaluate(tool.name, tool.risk)
        self.state.record(
            "policy",
            tool=tool.name,
            risk=tool.risk.value,
            decision=verdict.decision.value,
            reason=verdict.reason,
        )
        self.logger.emit(
            "policy.decision",
            run_id=self.run_id,
            step=step,
            tool=tool.name,
            risk=tool.risk.value,
            decision=verdict.decision.value,
            reason=verdict.reason,
        )

        if verdict.decision is Decision.DENY:
            self.metrics.increment("policy.denied")
            return (
                self._observe(
                    step,
                    action,
                    ToolResult(success=False, error=f"denied by policy: {verdict.reason}"),
                    tool=tool,
                    risk=tool.risk,
                ),
                None,
            )

        approved_by = None
        if verdict.decision is Decision.REQUIRE_APPROVAL:
            with self.tracer.span("approval", self.run_id, step, tool=tool.name):
                approved_by = self.approvals.ask(tool.name, dict(action.arguments))
            self.metrics.increment("approval.requested")
            if approved_by is None:
                self.metrics.increment("approval.refused")
                self.state.record("approval.refused", tool=tool.name, reason=verdict.reason)
                return (
                    self._observe(
                        step,
                        action,
                        ToolResult(
                            success=False,
                            error=f"awaiting human approval: {verdict.reason}",
                        ),
                        tool=tool,
                        risk=tool.risk,
                    ),
                    f"human approval required for {tool.name}: {verdict.reason}",
                )
            self.metrics.increment("approval.granted")

        self.state.budget.charge_tool_call()
        with self.tracer.span("tool", self.run_id, step, tool=tool.name) as span:
            result = tool.run(dict(action.arguments))
            span.attributes["success"] = result.success
            if result.error:
                span.error_type = "tool_error"

        self.metrics.increment("tool.success" if result.success else "tool.failure")
        self.metrics.record_ms(f"tool.{tool.name}", result.duration_ms)

        if not result.success:
            self.state.budget.charge_retry(tool.name)
            self.metrics.increment("tool.retry")

        observation = self._observe(
            step,
            action,
            result,
            tool=tool,
            risk=tool.risk,
            approved_by=approved_by,
        )
        self.logger.emit("tool.result", run_id=self.run_id, **observation.model_dump(exclude={"output"}))
        return observation, None

    def _observe(
        self,
        step: int,
        action: Action,
        result: ToolResult,
        *,
        tool: Tool | None = None,
        risk: Risk | None = None,
        approved_by: str | None = None,
    ) -> Observation:
        return Observation(
            step=step,
            action=action.name,
            tool=tool.name if tool else None,
            success=result.success,
            output=result.output,
            error=result.error,
            duration_ms=result.duration_ms,
            risk=risk.value if risk else None,
            approved_by=approved_by,
        )

    def _finish(self, step: int) -> LoopResult:
        met = bool(self.verifier(self.state)) if self.verifier else False
        self.state.record("verify", met=met, criteria=len(self.state.goal.success_criteria))
        self.metrics.increment("verify.pass" if met else "verify.fail")
        if met:
            return self._stop(Status.COMPLETED, "goal verified")
        return self._stop(Status.FAILED, "agent finished but verification failed")

    def _stop(self, status: Status, reason: str) -> LoopResult:
        if self.state.status is not status and not self.state.is_terminal:
            self.state.transition(status, reason)
        else:
            self.state.stop_reason = reason
        self.state.record("metrics", **self.metrics.snapshot())
        self.logger.emit(
            "run.stop",
            run_id=self.run_id,
            status=status.value,
            reason=reason,
            steps=self.state.step,
            budget=self.state.budget.as_dict(),
        )
        return LoopResult(
            run_id=self.run_id,
            state=self.state,
            observations=list(self.state.observations),
            stop_reason=reason,
            approved=self.approvals.journal(),
        )


def run_to_completion(
    planner: Planner,
    registry: ToolRegistry,
    goal: Goal,
    **kwargs: object,
) -> LoopResult:
    """Convenience wrapper: build a loop and run it once."""
    loop = AgentLoop(planner=planner, registry=registry, goal=goal, **kwargs)  # type: ignore[arg-type]
    return loop.run()


__all__ = [
    "AgentLoop",
    "LoopResult",
    "Planner",
    "TERMINAL_ACTIONS",
    "Verifier",
    "run_to_completion",
]