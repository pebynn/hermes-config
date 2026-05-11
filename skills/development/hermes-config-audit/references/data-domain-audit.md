# Data-Centric Domain Audit Extension

This document extends `hermes-config-audit` for domains that manage their own data stores (parquet caches, MySQL, API pipelines). Use when the domain being audited has `~/quant/`-style script directories + MySQL + cron-driven data feeds.

---

## Expanded Phase 1: Asset Catalogue (data-domain variant)

In addition to the standard Phase 1 of `hermes-config-audit`, for data-centric domains add:

```
[总指挥 — 数据域扩展]
  ├─ search_files ~/quant/*.py → 完整脚本清单
  ├─ terminal wc -l ~/quant/*.py → 行数统计
  ├─ read_file 每个脚本的前25行 → 提取docstring功能描述
  ├─ terminal du -sh ~/.finquant/cache/* → 缓存大小
  ├─ terminal ls ~/.finquant/cache/kline/*.parquet | wc -l → 缓存文件数
  ├─ mcp_mysql_get_database_summary → 表结构
  ├─ mcp_mysql_run_select_query 源分布/最新日期/行数 → 数据健康
  └─ read_file 脚本头部 → 提取API引用 + 数据源矩阵
```

## Phase 2 Addition: Data Consistency Cross-Check

After collecting baseline data, run these specific checks:

### Cache-vs-DB freshness

```sql
-- Check: does MySQL have the same latest data as parquet?
SELECT MAX(trade_date) FROM kline;
```
```bash
# Spot-check: sample a known stock's parquet cache
python3 -c "
import pandas as pd; from pathlib import Path
f = Path.home() / '.finquant' / 'cache' / 'kline' / '600519.parquet'
df = pd.read_parquet(f)
col = '日期' if '日期' in df.columns else 'date'
print(f'Latest: {pd.to_datetime(df[col]).max()}')
"
```

If parquet has data that MySQL doesn't — this is a 🔴 data pipeline break. Flag immediately.

### Bulk cache-vs-DB scan
```bash
# Count parquet files with recent data vs MySQL count for same period
python3 -c "
import pandas as pd; from pathlib import Path
kline_dir = Path.home() / '.finquant' / 'cache' / 'kline'
recent = 0
for f in kline_dir.glob('*.parquet'):
    try:
        df = pd.read_parquet(f)
        col = '日期' if '日期' in df.columns else 'date'
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
            if (df[col] >= '2026-05-01').any():
                recent += 1
    except: pass
print(f'Parquet files with recent data: {recent}')
"
```

Then compare against `SELECT COUNT(*) FROM kline WHERE trade_date >= '2026-05-01'`.

Mismatch = MySQL write path broken (common causes: wrong env, SQLAlchemy connection string, cron toolsets missing MySQL MCP, or `source` column constraint).

### API source matrix

Build from script headers (read first 25 lines of every .py that mentions `import akshare`, `import tushare`, `xueqiu`, etc.):

| Source | Scripts Using It | Status | Expiry/Risk |
|:-------|:-----------------|:-------|:------------|
| AKShare | daily_kline_update, precache_*, margin_data | ✅ primary | offline 19:00-08:00 |
| Tushare | tushare_data_pipeline, daily_kline_update | ✅ supplement | needs token file |
| Xueqiu | xueqiu_kline, kline_fallback | ✅ fallback | cookie expires ~30d |

### Script redundancy detection

Pattern: scripts with overlapping docstrings/functions. Detection:
```bash
# Find pairs with similar names suggesting overlap
ls ~/quant/*.py | grep -E 'check|import|bulk|convert' | sort
# Manually read first 5 lines of each pair → identify redundancy
```

Common offenders: `check_cache` vs `check_cache_v2` vs `debug_cache`, `import_*_mysql` vs `bulk_*_mysql`, `convert_*` vs `download_*` (historical one-shots).

### Cron-to-data-feed mapping

Map each finance cron to its data target:

| Cron | Schedule | Targets | Expected Output |
|:-----|:---------|:--------|:----------------|
| daily_kline_update | 16:00 | parquet + MySQL kline | ~5000 new rows |
| L4 margin | 16:15 | parquet margin/ | 1 new file |
| multi-factor+signal | 21:00 | daily_signal + detail | 2-3 new rows |

Then verify: was the cron's last run actually reflected in the target?
- If `last_status: ok` but target has no new data → write path broken
- If `last_status: error` → investigate separately
- If `next_run_at` in past but `last_run_at` is null → cron never triggered (first-run pending)

### credential expiry check

```bash
# Check token files exist and are recent
stat -c '%Y' ~/.finquant/tushare_token | xargs -I{} date -d @{} '+%Y-%m-%d'
stat -c '%Y' ~/.hermes/credentials/xueqiu_cookies.json | xargs -I{} date -d @{} '+%Y-%m-%d'
```

Flag any that are >30 days old as credential-expiry risk.

---

## Severity Upgrade Rules for Data Domains

Standard `hermes-config-audit` uses P1/P2/P3. For data domains, add:

| Condition | Severity |
|:----------|:---------|
| MySQL-parquet mismatch (parquet has data, DB doesn't) | 🔴 P0 — data pipeline break |
| MySQL latest date > 3 trading days behind | 🔴 P0 |
| Cron `last_status: ok` but target has no new data | 🔴 P0 |
| Single API source with no fallback | 🟠 P1 |
| Cookie/token > 25 days old | 🟠 P1 |
| Scripts with >80% functional overlap | 🟡 P2 |
| Non-critical cron never ran (first-run pending) | 🟡 P2 |

---

## Report Integration

When producing a data-domain audit report, add these sections to the standard `hermes-config-audit` Phase 4 output:

- **Data Health**: MySQL freshness, cache coverage, parquet-vs-DB gap
- **API Pipeline Status**: Source matrix with fallback chain diagram
- **Script Inventory**: Full table with line counts + descriptions + redundancy flags
- **Cron-to-Data Mapping**: Which cron feeds which store, with last-write verification
