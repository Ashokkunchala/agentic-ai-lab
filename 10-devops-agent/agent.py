from dataclasses import dataclass

@dataclass
class Action:
    name: str
    risk: str

PLAN = [
    Action("Inspect ECS service status", "read"),
    Action("Inspect target group health", "read"),
    Action("Inspect recent task failures", "read"),
    Action("Read relevant logs", "read"),
    Action("Propose configuration change", "approval"),
    Action("Deploy change", "write"),
    Action("Verify service health", "read"),
]

if __name__ == "__main__":
    for number, action in enumerate(PLAN, 1):
        print(f"{number}. {action.name} [{action.risk}]")
