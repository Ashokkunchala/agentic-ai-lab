# Agentic AI Lab — Command Reference

Assume you are running commands from the repository root unless a step says otherwise.

## Create an environment

### Windows PowerShell
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

### Linux / macOS / WSL
```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

## Run examples

```bash
python 01-first-agent/agent.py
python 02-tool-calling/agent.py
python 03-agent-loop/agent.py
python 04-memory/agent.py
python 05-planning/agent.py
python 06-rag/agent.py
python 07-mcp/mcp_demo.py
python 08-multi-agent/agents.py
python 09-coding-agent/agent.py
python 10-devops-agent/agent.py
python 11-autonomous-agent/agent.py
python 12-production-architecture/observability_demo.py
```

Read each lesson's README and source before running, because an example may create local output or have optional setup requirements.

## Quality checks

```bash
pytest -q
ruff check .
ruff format --check .
mypy
python scripts/check_diagrams.py
git diff --check
```

Cloudflare Worker test command:
```bash
cd 13-cloudflare
node worker.test.mjs
cd ..
```

## Safe Git workflow

```bash
git status
git switch -c practice/<short-topic>
# make a small change and add/update a test
git diff --check
git diff
pytest -q
git status
git add <specific-files>
git commit -m "learn: <topic>"
git push -u origin practice/<short-topic>
```

If you are already on a practice branch, do not create another branch unless you need to isolate the next experiment. Prefer staging explicit file names rather than `git add .`.

## Troubleshooting

| Symptom | What to check |
|---|---|
| `python` is not found | Use `py -3.11` on Windows or verify Python is on PATH. |
| Import error | Activate the intended venv, install the requirements and project, and run from the documented directory. |
| Pydantic import/API error | Run `python -m pip show pydantic`; the project expects Pydantic v2. |
| pytest reports no tests | Run from the repository root and inspect `tests/`. |
| Ruff or mypy not found | Install `requirements-dev.txt` in the active virtual environment. |
| Worker test won't start | Check `node --version` and run the command from `13-cloudflare/`. |
| Example creates files | Inspect its source and `git status` before staging; check `.gitignore`. |
| A check fails | Keep the exact failure output and reproduce it. Do not assume every environment or check is already clean. |

## Safety notes

- Use synthetic data and local fixtures.
- Do not commit `.env`, provider keys, AWS keys, kubeconfigs or tokens.
- Prefer read-only and dry-run exercises.
- Never experiment on a production account or deployment.
- HTTP 202 / “queued” means accepted, not successfully executed.
- A control described in documentation is not necessarily implemented; confirm code and tests.
