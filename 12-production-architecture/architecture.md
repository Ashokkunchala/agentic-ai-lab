# Production Reference Architecture

```text
Client
  ↓
API/Auth
  ↓
Agent Orchestrator
  ├── Model Adapter
  ├── State Store
  ├── Memory Store
  ├── Planner
  ├── Policy Engine
  └── Tool Registry
          ↓
   Execution Boundary
     ├── Git
     ├── Cloud APIs
     ├── Terraform
     └── Kubernetes
```

Every tool call should be authenticated, authorized, validated, observable and bounded.