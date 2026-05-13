#!/usr/bin/env python3
"""
Kanban 阻塞监控 v2.0 — 纯监控，不派发

v2.0:
- 移除旧版"总指挥"派发逻辑
- 只扫描 blocked/crashed 任务，静默记录
- 只在有真实阻塞时输出（给看门狗消费，不直接推用户）
- 排除 archived 任务
"""

import sqlite3, json, time, sys
from pathlib import Path
from datetime import datetime

DB = str(Path.home() / ".hermes" / "kanban.db")

def main():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row

    blocked = db.execute("""
        SELECT id, title, assignee, status, consecutive_failures, last_failure_error
        FROM tasks WHERE status = 'blocked' AND status != 'archived'
        ORDER BY created_at DESC
    """).fetchall()

    crashed = db.execute("""
        SELECT id, title, assignee, status, consecutive_failures, last_failure_error
        FROM tasks WHERE status = 'crashed'
        ORDER BY created_at DESC
    """).fetchall()

    # Running tasks without heartbeat >24h (zombie detection)
    cutoff = int(time.time()) - 86400
    zombies = db.execute("""
        SELECT id, title, assignee, started_at, last_heartbeat_at
        FROM tasks WHERE status = 'running' 
        AND last_heartbeat_at IS NOT NULL AND last_heartbeat_at < ?
        ORDER BY last_heartbeat_at ASC
    """, (cutoff,)).fetchall()

    db.close()

    if not blocked and not crashed and not zombies:
        return 0

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if blocked:
        print(f"BLOCKED ({len(blocked)}):")
        for t in blocked:
            err = (t['last_failure_error'] or '')[:80]
            print(f"  {t['id'][:12]} | {t['title'][:50]} | {t['assignee']} | fails={t['consecutive_failures']}")
            if err:
                print(f"    → {err}")

    if crashed:
        print(f"\nCRASHED ({len(crashed)}):")
        for t in crashed:
            print(f"  {t['id'][:12]} | {t['title'][:50]} | {t['assignee']}")

    if zombies:
        print(f"\nZOMBIE RUNNING >24h ({len(zombies)}):")
        for t in zombies:
            age_h = (time.time() - t['last_heartbeat_at']) / 3600
            print(f"  {t['id'][:12]} | {t['title'][:50]} | {t['assignee']} | idle {age_h:.0f}h")

    return 0

if __name__ == "__main__":
    sys.exit(main())
