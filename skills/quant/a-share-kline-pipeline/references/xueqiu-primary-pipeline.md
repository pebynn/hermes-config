# 雪球主数据源管线 (2026-05-08)

## 背景

当前环境（Ubuntu/中国网络）中 AKShare 所有接口均不可用（超时），但雪球 API 和东方财富 push2 API 可用。

## 方案

使用 `precache_xueqiu.py`（`~/quant/`）绕过 AKShare，用雪球作为唯一 K 线数据源。

### 依赖链
- 股票列表：tushare `pro.stock_basic()`（token: `~/.finquant/tushare_token`）
- K线数据：`xueqiu_kline.XueqiuSource.get_kline()`（cookies: `~/.hermes/credentials/xueqiu_cookies.json`）
- 输出：parquet (`~/.finquant/cache/kline/{code}.parquet`) + CSV (`~/stock_kline_2020/{code}.csv`)

### 脚本位置
`~/quant/precache_xueqiu.py`（4605字节，独立脚本，不依赖AKShare）

### 技术要点

**雪球 API 性能**
- `get_kline('SH600519', count=-2000)` → 2000条bars, ~0.6s
- 覆盖日期范围：从2018年2月至今（满足2020-01起需求）
- 20线程全量：~9只/s，4939只约9-10min

**数据字段映射**
| 雪球字段 | parquet列 | 说明 |
|:---------|:---------|:-----|
| date | 日期 | YYYY-MM-DD |
| open/high/low/close | 开盘/最高/最低/收盘 | float |
| volume | 成交量 | int64, 股 |
| change_pct | 涨跌幅 | float, % |
| change | 涨跌额 | float |
| amplitude | 振幅 | float, % |
| turnover | 换手率 | float |
| close×volume | 成交额 | float, 元（估算值） |
| — | source | 'xueqiu' |

**缺失数据**
- 成交额（amount）用 `close × volume` 估算，非真实值
- 振幅/涨跌幅/换手率直接从雪球API获取（无需自行计算）

### 已知坑

1. **雪球要求 cookies**：`~/.hermes/credentials/xueqiu_cookies.json` 需有效（~30天过期）
2. **首次拉取前必须配置**：tushare token（股票列表）+ xueqiu cookies（K线数据），缺一不可
3. **MySQL 密码**：已从 `***`（access denied）改为 `stock123`，所有脚本已同步
4. **Python 环境**：必须用 `~/tools/quant_env/bin/python3`（含 pyarrow/pymysql/pandas）
5. **增量更新**：首次全量后，每日16:00由 `daily_kline_update.py` cron（tushare bulk路径）负责增量
