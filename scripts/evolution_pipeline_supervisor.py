#!/usr/bin/env python3
"""进化管线监督器 — 每周一 09:00 检查 P1/P2 任务进度，阻塞/停滞自动告警。

Task tracking:
  P1: t_ae9ffb59 → t_457f1d86 → t_f7386342 (线性依赖)
  P2: t_5eed626c, t_48bdb336, t_f6de2309, t_c197c415 (并行无依赖)

Alert rules:
  - Any task failed → QQ Bot P0
  - Any task blocked → QQ Bot P1
  - Parent task complete but child still todo (dispatcher didn't promote) → QQ Bot P1
  - All tasks done → QQ Bot P3 completion notice
  - All tasks fine, nothing to report → silent (zero-cost)
"""

import subprocess
import json
import sys
import os
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))

P1_TASKS = ["t_ae9ffb59", "t_457f1d86", "t_f7386342"]
P2_TASKS = ["t_5eed626c", "t_48bdb336", "t_f6de2309", "t_c197c415"]
ALL_TASKS = P1_TASKS + P2_TASKS

DEPENDENCY_MAP = {
    "t_457f1d86": "t_ae9ffb59",
    "t_f7386342": "t_457f1d86",
}


def get_task_status(task_id):
    """Get kanban task status via hermes CLI"""
    try:
        result = subprocess.run(
            ["hermes", "kanban", "show", task_id, "--json"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Error getting {task_id}: {e}", file=sys.stderr)
        return None


def get_cron_last_run():
    """Read last check timestamp from state file"""
    state_file = os.path.expanduser("~/.hermes/data/evolution_supervisor_state.json")
    if os.path.exists(state_file):
        with open(state_file) as f:
            return json.load(f)
    return {"last_check": None, "previous_status": {}}


def save_cron_last_run(status_map):
    """Save current check timestamp and status"""
    state_file = os.path.expanduser("~/.hermes/data/evolution_supervisor_state.json")
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    with open(state_file, "w") as f:
        json.dump({
            "last_check": datetime.now(TZ).isoformat(),
            "previous_status": status_map
        }, f, indent=2)


def check_circuit_breaker():
    """Check if cost circuit breaker is tripped — if so, skip expensive checks"""
    try:
        result = subprocess.run(
            ["python3", os.path.expanduser("~/.hermes/scripts/cost-circuit-breaker.py")],
            capture_output=True, text=True, timeout=10
        )
        return "BROKEN" in result.stdout or "broken" in result.stdout.lower()
    except Exception:
        return False


def main():
    state = get_cron_last_run()
    previous_status = state.get("previous_status", {})
    
    alerts = []
    status_map = {}
    all_done = True
    
    for task_id in ALL_TASKS:
        task = get_task_status(task_id)
        if task is None:
            # API call failed — but don't alert on transient failures
            status_map[task_id] = "unknown"
            continue
        
        status = task.get("status", "unknown")
        status_map[task_id] = status
        
        if status == "done":
            continue
        
        all_done = False
        
        if status == "blocked":
            error = task.get("last_failure_error", "unknown reason")
            alerts.append(f"P1 阻塞: {task_id} ({task.get('title','')}) — {error[:200]}")
        elif status == "failed":
            error = task.get("last_failure_error", "unknown reason")
            alerts.append(f"P0 失败: {task_id} ({task.get('title','')}) — {error[:200]}")
        elif status == "todo":
            # Check if parent is done but child not promoted
            parent_id = DEPENDENCY_MAP.get(task_id)
            if parent_id and parent_id in status_map and status_map[parent_id] == "done":
                days_since_parent = "?"
                parent_task = get_task_status(parent_id)
                if parent_task and parent_task.get("completed_at"):
                    completed_ts = parent_task["completed_at"]
                    if isinstance(completed_ts, (int, float)):
                        delta = datetime.now(TZ) - datetime.fromtimestamp(completed_ts, tz=TZ)
                        days_since_parent = f"{delta.days}d"
                alerts.append(
                    f"P1 依赖就绪但未promote: {task_id} "
                    f"(parent {parent_id} done {days_since_parent} ago, still todo)"
                )
            else:
                # Check for stagnation — same todo status as last week
                prev = previous_status.get(task_id)
                if prev == "todo":
                    alerts.append(f"P2 停滞: {task_id} ({task.get('title','')}) — still todo after 1+ week")
    
    save_cron_last_run(status_map)
    
    # Check if cost circuit breaker would prevent QQ Bot delivery
    if check_circuit_breaker():
        # Circuit breaker tripped — just write to log
        log_file = os.path.expanduser("~/.hermes/logs/evolution_supervisor.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, "a") as f:
            f.write(f"\n[{datetime.now(TZ).isoformat()}] CIRCUIT_BREAKER: alerts suppressed\n")
            for a in alerts:
                f.write(f"  {a}\n")
        return
    
    # Build message for QQ Bot
    now_str = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    
    if all_done:
        print(f"进化管线全部完成\n"
              f"P1: SkillClaw分析 → EvoClaw退化检测 → 综合升级方案 ✅\n"
              f"P2: Tool优化/SystemPrompt优化/遗传算法借鉴/季度监控 ✅\n"
              f"时间: {now_str}")
        # Write completion marker
        done_file = os.path.expanduser("~/.hermes/data/evolution_pipeline_done")
        with open(done_file, "w") as f:
            f.write(f"All evolution tasks completed at {now_str}\n")
        return
    
    if alerts:
        lines = [f"[进化管线监督] {now_str}"]
        lines.append(f"进度: {sum(1 for s in status_map.values() if s == 'done')}/{len(ALL_TASKS)} 完成")
        lines.append("---")
        for a in alerts:
            lines.append(f"• {a}")
        lines.append(f"---")
        lines.append(f"Kanban看板: hermes kanban list")
        print("\n".join(lines))
    else:
        # All tasks progressing, nothing wrong → silent
        # Still print minimal status for cron log
        done_count = sum(1 for s in status_map.values() if s == 'done')
        running_count = sum(1 for s in status_map.values() if s == 'running')
        print(f"OK: {done_count} done, {running_count} running, rest pending")  # goes to cron log, not delivered


if __name__ == "__main__":
    main()
