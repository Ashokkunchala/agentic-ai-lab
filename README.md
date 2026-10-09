# Agentic AI Lab

A hands-on curriculum for learning agentic AI—from deterministic agents and tool calling to memory, planning, RAG, MCP, multi-agent systems, DevOps automation, production architecture, observability, and a Cloudflare control plane.

**Start here:** follow [the one-week understanding-first practice plan](docs/DAILY-LEARNING-PLAN.md). It begins with the repository map and concepts, then guides you through the first agent, tool validation, shared runtime, and a first safe change. It is not a 30-day challenge.

## Learning path

| Module | Topic |
|---|---|
| [00 — Foundations](00-foundations/README.md) | Core concepts |
| [01 — First agent](01-first-agent/README.md) | Deterministic goal-driven loop |
| [02 — Tool calling](02-tool-calling/README.md) | Typed contracts and validation |
| [03 — Agent loop](03-agent-loop/README.md) | State, budget, policy and verification |
| [04 — Memory](04-memory/README.md) | Working and persistent memory |
| [05 — Planning](05-planning/README.md) | Dependency-aware plans |
| [06 — RAG](06-rag/README.md) | Retrieval and grounding |
| [07 — MCP](07-mcp/README.md) | Protocol and trust boundaries |
| [08 — Multi-agent](08-multi-agent/README.md) | Delegation and coordination |
| [09 — Coding agent](09-coding-agent/README.md) | Controlled repository changes |
| [10 — DevOps agent](10-devops-agent/README.md) | Operational diagnosis and safe action |
| [11 — Autonomous agent](11-autonomous-agent/README.md) | Budgets, approvals and auditability |
| [12 — Production architecture](12-production-architecture/README.md) | Security, observability and evaluation |
| [13 — Cloudflare](13-cloudflare/README.md) | Edge control plane |

## Quick start

Requires Python 3.11+. Node.js 20 is needed only for the Cloudflare Worker tests. No paid model API key is required for the introductory deterministic examples.

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python 01-first-agent\agent.py
pytest -q
```

### Linux, macOS, or WSL

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python 01-first-agent/agent.py
pytest -q
```

## Practice and reference

- [One-week understanding-first plan](docs/DAILY-LEARNING-PLAN.md)
- [Daily practice record and readiness checklist](docs/DAILY-CHECKLIST.md)
- [Command reference and troubleshooting](docs/COMMAND-REFERENCE.md)
- [Roadmap](ROADMAP.md) · [Architecture](ARCHITECTURE.md) · [File guide](FILE_GUIDE.md)

Run local checks from the repository root:

```bash
pytest -q
ruff check .
ruff format --check .
mypy
python scripts/check_diagrams.py
```

## Safety and project status

This is a learning lab and reference implementation—not a turnkey production agent platform. Use synthetic data and read-only examples while learning. Keep tools allowlisted, use least-privilege credentials, set execution budgets, and require explicit approval for write/destructive operations. Never commit model keys, cloud credentials, kubeconfigs, tokens, or production data.

The Cloudflare Worker is intended as a control plane: it validates and can enqueue work. Privileged shell, Terraform, kubectl, and AWS operations belong in a separate authenticated execution boundary. HTTP `202` means accepted, not that work completed.

## License

MIT — see [LICENSE](LICENSE).
