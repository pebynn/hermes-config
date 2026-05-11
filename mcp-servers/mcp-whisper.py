#!/usr/bin/env python3
"""
MCP Server: whisper-stt
Exposes speech-to-text via MCP tools using openai-whisper (system Python, not venv).
"""
# mcp-server.py
import asyncio
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ServerCapabilities, ToolsCapability
import json
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server



# --- Configuration ---
SERVER_NAME = "whisper-stt"
WHISPER_CLI = "/home/pebynn/.local/bin/whisper"
SYSTEM_PYTHON = "python3"
WHISPER_MODEL = "base"
WHISPER_OUTPUT_DIR = "/tmp/whisper_out"

server = Server(SERVER_NAME)


def _whisper_transcribe(audio_path: str) -> str:
    """Run whisper on a local audio file and return the transcribed text."""
    abs_path = os.path.abspath(audio_path)
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"Audio file not found: {abs_path}")

    # Ensure output directory exists
    os.makedirs(WHISPER_OUTPUT_DIR, exist_ok=True)

    result = subprocess.run(
        [
            WHISPER_CLI,
            abs_path,
            "--model", WHISPER_MODEL,
            "--output_format", "txt",
            "--output_dir", WHISPER_OUTPUT_DIR,
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        raise RuntimeError(f"Whisper transcription failed: {error_msg}")

    # Read the output text file
    base_name = os.path.splitext(os.path.basename(abs_path))[0]
    output_path = os.path.join(WHISPER_OUTPUT_DIR, f"{base_name}.txt")

    if not os.path.isfile(output_path):
        # whisper might use the full basename including extension
        alt_base = os.path.basename(abs_path)
        output_path = os.path.join(WHISPER_OUTPUT_DIR, f"{alt_base}.txt")

    if not os.path.isfile(output_path):
        raise RuntimeError(
            f"Whisper output file not found at {output_path}. "
            f"Stdout: {result.stdout[:500]}. Stderr: {result.stderr[:500]}"
        )

    with open(output_path, "r") as f:
        text = f.read().strip()

    return text


def _cleanup_temp_files(*paths: str) -> None:
    """Remove temporary files, ignoring errors."""
    for path in paths:
        try:
            if path and os.path.isfile(path):
                os.unlink(path)
        except OSError:
            pass


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="transcribe_file",
            description="Transcribe an audio file from a local file path using whisper",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path to the audio file",
                    }
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="transcribe_url",
            description="Download audio from a URL and transcribe it using whisper",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the audio file to download and transcribe",
                    }
                },
                "required": ["url"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "transcribe_file":
        audio_path = arguments.get("path", "")
        if not audio_path:
            return [TextContent(type="text", text="Error: 'path' argument is required")]

        try:
            text = _whisper_transcribe(audio_path)
            return [TextContent(type="text", text=text)]
        except FileNotFoundError as e:
            return [TextContent(type="text", text=f"Error: {e}")]
        except subprocess.TimeoutExpired:
            return [TextContent(type="text", text="Error: Transcription timed out after 300 seconds")]
        except RuntimeError as e:
            return [TextContent(type="text", text=f"Error: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Unexpected error: {e}")]

    elif name == "transcribe_url":
        url = arguments.get("url", "")
        if not url:
            return [TextContent(type="text", text="Error: 'url' argument is required")]

        temp_file = None
        try:
            # Download audio to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
                temp_file = tmp.name

            urllib.request.urlretrieve(url, temp_file)

            text = _whisper_transcribe(temp_file)
            return [TextContent(type="text", text=text)]

        except urllib.error.URLError as e:
            return [TextContent(type="text", text=f"Error downloading audio: {e.reason}")]
        except subprocess.TimeoutExpired:
            return [TextContent(type="text", text="Error: Transcription timed out after 300 seconds")]
        except RuntimeError as e:
            return [TextContent(type="text", text=f"Error: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Unexpected error: {e}")]
        finally:
            if temp_file:
                _cleanup_temp_files(temp_file)
    else:
        return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]


async def main():
    async with stdio_server() as (read, write):
        await server.run(
        read, write,
        InitializationOptions(
            server_name="mcp-whisper",
            server_version="1.0.0",
            capabilities=ServerCapabilities(tools=ToolsCapability(list_changed=True))
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
