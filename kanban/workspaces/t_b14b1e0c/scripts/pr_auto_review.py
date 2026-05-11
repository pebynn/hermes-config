#!/usr/bin/env python3
"""
PR Auto Review Trigger Script
==============================
Monitors GitHub PRs with 'auto-review' label and creates kanban review tasks.
Supports both webhook mode (Flask server) and polling mode (cron-friendly).

Usage:
  # Webhook mode (long-running server)
  python pr_auto_review.py --mode webhook --port 8080 --secret <webhook-secret>

  # Polling mode (single scan, cron-friendly)
  python pr_auto_review.py --mode poll --repo owner/repo

  # One-shot for a specific PR
  python pr_auto_review.py --mode once --repo owner/repo --pr 123

Environment variables:
  GITHUB_TOKEN       - GitHub personal access token (required)
  KANBAN_DB          - Path to kanban SQLite DB (default: ~/.hermes/kanban.db)
  REVIEWER_PROFILE   - Kanban profile for reviewer (default: reviewer)
  BUS_DIR            - Data bus directory (default: ~/.hermes/bus/review-to-code)
"""

import argparse
import hashlib
import hmac
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_KANBAN_DB = os.path.expanduser("~/.hermes/kanban.db")
DEFAULT_BUS_DIR = os.path.expanduser("~/.hermes/bus/review-to-code")
DEFAULT_REVIEWER = "reviewer"
AUTO_REVIEW_LABEL = "auto-review"
MAX_FINDINGS = 20
MAX_ITERATIONS = 3

# ---------------------------------------------------------------------------
# GitHub API helpers (minimal, no external deps)
# ---------------------------------------------------------------------------

import urllib.request
import urllib.error
import urllib.parse


