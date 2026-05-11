# MCP JSON-RPC Bridge Pattern

## Problem

MCP tools are only available within agent sessions. Standalone scripts (cron jobs, backend services, CLI tools) cannot directly call MCP tools because they run outside the agent's MCP client context.

## Solution: Subprocess JSON-RPC Bridge

Create a Python module that communicates with an MCP server via subprocess + MCP JSON-RPC protocol (stdio transport), exposing MCP tools as plain Python functions.

## Architecture

```
standalone Python script
     │
     └── subprocess.Popen(["path/to/mcp-server"])
              │
              ├── stdin:  {"jsonrpc":"2.0","id":1,"method":"initialize",...}
              ├── stdin:  {"jsonrpc":"2.0","method":"notifications/initialized"}
              ├── stdin:  {"jsonrpc":"2.0","id":2,"method":"tools/call",
              │            "params":{"name":"tool_name","arguments":{...}}}
              └── stdout: {"jsonrpc":"2.0","id":2,"result":{"content":[...]}}
```

## Core Implementation

```python
import subprocess, json

def call_mcp_tool(mcp_cmd: list, tool_name: str, arguments: dict = {}, timeout: int = 15) -> dict:
    """Call an MCP tool via subprocess JSON-RPC protocol"""
    try:
        proc = subprocess.Popen(
            mcp_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 1. Initialize
        _send(proc, {"jsonrpc":"2.0","id":1,"method":"initialize",
                     "params":{"protocolVersion":"2024-11-05",
                               "capabilities":{},
                               "clientInfo":{"name":"bridge","version":"1.0"}}})
        _recv(proc)  # read initialize response
        
        # 2. Initialized notification
        _send(proc, {"jsonrpc":"2.0","method":"notifications/initialized"})
        
        # 3. tools/call
        _send(proc, {"jsonrpc":"2.0","id":2,"method":"tools/call",
                     "params":{"name":tool_name,"arguments":arguments}})
        result = _recv(proc)
        
        proc.terminate()
        
        # Parse MCP content (text type contains JSON string)
        if result and "result" in result and "content" in result["result"]:
            for item in result["result"]["content"]:
                if item.get("type") == "text":
                    return json.loads(item["text"])
        return result.get("result", {})
    except Exception as e:
        return {"error": str(e)}

def _send(proc, msg):
    proc.stdin.write(json.dumps(msg).encode() + b"\n")
    proc.stdin.flush()

def _recv(proc) -> dict:
    line = proc.stdout.readline()
    return json.loads(line.decode())
```

## Pitfalls

- **New process per call** — suitable for low-frequency calls (<10/min), not for high-frequency queries
- **stderr pipe full** — if MCP Server writes lots of stderr logs, pipe may deadlock. Use `stderr=subprocess.DEVNULL` or read thread
- **timeout control** — process may hang, must set `subprocess.Popen` + `proc.wait(timeout=...)`
- **Single-line output** — MCP Server outputs one JSON line per response. If server has extra debug output (non-JSON), `json.loads` fails; add line filtering
- **Not thread-safe** — don't share proc across threads; create independent subprocess per thread
- **MCP Server initialization** — some servers require sending `ListTools` request before `CallTool`

## Use Cases

- Cron scripts calling MCP tools for real-time data (e.g., stock-sdk-mcp for US/HK/A50 quotes)
- Backend services accessing databases via MCP proxy
- CLI tools wrapping MCP functionality

## Real-world Example

**`~/writing-data/scripts/shared/stock_sdk_client.py`** (365 lines):
- Calls `stock-sdk-mcp` (`/home/pebynn/.hermes/node/bin/stock-mcp`) via this pattern
- Exports: `fetch_us_indices()`, `fetch_hang_seng()`, `fetch_a50_futures()`
- Used by `morning_brief.py` for 08:00 morning brief cron job
- Verified: returns real HSI data (26393.71, -0.87%) and A50 data (15578, +0.2%)

## Alternatives

If the MCP Server has a CLI mode (e.g., `--tool tool_name --arg key=value`), prefer CLI over JSON-RPC. Check `--help` output.
