#!/usr/bin/env python3
"""
markdown-link-check.py — Check markdown links across a project.

Scans all .md files in a directory, extracts [text](url) links,
checks internal links (relative paths) exist on filesystem.
Reports broken links with file:line location.

Usage:
    python3 markdown-link-check.py /path/to/project
    python3 markdown-link-check.py /path/to/project --exclude node_modules
"""

import argparse
import json
import re
import sys
from pathlib import Path


LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def find_md_files(directory: Path, exclude_dirs: set[str]) -> list[Path]:
    """Find all .md files recursively, skipping excluded directories."""
    files = []
    for p in directory.rglob("*.md"):
        # Check if any parent is in exclude_dirs
        if any(part in exclude_dirs for part in p.relative_to(directory).parts):
            continue
        files.append(p)
    return sorted(files)


def check_file(file_path: Path, repo_root: Path) -> list[dict]:
    """Extract and check all links in a markdown file."""
    broken_links = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return [{"file": str(file_path), "line": 1, "url": "(file)", "reason": f"Cannot read: {e}"}]

    lines = content.split("\n")

    for line_num, line in enumerate(lines, 1):
        for match in LINK_RE.finditer(line):
            url = match.group(2).strip()

            # Skip external URLs and anchors
            if url.startswith(("http://", "https://", "#", "mailto:")):
                continue

            # Resolve relative path
            target = (file_path.parent / url).resolve()

            # Check if target is a directory with README
            if target.is_dir():
                readme = target / "README.md"
                if readme.exists():
                    continue

            if not target.exists():
                broken_links.append({
                    "file": str(file_path),
                    "line": line_num,
                    "url": url,
                    "reason": f"File not found (resolved: {target})",
                })

    return broken_links


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check markdown links for validity across a project."
    )
    parser.add_argument(
        "directory",
        type=str,
        help="Path to the project directory",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        nargs="*",
        default=["node_modules", ".git", "__pycache__", "dist", "build", ".venv", "venv"],
        help="Directory names to exclude (default: node_modules .git __pycache__ dist build .venv venv)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output",
    )
    args = parser.parse_args()

    repo_root = Path(args.directory).resolve()
    if not repo_root.is_dir():
        print(json.dumps({"error": f"Directory not found: {repo_root}"}, indent=2))
        sys.exit(1)

    exclude_set = set(args.exclude)
    md_files = find_md_files(repo_root, exclude_set)

    if not md_files:
        print(json.dumps({"total_links": 0, "broken": [], "files_checked": 0}))
        return

    all_broken = []
    total_links = 0

    for md_file in md_files:
        broken = check_file(md_file, repo_root)
        all_broken.extend(broken)

        # Count total links for stats
        try:
            content = md_file.read_text(encoding="utf-8")
            total_links += len(LINK_RE.findall(content))
        except Exception:
            pass

    report = {
        "total_links": total_links,
        "broken": all_broken,
        "files_checked": len(md_files),
        "broken_count": len(all_broken),
    }

    print(json.dumps(report, indent=2))

    if args.verbose and all_broken:
        print(f"\n--- Broken Links ({len(all_broken)} total) ---", file=sys.stderr)
        for b in all_broken:
            print(f"  {b['file']}:{b['line']}  {b['url']}  ({b['reason']})", file=sys.stderr)

    if all_broken:
        sys.exit(1)


if __name__ == "__main__":
    main()
