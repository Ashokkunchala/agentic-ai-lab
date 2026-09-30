from dataclasses import dataclass, field

@dataclass
class Step:
    name: str
    depends_on: list[str] = field(default_factory=list)
    completed: bool = False

def runnable(steps: dict[str, Step]) -> list[Step]:
    return [s for s in steps.values() if not s.completed and all(steps[d].completed for d in s.depends_on)]

if __name__ == "__main__":
    steps = {
        "inspect": Step("inspect"),
        "build": Step("build", ["inspect"]),
        "test": Step("test", ["build"]),
        "deploy": Step("deploy", ["test"]),
        "verify": Step("verify", ["deploy"]),
    }
    while pending := runnable(steps):
        for step in pending:
            print("running:", step.name)
            step.completed = True
