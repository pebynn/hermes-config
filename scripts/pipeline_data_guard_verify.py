#!/usr/bin/env python3
"""pipeline_data_guard_verify.py — 验证 data_guard 观察期日志"""
from pathlib import Path
from datetime import datetime, timedelta
import json
import traceback

LOG_FILE = Path.home() / "writing-data" / "logs" / "data_guard.log"
now = datetime.now()

if not LOG_FILE.exists():
    print("📭 data_guard 日志不存在 — 管线可能未触发")
    exit(1)

lines = LOG_FILE.read_text().strip().split('\n')
total_entries = len(lines)

# 最近7天
recent = []
for line in lines:
    try:
        entry = json.loads(line)
        recent.append(entry)
    except:
        traceback.print_exc()
        pass

# 统计
from collections import Counter
sources = Counter(e.get("source", "unknown") for e in recent)
total_rows = sum(e.get("rows", 0) for e in recent)
errors = [e for e in recent if e.get("errors")]

print(f"data_guard 观察期报告")
print(f"{'='*50}")
print(f"  日志周期: {LOG_FILE}")
print(f"  总调用: {len(recent)} 次")
print(f"  总数据行: {total_rows}")
print(f"  异常: {len(errors)} 次")
print()

if errors:
    print("  ⚠️ 异常详情:")
    for e in errors[:5]:
        print(f"    API: {e.get('api')}")
        print(f"    错误: {e.get('errors')}")
        print()

print(f"  数据源分布:")
for src, cnt in sources.most_common():
    print(f"    {src}: {cnt} 次")

print()
if len(errors) == 0:
    print("  ✅ data_guard 观察期零异常，可安全删除旧路径")
elif len(errors) <= 3:
    print(f"  ⚠️ {len(errors)} 次小异常，建议保留旧路径再观察一周")
else:
    print(f"  ❌ {len(errors)} 次异常，需要排查后决定")
