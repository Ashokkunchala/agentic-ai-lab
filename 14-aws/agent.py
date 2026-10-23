"""Lesson 14: keep the agent local while using Amazon Bedrock as its model."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.bedrock import BedrockModel  # noqa: E402
from shared.config import env_int, env_str  # noqa: E402
from shared.loop import AgentLoop  # noqa: E402
from shared.models import Action, Goal  # noqa: E402
from shared.policy import PolicyEngine  # noqa: E402
from shared.state import AgentState  # noqa: E402
from shared.tooling import EmptyInput, Tool, ToolRegistry  # noqa: E402


def read_project_facts() -> dict[str, object]:
    """A bounded, read-only tool so the lesson has a safe action to choose."""
    return {
        "lessons": "foundations through production architecture",
        "runtime": "goal, typed tools, policy, bounded loop, observations, verification",
        "safety": "the model proposes actions; the host validates and executes them",
    }


def build_registry() -> ToolRegistry:
    return ToolRegistry().register_all(
        [
            Tool(
                "read_project_facts",
                "Read a short, fixed summary of this agent lab. This tool has no side effects.",
                EmptyInput,
                read_project_facts,
            )
        ]
    )


def verified(state: AgentState) -> bool:
    return any(
        observation.success and observation.tool == "read_project_facts"
        for observation in state.observations
    )


def main() -> int:
    region = env_str("AWS_REGION", "us-east-1")
    model_id = env_str("BEDROCK_MODEL_ID", "amazon.nova-micro-v1:0")
    max_tokens = env_int("BEDROCK_MAX_TOKENS", 256)

    try:
        model = BedrockModel(model_id=model_id, region_name=region, max_tokens=max_tokens)
    except (ImportError, RuntimeError, ValueError) as exc:
        print(f"Bedrock setup error: {exc}", file=sys.stderr)
        return 2

    goal = Goal(
        objective="Read the project facts with the available tool, then finish.",
        success_criteria=["read_project_facts was observed successfully"],
        max_steps=4,
    )
    registry = build_registry()

    def planner(state: AgentState, tools: Sequence[dict[str, object]]) -> Action:
        return model.propose(state.goal, state.observations, tools)

    result = AgentLoop(
        planner=planner,
        registry=registry,
        policy=PolicyEngine(),
        goal=goal,
        verifier=verified,
    ).run()

    print(f"model: {model_id} ({region})")
    print(result.summary())
    for observation in result.observations:
        print(f"  {observation.summary()}")
    print(f"verified: {result.ok}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
