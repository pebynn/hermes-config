# precache_financial.py API Migration (2026-05-10)

## Problem

AKShare `stock_financial_abstract_ths` API broke — returns `AttributeError: 'NoneType' object has no attribute 'string'`. All 10 workers failed, 0 cache files produced in 8 minutes.

## Root Cause

The underlying website changed its HTML structure; AKShare's parser can no longer find the data element.

## Fix

**Switch to `stock_financial_abstract`** which returns a fundamentally different format:

### Old format (stock_financial_abstract_ths)
```
列: ['报告期', '基本每股收益', '净资产收益率', '营业总收入同比增长率', '资产负债率']
行: 每行一个报告期
```

### New format (stock_financial_abstract)
```
列: ['选项', '指标', '20260331', '20251231', ...]
行: 每行一个指标, 列是日期 (transposed)
```

### Indicator name changes
| Field | Old name | New name |
|:--|:--|:--|
| EPS | 基本每股收益 | 基本每股收益 ✅ (same) |
| ROE | 净资产收益率 | 净资产收益率(ROE) ⚠️ changed |
| Revenue | 营业总收入同比增长率 | 营业总收入 (absolute, NOT YoY) ⚠️ |
| Debt ratio | 资产负债率 | 资产负债率 ✅ (same) |

### Revenue YoY growth
The new API returns absolute revenue, not YoY growth. Must compute from consecutive same-quarter periods:
```python
prev_dc = str(int(dc) - 10000)  # e.g. 20260331→20250331
if prev_dc in date_data:
    prev_rev = _parse_float(date_data[prev_dc].get("_revenue"))
    yoy = (rev - prev_rev) / prev_rev
```

## Key Pitfalls

1. **ROE name change**: "净资产收益率" → "净资产收益率(ROE)" — exact match required
2. **Revenue is absolute**: Must compute YoY from consecutive periods
3. **Concurrency kills**: 10 workers → all 429'd. Use `--workers 2` max for this API
4. **5845 stocks × 2s = 3.2h**: Full refresh is slow, run in background
5. **Cache takes effect immediately**: signal_engine.py reads from `.finquant/cache/financial/`
