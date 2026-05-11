#!/usr/bin/env python3
"""Writing reviewer 效果闭环 — 统计审核通过率/修正效率"""
import sqlite3, json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB = Path.home() / ".hermes" / "kanban.db"
TZ = timezone(timedelta(hours=8))

def main():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    
    # 最近7天的 writing + reviewer 任务
    cutoff = int((datetime.now(TZ) - timedelta(days=7)).timestamp())
    
    cursor.execute("""
        SELECT r.task_id, r.profile, r.outcome, r.summary, r.metadata, r.started_at, 
               r.ended_at, t.title
        FROM task_runs r
        LEFT JOIN tasks t ON r.task_id = t.id
        WHERE r.profile IN ('writer', 'reviewer')
          AND r.started_at > ?
        ORDER BY r.started_at DESC
    """, (cutoff,))
    runs = cursor.fetchall()
    
    if not runs:
        print("最近7天无writing管线活动")
        conn.close()
        return
    
    writer_tasks = [r for r in runs if r[1] == 'writer']
    reviewer_tasks = [r for r in runs if r[1] == 'reviewer']
    
    # Reviewer 统计
    approved = 0
    rejected = 0
    issues_found = []
    
    for r in reviewer_tasks:
        summary = r[3] or ""
        meta_str = r[4]
        
        if "APPROVED" in summary.upper() or "approved" in str(meta_str or "").lower():
            approved += 1
        elif "REJECTED" in summary.upper() or "rejected" in str(meta_str or "").lower():
            rejected += 1
            
        # 提取问题严重度
        if meta_str:
            try:
                meta = json.loads(meta_str) if isinstance(meta_str, str) else meta_str
                if isinstance(meta, dict) and "findings" in meta:
                    for f in meta["findings"]:
                        issues_found.append(f.get("severity", "unknown"))
            except:
                pass
    
    # Writer 统计
    writer_durations = []
    for r in writer_tasks:
        if r[5] and r[6]:
            writer_durations.append(r[6] - r[5])
    
    avg_dur = sum(writer_durations) / len(writer_durations) if writer_durations else 0
    
    print(f"📝 Writing 管线质量报告 (7天)")
    print(f"   Writer 任务: {len(writer_tasks)}")
    print(f"   Reviewer 任务: {len(reviewer_tasks)}")
    print(f"   Writer 平均耗时: {avg_dur:.0f}s")
    print()
    print(f"   审核结果: ✓{approved} / ✗{rejected}")
    
    if issues_found:
        from collections import Counter
        severity = Counter(issues_found)
        print(f"   问题分布: {dict(severity)}")
    
    if rejected > 0:
        ratio = rejected / max(len(reviewer_tasks), 1) * 100
        print(f"   驳回率: {ratio:.0f}%")

    conn.close()

if __name__ == "__main__":
    main()
