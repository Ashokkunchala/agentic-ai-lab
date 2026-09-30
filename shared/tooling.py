from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: str | None = None

@dataclass
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]

    def run(self, **kwargs: Any) -> ToolResult:
        try:
            return ToolResult(success=True, output=self.handler(**kwargs))
        except Exception as exc:
            return ToolResult(success=False, error=f"{type(exc).__name__}: {exc}")

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools)
