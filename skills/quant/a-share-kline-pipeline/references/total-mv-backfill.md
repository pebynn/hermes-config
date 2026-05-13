# total_mv 回填手册 (2026-05-14)

## 背景

MySQL `kline` 表新增 `total_mv DECIMAL(16,2)` 列（单位：亿元），存储每只股票每个交易日的总市值。计算方式：

```
total_mv = close × totalShares / 100000000
```

## 数据源

**总股本（totalShares）来源：** stock-sdk MCP `get_all_a_share_quotes` → 提取 `totalShares` 字段 → 保存为 `/home/pebynn/quant/data/total_shares.json`。

**覆盖范围：** 5515只A股（含主板/创业板/科创板/北交所），CDR股票（如689009九号公司）需单独补充。

**刷新频率：** 总股本变动缓慢（季度级别），手动刷新即可。刷新方式：
- 通过 Hermes MCP `stock_sdk` → `get_all_a_share_quotes` 拉取全市场行情
- 提取 `totalShares` 字段写入 `data/total_shares.json`

## 回填流程

```bash
# 1. 添加列（一次性）
ALTER TABLE kline ADD COLUMN total_mv DECIMAL(16,2) DEFAULT NULL;

# 2. 运行回填脚本
~/tools/quant_env/bin/python3 ~/quant/scripts/backfill_total_mv.py
```

**回填脚本逻辑：**
1. 加载 `data/total_shares.json` → {code: totalShares}
2. 查询 DB 中有2024+数据的代码
3. 逐代码 UPDATE: `SET total_mv = ROUND(close * shares / 1e8, 2) WHERE code=? AND total_mv IS NULL`
4. 每500代码打印进度

**性能：** 5507只代码约5分钟，295万行。

## 每日增量

`daily_kline_update.py` 的 `_insert_to_db()` 已集成 total_mv 计算：
- 新增 `_load_total_shares()` 函数，懒加载 `data/total_shares.json`
- INSERT/UPDATE 时自动写入 total_mv
- 代码缺失 totalShares 时 total_mv 为 NULL

## 坑点

**CDR股票漏数据：** 689009（九号公司-WD）等CDR股票不在 `get_all_a_share_quotes` 快照中，需用 `get_quotes_by_query(["689009"])` 单独拉取，手动补入 `total_shares.json`。

**科创板代码排序靠后：** 回填按代码字母序处理，688/689代码排在末尾，进度条看起来卡住属正常。

**tushare daily_basic 无权限：** 用户只有 `daily` 接口可用，无法通过 tushare 获取总市值。stock-sdk 快照是唯一可用数据源。