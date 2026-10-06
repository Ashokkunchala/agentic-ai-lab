"""Policy engine: the gate between a model's intent and real-world effect.

The runtime calls `PolicyEngine.evaluate()` for every tool call, including
read-only ones. Denials and approval requirements are *returned*, never
raised, so the loop can record them as observations and keep going. A policy
that silently aborts the process is a policy you cannot debug.

Precedence, highest first:

1. `deny` set — always denied, no override.
2. `allow` set — allowed regardless of the tool's declared risk.
3. `require_approval` set — needs a human even if risk is READ.
4. Declared risk default: READ allows, WRITE/DESTRUCTIVE need approval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable


class Risk(str, Enum):
    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"


class Decision(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


@dataclass(frozen=True)
class PolicyResult:
    decision: Decision
    reason: str

    @property
    def blocked(self) -> bool:
        return self.decision is Decision.DENY


def requires_approval(risk: Risk) -> bool:
    """Risk levels that may never run without a human decision."""
    return risk in {Risk.WRITE, Risk.DESTRUCTIVE}


def allowed_by_default(risk: Risk) -> bool:
    """Risk levels that run unattended when policy says nothing else."""
    return risk == Risk.READ


@dataclass
class PolicyEngine:
    """Rule sets are evaluated in the order documented in the module docstring."""

    deny: set[str] = field(default_factory=set)
    allow: set[str] = field(default_factory=set)
    require_approval: set[str] = field(default_factory=set)

    def evaluate(self, tool_name: str, risk: Risk) -> PolicyResult:
        if tool_name in self.deny:
            return PolicyResult(Decision.DENY, f"{tool_name} is on the deny list")
        if tool_name in self.allow:
            return PolicyResult(Decision.ALLOW, f"{tool_name} is on the allow list")
        if tool_name in self.require_approval:
            return PolicyResult(
                Decision.REQUIRE_APPROVAL, f"{tool_name} requires approval by name"
            )
        if allowed_by_default(risk):
            return PolicyResult(Decision.ALLOW, f"{tool_name} is risk={risk.value}")
        if requires_approval(risk):
            return PolicyResult(
                Decision.REQUIRE_APPROVAL, f"{tool_name} is risk={risk.value}"
            )
        return PolicyResult(Decision.DENY, f"{tool_name} has no matching rule")

    def describe(self) -> dict[str, str]:
        return {
            "allow": ", ".join(sorted(self.allow)) or "-",
            "require_approval": ", ".join(sorted(self.require_approval)) or "-",
            "deny": ", ".join(sorted(self.deny)) or "-",
        }


@dataclass
class ApprovalGate:
    """Records approval decisions so a run can be audited after the fact.

    An approver callback receives `(tool_name, arguments)` and returns an
    approver identity or None. Passing no approver means the action stays
    unapproved and the loop must not execute it.
    """

    approver: Callable[[str, dict[str, object]], str | None] | None = None
    granted: dict[str, str] = field(default_factory=dict)
    refused: set[str] = field(default_factory=set)

    def ask(self, tool_name: str, arguments: dict[str, object]) -> str | None:
        if self.approver is None:
            self.refused.add(tool_name)
            return None
        identity = self.approver(tool_name, arguments)
        if identity:
            self.granted[tool_name] = identity
        else:
            self.refused.add(tool_name)
        return identity

    def journal(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = [
            {"tool": name, "approved_by": who} for name, who in sorted(self.granted.items())
        ]
        rows += [{"tool": name, "approved_by": None} for name in sorted(self.refused)]
        return rows


def deny_everything(*extra: Iterable[str]) -> PolicyEngine:
    """Safest possible engine: nothing runs. Useful as a test fixture."""
    names: set[str] = set()
    for group in extra:
        names.update(group)
    return PolicyEngine(deny=names)