"""Retrieval as a tool, with citations.

Two things separate a useful retriever from a word-search:

* **Ranking** — IDF weighting stops a common term from dominating every score.
  `score = tf * idf`, summed over query terms.
* **Grounding** — every hit carries the chunk id it came from. If the runtime
  cannot point at a source, it cannot be audited or fact-checked.

This is the smallest thing that teaches the lesson. Production retrieval adds
embeddings, hybrid search, reranking and a vector store; `docs/FILES.md` maps
each of those to the line it would replace.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence

TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    source: str = "inline"
    metadata: dict[str, str] | None = None

    def as_dict(self) -> dict[str, object]:
        return {"id": self.id, "text": self.text, "source": self.source, "metadata": self.metadata or {}}


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float
    matched_terms: tuple[str, ...]

    def citation(self) -> str:
        return f"[{self.chunk.source}#{self.chunk.id}]"

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.chunk.id,
            "score": round(self.score, 4),
            "citation": self.citation(),
            "matched_terms": list(self.matched_terms),
            "text": self.chunk.text,
        }


class Retriever:
    """In-memory TF-IDF retriever over a fixed chunk set.

    `index()` is rebuilt on every mutation, which is fine for hundreds of
    chunks and wrong for millions. That trade is documented rather than hidden.
    """

    def __init__(self, chunks: Iterable[Chunk] | None = None) -> None:
        self.chunks: list[Chunk] = list(chunks or [])
        self._tokens: list[Counter[str]] = []
        self._df: Counter[str] = Counter()
        self.index()

    def add(self, chunk: Chunk) -> None:
        if any(c.id == chunk.id for c in self.chunks):
            raise ValueError(f"duplicate chunk id: {chunk.id}")
        self.chunks.append(chunk)
        self.index()

    def index(self) -> None:
        self._tokens = [Counter(tokenize(chunk.text)) for chunk in self.chunks]
        self._df = Counter()
        for counts in self._tokens:
            self._df.update(counts.keys())

    def idf(self, term: str) -> float:
        total = len(self.chunks) or 1
        seen = self._df.get(term, 0)
        return math.log((total + 1) / (seen + 1)) + 1.0

    def search(self, query: str, limit: int = 3, min_score: float = 0.0) -> list[Hit]:
        terms = set(tokenize(query))
        hits: list[Hit] = []
        for chunk, counts in zip(self.chunks, self._tokens):
            matched = terms & counts.keys()
            if not matched:
                continue
            score = sum(counts[t] * self.idf(t) for t in matched)
            if score <= min_score:
                continue
            hits.append(Hit(chunk=chunk, score=score, matched_terms=tuple(sorted(matched))))
        hits.sort(key=lambda hit: (-hit.score, hit.chunk.id))
        return hits[:limit]

    def context(self, query: str, limit: int = 3, width: int = 240) -> list[str]:
        """Grounded context blocks, each carrying its citation.

        Returned as plain strings so the caller can drop them straight into a
        prompt. The citation tag is what makes the answer checkable later.
        """
        blocks: list[str] = []
        for hit in self.search(query, limit=limit):
            text = hit.chunk.text if len(hit.chunk.text) <= width else hit.chunk.text[: width - 1] + "…"
            blocks.append(f"{hit.citation()} {text}")
        return blocks

    def __len__(self) -> int:
        return len(self.chunks)


DEFAULT_CHUNKS: Sequence[Chunk] = (
    Chunk(
        id="agent-loop",
        source="00-foundations/concepts.md",
        text=(
            "An agent is a system that accepts a goal, inspects state, decides an action, "
            "uses a tool, observes the result, and repeats until the goal is verified."
        ),
    ),
    Chunk(
        id="verification",
        source="03-agent-loop/README.md",
        text=(
            "Verification is a check on observed state, not an action in the loop. "
            "A green command exit code is not proof that the goal succeeded."
        ),
    ),
    Chunk(
        id="policy",
        source="shared/policy.py",
        text=(
            "The policy engine gates every tool call. Deny rules win, then explicit allow, "
            "then named approval, then the declared risk default for read versus write."
        ),
    ),
    Chunk(
        id="budget",
        source="shared/budget.py",
        text=(
            "Budgets bound autonomy: maximum steps, tool calls, retries, wall-clock seconds "
            "and cost. Limits are checked before the action that would consume them."
        ),
    ),
    Chunk(
        id="mcp",
        source="07-mcp/mcp_concepts.md",
        text=(
            "MCP standardises the connection between an AI application and external tools "
            "or context. It is an interoperability layer, not the agent runtime."
        ),
    ),
    Chunk(
        id="grounding",
        source="06-rag/README.md",
        text=(
            "Retrieval supplies external context to a model. Retrieval is a capability; "
            "it does not by itself make a system agentic."
        ),
    ),
)


def default_retriever() -> Retriever:
    return Retriever(DEFAULT_CHUNKS)