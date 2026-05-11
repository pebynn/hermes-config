# Fund Flow Cache Column Normalization Pattern (2026-05-10)

## Problem

Three different sources write fund flow parquet files with different column names:

| Source | File | Columns |
|--------|------|---------|
| `precache_fund_flow_financial.py` (East Money clist) | `fund_flow_{date}.parquet` | `net_inflow`, `net_pct`, `super_large_in`, `small_in`, `close` |
| `precache_fund_flow_full.py` (East Money fflow/daykline) | `fund_flow_{date}.parquet` | `main_flow`, `retail_flow`, `mid_flow`, `large_flow` |
| `stock_fund_flow.py` (stock-sdk Node.js) | `fund_flow_{date}.parquet` | `main_net`, `main_net_ratio`, `retail_net`, `score` |

After `stock_fund_flow.query_fund_flow(code)` returns `{}`, `signal_engine._compute_fund_flow()` gets `ff_score=50.0` (default).

## Solution: `_normalize_columns()`

```python
# stock_fund_flow.py
CACHE_COL_MAP = {
    "net_inflow": "main_net",
    "net_pct": "main_net_ratio",
    "super_large_in": "main_inflow",
    "small_in": "retail_net",
    "retail_flow": "retail_net",
    "main_flow": "main_net",
}

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """将缓存文件中的列名统一为 COL_MAP 输出格式."""
    df = df.rename(columns={k: v for k, v in CACHE_COL_MAP.items() if k in df.columns})
    # 确保必需列存在
    for col in ["main_net", "main_net_ratio", "retail_net", "score"]:
        if col not in df.columns:
            df[col] = 0.0 if col != "score" else 50.0
    # 如果 score 列全是默认值，尝试计算
    if (df["score"] == 50.0).all() and df["main_net"].notna().any():
        try:
            for idx, row in df.iterrows():
                df.at[idx, "score"] = compute_fund_flow_score(row.to_dict())
        except Exception:
            pass
    return df
```

Call `_normalize_columns()` in:
- `load_fund_flow_cache()` — after `pd.read_parquet()`
- `preload_fund_flow()` — after `pd.read_parquet()` inside the loop

## Second Issue: Cache File Naming

`stock_fund_flow.py` expected `{date}.parquet` while precache scripts used `fund_flow_{date}.parquet`.

**Fix**: Added `_cache_path(date_str)` helper returning `CACHE_DIR / f"fund_flow_{date_str}.parquet"`. All callers (`fetch_and_cache_today`, `load_fund_flow_cache`, `preload_fund_flow`) now use `_cache_path()`.

**Existing files renamed**:
```bash
cd ~/.finquant/cache/fund_flow
mv 2026-05-08.parquet fund_flow_2026-05-08.parquet
mv 2026-05-09.parquet fund_flow_2026-05-09.parquet
```
