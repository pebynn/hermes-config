#!/usr/bin/env python3
"""
MCP server: graphify
Exposes the Hermes knowledge graph as MCP query tools.

Tools:
  - graph_search(query_text)  - Search nodes by label/properties (case-insensitive substring)
  - graph_find_path(source, target) - Shortest path via BFS between two node IDs
  - graph_explain(node_id)    - Show node details with properties and connected edges
  - graph_stats()             - Graph statistics (node/edge counts, node type counts)

Usage:
  python3 mcp-graphify.py
"""
# mcp-server.py
import asyncio
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ServerCapabilities, ToolsCapability
import json
import os
from collections import deque

from mcp.server import Server
from mcp.server.stdio import stdio_server



GRAPH_PATH = "/home/pebynn/brain/graphify-out/graph.json"

# ---------------------------------------------------------------------------
# Graph data loader & cache
# ---------------------------------------------------------------------------

_graph_data = None  # cached {"nodes": [...], "edges": [...], ...}


def load_graph():
    """Load and cache the graph JSON file. Returns (nodes, edges, metadata_dict)."""
    global _graph_data
    if _graph_data is not None:
        return _graph_data

    if not os.path.isfile(GRAPH_PATH):
        raise FileNotFoundError(f"Graph file not found: {GRAPH_PATH}")

    try:
        with open(GRAPH_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Graph file is malformed JSON: {e}")

    nodes = data.get("nodes", [])
    # The graph may use "links" or "edges" for relationships
    edges = data.get("edges") or data.get("links", [])

    if not isinstance(nodes, list):
        raise ValueError("'nodes' field is not a list")
    if not isinstance(edges, list):
        raise ValueError("'edges'/'links' field is not a list")

    _graph_data = (nodes, edges, data)
    return _graph_data


def build_edge_index(edges):
    """Build adjacency dict: {node_id: [(neighbor_id, edge_dict)]}"""
    idx = {}
    for e in edges:
        src = e.get("source")
        tgt = e.get("target")
        if not src or not tgt:
            continue
        idx.setdefault(src, []).append((tgt, e))
        idx.setdefault(tgt, []).append((src, e))
    return idx


def build_node_map(nodes):
    """Build {node_id: node_dict} lookup."""
    return {n.get("id"): n for n in nodes if n.get("id")}


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

server = Server("graphify")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="graph_search",
            description="Search graph nodes by label/text for matching nodes. Case-insensitive substring match on node labels and string properties.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "Search text to match against node labels and properties",
                    }
                },
                "required": ["query_text"],
            },
        ),
        Tool(
            name="graph_find_path",
            description="Find shortest path between two nodes by their IDs using BFS.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Source node ID",
                    },
                    "target": {
                        "type": "string",
                        "description": "Target node ID",
                    },
                },
                "required": ["source", "target"],
            },
        ),
        Tool(
            name="graph_explain",
            description="Show a node with all its properties and connected edges (neighbors).",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "Node ID to inspect",
                    }
                },
                "required": ["node_id"],
            },
        ),
        Tool(
            name="graph_stats",
            description="Show graph statistics: node count, edge count, node types count.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        nodes, edges, _raw = load_graph()
    except (FileNotFoundError, ValueError) as e:
        return [TextContent(type="text", text=f"Error loading graph: {e}")]

    try:
        if name == "graph_search":
            return _handle_graph_search(nodes, arguments)
        elif name == "graph_find_path":
            return _handle_graph_find_path(nodes, edges, arguments)
        elif name == "graph_explain":
            return _handle_graph_explain(nodes, edges, arguments)
        elif name == "graph_stats":
            return _handle_graph_stats(nodes, edges)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing {name}: {e}")]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


def _handle_graph_search(nodes: list, args: dict) -> list[TextContent]:
    query = args.get("query_text", "").strip().lower()
    if not query:
        return [TextContent(type="text", text="Error: query_text is required.")]

    matches = []
    for n in nodes:
        nid = n.get("id", "")
        label = str(n.get("label", "")).lower()
        if query in label or query in nid.lower():
            matches.append(n)
            continue
        # Also search string property values
        for k, v in n.items():
            if isinstance(v, str) and query in v.lower():
                matches.append(n)
                break

    if not matches:
        return [TextContent(type="text", text=f"No nodes found matching '{query}'.")]

    # Limit output to avoid huge responses
    MAX_SHOWN = 50
    shown = matches[:MAX_SHOWN]
    lines = [f"Found {len(matches)} node(s) matching '{args['query_text']}':"]
    for m in shown:
        nid = m.get("id", "?")
        label = m.get("label", "")
        ntype = m.get("file_type", m.get("type", ""))
        lines.append(f"  [{ntype}] {nid} - {label}")

    if len(matches) > MAX_SHOWN:
        lines.append(f"  ... and {len(matches) - MAX_SHOWN} more")

    return [TextContent(type="text", text="\n".join(lines))]


def _handle_graph_find_path(nodes: list, edges: list, args: dict) -> list[TextContent]:
    source = args.get("source", "").strip()
    target = args.get("target", "").strip()
    if not source or not target:
        return [TextContent(type="text", text="Error: source and target are required.")]

    node_map = build_node_map(nodes)
    if source not in node_map:
        return [TextContent(type="text", text=f"Error: source node '{source}' not found.")]
    if target not in node_map:
        return [TextContent(type="text", text=f"Error: target node '{target}' not found.")]

    adj = build_edge_index(edges)

    # BFS
    visited = {source}
    queue = deque([(source, [source])])

    while queue:
        current, path = queue.popleft()
        if current == target:
            # Build human-readable path
            lines = [f"Shortest path ({len(path) - 1} hops):"]
            for i, nid in enumerate(path):
                node = node_map.get(nid, {})
                label = node.get("label", nid)
                arrow = " -> " if i < len(path) - 1 else ""
                lines.append(f"  {i}. {nid} ({label}){arrow}")
            return [TextContent(type="text", text="\n".join(lines))]

        for neighbor, _ in adj.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return [TextContent(
        type="text",
        text=f"No path found between '{source}' and '{target}'."
    )]


def _handle_graph_explain(nodes: list, edges: list, args: dict) -> list[TextContent]:
    node_id = args.get("node_id", "").strip()
    if not node_id:
        return [TextContent(type="text", text="Error: node_id is required.")]

    node_map = build_node_map(nodes)
    if node_id not in node_map:
        return [TextContent(type="text", text=f"Error: node '{node_id}' not found.")]

    node = node_map[node_id]

    # Collect connected edges
    connected = []
    for e in edges:
        src = e.get("source")
        tgt = e.get("target")
        if src == node_id or tgt == node_id:
            connected.append(e)

    lines = [f"Node: {node_id}"]
    # Properties (skip id which we already show)
    props = {k: v for k, v in node.items() if k != "id"}
    if props:
        lines.append("  Properties:")
        for k, v in props.items():
            lines.append(f"    {k}: {v}")

    if connected:
        lines.append(f"  Connected edges ({len(connected)}):")
        for e in connected:
            src = e.get("source")
            tgt = e.get("target")
            rel = e.get("relation", "?")
            lines.append(f"    {src} --[{rel}]--> {tgt}")
    else:
        lines.append("  No connected edges.")

    return [TextContent(type="text", text="\n".join(lines))]


def _handle_graph_stats(nodes: list, edges: list) -> list[TextContent]:
    node_count = len(nodes)
    edge_count = len(edges)

    # Count node types. The type field could be "file_type" or "type"
    type_counts = {}
    for n in nodes:
        ntype = n.get("file_type") or n.get("type") or "unknown"
        type_counts[ntype] = type_counts.get(ntype, 0) + 1

    lines = [
        f"Graph Statistics:",
        f"  Total nodes: {node_count}",
        f"  Total edges: {edge_count}",
        f"  Node types ({len(type_counts)}):",
    ]
    for ntype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        lines.append(f"    {ntype}: {count}")

    return [TextContent(type="text", text="\n".join(lines))]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main():
    async with stdio_server() as (read, write):
        await server.run(
        read, write,
        InitializationOptions(
            server_name="mcp-graphify",
            server_version="1.0.0",
            capabilities=ServerCapabilities(tools=ToolsCapability(list_changed=True))
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
