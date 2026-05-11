#!/usr/bin/env python3
"""
cost-daily-report.py — Hermes daily cost report formatter for WeChat push.

Runs cost-tracker.py --days 2 --json and formats a human-readable report.
Designed for use as a cron job script that prints to stdout (auto-delivered).
"""

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT_DIR = Path.home() / ".hermes/skills/devops/autonomous-optimization-architect/scripts"
COST_TRACKER = SCRIPT_DIR / "cost-tracker.py"
BEIJING_TZ = timezone(timedelta(hours=8))


def get_cost_data() -> dict:
    """Run cost-tracker.py --days 2 --json and return parsed JSON.
    Uses --days 2 because cron runs at 00:30, so --days 1 would capture
    the current (almost empty) day. --days 2 ensures yesterday's full data
    is included.
    """
    result = subprocess.run(
        [sys.executable, str(COST_TRACKER), "--days", "2", "--json"],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"cost-tracker failed (exit {result.returncode}): {result.stderr.strip()}")
    return json.loads(result.stdout)


def format_report(data: dict) -> str:
    """Format cost data into a WeChat-friendly message string."""
    period = data.get("period", {})
    by_model = data.get("by_model", {})
    by_domain = data.get("by_domain", {})
    flagged = data.get("flagged_sessions", [])

    # Date label — always yesterday (cron runs at 00:30, reporting previous day)
    yesterday = (datetime.now(BEIJING_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
    report_date = yesterday

    total_sessions = period.get("total_sessions", 0)
    total_cost = period.get("total_cost", 0.0)

    # Model breakdown
    model_parts = []
    for model_name, info in sorted(by_model.items(), key=lambda x: -x[1].get("sessions", 0)):
        label = model_name if model_name else "unknown"
        model_parts.append(f"{label} {info.get('sessions', 0)}")

    # Domain breakdown
    domain_parts = []
    for domain_name, info in sorted(by_domain.items(), key=lambda x: -x[1].get("sessions", 0)):
        domain_parts.append(f"{domain_name} {info.get('sessions', 0)}")

    # Circuit breaker status (check flagged sessions)
    fail_count = len(flagged)
    circuit_status = "OK"
    if fail_count > 0:
        circuit_status = f"⚠ {fail_count} flagged"

    lines = [
        f"📊 Hermes 每日成本报告 ({report_date})",
        f"总会话: {total_sessions}  |  总成本: ${total_cost:.4f}",
        f"模型: {'  /  '.join(model_parts)}",
        f"按域: {'  /  '.join(domain_parts)}",
        f"熔断状态: {circuit_status}  最近故障: {fail_count}",
    ]
    return "\n".join(lines)


def main():
    try:
        data = get_cost_data()
        report = format_report(data)
        print(report)
    except Exception as e:
        print(f"❌ Hermes 成本报告生成失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
