#!/usr/bin/env python3
"""
MCP Server: security-auditor

Provides MCP tools for security auditing/scanning:
  - scan_file(path)         : Scan a single file for secrets, dangerous calls, etc.
  - scan_directory(path)    : Recursively scan a directory for security issues.
  - check_file_permissions(path) : Check file permissions for dangerous settings.

Usage:
    source ~/.hermes/hermes-agent/venv/bin/activate
    python mcp-security-auditor.py
"""

import asyncio
import os
import re
import stat
import fnmatch
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ServerCapabilities, ToolsCapability

# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

SECRET_PATTERNS: list[dict[str, Any]] = [
    # OpenAI / Anthropic / generic sk-... keys
    {
        "pattern": re.compile(r'(?<![a-zA-Z0-9])(sk-[a-zA-Z0-9]{20,})(?![a-zA-Z0-9])'),
        "name": "OpenAI/AI API Key (sk-...)",
        "severity": "HIGH",
    },
    # GitHub personal access tokens
    {
        "pattern": re.compile(r'(?<![a-zA-Z0-9])(ghp_[a-zA-Z0-9]{36,})(?![a-zA-Z0-9])'),
        "name": "GitHub Personal Access Token (ghp_)",
        "severity": "HIGH",
    },
    # GitHub fine-grained access tokens
    {
        "pattern": re.compile(r'(?<![a-zA-Z0-9])(github_pat_[a-zA-Z0-9]{22,})(?![a-zA-Z0-9])'),
        "name": "GitHub Fine-Grained Token (github_pat_)",
        "severity": "HIGH",
    },
    # AWS Access Key ID
    {
        "pattern": re.compile(r'(?<![A-Za-z0-9/+=])(AKIA[A-Z0-9]{16})(?![A-Za-z0-9/+=])'),
        "name": "AWS Access Key ID (AKIA...)",
        "severity": "HIGH",
    },
    # AWS Secret Access Key
    {
        "pattern": re.compile(r'(?<![A-Za-z0-9/+=])([^A-Za-z0-9/+=]?[A-Za-z0-9/+=]{40})'),
        "name": "Possible AWS Secret Access Key (40-char base64)",
        "severity": "HIGH",
    },
    # Generic password/token assignment
    {
        "pattern": re.compile(
            r'(?i)(password|passwd|pwd|secret|token|api_key|apikey|api[_-]?secret)\s*[=:]\s*["\']([^"\'\s]{8,})["\']'
        ),
        "name": "Hard-coded Password/Secret/Token",
        "severity": "HIGH",
    },
    # Private key header
    {
        "pattern": re.compile(r'-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PRIVATE)\s+KEY-----'),
        "name": "Private Key",
        "severity": "HIGH",
    },
    # JWT tokens
    {
        "pattern": re.compile(r'eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}'),
        "name": "JWT Token",
        "severity": "HIGH",
    },
    # Slack token
    {
        "pattern": re.compile(r'(xox[baprs]-[a-zA-Z0-9-]{10,})'),
        "name": "Slack Token",
        "severity": "HIGH",
    },
    # Google API key
    {
        "pattern": re.compile(r'(?i)(AIza[0-9A-Za-z\-_]{35})'),
        "name": "Google API Key",
        "severity": "HIGH",
    },
    # Heroku API key
    {
        "pattern": re.compile(r'(?i)(heroku[a-z0-9_\-]{20,})'),
        "name": "Heroku API Key",
        "severity": "HIGH",
    },
    # Telegram bot token
    {
        "pattern": re.compile(r'(?<![a-zA-Z0-9])([0-9]{8,10}:[a-zA-Z0-9_-]{35})(?![a-zA-Z0-9])'),
        "name": "Telegram Bot Token",
        "severity": "HIGH",
    },
    # Generic connection string with password
    {
        "pattern": re.compile(r'(?i)(postgresql|mysql|mongodb|redis|amqp|rabbitmq)://[^:]+:[^@]+@'),
        "name": "Database Connection String with Password",
        "severity": "HIGH",
    },
]

