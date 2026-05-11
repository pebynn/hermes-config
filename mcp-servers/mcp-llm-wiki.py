#!/usr/bin/env python3
"""
MCP Server: LLM Wiki / Research Knowledge Base

Exposes the research-skill-graph markdown knowledge base as MCP tools.
Tools:
  - wiki_search  : full-text search across all .md files
  - wiki_read    : read a specific file (path-sanitized)
  - wiki_list    : list files in a subdirectory
"""
# mcp-server.py
import asyncio
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ServerCapabilities, ToolsCapability
import os
import stat
from pathlib import Path
from datetime import datetime, timezone

from mcp.server import Server
from mcp.server.stdio import stdio_server




# ── configuration ───────────────────────────────────────────────────────────
HOME = Path.home()
WIKI_ROOT = HOME / "research-skill-graph"


# ── path sanitisation ───────────────────────────────────────────────────────
def safe_resolve(relative_path: str) -> Path | None:
    """
    Resolve *relative_path* under WIKI_ROOT, ensuring the result stays within
    WIKI_ROOT.  Returns the resolved absolute Path on success, or None if the
    path tries to escape the wiki root.
    """
    # Normalise: strip leading slashes, reject absolute inputs early
    clean = relative_path.lstrip("/")
    if not clean:
        return WIKI_ROOT

    candidate = (WIKI_ROOT / clean).resolve()
    try:
        candidate.relative_to(WIKI_ROOT)
    except ValueError:
        return None  # traversal attempt
    return candidate


# ── helpers ─────────────────────────────────────────────────────────────────
def _collect_markdown_files(root: Path) -> list[Path]:
    """Recursively collect all ``.md`` files under *root*."""
    return sorted(root.rglob("*.md"))


def _format_mtime(path: Path) -> str:
    """Return human-readable last-modified timestamp, or ``"unknown"``."""
    try:
        st = path.stat()
        mtime = st.st_mtime
        dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except OSError:
        return "unknown"


# ── server setup ────────────────────────────────────────────────────────────
server = Server("llm-wiki")


# ── tools ───────────────────────────────────────────────────────────────────
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="wiki_search",
            description=(
                "Full-text search across all markdown files in the research "
                "knowledge base.  Case-insensitive.  Returns file paths and "
                "matching context lines."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Search term to look for in .md files",
                    }
                },
                "required": ["topic"],
            },
        ),
        Tool(
            name="wiki_read",
            description=(
                "Read the content of a specific file inside the knowledge "
                "base.  Supply a relative path such as 'index.md' or "
                "'knowledge/concepts.md'.  Directory-traversal attacks are "
                "blocked."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Relative file path inside the wiki root, "
                            "e.g. 'index.md' or 'knowledge/concepts.md'"
                        ),
                    }
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="wiki_list",
            description=(
                "List files (and directories) inside a subdirectory of the "
                "knowledge base.  Pass an empty string for the root listing, "
                "or a relative directory like 'knowledge', 'lenses', etc.  "
                "Returns file names and last-modified timestamps."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": (
                            "Relative directory path inside the wiki root "
                            "(e.g. 'knowledge', 'lenses', '' for root)"
                        ),
                    }
                },
                "required": ["directory"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "wiki_search":
        return await _handle_search(arguments)
    elif name == "wiki_read":
        return await _handle_read(arguments)
    elif name == "wiki_list":
        return await _handle_list(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


# ── tool implementations ────────────────────────────────────────────────────

async def _handle_search(arguments: dict) -> list[TextContent]:
    topic = arguments.get("topic", "").strip()
    if not topic:
        return [TextContent(type="text", text="Error: 'topic' is required.")]

    if not WIKI_ROOT.is_dir():
        return [
            TextContent(
                type="text",
                text=(
                    f"Error: Wiki root '{WIKI_ROOT}' does not exist or is "
                    f"not a directory."
                ),
            )
        ]

    files = _collect_markdown_files(WIKI_ROOT)
    topic_lower = topic.lower()
    results: list[str] = []

    for fpath in files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            results.append(f"[error reading {fpath.name}]: {exc}")
            continue

        lines = text.splitlines()
        matching: list[str] = []
        for i, line in enumerate(lines, start=1):
            if topic_lower in line.lower():
                # Truncate long lines for readability
                display = line.strip()[:300]
                matching.append(f"  L{i}: {display}")

        if matching:
            rel = fpath.relative_to(WIKI_ROOT)
            results.append(f"\n── {rel} ──")
            results.extend(matching)

    if not results:
        return [
            TextContent(
                type="text",
                text=f"No matches found for '{topic}' in the wiki.",
            )
        ]

    return [TextContent(type="text", text="\n".join(results))]


async def _handle_read(arguments: dict) -> list[TextContent]:
    path_str = arguments.get("path", "").strip()
    if not path_str:
        return [TextContent(type="text", text="Error: 'path' is required.")]

    resolved = safe_resolve(path_str)
    if resolved is None:
        return [
            TextContent(
                type="text",
                text=(
                    f"Error: Path '{path_str}' escapes the wiki root. "
                    f"Access denied."
                ),
            )
        ]

    if not resolved.exists():
        return [
            TextContent(
                type="text",
                text=f"Error: File '{resolved}' does not exist.",
            )
        ]

    if not resolved.is_file():
        return [
            TextContent(
                type="text",
                text=f"Error: '{resolved}' is not a file.",
            )
        ]

    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [
            TextContent(
                type="text",
                text=f"Error reading file: {exc}",
            )
        ]

    rel = resolved.relative_to(WIKI_ROOT)
    header = f"── {rel} ──\n"
    return [TextContent(type="text", text=header + content)]


async def _handle_list(arguments: dict) -> list[TextContent]:
    dir_str = arguments.get("directory", "").strip()

    resolved = safe_resolve(dir_str)
    if resolved is None:
        return [
            TextContent(
                type="text",
                text=(
                    f"Error: Path '{dir_str}' escapes the wiki root. "
                    f"Access denied."
                ),
            )
        ]

    if not resolved.is_dir():
        return [
            TextContent(
                type="text",
                text=(
                    f"Error: '{resolved}' is not a valid directory "
                    f"inside the wiki."
                ),
            )
        ]

    try:
        entries = sorted(resolved.iterdir(), key=lambda p: p.name)
    except OSError as exc:
        return [
            TextContent(type="text", text=f"Error listing directory: {exc}")
        ]

    lines: list[str] = []
    for entry in entries:
        mtime = _format_mtime(entry)
        kind = "DIR" if entry.is_dir() else "FILE"
        name = entry.name
        rel = entry.relative_to(WIKI_ROOT)
        lines.append(f"{kind:4s}  {rel}  [{mtime}]")

    if not lines:
        rel = resolved.relative_to(WIKI_ROOT)
        return [
            TextContent(
                type="text",
                text=f"Directory '{rel}' is empty.",
            )
        ]

    return [TextContent(type="text", text="\n".join(lines))]


# ── entry point ─────────────────────────────────────────────────────────────
async def main():
    async with stdio_server() as (read, write):
        await server.run(
        read, write,
        InitializationOptions(
            server_name="mcp-llm-wiki",
            server_version="1.0.0",
            capabilities=ServerCapabilities(tools=ToolsCapability(list_changed=True))
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
