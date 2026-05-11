#!/usr/bin/env python3
"""Drift detection wrapper — baseline-aware, only alert on new drift"""
import sys, os, json
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/writing-data/shared"))
from data_guard import detect_function_drift

BASELINE_FILE = Path.home() / ".hermes" / "cache" / "drift_baseline.json"
results = detect_function_drift()
current = {r["function"]: sorted(r["locations"]) for r in results}
current_count = len(results)

# Load baseline
baseline_count = 0
if BASELINE_FILE.exists():
    try:
        baseline = json.loads(BASELINE_FILE.read_text())
        baseline_count = baseline.get("count", 0)
    except Exception:
        pass

# Save current as new baseline
BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
BASELINE_FILE.write_text(json.dumps({"count": current_count, "functions": list(current.keys())}))

if current_count == 0:
    print("✅ 未发现函数漂移")
    sys.exit(0)

# Only alert if drift grew >30% vs baseline (new drift introduced)
threshold = max(baseline_count * 1.3, baseline_count + 3)
if current_count > threshold and baseline_count > 0:
    lines = [f"⚠️ 函数漂移增加: {baseline_count} → {current_count} (+{current_count - baseline_count})"]
    for func, locs in list(current.items())[:5]:
        lines.append(f"  {func}: {len(locs)} 个副本")
    msg = "\n".join(lines)
    print(msg)
    try:
        from notify import send
        send("函数漂移检测", msg)
    except Exception:
        pass
    sys.exit(1)
else:
    # Stable or first run — baseline established, no alert
    if baseline_count == 0:
        print(f"📊 基线已建立: {current_count} 个函数漂移（存量合理分化，不报警）")
    else:
        print(f"📊 漂移稳定: {current_count} 个（基线 {baseline_count}，阈值 {int(threshold)}）")
    sys.exit(0)
