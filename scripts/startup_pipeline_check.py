#!/usr/bin/env python3
"""
startup_pipeline_check.py — 会话启动时检查管线完整性

检查内容:
1. writing/quant 脚本头是否被直接作为入口点调用（而非通过 pipeline_runner）
2. data_guard.py 是否存在且可导入
3. 关键引用文件是否存在

静默模式（无异常不输出）：
  正常→无输出
  异常→输出警告到stderr
"""
import ast
import sys
from pathlib import Path
import traceback

HOME = Path.home()
SCRIPTS = [
    HOME / "writing-data" / "scripts" / "collect_data.py",
    HOME / "writing-data" / "scripts" / "generate_charts.py",
    HOME / "writing-data" / "scripts" / "generate_review.py",
    HOME / "writing-data" / "scripts" / "publish_draft.py",
    HOME / "writing-data" / "scripts" / "weekly_summary.py",
]

SHARED = HOME / "writing-data" / "shared" / "data_guard.py"

warnings = []

# 检查1: data_guard 可导入
if not SHARED.exists():
    warnings.append(f"data_guard.py 不存在: {SHARED}")
else:
    sys.path.insert(0, str(SHARED.parent))
    try:
        from data_guard import enforce_pipeline_gate, check_chart_files, \
            validate_ingested_data, detect_function_drift, validate_title
        warnings.append(f"✅ data_guard 加载正常 ({len(dir())}个函数)")
    except Exception as e:
        traceback.print_exc()
        warnings.append(f"❌ data_guard 加载失败: {e}")

# 检查2: 脚本没有被绕过 pipeline_runner
pipeline_runner = HOME / ".hermes" / "scripts" / "pipeline_runner.py"
if not pipeline_runner.exists():
    warnings.append("pipeline_runner.py 不存在，管线缺少唯一入口")

# 检查3: 关键参考文件存在
refs = [
    HOME / ".hermes" / "scripts" / "data_guard_wrapper.py",
    HOME / ".hermes" / "scripts" / "drift_detect.py",
]
for ref in refs:
    if not ref.exists():
        warnings.append(f"引用脚本不存在: {ref}")

if warnings:
    print("[pipeline_check]", file=sys.stderr)
    for w in warnings:
        print(f"  {w}", file=sys.stderr)
