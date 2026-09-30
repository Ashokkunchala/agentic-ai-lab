# 13 — Cloudflare Track

Cloudflare can host the edge/control plane of an agentic application.

Good fits include Workers for API/orchestration, Durable Objects for stateful coordination, Queues for asynchronous jobs, R2 for objects and D1 for application data.

A Worker is not a generic Linux VM. Keep privileged shell, Terraform, kubectl, Docker and AWS operations behind a dedicated authenticated execution boundary.