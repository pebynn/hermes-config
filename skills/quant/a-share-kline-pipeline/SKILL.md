---
allowed-tools:
- terminal
- file
- cronjob
arguments:
- default: daily
  description: backfill(历史批量) | daily(当日增量) | mysql(导入数据库)
  name: action
- default: all
  description: 股票池 (all/main/gem/star)
  name: market
- default: 10
  description: 并发线程数
  name: workers
- default: false
  description: 强制刷新（忽略已有缓存）
  name: force
author: unknown
description: A股日K线数据管线 — 历史批量拉取 + 每日增量更新(cron) + MySQL主读 + Parquet/CSV双写回退。四数据源(AKShare+Tushare+雪球)统一数据层，支持全A股（主板/创业板/科创板）。
name: a-share-kline-pipeline
related_skills:
- finance-domain
- mid-cap-multi-factor
version: 2.9.0
when-to-use: '用户说"拉取A股K线数据"、"下载日线数据"、"更新股票数据"、

  "历史K线批量下载"、"从2020年开始拉K线"、"把K线存到数据库"、

  "K线数据缺失"、"回测没数据"、"缓存补数据"、

  "拉创业板K线"、"科创板数据缓存"

  也适用于任何存量数据管线搭建场景：历史全量 + 每日增量 + 多格式输出。'
---
# A股日K线数据管线 v2.1 — DB优先架构

## 概述

搭建自动化日K线数据收集管线：MySQL为策略脚本主读源，parquet/CSV为离线回退和增量写入层。

**v2.2 架构变更：** 2026-04-30 验证 MySQL(localhost:3306) 连接被拒绝。策略脚本优先级链改为：**cache优先 → MySQL兜底(跳过拒绝) → API最终兜底**。详见 `references/kline-cache-architecture.md`。

所有脚本位于 `~/quant/`，使用 `~/tools/quant_env/bin/python3`（含 pyarrow、pymysql、sqlalchemy）。

**v2.0 核心改进：**
- 统一数据层 `data_common.py`（替换各脚本内重复的 `get_stock_list()`）
- 全A股支持（主板+创业板+科创板，4966只）
- `--market` 参数可选 all / main / gem / star
- Tushare 申万110行业分类作为行业数据源

## 股票范围

默认 `--market=all` 通过 tushare/akshare 获取 ~4966 只（排除ST/退市/北交所）。
**使用 stock-sdk `getAShareCodeList({simple: true})` 可获得 5512 只全量（含北交所312只、ST、全部活跃股），无过滤。**

| 参数 | 覆盖 | 数量 |
|:----|:-----|:-----|
| `--market=all` | 主板+创业板+科创板（排除ST/退市/北交所） | ~4966只 |
| `--market=main` | 仅主板 | ~3017只 |
| `--market=gem` | 仅创业板 | ~1350只 |
| `--market=star` | 仅科创板 | ~599只 |
| stock-sdk 全量 | 沪深北全部活跃A股（含ST/北交所） | **5512只** |

## ⚠️ AKShare 环境不可用 (2026-05-08 验证)

**当前环境（Ubuntu/中国网络）中 AKShare 所有接口均不可用：**
- `stock_zh_a_daily` → 超时 (exit_code=124)
- `stock_zh_a_hist_tx` → 超时
- `stock_zh_a_hist` → 超时
- `stock_info_a_code_name` → 超时
- 东方财富 `stock_zh_a_spot_em` → 超时

**可用数据源：**
- ✅ **Tushare** — pro.daily() 批量拉取K线（需要 token），pro.stock_basic() 获取股票列表（含申万行业）
- ✅ **雪球 API** — `xueqiu_kline.XueqiuSource.get_kline()` 24h可用，count=-2000 返回2000条/~0.6s，覆盖~8年
- ✅ **东方财富 push2 API** — 股票列表（已验证可用）
- ✅ **Baostock** — **✅ 2026-05-08 验证通过：完全可用，无需注册！** 覆盖日K(1990至今)、5/15/30/60分K(2020至今)、复权因子、财务数据。详见 `references/data-source-comprehensive-research-2026-05-08.md`
- ✅ **腾讯 qt.gtimg.cn / ifzq.gtimg.cn** — 前复权日K(1023条)、分钟K线稳定公开
- ✅ **百度/东方财富基础网络** — 连通正常

**策略**: 历史全量优先 Baostock (含真实amount/pctChg/isST) → 降级雪球。每日增量 tushare daily → 雪球兜底。AKShare 路径全部跳过。详见 `references/data-source-comprehensive-research-2026-05-08.md`（含完整对比矩阵和Tencent/stock-sdk-mcp/iTick等新数据源）。


详见 `references/xueqiu-primary-pipeline.md`.

## 数据源（四源自动切换，修正优先级）

**注意——不同脚本的数据源差异（2026-04-30 daily_kline_update 已切到 stock_zh_a_daily）：**

| 脚本 | 数据源1 | 原因 | 列 |\n|:----|:-------|:-----|:---|\n| `precache_kline.py` (历史批量) | `stock_zh_a_daily`（腾讯完整版） | 需要成交量/换手率 | 9列含volume/turnover |\n| `daily_kline_update.py` (每日增量) | **tushare `pro.daily()`（v2.1 批量）** | 1次API拉全A股，~0.4s → 总3分钟。三级回退: Tushare→雪球→AKShare | 11列：含真实 pct_chg/change + 自算 amplitude/turnover |\n| 策略脚本（mid_cap_enhanced 等） | `stock_zh_a_hist_tx`（腾讯精简版，仅数据库读取时走MySQL） | 交易信号脚本默认用精简源提效, 但kline_get优先查MySQL | 6列，由管线增量补全后入DB |

