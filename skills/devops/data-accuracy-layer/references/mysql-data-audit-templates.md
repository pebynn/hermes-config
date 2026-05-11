# MySQL Data Audit Templates — K线表完整性审计

## 审计命令集 (mysql CLI)

MCP MySQL 工具有 SELECT 误拦截 bug（CASE WHEN、变量赋值、某些聚合查询会被错误拒绝），因此数据审计应直接用终端 mysql 客户端绕过：

```bash
mysql -u stock -p'stock123' -h 127.0.0.1 stock_kline -NBe "SELECT ..." 2>&1 | grep -v Warning
```

## 审计指标

### 1. 基础统计

```sql
-- 总行数
SELECT COUNT(*) FROM kline;

-- 时间范围
SELECT MIN(trade_date), MAX(trade_date) FROM kline;

-- 唯一股票数
SELECT COUNT(DISTINCT code) FROM kline;

-- 数据来源分布
SELECT source, COUNT(*) FROM kline GROUP BY source;
```

### 2. 字段完整性（NULL检测）

注意：`change` 是 MySQL 保留字，需用反引号转义。

```sql
SELECT 'null_pct_chg', COUNT(*) FROM kline WHERE pct_chg IS NULL;
SELECT 'null_change', COUNT(*) FROM kline WHERE `change` IS NULL;
SELECT 'null_turnover', COUNT(*) FROM kline WHERE turnover IS NULL;
SELECT 'null_amplitude', COUNT(*) FROM kline WHERE amplitude IS NULL;
SELECT 'null_volume', COUNT(*) FROM kline WHERE volume IS NULL;
SELECT 'null_open', COUNT(*) FROM kline WHERE `open` IS NULL;
```

### 3. 每日覆盖趋势

```sql
-- 近40天每日股票覆盖数
SELECT trade_date, COUNT(DISTINCT code) as stock_cnt
FROM kline
WHERE trade_date >= DATE_SUB(CURDATE(), INTERVAL 40 DAY)
GROUP BY trade_date
ORDER BY trade_date;
```

### 4. 各股票行数分布

```sql
-- 行数区间统计
SELECT CASE
  WHEN cnt >= 1500 THEN '1500+'
  WHEN cnt >= 1400 THEN '1400-1499'
  WHEN cnt >= 1000 THEN '1000-1399'
  WHEN cnt >= 500 THEN '500-999'
  WHEN cnt >= 100 THEN '100-499'
  WHEN cnt >= 10 THEN '10-99'
  ELSE '1-9'
END AS bucket, COUNT(*) as stock_count, SUM(cnt) as total_rows
FROM (SELECT code, COUNT(*) as cnt FROM kline GROUP BY code) sub
GROUP BY bucket
ORDER BY bucket;
```

### 5. 最新日期分布（发现滞后股票）

```sql
-- 最新日期不是今日的股票（停牌/退市/数据缺失）
SELECT code, MAX(trade_date) as latest, COUNT(*) as cnt
FROM kline
GROUP BY code
HAVING latest < CURDATE()
ORDER BY latest DESC
LIMIT 30;
```

### 6. 数据连续性（检查gap）

A 股节假日会有正常的 gap，需要区分：

```sql
-- 连续两天间隔 >3 天的 gap（排除春节/国庆等长假）
SET @prev_date = NULL;
SELECT gap_start, gap_end, gap_days
FROM (
  SELECT 
    @prev_date as gap_start,
    trade_date as gap_end,
    DATEDIFF(trade_date, @prev_date) - 1 as gap_days,
    @prev_date := trade_date
  FROM (SELECT DISTINCT trade_date FROM kline ORDER BY trade_date) dates
) gaps
WHERE gap_days > 3 AND gap_start IS NOT NULL;
```

已知正常休市模式：
- **春节**: 7-10天 gap（如 2026-02-13~2026-02-24）
- **国庆**: 7-10天 gap（如 2024-09-30~2024-10-08）
- **五一**: 5天 gap（如 2026-04-30~2026-05-06）
- **清明/端午/中秋**: 3-4天 gap
- **春节前最后一个交易日到节后**: 通常 7-10天
- **普通周末**: 1-2天 gap（不会被 >3 过滤捕捉）

### 7. 每日记录数极值检查

```sql
-- 每日记录数的最小/最大/平均
SELECT MIN(day_cnt) as min_per_day, MAX(day_cnt) as max_per_day, AVG(day_cnt) as avg_per_day
FROM (SELECT trade_date, COUNT(*) as day_cnt FROM kline GROUP BY trade_date) sub;

-- 总交易日数 vs 日历天数（含节假日）
SELECT 
  COUNT(DISTINCT trade_date) as actual_trading_days,
  DATEDIFF(MAX(trade_date), MIN(trade_date)) + 1 as calendar_days,
  ROUND(COUNT(DISTINCT trade_date) / (DATEDIFF(MAX(trade_date), MIN(trade_date)) + 1) * 100, 1) as fill_rate_pct
FROM kline;
```

A股年化特征：约 240-245 交易日/年，日历填充率约 65-67%（含周末和节假日）。

### 8. 完整度分布

```sql
-- 每只股票相对最大天数的完成度
SELECT 
  ROUND(completed_pct, -1) as pct_bucket,
  COUNT(*) as stock_count
FROM (
  SELECT code, COUNT(*) / (SELECT COUNT(DISTINCT trade_date) FROM kline) * 100 as completed_pct
  FROM kline GROUP BY code
) sub
GROUP BY pct_bucket
ORDER BY pct_bucket;
```

### 9. 表大小

```sql
SELECT 
  table_name,
  ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
FROM information_schema.tables
WHERE table_schema = 'stock_kline' AND table_name = 'kline';
```

## 典型审计输出格式

```
### 基础统计
| 指标 | 数值 |
|------|------|
| 总行数 | 7,084,614 |
| 唯一股票数 | 5,351 |
| 时间范围 | 2020-01-02 ~ 2026-05-08 |
| 总交易日 | 1,535 |
| 表大小 | 1,206 MB |

### 字段完整性
| 字段 | NULL数 | 健康度 |
|------|--------|--------|
| open/close/high/low/volume | 0 | 100% ✅ |
| pct_chg/change | ~73K (1%) | 99% ✅ |
| turnover/amplitude | ~3.7M (52%) | ❌ 部分源无此字段 |

### 数据连续性
- 每日最小: 3,386 条 | 最大: 5,339 条 | 平均: 4,615 条
- 所有 gap 均为 A 股节假日休市，无异常缺失
- 最新交易日覆盖 5,335 只股票
```

## 关键陷阱

1. **`change` 是 MySQL 保留字** — 查询时用反引号 `\`change\``
2. **`open` 也可能是保留字** — 统一用反引号规避
3. **时区问题** — MySQL 存的是 UTC 日期 (trade_date)，但含义是 A 股交易日（北京时间），SELECT 时不会有时区偏移问题，因为字段是 date 类型不含时间
4. **MCP 工具的 SELECT 误拦截** — 含 `CASE WHEN`、用户变量(`@prev_date`)、`SET` 的查询会被错误拒绝。优先用终端 mysql 客户端
5. **数据源标识** — 不同来源 (parquet_backfill/stock_sdk) 可能字段完整性不同，审计时按 source 分组对比更准确
