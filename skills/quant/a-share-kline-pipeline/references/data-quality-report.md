# 数据质量日报 — 6 维度检查框架

## 脚本

`~/quant/data_quality_report.py` — 依赖 `data_common.py` + MySQL `stock_kline.kline` 表 + `cross_check` 日志。

## CLI

```
python3 data_quality_report.py                    # 检查今天
python3 data_quality_report.py --date 2026-05-06  # 指定日期
python3 data_quality_report.py --days 30          # 覆盖率窗口30个交易日
python3 data_quality_report.py --no-terminal      # 仅写文件，不打印终端
python3 data_quality_report.py --no-json --no-md  # 仅终端
```

输出文件：
- `~/quant/logs/quality_report_{YYYYMMDD}.json`
- `~/quant/logs/quality_report_{YYYYMMDD}.md`

退出码: 0=OK, 1=WARN, 2=ERROR。

## 6 维度

| # | 维度 | 检查内容 | 数据源 | 状态判定 |
|---|------|----------|--------|----------|
| 1 | K线覆盖率 | 最近 N 个交易日，有 K 线数据的股票数 / 总股票数 | MySQL `kline` + `data_common.get_stock_list()` | OK≥95% / WARN≤2天不达标 / ERROR>2天 |
| 2 | NaN 率 | 最近一日各列 NULL 值占比（核心列 OHLC 严格，非核心列放宽） | MySQL `kline` | OK(核心列0%) / WARN(<1%) / ERROR(≥1%) |
| 3 | 异常值率 | 涨跌幅超限行占比（主板>±10%，科创/创业板>±20%） | MySQL `kline` | OK(0行) / WARN(<0.5%) / ERROR(≥0.5%) |
| 4 | 数据延迟 | MAX(trade_date) vs 期望日期 | MySQL `kline` | OK(0天) / WARN(1-3天) / ERROR(>3天) |
| 5 | 数据源分布 | 按 source 列分组统计占比 | MySQL `kline.source` | OK / WARN |
| 6 | 交叉验证状态 | 最近一次 cross_check 日志的匹配率 | `~/quant/logs/cross_check_*.log` | OK(≤1% mismatch) / WARN(≤5%) / ERROR(>5%) |

## 容错设计

- MySQL 不可用 → 相关维度标记 `UNKNOWN`，不阻断其他维度
- 无 cross_check 日志 → 维度6标记 `N/A`
- 每个维度独立 try/except，单维度失败不影响整体报告
- SQLAlchemy 错误信息自动截断（去掉冗长的 Background on this error URL）

## MySQL 连接

脚本复用 `daily_kline_update.py` 的连接模式：
- SQLAlchemy `create_engine("mysql+pymysql://stock:<pass>@127.0.0.1:3306/stock_kline", pool_pre_ping=True, pool_recycle=3600)`
- 密码可通过 `~/.finquant/` 或 `~/.hermes/config.yaml` 中的 MCP MySQL server 配置获取

## 与现有质量体系的关系

| 工具 | 定位 | 触发方式 |
|------|------|----------|
| `validate_kline.py` | 写入前逐行校验（涨跌幅/OHLC/成交额/价格跳变） | 导入脚本调用 |
| `cross_check.py` | 多源交叉验证（Tushare vs AKShare vs 雪球） | cron 按时间窗口执行 |
| `verify_write()` in `data_common.py` | 写入后端到端验证（行数/日期/抽样） | 导入脚本调用 |
| **`data_quality_report.py`** | **运行时全景监控（6维度日报）** | **cron / 手动** |

建议 cron: 每个交易日 16:30 执行，在 daily_kline_update 完成后。
