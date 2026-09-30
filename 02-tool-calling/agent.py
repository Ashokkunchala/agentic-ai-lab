from pathlib import Path
from typing import Any, Callable
from pydantic import BaseModel


class ReadFileInput(BaseModel):
    path: str


class Tool:
    def __init__(self, name: str, description: str, schema: type[BaseModel], fn: Callable[..., Any]):
        self.name = name
        self.description = description
        self.schema = schema
        self.fn = fn

    def call(self, raw_input: dict[str, Any]) -> Any:
        validated = self.schema.model_validate(raw_input)
        return self.fn(**validated.model_dump())


def read_file(path: str) -> dict[str, Any]:
    target = Path(path).resolve()
    if not target.is_file():
        raise FileNotFoundError(target)
    return {"path": str(target), "content": target.read_text(encoding="utf-8")[:4000]}


TOOLS = {
    "read_file": Tool(
        "read_file",
        "Read a text file without modifying it.",
        ReadFileInput,
        read_file,
    )
}


if __name__ == "__main__":
    result = TOOLS["read_file"].call({"path": "02-tool-calling/README.md"})
    print(result["content"])
