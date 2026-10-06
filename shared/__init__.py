"""Shared agent runtime used by every lesson in this repository.

Import order matters for reading the code: config, models, policy, state,
budget, tooling, model, observability, then loop. Each module is standalone
so a lesson can read exactly one file and still learn one idea.
"""

from .budget import Budget, BudgetExhausted
from .config import load_env, model_name
from .evaluation import Case, Scorecard, score
from .loop import AgentLoop, LoopResult, Planner, Verifier
from .memory import Memory, WorkingMemory
from .model import EchoModel, ModelAdapter, ScriptedModel
from .models import Action, Goal, Observation
from .observability import JsonlLogger, Metrics, Tracer
from .planner import Plan, PlanStep, topological_order
from .policy import ApprovalGate, Decision, PolicyEngine, PolicyResult, Risk
from .retrieval import Chunk, Retriever
from .state import AgentState, Status
from .tooling import Tool, ToolRegistry, ToolResult

__all__ = [
    "Action",
    "AgentLoop",
    "AgentState",
    "ApprovalGate",
    "Budget",
    "BudgetExhausted",
    "Case",
    "Chunk",
    "Decision",
    "EchoModel",
    "Goal",
    "JsonlLogger",
    "LoopResult",
    "Memory",
    "Metrics",
    "ModelAdapter",
    "Observation",
    "Plan",
    "PlanStep",
    "Planner",
    "PolicyEngine",
    "PolicyResult",
    "Retriever",
    "Risk",
    "Scorecard",
    "ScriptedModel",
    "Status",
    "Tool",
    "ToolRegistry",
    "ToolResult",
    "Tracer",
    "Verifier",
    "WorkingMemory",
    "load_env",
    "model_name",
    "score",
    "topological_order",
]