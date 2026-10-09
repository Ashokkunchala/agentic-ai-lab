from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from pydantic import BaseModel, Field

from shared.model import EchoModel
from shared.models import Goal
from shared.policy import Decision, PolicyEngine, Risk, allowed_by_default, requires_approval
from shared.tooling import DuplicateTool, Tool, ToolRegistry


class EchoInput(BaseModel):
    value: str = Field(min_length=1)


def test_policy_helpers() -> None:
    assert allowed_by_default(Risk.READ)
    assert not allowed_by_default(Risk.WRITE)
    assert requires_approval(Risk.WRITE)
    assert requires_approval(Risk.DESTRUCTIVE)


def test_policy_precedence_is_deny_then_allow_then_approval() -> None:
    policy = PolicyEngine(
        deny={"danger"},
        allow={"danger", "manual"},
        require_approval={"manual", "review"},
    )
    assert policy.evaluate("danger", Risk.READ).decision is Decision.DENY
    assert policy.evaluate("manual", Risk.DESTRUCTIVE).decision is Decision.ALLOW
    assert policy.evaluate("review", Risk.READ).decision is Decision.REQUIRE_APPROVAL
    assert policy.evaluate("unlisted", Risk.READ).decision is Decision.ALLOW
    assert policy.evaluate("unlisted", Risk.WRITE).decision is Decision.REQUIRE_APPROVAL


def test_echo_model_proposes_deterministic_finish() -> None:
    action = EchoModel().propose(Goal(objective="hello"), observations=[], tools=[])
    assert action.name == "finish"
    assert "EchoModel" in action.rationale


def test_tool_registry_validates_before_handler() -> None:
    called = False

    def handler(value: str) -> str:
        nonlocal called
        called = True
        return value

    registry = ToolRegistry()
    registry.register(Tool("echo", "echo input", EchoInput, handler))
    result = registry.get("echo").run({"value": ""})
    assert not result.success
    assert "invalid arguments" in (result.error or "")
    assert not called


def test_tool_registry_turns_handler_exception_into_result() -> None:
    def fail(value: str) -> str:
        raise RuntimeError("boom")

    registry = ToolRegistry()
    registry.register(Tool("fail", "fail safely", EchoInput, fail))
    result = registry.get("fail").run({"value": "go"})
    assert not result.success
    assert "RuntimeError: boom" in (result.error or "")


def test_tool_registry_rejects_duplicate_names() -> None:
    registry = ToolRegistry()
    registry.register(Tool("echo", "first", EchoInput, lambda value: value))
    with pytest.raises(DuplicateTool):
        registry.register(Tool("echo", "second", EchoInput, lambda value: value))


def test_config_parsers_use_defaults_on_invalid_input(monkeypatch: pytest.MonkeyPatch) -> None:
    from shared.config import env_bool, env_float, env_int, env_str

    monkeypatch.setenv("AGENTIC_TEST_INT", "not-an-int")
    monkeypatch.setenv("AGENTIC_TEST_FLOAT", "not-a-float")
    monkeypatch.setenv("AGENTIC_TEST_BOOL", "y")
    monkeypatch.setenv("AGENTIC_TEST_STR", "  value  ")
    assert env_int("AGENTIC_TEST_INT", 12) == 12
    assert env_float("AGENTIC_TEST_FLOAT", 2.5) == 2.5
    assert env_bool("AGENTIC_TEST_BOOL", False) is False
    assert env_str("AGENTIC_TEST_STR") == "value"


def test_api_key_accessor_returns_none_for_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    from shared.config import env_api_key

    monkeypatch.setenv("AGENTIC_TEST_KEY", "   ")
    assert env_api_key("AGENTIC_TEST_KEY") is None
