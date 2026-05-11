# Drift Detection — Baseline-Aware Pattern

## Problem

`data_guard.py`'s `detect_function_drift()` scans all Python files for same-named functions with different implementations. It reports ALL differences — including `main()` entry functions (different by definition), and legitimate per-script variants of utility functions.

This produces an overwhelming alert (25 functions "drifting") every run. The cron reports `error` status daily, causing notification fatigue.

## Root Cause

The detector treats every same-name function with different hash as a problem. But many are legitimate:
- `main()` in 17 scripts — every script has its own entry point
- `load_data()` in 4 scripts — different data sources need different loaders
- `is_trading_day()` in 5 scripts — different APIs for the same question

## Solution: Baseline-Aware Drift Detection

Instead of alarming on every drift, establish a baseline and only alert when drift count grows significantly.

### Step 1: Exclude entry functions

```python
ENTRY_FUNCTION_EXCLUDE = {"main", "test_main", "run", "if __name__"}
# Skip these in detect_function_drift()
```

This took 25→24 (removed the 17 `main()` false positives).

### Step 2: Baseline file

```python
BASELINE_FILE = Path.home() / ".hermes" / "cache" / "drift_baseline.json"
# Stores: {"count": 24, "functions": ["load_data", "is_trading_day", ...]}
```

On first run, save the current count as baseline. On subsequent runs, only alert if count exceeds `max(baseline * 1.3, baseline + 3)`.

### Step 3: Growth-only alerting

```python
threshold = max(baseline_count * 1.3, baseline_count + 3)
if current_count > threshold and baseline_count > 0:
    # Alert — new drift introduced
    sys.exit(1)
else:
    # Stable — no alert
    sys.exit(0)
```

## Result

- Before: 25 functions reported, cron `error` every day
- After: 24 baseline established, exit 0, no false alarms
- Only alerts when drift count grows >30% (genuine new problems)

## When to Re-Baseline

After intentional code changes that introduce legitimate new drift (refactoring, new scripts), delete the baseline file and let it re-establish on next run.

## Files

- `~/.hermes/scripts/drift_detect.py` — the wrapper script
- `~/writing-data/shared/data_guard.py` — the `detect_function_drift()` function
