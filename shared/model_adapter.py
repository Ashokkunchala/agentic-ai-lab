from typing import Protocol

class ModelAdapter(Protocol):
    def complete(self, prompt: str) -> str:
        ...

class EchoModel:
    """Deterministic adapter used to learn runtime mechanics without API keys."""
    def complete(self, prompt: str) -> str:
        return f"[demo-model] {prompt}"
