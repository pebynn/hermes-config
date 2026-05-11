#!/usr/bin/env python3
"""
readme-lint.py — Lint a README.md for quality and completeness.

Validates against the '5-second test': project name, one-line description,
Why/QuickStart/Installation/Usage sections. Checks code block fencing and
language tags. Scores 0-100. Outputs JSON.

Usage:
    python3 readme-lint.py README.md
    python3 readme-lint.py README.md --verbose
"""

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_SECTIONS_5SEC = {
    "project_name": {
        "pattern": re.compile(r"^#\s+\S", re.MULTILINE),
        "description": "Project name (level-1 heading)",
    },
    "one_line_desc": {
        "pattern": re.compile(r"^>\s+\S|^[^#\n]*?(?:does|helps|lets|enables|is\s+a)", re.MULTILINE),
        "description": "One-line description (paragraph or blockquote)",
    },
    "why": {
        "pattern": re.compile(r"^#+\s*(why|motivation|background|about)", re.IGNORECASE | re.MULTILINE),
        "description": "Why section",
    },
    "quickstart": {
        "pattern": re.compile(r"^#+\s*(quick\s*start|getting\s*started)", re.IGNORECASE | re.MULTILINE),
        "description": "Quick Start section",
    },
    "installation": {
        "pattern": re.compile(r"^#+\s*(install|setup|prerequisites)", re.IGNORECASE | re.MULTILINE),
        "description": "Installation section",
    },
    "usage": {
        "pattern": re.compile(r"^#+\s*(usage|examples?|how\s*to)", re.IGNORECASE | re.MULTILINE),
        "description": "Usage section",
    },
}


CODE_FENCE_RE = re.compile(r"(```+)")


def lint_readme(readme_path: Path) -> dict:
    """Run all lint checks and return a JSON-serializable report."""
    try:
        content = readme_path.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "pass_5sec_test": False,
            "score": 0,
            "missing_sections": ["(cannot read file)"],
            "issues": [{"severity": "error", "detail": f"Cannot read file: {e}"}],
        }

    issues = []
    missing_sections = []
    present_count = 0

    # 5-second test: check required sections
    for key, info in REQUIRED_SECTIONS_5SEC.items():
        if info["pattern"].search(content):
            present_count += 1
        else:
            missing_sections.append(info["description"])
            issues.append({
                "severity": "warning",
                "detail": f"Missing: {info['description']}",
            })

    pass_5sec = (present_count / len(REQUIRED_SECTIONS_5SEC)) >= 0.5

    # Code block checks
    lines = content.split("\n")
    in_fence = False
    fence_opener = ""
    code_block_lines = []
    block_count = 0
    untagged_blocks = 0

    for i, line in enumerate(lines):
        fence_match = CODE_FENCE_RE.match(line.strip())
        if fence_match:
            if not in_fence:
                in_fence = True
                fence_opener = fence_match.group(1)
                # Check if this opening has a language tag
                rest_line = line.strip()[len(fence_opener):].strip()
                if not rest_line:
                    untagged_blocks += 1
                    issues.append({
                        "severity": "warning",
                        "detail": f"Line {i + 1}: Code block without language tag",
                    })
                block_count += 1
                code_block_lines = []
            else:
                # Closing fence
                in_fence = False
        elif in_fence:
            code_block_lines.append((i + 1, line))

    # Check for unclosed fences
    if in_fence:
        issues.append({
            "severity": "error",
            "detail": "Unclosed code block (EOF reached while inside a fence)",
        })

    # Calculate score
    score = 100
    deductions = {"error": 20, "warning": 5}

    # Section deductions: each missing section costs
    score -= max(0, len(missing_sections) - 1) * 10  # Allow 1 miss for leniency

    for issue in issues:
        sev = issue.get("severity", "warning")
        score -= deductions.get(sev, 5)

    score = max(0, min(100, score))

    return {
        "pass_5sec_test": pass_5sec,
        "score": score,
        "missing_sections": missing_sections,
        "issues": issues,
        "file": str(readme_path),
        "stats": {
            "total_lines": len(lines),
            "code_blocks": block_count,
            "untagged_blocks": untagged_blocks,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lint a README.md for quality and completeness."
    )
    parser.add_argument(
        "readme",
        type=str,
        help="Path to the README.md file",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output",
    )
    args = parser.parse_args()

    path = Path(args.readme).resolve()
    if not path.is_file():
        print(json.dumps({"error": f"File not found: {path}"}, indent=2))
        sys.exit(1)

    report = lint_readme(path)
    print(json.dumps(report, indent=2))

    if args.verbose:
        print(f"\n--- Summary ---", file=sys.stderr)
        print(f"  Score: {report['score']}/100", file=sys.stderr)
        print(f"  Passes 5-second test: {report['pass_5sec_test']}", file=sys.stderr)
        print(f"  Missing sections: {', '.join(report['missing_sections']) or 'none'}", file=sys.stderr)
        print(f"  Issues: {len(report['issues'])}", file=sys.stderr)
        for i in report["issues"]:
            print(f"    [{i['severity'].upper()}] {i['detail']}", file=sys.stderr)

    if report["score"] < 50:
        sys.exit(2)
    if report["issues"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
