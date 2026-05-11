#!/usr/bin/env python3
"""
doc-audit.py — Documentation quality audit for a project directory.

Scans all README.md files, checks completeness, link validity,
code block language tags, and staleness. Outputs a JSON report.

Usage:
    python3 doc-audit.py /path/to/project
    python3 doc-audit.py /path/to/project --verbose
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_SECTIONS = [
    ("what", re.compile(r"^#+\s*(what|overview|about)", re.IGNORECASE | re.MULTILINE)),
    ("why", re.compile(r"^#+\s*(why|motivation|background)", re.IGNORECASE | re.MULTILINE)),
    ("quickstart", re.compile(r"^#+\s*(quick\s*start|getting\s*started|usage)", re.IGNORECASE | re.MULTILINE)),
    ("api", re.compile(r"^#+\s*(api|reference|api\s*reference)", re.IGNORECASE | re.MULTILINE)),
]

STALE_DAYS = 180  # ~6 months

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
CODE_BLOCK_RE = re.compile(r"```(\w*)")


def find_readme_files(directory: Path) -> list[Path]:
    """Find all README.md files recursively."""
    return sorted(directory.rglob("README.md"))


def check_sections(content: str) -> list[dict]:
    """Check which required sections are present."""
    issues = []
    for name, pattern in REQUIRED_SECTIONS:
        if not pattern.search(content):
            issues.append({"section": name, "severity": "warning", "detail": f"Missing '{name}' section"})
    return issues


def check_links(content: str, readme_path: Path, repo_root: Path) -> list[dict]:
    """Check markdown links for validity."""
    issues = []
    for match in LINK_RE.finditer(content):
        url = match.group(2).strip()
        # Skip external URLs, anchors, and mailto
        if url.startswith(("http://", "https://", "#", "mailto:")):
            continue
        # Resolve relative path
        target = (readme_path.parent / url).resolve()
        try:
            target = target.relative_to(repo_root)
        except ValueError:
            pass
        if not (repo_root / target).exists():
            issues.append({
                "severity": "error",
                "detail": f"Broken link: '{url}' (resolved to '{target}')",
            })
    return issues


def check_code_blocks(content: str) -> list[dict]:
    """Check if code blocks have language tags."""
    issues = []
    for match in CODE_BLOCK_RE.finditer(content):
        lang = match.group(1).strip()
        if not lang:
            issues.append({
                "severity": "warning",
                "detail": "Code block without language tag",
            })
    return issues


def check_staleness(readme_path: Path) -> list[dict]:
    """Check if the README is stale (>6 months old)."""
    issues = []
    try:
        mtime = os.path.getmtime(readme_path)
        mod_time = datetime.fromtimestamp(mtime, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - mod_time
        if delta.days > STALE_DAYS:
            issues.append({
                "severity": "warning",
                "detail": f"File not modified in {delta.days} days (> {STALE_DAYS} days threshold)",
            })
    except OSError as e:
        issues.append({
            "severity": "error",
            "detail": f"Cannot read modification time: {e}",
        })
    return issues


def audit_file(readme_path: Path, repo_root: Path) -> dict:
    """Run all checks on a single README.md file."""
    try:
        content = readme_path.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "file": str(readme_path),
            "score": 0,
            "issues": [{"severity": "error", "detail": f"Cannot read file: {e}"}],
            "suggestions": ["Check file encoding and permissions"],
        }

    issues = []
    suggestions = []

    # Section checks
    section_issues = check_sections(content)
    issues.extend(section_issues)
    if section_issues:
        missing_names = [i["section"] for i in section_issues]
        suggestions.append(f"Add missing section(s): {', '.join(missing_names)}")

    # Link checks
    link_issues = check_links(content, readme_path, repo_root)
    issues.extend(link_issues)
    if link_issues:
        suggestions.append("Fix broken internal links")

    # Code block language tags
    code_issues = check_code_blocks(content)
    issues.extend(code_issues)
    if code_issues:
        suggestions.append("Add language tags to code blocks (e.g., ```python)")

    # Staleness
    stale_issues = check_staleness(readme_path)
    issues.extend(stale_issues)
    if stale_issues:
        suggestions.append("Review and update stale documentation")

    # Calculate score (start at 100, deduct for issues)
    score = 100
    deductions = {"error": 15, "warning": 5}
    for issue in issues:
        sev = issue.get("severity", "warning")
        score -= deductions.get(sev, 5)
    score = max(0, score)

    return {
        "file": str(readme_path),
        "score": score,
        "issues": issues,
        "suggestions": suggestions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit documentation quality in a project directory."
    )
    parser.add_argument(
        "directory",
        type=str,
        help="Path to the project directory to audit",
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

    readme_files = find_readme_files(repo_root)
    if not readme_files:
        report = {
            "score": 0,
            "issues": [{"file": str(repo_root), "severity": "error", "detail": "No README.md files found"}],
            "suggestions": ["Create a top-level README.md"],
        }
        print(json.dumps(report, indent=2))
        return

    results = [audit_file(f, repo_root) for f in readme_files]

    total_score = sum(r["score"] for r in results) / len(results) if results else 0
    all_issues = []
    for r in results:
        for i in r["issues"]:
            all_issues.append({
                "file": r["file"],
                "severity": i["severity"],
                "detail": i["detail"],
            })
    all_suggestions = list(set(s for r in results for s in r["suggestions"]))

    report = {
        "score": round(total_score, 1),
        "files_audited": len(results),
        "issues": all_issues,
        "suggestions": sorted(all_suggestions),
    }

    print(json.dumps(report, indent=2))

    if args.verbose:
        for r in results:
            print(f"\n--- {r['file']} (score: {r['score']}) ---", file=sys.stderr)
            for i in r["issues"]:
                print(f"  [{i['severity'].upper()}] {i['detail']}", file=sys.stderr)

    if any(i["severity"] == "error" for i in all_issues):
        sys.exit(1)


if __name__ == "__main__":
    main()
