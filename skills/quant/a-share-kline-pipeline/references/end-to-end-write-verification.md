# 端到端写入验证 (verify_write) — P1-3 实现

**实现日期**: 2026-05-07
**状态**: ✅ 已上线
**涉及文件**: `~/quant/data_common.py` (定义), `~/quant/backfill_today_mysql.py` (调用), `~/quant/daily_kline_update.py` (调用)

## 概述

所有 K线数据写入 MySQL/Parquet 后，自动执行三向交叉验证：
- MySQL `stock_kline.kline` 表行数
- Parquet 缓存目录文件数
- 股票池 (`get_stock_list(market="all")`) 总数

不阻断流程，只报告差异并写入日志。

## 函数签名

```python
# data_common.py
def verify_write(date_str: str, expected_count: int = None) -> dict
```

## 返回值 (dict)

| Key | Type | Description |
|:----|:-----|:------------|
| `mysql_count` | int | `SELECT COUNT(*) FROM kline WHERE trade_date=?` |
| `parquet_count` | int | Parquet 文件数（`df.iloc[-1,0][:10]` 匹配该日期） |
| `stock_pool_count` | int | `get_stock_list(market="all")` 股票池总数 |
| `match` | bool | 所有检查通过 |
| `status` | str | `"PASS"` / `"WARN"` / `"FAIL"` |
| `delta` | dict | `mysql_vs_parquet_pct`, `mysql_vs_parquet_abs`, `mysql_vs_stock_pool_pct` |
| `details` | list[str] | 差异详情 |

## 验证规则

### Rule 1: mysql_count > 0 (FAIL)
MySQL 行数为 0 → **FAIL** — 数据完全没有写入。

### Rule 2: MySQL vs Parquet 差异 (FAIL/WARN)
- 差异 > 10% → **FAIL**: `MySQL(N) vs Parquet(M) 差异=X% > 10%`
- 差异 5-10% → **WARN**: `MySQL(N) vs Parquet(M) 差异=X% (5-10%)`
- 差异 < 5% → 通过
- Parquet 行数为 0 → **WARN**: `Parquet 缓存中无该日期数据`

### Rule 3: MySQL vs 股票池覆盖率 (WARN)
- MySQL 行数 < 股票池 × 90% → **WARN**: `MySQL(N) / 股票池(M) = X% < 90% (10%停牌正常)`
- ≥ 90% → 通过

## 调用点

### backfill_today_mysql.py (1 处)
数据写入循环完成后，末尾调用 `verify_write(TODAY)`。

### daily_kline_update.py (3 处，三路径各一)
1. **Tushare 路径** (~line 594): 批量更新缓存成功后, `return` 前
2. **雪球路径** (~line 640): 成功率 >80% 提前返回前
3. **AKShare 路径** (~line 680): `main()` 末尾最终出口

## 日志文件

验证结果写入 `~/quant/logs/verify_write_{YYYYMMDD}.log`:

```
=== 端到端写入验证: 2026-05-07 ===
状态: PASS
MySQL 行数: 4876
Parquet 文件数: 4892
股票池总数: 5415
一致性检查: PASS
delta.mysql_vs_parquet_pct: 0.3
delta.mysql_vs_parquet_abs: -16
delta.mysql_vs_stock_pool_pct: 90.0
```

## 设计决策

1. **不阻断流程**: 验证在写入完成后执行，发现差异只报告不回滚。原因：数据已写入，回滚可能造成更大不一致；差异通常由停牌/网络波动导致，次日自愈。

2. **复用 data_common._get_db_engine()**: 使用已有的 pool_pre_ping + pool_recycle 连接，不创建重复连接。

3. **日志写入不抛异常**: `_write_verify_log()` 的 try/except 吞掉所有异常，日志丢失不影响主流程。

4. **Parquet 计数基于文件遍历**: 遍历 `~/.finquant/cache/kline/*.parquet`，读每文件最后一行检查日期。对 ~5000 个文件约 0.5s，可接受。

5. **日期格式**: `YYYY-MM-DD` 字符串，与 kline 表 `trade_date` 列和 parquet 文件内日期列一致。

## 常见差异场景

| 差异 | 原因 | 是否正常 |
|:-----|:-----|:---------|
| mysql_count < parquet_count (小差) | 部分 parquet 写入成功但 MySQL upsert 失败 | 需排查 DB 错误日志 |
| mysql_count < stock_pool × 90% (恒态) | 停牌、未上市、数据源缺失 | 正常 — 但需关注趋势 |
| parquet_count = 0 | daily_kline_update 未运行或 Tushare/AKShare 均失败 | 需排查数据源 |
| mysql_count = 0 但 parquet_count > 0 | backfill_today_mysql.py 删除脏数据后未重新导入 | 需手动运行 backfill |

## 相关修改

- `data_common.py` L660-770: `verify_write()` + `_write_verify_log()` 定义
- `backfill_today_mysql.py` L7: 新增 import, L104-120: 调用
- `daily_kline_update.py` L21: 新增 import, L594-602/L640-648/L680-689: 三路径调用
