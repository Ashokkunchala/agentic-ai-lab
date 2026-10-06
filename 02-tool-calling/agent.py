"""Lesson 02: a tool is a contract, not a function.

The lesson is the separation of five stages:

    propose -> registry lookup -> validate -> execute -> observe

An agent must never execute model-generated code. It executes *named,
declared, validated* tools that a human registered ahead of time. That is the
entire security model of this repository.

```python
Tool(name, description, input_model, handler, risk)
```

`input_model` is a pydantic model, so a wrong argument is a validation error
you can observe and retry, not an exception that kills the run. `risk` is what
`shared/policy.py` will gate on in lesson 03.

Run:
    python 02-tool-calling/agent.py
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.policy import Risk  # noqa: E402
from shared.tooling import EmptyInput, Tool, ToolRegistry  # noqa: E402

MAX_READ_BYTES = 4000


class ReadFileInput(BaseModel):
    """The declared contract. The handler cannot receive anything else."""

    path: str = Field(min_length=1)
    max_bytes: int = Field(default=MAX_READ_BYTES, ge=1, le=100_000)


class ListDirInput(BaseModel):
    path: str = Field(min_length=1)
    pattern: str = Field(default="*.py", min_length=1)


def read_file(path: str, max_bytes: int = MAX_READ_BYTES) -> dict[str, Any]:
    """READ risk: observes the filesystem, changes nothing."""
    target = Path(path).resolve()
    if not target.is_file():
        raise FileNotFoundError(target)
    text = target.read_text(encoding="utf-8", errors="replace")
    return {
        "path": str(target),
        "bytes": len(text.encode("utf-8")),
        "truncated": len(text) > max_bytes,
        "content": text[:max_bytes],
    }


def list_python_files(path: str, pattern: str = "*.py") -> dict[str, Any]:
    """READ risk. Note the exclusions: a tool should be safe by default."""
    root = Path(path).resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    excluded = {".git", ".venv", "venv", "__pycache__", "node_modules", ".runs"}
    found = sorted(
        str(p.relative_to(root))
        for p in root.rglob(pattern)
        if not excluded & set(p.parts)
    )
    return {"root": str(root), "count": len(found), "files": found[:200]}


def build_registry() -> ToolRegistry:
    return ToolRegistry().register_all(
        [
            Tool("read_file", "Read a UTF-8 text file. Truncates output.", ReadFileInput, read_file, Risk.READ),
            Tool("list_python_files", "List python files under a directory.", ListDirInput, list_python_files, Risk.READ),
            Tool("ping", "Liveness check with no arguments.", EmptyInput, lambda: {"pong": True}, Risk.READ),
        ]
    )


def show(label: str, result: Any) -> None:
    status = "ok" if result.success else f"error -> {result.error}"
    print(f"  {label:<34} {status}  ({result.duration_ms:.2f} ms)")


def main() -> None:
    registry = build_registry()
    print(f"registered tools: {registry.names()}")
    print(f"declared schemas:\n{registry.describe()[0]}\n")

    print("stage 3+4: validate then execute")
    show("read_file(valid)", registry.get("read_file").run({"path": "02-tool-calling/README.md"}))
    show("ping(no args)", registry.get("ping").run({}))

    print("\nvalidation errors become observations, not crashes")
    show("read_file(missing path)", registry.get("read_file").run({}))
    show("read_file(empty path)", registry.get("read_file").run({"path": ""}))
    show("read_file(nonexistent)", registry.get("read_file").run({"path": "does/not/exist.txt"}))
    show("read_file(bad max_bytes)", registry.get("read_file").run({"path": "README.md", "max_bytes": -5}))

    print("\nunknown tool names fail loudly at the registry boundary")
    try:
        registry.get("delete_everything")
    except KeyError as exc:
        print(f"  registry.get('delete_everything') -> {exc}")

    print("\nrisk is declared, not inferred")
    for item in registry.describe():
        print(f"  {item['name']:<20} risk={item['risk']}")


if __name__ == "__main__":
    main()