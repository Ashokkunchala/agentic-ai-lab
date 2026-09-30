DOCUMENTS = {
    "agent.md": "An agent pursues a goal using state, tools, observations, and a control loop.",
    "memory.md": "Memory stores information the runtime can reuse beyond the immediate turn.",
    "mcp.md": "MCP standardizes interoperability between AI applications and external tools/context.",
}

def retrieve(query: str, limit: int = 2):
    terms = set(query.lower().split())
    scored = []
    for name, text in DOCUMENTS.items():
        score = sum(term in text.lower() for term in terms)
        scored.append((name, score, text))
    return sorted(scored, key=lambda item: item[1], reverse=True)[:limit]

if __name__ == "__main__":
    for name, score, text in retrieve("agent tools memory"):
        print(f"{name}: score={score}\n{text}\n")
