"""Validate every Mermaid source in assets/diagrams.

This is not a Mermaid parser. It is a cheap structural gate that catches the
mistakes that actually happen when hand-editing diagrams: an unknown diagram
type, unbalanced brackets, a tab character, or an empty file.

A real parse needs `npx @mermaid-js/mermaid-cli`; see docs/DIAGRAMS.md. This
script runs in CI with no dependencies so a broken diagram fails the build
rather than the reader.

    python scripts/check_diagrams.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DIAGRAM_DIR = REPO_ROOT / "assets" / "diagrams"

DECLARATIONS = (
    "flowchart",
    "graph",
    "sequenceDiagram",
    "stateDiagram-v2",
    "classDiagram",
    "erDiagram",
    "gantt",
    "pie",
    "journey",
    "mindmap",
    "timeline",
    "quadrantChart",
    "xychart-beta",
    "requirementDiagram",
    "gitGraph",
    "sankey-beta",
)

OPENERS = {"[": "]", "(": ")", "{": "}", '"': '"'}
ALLOWED_TABS = 0


def check(path: Path) -> list[str]:
    problems: list[str] = []
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    body = [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("%%")
    ]
    if not body:
        return ["file is empty or contains only comments"]

    first = body[0]
    if not any(first.startswith(decl) for decl in DECLARATIONS):
        problems.append(f"line 1 does not declare a diagram type (got {first[:40]!r})")

    if "\t" in raw:
        problems.append("contains a tab character; use spaces")

    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("%%"):
            continue
        depth = 0
        for char in stripped:
            if char in "[({":
                depth += 1
            elif char in "])}":
                depth -= 1
        if depth < 0:
            problems.append(f"line {number}: closing bracket without an opening one")
            break
        if depth > 0 and stripped.endswith(("]", ")", "}")) is False and number == len(lines):
            pass

    if raw.count("[") != raw.count("]"):
        problems.append(f"unbalanced square brackets ({raw.count('[')} open, {raw.count(']')} close)")
    if raw.count('"') % 2 != 0:
        problems.append("odd number of double quotes, a label is probably unterminated")

    ids = set(re.findall(r"^\s*([A-Za-z][A-Za-z0-9_]*)[\(\[\{]", raw, re.MULTILINE))
    if len(raw.splitlines()) < 8 and "quadrantChart" not in first and "xychart-beta" not in first and "pie" not in first:
        problems.append("suspiciously short for a diagram; did you truncate it?")

    return problems


def main() -> int:
    if not DIAGRAM_DIR.exists():
        print(f"missing diagram directory: {DIAGRAM_DIR}")
        return 1

    files = sorted(DIAGRAM_DIR.glob("*.mmd"))
    if not files:
        print("no .mmd files found")
        return 1

    failures = 0
    for path in files:
        problems = check(path)
        if problems:
            failures += 1
            print(f"FAIL  {path.name}")
            for problem in problems:
                print(f"        {problem}")
        else:
            declared = path.read_text(encoding="utf-8").splitlines()[0].strip()
            print(f"PASS  {path.name:<34} {declared}")

    print(f"\n{len(files) - failures}/{len(files)} diagram sources valid")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())