from dataclasses import dataclass


@dataclass
class State:
    target: int
    current: int = 0
    verified: bool = False


def act(state: State) -> str:
    return "increment" if state.current < state.target else "verify"


def execute(action: str, state: State) -> None:
    if action == "increment":
        state.current += 1
    elif action == "verify":
        state.verified = state.current == state.target


def run(target: int, max_steps: int = 10) -> State:
    state = State(target)
    for step in range(1, max_steps + 1):
        action = act(state)
        print(f"[step {step}] action={action} current={state.current}")
        if action == "verify" and state.verified:
            print("Verified.")
            return state
        execute(action, state)
    raise RuntimeError("step budget exhausted")


if __name__ == "__main__":
    run(3)
