#!/usr/bin/env python3
"""MCP server for web search via Tavily API."""
# mcp-server.py
import asyncio
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ServerCapabilities, ToolsCapability
import json
import os
import urllib.request
import urllib.error
import urllib.parse

from mcp.server import Server
from mcp.server.stdio import stdio_server




server = Server("web-search")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="web_search",
            description="Search the web using Tavily API. Returns a list of results with title, URL, and content summary.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != "web_search":
        raise ValueError(f"Unknown tool: {name}")

    query = arguments.get("query", "").strip()
    limit = arguments.get("limit", 5)

    if not query:
        return [TextContent(type="text", text="Error: 'query' parameter is required.")]

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return [
            TextContent(
                type="text",
                text="Error: TAVILY_API_KEY environment variable is not set. "
                "Configure it in your environment to use the web search tool.",
            )
        ]

    try:
        payload = json.dumps({
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": limit,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        # Set a reasonable timeout (15 seconds)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        results = data.get("results", [])

        if not results:
            return [
                TextContent(
                    type="text",
                    text=f"No results found for query: {query}",
                )
            ]

        formatted = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            url = r.get("url", "")
            content = r.get("content", "")
            formatted.append(
                f"Result {i}:\n"
                f"  Title: {title}\n"
                f"  URL:   {url}\n"
                f"  Snippet: {content}\n"
            )

        return [
            TextContent(
                type="text",
                text=f"Search results for '{query}':\n\n" + "\n".join(formatted),
            )
        ]

    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            error_body = ""
        return [
            TextContent(
                type="text",
                text=f"HTTP error {e.code} from Tavily API: {e.reason}\n{error_body}",
            )
        ]
    except urllib.error.URLError as e:
        return [
            TextContent(
                type="text",
                text=f"Connection error accessing Tavily API: {e.reason}",
            )
        ]
    except json.JSONDecodeError:
        return [
            TextContent(
                type="text",
                text="Error: Invalid JSON response from Tavily API.",
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=f"Unexpected error during web search: {e}",
            )
        ]


async def main():
    async with stdio_server() as (read, write):
        await server.run(
        read, write,
        InitializationOptions(
            server_name="mcp-web-search",
            server_version="1.0.0",
            capabilities=ServerCapabilities(tools=ToolsCapability(list_changed=True))
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
