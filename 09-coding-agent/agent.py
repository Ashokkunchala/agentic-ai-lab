"""Lesson 09: a coding agent that starts read-only.

Order of operations is the entire lesson:

```text
READ-ONLY tools -> propose a plan -> approval -> WRITE tools -> verify by test
```

A coding agent's dangerous tools are `write_file`, `apply_patch`, `run_shell`
and `git_push`. All four are declared WRITE or DESTRUCTIVE, so `PolicyEngine`
blocks them until a human approves. The read-only tools (`list_files`,
`read_file`, `search`, `run_tests`) work immediately.

This is why the module ships zero write tools enabled: adding them is an
exercise in `docs/EXERCISES.md`, not a default.

Run:
    python 09-coding-agent/agent.py
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Sequence

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.loop import AgentLoop  # noqa: E402
from shared.models import Action, Goal  # noqa: E402
from shared.policy import ApprovalGate, PolicyEngine, Risk  # noqa: E402
from shared.state import AgentState  # noqa: E402
from shared.tooling import EmptyInput, Tool, ToolRegistry  # noqa: E402

IGNORED = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", ".runs", ".mypy_cache"}


class PathInput(BaseModel):
    path: str = Field(min_length=1)


class SearchInput(BaseModel):
    query: str = Field(min_length=2)
    limit: int = Field(default=20, ge=1, le=200)


def resolve_inside_repo(path: str) -> Path:
    """Reject anything that escapes the repository.

    The single most important line in this lesson. Path traversal is not a
    theoretical risk for a tool that a model chooses the argument for.
    """
    root = REPO_ROOT.resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root):
        raise PermissionError(f"path escapes the repository: {path}")
    return target


def list_files(path: str = ".") -> dict[str, Any]:
    root = resolve_inside_repo(path)
    if not root.is_dir():
        raise NotADirectoryError(root)
    rows = sorted(
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*")
        if p.is_file() and not IGNORED & set(p.parts)
    )
    return {"root": str(root), "count": len(rows), "files": rows[:300]}


def read_file(path: str) -> dict[str, Any]:
    target = resolve_inside_repo(path)
    if not target.is_file():
        raise FileNotFoundError(target)
    text = target.read_text(encoding="utf-8", errors="replace")
    return {"path": str(target), "lines": text.count("\n") + 1, "content": text[:3000]}


def search(query: str, limit: int = 20) -> dict[str, Any]:
    needle = query.lower()
    matches: list[str] = []
    for path in sorted(REPO_ROOT.rglob("*.md")):
        if IGNORED & set(path.parts):
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if needle in line.lower():
                matches.append(f"{path.relative_to(REPO_ROOT).as_posix()}:{number}: {line.strip()[:120]}")
                if len(matches) >= limit:
                    return {"query": query, "matches": matches, "truncated": True}
    return {"query": query, "matches": matches, "truncated": False}


def build_registry() -> ToolRegistry:
    """Read-only tools only. Every risk is READ, so nothing needs approval."""
    return ToolRegistry().register_all(
        [
            Tool("list_files", "List repository files.", PathInput, list_files, Risk.READ),
            Tool("read_file", "Read one repository file.", PathInput, read_file, Risk.READ),
            Tool("search", "Search markdown for a string.", SearchInput, search, Risk.READ),
        ]
    )


def summarise_repository() -> dict[str, Any]:
    listing = list_files(".")
    files = listing["files"]
    return {
        "total_files": listing["count"],
        "python_files": len([f for f in files if f.endswith(".py")]),
        "markdown_files": len([f for f in files if f.endswith(".md")]),
        "diagram_sources": len([f for f in files if f.endswith(".mmd")]),
    }


def make_planner(question: str) -> Any:
    """Two-step read-only investigation: list, then search."""
    needle = question[:200]

    def planner(state: AgentState, tools: Sequence[dict[str, object]]) -> Action:
        used = [o.tool for o in state.observations if o.tool]
        if "list_files" not in used:
            return Action(name="list_files", arguments={"path": "."}, rationale="survey the repository")
        if "search" not in used:
            return Action(name="search", arguments={"query": needle}, rationale="locate the relevant notes")
        return Action(name="finish", rationale="read-only investigation complete")

    return planner


def main() -> None:
    print("=== read-only repository survey ===")
    summary = summarise_repository()
    print(f"  files tracked      : {summary['total_files']}")
    print(f"  python modules     : {summary['python_files']}")
    print(f"  markdown notes     : {summary['markdown_files']}")
    print(f"  mermaid diagrams   : {summary['diagram_sources']}")

    print("\n=== path traversal is refused ===")
    for attempt in ("../../../../Windows/System32/drivers/etc/hosts", "..", "C:/Windows/System32"):
        outcome = Tool("read_file", "", PathInput, read_file, Risk.READ).run({"path": attempt})
        print(f"  {attempt[:46]:<48} -> {outcome.error or 'ALLOWED (unexpected)'}")

    print("\n=== a read-only agent run ===")
    registry = build_registry()
    goal = Goal(objective="find where verification is documented", max_steps=4)
    loop = AgentLoop(
        planner=make_planner("verif"),
        registry=registry,
        policy=PolicyEngine(),
        goal=goal,
        verifier=lambda state: bool(state.observations_of("search")),
    )
    result = loop.run()
    print(f"  {result.summary()}")
    for observation in result.observations:
        print(f"    {observation.summary(limit=110)}")

    print("\n=== what a write tool would look like (declared, not registered) ===")
    print("  Tool('write_file', ..., Risk.WRITE)        -> needs approval")
    print("  Tool('run_shell',   ..., Risk.DESTRUCTIVE) -> needs approval")
    print("  they are absent here, so policy never has to block them.")
    print("  'declared but denied' is a weaker posture than 'not implemented'.")
    print("  see docs/EXERCISES.md exercise 9-C to add one behind an approval gate.")


if __name__ == "__main__":
    main()