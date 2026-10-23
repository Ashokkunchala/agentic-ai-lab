# Learning Guide: Agentic AI from Scratch

This guide is for learning the ideas, not just running scripts. You can study at your own pace. A lesson is complete when you can explain its idea, trace it in code, and make one intentional change.

## Before you begin

You do not need machine learning experience, an API key, or a cloud account. Familiarity with basic Python helps. If Python is new to you, first practice functions, classes, dictionaries, lists, exceptions, imports, and virtual environments.

Keep a learning journal with four prompts for every lesson:

- What problem does this lesson solve?
- What data enters and leaves the main function?
- What can fail, and how is that failure represented?
- What change did I make, and what did it teach me?

## The curriculum

### 00 — Foundations

Read `00-foundations/concepts.md`. Explain the difference between a model, chatbot, agent, tool, state, memory, and MCP. Draw the agent loop from memory.

**Try:** Give an agent a simple goal, such as organizing a list. Identify its observations, possible actions, and a check that would prove it finished.

### 01 — First agent

Run `01-first-agent/agent.py`, then trace `run()`, `choose_action()`, `execute()`, and `is_done()` in that order. This example is intentionally deterministic: its purpose is to teach control flow without model unpredictability.

**Try:** Add one state field and action, such as `cleaned`. Make the agent perform it before finishing. Then reduce `max_steps` until it cannot finish and explain why.

### 02 — Tool calling

Run `02-tool-calling/agent.py`. Follow one request through the input schema, registry, validation, handler, and result. Notice that an action names a registered capability; it does not contain executable code.

**Try:** Add a read-only tool with a Pydantic input model. Try valid input, missing input, and an invalid value. Describe where each error appears.

### 03 — Agent loop

Run `03-agent-loop/agent.py` and compare it with `03-agent-loop/naive.py`. Follow one successful run and one parked or failed run through `shared/loop.py`.

**Try:** Change the target or step limit. Predict whether the run completes, exhausts its budget, or waits for approval. Check the status and stop reason.

### 04 — Memory

Run `04-memory/agent.py`. Identify which facts live in the current state, which are summarized for later decisions, and which survive beyond a run. Memory is useful only when it helps a later decision.

**Try:** Add a remembered fact and use it to change the next action. Then remove the fact and observe the difference.

### 05 — Planning

Run `05-planning/agent.py`. Look at how a broad goal becomes smaller steps and how dependencies constrain their order.

**Try:** Add a step that depends on another step. Make the dependency explicit and check that the plan does not run the dependent step too early.

### 06 — Retrieval-augmented generation

Run `06-rag/agent.py`. Separate retrieving relevant text from reasoning about that text. Retrieved content is evidence to inspect, not guaranteed truth.

**Try:** Ask a question answerable from the included material, then one that is not. Check whether the agent can say that its evidence is insufficient.

### 07 — MCP

Read `07-mcp/mcp_concepts.md` and run `07-mcp/mcp_demo.py`. Keep the agent runtime, MCP client, MCP server, and host policy distinct in your mental model.

**Try:** Draw the request and response path. Mark where authentication, tool allowlists, timeouts, and approval checks belong.

### 08 — Multi-agent systems

Run `08-multi-agent/agents.py`. Identify the benefit of specialization and the extra coordination each handoff requires.

**Try:** Compare one agent doing a task with two agents splitting it. Write down what information must cross the boundary and how you would check the combined result.

### 09 — Coding agents

Run `09-coding-agent/agent.py`. Trace repository inspection, proposed edits, and verification. A code-writing agent needs narrow tools and evidence that the requested change worked.

**Try:** Add a read-only inspection step before a proposed edit. State what evidence would be enough to approve the change.

### 10 — DevOps agents

Run `10-devops-agent/agent.py` and read `10-devops-agent/runbook.md`. The core habit is evidence before mutation: inspect the system before proposing a change.

**Try:** For one runbook action, label it read-only or mutating. Name the approval and post-change check it needs.

### 11 — Autonomous agents

Run `11-autonomous-agent/agent.py`. Study the step, time, retry, cost, approval, and rollback limits. Autonomy means the system can continue; it does not mean it should have unlimited authority.

**Try:** Lower one budget and observe how the run stops. Explain why its stop reason is useful to an operator.

### 12 — Production architecture

Read `12-production-architecture/README.md`, `architecture.md`, `security.md`, and `observability.md`. Connect each control to a concrete failure it helps detect or prevent.

**Try:** For a hypothetical agent that can edit files, identify its identity, allowed paths, approval boundary, audit events, and success check.

### 13 — Cloudflare track

Read `13-cloudflare/README.md` and `architecture.md`. Distinguish the control plane that coordinates work from the execution boundary that holds powerful credentials.

**Try:** Draw one request from browser to result. Mark what state belongs in a Durable Object or queue and which actions must stay behind an authenticated executor.

### 14 — AWS Bedrock

Read `14-aws/README.md` and run `14-aws/agent.py`. The agent loop stays local while Bedrock supplies model decisions. Compare the provider adapter with `TranscriptModel`, then trace the action through validation, policy, and verification.

**Try:** Change the goal or remove the read-only tool. Observe how the runtime reports an unverified goal, even when the model response itself is valid.

## Milestones

You are ready to move on when you can:

1. Explain the goal → state → decision → tool → observation cycle.
2. Add a typed tool and predict how invalid input is handled.
3. Explain how policy and budgets constrain a run.
4. Show how verification checks the result rather than trusting the model's claim.
5. Describe what extra failure modes memory, retrieval, MCP, delegation, and deployment introduce.

## Key terms in plain language

| Term | Meaning |
| --- | --- |
| Goal | The outcome the system is trying to achieve. |
| State | The current goal, facts, observations, and limits needed to continue. |
| Action | A structured proposal for the next step. |
| Tool | A named capability the runtime allows the agent to call. |
| Observation | The recorded result of an action or tool call. |
| Policy | Rules that allow, deny, or require approval for actions. |
| Verification | An independent check that the goal was actually met. |
| Memory | Information retained to inform later decisions. |
| RAG | Retrieval of relevant external content to ground a response. |
| MCP | A protocol for connecting AI applications with tools and context. |
