#!/usr/bin/env python3
"""
pending_push.py — 将待办任务推入 task_tracker.json，自动继承到次日 agenda。
被 SOUL.md 启动协议和会话结束 hook 调用。

用法:
  python3 pending_push.py "任务描述" P1 "tag1,tag2"
  python3 pending_push.py "signal_engine接口解耦" P1 "quant,refactoring"
  python3 pending_push.py --done "desc fragment"
  python3 pending_push.py --list
"""
import json, sys
from datetime import datetime
from pathlib import Path

HOME = Path.home()
TRACKER_FILE = HOME / '.hermes' / 'agenda' / 'task_tracker.json'


def load_tracker():
    if TRACKER_FILE.exists():
        try:
            return json.loads(TRACKER_FILE.read_text())
        except:
            pass
    return {"tasks": [], "last_updated": datetime.now().strftime('%Y-%m-%d')}


def save_tracker(data):
    data["last_updated"] = datetime.now().strftime('%Y-%m-%d')
    TRACKER_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def push(desc, priority="P2", tags=None):
    tracker = load_tracker()
    today = datetime.now().strftime('%Y-%m-%d')
    for t in tracker["tasks"]:
        if t["desc"] == desc:
            print(f"⚠️ 任务已存在: {desc}")
            return False
    task = {
        "id": f"task-{datetime.now().strftime('%Y%m%d')}-{len(tracker['tasks'])}",
        "desc": desc,
        "added": today,
        "last_seen": today,
        "days_pending": 0,
        "priority": priority.upper() if priority.upper() in ("P1","P2","P3") else "P2",
        "tags": tags.split(",") if tags else [],
        "source": "manual"
    }
    tracker["tasks"].append(task)
    save_tracker(tracker)
    print(f"✅ 已添加任务: [{task['priority']}] {desc}")
    return True


def mark_done(desc_fragment):
    tracker = load_tracker()
    before = len(tracker["tasks"])
    tracker["tasks"] = [t for t in tracker["tasks"] if desc_fragment not in t["desc"]]
    if len(tracker["tasks"]) != before:
        save_tracker(tracker)
        print(f"✅ 已标记完成: {desc_fragment}")
        return True
    print(f"⚠️ 未找到匹配任务: {desc_fragment}")
    return False


def list_tasks():
    tracker = load_tracker()
    if not tracker["tasks"]:
        print("(暂无待办)")
        return
    for t in sorted(tracker["tasks"],
                     key=lambda x: ({"P1":0,"P2":1,"P3":2}.get(x.get("priority","P2"),99), -x.get("days_pending",0))):
        days = t.get("days_pending", 0)
        icon = "  "
        if days >= 7: icon = "🚨"
        elif days >= 3: icon = "⚠️"
        elif days >= 1: icon = "🕐"
        print(f"  {icon}[{t['priority']}] {t['desc']} (第{days}天)")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: pending_push.py <desc> [priority] [tags]")
        print("       pending_push.py --done <desc_fragment>")
        print("       pending_push.py --list")
        sys.exit(1)
    if sys.argv[1] == '--done':
        mark_done(sys.argv[2])
    elif sys.argv[1] == '--list':
        list_tasks()
    else:
        desc = sys.argv[1]
        priority = sys.argv[2] if len(sys.argv) > 2 else "P2"
        tags = sys.argv[3] if len(sys.argv) > 3 else None
        push(desc, priority, tags)