def github_api(
    method: str,
    path: str,
    token: str,
    data: Optional[dict] = None,
) -> dict:
    """Make a GitHub API request. Returns parsed JSON response."""
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "hermes-pr-auto-review/1.0",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 403 and "rate limit" in (e.read() or b"").decode().lower():
                wait = min(2 ** attempt * 5, 300)  # exponential backoff, max 5min
                print(f"Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if e.code == 404:
                print(f"Not found: {path}")
                return {}
            raise
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
    return {}


def get_pr_info(repo: str, pr_number: int, token: str) -> dict:
    """Fetch PR details from GitHub."""
    return github_api("GET", f"/repos/{repo}/pulls/{pr_number}", token)


def get_pr_diff(repo: str, pr_number: int, token: str) -> str:
    """Fetch PR diff text."""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.diff",
        "User-Agent": "hermes-pr-auto-review/1.0",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


def get_pr_labels(repo: str, pr_number: int, token: str) -> list[str]:
    """Get label names on a PR."""
    data = github_api("GET", f"/repos/{repo}/issues/{pr_number}/labels", token)
    return [lbl["name"] for lbl in data] if isinstance(data, list) else []


def list_open_prs(repo: str, token: str) -> list[dict]:
    """List all open PRs for a repo."""
    prs = []
    page = 1
    while True:
        data = github_api(
            "GET",
            f"/repos/{repo}/pulls?state=open&per_page=100&page={page}",
            token,
        )
        if not isinstance(data, list) or not data:
            break
        prs.extend(data)
        page += 1
        if len(data) < 100:
            break
    return prs


# ---------------------------------------------------------------------------
# Kanban helpers
# ---------------------------------------------------------------------------

def get_kanban_db() -> str:
    return os.environ.get("KANBAN_DB", DEFAULT_KANBAN_DB)


def find_existing_review_task(pr_number: int, iteration: int) -> Optional[str]:
    """Check if a review task already exists for this PR + iteration."""
    db_path = get_kanban_db()
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT id FROM tasks WHERE title LIKE ? AND status NOT IN ('archived')",
            (f"%PR #{pr_number}%iteration {iteration}%",),
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def create_review_task(
    pr_number: int,
    pr_url: str,
    branch: str,
    base_branch: str,
    iteration: int = 0,
    reviewer: str = DEFAULT_REVIEWER,
) -> str:
    """Create a kanban review task via the hermes CLI.

    Returns the task_id on success.
    NOTE: In a full Hermes deployment, this would use the kanban_create tool
    directly. This script uses the CLI as a fallback for non-agent contexts.
    """
    title = f"Review PR #{pr_number} — iteration {iteration}"
    body = f"""## 审查任务
- PR: {pr_url}
- Branch: {branch} → {base_branch}
- 触发标签: {AUTO_REVIEW_LABEL}
- 迭代轮次: {iteration}

## 审查标准
按优先级分类：安全(P0) > 性能(P1) > 风格(P2) > 逻辑(P3)
详细标准见 review-criteria.json

## 产出要求
1. 读取 PR diff
2. 逐文件检查，按 criteria 分类 findings
3. 将结果写入 ~/.hermes/bus/review-to-code/{pr_number}-{iteration}.json
4. 在任务 metadata 中记录 findings 统计

## 强制规则
- 安全类(P0) findings 的 requires_human 必须为 true
- 涉及资金改动的 requires_human 必须为 true
- findings 总数 > {MAX_FINDINGS} 时，block 等人工分流
"""

    # Try the hermes CLI first
    try:
        import subprocess
        result = subprocess.run(
            [
                "hermes", "kanban", "create", title,
                "--assignee", reviewer,
                "--body", body,
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            task_id = result.stdout.strip().split("\n")[-1].strip()
            print(f"Created kanban task: {task_id}")
            return task_id
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: write a manifest file that can be picked up
    manifest_dir = Path(os.environ.get("BUS_DIR", DEFAULT_BUS_DIR))
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "action": "create_review_task",
        "title": title,
        "assignee": reviewer,
        "body": body,
        "pr_number": pr_number,
        "iteration": iteration,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = manifest_dir / f"pending-review-{pr_number}-{iteration}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Wrote review task manifest: {manifest_path}")
    return f"pending:{manifest_path}"


# ---------------------------------------------------------------------------
# Iteration tracking
# ---------------------------------------------------------------------------

def get_current_iteration(pr_number: int) -> int:
    """Determine the current iteration for a PR by checking existing tasks."""
    db_path = get_kanban_db()
    if not os.path.exists(db_path):
        return 0
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE title LIKE ? AND status IN ('done', 'running', 'ready')",
            (f"%PR #{pr_number}%",),
        )
        count = cur.fetchone()[0]
        # Each full cycle (review+fix+verify) = 1 iteration
        # We count how many review tasks exist
        cur2 = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE title LIKE ? AND status IN ('done', 'running', 'ready')",
            (f"%Review PR #{pr_number}%",),
        )
        review_count = cur2.fetchone()[0]
        return review_count
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def process_pr(repo: str, pr_number: int, token: str) -> Optional[str]:
    """Process a single PR: check labels, create review task if needed."""
    pr_info = get_pr_info(repo, pr_number, token)
    if not pr_info:
        print(f"  PR #{pr_number}: not found, skipping")
        return None

    # Check for auto-review label
    labels = get_pr_labels(repo, pr_number, token)
    if AUTO_REVIEW_LABEL not in labels:
        print(f"  PR #{pr_number}: no '{AUTO_REVIEW_LABEL}' label, skipping")
        return None

    pr_url = pr_info.get("html_url", "")
    branch = pr_info.get("head", {}).get("ref", "")
    base_branch = pr_info.get("base", {}).get("ref", "")

    # Determine iteration
    iteration = get_current_iteration(pr_number)
    if iteration >= MAX_ITERATIONS:
        print(f"  PR #{pr_number}: max iterations ({MAX_ITERATIONS}) reached, needs human intervention")
        return None

    # Check for existing review task
    existing = find_existing_review_task(pr_number, iteration)
    if existing:
        print(f"  PR #{pr_number}: review task already exists ({existing}), skipping")
        return None

    # Create review task
    print(f"  PR #{pr_number}: creating review task (iteration {iteration})")
    task_id = create_review_task(
        pr_number=pr_number,
        pr_url=pr_url,
        branch=branch,
        base_branch=base_branch,
        iteration=iteration,
    )
    return task_id


def run_poll(repo: str, token: str) -> list[str]:
    """Scan all open PRs for the auto-review label."""
    print(f"Scanning open PRs in {repo}...")
    prs = list_open_prs(repo, token)
    print(f"Found {len(prs)} open PRs")

    created = []
    for pr in prs:
        pr_number = pr.get("number")
        if not pr_number:
            continue
        task_id = process_pr(repo, pr_number, token)
        if task_id:
            created.append(task_id)

    print(f"Created {len(created)} review tasks")
    return created


