"""Memory, split into the three layers that actually behave differently.

```text
working memory   -> AgentState.memory, dies with the process
persistent memory-> a JSON file, survives the process
retrieval memory  -> chunk store + ranking, lives in `retrieval.py`
```

Conflating them is the most common memory bug: an agent that keeps a growing
dict in working memory eventually pays for it in every model call.
`WorkingMemory` therefore has a hard entry cap and evicts the least recently
used entry, which is a deliberately crude but honest LRU.
"""

from __future__ import annotations

import json
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterator

DEFAULT_MEMORY_FILE = Path(__file__).with_name("memory.json")


class WorkingMemory:
    """Bounded, in-process, LRU-evicted. This is the only layer a hot loop reads."""

    def __init__(self, capacity: int = 32) -> None:
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.capacity = capacity
        self._items: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def put(self, key: str, value: Any) -> None:
        self._items[key] = (time.monotonic(), value)
        self._items.move_to_end(key)
        while len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def get(self, key: str, default: Any = None) -> Any:
        if key not in self._items:
            return default
        self._items.move_to_end(key)
        return self._items[key][1]

    def as_dict(self) -> dict[str, Any]:
        return {key: value for key, (_, value) in self._items.items()}

    def keys(self) -> list[str]:
        return list(self._items)

    def __contains__(self, key: object) -> bool:
        return key in self._items

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)


class Memory:
    """Durable key/value store, one JSON file, no database.

    Writes are atomic (temp file plus replace) so a crash mid-write cannot
    leave a half-written memory file that breaks every future run.
    """

    def __init__(self, path: str | Path = DEFAULT_MEMORY_FILE) -> None:
        self.path = Path(path)
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            self._data = {}
            return self._data
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._data = {}
            return self._data
        self._data = loaded if isinstance(loaded, dict) else {}
        return self._data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")
        temp.replace(self.path)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def delete(self, key: str) -> None:
        if key in self._data:
            del self._data[key]
            self.save()

    def keys(self) -> list[str]:
        return sorted(self._data)

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)

    def __len__(self) -> int:
        return len(self._data)


def lesson_memory(name: str, **facts: Any) -> dict[str, Any]:
    """Record that a lesson was completed. Used by the progress tracker."""
    memory = Memory()
    memory.set("last_lesson", name)
    memory.set("completed", sorted(set(memory.get("completed", [])) | {name}))
    memory.set("facts", {**memory.get("facts", {}), **facts})
    return memory.as_dict()