**precache_kline.py 四源优先级（AKShare不可用时雪球为主）：**

| 优先级 | 函数 | 来源 | 特点 |
|:------|:-----|:-----|:-----|
| 0 | `bs.query_history_k_data_plus()` | **Baostock** | 含真实 amount/pctChg/isST/复权因子，1990-12-19全历史。间歇性超时 |
| 1 | `stock_zh_a_daily` | 腾讯 | 含 volume/amount/turnover/outstanding_share，需sz/sh前缀 |
| 2 | `stock_zh_a_hist_tx` | 腾讯 | 仅6列(date/open/close/high/low/amount)，无成交量/换手率 |
| 3 | `stock_zh_a_hist` | 东方财富 | 完整11列，凌晨可能不可用 |
| 4 | `get_stock_kline()` via `kline_fallback` | 雪球 | 24h可用，count=-2500 拉取后过滤日期范围。不含成交额（用 close×volume 估算），标记 source='xueqiu' |

自动切换逻辑在 `precache_kline.py` 的 `_fetch_kline()` 函数中。Baostock 优先级设为 0（最优先）以避免雪球的 amount 估算问题，但需处理间歇性超时降级。

**2026-05-08 新增 Baostock (实测)**: v0.9.1 已安装在 quant_env。实测结果：
- ✅ 登录: 1s内成功
- ✅ 单只日K线: 贵州茅台7行含真实amount/pctChg/isST
- ❌ query_all_stock: 60s超时
- ❌ query_stock_industry: 20s超时
- ❌ 5分钟K线: 60s超时
- ❌ 上证指数K线: 15s超时

结论：Baostock **单只K线查询可用但间歇性超时**，不适合做主数据源/批量任务。可用于单只补数据场景。详见 `references/data-source-comprehensive-research-2026-05-08.md`。

**2026-05-08 新增 stock-sdk-mcp (腾讯数据源, 强烈推荐)**: 
- 基于腾讯 qt.gtimg.cn 数据源的 Node.js MCP Server
- 实测: 日K线5914行(23年), 5分钟K线1205行, 行业板块K线6379行, 批量20只行情327ms
- 50+ MCP工具已注册: 实时行情/历史K线/分钟K线/行业板块K线/涨停池/龙虎榜/资金流/北向资金/条件选股等
- 已全局安装: `/home/pebynn/.hermes/node/bin/stock-mcp`
- **填补了现有管线缺失的能力**: 分钟K线、行业板块K线+成分股、资金流历史、涨停/龙虎榜、实时行情批量查询
详见 `references/stock-sdk-mcp-integration.md` 和 `references/data-source-comprehensive-research-2026-05-08.md`。

### stock-sdk 批量回填 MySQL (2026-05-08 新增)

当 MySQL `kline` 表中 `pct_chg`/`change`/`turnover`/`amplitude` 为 NULL 时，用 stock-sdk SDK 直调方式批量修复：

**脚本**: `scripts/stock_sdk_backfill.js` — Node.js 12路并发 + MySQL COALESCE UPSERT

```bash
NODE_PATH=/home/pebynn/.hermes/node/lib/node_modules \
  node ~/.hermes/skills/quant/a-share-kline-pipeline/scripts/stock_sdk_backfill.js --start=20200101
```

**关键设计：**
- COALESCE 模式：默认只更新目标列为 NULL 的行，已有值不受影响
- volume 转换：stock-sdk 返回"手"，MySQL 存"股"（×100）
- 全量 5512 只含北交所/ST，无板块过滤
- 进度日志写入 `/tmp/stock_sdk_backfill_progress.txt`

详见 `references/stock-sdk-bulk-backfill.md`（含完整列映射、性能基准、坑点清单）。

## 统一数据层（data_common.py）

`~/quant/data_common.py` 提供9个函数，所有管线脚本和策略脚本统一调用：

| 函数 | 说明 |
|:-----|:-----|
| `get_stock_list(market='all')` | 股票列表（tushare→akshare，4966只全A） |
| `refresh_stock_list(force=False)` | 强制刷新缓存 |
| `get_industry_map()` | 申万110行业映射 `{code: industry}`（tushare源） |
| `filter_by_market_cap(df, min_cap, max_cap)` | 市值过滤 |
| `load_share_db(force_reload=False)` | 总股本数据库 |
| `cache_get(code, cache_dir)` | 读单只股票数据 — K线(**KLINE_DIR**)优先查MySQL→回退parquet，其他目录只读parquet |
| `cache_set(df, code, cache_dir)` | 写单只股票parquet缓存 |
| `kline_from_db(code, start_date, end_date)` | 直接查MySQL stock_kline.kline表，返回英文列名DataFrame |
| `verify_write(date_str, expected_count)` | 端到端写入验证：MySQL vs Parquet vs 股票池三向对比，不阻断流程 |
| `get_db_engine()` | 延时初始化SQLAlchemy引擎（pool_pre_ping + pool_recycle） |
| `get_market_label(code)` | 返回 '主板'/'创业板'/'科创板' |
| `get_index_daily(name, start, end)` | 🆕 指数日K线（东方财富），供writing域采集大盘指数 |
| `get_sector_flow(date)` | 🆕 行业板块资金流向排名，供writing域采集板块资金流 |
| `get_limit_up_pool(date)` | 🆕 涨停池+跌停池数据，供writing域采集涨跌停 |
| `get_trading_calendar()` | 🆕 A股交易日历（Sina），供writing域过滤节假日 |

