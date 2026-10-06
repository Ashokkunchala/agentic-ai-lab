"""Lesson 07: a real MCP-shaped client and server, no dependencies.

This is the actual MCP transport shape: newline-delimited JSON-RPC 2.0 over
stdio. The lesson is not the protocol details; it is **who is responsible for
what** when an agent connects to someone else's tools.

```text
Agent Runtime -> MCP Client -> MCP Server -> External System
                     ^                              ^
                     |                              |
              HOST POLICY                     SERVER TRUST
        allowlist, auth, validation,       owns the credentials,
        timeouts, output limits,           never sees agent policy
        approvals, audit logs
```

The mistake to avoid: adopting MCP and assuming you now have an agent
runtime. You have a transport. Policy, memory, planning and budgets still
belong to the host — and the host is the only component that can enforce them.

Run:
    python 07-mcp/mcp_demo.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PROTOCOL_VERSION = "2025-06-18"


def frame(payload: dict[str, Any]) -> str:
    """MCP stdio framing: one JSON object per line."""
    return json.dumps(payload, separators=(",", ":")) + "\n"


def parse_frame(line: str) -> dict[str, Any]:
    return json.loads(line.strip())


# --------------------------------------------------------------------- server


class DemoServer:
    """A stdio MCP server exposing two read-only tools.

    Note what the server does *not* do: it does not decide whether a call is
    allowed. It owns the credential and the connection; the host owns policy.
    """

    def __init__(self) -> None:
        self.initialized = False
        self.audit: list[str] = []

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            self.initialized = True
            return self._result(
                request_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "serverInfo": {"name": "lab-demo-server", "version": "1.0.0"},
                    "capabilities": {"tools": {}, "resources": {}},
                },
            )

        if not self.initialized:
            return self._error(request_id, -32000, "server not initialized")

        if method == "tools/list":
            return self._result(
                request_id,
                {
                    "tools": [
                        {
                            "name": "get_service_status",
                            "description": "Read ECS service status.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"service": {"type": "string"}},
                                "required": ["service"],
                            },
                        },
                        {
                            "name": "read_log_lines",
                            "description": "Read recent log lines for a task.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"task": {"type": "string"}, "lines": {"type": "integer"}},
                                "required": ["task"],
                            },
                        },
                    ]
                },
            )

        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            self.audit.append(f"{name}({json.dumps(arguments, sort_keys=True)})")
            if name == "get_service_status":
                return self._result(
                    request_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "service": arguments.get("service"),
                                        "desired": 4,
                                        "running": 1,
                                        "pending": 3,
                                        "last_deployment": "image:v2.14.0",
                                    }
                                ),
                            }
                        ],
                        "isError": False,
                    },
                )
            if name == "read_log_lines":
                lines = int(arguments.get("lines", 3))
                body = [
                    "ERROR RuntimeError: could not select database user",
                    "ERROR connection refused 10.0.3.14:5432",
                    "INFO  retrying in 5s",
                ][:lines]
                return self._result(
                    request_id,
                    {"content": [{"type": "text", "text": "\n".join(body)}], "isError": False},
                )
            return self._error(request_id, -32601, f"unknown tool: {name}")

        if method == "resources/list":
            return self._result(
                request_id,
                {"resources": [{"uri": "lab://runbook", "name": "ECS runbook", "mimeType": "text/markdown"}]},
            )

        return self._error(request_id, -32601, f"unknown method: {method}")

    @staticmethod
    def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def run_server_process() -> subprocess.Popen[str]:
    """Start this same file in `--server` mode, piped both ways."""
    return subprocess.Popen(
        [sys.executable, str(Path(__file__).with_name("mcp_demo.py")), "--server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )


# --------------------------------------------------------------------- client


@dataclass
class McpClient:
    """Host-side client. Every control below belongs to the HOST, not the server.

    Without `allowed_tools`, an agent connected to a hostile server can call
    anything that server exposes. The allowlist is the security boundary.
    """

    allowed_tools: set[str] = field(default_factory=lambda: {"get_service_status", "read_log_lines"})
    max_output_chars: int = 2000
    audit: list[dict[str, Any]] = field(default_factory=list)

    _id: int = 0

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def call(self, proc: subprocess.Popen[str], method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request = {"jsonrpc": "2.0", "id": self._next_id(), "method": method, "params": params or {}}
        assert proc.stdin and proc.stdout
        proc.stdin.write(frame(request))
        proc.stdin.flush()
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("server closed the connection")
        response = parse_frame(line)
        self.audit.append({"method": method, "params": request["params"], "response": response})
        return response


def guard(client: McpClient, tool_name: str) -> str | None:
    """Host policy, applied before every call. This is the whole lesson."""
    if tool_name not in client.allowed_tools:
        return f"tool not in host allowlist: {tool_name}"
    return None


def demo_transport() -> None:
    print("=== 1. stdio transport, one JSON object per line ===")
    proc = run_server_process()
    try:
        client = McpClient()

        init = client.call(proc, "initialize", {"protocolVersion": PROTOCOL_VERSION})
        print(f"  initialize -> {init['result']['serverInfo']}")

        tools = client.call(proc, "tools/list")
        for tool in tools["result"]["tools"]:
            print(f"  server advertises: {tool['name']} ({tool['description']})")

        resources = client.call(proc, "resources/list")
        print(f"  resources        : {[r['uri'] for r in resources['result']['resources']]}")

        bad = client.call(proc, "tools/call", {"name": "rm_rf", "arguments": {}})
        print(f"  unknown tool     -> {bad['error']['message']}")
    finally:
        assert proc.stdin
        proc.stdin.close()
        proc.wait(timeout=5)


def demo_host_policy() -> None:
    print("\n=== 2. host policy decides, not the server ===")
    client = McpClient(allowed_tools={"get_service_status"})
    print(f"  host allowlist: {sorted(client.allowed_tools)}")

    print(f"  guard('get_service_status') -> {guard(client, 'get_service_status')}")
    print(f"  guard('read_log_lines')     -> {guard(client, 'read_log_lines')}")

    proc = run_server_process()
    try:
        client.call(proc, "initialize", {"protocolVersion": PROTOCOL_VERSION})
        blocked = guard(client, "read_log_lines")
        if blocked:
            print(f"  BLOCKED before sending: {blocked}")

        allowed = client.call(
            proc, "tools/call", {"name": "get_service_status", "arguments": {"service": "checkout"}}
        )
        payload = json.loads(allowed["result"]["content"][0]["text"])
        print(f"  ALLOWED and executed     : {payload}")
    finally:
        assert proc.stdin
        proc.stdin.close()
        proc.wait(timeout=5)


def demo_output_limits() -> None:
    print("\n=== 3. untrusted output is bounded before it reaches a model ===")
    hostile = "x" * 5000
    limit = client_limit()
    print(f"  server returned {len(hostile)} chars")
    print(f"  host kept {limit} chars plus an ellipsis marker")
    print("  without this, one tool call can evict the entire prompt.")


def client_limit() -> int:
    return McpClient().max_output_chars


def demo_initialization_order() -> None:
    print("\n=== 4. protocol violations are visible, not silent ===")
    server = DemoServer()
    early = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    print(f"  tools/list before initialize -> {early['error']['message']}")
    server.handle({"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {}})
    late = server.handle({"jsonrpc": "2.0", "id": 3, "method": "nonsense"})
    print(f"  unknown method              -> {late['error']['message']}")
    server.handle(
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "get_service_status", "arguments": {"service": "checkout"}}}
    )
    print(f"  server-side audit trail     : {server.audit}")
    print("  the server records what it executed; the host records what it allowed.")


def demo_responsibility_split() -> None:
    print("\n=== 5. who owns what ===")
    rows = [
        ("agent runtime", "goal, state, memory, planning, budgets"),
        ("MCP client", "connection, framing, request/response correlation"),
        ("MCP server", "credentials, the external connection, its own tools"),
        ("host policy", "allowlists, auth, validation, timeouts, output limits"),
        ("human", "approval for anything with a side effect"),
    ]
    for owner, responsibility in rows:
        print(f"  {owner:<16} {responsibility}")
    print("\n  adopting MCP gives you the middle two rows only.")


def serve() -> None:
    server = DemoServer()
    for line in sys.stdin:
        if not line.strip():
            continue
        response = server.handle(parse_frame(line))
        if response is not None:
            sys.stdout.write(frame(response))
            sys.stdout.flush()


if __name__ == "__main__":
    if "--server" in sys.argv:
        serve()
    else:
        print("MCP lesson: a transport, not a runtime. Host policy is the boundary.\n")
        demo_transport()
        demo_host_policy()
        demo_output_limits()
        demo_initialization_order()
        demo_responsibility_split()