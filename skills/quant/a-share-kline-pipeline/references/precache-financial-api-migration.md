# precache_financial.py API Migration — 2026-05-10

## Problem

`precache_financial.py` used `ak.stock_financial_abstract_ths()` which broke (AKShare HTML structure changed). All 10 workers got `AttributeError: 'NoneType' object has no attribute 'string'` — 0 successful caches.

## Fix: Switch to `stock_financial_abstract` + Adapt Format

### API Format Differences

| Old API | New API |
|:--|:--|
| `stock_financial_abstract_ths()` | `stock_financial_abstract()` |
| Columns: `['报告期', '基本每股收益', '净资产收益率', ...]` | Columns: `['选项', '指标', '20260331', '20251231', ...]` |
| Each row = one period | Each row = one indicator, columns = periods (TRANSPOSED) |

### Adaptation Code

```python
indicator_map = {
    "基本每股收益": COL_EPS,
    "净资产收益率(ROE)": COL_ROE,      # Note: "(ROE)" suffix — old map had no suffix
    "摊薄净资产收益率": COL_ROE,        # Fallback if ROE missing
    "营业总收入": "_revenue",          # Absolute value, not YoY growth
    "资产负债率": COL_DEBT_RATIO,
}

# Transposed format → {date: {field: value}}
date_data = {}
for _, row in df_raw.iterrows():
    indicator = str(row.get("指标", "")).strip()
    field = indicator_map.get(indicator)
    if not field:
        continue
    for dc in date_cols:
        val = row.get(dc)
        if val is None or val == "" or val == "—":
            continue
        date_data.setdefault(dc, {})[field] = str(val)

# Compute YoY revenue from consecutive periods
for dc in sorted(date_data.keys(), reverse=True):
    rev = _parse_float(dd.get("_revenue"))
    if rev and rev > 0:
        prev_dc = str(int(dc) - 10000)  # 20260331 → 20250331
        prev_rev = date_data.get(prev_dc, {}).get("_revenue")
        if prev_rev:
            yoy = (rev - prev_rev) / prev_rev
```

## Key Pitfalls

1. **Indicator name mismatch**: Old map had `"净资产收益率"`, new API has `"净资产收益率(ROE)"` with suffix
2. **YoY growth not provided**: Old API gave `"营业总收入同比增长率"` directly, new API only gives absolute `"营业总收入"` — must compute YoY from same-quarter-last-year
3. **Concurrency**: 10 workers hit rate limits. Reduced to 2 workers, 4939 stocks completed in 30min with 0 failures

## Results

- 4939 stocks refreshed, 0 failures, 30 minutes
- All L1 12 factors now have data (ROE + YoY revenue + EPS + debt_ratio populated)
- 5849 total cache files in `~/.finquant/cache/financial/`
