"""Lesson 04: three memory layers that behave differently.

```text
working memory    bounded, in-process, LRU-evicted   AgentState.memory
persistent memory one JSON file, survives restarts   shared.memory.Memory
retrieval memory  chunk store + ranking              shared.retrieval.Retriever
```

The bug this lesson prevents: an agent that keeps everything in working memory
pays for it in every model call, because context grows until the request is
rejected or the answers get worse. Bounded memory with deliberate eviction is
not a limitation to work around; it is the design.

Run:
    python 04-memory/agent.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.memory import Memory, WorkingMemory  # noqa: E402
from shared.retrieval import Chunk, Retriever  # noqa: E402


def demo_working_memory() -> None:
    print("=== working memory: bounded, evicted least-recently-used ===")
    memory = WorkingMemory(capacity=3)
    for index in range(1, 6):
        memory.put(f"fact-{index}", index)
        print(f"  put fact-{index} -> keys={memory.keys()}")
    print(f"  capacity honoured: {len(memory)} <= 3")
    print(f"  fact-1 evicted: {'fact-1' not in memory}")
    print(f"  most recent survived: {memory.get('fact-5')}\n")


def demo_persistent_memory() -> None:
    print("=== persistent memory: survives a new process ===")
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "memory.json"
        first = Memory(path)
        first.set("last_lesson", "04-memory")
        first.set("facts", {"repos_opened": 3})
        print(f"  wrote {path.name}: {first.as_dict()}")

        # A brand new Memory instance stands in for a new process.
        second = Memory(path)
        print(f"  reopened: {second.as_dict()}")
        print(f"  survived restart: {second.get('last_lesson') == '04-memory'}")

        second.set("facts", {**second.get("facts", {}), "repos_opened": 4})
        print(f"  updated: {second.get('facts')}")
        second.delete("facts")
        print(f"  after delete: {second.keys()}\n")


def demo_corrupt_memory() -> None:
    print("=== persistent memory: corrupt file degrades, does not crash ===")
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "memory.json"
        path.write_text("{not json at all", encoding="utf-8")
        memory = Memory(path)
        print(f"  unreadable file -> {memory.as_dict()} (empty, run continues)")
        memory.set("recovered", True)
        print(f"  writes still work -> {memory.get('recovered')}\n")


def demo_retrieval_memory() -> None:
    print("=== retrieval memory: store is large, context is small ===")
    retriever = Retriever(
        [
            Chunk(id="c1", source="runbook.md", text="Evidence before mutation. Never apply a fix you cannot explain."),
            Chunk(id="c2", source="runbook.md", text="A green command exit code is not proof that the goal succeeded."),
            Chunk(id="c3", source="policy.md", text="Deny rules win, then explicit allow, then named approval."),
            Chunk(id="c4", source="memory.md", text="Bounded memory with deliberate eviction is the design, not a limitation."),
        ]
    )
    print(f"  stored chunks: {len(retriever)}")
    context = retriever.context("how do I know a fix worked", limit=2)
    print(f"  context blocks returned for a 7-word query: {len(context)}")
    for block in context:
        print(f"    {block}")
    print("\n  every block carries a citation, so an answer can be checked:")
    hit = retriever.search("exit code proof")[0]
    print(f"    top hit score={hit.score:.3f} terms={hit.matched_terms} cite={hit.citation()}")


def main() -> None:
    print("Memory lesson: three layers, three lifetimes, three failure modes.\n")
    demo_working_memory()
    demo_persistent_memory()
    demo_corrupt_memory()
    demo_retrieval_memory()
    print("\nrule of thumb: if it fits in one prompt, it is context, not memory.")


if __name__ == "__main__":
    main()