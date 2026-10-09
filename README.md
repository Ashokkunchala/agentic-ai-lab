# Agentic AI Lab

A hands-on curriculum for learning agentic AI—from deterministic agents and tool calling to memory, planning, RAG, MCP, multi-agent systems, DevOps automation, production architecture, observability, and a Cloudflare control plane.

The project is intentionally runnable without a paid model API. Start with the small deterministic lessons, then study how shared runtime components add validation, bounded loops, policy gates, and auditability.

## Learning path

| Module | Topic | What you'll learn |
|---|---|---|
| [00 — Foundations](00-foundations/README.md) | Core concepts | Goals, state, tools, observations, policy and verification |
| [01 — First agent](01-first-agent/README.md) | Agent basics | A minimal deterministic goal-driven loop |
| [02 — Tool calling](02-tool-calling/README.md) | Tool contracts | Typed input, validation, registries and error handling |
| [03 — Agent loop](03-agent-loop/README.md) | Runtime | Bounded execution, policy and terminal verification |
| [04 — Memory](04-memory/README.md) | Memory | Working and persistent state |
| [05 — Planning](05-planning/README.md) | Planning | Decomposition and dependency-aware steps |
| [06 — RAG](06-rag/README.md) | Retrieval | Grounded answers, chunking and retrieval |
| [07 — MCP](07-mcp/README.md) | Model Context Protocol | Tools, resources, clients and trust boundaries |
| [08 — Multi-agent](08-multi-agent/README.md) | Collaboration | Delegation and coordination trade-offs |
| [09 — Coding agent](09-coding-agent/README.md) | Repository changes | Controlled edits and verification |
| [10 — DevOps agent](10-devops-agent/README.md) | Operations | Safe automation for infrastructure workflows |
| [11 — Autonomous agent](11-autonomous-agent/README.md) | Autonomy controls | Budgets, approval gates and audit trails |
| [12 — Production architecture](12-production-architecture/README.md) | Operations & safety | Security, observability and evaluation |
| [13 — Cloudflare](13-cloudflare/README.md) | Edge control plane | Validate and queue work without executing privileged commands in a Worker |

See [ROADMAP.md](ROADMAP.md), [ARCHITECTURE.md](ARCHITECTURE.md), [FILE_GUIDE.md](FILE_GUIDE.md), and the [lesson diagrams](assets/diagrams/).

## Quick start

Requirements: Python 3.11+ and Node.js 18+ only for the Cloudflare Worker lesson. Python lessons run locally and use a deterministic demo model by default.

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python 01-first-agent\agent.py
python 03-agent-loop\agent.py
pytest -q
```

### Linux, macOS, or WSL

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python 01-first-agent/agent.py
python 03-agent-loop/agent.py
pytest -q
```

Run the dependency-free Cloudflare Worker tests from the lesson directory:

```bash
cd 13-cloudflare
node worker.test.mjs
```

## Configuration

Copy `.env.example` to `.env` only when you need custom settings. The default curriculum does not need provider credentials.

| Variable | Purpose | Default |
|---|---|---|
| `AGENT_MODEL_NAME` | Selected model adapter name | `echo` |
| `AGENT_MAX_STEPS` | Default step budget | `8` |
| `AGENT_REQUIRE_APPROVAL` | Require a human decision for risky actions | `true` |
| `AGENT_SHARED_SECRET` | Optional secret for the Cloudflare lesson | unset |

Do not commit `.env`, model keys, cloud credentials, access tokens, kubeconfigs, or production data. Keep secrets in the deployment platform's secret manager.

## Development checks

```bash
ruff check .
ruff format --check .
mypy
pytest -q
python scripts/check_diagrams.py
```

The GitHub Actions pipeline runs linting, formatting checks, type checks, tests, diagram validation, and a lightweight committed-secret pattern scan on supported Python versions.

## Safety model and production status

This repository is a learning lab and reference implementation—not a turnkey production agent platform. Before connecting a real model, cloud account, cluster, or deployment system, review [the security notes](12-production-architecture/security.md) and [the DevOps runbook](10-devops-agent/runbook.md). Keep tools allowlisted, use least-privilege credentials, start in dry-run mode, set execution budgets and timeouts, require human approval for write/destructive operations, and log enough metadata to audit decisions without logging secrets.

The Cloudflare Worker is designed as a control plane: it validates and authorizes requests and can enqueue them. Privileged commands belong in a separate authenticated executor. A successful `202` response means a request was accepted, not that the job ran or succeeded.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Start with one lesson, add or update tests, and keep examples deterministic wherever possible.

## License

MIT — see [LICENSE](LICENSE).
