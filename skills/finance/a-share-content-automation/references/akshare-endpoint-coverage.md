# AKShare 端点实测数据覆盖范围

## 实测日期：2026-05-05 | AKShare 版本：1.4.92+

## 端点 ≠ 无限历史

多个名称含 "hist" 的端点实际只覆盖特定历史窗口，不可用于当前（2026年）回填。

### 已验证端点覆盖

| 端点 | 实测日期范围 | 是否可用于2026 | 结论 |
|------|------------|-------------|------|
| `stock_board_industry_hist_em(symbol)` | 2021-12 ~ 2022-04 | ❌ | 仅82行，不可用 |
| `stock_board_concept_hist_em(symbol)` | 2022-01 ~ 2022-11 | ❌ | 不可用 |
| `stock_board_industry_index_ths(symbol)` | 2020-01 ~ 2024-01 | ❌ | 975行，不可用 |
| `stock_board_concept_index_ths(symbol)` | 2020-01 ~ 2025-02 | ❌ | 1248行，不可用 |
| `stock_zh_index_daily_em(symbol)` | 1990 ~ 当前 | ✅ | 全历史可用 |
| `stock_board_industry_name_em()` | 当日实时 | ✅ | 当日采集可用（无历史） |
| `stock_board_concept_name_em()` | 当日实时 | ✅ | 同上 |
| `stock_market_fund_flow()` | 当日实时 | ✅ | 仅当日（无date参数） |
| `stock_sector_fund_flow_rank()` | 当日实时 | ✅ | 仅当日（无date参数） |
| `stock_zt_pool_em(date=)` | 按日期 | ✅ | 支持date参数 |
| `stock_zt_pool_dtgc_em(date=)` | 按日期 | ✅ | 支持date参数 |

### 正确架构

**板块数据**：不要在周总结时重新拉取历史。当日15:30定时采集 → JSON存盘 → 周总结从存盘读取。

```
交易日15:30: collect_data.py --date 2026-05-05
  → stock_board_industry_name_em() 返回当日实时数据 ✅
  → 存入 ~/writing-data/raw/2026-05-05/all_data.json

周末: weekly_summary.py
  → scan_available_data() 读取各日 all_data.json
  → 数据在采集当日就已准确 ✅
```

**不可回填**：如果某交易日未采集，板块数据无法回填。需要Tushare Pro `dc_index_daily` 作为备用。

### 资金流向本质

资金流向不是交易所官方数据，是第三方基于逐笔成交的L1分类估算：
- 超大单 ≥ 500万 | 大单 100-499万 | 中单 20-99万 | 小单 < 20万
- 东方财富、同花顺、Wind算法相近但结果有差异
- **没有任何数据源能声称资金流向100%准确**

### 已验证可用的端点（A级准确性）

| 端点 | 用途 | 日期支持 |
|------|------|---------|
| `stock_zh_index_daily_em(symbol)` | 大盘指数日K线 | full history, filterable |
| `stock_board_industry_name_em()` | 行业板块当日排名 | 当日 |
| `stock_board_concept_name_em()` | 概念板块当日排名 | 当日 |
| `stock_zt_pool_em(date=YYYYMMDD)` | 涨停股 | date参数 ✅ |
| `stock_zt_pool_dtgc_em(date=YYYYMMDD)` | 跌停股 | date参数 ✅ |

### Tushare Pro 替代方案（有偿）

| 需求 | 接口 | 积分 |
|------|------|------|
| 板块历史日K线 | `dc_index_daily` | 2000 |
| 大盘资金流历史 | `moneyflow_mkt_dc` | 6000 |
| 板块资金流历史 | `moneyflow_dc` | 2000 |
