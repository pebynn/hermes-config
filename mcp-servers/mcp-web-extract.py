#!/usr/bin/env python3
"""MCP server for web page content extraction via Jina Reader with Crawl4AI fallback."""
# mcp-server.py
import asyncio
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ServerCapabilities, ToolsCapability
import urllib.request
import urllib.error
import traceback
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server




server = Server("web-extract")


def _extract_with_jina(url: str) -> str | None:
    """Try to extract content using Jina Reader. Returns markdown or None on failure."""
    try:
        req = urllib.request.Request(
            f"https://r.jina.ai/{url}",
            headers={"Accept": "text/markdown"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return None


async def _extract_with_crawl4ai(url: str) -> str | None:
    """Fallback: extract content using Crawl4AI."""
    try:
        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            content = result.markdown or result.text or "no content"
            return content
    except Exception:
        return None


async def _extract_single_url(url: str) -> str:
    """Extract content from a single URL. Jina Reader first, then Crawl4AI."""
    # Try Jina Reader first
    jina_content = _extract_with_jina(url)
    if jina_content is not None:
        return jina_content

    # Fallback to Crawl4AI
    crawl_content = await _extract_with_crawl4ai(url)
    if crawl_content is not None:
        return crawl_content

    return f"Error: Failed to extract content from {url} using both Jina Reader and Crawl4AI."


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="extract_url",
            description="Extract content from a single URL. Uses Jina Reader first, falls back to Crawl4AI.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to extract content from",
                    }
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="extract_bulk",
            description="Extract content from multiple URLs (max 5). Each URL uses Jina Reader first, falls back to Crawl4AI.",
            inputSchema={
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of URLs to extract content from (max 5)",
                        "maxItems": 5,
                    }
                },
                "required": ["urls"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "extract_url":
        url = arguments["url"]
        try:
            content = await _extract_single_url(url)
            return [TextContent(type="text", text=content)]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"Error extracting {url}: {e}\n{traceback.format_exc()}",
                )
            ]

    elif name == "extract_bulk":
        urls = arguments["urls"]
        if len(urls) > 5:
            return [
                TextContent(
                    type="text",
                    text=f"Error: Maximum 5 URLs allowed, got {len(urls)}.",
                )
            ]

        results = []
        for url in urls:
            try:
                content = await _extract_single_url(url)
                # Truncate each result to avoid overly large responses
                if len(content) > 50000:
                    content = content[:50000] + "\n\n[... content truncated at 50000 chars ...]"
                results.append(f"=== {url} ===\n\n{content}")
            except Exception as e:
                results.append(
                    f"=== {url} ===\n\nError: {e}\n{traceback.format_exc()}"
                )

        return [TextContent(type="text", text="\n\n---\n\n".join(results))]

    else:
        return [
            TextContent(
                type="text",
                text=f"Error: Unknown tool '{name}'",
            )
        ]


async def main():
    async with stdio_server() as (read, write):
        await server.run(
        read, write,
        InitializationOptions(
            server_name="mcp-web-extract",
            server_version="1.0.0",
            capabilities=ServerCapabilities(tools=ToolsCapability(list_changed=True))
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
