# AKShare API 陷阱与修复

## 1. 北向资金数据停更 → 主力资金替代

- **问题**: `ak.stock_hsgt_hist_em(symbol="北向资金")` 列 `当日成交净买额` 在 2024-08-16 后全部为 NaN
- **解决**: 切换为 `ak.stock_market_fund_flow()`，字段 `主力净流入-净额`（单位：元，需 /1e8 转到亿）

## ⚠️ 核心陷阱：hist ≠ 全历史（2026-05-05 实测）

多个名称含 `hist` / `index_ths` 的端点**只覆盖特定历史窗口**，不可用于当前数据回填：

| 端点 | 实测覆盖 | 2026可用 |
|------|---------|---------|
| `stock_board_industry_hist_em(symbol)` | 2021-12 ~ 2022-04 | ❌ |
| `stock_board_concept_hist_em(symbol)` | 2022-01 ~ 2022-11 | ❌ |
| `stock_board_industry_index_ths(symbol)` | 2020-01 ~ 2024-01 | ❌ |
| `stock_board_concept_index_ths(symbol)` | 2020-01 ~ 2025-02 | ❌ |

**正确的板块数据架构**：当日15:30 `stock_board_industry_name_em()` 实时采集 → JSON存盘 → 周总结读盘。
不可假设 `_hist_` 端点能回填历史，详见 `references/akshare-endpoint-coverage.md`。

### 主力资金数据结构
```
列: 日期, 上证-收盘价, 深证-收盘价, 主力净流入-净额, 主力净流入-净占比,
    超大单净流入-净额, 超大单净流入-净占比, 大单净流入-净额, 大单净流入-净占比
```
- `主力净流入-净额` 为每日值（元），除以 1e8 得到"亿"
- 示例: -52028570000 → -520.29亿

## 2. 涨跌停日期格式

- `ak.stock_zt_pool_em(date=)` 和 `ak.stock_zt_pool_dtgc_em(date=)` 需要 `YYYYMMDD` 格式
- ❌ `date="2026-05-05"` → 返回空
- ✅ `date="20260505"` → 正确
- 转换: `date_str.replace("-", "")`

## 3. 涨跌停需过滤非标准股票

见 `references/limit-stock-filtering.md`

## 4. 大盘指数数据源选择

- `stock_zh_index_daily` — 无 `amount` 列（成交额为 0）
- `stock_zh_index_daily_em` — 有 `amount` 列 ✅

## 5. 涨跌幅计算公式

❌ `(close - open) / open * 100` — 错误（用开盘价而非昨收）
✅ `(close - prev_close) / prev_close * 100` — 需取 iloc[-2] 的收盘价

## 7. 板块历史涨跌幅 — 无可靠历史端点

**问题**：`stock_board_industry_name_em()` 始终返回最新板块排行，不支持 date 参数。

**误区**：`stock_board_industry_hist_em()` 看似支持全历史，实测数据范围仅 2021-12 ~ 2022-04（见核心陷阱表）。不可用。

**正确方案**：
- 当日采集：`stock_board_industry_name_em()` — 15:30 cron 准时运行，当日数据绝对准确
- 周总结聚合：从 `~/writing-data/raw/YYYY-MM-DD/all_data.json` 读取存盘数据
- 不可回填历史：如果某日未采集，无法补采板块数据

**每周 cron 兜底**：`weekly_summary.py` 已内置自动采集逻辑——当日数据缺失时自动调 `collect_data.py` 补采。

## 8. Tushare Pro 数据源参考（如需历史资金流向）

### 大盘资金流向历史
```python
import tushare as ts
pro = ts.pro_api('your_token')
# moneyflow_mkt_dc — 东方财富大盘资金流向
df = pro.moneyflow_mkt_dc(trade_date='20260505')
# 字段: trade_date, close_sh, close_sz, net_amount, net_amount_rate, buy_elg_amount, ...
```

### 板块资金流向历史
```python
# moneyflow_dc — 东方财富板块资金流向
df = pro.moneyflow_dc(trade_date='20260505')
# 字段: trade_date, ts_code, name, pct_change, net_amount, net_amount_rate, ...
```

### 板块指数日线
```python
# dc_index_daily — 板块指数日线行情
df = pro.dc_index_daily(ts_code='885748.TI', start_date='20260428', end_date='20260505')
```

## 9. 凌晨/夜间 API 不可用 — 东方财富后端维护窗口

**问题**：以下三个端点在北京时间 00:00-06:00 期间几乎100%超时或断连：

- `ak.stock_market_fund_flow()` — 主力资金
- `ak.stock_board_industry_name_em()` — 行业板块
- `ak.stock_zt_pool_em()` / `ak.stock_zt_pool_dtgc_em()` — 涨跌停

而 `ak.stock_zh_index_daily_em()` 同样走东方财富后端但在凌晨仍可用（K线数据有缓存）。

**症状**：
- `stock_market_fund_flow()` → 无报错但永久阻塞，需 `timeout 30` 强制终止
- `stock_board_industry_name_em()` → `RemoteDisconnected('Remote end closed connection without response')`
- `stock_zt_pool_em()` → 同永久阻塞

**影响**：凌晨手动调 `collect_data.py` 或 `generate_charts.py` 会卡死。数据采集 cron 设计在 15:30 运行，此时 API 正常。

**调试建议**：凌晨排查仅限代码逻辑/字体/离线图表（sector_heatmap 读本地 JSON，不调 API）。需调 API 时等待市场时段 09:00-17:00。
