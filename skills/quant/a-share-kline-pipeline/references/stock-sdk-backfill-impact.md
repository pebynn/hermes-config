# stock-sdk 数据回填影响评估 (2026-05-08)

## 背景

`backfill_kline.py`（历史 parquet→MySQL 批量导入脚本）仅写入 8 列：code、trade_date、open、high、low、close、volume、amount、source。**不包含** pct_chg、change、amplitude、turnover 四列。

结果：MySQL stock_kline.kline 表的 `parquet_backfill` 源数据中，这四列全部为 NULL。

stock-sdk（基于腾讯 gtimg.cn 数据源的 Node.js 回填工具）将这些 NULL 列更新为有效值。

## MySQL 现状 (2026-05-08)

```
总行数:     7,069,553
stock_sdk:  2,750,600  (39%)  ← 已更新
NULL rows:  4,318,953  (61%)  ← 待回填
```

stock-sdk 仍在进行中，已完成 ~39%。

## 影响到的列

| 列 | 原值 | 新值 | 说明 |
|:---|:-----|:-----|:-----|
| pct_chg | NULL → 有效涨跌幅% | | signal_engine 自动受益 |
| change | NULL → 有效涨跌额 | | 仅展示用，无策略依赖 |
| turnover | NULL → 有效换手率% | | signal_engine L1情绪因子自动受益 |
| amplitude | NULL → 有效振幅% | | 仅展示用 |

## 脚本影响矩阵

### 自动受益 (无需改动)

| 脚本 | 受益部分 | 说明 |
|:-----|:---------|:-----|
| signal_engine.py | L1情绪因子 `l1_turnover_1m` | 之前 turnover 全 NaN → l1_turnover_1m 恒为 NaN。现在有效，L1总分改善 |
| data_bridge.py | get_market_summary() | 读 pct_chg 展示指数涨跌幅，NULL→有效值后展示不再缺数据 |
| daily_signal_report.py | get_zz500_info() | 读中证500涨跌幅，同理受益 |

### 无影响

| 脚本 | 原因 |
|:-----|:-----|
| data_common.py | cache_get() 优先 MySQL，返回全部列；parquet回退也读原列。无NULL处理逻辑 |
| backfill_today_mysql.py | 全列映射，无workaround |
| bulk_import_to_mysql.py | 全列映射，无workaround |
| all writing-domain scripts | 不直接读 MySQL kline 表，通过 AKShare→JSON 采集 |
| precache_kline.py | 写 parquet 而非读 MySQL，不受 NULL 影响 |
| precache_xueqiu.py | 同上 |

### 有 workaround 但无需紧急调整

| 脚本 | 位置 | workaround | 建议 |
|:-----|:-----|:-----------|:-----|
| daily_kline_update.py | L397 (fetch_today_akshare) | AKShare回退路径 `df["涨跌幅"] = 0.0` (单日数据无pct_change，填0) | 建议用 pre_close 计算：`((close - pre_close) / pre_close * 100).round(2)` |
| precache_kline.py | L184 (雪球数据源) | `fillna(0.0)` 用于防NaN | 可改为 `fillna(None)` 保留原始缺失标记 |

> **优先级**: AKShare 是 daily_kline_update 的最后回退（tushare→雪球→AKShare），极少触发。改成 pre_close 计算是低优优化。

## 验证方法

```sql
-- 检查回填进度
SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN pct_chg IS NULL THEN 1 ELSE 0 END) as null_pct_chg,
  SUM(CASE WHEN turnover IS NULL THEN 1 ELSE 0 END) as null_turnover,
  SUM(CASE WHEN source = 'stock_sdk' THEN 1 ELSE 0 END) as stock_sdk_rows,
  ROUND(SUM(CASE WHEN source = 'stock_sdk' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) as pct_done
FROM stock_kline.kline;

-- 检查数据源分布
SELECT source, COUNT(*) as cnt FROM stock_kline.kline GROUP BY source ORDER BY cnt DESC;

-- 抽样验证 stock_sdk 数据质量 (对比 tushare 同日期)
SELECT code, trade_date, pct_chg, source
FROM stock_kline.kline
WHERE source = 'stock_sdk'
  AND trade_date = '2026-05-08'
LIMIT 10;
```

## 数据源回退链 (增量更新，不受 stock-sdk 影响)

```
daily_kline_update.py:
  tushare pro.daily()      → 1次批量拉全A股 (含真实pct_chg/change, 自算振幅/换手率)
    ↓ 失败
  雪球 get_stock_kline()   → 逐只拉取 (含change_pct/amplitude/turnover, 成交额用close×vol估算)
    ↓ 失败
  AKShare stock_zh_a_daily  → 逐只拉取 (无pct_chg/change, 手动填0.0 ← workaround)

precache_kline.py:
  雪球 → 腾讯stock_zh_a_daily → 腾讯stock_zh_a_hist_tx → 东财stock_zh_a_hist → 雪球(重试)
```

stock-sdk 不参与增量更新管线。它的角色是历史数据回填（修复 parquet_backfill 的 NULL 列），不修改 daily_kline_update 等增量脚本的行为。
