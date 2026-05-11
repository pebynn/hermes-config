#!/usr/bin/env python3
"""
MCP server: hermes-cron
Exposes Hermes cron job management as MCP tools.
"""
# mcp-server.py
import asyncio
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ServerCapabilities, ToolsCapability
import re
import subprocess
import shutil
from mcp.server import Server
from mcp.server.stdio import stdio_server



HERMES_BIN = "/home/pebynn/.hermes/hermes-agent/venv/bin/hermes"


def _run_hermes(args: list[str], timeout: int = 30) -> str:
    """Run the hermes CLI with the given arguments and return stdout."""
    if not shutil.which(HERMES_BIN) and not __import__("os").path.exists(HERMES_BIN):
        return f"Error: Hermes CLI not found at {HERMES_BIN}"
    cmd = [HERMES_BIN] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout}s: {' '.join(cmd)}"
    except FileNotFoundError:
        return f"Error: Hermes CLI not found at {HERMES_BIN}"
    except Exception as e:
        return f"Error: Failed to run command: {e}"

    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip() or f"Exit code {result.returncode}"
        return f"Error: {err}"
    return result.stdout.strip()


def _parse_cron_list(raw_output: str) -> str:
    """Parse hermes cron list output into a structured table format."""
    if not raw_output or raw_output.startswith("Error:"):
        return raw_output

    lines = raw_output.splitlines()
    if not lines:
        return "No cron jobs found."

    # Try to detect if it's a table-like output or JSON or key-value list
    # Typical 'hermes cron list' output looks like:
    #   Job ID: abc123   Name: my-job   Schedule: 0 9 * * *   Status: active   Last run: 2025-01-01 09:00
    # or a simple list with job IDs and names.
    # We'll parse it generically.

    header = "Job ID                               Name                Schedule             Status      Last Run"
    separator = "-" * len(header)
    rows = [header, separator]

    job_pattern = re.compile(
        r"(?:Job ID|ID|job_id)[:\s]+(\S+)"
        r".*?(?:Name|name)[:\s]+(.+?)?"
        r"(?:\s+(?:Schedule|schedule)[:\s]+(.+?))?"
        r"(?:\s+(?:Status|status)[:\s]+(\S+?))?"
        r"(?:\s+(?:Last run|last_run|Last Run|last run)[:\s]+(.+?))?",
        re.IGNORECASE,
    )

    parsed_any = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip separator lines and headers
        if re.match(r"^[-\s]+$", line) or re.match(r"^(Job ID|ID)\s", line, re.IGNORECASE):
            continue

        m = job_pattern.search(line)
        if m:
            job_id = m.group(1)
            name = (m.group(2) or "").strip()
            schedule = (m.group(3) or "").strip()
            status = (m.group(4) or "").strip()
            last_run = (m.group(5) or "").strip()
            if name and not schedule:
                # Try to extract more structured info from next tokens
                pass
            rows.append(
                f"{job_id:<40} {name:<20} {schedule:<18} {status:<12} {last_run}"
            )
            parsed_any = True
        else:
            # If no structured parsing worked, just include the raw line
            rows.append(line)
            parsed_any = True

    if not parsed_any:
        # Show raw output if we couldn't parse
        return raw_output

    return "\n".join(rows)


server = Server("hermes-cron")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="cron_list",
            description="List all Hermes cron jobs. Pass show_all=True to include paused/completed jobs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "show_all": {
                        "type": "boolean",
                        "description": "Show all jobs including paused/completed",
                        "default": False,
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="cron_create",
            description="Create a new Hermes cron job.",
            inputSchema={
                "type": "object",
                "properties": {
                    "schedule": {
                        "type": "string",
                        "description": "Cron schedule expression (e.g., '0 9 * * *')",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Prompt to run on the schedule",
                    },
                    "name": {
                        "type": "string",
                        "description": "Optional name for the cron job",
                    },
                    "deliver": {
                        "type": "string",
                        "description": "Delivery method (e.g., 'local', 'telegram', etc.)",
                    },
                },
                "required": ["schedule", "prompt"],
            },
        ),
        Tool(
            name="cron_pause",
            description="Pause a cron job by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "The ID of the cron job to pause",
                    }
                },
                "required": ["job_id"],
            },
        ),
        Tool(
            name="cron_resume",
            description="Resume a paused cron job by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "The ID of the cron job to resume",
                    }
                },
                "required": ["job_id"],
            },
        ),
        Tool(
            name="cron_remove",
            description="Remove a cron job by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "The ID of the cron job to remove",
                    }
                },
                "required": ["job_id"],
            },
        ),
        Tool(
            name="cron_status",
            description="Check if the Hermes cron scheduler is running.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "cron_list":
            show_all = arguments.get("show_all", False)
            args = ["cron", "list"]
            if show_all:
                args.append("--all")
            raw_output = _run_hermes(args, timeout=30)
            formatted = _parse_cron_list(raw_output)
            return [TextContent(type="text", text=formatted)]

        elif name == "cron_create":
            schedule = arguments["schedule"]
            prompt = arguments["prompt"]
            job_name = arguments.get("name", "")
            deliver = arguments.get("deliver", "local")

            cmd_args = ["cron", "create"]
            if job_name:
                cmd_args.extend(["--name", job_name])
            if deliver:
                cmd_args.extend(["--deliver", deliver])
            cmd_args.append(schedule)
            cmd_args.append(prompt)

            output = _run_hermes(cmd_args, timeout=60)
            return [TextContent(type="text", text=output)]

        elif name == "cron_pause":
            job_id = arguments["job_id"]
            output = _run_hermes(["cron", "pause", job_id], timeout=30)
            return [TextContent(type="text", text=output)]

        elif name == "cron_resume":
            job_id = arguments["job_id"]
            output = _run_hermes(["cron", "resume", job_id], timeout=30)
            return [TextContent(type="text", text=output)]

        elif name == "cron_remove":
            job_id = arguments["job_id"]
            output = _run_hermes(["cron", "remove", job_id], timeout=30)
            return [TextContent(type="text", text=output)]

        elif name == "cron_status":
            output = _run_hermes(["cron", "status"], timeout=30)
            return [TextContent(type="text", text=output)]

        else:
            return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]

    except KeyError as e:
        return [TextContent(type="text", text=f"Error: Missing required argument: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


async def main():
    async with stdio_server() as (read, write):
        await server.run(
        read, write,
        InitializationOptions(
            server_name="mcp-hermes-cron",
            server_version="1.0.0",
            capabilities=ServerCapabilities(tools=ToolsCapability(list_changed=True))
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
