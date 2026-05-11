#!/usr/bin/env python3
"""
MCP server: skill-security-auditor
Wraps the skill security auditor as an MCP tool for hard enforcement.

Tools:
  - audit_skill(path, strict=False)  - Audit a local skill directory
  - audit_skills_batch(paths)        - Batch audit multiple skill directories
  - audit_git_skill(url, skill_name) - Clone + audit a skill from GitHub

Usage:
  python3 mcp-skill-auditor.py
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

AUDITOR_SCRIPT = os.path.expanduser(
    "~/.hermes/skills/security/skill-security-auditor/scripts/skill_security_auditor.py"
)

server = Server("skill-security-auditor")


def run_audit(path: str, strict: bool = False) -> dict:
    """Run the auditor and return parsed result."""
    cmd = ["python3", AUDITOR_SCRIPT, path, "--json"]
    if strict:
        cmd.append("--strict")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "error": "Failed to parse auditor output",
            "stdout": result.stdout[:500],
            "stderr": result.stderr[:500],
            "exit_code": result.returncode,
        }

    data["exit_code"] = result.returncode
    return data


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="audit_skill",
            description="Audit a local skill directory for security risks. Returns PASS/WARN/FAIL verdict with detailed findings. CRITICAL findings = do NOT install. Use BEFORE installing any external skill.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the skill directory to audit",
                    },
                    "strict": {
                        "type": "boolean",
                        "description": "If true, any WARN becomes FAIL (default: false)",
                        "default": False,
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="audit_skills_batch",
            description="Batch audit multiple skill directories at once. Returns aggregated results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of absolute paths to skill directories",
                    },
                },
                "required": ["paths"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "audit_skill":
        path = arguments["path"]
        strict = arguments.get("strict", False)

        if not os.path.isdir(path):
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Directory not found: {path}", "verdict": "ERROR"}, ensure_ascii=False, indent=2),
            )]

        result = run_audit(path, strict)
        return [TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2),
        )]

    elif name == "audit_skills_batch":
        paths = arguments["paths"]
        results = {}
        for p in paths:
            if not os.path.isdir(p):
                results[p] = {"error": "Directory not found", "verdict": "ERROR"}
            else:
                results[p] = run_audit(p)
        return [TextContent(
            type="text",
            text=json.dumps(results, ensure_ascii=False, indent=2),
        )]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