def run_once(repo: str, pr_number: int, token: str) -> Optional[str]:
    """Process a single specific PR."""
    print(f"Processing PR #{pr_number} in {repo}...")
    return process_pr(repo, pr_number, token)


# ---------------------------------------------------------------------------
# Webhook server (Flask optional)
# ---------------------------------------------------------------------------

def run_webhook(port: int, secret: str, repo: str, token: str):
    """Run a Flask-based webhook server for GitHub PR events."""
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        print("Flask not installed. Install with: pip install flask")
        print("Alternatively, use --mode poll or --mode once")
        sys.exit(1)

    app = Flask(__name__)

    @app.route("/webhook", methods=["POST"])
    def handle_webhook():
        # Verify signature
        sig_header = request.headers.get("X-Hub-Signature-256", "")
        if secret:
            expected = "sha256=" + hmac.new(
                secret.encode(), request.get_data(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(sig_header, expected):
                return jsonify({"error": "Invalid signature"}), 403

        payload = request.get_json()
        if not payload:
            return jsonify({"error": "No payload"}), 400

        event = request.headers.get("X-GitHub-Event", "")

        # Handle PR events
        if event == "pull_request":
            action = payload.get("action", "")
            if action not in ("opened", "synchronize", "labeled"):
                return jsonify({"status": "ignored", "reason": f"action={action}"})

            pr = payload.get("pull_request", {})
            pr_number = pr.get("number")
            pr_labels = [lbl["name"] for lbl in pr.get("labels", [])]

            if AUTO_REVIEW_LABEL not in pr_labels:
                return jsonify({"status": "ignored", "reason": "no auto-review label"})

            pr_url = pr.get("html_url", "")
            branch = pr.get("head", {}).get("ref", "")
            base_branch = pr.get("base", {}).get("ref", "")
            iteration = get_current_iteration(pr_number)

            if iteration >= MAX_ITERATIONS:
                return jsonify({"status": "blocked", "reason": "max iterations reached"})

            existing = find_existing_review_task(pr_number, iteration)
            if existing:
                return jsonify({"status": "ignored", "reason": "task exists"})

            task_id = create_review_task(
                pr_number=pr_number,
                pr_url=pr_url,
                branch=branch,
                base_branch=base_branch,
                iteration=iteration,
            )
            return jsonify({"status": "created", "task_id": task_id})

        return jsonify({"status": "ignored", "reason": f"event={event}"})

    print(f"Starting webhook server on port {port}...")
    app.run(host="0.0.0.0", port=port)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PR Auto Review Trigger — creates kanban review tasks for auto-review labeled PRs"
    )
    parser.add_argument(
        "--mode",
        choices=["webhook", "poll", "once"],
        required=True,
        help="Run mode: webhook server, single poll scan, or one-shot for a specific PR",
    )
    parser.add_argument("--repo", help="GitHub repo in owner/name format")
    parser.add_argument("--pr", type=int, help="PR number (for --mode once)")
    parser.add_argument("--port", type=int, default=8080, help="Webhook server port (default: 8080)")
    parser.add_argument("--secret", default="", help="GitHub webhook secret")
    parser.add_argument(
        "--token-env",
        default="GITHUB_TOKEN",
        help="Environment variable name for GitHub token (default: GITHUB_TOKEN)",
    )

    args = parser.parse_args()

    token = os.environ.get(args.token_env, "")
    if not token and args.mode != "webhook":
        print(f"Error: {args.token_env} environment variable not set")
        sys.exit(1)

    if args.mode == "webhook":
        run_webhook(args.port, args.secret, args.repo or "", token)
    elif args.mode == "poll":
        if not args.repo:
            print("Error: --repo required for poll mode")
            sys.exit(1)
        run_poll(args.repo, token)
    elif args.mode == "once":
        if not args.repo or not args.pr:
            print("Error: --repo and --pr required for once mode")
            sys.exit(1)
        task_id = run_once(args.repo, args.pr, token)
        if task_id:
            print(f"Created task: {task_id}")
        else:
            print("No task created (PR may not have auto-review label or task already exists)")


if __name__ == "__main__":
    main()
