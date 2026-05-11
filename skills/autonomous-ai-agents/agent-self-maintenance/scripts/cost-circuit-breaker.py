#!/usr/bin/env python3
"""
cost-circuit-breaker.py — 成本熔断看门狗
成本熔断看门狗，每小时运行，日消耗>$8.00(≈¥57)自动暂停高消费cron任务。

暂停目标（硬编码，L3以下可自动暂停）:
  - 8b9037f1fbdf: session-miner
  - 15d19bd7a80f: 周度自优化
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

COST_TRACKER = Path.home() / ".hermes/skills/devops/autonomous-optimization-architect/scripts/cost-tracker.py"
THRESHOLD_USD = 8.00  # ≈ ¥57
HIGH_COST_JOBS = ["8b9037f1fbdf", "15d19bd7a80f"]  # Jobs to auto-pause
BEIJING_TZ = timezone(timedelta(hours=8))


def get_daily_cost() -> float:
    """Get today's calendar-day cost (resets at midnight)."""
    result = subprocess.run(
        [sys.executable, str(COST_TRACKER), "--days", "2", "--json"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        print(f"cost-tracker failed: {result.stderr.strip()}", file=sys.stderr)
        return 0.0
    data = json.loads(result.stdout)
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    return data.get("by_day", {}).get(today, {}).get("cost", 0.0)


def get_active_jobs() -> list[dict]:
    """Get list of active cron jobs."""
    result = subprocess.run(
        ["hermes", "cron", "list", "--json"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return []
    data = json.loads(result.stdout)
    if isinstance(data, dict) and "jobs" in data:
        return data["jobs"]
    if isinstance(data, list):
        return data
    return []


def pause_job(job_id: str) -> bool:
    """Pause a cron job by ID."""
    result = subprocess.run(
        ["hermes", "cron", "pause", job_id],
        capture_output=True, text=True, timeout=30,
    )
    return result.returncode == 0


def main():
    cost = get_daily_cost()
    now = datetime.now(BEIJING_TZ).strftime("%H:%M")

    if cost >= THRESHOLD_USD:
        print(f"🚨 成本熔断触发 [{now}]")
        print(f"   今日成本: ${cost:.4f} (阈值: ${THRESHOLD_USD:.2f})")
        print(f"   自动暂停高消费cron任务...")

        jobs = get_active_jobs()
        paused = []
        for job in jobs:
            jid = job.get("id") or job.get("job_id", "")
            if jid in HIGH_COST_JOBS and job.get("enabled", False):
                name = job.get("name", jid)
                if pause_job(jid):
                    paused.append(f"✅ {name} ({jid})")
                    print(f"   {paused[-1]}")
                else:
                    print(f"   ❌ 暂停失败: {name}")

        if paused:
            print(f"\n   已暂停 {len(paused)} 个任务。成本回落后手动恢复。")
            try:
                from notify import send
                send("成本熔断触发", f"今日${cost:.2f}(阈值${THRESHOLD_USD:.2f})\n已暂停{len(paused)}个任务")
            except Exception:
                pass


if __name__ == "__main__":
    main()
