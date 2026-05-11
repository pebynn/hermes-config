#!/usr/bin/env python3
"""kanban_failure_collector.py — 采集kanban失败事件，提取错误模式写入lessons

由 error-learner cron (575103045eb1) 每日22:00调用。
扫描最近24小时的blocked/failed任务，按域归类，去重后追加到对应lessons文件。
"""

import sqlite3
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

KANBAN_DB = Path.home() / ".hermes" / "kanban.db"
LESSONS_DIR = Path.home() / ".hermes" / "lessons"

# 域映射: kanban assignee → lessons文件
DOMAIN_MAP = {
    "finance-domain": "finance-domain.md",
    "code-domain": "code-domain.md",
    "ops-domain": "ops-domain.md",
    "research-domain": "research-domain.md",
    "writer": "writing-domain.md",
    "reviewer": "writing-domain.md",
    "ec-sourcing": "ec-domain.md",
    "ec-listing": "ec-domain.md",
    "ec-fulfillment": "ec-domain.md",
}

def get_recent_failures(hours=24):
    """从kanban.db获取最近N小时的失败/阻塞任务"""
    conn = sqlite3.connect(KANBAN_DB)
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    cursor.execute("""
        SELECT id, title, assignee, status, last_failure_error, updated_at
        FROM tasks
        WHERE status IN ('blocked', 'failed', 'error')
          AND updated_at >= ?
        ORDER BY assignee, updated_at DESC
    """, (cutoff,))
    
    rows = cursor.fetchall()
    conn.close()
    return rows

def extract_error_pattern(error_msg):
    """提取错误模式：去掉具体参数值，保留结构"""
    if not error_msg:
        return "unknown_error"
    # 替换具体ID、数值为占位符
    pattern = re.sub(r't_[a-f0-9]{8}', 't_<id>', error_msg)
    pattern = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', '<timestamp>', pattern)
    pattern = re.sub(r'0x[0-9a-fA-F]+', '<hex>', pattern)
    pattern = re.sub(r'\b\d+\b', '<N>', pattern)
    # 截断过长的模式
    if len(pattern) > 200:
        pattern = pattern[:200] + "..."
    return pattern.strip()

def categorize_by_domain(failures):
    """按域归类失败事件"""
    by_domain = defaultdict(list)
    for task_id, title, assignee, status, error, updated_at in failures:
        domain = DOMAIN_MAP.get(assignee, "global.md")
        pattern = extract_error_pattern(error)
        by_domain[domain].append({
            "task_id": task_id,
            "title": title,
            "status": status,
            "pattern": pattern,
            "raw_error": error,
            "time": updated_at,
            "assignee": assignee,
        })
    return by_domain

def deduplicate_patterns(events):
    """去重：相同错误模式只保留一次，记录出现次数"""
    pattern_counts = defaultdict(lambda: {"count": 0, "examples": []})
    for evt in events:
        key = evt["pattern"]
        pattern_counts[key]["count"] += 1
        if len(pattern_counts[key]["examples"]) < 3:
            pattern_counts[key]["examples"].append(evt)
    return pattern_counts

def append_to_lesson(lesson_file, patterns, date_str):
    """追加教训到lessons文件"""
    lesson_path = LESSONS_DIR / lesson_file
    if not lesson_path.exists():
        lesson_path = LESSONS_DIR / "global.md"
    
    with open(lesson_path, "r") as f:
        content = f.read()
    
    # 检查是否已有同日期条目
    date_header = f"## {date_str} Kanban事件"
    if date_header in content:
        return  # 已存在，跳过
    
    entries = []
    for pattern, info in patterns.items():
        count = info["count"]
        severity = "🔴" if count >= 3 else "🟡"
        examples = info["examples"]
        assignee = examples[0]["assignee"]
        entries.append(
            f"- {severity} [{assignee}] ×{count}: `{pattern[:120]}`\n"
            f"  - 最近: {examples[0]['task_id']} ({examples[0]['time'][:19]})\n"
        )
    
    if entries:
        block = f"\n{date_header}\n" + "".join(entries) + "\n"
        with open(lesson_path, "a") as f:
            f.write(block)

def main():
    failures = get_recent_failures(hours=24)
    
    if not failures:
        print("✅ 近24小时无kanban异常事件")
        return
    
    by_domain = categorize_by_domain(failures)
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    for lesson_file, events in by_domain.items():
        patterns = deduplicate_patterns(events)
        append_to_lesson(lesson_file, patterns, today_str)
        
    total = len(failures)
    domains = len(by_domain)
    print(f"📊 采集完成: {total}个异常事件, {domains}个域")
    
    # 输出摘要供error-learner消费
    for domain, events in by_domain.items():
        patterns = deduplicate_patterns(events)
        for pattern, info in patterns.items():
            sev = "🔴" if info["count"] >= 3 else "🟡"
            print(f"  {sev} {domain}: ×{info['count']} - {pattern[:100]}")

if __name__ == "__main__":
    main()