DANGEROUS_CALL_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern": re.compile(r'\beval\s*\('),
        "name": "Dangerous call: eval()",
        "severity": "MEDIUM",
    },
    {
        "pattern": re.compile(r'\bexec\s*\('),
        "name": "Dangerous call: exec()",
        "severity": "MEDIUM",
    },
    {
        "pattern": re.compile(r'\bos\.system\s*\('),
        "name": "Dangerous call: os.system()",
        "severity": "MEDIUM",
    },
    {
        "pattern": re.compile(r'\bsubprocess\s*\.\s*(?:call|Popen|run|check_output)\s*\([^)]*shell\s*=\s*True'),
        "name": "Dangerous call: subprocess with shell=True",
        "severity": "MEDIUM",
    },
    {
        "pattern": re.compile(r'\b__import__\s*\('),
        "name": "Dangerous call: __import__()",
        "severity": "MEDIUM",
    },
    {
        "pattern": re.compile(r'\bcompile\s*\('),
        "name": "Dangerous call: compile()",
        "severity": "LOW",
    },
    {
        "pattern": re.compile(r'\bpickle\.\s*(?:loads|load)\s*\('),
        "name": "Insecure deserialization: pickle",
        "severity": "MEDIUM",
    },
    {
        "pattern": re.compile(r'\byaml\.\s*(?:load|dump)\s*\([^)]*Loader\s*=\s*yaml\.\s*FullLoader'),
        "name": "YAML load with safe/dangerous loader",
        "severity": "LOW",
    },
    {
        "pattern": re.compile(r'\binput\s*\('),
        "name": "Potential unsafe input(/) in Python 2 context (or debug code)",
        "severity": "LOW",
    },
]

SUSPICIOUS_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern": re.compile(r'(?i)(?:TODO|FIXME|HACK|XXX|DEBUG)\s*[:]?\s*'),
        "name": "Debug/TODO/FIXME marker",
        "severity": "LOW",
    },
    {
        "pattern": re.compile(r'(?i)(?:print|console\.log|printf)\s*\('),
        "name": "Print/debug statement (potential leftover debug code)",
        "severity": "LOW",
    },
    {
        "pattern": re.compile(r'\b(?:127\.0\.0\.1|localhost)\b', re.IGNORECASE),
        "name": "Hard-coded localhost / loopback IP",
        "severity": "LOW",
    },
    {
        "pattern": re.compile(r'\b(?:0\.0\.0\.0)\b'),
        "name": "Wildcard bind address (0.0.0.0) — potential exposure",
        "severity": "LOW",
    },
]

# File patterns to skip (binary, images, archives, etc.)
BINARY_EXTENSIONS: set[str] = {
    ".pyc", ".pyo", ".so", ".o", ".a", ".lib", ".dll", ".dylib",
    ".exe", ".msi", ".bin", ".dat",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico", ".svg",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".rar", ".7z",
    ".mp3", ".mp4", ".avi", ".mkv", ".mov",
    ".woff", ".woff2", ".ttf", ".eot",
    ".db", ".sqlite", ".sqlite3",
}

# Directories to skip
SKIP_DIRS: set[str] = {
    ".git", ".svn", ".hg", "__pycache__", "node_modules",
    ".venv", "venv", "env", ".env", "dist", "build", ".tox",
    "vendor", "bower_components", ".mypy_cache", ".pytest_cache",
    ".hypothesis", ".eggs", "eggs", ".terraform",
}

# Config files that commonly contain secrets
SENSITIVE_CONFIG_FILES: set[str] = {
    ".env", ".env.local", ".env.production", ".env.staging",
    ".env.example",  # examples often have dummy passwords
    ".env.development", ".env.test",
}

