#!/usr/bin/env python3
"""
MCP Server: Hermes Delegate

Exposes Hermes Agent delegation as MCP tools for external AI agents.
This is a task queue system: tasks are written as JSON files to
~/.hermes/mcp-tasks/. External processes (cron, gateway hooks, or a
user manually running hermes) can pick up queued tasks, execute them,
and update the task file with results.

Tools:
  - delegate(goal, context, skills)    -> Submit a task, returns task_id
  - check_task(task_id)                -> Check status/output of a task
  - list_tasks(limit)                  -> List recent tasks with status
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ── Constants ──────────────────────────────────────────────────────────

HERMES_HOME = Path(os.path.expanduser("~/.hermes"))
TASKS_DIR = HERMES_HOME / "mcp-tasks"
SERVER_NAME = "hermes-delegate"

# ── Ensure task directory exists ───────────────────────────────────────

TASKS_DIR.mkdir(parents=True, exist_ok=True)

# ── MCP Server instance ────────────────────────────────────────────────

server = Server(SERVER_NAME)


# ── Helpers ────────────────────────────────────────────────────────────

def _read_task_file(task_id: str) -> dict | None:
    """Read a task JSON file, return None if not found."""
    task_path = TASKS_DIR / f"{task_id}.json"
    if not task_path.exists():
        return None
    try:
        with open(task_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        return {"id": task_id, "status": "error", "error": str(exc)}


def _write_task_file(task: dict) -> None:
    """Write a task dict to its JSON file."""
    task_path = TASKS_DIR / f"{task['id']}.json"
    with open(task_path, "w") as f:
        json.dump(task, f, indent=2, default=str)


def _list_task_files() -> list[Path]:
    """Return all .json task files sorted by mtime (newest first)."""
    files = sorted(
        TASKS_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files


# ── Tool definitions ───────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="delegate",
            description="Submit a task to Hermes for execution. Queues it as a JSON file in ~/.hermes/mcp-tasks/ and returns immediately with a task ID. Check back later with check_task().",
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "The goal or instruction for Hermes to execute",
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context or background information",
                        "default": "",
                    },
                    "skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of skill names to enable for this task",
                        "default": [],
                    },
                },
                "required": ["goal"],
            },
        ),
        Tool(
            name="check_task",
            description="Check the status and output of a previously submitted task by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The unique task ID returned by delegate()",
                    },
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="list_tasks",
            description="List recent submitted tasks with their status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of tasks to return (default: 10)",
                        "default": 10,
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "delegate":
            return await _handle_delegate(arguments)
        elif name == "check_task":
            return await _handle_check_task(arguments)
        elif name == "list_tasks":
            return await _handle_list_tasks(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as exc:
        return [TextContent(type="text", text=json.dumps({
            "error": str(exc),
            "type": type(exc).__name__,
        }, indent=2))]


# ── Tool handlers ──────────────────────────────────────────────────────

async def _handle_delegate(args: dict) -> list[TextContent]:
    goal = args.get("goal", "").strip()
    if not goal:
        return [TextContent(type="text", text=json.dumps({
            "error": "goal is required",
        }, indent=2))]

    context = args.get("context", "") or ""
    skills = args.get("skills", []) or []

    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    task = {
        "id": task_id,
        "goal": goal,
        "context": context,
        "skills": skills,
        "created_at": now,
        "status": "queued",
        "output": None,
        "error": None,
    }

    _write_task_file(task)

    return [TextContent(type="text", text=json.dumps({
        "task_id": task_id,
        "status": "queued",
        "message": f"Task {task_id} queued. Use check_task('{task_id}') to poll for results.",
    }, indent=2))]


async def _handle_check_task(args: dict) -> list[TextContent]:
    task_id = args.get("task_id", "").strip()
    if not task_id:
        return [TextContent(type="text", text=json.dumps({
            "error": "task_id is required",
        }, indent=2))]

    task = _read_task_file(task_id)
    if task is None:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Task not found: {task_id}",
        }, indent=2))]

    # Return a clean summary
    result = {
        "task_id": task["id"],
        "status": task.get("status", "unknown"),
        "goal": task.get("goal", ""),
        "created_at": task.get("created_at", ""),
    }

    if task.get("completed_at"):
        result["completed_at"] = task["completed_at"]
    if task.get("output"):
        result["output"] = task["output"]
    if task.get("error"):
        result["error"] = task["error"]
    if task.get("skills"):
        result["skills"] = task["skills"]

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _handle_list_tasks(args: dict) -> list[TextContent]:
    limit = max(1, min(100, args.get("limit", 10)))

    files = _list_task_files()
    tasks = []
    for f in files[:limit]:
        task = _read_task_file(f.stem)
        if task:
            tasks.append({
                "task_id": task.get("id", f.stem),
                "status": task.get("status", "unknown"),
                "goal": task.get("goal", "")[:120],
                "created_at": task.get("created_at", ""),
            })

    return [TextContent(type="text", text=json.dumps({
        "count": len(tasks),
        "tasks": tasks,
    }, indent=2))]


# ── Entry point ────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
