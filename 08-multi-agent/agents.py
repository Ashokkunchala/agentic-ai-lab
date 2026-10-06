"""Lesson 08: delegation, and the coordination cost that comes with it.

Splitting one agent into several is not free. Each added agent needs:

* a contract (what it returns, typed),
* a routing rule (who calls whom),
* a budget (what it may spend),
* a verification story (how the parent checks the child's claim).

The lesson's honest conclusion: **most systems do not need multiple agents.**
Lesson 08 exists so you can recognise when you do, and recognise the smell of
an architecture that adopted multi-agent design too early.

Run:
    python 08-multi-agent/agents.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Protocol

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.budget import Budget  # noqa: E402


@dataclass(frozen=True)
class Finding:
    """The only thing a child agent is allowed to return.

    A typed result with a `confidence` is what makes delegation auditable. A
    child that returns free prose forces the parent to trust it blindly.
    """

    summary: str
    evidence: tuple[str, ...]
    confidence: float

    def as_dict(self) -> dict[str, object]:
        return {"summary": self.summary, "evidence": list(self.evidence), "confidence": self.confidence}


class Specialist(Protocol):
    name: str

    def __call__(self, task: str) -> Finding: ...


DEFAULT_CORPUS = {
    "policy.md": "Deny rules win over allow rules. Writes need approval.",
    "budget.md": "Step, tool-call, retry, time and cost budgets bound autonomy.",
    "retrieval.md": "Every retrieved chunk must carry a citation.",
    "logging.md": "Logs record run id, step id, tool name, status and duration.",
}


@dataclass
class Researcher:
    name: str = "researcher"
    corpus: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_CORPUS))

    def __call__(self, task: str) -> Finding:
        words = [w for w in task.lower().split() if len(w) > 3]
        hits = [key for key, text in self.corpus.items() if any(w in text.lower() for w in words)]
        if not hits:
            return Finding(summary=f"no evidence found for {task!r}", evidence=(), confidence=0.0)
        return Finding(
            summary=f"evidence from {len(hits)} document(s)",
            evidence=tuple(hits),
            confidence=round(min(1.0, 0.4 + 0.2 * len(hits)), 3),
        )


@dataclass
class Reviewer:
    """A child that can *reject* its sibling's output."""

    name: str = "reviewer"
    required_terms: tuple[str, ...] = ("evidence",)

    def __call__(self, task: str, finding: Finding) -> Finding:
        missing = [term for term in self.required_terms if term not in finding.summary.lower()]
        if missing or not finding.evidence:
            return Finding(
                summary=f"rejected: {finding.summary} lacks {missing or ['evidence']}",
                evidence=finding.evidence,
                confidence=0.0,
            )
        return Finding(
            summary=f"accepted: {finding.summary}",
            evidence=finding.evidence,
            confidence=round(min(1.0, finding.confidence + 0.3), 3),
        )


@dataclass
class Orchestrator:
    """The parent. Owns the budget, the routing and the final decision."""

    researcher: Researcher = field(default_factory=Researcher)
    reviewer: Reviewer = field(default_factory=Reviewer)
    budget: Budget = field(default_factory=lambda: Budget(max_steps=6))

    def handle(self, goal: str) -> dict[str, object]:
        self.budget.charge_step()
        research = self.researcher(goal)
        self.budget.charge_tool_call()
        print(f"  [{self.researcher.name}] {research.summary} conf={research.confidence}")

        if not research.evidence:
            return {
                "goal": goal,
                "answer": "insufficient evidence; escalate to a human",
                "confident": False,
                "steps_used": self.budget.steps,
            }

        self.budget.charge_step()
        review = self.reviewer(goal, research)
        self.budget.charge_tool_call()
        print(f"  [{self.reviewer.name}] {review.summary} conf={review.confidence}")

        confident = review.confidence >= 0.7
        print(f"  [orchestrator] budget: {self.budget.as_dict()}")
        return {
            "goal": goal,
            "answer": review.summary,
            "confident": confident,
            "steps_used": self.budget.steps,
            "needs_human": not confident,
        }


def demo_single_agent_first() -> None:
    print("=== step 0: does this need more than one agent? ===")
    print("  A single agent with two tools is usually enough.")
    print("  Reach for a second agent when the task needs a *different")
    print("  permission set, a different context window, or an independent")
    print("  judgement - not merely because the prompt got long.\n")


def demo_delegation() -> None:
    print("=== delegation with typed results ===")
    orchestrator = Orchestrator(
        researcher=Researcher(
            corpus={
                "policy.md": "Deny rules win over allow rules. Writes need approval.",
                "budget.md": "Step, tool-call, retry, time and cost budgets bound autonomy.",
                "retrieval.md": "Every retrieved chunk must carry a citation.",
                "logging.md": "Logs record run id, step id, tool name, status and duration.",
            }
        )
    )
    outcome = orchestrator.handle("what evidence does policy require for a write")
    print(f"  outcome: {outcome}\n")


def demo_rejection() -> None:
    print("=== a child that can reject its sibling ===")
    empty = Finding(summary="everything is fine", evidence=(), confidence=0.9)
    review = Reviewer().__call__("anything", empty)
    print(f"  child claimed : {empty.summary} (confidence {empty.confidence})")
    print(f"  reviewer said : {review.summary} (confidence {review.confidence})")
    print("  high confidence with no evidence is exactly the failure mode")
    print("  a reviewer exists to catch.\n")


def demo_cost() -> None:
    print("=== what multi-agent actually costs ===")
    orchestrator = Orchestrator()
    orchestrator.handle("citation retrieved evidence")
    used = orchestrator.budget
    print(f"  steps charged      : {used.steps}")
    print(f"  tool calls charged : {used.tool_calls}")
    print("  each hop adds latency, tokens and a new failure point")
    print("  N agents is N times the contract surface to maintain.\n")


def demo_budget_exhaustion() -> None:
    print("=== children inherit a budget or they will not stop ===")
    orchestrator = Orchestrator()
    for index in range(6):
        try:
            orchestrator.handle("citation retrieved evidence")
        except Exception as exc:
            print(f"  parent stopped at call {index + 1}: {exc}")
            break
    else:
        print("  (no exhaustion, budget was sufficient)")
    print("  lesson 11 turns this into a first-class control.")


if __name__ == "__main__":
    print("Multi-agent lesson: delegation is a cost, not an upgrade.\n")
    demo_single_agent_first()
    demo_delegation()
    demo_rejection()
    demo_cost()
    demo_budget_exhaustion()