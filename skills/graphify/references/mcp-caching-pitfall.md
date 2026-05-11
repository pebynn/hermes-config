# MCP Server Caching Pitfall

**Date**: 2026-05-07  
**Discovered**: During Superpowers × Hermes integration, when adding cross-graph edges

## Symptom

`mcp_graphify_graph_find_path(source, target)` returns "No path found" even after graph.json has been updated with new edges. CLI `graphify path` confirms the path exists.

## Root Cause

The MCP server (`~/.hermes/mcp-servers/mcp-graphify.py`) caches the graph in a module-level variable:

```python
_graph_data = None  # cached {"nodes": [...], "edges": [...], ...}

def load_graph():
    global _graph_data
    if _graph_data is not None:
        return _graph_data  # ← returns stale data after graph.json update
    ...
```

The MCP server runs as a persistent process. Once loaded, graph changes are invisible until the process restarts.

## Detection

```python
# CLI always reads fresh:
graphify path "Source" "Target" --graph /home/pebynn/brain/graphify-out/graph.json
# → Shortest path (1 hops): ...

# MCP may return stale:
mcp_graphify_graph_find_path(source="Source", target="Target")
# → "No path found between ..."  (but CLI confirms it exists!)
```

Discrepancy between CLI and MCP results is the telltale sign.

## Fix

1. **Immediate**: Clear `__pycache__` in the MCP server directory (sometimes old bytecode caches the stale `_graph_data`)
   ```bash
   find ~/.hermes/mcp-servers/__pycache__ -name "*raphify*" -delete
   ```

2. **Session-level**: Start a new Hermes session. The MCP server process restarts on new session, picking up fresh graph.json.

3. **Permanent fix** (not yet implemented): Modify `mcp-graphify.py` to check file modification time:
   ```python
   _graph_mtime = 0
   
   def load_graph():
       global _graph_data, _graph_mtime
       mtime = os.path.getmtime(GRAPH_PATH)
       if _graph_data is not None and mtime <= _graph_mtime:
           return _graph_data
       ...
       _graph_mtime = mtime
   ```

## When This Matters

- After `graphify merge-graphs` to combine graphs from multiple sources
- After manually adding cross-graph edges (patching graph.json directly)
- After any external modification to graph.json

**Rule of thumb**: After modifying graph.json, always verify with `graphify path` CLI. If CLI works but MCP doesn't, restart the session.
