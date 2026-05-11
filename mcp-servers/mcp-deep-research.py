#!/usr/bin/env python3
"""
MCP Server: Deep Research
Multi-angle research assistant using Tavily search API.
Generates 3-5 research angles for a question, searches each in parallel,
and compiles a structured research report.
"""
# mcp-server.py
import asyncio
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ServerCapabilities, ToolsCapability
import json
import os
import urllib.request
import urllib.error
import urllib.parse
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server



# ---------------------------------------------------------------------------
# Tavily search helpers
# ---------------------------------------------------------------------------

TAVILY_URL = "https://api.tavily.com/search"


def tavily_search(query: str, api_key: str) -> list[dict[str, Any]]:
    """Execute a single Tavily search and return the results list."""
    if not api_key:
        raise ValueError("TAVILY_API_KEY is not set or empty")

    payload = json.dumps({
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "max_results": 5,
    }).encode("utf-8")

    req = urllib.request.Request(
        TAVILY_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = b""
        try:
            error_body = e.read()
        except Exception:
            pass
        raise RuntimeError(
            f"Tavily API HTTP {e.code}: {error_body.decode('utf-8', errors='replace')}"
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Tavily API connection error: {e.reason}") from e

    return body.get("results", [])


# ---------------------------------------------------------------------------
# Angle / query generation
# ---------------------------------------------------------------------------

_ANGLE_TEMPLATES = [
    "overview and key concepts",
    "latest developments and news",
    "technical details and fundamentals",
    "use cases and applications",
    "challenges and limitations",
]


def extract_keywords(question: str) -> list[str]:
    """Break a question into meaningful component keywords.

    Removes common stop-words and punctuation, returning the remaining
    lowercased tokens that are longer than 2 characters.
    """
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "shall", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "through", "during",
        "before", "after", "above", "below", "between", "out", "off", "over",
        "under", "again", "further", "then", "once", "here", "there", "when",
        "where", "why", "how", "all", "both", "each", "few", "more", "most",
        "other", "some", "such", "no", "nor", "not", "only", "own", "same",
        "so", "than", "too", "very", "just", "because", "but", "and", "or",
        "if", "while", "about", "up", "what", "which", "who", "whom", "this",
        "that", "these", "those", "it", "its", "please", "explain", "tell",
        "describe", "define", "whats", "what's", "dont", "don't",
    }

    # Normalise: lowercase, strip punctuation
    for ch in "?!,.;:\"'()[]{}":
        question = question.replace(ch, " ")

    tokens = [
        t.strip().lower()
        for t in question.split()
        if t.strip() and t.strip().lower() not in stop_words and len(t.strip()) > 2
    ]

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    return unique if unique else [question.lower().strip()]


def generate_angle_queries(question: str) -> list[str]:
    """Generate search queries for each research angle.

    Uses the question itself as the base query when keywords are sparse.
    """
    keywords = extract_keywords(question)
    base = " ".join(keywords[:4])  # limit to 4 keywords to keep queries focused
    queries: list[str] = []
    for angle in _ANGLE_TEMPLATES:
        queries.append(f"{base} {angle}")
    return queries


# ---------------------------------------------------------------------------
# Research synthesis
# ---------------------------------------------------------------------------


def format_source(source: dict[str, Any]) -> str:
    """Format a single search result into a readable entry."""
    title = source.get("title", "Untitled")
    url = source.get("url", "")
    content = source.get("content", "")
    snippet = content.strip() if content else "(no content available)"
    return (
        f"  Source: {title}\n"
        f"  URL:    {url}\n"
        f"  ---\n"
        f"  {snippet[:600]}\n"
    )


def synthesize_report(
    question: str, angle_queries: list[str], results: list[list[dict[str, Any]]]
) -> str:
    """Combine all angle-search results into a single structured report."""
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("DEEP RESEARCH REPORT")
    lines.append("=" * 72)
    lines.append(f"Question: {question}")
    lines.append(f"Angles explored: {len(angle_queries)}")
    lines.append("=" * 72)
    lines.append("")

    total_sources = 0
    for i, (query, sources) in enumerate(zip(angle_queries, results)):
        section_label = _ANGLE_TEMPLATES[i] if i < len(_ANGLE_TEMPLATES) else f"angle-{i}"
        lines.append(f"--- Section {i + 1}: {section_label}")
        lines.append(f"    Search query: {query}")
        lines.append("")

        if not sources:
            lines.append("  (No results found for this angle.)")
            lines.append("")
            continue

        for src in sources:
            lines.append(format_source(src))
            lines.append("")
            total_sources += 1

    # Summary footer
    lines.append("-" * 72)
    lines.append(f"Total sources cited: {total_sources}")
    lines.append(f"Angles investigated: {len(angle_queries)}")
    lines.append("-" * 72)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

server = Server("deep-research")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="deep_research",
            description=(
                "Perform multi-angle research on a question. "
                "Generates 3-5 research subtopics, searches the web for each "
                "via Tavily, and returns a structured report."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The research question or topic to investigate.",
                    }
                },
                "required": ["question"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != "deep_research":
        raise ValueError(f"Unknown tool: {name}")

    question: str = arguments.get("question", "").strip()
    if not question:
        return [TextContent(
            type="text",
            text="Error: 'question' parameter is required and must be non-empty.",
        )]

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return [TextContent(
            type="text",
            text=(
                "Error: TAVILY_API_KEY environment variable is not set.\n\n"
                "Please set it before running the server, e.g.:\n"
                "  export TAVILY_API_KEY='your-key-here'"
            ),
        )]

    # 1. Generate angle queries
    angle_queries = generate_angle_queries(question)

    # 2. Execute searches in parallel
    async def search_angle(query: str) -> list[dict[str, Any]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, tavily_search, query, api_key)

    try:
        results: list[list[dict[str, Any]]] = await asyncio.gather(
            *(search_angle(q) for q in angle_queries),
            return_exceptions=True,
        )
    except Exception as exc:
        return [TextContent(
            type="text",
            text=f"Unexpected error during parallel search: {exc}",
        )]

    # 3. Handle individual search errors
    cleaned_results: list[list[dict[str, Any]]] = []
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            cleaned_results.append([])
        else:
            cleaned_results.append(res)

    # 4. Synthesise the report
    report = synthesize_report(question, angle_queries, cleaned_results)

    return [TextContent(type="text", text=report)]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    async with stdio_server() as (read, write):
        await server.run(
        read, write,
        InitializationOptions(
            server_name="mcp-deep-research",
            server_version="1.0.0",
            capabilities=ServerCapabilities(tools=ToolsCapability(list_changed=True))
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
