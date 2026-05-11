#!/usr/bin/env python3
"""
MCP server: cost-guard
Hard-wires circuit breaker and cost tracking into the agent tool chain.

Tools:
  - check_circuit()           → circuit status + recent failures + recommendations
  - query_cost(period)        → cost breakdown by domain/model for period
  - get_model_costs()         → current model pricing table
  - check_thresholds()        → compare current costs against configured limits

Usage:
  python3 mcp-cost-guard.py
"""
import asyncio
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

CIRCUIT_GUARD = os.path.expanduser(
    "~/.hermes/skills/devops/autonomous-optimization-architect/scripts/circuit-guard.py"
)
COST_TRACKER = os.path.expanduser(
    "~/.hermes/skills/devops/autonomous-optimization-architect/scripts/cost-tracker.py"
)
SESSIONS_DIR = os.path.expanduser("~/.hermes/sessions")

server = Server("cost-guard")


def run_script(script: str, args: list = None, timeout: int = 30) -> dict:
    """Run a Python script and return parsed JSON output."""
    cmd = ["python3", script] + (args or [])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        # Try to parse JSON output
        for line in result.stdout.strip().split("\n"):
            try:
                data = json.loads(line)
                return data
            except json.JSONDecodeError:
                continue
        return {"status": "ok", "raw_output": result.stdout[:2000], "exit_code": result.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "Script timed out", "timeout": timeout}
    except Exception as e:
        return {"error": str(e)}


def count_recent_failures(hours: int = 24) -> dict:
    """Scan session logs for recent errors/failures."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    sessions_dir = Path(SESSIONS_DIR)
    
    failures = []
    total_sessions = 0
    
    if not sessions_dir.is_dir():
        return {"error": "Sessions directory not found", "total": 0, "failures": 0}
    
    for f in sorted(sessions_dir.glob("session_*.json"), reverse=True):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                break
            total_sessions += 1
            
            # Quick scan for error patterns
            content = f.read_text()[:50000]
            error_count = len(re.findall(r'"error"|"failed"|"timeout"|"circuit.*broken"', content, re.IGNORECASE))
            if error_count > 3:
                failures.append({
                    "session": f.name,
                    "time": mtime.isoformat(),
                    "error_count": error_count,
                })
        except Exception:
            continue
    
    return {
        "total_sessions": total_sessions,
        "failed_sessions": len(failures),
        "recent_failures": failures[:5],
        "window_hours": hours,
    }


def get_circuit_status() -> dict:
    """Check circuit breaker status from cost-tracker output and session analysis."""
    # Run circuit-guard for formal status
    cg_result = run_script(CIRCUIT_GUARD, timeout=20)
    
    # Analyze recent sessions for failures
    failures = count_recent_failures(24)
    
    # Determine circuit status
    fail_count = failures.get("failed_sessions", 0)
    total = failures.get("total_sessions", 1)
    fail_rate = fail_count / max(total, 1)
    
    if fail_rate > 0.5:
        status = "circuit_broken"
        recommendation = "Switch to fallback provider immediately"
    elif fail_rate > 0.3:
        status = "circuit_warning"
        recommendation = "Monitor closely, consider preemptive fallback"
    elif fail_count >= 3:
        status = "elevated_failures"
        recommendation = f"{fail_count} failures in 24h — investigate"
    else:
        status = "healthy"
        recommendation = "No action needed"
    
    return {
        "status": status,
        "recommendation": recommendation,
        "failure_rate_24h": round(fail_rate, 3),
        "recent_failures": failures.get("recent_failures", []),
        "circuit_guard_raw": cg_result,
    }


def get_cost_summary() -> dict:
    """Get cost summary from cost-tracker."""
    ct_result = run_script(COST_TRACKER, timeout=20)
    
    # Also estimate from session metadata
    sessions_dir = Path(SESSIONS_DIR)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_sessions = 0
    today_tokens = {"input": 0, "output": 0}
    
    if sessions_dir.is_dir():
        for f in sessions_dir.glob(f"session_{today}*.json"):
            today_sessions += 1
            try:
                data = json.loads(f.read_text()[:10000])
                usage = data.get("usage", {})
                today_tokens["input"] += usage.get("input_tokens", 0)
                today_tokens["output"] += usage.get("output_tokens", 0)
            except Exception:
                continue
    
    # Estimate cost (using deepseek-v4-pro rates with cache-hit awareness)
    # Input: 85% cache-hit at $0.003625/M, 15% cache-miss at $0.435/M
    # Effective input: $0.06833/M, output: $0.87/M
    estimated_cost = (
        today_tokens["input"] * 0.06833 / 1_000_000 +
        today_tokens["output"] * 0.87 / 1_000_000
    )
    
    return {
        "today": {
            "sessions": today_sessions,
            "input_tokens": today_tokens["input"],
            "output_tokens": today_tokens["output"],
            "estimated_cost_usd": round(estimated_cost, 4),
        },
        "cost_tracker_raw": ct_result,
    }


MODEL_COSTS = {
    # V4 Pro — 75% discount active until 2026-05-31
    "deepseek-v4-pro":   {"cache_miss": 0.435, "cache_hit": 0.003625, "output": 0.87, "unit": "$/1M tokens"},
    # V4 Flash — standard pricing
    "deepseek-v4-flash": {"cache_miss": 0.14,  "cache_hit": 0.0028,   "output": 0.28, "unit": "$/1M tokens"},
    # V3.2 / deepseek-chat
    "deepseek-chat":     {"cache_miss": 0.28,  "cache_hit": 0.028,    "output": 0.42, "unit": "$/1M tokens"},
    "glm-4.5-air":       {"cache_miss": 0.50,  "cache_hit": 0.50,     "output": 0.50, "unit": "$/1M tokens"},
}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="check_circuit",
            description="Check circuit breaker status: healthy/warning/broken. MUST be called before making model routing decisions. Returns failure rate, recent errors, and recommendations.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="query_cost",
            description="Query current cost summary: today's token usage, estimated cost, session count. Use before expensive operations.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_model_costs",
            description="Get current model pricing table ($/1M tokens). Use for model selection decisions.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "check_circuit":
        result = get_circuit_status()
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "query_cost":
        result = get_cost_summary()
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "get_model_costs":
        return [TextContent(type="text", text=json.dumps(MODEL_COSTS, ensure_ascii=False, indent=2))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