缓存：`~/.finquant/cache/stocks/stock_list.parquet`，7天过期。

## 管线结构

### 数据流向

```
采集层:
  precache_kline.py ──→ ~/.finquant/cache/kline/{code}.parquet
  daily_kline_update.py ──→ ~/.finquant/cache/kline/{code}.parquet + ~/stock_kline_2020/{code}.csv

策略脚本读K线优先级链:
  [2026-04-30 更新] cache优先 → MySQL兜底(已断开) → API最终兜底

  mid_cap_enhanced.kline_get(code):
    1. _cache_get('k_{code}.parquet')     -- 策略历史缓存 (get_kline_cached 写入, 英文列名)
    2. _cache_get('{code}.parquet')       -- daily更新管线缓存 (中文列名→自动映射英文)
    3. kline_from_db(code=code)           -- MySQL stock_kline.kline (连接断开时~0.1s失败)
    4. get_kline_cached() → API兜底       -- 拉取+缓存到 k_{code}.parquet

  chan_theory_signals 等: 继承 mid_cap_enhanced.kline_get

### 脚本清单

| 脚本 | 功能 | 命令 |
|:-----|:-----|:-----|
| `~/quant/precache_kline.py` | 历史批量全量拉取(2020-01起) | `--workers 10` / `--force` / `--limit N` / `--market all` |
| `~/quant/precache_xueqiu.py` | 🆕 **雪球全量拉取（AKShare不可用时主方案）** | `--workers 20` (4939只~10min) / `--limit N` |
| `~/quant/precache_kline.py` | 历史批量全量拉取(2020-01起，仅AKShare可用时) | `--workers 10` / `--force` / `--limit N` / `--market all` |
| `~/quant/precache_financial.py` | 财务数据批量拉取（AKShare不可用时卡死） | `--workers 10` / `--force` / `--market all` |
| `~/quant/precache_fund_flow_financial.py` | 🆕 **资金流+财务一次性补拉（东方财富API，不依赖AKShare）** | 自动分页+20线程并发 |
| `~/quant/daily_kline_update.py` | 每日增量更新（配合cron） | 交易日16:00自动执行 |
| `~/quant/convert_kline_to_csv.py` | parquet → CSV(UTF-8 BOM) 批量转换 | 一次性转换所有 |
| `~/quant/import_kline_to_mysql.py` | CSV → MySQL 批量导入（含中文→英文列映射，pandas to_sql，慢——备选） | 需要 pymysql + sqlalchemy |
| `~/quant/bulk_import_to_mysql.py` | CSV → MySQL 全量导入（LOAD DATA LOCAL INFILE，快，主方案） | 需要 pymysql; ~5min完成5052文件 |
| `~/quant/normalize_kline_cache.py` | K线缓存文件名规范化（k_/k_sz/k_sh前缀→6位代码） | 一次性修复脚本 |
| `~/quant/tushare_data_pipeline.py` | Tushare数据专用管线 | init / stock-basic / daily / new-share / status |
| `~/quant/data_quality_report.py` | 6维度数据质量日报 | `--date YYYY-MM-DD` / `--days N` (终端+JSON+Markdown), 详见 `references/data-quality-report.md` |
| `~/quant/data_bridge.py` | 🆕 量化→写作数据桥 | 只读接口: get_daily_signals / get_top_stocks / get_market_summary. MySQL(主)→JSON(/tmp/midcap_signal.json)→fallback |
| `scripts/stock_sdk_backfill.js` | 🆕 **stock-sdk 全量回填MySQL** (Node.js) | `NODE_PATH=... node scripts/stock_sdk_backfill.js --start=20200101` |
| `scripts/parquet_patch_mysql.py` | 🆕 **parquet→MySQL pct_chg补丁** (Python/LOAD DATA) | `~/tools/quant_env/bin/python3 scripts/parquet_patch_mysql.py` |

### 缓存目录

```
~/.finquant/cache/
├── kline/           # K线 parquet (per-stock, {code}.parquet)
├── financial/       # 财务数据 parquet (per-stock)
├── shares/          # 总股本数据库 (share_db.parquet)
├── stocks/          # 股票列表 (stock_list.parquet)
└── tushare/         # tushare 专用缓存
    ├── kline/       # tushare daily K线
    └── stock_basic.parquet  # A股5512只+申万行业