# Files that might contain private keys or credentials
SENSITIVE_FILENAMES: set[str] = {
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    "id_rsa.pub",  # public keys are harmless, but still worth flagging
}


# ---------------------------------------------------------------------------
# Helper: find all pattern matches on a single line
# ---------------------------------------------------------------------------

def _match_secrets(line: str, line_num: int) -> list[dict[str, Any]]:
    """Check a single line against all secret patterns."""
    findings: list[dict[str, Any]] = []
    for entry in SECRET_PATTERNS:
        for m in entry["pattern"].finditer(line):
            findings.append({
                "line": line_num,
                "severity": entry["severity"],
                "description": f"{entry['name']} detected: {m.group(0)[:40]}{'...' if len(m.group(0)) > 40 else ''}",
                "match": m.group(0)[:60],
            })
    return findings


def _match_dangerous_calls(line: str, line_num: int) -> list[dict[str, Any]]:
    """Check a single line against dangerous call patterns."""
    findings: list[dict[str, Any]] = []
    for entry in DANGEROUS_CALL_PATTERNS:
        for m in entry["pattern"].finditer(line):
            findings.append({
                "line": line_num,
                "severity": entry["severity"],
                "description": entry["name"],
                "match": m.group(0)[:60],
            })
    return findings


def _match_suspicious(line: str, line_num: int) -> list[dict[str, Any]]:
    """Check a single line against suspicious / low-severity patterns."""
    findings: list[dict[str, Any]] = []
    for entry in SUSPICIOUS_PATTERNS:
        for m in entry["pattern"].finditer(line):
            findings.append({
                "line": line_num,
                "severity": entry["severity"],
                "description": entry["name"],
                "match": m.group(0)[:60],
            })
    return findings


# ---------------------------------------------------------------------------
# Core scanning logic
# ---------------------------------------------------------------------------

def _scan_file_content(path: str, content: str) -> list[dict[str, Any]]:
    """Scan file content and return all findings."""
    findings: list[dict[str, Any]] = []
    lines = content.splitlines()

    for line_num, line in enumerate(lines, start=1):
        findings.extend(_match_secrets(line, line_num))
        findings.extend(_match_dangerous_calls(line, line_num))
        findings.extend(_match_suspicious(line, line_num))

    return findings


def _is_binary(path: str) -> bool:
    """Quick heuristic: skip known binary extensions."""
    _, ext = os.path.splitext(path)
    if ext.lower() in BINARY_EXTENSIONS:
        return True
    return False


