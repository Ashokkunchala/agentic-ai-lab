"""Lesson 01: the smallest agent loop that can work.

Deliberately does NOT import `shared`. You should be able to read this file
top-to-bottom and hold the whole mechanism in your head. Lesson 03 is where
you replace this with something that survives production.

    goal -> decide -> act -> verify -> finish

Everything here is deterministic: no model, no network, no API key. That is on
purpose. The mechanics must be boring before a probabilistic component is
introduced, or you cannot tell which one broke.

Run:
    python 01-first-agent/agent.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

# Direct-script execution puts this folder on sys.path, not the repo root, so
# `import shared` would fail. Lessons that need the runtime add this two-line
# bootstrap; lesson 01 does not need it.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass
class State:
    """Everything needed to continue correctly. Nothing else."""

    goal: str
    prepared: bool = False
    organized: bool = False
    verified: bool = False
    steps_used: int = 0
    log: list[str] = field(default_factory=list)


def choose_action(state: State) -> str:
    """The policy of *what to do next*, hard-coded.

    A real agent asks a model this question. Note that it never mutates state:
    deciding and acting are separate, which is what makes the trace readable.
    """
    if not state.prepared:
        return "prepare"
    if not state.organized:
        return "organize"
    if not state.verified:
        return "verify"
    return "finish"


def execute(action: str, state: State) -> None:
    """The 'tools'. Here they are three lines of bookkeeping."""
    state.log.append(f"tool:{action}")
    if action == "prepare":
        state.prepared = True
    elif action == "organize":
        state.organized = True
    elif action == "verify":
        state.verified = state.prepared and state.organized


def is_done(state: State) -> bool:
    """Verification is a question about state, never a step in the loop."""
    return state.prepared and state.organized and state.verified


def run(goal: str, max_steps: int = 6) -> State:
    state = State(goal=goal)
    print(f"[goal] {goal}")
    while state.steps_used < max_steps:
        state.steps_used += 1
        action = choose_action(state)
        print(f"[step {state.steps_used}] decide -> {action}")
        if action == "finish":
            print("[verify] success criteria met")
            print("[result] complete")
            return state
        execute(action, state)
    raise RuntimeError(f"budget exhausted after {max_steps} steps: goal={goal!r}")


if __name__ == "__main__":
    final = run("Prepare the workspace")
    print("\ntrace:")
    for line in final.log:
        print(f"  {line}")