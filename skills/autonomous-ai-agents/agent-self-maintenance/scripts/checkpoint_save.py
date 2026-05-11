#!/usr/bin/env python3
"""
checkpoint_save.py — 保存任务执行现场

在阶段完成或中断时调用，记录当前阶段、产出物、决策记录。

用法:
  python3 checkpoint_save.py <task_id> <stage> <total> <desc> [artifacts_json]
  python3 checkpoint_save.py --show <task_id>
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
    return {"tasks": [], "last_updated": ""}


def save_tracker(data):
    data["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M')
    TRACKER_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def find_task(tracker, task_id):
    for i, t in enumerate(tracker["tasks"]):
        if t["id"] == task_id or task_id in t["desc"]:
            return i, t
    for t in tracker["tasks"]:
        if task_id.lower() in t["desc"].lower():
            return tracker["tasks"].index(t), t
    return None, None


def save_checkpoint(task_id, stage, total_stages, desc, artifacts=None):
    tracker = load_tracker()
    idx, task = find_task(tracker, task_id)
    if task is None:
        print(f"⚠️ 未找到任务: {task_id}")
        return False
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    cp = {"stage": stage, "total_stages": total_stages, "description": desc,
          "produced": artifacts or [], "timestamp": now}
    if "checkpoints" not in task:
        task["checkpoints"] = []
    task["checkpoints"].append(cp)
    task["progress"] = f"阶段 {stage}/{total_stages}"
    task["last_checkpoint"] = now
    save_tracker(tracker)
    print(f"✅ 已保存 checkpoint: {desc}")
    print(f"   进度: {stage}/{total_stages} | 产出: {len(artifacts or [])} 个文件")
    return True


def show_checkpoints(task_id):
    tracker = load_tracker()
    idx, task = find_task(tracker, task_id)
    if task is None:
        print(f"⚠️ 未找到任务")
        return
    print(f"任务: {task['desc']}")
    print(f"进度: {task.get('progress', '未开始')}")
    for cp in task.get("checkpoints", []):
        print(f"  [{cp['timestamp']}] 阶段{cp['stage']}/{cp['total_stages']}: {cp['description']}")
        for f in cp.get("produced", []):
            print(f"    └─ {f}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法:")
        print("  checkpoint_save.py <task_id> <stage> <total> <desc> [artifacts_json]")
        print("  checkpoint_save.py --show <task_id>")
        sys.exit(1)
    if sys.argv[1] == '--show':
        show_checkpoints(sys.argv[2])
    elif len(sys.argv) >= 5:
        artifacts = json.loads(sys.argv[5]) if len(sys.argv) > 5 else None
        save_checkpoint(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], artifacts)
    else:
        print("参数不够")
