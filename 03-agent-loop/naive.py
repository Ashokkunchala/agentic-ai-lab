"""The loop that used to be lesson 03. Kept so you can watch it fail.

Run this FIRST:

    python 03-agent-loop/naive.py

Two real bugs live in this file.

**Bug 1 — verification costs two steps.** `act()` returns "verify" as if it
were an action, but `run()` checks `state.verified` *before* calling
`execute()`, and only `execute()` can set it. So the goal is confirmed one
iteration late:

    [step 4] action=verify current=3
    [step 5] action=verify current=3
    Verified.

**Bug 2 — a reachable goal fails.** Because of bug 1, reaching `target` needs
`target + 2` steps. With the default `max_steps=10`, this is a *successful*
run reported as a failure:

    RuntimeError: step budget exhausted

Nobody notices bug 1 until bug 2 lands in production at 2am. Now run
`agent.py` next to it and diff the step counts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class State:
    target: int
    current: int = 0
    verified: bool = False


def act(state: State) -> str:
    # BUG 1: "verify" is returned as an action, so it gets an execution step.
    return "increment" if state.current < state.target else "verify"


def execute(action: str, state: State) -> None:
    if action == "increment":
        state.current += 1
    elif action == "verify":
        state.verified = state.current == state.target


def run(target: int, max_steps: int = 10) -> State:
    state = State(target=target)
    for step in range(1, max_steps + 1):
        action = act(state)
        print(f"[step {step}] action={action} current={state.current}")
        # BUG 1 visible here: verified is still False on the first pass, so the
        # check can never succeed and execute() must run a second time.
        if action == "verify" and state.verified:
            print("Verified.")
            return state
        execute(action, state)
    # BUG 2: the goal was reached, but the budget was already spent proving it.
    raise RuntimeError("step budget exhausted")


if __name__ == "__main__":
    print("--- case 1: target well inside the budget ---")
    run(3)

    print("\n--- case 2: a reachable goal that fails anyway ---")
    try:
        run(9)
    except RuntimeError as exc:
        print(f"RuntimeError: {exc}")
        print("current == target, yet the run reports failure.")
        print(f"proof it needed target+2 steps: {9 + 2}, but max_steps=10")

    print("\n--- case 3: the correct budget for this design ---")
    run(9, max_steps=11)
    print("works, but the caller had to know the +2 tax. That is the smell.")