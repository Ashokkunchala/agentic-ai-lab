"""Lesson 06: retrieval as a tool, with citations.

Grounding is the point. A retriever that returns text without a source cannot
be fact-checked, so every `Hit` here carries `[source#id]`.

Ranking is TF-IDF: `score = term_frequency * inverse_document_frequency`.
IDF is what stops the word "agent" (in almost every document) from dominating
a query. A plain substring count is the version people ship first, and it
returns the same documents for every query.

Retrieval is a *capability*, not a system. It does not make anything agentic.

Run:
    python 06-rag/agent.py
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.retrieval import Chunk, Retriever, default_retriever  # noqa: E402

DOCUMENTS = [
    Chunk(
        id="agent-loop",
        source="00-foundations/concepts.md",
        text="An agent is a system that accepts a goal, inspects state, decides an action, uses a tool, observes the result, and repeats until the goal is verified.",
    ),
    Chunk(
        id="memory",
        source="04-memory/README.md",
        text="Memory is information retained beyond one immediate turn. Separate context, working memory and persistent memory.",
    ),
    Chunk(
        id="mcp",
        source="07-mcp/mcp_concepts.md",
        text="MCP standardises interoperability between AI applications and external tools or context. MCP is not the agent runtime.",
    ),
    Chunk(
        id="policy",
        source="shared/policy.py",
        text="The policy engine gates every tool call. Deny rules win, then explicit allow, then named approval, then risk default.",
    ),
    Chunk(
        id="budget",
        source="shared/budget.py",
        text="Autonomy without limits is an outage. Check step, tool call, retry, time and cost budgets before acting.",
    ),
    Chunk(
        id="verification",
        source="10-devops-agent/runbook.md",
        text="A green command exit code is not proof that the goal succeeded. Verify user-facing behaviour.",
    ),
]


def naive_scores(query: str) -> list[tuple[str, int]]:
    """The first version everyone writes: count substring matches.

    Included so you can see why it fails.
    """
    terms = set(query.lower().split())
    rows = []
    for chunk in DOCUMENTS:
        text = chunk.text.lower()
        rows.append((chunk.id, sum(1 for term in terms if term in text)))
    return sorted(rows, key=lambda row: row[1], reverse=True)


def demo_naive_fails() -> None:
    print("=== naive ranking: substring counting ===")
    for query in ["agent memory", "memory agent"]:
        print(f"  query={query!r}")
        for chunk_id, score in naive_scores(query)[:3]:
            print(f"    {chunk_id:<14} score={score}")
    print("  the same three documents win for both word orders, and the")
    print("  documents that actually matter score 0. Substring counting cannot")
    print("  tell 'contains the word' from 'is about the word'.\n")


def demo_idf() -> None:
    print("=== TF-IDF: ranking now separates the two documents ===")
    retriever = Retriever(DOCUMENTS)
    for query in ["agent memory", "memory agent"]:
        print(f"  query={query!r}")
        for hit in retriever.search(query, limit=3):
            print(f"    {hit.chunk.id:<14} score={hit.score:.3f} terms={list(hit.matched_terms)}")
    print("  'agent' now scores lower than 'memory' because 'agent' appears in")
    print("  two documents and 'memory' is concentrated in one.\n")


def demo_rarity() -> None:
    print("=== why IDF matters ===")
    retriever = Retriever(DOCUMENTS)
    for term in ("agent", "outage", "verification"):
        seen = retriever._df.get(term, 0)
        print(f"  idf({term!r}) = {retriever.idf(term):.3f}  (appears in {seen} document(s))")
    print("  a term in every document discriminates nothing; that is why it")
    print("  must count for less than a term in exactly one.\n")


def demo_no_stemming() -> None:
    print("=== the honest limitation: exact tokens only ===")
    retriever = Retriever(DOCUMENTS)
    for query in ["budget", "budgets", "verify", "verification"]:
        hits = retriever.search(query, limit=1)
        top = hits[0].chunk.id if hits else "no match"
        print(f"  query={query!r:<16} top hit: {top}")
    print("  'budgets' does not match a query for 'budget' without stemming.")
    print("  that is what embeddings or a stemmer fix, and it is why real")
    print("  retrieval layers are more than a counting function.\n")


def demo_grounding() -> None:
    print("=== grounding: every block is cited ===")
    retriever = default_retriever()
    query = "how do I know the goal actually succeeded"
    print(f"  query: {query}")
    for block in retriever.context(query, limit=2):
        print(f"    {block}")
    print("\n  an answer built from these blocks can be traced to a file.")
    print("  a hallucinated answer cannot.\n")


def demo_no_match() -> None:
    print("=== retrieval can return nothing, and that is fine ===")
    retriever = Retriever(DOCUMENTS)
    hits = retriever.search("kubernetes hpa autoscaling", limit=3)
    print(f"  hits for an out-of-domain query: {len(hits)}")
    print("  a retriever that always returns something is lying.")
    print("  an agent must handle 'no context' rather than invent context.\n")


def demo_chunking() -> None:
    print("=== chunk granularity changes the answer ===")
    long_text = (
        "Verification is a check on observed state. "
        "It is not an action in the loop. "
        "A green command exit code is not proof that the goal succeeded."
    )
    fine = Retriever(
        [
            Chunk(id=f"f{index}", source="doc.md", text=part)
            for index, part in enumerate(long_text.split(". "))
        ]
    )
    coarse = Retriever([Chunk(id="whole", source="doc.md", text=long_text)])
    query = "green exit code"
    print(f"  fine-grained chunks  : {[h.chunk.id for h in fine.search(query)]}")
    print(f"  one coarse chunk     : {[h.chunk.id for h in coarse.search(query)]}")
    print("  fine chunks cite precisely; coarse chunks carry more context.")
    print("  choosing between them is a real engineering trade-off.\n")


if __name__ == "__main__":
    print("Retrieval lesson: rank properly, cite always, allow zero hits.\n")
    demo_naive_fails()
    demo_idf()
    demo_rarity()
    demo_no_stemming()
    demo_grounding()
    demo_no_match()
    demo_chunking()