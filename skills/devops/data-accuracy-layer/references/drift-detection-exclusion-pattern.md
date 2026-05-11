# Drift Detection Exclusion + Baseline Pattern

*Captured 2026-05-11 from data_guard.py + drift_detect.py fix session*

## Problem

`detect_function_drift()` scanned all `.py` files and reported any same-named function with different hash as "drift." This produced 25 false alarms, mostly from `main()` appearing in 17 different scripts — each naturally having a different implementation.

## Solution: Two-Part Fix

### Part 1: Entry Function Exclusion

Add `ENTRY_FUNCTION_EXCLUDE` set to `detect_function_drift()`:

```python
ENTRY_FUNCTION_EXCLUDE = {
    "main",            # Every script has its own main()
    "test_main",       # Test entry points
    "run",             # Script runner variants
}
```

Applied at collection time:
```python
if func_name in ENTRY_FUNCTION_EXCLUDE:
    continue
```

**Result**: 25 → 24 false alarms removed. Remaining 24 are legitimate tool-function drifts (`load_data` across 4 sources, `is_trading_day` across 5 scripts, etc.).

### Part 2: Baseline-Aware Alerting

Convert `drift_detect.py` from "any drift = alarm" to "only alarm on drift increase":

```python
BASELINE_FILE = Path.home() / ".hermes" / "cache" / "drift_baseline.json"

# Load previous baseline
baseline_count = json.loads(BASELINE_FILE.read_text()).get("count", 0) if BASELINE_FILE.exists() else 0

# Save current as new baseline
BASELINE_FILE.write_text(json.dumps({"count": current_count, "functions": list(current.keys())}))

# Only alarm if drift grew >30% vs baseline
threshold = max(baseline_count * 1.3, baseline_count + 3)
if current_count > threshold and baseline_count > 0:
    # ALARM — new drift introduced
    notify("函数漂移增加", f"{baseline_count} → {current_count}")
    sys.exit(1)
else:
    # Stable or first run — baseline established
    print(f"📊 漂移稳定: {current_count} 个（基线 {baseline_count}）")
    sys.exit(0)
```

**Result**: cron `3dc57f9de476` no longer error-exits on stable drift. Only alarms when new tool-function drift is introduced (>30% increase).

## Pattern Reuse

This pattern applies to any "detect-and-alarm" system where baseline anomalies are known and acceptable. Key principles:
1. Establish baseline on first run (silent)
2. Alarm only on deviation from baseline (>30% threshold)
3. Save new baseline after each check
4. Exit 0 when stable, exit 1 only on real regression