```

### K线缓存文件名规范化

**2026-04-30 旧缓存文件名修复：** 旧版 precache_kline.py 写入 `k_{code}.parquet`（k_前缀）格式，与新版 data_common 的 `{code}.parquet`（无前缀）格式不一致。一次性修复脚本：

```bash
~/tools/quant_env/bin/python3 ~/quant/normalize_kline_cache.py
```

修复内容：
- 删除旧版中文列 parquet（无k_前缀的纯数字文件，对应中文列名格式）
- 重命名 `k_{code}.parquet` → `{code}.parquet`
- 重命名 `k_sz{code}.parquet` / `k_sh{code}.parquet` → `{code}.parquet`
- 同名冲突时保留更新的文件

规范化后所有缓存文件名统一为 `{6位代码}.parquet`。

### 列说明

| 列 | 类型 | 说明 |
|:---|:-----|:-----|
| trade_date | date | 交易日期 |
| open/close/high/low | decimal(12,2) | 开盘/收盘/最高/最低（前复权） |
| volume | bigint | 成交量（股） |
| amount | decimal(16,2) | 成交额（元） |
| amplitude | decimal(8,2) | 振幅% |
| pct_chg | decimal(8,2) | 涨跌幅% |
| change | decimal(8,2) | 涨跌额（注意是MySQL保留字，需用反引号） |
| turnover | decimal(12,10) | 换手率 |
| source | varchar(16) | 数据来源标记 (v2.5+): tushare / akshare / xueqiu / NULL(历史数据) |

### 参考文档

| 文件 | 内容 |
|:----|:-----|
| `references/data-source-comprehensive-research-2026-05-08.md` | 全量数据源深度调研：Baostock/Tencent/stock-sdk-mcp/iTick对比矩阵 + 双域评估 + 管线演进建议 |
| `references/stock-sdk-mcp-integration.md` | stock-sdk MCP Server 安装、50+ 工具清单、实测结果 |
| `references/stock-sdk-bulk-backfill.md` | **stock-sdk 批量回填 MySQL 技术手册** — 列映射/volume转换/UPSERT模式/坑点/性能基准 |
| `references/data-source-priority-fix.md` | 三数据源自动切换的修复记录 |
| `references/data-source-priority-fix.md` | 三数据源自动切换的修复记录 |
| `references/backtest-debugging-patterns.md` | 回测常见bug模式：NAV为1.0/行业评分统一/K线缓存文件名/中文列名/行业映射/未来数据泄露/OOM |
| `references/api-limitations-verified-2026-05.md` | AKShare API 限制验证（主力资金流/北向个股/市场级API可靠性/策略回测避坑） |
| `references/mysql-bulk-import.md` | 全量MySQL导入方案对比（LOAD DATA INFILE vs pandas to_sql）、redo log容量问题、崩溃恢复 |
| `references/mysql-crash-recovery.md` | MySQL 崩溃恢复、metadata lock 排障、绕过方案、daily_kline_update 密码修复 |
| `references/trading-day-check-pattern.md` | 交易日判断可复用模式 — is_trading_day() + AKShare 新浪日历缓存，适用于所有需要节假日跳过的数据拉取 cron |
| `references/data-quality-audit-2026-05-07.md` | 数据准确性审计报告 — NaN→0污染/P0-P2修复清单/雪球集成插入点/交叉验证缺口 |
| `references/end-to-end-write-verification.md` | P1-3 端到端写入验证实现 — verify_write() 函数设计/验证规则/调用点/日志格式 |
| `references/mysql-source-lineage.md` | 数据血统追踪 — source 列设计/COALESCE UPSERT 安全模式/三源标注/回填透传/元数据列添加检查清单 |
| `references/data-quality-report.md` | data_quality_report.py 使用指南 — 6维度检查框架/CLI/容错/与现有质量体系关系 |
| `references/fallback-resolver-and-data-bridge.md` | 🆕 晚间感知三源回退(flallback_resolver.py) + 量化→写作数据桥(data_bridge.py) |
| `references/akshare-unavailable-2026-05-08.md` | 🆕 AKShare环境不可用诊断报告 + 可用替代源 + 验证脚本 |
| `references/em-fund-flow-financial-pipeline.md` | 🆕 东方财富资金流 + 财务数据缓存管线（字段映射/已知问题/分页限制） |

## 数据质量保障 (2026-05-07 审计，当日修复)

**当前状态：P0 三项全部修复，validate_kline.py + xueqiu fallback 已上线。**

### 数据质量日报 (data_quality_report.py)

`~/quant/data_quality_report.py` 提供每日 6 维度自动化质量检查，适合 cron 定时执行。结果输出终端彩色报告 + JSON + Markdown 三格式。维度包括：K线覆盖率、NaN率、异常值率、数据延迟、数据源分布、交叉验证状态。详见 `references/data-quality-report.md`。

### 关键风险（已修复）

| 风险 | 严重度 | 位置 | 状态 |
|:-----|:------|:-----|:-----|
| NaN→0 静默转换造成数据污染 | 🔴 P0 | backfill_today_mysql.py L49-57 | ✅ **已修复** — 保留NaN→MySQL NULL，加 `_check_nan_and_warn()` |
| 所有导入脚本缺少 pre-write validation (涨跌幅/OHLC/成交额) | 🔴 P0 | 全局 | ✅ **已修复** — 新建 `validate_kline.py` (30项单测全过) |
| Tushare成功时不做AKShare交叉验证 | 🟡 P1 | daily_kline_update.py L466 | 待实现 cross_check() |
| AKShare push2 晚间(19:00-08:00)不可用，无雪球回退 | 🔴 P0 | daily_kline_update.py L362, L498 | ✅ **已修复** — v2.1 三级回退: Tushare→雪球→AKShare |
| 北向资金晚间不可用 | 🟡 P1 | signal_engine.py L1100 | ✅ **已修复** — v2.1 雪球指数快照推断 (校准~50亿/1%平均涨跌)，三态回退: AKShare→雪球→默认1.0 |
| 写入后端到端验证缺失(行数/日期/抽样) | 🟢 P1 ✅ | backfill_today_mysql.py, daily_kline_update.py | ✅ 已实现 — verify_write() in data_common.py，详见 references/end-to-end-write-verification.md |

### 数据导入写入前必检清单（validate_kline.py 设计规格）

任何写 MySQL/Parquet 的数据导入脚本，写入前必须通过以下检查：

1. **涨跌幅范围**: 主板 ±10%, GEM/STAR ±20%, 超过则告警
2. **OHLC 关系**: open ≤ high, low ≤ close, low ≤ high
3. **成交额一致性**: volume > 0 时 amount 不应为 0
4. **停牌检测**: volume = 0 且 amount = 0 → 停牌(正常), volume = 0 但 amount > 0 → 异常
5. **价格跳变**: |close - prev_close| / prev_close > 30% → 异常(除复权日)
6. **列完整性**: 必选列(日期/开盘/收盘/最高/最低/成交量/成交额)不可全 NaN

### 雪球集成（晚间回退 + 交叉验证）

共享模块：`~/quant/xueqiu_kline.py` (XueqiuSource) + `~/quant/kline_fallback.py` (wrapper)

| 插入点 | 优先级 | 价值 | 状态 |
|:-------|:------|:-----|:-----|
| precache_kline.py 腾讯→腾讯hist_tx→东财→雪球 四源回退 | P2 | 夜间/凌晨可用, 覆盖东财不可用时段 | ✅ **已完成 (2026-05-07)** |
| daily_kline_update.py Tushare→雪球→AKShare 三级回退 | P0 | 夜间可用 | ✅ **已完成 (v2.1)** |
| daily_kline_update.py 写入前雪球 100 只抽样对比差异化 >1% 告警 | P1 | 首次 cross-source validation | 待实现 |
| signal_engine.py 北向资金雪球 fallback | P1 | 夜间可用 | ✅ **已完成 (2026-05-07)** — 三态回退: AKShare→雪球指数快照→默认1.0 |
| backfill_today_mysql.py 导入前雪球 20 只抽样验证 | P2 | 防 MySQL 污染 | 待实现 |

## 数据血统追踪 (v2.5+, 2026-05-07)

`stock_kline.kline` 表新增 `source VARCHAR(16)` 列，三个数据源写入时自动标注来源：

| 数据路径 | source 值 | 写入点 |
|:--------|:---------|:------|
| tushare `pro.daily()` 批量 | `'tushare'` | `_insert_to_db(df, code, source='tushare')` |
| AKShare `stock_zh_a_daily` 逐只 | `'akshare'` | `_insert_to_db(df, code, source='akshare')` |
| 雪球 `get_stock_kline()` 逐只 | `'xueqiu'` | `_insert_to_db(df, code, source='xueqiu')` / `precache_kline.py` `_fetch_kline()` parquet `source` 列 |
| 历史数据 (2026-05-07 前) | `NULL` | 默认值 |

**UPDATE UPSERT 安全设计**: `_insert_to_db` 的 UPDATE 子句使用 `source=COALESCE(:src, source)` — 当调用者传入 `source=None`（如旧脚本/未知路径），不会将已有非NULL source 覆盖为 NULL。INSERT 路径直接使用 `:src` 参数。

**backfill_today_mysql.py 透传**: 该脚本通过 `COL_MAP.get(k, k)` 模式（key不在映射表则原样保留）自动将 parquet 的 `source` 列（如有）透传写入 MySQL。脚本末尾有数据源分布摘要查询。旧 parquet 无 source 列时 MySQL 写入 NULL。

## 操作流程

### 1. 首次：历史全量拉取

**优先使用雪球方案（AKShare不可用时唯一可用）：**
```bash
# 全A股（默认），20线程
~/tools/quant_env/bin/python3 ~/quant/precache_xueqiu.py --workers 20
```

性能：~9只/s（20线程），全市场~4939只需~9-10分钟。数据源：tushare股票列表 + 雪球K线（count=-2000，覆盖~8年）。

**备选：AKShare方案（仅AKShare可用时）：**
```bash
~/tools/quant_env/bin/python3 ~/quant/precache_kline.py --workers 10
~/tools/quant_env/bin/python3 ~/quant/precache_kline.py --market=gem --workers 10
~/tools/quant_env/bin/python3 ~/quant/precache_kline.py --market=star --workers 10
```

增量模式：已有缓存则只补缺失日期。

### 2. 财务数据预缓存

```bash
~/tools/quant_env/bin/python3 ~/quant/precache_financial.py --workers 10
```

覆盖同花顺THS财务数据（ROE/营收增速/负债率/EPS）。

### 3. 设置每日增量更新（含DB upsert）

```bash
# 已通过 cronjob 设置: 0 16 * * 1-5
# daily_kline_update.py 已内置 DB upsert: 拉取→parquet→CSV→MySQL 一步完成
```

每日16:00自动拉取当日K线，合并到总缓存 + 同步写入 MySQL。

写入策略（`_insert_to_db`）是 **upsert**：
1. `UPDATE kline SET ... WHERE code=? AND trade_date=?` — 存在则更新
2. `rowcount == 0` → `INSERT INTO kline ...` — 不存在则插入

同一个 `engine.begin()` 事务中完成，原子性保证，无需外部 cron 再跑 import 脚本。

### 4. (可选) 手动导入历史数据到 MySQL

如果某只股票的历史数据未在 DB 中，或想全量同步 parquet→MySQL：

```bash
~/tools/quant_env/bin/python3 ~/quant/import_kline_to_mysql.py
```

## tushare 数据管线

作为 AKShare 的补充数据源，tushare 提供申万行业分类（110个，覆盖5512只A股）。当前可用接口：

| 命令 | 数据 | 所需积分 | 当前状态 |
|:----|:-----|:---------|:---------|
| `python3 tushare_data_pipeline.py stock-basic` | A股列表+行业 | 0 | ✓ 已开通 |
| `python3 tushare_data_pipeline.py daily` | 日线行情 | 0 (免费) | ✓ 已开通，v2.0 daily_kline_update 已集成 |
| `python3 tushare_data_pipeline.py status` | 查看所有接口权限 | — | ✓ |

Token：`~/.finquant/tushare_token`。分配积分：登录 tushare.pro → 个人中心 → 接口TOKEN。

## Backtest Preparation: Pre-cache All Candidate Stocks

Before running a full backtest (64 periods, 4966 stocks), pre-populate the K-line cache for ALL candidate stocks using `get_kline_cached()` with multithreading:

```bash
# Check current cache coverage
ls ~/.finquant/cache/kline/*.parquet | wc -l

# Pre-fetch uncached stocks (uses 20-thread ThreadPoolExecutor)
# Script at: /tmp/prefetch_kline.py
/home/pebynn/tools/quant_env/bin/python3 /tmp/prefetch_kline.py
```

Without pre-caching, the first backtest run will trigger API fallback for each uncached stock (3-10s each), making it ~40 min for 4966 stocks even with 20 threads.

After pre-caching, the industry scoring runs at 2.0-2.2 it/s (per-period speed doubles from API's 1.0-1.2 it/s).

## MySQL回填：parquet→MySQL 批量增补（2026-05-07实战）

当MySQL数据滞后（如假期后数据缺失）而parquet缓存已有数据时，用此流程回填。

**脚本**: `~/quant/backfill_kline.py` — pymysql executemany 批量INSERT IGNORE

```bash
# 回填5月数据
/home/pebynn/tools/quant_env/bin/python3 ~/quant/backfill_kline.py
```

**核心模式**:
1. 遍历 `~/.finquant/cache/kline/*.parquet`
2. 筛选 `日期 >= '2020-01-01'`（全量导入，从2020年开始）
3. pymysql `executemany(sql, batch)` 每500行一批
4. `INSERT IGNORE INTO kline (...) VALUES (...)` 避免主键冲突

**首次运行注意事项**:
- 如果 `~/.finquant/cache/kline/` 为空，先运行 `precache_xueqiu.py` 拉取数据
- 雪球数据不含成交额（amount），用 close×volume 估算
- parquet 写入 source='xueqiu' 标记数据来源

**关键列映射（易错）**:
| Parquet列(中文) | MySQL列 | MySQL类型 | 说明 |
|:----|:----|:----|:----|
| 成交量 | `volume` | bigint | ✅ |
| 成交额 | `amount` | decimal(16,2) | ⚠️ 不是`turnover` |
| — | `turnover` | decimal(12,10) | 换手率(rate)，非成交额 |

**MySQL连接方式**: 
- 密码: `stock123`（2026-05-08 从`***`重置。原密码`***`在MySQL中 access denied，需用 `ALTER USER` 重置）
- MCP MySQL工具：不稳定（connection频繁断开），批量操作用pymysql直连
- 命令行: `mysql -u stock -p'stock123' -h 127.0.0.1 stock_kline`
- 所有脚本密码同步存在 daily_kline_update.py / backfill_kline.py / bulk_import_to_mysql.py 三处
- .env: `MYSQL_STOCK_PASSWORD=stock123`
- **MCP MySQL config**: `~/.hermes/config.yaml` 中 mysql server 用 `$MYSQL_STOCK_PASSWORD` 环境变量引用
- **source列缺失**: MySQL kline 表初始无 `source` 列。`ALTER TABLE kline ADD COLUMN source VARCHAR(16) DEFAULT NULL` 即可
- 所有脚本密码同步存在 daily_kline_update.py / backfill_kline.py / bulk_import_to_mysql.py 三处
- .env: `MYSQL_STOCK_PASSWORD=stock123`

**Python环境**: 必须用 `~/tools/quant_env/bin/python3`（含pyarrow/pymysql），系统Python无pyarrow无法读parquet。

## 已知坑点

| 问题 | 原因 | 解决 |
|:-----|:-----|:-----|
| **stock-sdk volume 单位是"手"，MySQL 存"股" (2026-05-08)** | stock-sdk 从腾讯gtimg.cn获取的volume是手（1手=100股），直接写入MySQL会导致volume少两个数量级 | 列映射时 `volume = r.volume * 100`。详见 `references/stock-sdk-bulk-backfill.md` |
| **EastMoney 批量限流 (~2200只后) (2026-05-08)** | stock-sdk `getHistoryKline` 底层走 EastMoney `push2his` API。连续 ~2200 次请求后所有 EastMoney 域名返回空响应（curl exit 52），持续 30-60min | 限流后改用 parquet 补丁方案 (`scripts/parquet_patch_mysql.py`)。详见 `references/stock-sdk-bulk-backfill.md` |
| **北交所 (92/83开头) 无历史K线 (2026-05-08)** | stock-sdk `getHistoryKline` 对北交所全部 `fetch failed`（EastMoney push2his 不支持），但 `getSimpleQuotes` 正常 | 北交所走 parquet 补丁。脚本中需 `filter(c => !c.startsWith('92') && !c.startsWith('83'))` |
| 北交所数据拉取失败 | `stock_zh_a_hist` 不支持bj前缀 | 脚本已排除北交所市场 |
| CSV 在 Excel 乱码 | 缺少 UTF-8 BOM | 已用 `encoding='utf-8-sig'` |
| `change` 列 SQL 报错 | MySQL 保留字 | 表定义中已用 `` `change` `` |
| `stock_zh_a_hist_tx` 返回列少且成交量为0 | 只有6列(无volume/turnover/pct_chg)，旧版手动填0 | **第一数据源已改为 `stock_zh_a_daily`**，保留 hist_tx 为数据源2。详见 references/data-source-priority-fix.md |
| 涨跌幅计算错误: `(close-open)/open*100` 或填0 | AKShare 单日数据无法计算涨跌幅（无前值），旧版填0.0 | tushare pro.daily() 直接返回真实 pct_chg 和 change，无需手动计算。AKShare回退路径建议优化：用 pre_close 计算 `((close-pre_close)/pre_close*100).round(2)` 替代填0.0。详见 `references/stock-sdk-backfill-impact.md` |
| pandas `to_sql` 大事务撑爆 redo log | 2000个CSV concat后单次INSERT 3M行，触发 `innodb_redo_log_capacity` 告警，MySQL卡死 | 改用 `LOAD DATA LOCAL INFILE` 逐文件导入+每文件commit。详见 `references/mysql-bulk-import.md` |
| tushare stock_basic rate limit | 免费版 1次/分钟（日常够用），波动期可能拒绝后续请求 | 首次成功后缓存 ~/.finquant/cache/shares/float_shares.parquet，后续不再需要调用 stock_basic。若首次即限速→回退 share_db.parquet 总股本近似换手率 |
| **`kline_get()` 返回None: 缓存文件名前缀不匹配** | `kline_get` 读 `k_{code}.parquet`，但 daily_kline_update 写 `{code}.parquet`（无k_前缀） | `kline_get` 现支持双前缀：优先 `k_` 前缀（get_kline_cached写入），兜底 `{code}`（daily管线写入），再兜底API拉取 |
| **`kline_get()` 返回数据但 `close` 列缺失: 中文列名** | daily_kline_update 输出中文列名(日期/开盘/收盘/最高/最低/成交量/成交额/振幅/涨跌幅/涨跌额/换手率)，策略脚本用英文(close/open/high/low) | `kline_get` 内置 `_COL_CN2EN` 映射，自动将中文列名转为英文：日期→trade_date, 开盘→open, 收盘→close, 最高→high, 最低→low, 成交量→volume, 成交额→amount, 振幅→amplitude, 涨跌幅→pct_chg, 涨跌额→change, 换手率→turnover。同时将 datetime.date 类型 trade_date 转为 str |
| **策略回测 NAV 始终为 1.0** | 调仓逻辑中 `d in pos and pos` 用日期字符串查股票字典key——`d`是日期字符串, `pos`是`{code: weight}`字典 | 改为 `d in rb_set and pos`（去掉日期字符串查股票key的错误条件）。该bug也在mid_cap_momentum_rotation.py的v1.3修复 |
| **MCP MySQL Server 僵死连接持有 metadata lock** | pandas to_sql 大事务被 kill -9 后，残留的 `@berthojoris/mcp-mysql-server` 进程在 D 状态，持有 metadata lock 无法被 KILL | 换表名绕过：`CREATE TABLE kline_v2 LIKE kline` → 导入到 v2 → `RENAME TABLE kline TO kline_old, kline_v2 TO kline` → `DROP TABLE kline_old`。或 kill -9 MCP 进程（会失去 MySQL MCP 工具） |
| 腾讯 hist_tx 导入 DB 后成交量/换手率全0 | hist_tx 只有6列(无volume/turnover/pct_chg)，旧版 daily_kline_update 手动填0占位 | 2026-04-30 daily_kline_update 已切到 stock_zh_a_daily（含真实成交量/换手率）。历史重复行仍可能有0值，可通过 import_kline_to_mysql 重新导入 |
| **K线缓存"日期"列类型不一致** | tushare写入的parquet日期列为datetime.date(object)，AKShare写入的为str。pandas跨类型比较报 `Invalid comparison between dtype=str and date` | `date_col = df["日期"].astype(str)` 统一转字符串再比较/过滤 |
| **MySQL stock用户密码`***`access denied (2026-05-08)** | MYSQL_STOCK_PASSWORD=*** 在 .env 中但MySQL拒绝连接 | `sudo mysql -e "ALTER USER 'stock'@'localhost' IDENTIFIED BY 'stock123'"` 重置密码。同步更新所有脚本和.env。 |
| **`daily_kline_update.py` 启动报 SyntaxError** | DB URL 密码占位符 `***` + 换行符间缺少逗号，语法错误 | 密码改实际值 `stock123`，URL 换行前加逗号，连接地址用 `127.0.0.1` 避免 socket 问题 |
| **AKShare回退路径振幅公式错误 (2026-05-06发现)** | `daily_kline_update.py:381` 和 `precache_kline.py:174` 振幅 = `(high-low)/low×100`，应为 `(high-low)/pre_close×100`。分母用最低价替代昨收，振幅值系统性偏高（极端低开时严重失真）。tushare bulk路径已正确使用pre_close | 修改分母为 pre_close。daily_kline_update.py AKShare回退路径需增加 pre_close 列；precache_kline.py 应改为 `(close.shift(1))` 作为分母 |
| **backfill_today_mysql.py NaN→0 静默数据污染 (2026-05-07发现)** | `backfill_today_mysql.py L49-57` 将 open/close/high/low/amount 等列的 NaN 全部转为 0 再插入 MySQL，无任何告警。若 parquet 数据缺失则 MySQL 被静默污染为 0 值 | 保留 NaN，仅 volume 特殊处理。所有列如果为 NaN 记录告警日志。详见 references/data-quality-audit-2026-05-07.md |
| **Tushare成功时不做交叉验证 (2026-05-07发现)** | `daily_kline_update.py L466` Tushare bulk 成功后直接使用数据，不再调用 AKShare 对比。两源数据差异（如振幅公式不同、单位转换错误）无法被及时发现 | 随机抽样 50-100 只用 AKShare 对比 close，差异 >0.5% 告警不阻断。详见 references/data-quality-audit-2026-05-07.md |
| **Xueqiu API `error_code: 0` = 成功 (2026-05-07)** | 雪球 API 用 `error_code: 0` 表示成功，非零表示错误。`if \"error_code\" in data` 会把成功当错误抛出 | `if data.get(\"error_code\", 0) != 0` 显式检查非零。xueqiu_kline.py `_api_get()` |
| **雪球成交额估算 (2026-05-08)** | 雪球API不提供成交额(amount)，precache_xueqiu.py用 close×volume 估算 | 差值可能在除权日较大，不影响策略（策略用 close/volume，amount仅参考） |\n| **雪球Web发布被React反自动化拦截 (2026-05-07)** | Playwright headless 填写编辑器成功但点击`a.submit__confirm__btn`被React拦截，即使非headless也不生效 | 降级为本地Markdown备份到 `~/writing-data/xueqiu-backups/`，手动发布 |

## 速度瓶颈已解决: tushare bulk daily (v2.0, 雪球回退 v2.1)

原 `daily_kline_update.py` 逐只调用 AKShare `stock_zh_a_daily` × 5000次 ≈ **84分钟**。
已重写为 tushare `pro.daily()` 批量方案（v2.0），实测性能：

| 阶段 | 原方案(AKShare) | 新方案(tushare) |
|:-----|:--:|:--:|
| API调用 | 5000+次, 逐只 | 1次, ~0.4s |
| 缓存更新 | 并发10线程 | 顺序遍历（数据已在内存） |
| **总耗时** | **~84分钟** | **~3分钟** |

**架构**: tushare pro.daily() 1次拉取全A股日K → 单位转换 → 逐只更新 parquet + CSV + MySQL upsert。
**回退**: tushare 不可用（节假日/token失效）→ 自动回退到雪球(24h可用) → 雪球不可用再回退到原 AKShare ThreadPoolExecutor 逐只路径。

**v2.1 雪球回退 (2026-05-07)**: daily_kline_update.py 新增 `fetch_today_xueqiu()` 函数，通过 `kline_fallback.get_stock_kline()` 调用雪球 API 拉取当日K线。字段映射：雪球 {date, open, high, low, close, volume, change, change_pct, amplitude, turnover} → OUTPUT_COLS。成交额以 `close × volume` 近似估算。parquet 额外列 `source='xueqiu'` 标记数据来源。控制流：成功率>80%则返回跳过AKShare，否则继续AKShare兜底。`--akshare` 标志可强制跳过tushare和雪球直达AKShare。

**单位转换细节**（详见 `references/tushare-daily-integration.md`）：
- vol(手) → 成交量(股) × 100
- amount(千元) → 成交额(元) × 1000
- 振幅 = (high-low)/pre_close×100（单日数据用pre_close而非low做分母）
- 换手率 = vol(手)×100/流通股本；流通股本缺省时回退 share_db.parquet 总股本近似
- trade_date YYYYMMDD → 日期 YYYY-MM-DD（匹配现有缓存格式）
- ts_code ".SZ"/".SH" 后缀剥离 → 6位代码

**token**: `~/.finquant/tushare_token` 已配置，可用。
**stock_basic 限速**: 免费版 1次/分钟（非原文的1次/小时），首次调用缓存 float_shares.parquet 后不再需要。

## 两融数据管线 (2026-05-01)

`~/quant/margin_data.py`（~660行）+ 缓存目录 `~/.finquant/cache/margin/`：

| cron | 时间 | 任务 |
|:-----|:-----|:-----|
| `18edaa02cd7e` | 16:15 仅工作日 | 拉取沪深两融 → `{date}.parquet`，非交易日自动跳过（通过 `is_trading_day()` 日历检查） |

AKShare 接口: `stock_margin_detail_sse`（沪市~2000只）+ `stock_margin_detail_szse`（深市~2080只）。

**深市限制 (2026-05-01 已修复)**: `stock_margin_detail_szse` 列名与代码映射不匹配（无`日期`/`融资偿还额`/`融券偿还量`列）。已更新 `SZSE_COL_MAP`、注入date列、补NaN到缺失列。深市API不提供偿还额字段（天花板），导致 L4 `l4_net_buy` 对深市股票恒为0。详见 mid-cap-multi-factor 的 `references/szse-margin-column-fix.md`。

**内存预加载优化（v2.0, 2026-05-01）**: 信号引擎 `scan_signals()` 启动时调用 `preload_margin_index(10)` 一次性加载近10天两融到内存 dict，替代原来每只股票逐文件读盘（2000只×4次函数调用×多次parquet打开≈12万次IO → 5次文件读取）。优化思路与 K线更新从逐只AKShare→tushare批量1次调用同源。新增函数: `preload_margin_index()` / `query_margin_from_index()` / `query_margin_history_from_index()`。

## 数据源可靠性 (2026-05-01)

| 数据 | 可靠性 | 说明 |
|:-----|:-----|:-----|
| K线 (Baostock) | ⭐⭐⭐⭐⭐ | 1990-12-19至今全量，含真实amount/pctChg/isST。17:30后更新当日。2026-05-08实测可用 |
| K线 (Tushare pro.daily) | ⭐⭐⭐⭐⭐ | 1次批量拉全A股，0.4s/次，含真实涨跌幅。v2.0主力方案 |
| K线 (雪球) | ⭐⭐⭐⭐ | 24h可用最佳，count=-2000(~8年)，无amount(close×volume估算) |
| 融资融券 (AKShare官方) | ⭐⭐⭐⭐ | 交易所披露数据，非算法估算 |
| ~~主力资金流向 (东方财富)~~ | ⭐⭐ | **已被证伪**：新浪2019实证负相关，BigQuant回测-45.94%。**不推荐使用** |
| 财务数据 (同花顺THS) | ⭐⭐⭐ | 部分字段为空，不同股票列数不同(25~30列) |