# Agentic AI Architecture

## Components

1. Goal — desired outcome.
2. State — current knowledge, plan, observations and approvals.
3. Reasoning/planning — proposes next actions.
4. Tools — external capabilities.
5. Policy — allows, blocks or gates actions.
6. Observation — tool result becomes new state.
7. Verification — checks whether the actual goal succeeded.

## Control loop

```text
Goal → Observe → Decide → Policy → Act → Verify
                 ↑                  ↓
                 └────── loop ─────┘
```

## Model vs runtime

```text
Agent Runtime
├── Model adapter (GPT/Claude/Gemini/local)
├── State + memory
├── Planner
├── Policy engine
└── Tool registry
        ├── GitHub
        ├── AWS
        ├── Terraform
        ├── Kubernetes
        └── MCP
```

Cloudflare can host the edge/control plane; privileged Terraform, kubectl, shell and AWS operations should run behind an authenticated execution boundary.
