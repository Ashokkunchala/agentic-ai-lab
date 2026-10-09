# Agentic AI Lab — Understand First, Then Practise in One Week

This is an **understanding-first guide**, not a 30-day challenge. Spend the first part of the week building a mental model of the repository. Begin modifying code only after you can explain the core concepts and how the modules connect.

**Recommended time:** 60–90 minutes per day  
**Goal for the week:** Understand the project architecture, run the main examples, make one small safe improvement, and explain how you verified it. This is an introduction—not a claim that you have mastered production agent engineering in seven days.

## How to study each day

Use the same four-step rhythm:
1. **Understand (20–30 min):** read the named files slowly; define unfamiliar terms.
2. **Trace (15 min):** follow one request or action through the code. Write the file/function names in order.
3. **Try (20–30 min):** run the example or test. Avoid live credentials and production systems.
4. **Recall (10 min):** close the files and explain what you learned in your own words.

Do not start by editing many files. First ask: What is this component for? What calls it? What can it change? How do I know it worked?

## Before Day 1: Prepare your environment

Repository: https://github.com/Ashokkunchala/agentic-ai-lab

### Windows PowerShell
```powershell
git clone https://github.com/Ashokkunchala/agentic-ai-lab.git
cd agentic-ai-lab
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python --version
pytest -q
```

### Linux / macOS / WSL
```bash
git clone https://github.com/Ashokkunchala/agentic-ai-lab.git
cd agentic-ai-lab
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python --version
pytest -q
```

If the repo is already cloned, don't clone it again. Check `git status` first and don't overwrite existing changes. You do not need paid model API keys for the introductory deterministic examples.

## Day 1 — Learn what the repository contains

**Purpose:** Build a map before diving into source code.

**Read in this order:**
1. `README.md` — what the project teaches.
2. `ROADMAP.md` — the learning sequence.
3. `FILE_GUIDE.md` — where things are.
4. `ARCHITECTURE.md` — the runtime components.
5. `00-foundations/README.md` and `00-foundations/concepts.md`.

**Understand these words:** LLM, chatbot, agent, goal, state, tool, observation, policy, verification, memory, MCP, RAG, autonomy.

**Practical task:** Draw this flow on paper:
```text
Goal
  ↓
Observe current state
  ↓
Decide on one action
  ↓
Policy gate / approval
  ↓
Execute an allowlisted tool
  ↓
Record observation
  ↓
Verify goal ── not complete → continue within budget
```

**Answer in your own words:**
- What is the difference between a model and an agent?
- Why is a tool registry safer than executing arbitrary model-generated code?
- Why can an agent say “finished” but still fail verification?
- Which folders are lessons and which files are shared runtime components?

**Done when:** You can explain the flow without reading aloud from the README.

## Day 2 — Run one small agent, understand each step

**Read:** `01-first-agent/README.md`, then `01-first-agent/agent.py`.

**Run from repo root:**
```bash
python 01-first-agent/agent.py
```

**Follow:** goal → state → choose action → execute → verify → finish.

Before running, predict the output. After running, compare your prediction with the actual output.

**Practice without editing:** Write down what would happen if:
- one state flag never becomes true;
- the step budget is too low;
- action selection returns an unexpected action.

Only after you can explain the source, make one small local change—such as adding a harmless preparation step—and run it again. Keep the experiment on a practice branch.

**Done when:** You can explain the purpose of state and the reason the loop must be bounded.

## Day 3 — Understand tools, validation, and policy

**Read:** `02-tool-calling/README.md`, `02-tool-calling/agent.py`, `shared/tooling.py`, `shared/policy.py`.

**Run:**
```bash
python 02-tool-calling/agent.py
```

**Trace the tool contract:**
1. Tool name and description.
2. Input schema.
3. Registry lookup.
4. Input validation.
5. Risk decision and approval, where used.
6. Handler execution.
7. Structured success/error result.

Understand the risks:
- **READ:** observe only.
- **WRITE:** changes state; requires a deliberate approval policy.
- **DESTRUCTIVE:** can cause irreversible or broad impact; requires stricter safeguards.

**Practice:** Find where invalid input is rejected. Follow the error into the returned result. Add no cloud or shell capabilities at this stage.

**Questions:** What happens if the handler raises an exception? Why should duplicate tool names be rejected? Why should a write action not run when no approver is configured?

**Done when:** You can trace a tool call and point out where it can be blocked before it causes an effect.

## Day 4 — Understand the shared runtime

**Read in this order:**
1. `shared/models.py` — schemas for goals, actions and observations.
2. `shared/state.py` — state/status transitions.
3. `shared/budget.py` — execution limits.
4. `shared/model.py` — model adapter boundary and deterministic/scripted models.
5. `shared/loop.py` — how the pieces are composed.
6. `shared/observability.py` — logs, metrics and traces.

