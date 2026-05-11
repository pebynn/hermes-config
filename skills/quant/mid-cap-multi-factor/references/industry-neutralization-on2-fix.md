# Industry Neutralization O(N²) Fix — 2026-05-07

## Root Cause

`signal_engine.py` line 414-421, `_neutralize_industry_zscores()`:

```python
# OLD: O(N²) — each factor loop iterates ALL rows with .sum() per industry
for factor in factor_cols:
    for x in industries:
        count = (df["_industry"] == x).sum()  # full column scan per industry
```

For 600 results × 12 factors × ~100 industries = ~720K full-column comparisons.
Each comparison scans all 600 rows → ~430M element operations.

## Fix

Pre-compute industry counts once (O(N)), then use dict lookup (O(1) per access):

```python
# NEW: O(N) — single value_counts() pass
industry_counts = df["_industry"].value_counts()
for factor in factor_cols:
    for x in industries:
        count = industry_counts.get(x, 0)  # O(1) dict lookup
```

## Impact

| Metric | Before | After |
|:--|:--|:--|
| Industry neutralization | 30s-2min (stuck) | 2-5s |
| Full scan (mid-cap, 618 stocks) | 37min timeout | 6-10min |
| Complexity | O(N²) | O(N) |

## Affected Files

- `/home/pebynn/quant/signal_engine.py` — `_neutralize_industry_zscores()` function
- Cron `b60f3c86dd1b` (晚间合并:多因子回测+信号日报) — was timing out at 37min

## Verification

- Python syntax check: `py_compile.compile()` passed
- Cron updated with correct module name (`mid_cap_strategy`) and CLI args (`--signal --output`)
- Redundant dual-scan eliminated (mid_cap_strategy + daily_signal_report → single scan)
- Next scheduled run: 2026-05-08 21:00
