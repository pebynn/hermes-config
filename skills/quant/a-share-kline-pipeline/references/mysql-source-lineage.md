# Kline 表 source 列血统追踪 — 实现笔记

## 背景

`stock_kline.kline` 表有 ~6.8M 行历史数据，来自三个数据源（tushare/akshare/xueqiu），此前无法区分来源。2026-05-07 新增 `source` 列实现血统追踪。

## SQL 迁移

```sql
ALTER TABLE kline ADD COLUMN source VARCHAR(16) DEFAULT NULL;
```

- 历史数据保持 NULL，不触发表重建
- VARCHAR(16) 容纳 `tushare`/`akshare`/`xueqiu`，留有扩展空间

## UPSERT 安全设计模式

核心问题：`_insert_to_db` 同时处理 UPDATE 和 INSERT 路径。如果直接 `SET source=:src`，则在非显式传 source 的调用中会将已有非NULL source 覆盖为 NULL。

**解决**: UPDATE 使用 `COALESCE(:src, source)`：

```sql
UPDATE kline SET
  open=:o, close=:c, ...,
  source=COALESCE(:src, source)   -- NULL-safe: 不传source则保留旧值
WHERE code=:code AND trade_date=:td
```

INSERT 直接使用 `:src`（新行无旧值可保留）。

## 三数据源写入点

| 函数 | source 值 | 文件行 |
|:-----|:---------|:------|
| `update_cache_from_row()` | `'tushare'` | daily_kline_update.py:353 |
| `fetch_today_akshare()` | `'akshare'` | daily_kline_update.py:428 |
| `fetch_today_xueqiu()` | `'xueqiu'` | daily_kline_update.py:523 |
| `backfill_today_mysql.py` | 透传 parquet 的 source 列 | backfill_today_mysql.py:78 (COL_MAP fallthrough) |

## backfill 透传机制

`backfill_today_mysql.py` 不需要显式修改 — 其 `COL_MAP.get(k, k)` 模式（key 不在映射表则原样保留 key）自动将 parquet 中的 `source` 列透传写入 MySQL：

```python
for k, v in row.items():
    en_k = COL_MAP.get(k, k)   # "source" not in COL_MAP → stays "source"
    renamed[en_k] = v
```

pd.to_sql 自动匹配同名列。旧 parquet 无 source 列时 MySQL 写入 NULL。

## 添加类似元数据列的检查清单

当需要给现有大表加元数据列时：

1. **ALTER TABLE** 加列（DEFAULT NULL，避表重建）
2. **UPDATE 路径**: 使用 COALESCE(:new_col, new_col) 保护已有非NULL值
3. **INSERT 路径**: 直接使用参数值
4. **调用方**: 每个数据路径显式传值
5. **回填脚本**: 检查是否自动透传（如 pd.to_sql 的列匹配），否则显式处理
6. **验证**: `SELECT new_col, COUNT(*) FROM table GROUP BY new_col` 确认分布