def _should_skip(path: str) -> bool:
    """Return True if a file/directory should be skipped."""
    if _is_binary(path):
        return True
    # Skip based on file name patterns
    fname = os.path.basename(path)
    for skip in SKIP_DIRS:
        if fname.startswith(skip):
            return True
    return False


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def scan_file(path: str) -> list[TextContent]:
    """Scan a single file for security issues."""
    resolved = os.path.abspath(os.path.expanduser(path))

    if not os.path.exists(resolved):
        return [TextContent(
            type="text",
            text=f"ERROR: File not found: {resolved}",
        )]
    if not os.path.isfile(resolved):
        return [TextContent(
            type="text",
            text=f"ERROR: Not a file: {resolved}",
        )]

    try:
        # Try reading as text
        with open(resolved, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except PermissionError:
        return [TextContent(
            type="text",
            text=f"ERROR: Permission denied reading file: {resolved}",
        )]
    except Exception as exc:
        return [TextContent(
            type="text",
            text=f"ERROR: Could not read file {resolved}: {exc}",
        )]

    findings = _scan_file_content(resolved, content)

    if not findings:
        return [TextContent(
            type="text",
            text=f"No issues found in {resolved}",
        )]

    # Group by severity for clean output
    lines_out: list[str] = []
    lines_out.append(f"Scan results for: {resolved}")
    lines_out.append(f"Total findings: {len(findings)}")
    lines_out.append("")

    # Sort: HIGH first, then MEDIUM, then LOW
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    findings_sorted = sorted(findings, key=lambda f: (severity_order.get(f["severity"], 99), f["line"]))

    for f in findings_sorted:
        sev = f["severity"]
        sev_label = sev
        lines_out.append(f"  [{sev_label}] Line {f['line']}: {f['description']}")

    return [TextContent(type="text", text="\n".join(lines_out))]


async def scan_directory(path: str) -> list[TextContent]:
    """Recursively scan a directory for security issues."""
    resolved = os.path.abspath(os.path.expanduser(path))

    if not os.path.exists(resolved):
        return [TextContent(
            type="text",
            text=f"ERROR: Path not found: {resolved}",
        )]
    if not os.path.isdir(resolved):
        return [TextContent(
            type="text",
            text=f"ERROR: Not a directory: {resolved}",
        )]

    all_findings: dict[str, list[dict[str, Any]]] = {}
    files_scanned = 0
    files_with_issues = 0
    total_findings = 0

    try:
        for root, dirs, files in os.walk(resolved, followlinks=False):
            # Prune skip directories in-place
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for fname in files:
                fpath = os.path.join(root, fname)

                if _should_skip(fpath):
                    continue

                # Check if it's a sensitive config file
                rel_path = os.path.relpath(fpath, resolved)
                is_sensitive = (fname in SENSITIVE_CONFIG_FILES or fname in SENSITIVE_FILENAMES)

                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read()
                except (PermissionError, UnicodeDecodeError, OSError):
                    continue

                files_scanned += 1
                findings = _scan_file_content(fpath, content)

                # Even if no patterns matched, flag sensitive config files
                if not findings and is_sensitive:
                    findings.append({
                        "line": 1,
                        "severity": "LOW",
                        "description": f"Sensitive config file present: {fname}",
                        "match": "",
                    })

                if findings:
                    files_with_issues += 1
                    total_findings += len(findings)
                    all_findings[rel_path] = findings

    except PermissionError as exc:
        return [TextContent(
            type="text",
            text=f"ERROR: Permission denied accessing directory {resolved}: {exc}",
        )]
    except Exception as exc:
        return [TextContent(
            type="text",
            text=f"ERROR: Failed to scan directory {resolved}: {exc}",
        )]

    if not all_findings:
        return [TextContent(
            type="text",
            text=f"No security issues found in {resolved} (scanned {files_scanned} files).",
        )]

    # Build summary
    lines_out: list[str] = []
    lines_out.append(f"Security scan summary for: {resolved}")
    lines_out.append(f"  Files scanned : {files_scanned}")
    lines_out.append(f"  Files with issues: {files_with_issues}")
    lines_out.append(f"  Total findings: {total_findings}")
    lines_out.append("")

    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

    for rel_path in sorted(all_findings.keys()):
        findings = all_findings[rel_path]
        # Count severities
        high = sum(1 for f in findings if f["severity"] == "HIGH")
        med = sum(1 for f in findings if f["severity"] == "MEDIUM")
        low = sum(1 for f in findings if f["severity"] == "LOW")

        sev_counts = []
        if high:
            sev_counts.append(f"{high} HIGH")
        if med:
            sev_counts.append(f"{med} MEDIUM")
        if low:
            sev_counts.append(f"{low} LOW")

        lines_out.append(f"  {rel_path}: {', '.join(sev_counts)} ({len(findings)} total)")

        # Show detail for files with HIGH findings
        if high > 0:
            for f in sorted(findings, key=lambda x: (severity_order.get(x["severity"], 99), x["line"])):
                if f["severity"] == "HIGH":
                    lines_out.append(f"    [HIGH] Line {f['line']}: {f['description']}")

    return [TextContent(type="text", text="\n".join(lines_out))]


async def check_file_permissions(path: str) -> list[TextContent]:
    """Check if a file has dangerous permissions."""
    resolved = os.path.abspath(os.path.expanduser(path))

    if not os.path.exists(resolved):
        return [TextContent(
            type="text",
            text=f"ERROR: Path not found: {resolved}",
        )]

    if not os.path.isfile(resolved):
        return [TextContent(
            type="text",
            text=f"ERROR: Not a file: {resolved}",
        )]

    try:
        st = os.stat(resolved)
        mode = st.st_mode
        perms = stat.S_IMODE(mode)
    except PermissionError:
        return [TextContent(
            type="text",
            text=f"ERROR: Permission denied accessing {resolved}",
        )]
    except Exception as exc:
        return [TextContent(
            type="text",
            text=f"ERROR: Failed to stat {resolved}: {exc}",
        )]

    issues: list[str] = []
    is_private_key = False
    fname = os.path.basename(resolved)

    # Check if it looks like a private key
    key_names = {"id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}
    if fname in key_names:
        is_private_key = True

    # World-readable
    if perms & stat.S_IROTH:
        issues.append(f"[HIGH] World-readable (other: read)")
        if is_private_key:
            issues.append(f"[HIGH] PRIVATE KEY is world-readable! This is a critical security risk.")

    # World-writable
    if perms & stat.S_IWOTH:
        issues.append(f"[HIGH] World-writable (other: write)")
        if is_private_key:
            issues.append(f"[HIGH] PRIVATE KEY is world-writable! This is a critical security risk.")

    # Group-writable
    if perms & stat.S_IWGRP and is_private_key:
        issues.append(f"[MEDIUM] Group-writable private key")

    # World-executable for a script/key
    if perms & stat.S_IXOTH and is_private_key:
        issues.append(f"[MEDIUM] World-executable private key")

    # Check for suid/sgid
    if mode & stat.S_ISUID:
        issues.append(f"[HIGH] SUID bit set — privilege escalation risk")
    if mode & stat.S_ISGID:
        issues.append(f"[MEDIUM] SGID bit set")

    lines: list[str] = []
    lines.append(f"Permission check for: {resolved}")
    lines.append(f"  Owner  : {st.st_uid} (mode: {oct(perms)})")
    lines.append("")

    if issues:
        for issue in issues:
            lines.append(f"  {issue}")
    else:
        lines.append("  Permissions look safe.")

    return [TextContent(type="text", text="\n".join(lines))]


# ---------------------------------------------------------------------------
# MCP Server Definition
# ---------------------------------------------------------------------------

server = Server("security-auditor")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="scan_file",
            description="Scan a single file for security issues: API keys, secrets, dangerous calls, hard-coded passwords.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path to the file to scan",
                    }
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="scan_directory",
            description="Recursively scan a directory for common security issues: secrets in files, .env/config checks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path to the directory to scan",
                    }
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="check_file_permissions",
            description="Check if a file has dangerous permissions (e.g., world-readable private keys).",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path to the file to check",
                    }
                },
                "required": ["path"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "scan_file":
        path = arguments.get("path", "")
        if not path:
            return [TextContent(type="text", text="ERROR: 'path' argument is required for scan_file")]
        return await scan_file(path)
    elif name == "scan_directory":
        path = arguments.get("path", "")
        if not path:
            return [TextContent(type="text", text="ERROR: 'path' argument is required for scan_directory")]
        return await scan_directory(path)
    elif name == "check_file_permissions":
        path = arguments.get("path", "")
        if not path:
            return [TextContent(type="text", text="ERROR: 'path' argument is required for check_file_permissions")]
        return await check_file_permissions(path)
    else:
        return [TextContent(type="text", text=f"ERROR: Unknown tool: {name}")]


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

async def main() -> None:
    async with stdio_server() as (read, write):
        await server.run(
            read, write,
            InitializationOptions(
                server_name="security-auditor",
                server_version="1.0.0",
                capabilities=ServerCapabilities(tools=ToolsCapability(list_changed=True))
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
