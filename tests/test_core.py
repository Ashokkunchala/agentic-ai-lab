import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.model_adapter import EchoModel
from shared.policy import Risk, allowed_by_default, requires_approval
from shared.tooling import Tool, ToolRegistry


def test_policy():
    assert allowed_by_default(Risk.READ)
    assert requires_approval(Risk.WRITE)
    assert requires_approval(Risk.DESTRUCTIVE)


def test_model_adapter():
    assert "demo-model" in EchoModel().complete("hello")


def test_tool_registry():
    registry = ToolRegistry()
    registry.register(Tool("echo", "echo input", lambda value: value))
    assert registry.get("echo").run(value="ok").output == "ok"
