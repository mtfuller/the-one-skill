#!/usr/bin/env python3
"""A tiny fake task-list connector (MCP over stdio), for the connector scenario.

Exposes read tools (completed and open tasks) and one write tool (add a task). Its data names a
project and an email address, so the eval can check that neither is copied into a skill.
Standard library only; speaks newline-delimited JSON-RPC 2.0.
"""
import json
import sys

TASKS_DONE = [
    {"id": "t-101", "content": "Ship onboarding emails", "project": "Apollo", "completed": "2026-11-14",
     "assignee": "ana@example.invalid"},
    {"id": "t-102", "content": "Fix login timeout", "project": "Apollo", "completed": "2026-11-13",
     "assignee": "ana@example.invalid"},
]
TASKS_OPEN = [
    {"id": "t-201", "content": "Draft Q1 plan", "project": "Apollo", "due": "2026-11-21", "blocked": False},
    {"id": "t-202", "content": "Migrate billing", "project": "Apollo", "due": "2026-11-20", "blocked": True,
     "blocked_by": "waiting on finance"},
]
TOOLS = [
    {"name": "list_completed_tasks", "description": "List tasks completed since a date (YYYY-MM-DD).",
     "inputSchema": {"type": "object", "properties": {"since": {"type": "string"}}}},
    {"name": "list_open_tasks", "description": "List open tasks, with due dates and whether each is blocked.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "add_task", "description": "Create a new task.",
     "inputSchema": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]}},
]


def result(req_id, res):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": res}) + "\n")
    sys.stdout.flush()


for line in sys.stdin:
    try:
        msg = json.loads(line)
    except ValueError:
        continue
    method, req_id = msg.get("method"), msg.get("id")
    if req_id is None:
        continue  # notifications need no reply
    if method == "initialize":
        result(req_id, {"protocolVersion": msg.get("params", {}).get("protocolVersion", "2025-06-18"),
                        "capabilities": {"tools": {}}, "serverInfo": {"name": "taskboard", "version": "0.1"}})
    elif method == "tools/list":
        result(req_id, {"tools": TOOLS})
    elif method == "tools/call":
        name = msg.get("params", {}).get("name")
        data = {"list_completed_tasks": TASKS_DONE, "list_open_tasks": TASKS_OPEN}.get(name, {"created": True})
        result(req_id, {"content": [{"type": "text", "text": json.dumps(data)}]})
    else:
        result(req_id, {})
