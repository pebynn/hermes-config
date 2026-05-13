# kline 表 Schema (stock_kline.kline)

最后更新: 2026-05-14

## 列定义

| 列 | 类型 | 说明 | 单位 |
|:--|:--|:--|:--|
| id | bigint PK | 自增 | — |
| code | varchar(12) | 6位代码 | — |
| trade_date | date | 交易日 | YYYY-MM-DD |
| open | decimal | 开盘价 | 元 |
| close | decimal | 收盘价 | 元 |
| high | decimal | 最高价 | 元 |
| low | decimal | 最低价 | 元 |
| volume | bigint | 成交量 | 股 |
| amount | decimal | **成交额** (非总市值) | 元 |
| amplitude | decimal | 振幅 | % |
| pct_chg | decimal | 涨跌幅 | % |
| change | decimal | 涨跌额 | 元 |
| turnover | decimal | 换手率 | % |
| total_mv | decimal(16,2) | **总市值** (2026-05-14新增) | 亿元 |
| source | varchar | 来源: tushare/akshare/xueqiu | — |

## 常见混淆

- `amount` = 成交额 (volume × avg_price)，**不是总市值**
- 平安银行 2026-05-11: close=11.25, amount=11.58亿(成交额), total_mv≈2183亿
- 总市值 = close × totalShares / 1e8

## total_mv 计算与回填

- 新增于 2026-05-14
- 计算方式: `total_mv = ROUND(close * totalShares / 100000000, 2)`
- totalShares 来源: stock-sdk `get_all_a_share_quotes` → 提取 `totalShares` 字段
- totalShares 快照: `/home/pebynn/quant/data/total_shares.json`（5514只股票）
- 回填脚本: `/home/pebynn/quant/scripts/backfill_total_mv.py`
- 2024-01-01 起约 295万行

## 数据规模

- 总行数: ~710万
- 代码数: 5,507
- 时间跨度: 2020-01-01 ~ now
- 2026年至今: ~44万行，各83个交易日

## 写入来源

- daily_kline_update.py (cron `afff56398abe`, 工作日15:30)
  - tushare pro.daily() → 雪球 → AKShare 三级回退
  - 自动写入 total_mv（v2.2+）
  - totalShares 文件路径: `data/total_shares.json`

## MySQL 约束

- UPDATE + JOIN 不支持 LIMIT
- 批量更新需逐代码循环（见 backfill_total_mv.py）
