def planner(goal: str) -> list[str]:
    return [f"research: {goal}", f"review: {goal}"]

def researcher(task: str) -> str:
    return f"Research completed for: {task}"

def reviewer(result: str) -> str:
    return f"Review completed for: {result}"

if __name__ == "__main__":
    plan = planner("understand agentic architecture")
    research = researcher(plan[0])
    print(reviewer(research))
