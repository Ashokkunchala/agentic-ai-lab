"""Observability with the standard library only.

Three signals, three shapes, one rule: **every event carries `run_id` and
`step`**, otherwise you cannot reconstruct a run after the fact.

* Logs answer "what happened, in order". Append-only JSONL.
* Metrics answer "is the system healthy". Counters and timers, no per-event rows.
* Traces answer "where did the time go, and what caused what". Nested spans
  with parent ids.

There is no dependency here on purpose. A logging library would be fine in
production; the point of the lesson is the *shape* of the data.
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from .config import RUNS_DIR


def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class JsonlLogger:
    """Append-only structured logger. Never raises; logging must not break a run."""

    def __init__(self, path: str | Path | None = None, *, echo: bool = False) -> None:
        self.path = Path(path) if path else None
        self.echo = echo
        self.records: list[dict[str, Any]] = []
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: str, **fields: Any) -> dict[str, Any]:
        record = {
            "ts": round(time.time(), 3),
            "event": event,
            **fields,
        }
        self.records.append(record)
        if self.echo:
            print(json.dumps(record, default=str))
        if self.path:
            try:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, default=str) + "\n")
            except OSError:
                pass
        return record

    def of_run(self, run_id: str) -> list[dict[str, Any]]:
        return [r for r in self.records if r.get("run_id") == run_id]


@dataclass
class Metrics:
    """Counters plus timing aggregates. Deliberately not a time-series database."""

    counters: dict[str, int] = field(default_factory=dict)
    timers_ms: dict[str, list[float]] = field(default_factory=dict)

    def increment(self, name: str, by: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + by

    def record_ms(self, name: str, value: float) -> None:
        self.timers_ms.setdefault(name, []).append(value)

    def success_rate(self) -> float:
        ok = self.counters.get("tool.success", 0)
        failed = self.counters.get("tool.failure", 0)
        total = ok + failed
        return round(ok / total, 4) if total else 1.0

    def p95_ms(self, name: str) -> float:
        """Nearest-rank p95. Fine for a handful of samples; swap for a real
        histogram when sample counts grow."""
        values = sorted(self.timers_ms.get(name, []))
        if not values:
            return 0.0
        index = min(len(values) - 1, int(0.95 * len(values)))
        return round(values[index], 3)

    def snapshot(self) -> dict[str, Any]:
        return {
            "counters": dict(sorted(self.counters.items())),
            "timers_ms_mean": {
                name: round(sum(values) / len(values), 3)
                for name, values in sorted(self.timers_ms.items())
                if values
            },
            "timers_ms_p95": {name: self.p95_ms(name) for name in sorted(self.timers_ms)},
            "tool_success_rate": self.success_rate(),
        }


@dataclass
class Span:
    span_id: str
    parent_id: str | None
    name: str
    run_id: str
    step: int
    started_at: float = field(default_factory=time.monotonic)
    duration_ms: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "run_id": self.run_id,
            "step": self.step,
            "duration_ms": None if self.duration_ms is None else round(self.duration_ms, 3),
            "error_type": self.error_type,
            "attributes": self.attributes,
        }


class Tracer:
    """In-memory span tree plus an exporter callback."""

    def __init__(self, exporter: Any = None) -> None:
        self.spans: list[Span] = []
        self.exporter = exporter
        self._stack: list[str] = []

    @contextmanager
    def span(
        self,
        name: str,
        run_id: str,
        step: int,
        **attributes: Any,
    ) -> Iterator[Span]:
        current = Span(
            span_id=f"sp_{len(self.spans):04d}",
            parent_id=self._stack[-1] if self._stack else None,
            name=name,
            run_id=run_id,
            step=step,
            attributes=attributes,
        )
        self.spans.append(current)
        self._stack.append(current.span_id)
        try:
            yield current
        except Exception as exc:  # noqa: BLE001 - record then re-raise
            current.error_type = type(exc).__name__
            raise
        finally:
            current.duration_ms = (time.monotonic() - current.started_at) * 1000
            self._stack.pop()
            if self.exporter:
                self.exporter(current.as_dict())

    def run_trace(self, run_id: str) -> list[dict[str, Any]]:
        return [s.as_dict() for s in self.spans if s.run_id == run_id]


def run_log_path(run_id: str, directory: str | Path | None = None) -> Path:
    base = Path(directory) if directory else RUNS_DIR
    return base / f"{run_id}.jsonl"