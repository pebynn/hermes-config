#!/usr/bin/env python3
"""
quarterly_hermes_ecosystem_scan.py

Quarterly scanner for awesome-hermes-agent (github.com/0xNyk/awesome-hermes-agent).
Compares current README entries against a stored snapshot, reports new/removed
projects. Designed for no_agent cron: stdout IS the delivery channel.

Cron schedule: 0 9 1 */3 *  (quarterly, first day of month)

Exit codes:
  0 — success (silent if no changes, message on stdout if changes found)
  1 — fetch/parse error (stderr logged, cron notified)
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
import urllib.error
import time
from datetime import date, datetime, timezone
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────

README_URL = (
    "https://raw.githubusercontent.com/0xNyk/"
    "awesome-hermes-agent/main/README.md"
)
SNAPSHOT_PATH = Path.home() / ".hermes/scripts/awesome_hermes_last_scan.json"
REPORT_DIR = Path.home() / ".hermes/kanban/workspaces"
REQUEST_TIMEOUT = 60  # seconds
MAX_RETRIES = 2

# Regex to match a project bullet entry:
#   - **[maturity]** [name](url) by [author](url) - description
# Group 1: maturity (production|beta|experimental)
# Group 2: project name
# Group 3: project URL
# Group 4: author name
# Group 5: author URL
# Group 6: description (rest of line)
BULLET_RE = re.compile(
    r"^\s*-\s*\*\*\[("
    r"production|beta|experimental"
    r")\]\*\*\s*\[([^\]]+)\]\(([^)]+)\)\s+by\s+\[([^\]]+)\]\(([^)]+)\)"
    r"\s*-\s*(.+)$",
    re.MULTILINE,
)


# ── Core Functions ───────────────────────────────────────────────────────────


def fetch_readme(url: str = README_URL) -> str:
    """Fetch the awesome-hermes-agent README with retries.

    Returns:
        Raw markdown text.

    Raises:
        RuntimeError: On network failure after all retries.
    """
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "hermes-ecosystem-scanner/1.0"},
            )
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)  # exponential backoff: 1s, 2s
                continue
    raise RuntimeError(
        f"Failed to fetch README after {MAX_RETRIES + 1} attempts: {last_error}"
    )


def parse_entries(text: str) -> list[dict[str, str]]:
    """Extract all project entries from the README markdown.

    Each entry is a dict with keys: name, url, maturity, author, author_url,
    description.  Only lines matching the **maturity** bullet pattern are
    captured.

    Args:
        text: Raw README markdown.

    Returns:
        List of parsed entry dicts.
    """
    entries: list[dict[str, str]] = []
    for m in BULLET_RE.finditer(text):
        entries.append(
            {
                "name": m.group(2).strip(),
                "url": m.group(3).strip(),
                "maturity": m.group(1),
                "author": m.group(4).strip(),
                "author_url": m.group(5).strip(),
                "description": m.group(6).strip(),
            }
        )
    return entries


def load_snapshot(path: Path) -> list[dict[str, str]]:
    """Load the last-scan snapshot from JSON.

    Returns an empty list if the file does not exist (first run).
    """
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        print(
            f"Warning: corrupt snapshot at {path}, treating as empty",
            file=sys.stderr,
        )
        return []


def save_snapshot(path: Path, entries: list[dict[str, str]]) -> None:
    """Persist the current entries as the new snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def diff_entries(
    current: list[dict[str, str]],
    last: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Diff current entries against last snapshot.

    Matches by ('name', 'url') tuple — the natural key for an awesome-list
    entry (same project won't appear at a different URL).

    Returns:
        (new_entries, removed_entries)
    """
    current_keys = {(e["name"], e["url"]): e for e in current}
    last_keys = {(e["name"], e["url"]): e for e in last}

    current_set = set(current_keys)
    last_set = set(last_keys)

    new = [current_keys[k] for k in (current_set - last_set)]
    removed = [last_keys[k] for k in (last_set - current_set)]

    # Sort for deterministic output (use .get for robustness)
    new.sort(key=lambda e: (e.get("maturity", ""), e["name"].lower()))
    removed.sort(key=lambda e: (e.get("maturity", ""), e["name"].lower()))

    return new, removed


def generate_report(
    new: list[dict[str, str]],
    removed: list[dict[str, str]],
    scan_date: str,
) -> str | None:
    """Generate a Markdown report for the scan.

    Returns None if there are no changes (enables silent exit).
    """
    if not new and not removed:
        return None

    lines: list[str] = []
    lines.append("# Awesome Hermes Agent — Ecosystem Scan")
    lines.append("")
    lines.append(f"**Scan date**: {scan_date}")
    lines.append(
        f"**Source**: [{README_URL}]({README_URL})"
    )
    lines.append("")

    total = len(new) + len(removed)
    lines.append(f"**Changes detected**: {total} entry(s)")
    lines.append("")

    if new:
        lines.append("## 🆕 New Entries")
        lines.append("")
        lines.append("| Maturity | Project | Author | Description |")
        lines.append("|:--|:--|:--|:--|")
        for e in new:
            desc = e.get("description", "")[:120]
            author_url = e.get("author_url", e.get("url", ""))
            lines.append(
                f"| {e.get('maturity', '')} "
                f"| [{e['name']}]({e['url']}) "
                f"| [{e['author']}]({author_url}) "
                f"| {desc} |"
            )
        lines.append("")

    if removed:
        lines.append("## ❌ Removed Entries")
        lines.append("")
        lines.append("| Maturity | Project | Author | Description |")
        lines.append("|:--|:--|:--|:--|")
        for e in removed:
            desc = e.get("description", "")[:120]
            author_url = e.get("author_url", e.get("url", ""))
            lines.append(
                f"| {e.get('maturity', '')} "
                f"| [{e['name']}]({e['url']}) "
                f"| [{e['author']}]({author_url}) "
                f"| {desc} |"
            )
        lines.append("")

    lines.append("---")
    lines.append(
        f"*Report generated by `quarterly_hermes_ecosystem_scan.py` "
        f"at {datetime.now(timezone.utc).isoformat()}*"
    )

    return "\n".join(lines)


def write_report(report: str, scan_date: str) -> Path:
    """Write the report to a timestamped file.

    Returns:
        Path to the written report file.
    """
    report_dir = REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    filename = f"ecosystem_scan_{scan_date}.md"
    path = report_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    return path


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    """Entry point. Returns exit code."""
    try:
        # 1. Fetch current README
        text = fetch_readme()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # 2. Parse entries
    current_entries = parse_entries(text)
    if not current_entries:
        print(
            "ERROR: parsed 0 entries from README — format may have changed",
            file=sys.stderr,
        )
        return 1

    # 3. Load last snapshot
    last_entries = load_snapshot(SNAPSHOT_PATH)

    # 4. First run? Save baseline silently
    if not last_entries:
        save_snapshot(SNAPSHOT_PATH, current_entries)
        print(
            f"First run: saved baseline with {len(current_entries)} entries. "
            f"Next scan will detect changes.",
            file=sys.stderr,
        )
        return 0

    # 5. Diff
    new, removed = diff_entries(current_entries, last_entries)

    # 6. Generate report
    today = date.today().isoformat()
    report = generate_report(new, removed, today)

    if report is None:
        # No changes — update snapshot silently, no stdout
        save_snapshot(SNAPSHOT_PATH, current_entries)
        return 0

    # 7. Changes found — write report, print to stdout, update snapshot
    report_path = write_report(report, today)
    save_snapshot(SNAPSHOT_PATH, current_entries)

    # Print report to stdout → delivered as message by no_agent cron
    print(report)
    print(f"\nReport saved to: {report_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
