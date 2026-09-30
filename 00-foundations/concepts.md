# Concepts

## LLM
A probabilistic model that generates tokens. By itself it does not have terminal, filesystem, AWS or GitHub access.

## Chatbot
A conversational interface around a model. It may never take external actions.

## Agent
A system that can accept a goal, inspect state, decide an action, use a tool, observe the result, and repeat or finish.

## Coding agent
An agent specialized for repository inspection, edits, tests and Git workflows.

## Autonomous agent
An agent allowed to continue across multiple steps without the user selecting every action. Production autonomy should be bounded by policy, budgets and approvals.

## Tool
A typed capability exposed to the agent.

## State
Information required to continue correctly: goal, plan, observations, pending actions, approvals, budgets and errors.

## Memory
Information retained beyond one immediate model turn.

## MCP
An interoperability protocol for connecting AI applications to tools and context. MCP is not the agent runtime.

```text
Model   = intelligence engine
Agent   = goal + model + state + tools + loop
MCP     = integration protocol
```
