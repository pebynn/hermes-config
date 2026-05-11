#!/usr/bin/env python3
"""audit_bd_layer.py — B/D层每日执行率审计
检查kanban.db中任务是否经过B/D层处理：
- B层指标：body含"已知陷阱"的task比例
- D层指标：result含[LESSONS]的task比例
- 低于阈值→QQ Bot告警
用法：python3 audit_bd_layer.py [--alert]
作为cron: no_agent=true, deliver=qqbot
"""

import sys
import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta

KANBAN_DB = Path(os.path.expanduser("~/.hermes/kanban.db"))
THRESHOLD_B = 0.50  # B层注入率低于50%告警
THRESHOLD_D = 0.20  # D层回收率低于20%告警
LOOKBACK_HOURS = 24

def audit():
    if not KANBAN_DB.exists():
        return {"error": "kanban.db not found"}

    conn = sqlite3.connect(str(KANBAN_DB))
    
    # 过去24小时的任务
    since = int((datetime.now() - timedelta(hours=LOOKBACK_HOURS)).timestamp())
    
    cur = conn.execute(
        "SELECT count(*) FROM tasks WHERE created_at >= ?", (since,))
    total = cur.fetchone()[0]
    
    if total == 0:
        conn.close()
        return {"total": 0, "status": "no_tasks", "message": "过去24h无新任务"}
    
    # B层检查
    cur = conn.execute(
        "SELECT count(*) FROM tasks WHERE created_at >= ? AND body LIKE '%已知陷阱%'",
        (since,))
    b_count = cur.fetchone()[0]
    
    # D层检查（从task_runs.summary）
    cur = conn.execute(
        "SELECT count(DISTINCT r.task_id) FROM task_runs r "
        "JOIN tasks t ON t.id=r.task_id "
        "WHERE t.created_at >= ? AND r.summary LIKE '%[LESSONS]%'",
        (since,))
    d_count = cur.fetchone()[0]
    
    # 已完成且有run的task数
    cur = conn.execute(
        "SELECT count(DISTINCT r.task_id) FROM task_runs r "
        "JOIN tasks t ON t.id=r.task_id "
        "WHERE t.created_at >= ? AND r.outcome='completed'",
        (since,))
    done_with_runs = cur.fetchone()[0]
    
    conn.close()
    
    b_rate = b_count / total if total > 0 else 0
    d_rate = d_count / done_with_runs if done_with_runs > 0 else 0
    
    alerts = []
    if b_rate < THRESHOLD_B and total >= 3:
        alerts.append(f"B层注入率 {b_rate:.0%} < {THRESHOLD_B:.0%} ({b_count}/{total})")
    if d_rate < THRESHOLD_D and done_with_runs >= 2:
        alerts.append(f"D层回收率 {d_rate:.0%} < {THRESHOLD_D:.0%} ({d_count}/{done_with_runs})")
    
    return {
        "total": total,
        "done": done_with_runs,
        "b_count": b_count,
        "d_count": d_count,
        "b_rate": b_rate,
        "d_rate": d_rate,
        "alerts": alerts,
        "status": "critical" if alerts else "ok"
    }

def main():
    result = audit()
    
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False))
    elif "--alert" in sys.argv:
        if result.get("alerts"):
            for a in result["alerts"]:
                print(f"⚠️ {a}")
        # silent if ok
    else:
        print(f"B/D层审计 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
        print(f"  过去24h任务: {result.get('total', 0)}")
        print(f"  B层注入: {result.get('b_rate', 0):.0%} ({result.get('b_count', 0)}/{result.get('total', 0)})")
        print(f"  D层回收: {result.get('d_rate', 0):.0%} ({result.get('d_count', 0)}/{result.get('done', 0)})")
        if result.get("alerts"):
            print(f"\n⚠️ 告警:")
            for a in result["alerts"]:
                print(f"  - {a}")
        else:
            print(f"\n✅ 正常")

if __name__ == "__main__":
    main()
