# Cloudflare Architecture

```text
Browser
  ↓
Cloudflare Worker
  ↓
Agent Orchestrator
  ↓
Durable state / Queue
  ↓
Authenticated executor
  ├── AWS
  ├── Terraform
  ├── Kubernetes
  └── GitHub
```

The control plane coordinates work; the execution plane performs privileged actions with narrow credentials and policy.