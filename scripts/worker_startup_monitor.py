#!/usr/bin/env python3
"""Worker启动耗时监控 — 从claimed到spawned的时间差"""
import sqlite3, json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB = Path.home() / ".hermes" / "kanban.db"
TZ = timezone(timedelta(hours=8))

def main():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    
    # 最近24h
    cutoff = int((datetime.now(TZ) - timedelta(hours=24)).timestamp())
    
    # 找所有 claimed+spawned 事件对，计算时间差
    cursor.execute("""
        SELECT e1.task_id, e1.created_at as claimed, e2.created_at as spawned,
               (e2.created_at - e1.created_at) as startup_sec,
               t.title, t.assignee
        FROM task_events e1
        JOIN task_events e2 ON e1.task_id = e2.task_id AND e2.kind = 'spawned'
        LEFT JOIN tasks t ON e1.task_id = t.id
        WHERE e1.kind = 'claimed'
          AND e1.created_at > ?
        ORDER BY e1.created_at DESC
    """, (cutoff,))
    rows = cursor.fetchall()
    
    if not rows:
        print("24h内无worker启动")
        conn.close()
        return
    
    by_profile = {}
    for row in rows:
        task_id, claimed, spawned, startup, title, profile = row
        if profile not in by_profile:
            by_profile[profile] = []
        by_profile[profile].append(startup)
    
    print(f"⚡ Worker启动耗时 (24h)")
    for profile, times in sorted(by_profile.items()):
        avg = sum(times) / len(times)
        mx = max(times)
        mn = min(times)
        print(f"  {profile}: {len(times)}次 | avg={avg:.1f}s min={mn}s max={mx}s")
    
    all_times = [s for times in by_profile.values() for s in times]
    if all_times:
        print(f"\n  总计: {len(all_times)}次启动 | 总平均: {sum(all_times)/len(all_times):.1f}s")
    
    conn.close()

if __name__ == "__main__":
    main()