**Run:**
```bash
python 03-agent-loop/agent.py
pytest -q
```

**Trace one run:** Start at the lesson's entry point, find the planner/model, follow the proposed action into the loop, locate the policy decision, then see how the result is added to state and how completion is verified.

**Create a small diagram** showing the responsibilities of the model adapter, state, budget, policy, tool registry, verifier, and logger.

**Understand:** A model proposes; the runtime controls. A tool result is evidence, not proof of goal completion. Budgets limit runaway behavior.

**Done when:** You can explain what decides success versus failure, and name two different ways a run can stop safely.

## Day 5 — Tour the remaining learning tracks

Today is for understanding the map, not mastering every topic.

| Track | Read | Main question |
|---|---|---|
| Memory | `04-memory/README.md`, `shared/memory.py` | What is retained, for how long, and why? |
| Planning | `05-planning/README.md`, `shared/planner.py` | How are tasks divided and dependencies respected? |
| RAG | `06-rag/README.md`, `shared/retrieval.py` | What evidence was retrieved for an answer? |
| MCP | `07-mcp/README.md`, `07-mcp/mcp_concepts.md` | Where does the client/server boundary sit? |
| Multi-agent | `08-multi-agent/README.md` | Is delegation worth its coordination cost? |
| Coding agent | `09-coding-agent/README.md` | How are repository edits inspected and verified? |
| DevOps agent | `10-devops-agent/README.md`, `runbook.md` | What evidence should come before a change? |
| Bounded autonomy | `11-autonomous-agent/README.md` | Which budgets and approvals limit the run? |
| Production | `12-production-architecture/README.md`, `security.md`, `observability.md` | What additional controls are needed before deployment? |
| Cloudflare | `13-cloudflare/README.md`, `worker.js` | Why is the Worker a control plane, not a privileged execution host? |

For each track, write just **one sentence** describing its purpose and one question you still have. Don't try to read all implementation details today.

**Done when:** You can describe how each track extends the same core agent pattern.

## Day 6 — First guided hands-on practice

Choose **one** focus based on what was hardest:
- Tool validation and error handling.
- Policy and approval flow.
- Step budgets and verification.
- Memory or retrieval behavior.

**Procedure:**
1. Create a practice branch: `git switch -c practice/first-safe-change` (only if you are not already on your own practice branch).
2. Read the chosen implementation and current tests.
3. Write down the expected behavior before changing code.
4. Make one small change.
5. Add or update a test proving the behavior.
6. Run the relevant example and `pytest -q`.
7. Review the diff with `git diff --check` and `git diff`.

**Recommended first change:** Add a unit test for an existing safety guarantee—for example, that invalid tool input never reaches the handler or a denied tool is not executed. A test is a safer first task than adding new powerful capabilities.

Don't connect exercises to AWS, Kubernetes, Terraform, GitHub write scopes, or production services. Use synthetic fixtures and read-only examples only.

**Done when:** The test fails if the guarantee is removed, passes when the implementation is correct, and you can explain why.

## Day 7 — Review and make a learning plan

**Review without opening source first:**
- Explain an agent and its core loop.
- Draw the runtime architecture.
- Explain tool schema validation.
- Explain the difference between policy, approval, and verification.
- Describe how budgets prevent an unbounded run.
- Explain what MCP adds and what it does not add.
- Explain why logs must avoid secrets and sensitive payloads.

Then rerun the checks:
```bash
pytest -q
ruff check .
ruff format --check .
mypy
python scripts/check_diagrams.py
```

If a check fails, capture its exact error and investigate before assuming the project is healthy. Some checks may expose pre-existing issues or depend on your environment.

**Write a one-page summary:**
- The three concepts I now understand.
- The part of the architecture I can explain.
- The part I still find confusing.
- One tested improvement I made.
- Three topics I want to study next.

### Choose your next week's focus

Pick a single track based on your goal:
- **Agent fundamentals:** loop, state, memory, planning, retrieval.
- **AI application integration:** tool calling, MCP, model adapters, RAG.
- **DevOps agent safety:** coding agent, runbooks, policies, budgets, verification.
- **Production engineering:** observability, evaluation, security, CI, Cloudflare control-plane boundaries.

Repeat the weekly routine with a deeper implementation exercise in that track. Seven days is an orientation and a foundation—not proof that a system is ready for production.

## Reusable daily checklist

- [ ] I read the named files and looked up unfamiliar terms.
- [ ] I ran the example or tests from the documented directory.
- [ ] I traced one execution path through code.
- [ ] I explained what can fail and how the failure is handled.
- [ ] I changed code only after I understood its current behavior.
- [ ] I tested one behavior or boundary.
- [ ] I wrote a short summary and remaining question.
- [ ] I kept secrets and production resources out of the exercise.
