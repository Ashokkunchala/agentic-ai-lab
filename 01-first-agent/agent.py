from dataclasses import dataclass


@dataclass
class State:
    goal: str
    cleaned: bool = False
    organized: bool = False
    verified: bool = False


def choose_action(state: State) -> str:
    if not state.cleaned:
        return "clean"
    if not state.organized:
        return "organize"
    if not state.verified:
        return "verify"
    return "finish"


def execute(action: str, state: State) -> None:
    print(f"[tool] {action}")
    if action == "clean":
        state.cleaned = True
    elif action == "organize":
        state.organized = True
    elif action == "verify":
        state.verified = state.cleaned and state.organized


def run(goal: str) -> None:
    state = State(goal)
    for step in range(1, 6):
        action = choose_action(state)
        print(f"[step {step}] {action}")
        if action == "finish":
            print("Goal complete")
            return
        execute(action, state)
    raise RuntimeError("step budget exhausted")


if __name__ == "__main__":
    run("Prepare the workspace")
