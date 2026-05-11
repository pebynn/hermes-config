#!/usr/bin/env python3
"""
research_to_graphify.py — Research → Knowledge Graph pipeline

Reads research output from a kanban workspace (structured markdown),
converts findings to graphify-friendly markdown files under
~/.hermes/research-findings/, which are then indexed by the daily
graphify cron and merged into the global graph.

Pipeline: kanban_complete → this script → ~/.hermes/research-findings/
  → graphify-daily cron (indexes .hermes/) → global graph → graph_search

Idempotent: re-running with same task_id overwrites existing files.

Usage:
  python3 research_to_graphify.py <workspace_dir> --task-id <task_id>
  python3 research_to_graphify.py <workspace_dir> --task-id t_xxx --dry-run
"""
import argparse
import hashlib
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────
HERMES_HOME = Path("/home/pebynn/.hermes")
FINDINGS_DIR = HERMES_HOME / "research-findings"
MAX_FILE_SIZE = 1024 * 100  # skip files larger than 100KB
MAX_FINDING_CHARS = 2000    # truncate finding content to this
MAX_TOTAL_FINDINGS = 100    # safety cap per run


def slugify(text: str) -> str:
    """Generate a filesystem-safe slug from text."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text[:60] or "untitled"


def parse_findings(text: str) -> list[dict]:
    """
    Parse research markdown into findings.
    H1 (#) = research title
    H2 (##) = individual findings
    Returns [{title, content, sources}]
    """
    findings = []
    current_finding = None
    current_lines = []
    sources = []

    for line in text.split('\n'):
        # Detect H2 — start of a new finding
        if line.startswith('## ') and not line.startswith('### '):
            # Save previous finding
            if current_finding:
                content = '\n'.join(current_lines).strip()[:MAX_FINDING_CHARS]
                findings.append({
                    'title': current_finding,
                    'content': content,
                    'sources': sources.copy(),
                })
                sources = []
            current_finding = line.replace('## ', '').strip()
            current_lines = []
        elif current_finding:
            # Collect sources (lines with URLs)
            urls = re.findall(r'https?://[^\s\)\]]+', line)
            if urls:
                sources.extend(urls)
            current_lines.append(line)

    # Last finding
    if current_finding:
        content = '\n'.join(current_lines).strip()[:MAX_FINDING_CHARS]
        findings.append({
            'title': current_finding,
            'content': content,
            'sources': sources.copy(),
        })

    return findings


def read_workspace(workspace_dir: Path) -> list[dict]:
    """Read all markdown files from workspace, return parsed findings."""
    all_findings = []
    research_title = None
    file_count = 0
    finding_count = 0

    if not workspace_dir.exists():
        print(f"❌ Workspace not found: {workspace_dir}")
        sys.exit(1)

    for fpath in sorted(workspace_dir.iterdir()):
        if not fpath.is_file() or not fpath.suffix.lower() in ('.md', '.markdown'):
            continue
        if fpath.stat().st_size > MAX_FILE_SIZE:
            print(f"  ⏭️  Skipping large file: {fpath.name} ({fpath.stat().st_size} bytes)")
            continue

        file_count += 1
        text = fpath.read_text(encoding='utf-8', errors='replace')

        # Extract research title from H1
        for line in text.split('\n'):
            if line.startswith('# ') and not research_title:
                research_title = line.replace('# ', '').strip()
                break

        # Parse findings from this file
        findings = parse_findings(text)
        for f in findings:
            f['source_file'] = fpath.name
            all_findings.append(f)
            finding_count += 1

        if finding_count > MAX_TOTAL_FINDINGS:
            break

    print(f"  📄 {file_count} files scanned")
    print(f"  🔍 {finding_count} findings extracted")
    return all_findings, research_title


def write_findings(
    task_id: str,
    findings: list[dict],
    research_title: str | None,
    workspace_dir: Path,
    dry_run: bool = False,
) -> int:
    """Write findings as structured markdown files. Returns file count."""
    out_dir = FINDINGS_DIR / task_id
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        # Clean old files in this task's directory for idempotency
        for old_file in out_dir.glob("*.md"):
            old_file.unlink()

    written = 0

    if not findings:
        # Write a placeholder even if no findings were parsed
        placeholder = f"""# Research: {research_title or task_id}

*No structured findings extracted. See workspace for full output.*

**Source workspace**: `{workspace_dir}`
**Task**: {task_id}
**Archived**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        if dry_run:
            print(f"  📝 Would write: {out_dir / 'index.md'}")
        else:
            (out_dir / "index.md").write_text(placeholder)
        return 1

    # Write index.md with summary
    summary_sources = []
    for f in findings:
        summary_sources.extend(f.get('sources', []))

    # Avoid duplicate "Research: Research:" if title already starts with it
    display_title = research_title or task_id
    if display_title.startswith("Research:"):
        index_heading = f"# {display_title.strip()}"
    else:
        index_heading = f"# Research: {display_title}"

    index_content = f"""{index_heading}

**Source**: kanban task `{task_id}`
**Workspace**: `{workspace_dir}`
**Archived**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Findings**: {len(findings)}

## Summary

This research produced {len(findings)} key findings:

"""
    for i, f in enumerate(findings, 1):
        index_content += f"- {i}. **{f['title']}** (from {f.get('source_file', '?')})\n"

    if summary_sources:
        index_content += "\n## Key Sources\n"
        for url in summary_sources[:20]:
            index_content += f"- {url}\n"

    if dry_run:
        print(f"  📝 Would write: {out_dir / 'index.md'}")
    else:
        (out_dir / "index.md").write_text(index_content)
    written += 1

    # Write individual finding files
    for i, f in enumerate(findings):
        slug = slugify(f['title'])[:40]
        fname = f"finding-{i+1:03d}-{slug}.md"
        content = f"""# Finding: {f['title']}

**Source**: kanban task `{task_id}`
**Source file**: {f.get('source_file', '?')}
**Index**: {i+1}/{len(findings)}

---

{f['content']}

"""
        if f.get('sources'):
            content += "\n### Sources\n\n"
            for url in f['sources'][:10]:
                content += f"- `{url}`\n"

        fpath = out_dir / fname
        if dry_run:
            print(f"  📝 Would write: {fpath}")
            print(f"     └─ {f['title'][:60]}")
        else:
            # Check if this finding already exists (by title hash)
            existing = list(out_dir.glob(f"finding-{i+1:03d}-*.md"))
            if existing:
                existing_content = existing[0].read_text()
                if f['title'] in existing_content:
                    continue  # skip duplicate
            fpath.write_text(content)
        written += 1

    return written


def main():
    parser = argparse.ArgumentParser(
        description="Research → Knowledge Graph pipeline"
    )
    parser.add_argument("workspace_dir", help="Path to research kanban workspace")
    parser.add_argument("--task-id", required=True, help="Kanban task ID (e.g. t_xxx)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    workspace = Path(args.workspace_dir).expanduser().resolve()
    task_id = args.task_id

    print(f"🔬 Research → Graphify pipeline")
    print(f"   Workspace: {workspace}")
    print(f"   Task:      {task_id}")
    print(f"   Output:    {FINDINGS_DIR / task_id}")

    if not workspace.exists():
        print(f"❌ Workspace not found: {workspace}")
        sys.exit(1)

    # Read and parse
    print(f"\n📖 Reading workspace...")
    findings, research_title = read_workspace(workspace)

    if not findings:
        print(f"⚠️  No findings extracted. Writing placeholder.")
    else:
        print(f"📊 Research title: {research_title or '(not specified)'}")

    # Write
    print(f"\n✍️  Writing findings to {FINDINGS_DIR / task_id}{' (DRY RUN)' if args.dry_run else ''}...")
    count = write_findings(task_id, findings, research_title, workspace, args.dry_run)
    print(f"   ✅ {count} files written")

    # Summary
    if not args.dry_run:
        print(f"\n📋 Summary:")
        print(f"   Output: {FINDINGS_DIR / task_id}")
        print(f"   Files:  {count}")
        print(f"   Next:   graphify-daily cron will index these at 03:00")
        print(f"           Or run: graphify --update {FINDINGS_DIR}")
    else:
        print(f"\n📋 Dry run complete — {count} files would be written")


if __name__ == "__main__":
    main()
