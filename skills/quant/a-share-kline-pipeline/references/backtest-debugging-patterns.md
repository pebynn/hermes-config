# Backtest Debugging Patterns

Recurring bugs found when debugging A-share backtest scripts.

## 1. NAV Stuck at 1.0 (Most Common)

**Symptom:** Backtest completes with all NAV=1.0, total return=0.00%, extreme negative Sharpe.

**Root cause:** The rebalance-day condition checks `d in pos` where `d` is a date string but `pos` is a `{code: weight}` dictionary. The date string is never a key in the stock dictionary, so the condition is always False.

**Fix:** Replace `d in rb_set and d in pos and pos` with `d in rb_set and pos`.

**Checklist:**
- Search for `d in pos` or `date in pos` patterns in the NAV calculation loop
- The correct pattern is `pos` (non-empty dict check) or `len(pos) > 0`
- This bug affected mid_cap_momentum_rotation.py v1.3

## 2. K-line Data Unavailable (kline_get returns None)

**Symptom:** "无法获取交易日历" error, or all industry scores = 50.0/51.1 (uniform percentiles), or "选股无结果" for all periods.

**Three common causes:**

### 2a. Cache File Prefix Mismatch

Files in `~/.finquant/cache/kline/`:
- `{code}.parquet` — written by daily_kline_update.py / precache_kline.py
- `k_{code}.parquet` — written by get_kline_cached() in mid_cap_enhanced.py

`kline_get(code)` was originally hardcoded to read `k_{code}.parquet` only. If only `{code}.parquet` exists, it returns None.

**Fix:** `kline_get` now tries both prefixes: `k_{code}.parquet` first, then `{code}.parquet`.

### 2b. Chinese Column Names

daily_kline_update.py saves with Chinese column names:
```
日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
```
But strategy scripts expect English:
```
trade_date, open, close, high, low, volume, amount, amplitude, pct_chg, change, turnover
```

When `kline_get` reads a Chinese-named file and returns it, the strategy crashes with `KeyError: 'close'`.

**Fix:** `kline_get` now has `_COL_CN2EN` mapping dict that renames Chinese→English columns.

### 2c. API Fallback Timeout

When neither cache file exists, `kline_get` falls back to `get_kline_cached()` which calls `stock_zh_a_hist_tx()` API. This takes 3-10 seconds per stock for the first call. With 4966 candidate stocks, the first backtest run crawls.

**Fix:** Pre-populate cache via `precache_kline.py` before running large backtests:
```bash
~/tools/quant_env/bin/python3 ~/quant/precache_kline.py --workers 20
```

## 3. Industry Scores All Equal (~50 or 51.1)

**Symptom:** All industries get the same total_score (~50 or 51.1), so ranking picks arbitrary ones.

**Root cause:** When ALL industries get the same score in one signal dimension (e.g., all momentum=0 because kline_get returned None), the percentile ranking assigns 50 to all. Combined uniform signals = uniform total score = no differentiation.

**Calculation:** If momentum_rank=50 (all equal), capflow_rank=50 (all equal), structure_rank=50 (all equal):
```
0.35 × 50 + 0.35 × 50 + 0.30 × 50 = 50.0
```

The 51.1 seen in practice comes from slight float variations in the percentile calculation when not all values are exactly equal but very close.

**Fix:** Ensure kline_get returns data (see section 2). If data truly unavailable, the strategy should handle gracefully (fall back to alternative signals rather than returning uniform values).

## 4. Industry Rotation Doesn't Change During Backtest

**Symptom:** The same 4 industries appear in all 64 rebalance periods.

**Root cause:** Future data leakage — scoring functions read the latest K-line data (the last row in cache) instead of filtering by `date_str` to only use data available at that point in time.

**Check:**
```python
# In calc_industry_momentum, calc_trend_quality, etc.:
kdf = kdf.sort_values("trade_date")
kdf = kdf[kdf["trade_date"] <= date_str]  # ← This line must be present
```

Without this filter, `closes[-1]` gives the MOST RECENT close price, which includes future data for all backtest periods.

**Verification:** Add debug logging:
```python
print(f"  date={date_str}, industries={[t['industry'] + '(' + str(round(t['score'],1)) + ')' for t in top_industries]}", file=sys.stderr)
```

## 5. Industry Mapping Errors

**Symptom:** Stocks assigned to wrong industries (e.g., 杭州热电→纺织服饰, 国检集团→银行).

**Root cause:** The SW industry classification API returns codes that get mapped incorrectly, or the stock's industry changed after the cached data was built.

**Fix:** Add to `_STOCK_INDUSTRY_OVERRIDE` dict in `mid_cap_enhanced.py`:

```python
"603060": "社会服务",    # 国检集团 — 检测认证
"603290": "电子",        # 斯达半导 — 半导体
"603393": "公用事业",    # 新天然气 — 天然气
"605011": "电力",        # 杭州热电 — 热电
```

Always clear cache after changes:
```bash
rm -f ~/.finquant/cache/shares/industry_map.parquet
```

**Watch for duplicates:** The same stock code can appear in TWO override entries (e.g., 601388 was in both "环保" and "公用事业" sections). The last entry wins, which is usually wrong.

## 6. Final Calculation Crashes (OOM / JSON Serialization)

**Symptom:** Backtest completes all 64 periods, then hangs at `[回测] 加载 N 只持仓股K线...` or crashes with exit code 1.

**Root causes:**
- `get_kline_cached` API fallback for 200+ held stocks (each takes 3-10s)
- JSON serialization fails on numpy.bool_ type: `TypeError: Object of type bool is not JSON serializable`
- Pre-loading all held stock K-lines into memory (248 stocks × 300 days × 11 columns → ~8MB, plus overhead)

**Fixes:**
- All `json.dump/json.dumps` must have `default=str`
- Use `get_kline_cached` with API fallback (not `kline_get` cache-only) for NAV calculation
- Add progress logging for held-stock loading

## 7. Stock Pool Filtering Changes

**Symptom:** Candidate stock count changes unexpectedly (e.g., 3017 → 4966).

**Root cause:** `data_common` integration changed the stock list function. Previously, `get_eligible_stocks` filtered only main-board (3000 stocks). With `market='all'`, it returns all A-shares (4966 stocks, 110 industries).

The rotation strategy defaults to `market='all'` while the multi-factor strategy defaults to `market='main'`. Check the default in each script:
- `mid_cap_momentum_rotation.py`: default `--market=all`
- `mid_cap_enhanced.py`: default `market='main'`

## 8. MySQL Priority Timeout (2026-04-30)

**Symptom:** Backtest runs at ~1 period per 40-45 seconds. Progress bars show industry scoring at 1.0-1.2 it/s instead of expected 2.0+ it/s. No MySQL error messages visible but log is spammed with `[data_common] DB查询失败` after the fact.

**Root cause:** `kline_get()` had MySQL (kline_from_db) as priority 1. MySQL on localhost:3306 was not running, causing a ~30s connection timeout per unique stock PER PERIOD. With 110 industries × 2 workers, the 30s timeout blocked 2 scoring threads for each period.

**Detection:** Check log for `[data_common] DB查询失败: (pymysql.err.OperationalError) (2003, "Can't connect to MySQL server on 'localhost' ([Errno 111] Connection refused)")`.

**Fix (v2026-04-30):** Reorder priority — cache #1, MySQL #3 with exception catch. When MySQL is unreachable, the exception is caught in ~0.1s instead of hitting the default 30s timeout.

**Performance impact:**
- Before (MySQL #1): ~1.0 it/s industry scoring, 40-45s per period
- After (cache #1): ~2.2 it/s industry scoring, 25-30s per period
