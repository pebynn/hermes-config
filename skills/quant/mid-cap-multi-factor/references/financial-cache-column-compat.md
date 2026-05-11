# Financial Cache Column Compatibility Pattern (2026-05-10)

## Problem

`signal_engine.py` `_compute_layer1()` searches for Chinese column names (`基本每股收益`, `每股净资产` etc.) but the financial cache (`~/.finquant/cache/financial/{code}.parquet`) was written in English by `precache_fund_flow_financial.py` (East Money API), yielding only: `code, name, pe, pe_ttm, pb, eps, total_mv, float_mv, date`.

Result: L1 factors all NaN → industry neutralization fillna(0) → l1_total=0 → l1_scaled=50 constant.

## Solution Pattern: `_fin_val()`

```python
def _fin_val(col_cn, col_en, col_en2=None, default=None):
    """从 fin_df 取值，优先中文列名，回退英文列名。"""
    if fin_df is None:
        return default
    if col_cn in fin_df.columns:
        v = _to_float(fin_df[col_cn].iloc[-1])
    elif col_en in fin_df.columns:
        v = _to_float(fin_df[col_en].iloc[-1])
    elif col_en2 and col_en2 in fin_df.columns:
        v = _to_float(fin_df[col_en2].iloc[-1])
    else:
        return default
    return v
```

### Mapping Table

| Factor (result key) | col_cn (akshare THS) | col_en (East Money) | col_en2 (alternate) |
|---------------------|----------------------|---------------------|---------------------|
| l1_ep | 基本每股收益 | eps | — |
| l1_bp | 每股净资产 | bps | — |
| l1_roe_stability | 净资产收益率 | roe | — |
| l1_net_margin | 销售净利率 | net_margin | net_profit_margin |
| l1_revenue_growth | 营业总收入同比增长率 | revenue_yoy | yoy_revenue |
| l1_profit_growth | 净利润同比增长率 | profit_yoy | yoy_profit |

### Available Factors (English-only cache)

With the English-only cache (only `eps`, `pb`, `pe`, `total_mv`), the following L1 factors work:
- **l1_ep** = eps / price (needs `eps` column)
- **l1_bp** = bps / price (needs `bps` or falls back to shares/market_cap)
- **l1_mom_12m, l1_reversal_1m** — from K-line, no financial cache needed
- **l1_vol_60d, l1_maxdd_60d** — from K-line
- **l1_turnover_1m, l1_volume_ratio** — from K-line

Missing with English-only cache: l1_roe_stability, l1_net_margin, l1_revenue_growth, l1_profit_growth.

### Fix

Two complementary approaches:
1. **Code-level** (done 2026-05-10): Above `_fin_val()` pattern in `_compute_layer1()`
2. **Cache-level** (recommended): Run `precache_financial.py --force` to overwrite with THS Chinese-column multi-row format
   ```bash
   cd ~/quant && ~/tools/quant_env/bin/python3 precache_financial.py --market all --workers 10 --force
   ```
   This takes ~5-8 min for 5800+ stocks. After this, all 12 factors are available.
