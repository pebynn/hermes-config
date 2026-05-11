---
name: mid-cap-multi-factor
description: A股中盘股(50亿~400亿)多因子选股策略 — 6组12因子+行业中性化+风控。支持回测和每日信号模式。可扩展至全A股（主板/创业板/科创板）。
trigger: 多因子策略 中盘股 选股策略 因子选股 改进策略 新版策略 基本面选股 量化选股 选股信号 今日选股 全市场选股
author: Hermes
version: 4.0
related_skills:
  - finance-domain
  - a-share-kline-pipeline
  - deep-research
---

# mid-cap-multi-factor: 中盘多因子策略 v2.1

A股中盘股多因子评分策略，包含回测和每日信号两种模式。

**v2.1 更新：**
- 接入统一数据层 `data_common.py`（tushare 申万110行业分类替代原有行业映射）
- 支持 `--market {all|main|gem|star}` 参数扩展至全市场
- 支持 `--mc-min` / `--mc-max` 参数自定义市值范围
- 双数据源兜底（data_common → 原有 akshare 实现）

## 版本说明

| 版本 | 实现 | 说明 |
|:----|:-----|:-----|
| v4 (现用) | `signal_engine.py` v4.0 | L4两融→stock-sdk资金流；资金流升独立维度权重0.20；共振乘数→直接加法合成；L1降权至0.25；policy_detect完全移除(原87min瓶颈)；scan_signals并行化(4路multiprocessing→~30s)；北向资金晚间时段(h≥19或h≤8)直接跳过不调用AKShare；行业中性化加duplicate index防护；cron 21:00→17:00 |
| v3 (已归档) | `signal_engine.py` v3.0 | 12因子基本面+缠论二买+量价指标+两融共振(L4+北向+政策乘数) |
| v2 (已删) | `mid_cap_enhanced.py` | 6组12因子+行业中性化，年化28.35%/夏普1.54 |
| v1 (已删) | `mid_cap_strategy.py` | 4因子(PE/ROE/营收增长/负债率) |

## 策略参数 (v2)

| 项目 | 值 |
|------|-----|
| 股票池 | 默认主板 (--market=main, 可用 --market=all 全A) |
| 市值范围 | 默认 50~400亿 (--mc-min / --mc-max 可自定义) |
| 因子组 | 价值25% + 质量20% + 成长15% + 动量20% + 低波10% + 情绪10% |
| 子因子 | EP, BP, ROE稳定性, 净利率, 营收增速(环比), 营业利润增速, 12M动量(剔除1M), 1M反转(负向), 60日波动率, 60日最大回撤, 1M换手率(负向), 5日/20日量比 |
| 行业中性化 | 申万一级行业内Z-score（tushare源，110行业） |
| 调仓频率 | 每10个交易日 (双周) |
| 持仓数 | 15~20只, 等权 |
| 风控 | 个股权重上限10%, 单行业上限30%, 流动性过滤>2000万/日, 换手率上限35%, 回撤>25%减半仓 |

## 当前实现 (v4.0 — 2026-05-08)

信号引擎集成四层，不再有独立选股脚本。资金流(stock-sdk)替代原L4两融，升级为独立权重维度。

```bash
# 今日信号（全市场中盘）
~/tools/quant_env/bin/python3 -c "
from signal_engine import scan_signals
df = scan_signals(market='all', mc_min=50e8, mc_max=400e8)
print(df[['code','name','ff_score','composite']].head(20))
"

# 资金流预采集（15:30 cron，为21:00扫描预缓存）
~/tools/quant_env/bin/python3 -c "
from stock_fund_flow import fetch_and_cache_today
fetch_and_cache_today()
"

# 每日信号扫描（cron专用）
cd /home/pebynn/quant && /home/pebynn/tools/quant_env/bin/python3 mid_cap_strategy.py --signal --output /tmp/midcap_signal.json
```

## 因子系统详解 (v2)

### 12因子说明

| 因子组 | 权重 | 子因子 | 计算方式 | 方向 |
|:------|:----|:-------|:---------|:----|
| 价值 | 25% | EP | EPS/股价 (TTM) | 越高越好 |
| | | BP | 净资产/市值 (估算) | 越高越好 |
| 质量 | 20% | ROE稳定性 | 3年均值/标准差 | 越高越稳定 |
| | | 净利率 | 净利润/营收 | 越高越好 |
| 成长 | 15% | 营收增速 | 环比增长率 | 越高越好 |
| | | 营业利润增速 | 环比增长率 | 越高越好 |
| 动量 | 20% | 12M动量(剔除1M) | 过去12月(不含最近1月)累计收益 | 正向 |
| | | 1M反转 | 近1月收益取负值 | 跌多加分 |
| 低波 | 10% | 60日波动率 | 60天日收益率标准差 | 越低越好 |
| | | 60日最大回撤 | 60天最大回撤幅度 | 越小越好 |
| 情绪 | 10% | 1M换手率 | 月均成交量/流通股 | 越低越好 |
| | | 量比 | 5日均量/20日均量 | 放量加分 |

### 行业中性化

申万一级行业分类（tushare源，110个行业）→ 行业内Z-score标准化:
```
factor_z = (factor_value - industry_mean) / industry_std
```

fallback: 原有 akshare 行业映射 (`build_industry_map()`)

### 权重方案

- 固定基准权重 (如上表)
- 可选: IC半衰加权 (过去12M IC, λ=0.9, 月度更新)
- 单因子权重上下限: 5%~30%

## 数据源与缓存

| 数据 | 来源 | 缓存 |
|:----|:-----|:----|
| 股票列表 | data_common (tushare→akshare) | ~/.finquant/cache/stocks/stock_list.parquet |
| 行业分类 | data_common (tushare申万110行业) | ~/.finquant/cache/tushare/stock_basic.parquet |
| K线(前复权) | AKShare 腾讯 stock_zh_a_hist_tx | ~/.finquant/cache/kline/{code}.parquet |
| 财务数据(EPS/ROE/营收增长等) | AKShare 同花顺 stock_financial_abstract_ths | ~/.finquant/cache/financial/{code}.parquet |
| 总股本 | 深交所/同花顺资产负债表 | ~/.finquant/cache/shares/share_db.parquet |

**性能提示**: 全市场(~4966只)回测较主板(~3017只)约慢60%。建议先用 `--market=main` 回测确认策略，再用 `--market=all` 扩展。

## 已知坑点

| 问题 | 原因 | 解决 |
|:----|:-----|:-----|
| **Python docstring 内 `"""` 导致 SyntaxError** | 模块级 docstring 用 `"""..."""`，内部又含 `"""` 字符串，Python 解析器在第一个内部 `"""` 处提前闭合模块 docstring | 避免在模块 docstring 内嵌 triple-quoted 字符串。函数签名描述用纯注释替代：`# detect_buy2(df) -> DataFrame` 而非 `def detect_...: """..."""` |
| **信号扫描极慢(15.6min) — parquet三重重读** | daily_signal_report 串行预过滤(第1遍) → scan_signals 市值过滤(第2遍) → _compute_one_stock 信号计算(第3遍)。每只股票读3次parquet，全市场~15000次磁盘I/O | 市值过滤合并进 `_compute_one_stock`（一次parquet读完成市值检查+信号计算），删除 daily_signal_report 串行预过滤，N_WORKERS 4→8。详见 `references/io-optimization-parquet-triple-read.md` |
| **L2信号泛滥 — 2495/2495全触发** | `detect_chan_buy2` 对所有股票返回信号，`_score_buy2` 最低给50分("弱")且 `_compute_one_stock` 无质量门禁 | L652加 `if l2_score < 75: return None`，只保留"中"(75)和"强"(100)信号。信号数降至200-500 |
| **L2评分天花板 — "强"(100)永远不可达 (2026-05-06发现)** | `_score_buy2` 最高分=基础50+vol_ratio_bonus(20)+pullback_bonus(15)=85，`if score >= 90` 永远为False，所有通过质量门禁的信号只给75分("中")。无股票能拿到100分L2 | 将阈值 `>= 90` → `>= 80`，或基础分提到55并各bonus+5。修复后Top信号中出现"强"级(tested:600519 贵州茅台 可能触发) |
| 回测耗时>10分钟 | 每调仓日需加载大量K线+财务+计算12因子 | 用 --signal 信号模式替代全回测; 或缩短回测区间 |
| 全市场回测更慢 | 股票池扩大65% (3017→4966) | 先 main 回测验证, 再 all 扩展 |
| AKShare超时 | 网络限流 | 脚本含3次重试 |
| 财务数据缺失 | 部分股票无同花顺覆盖 | 跳过该股票，不中断回测 |
| 因子IC方向反转 | 质量因子(ROE稳定/净利率)在中盘股IC近零 | 可考虑替换为毛利率或ROA |
| tushare rate limit | 免费版1次/分钟 | 节流 time.sleep，或用 data_common 的缓存机制 |
| 行业映射缓存 | 修改后 load_industry_map 仍返回旧数据 | rm -f ~/.finquant/cache/shares/industry_map.parquet |
| 财务缓存列类型 | 所有值为 str (非 float)，直接比较会 TypeError | 使用 _to_float() 转换，详见 `references/financial-cache-format.md` |
| 财务缓存列不一致 | 不同股票 parquet 列数不同 (25~30列) | 用 `col in df.columns` 判断 |
| **北向晚间推断不准** | 雪球无北向API，用指数快照间接推断。横盘/板块分化时返回0。非严格线性关系 | 默认已实现三态回退。接受晚间推断≈真实值±30%的误差，仅用于×1.05微弱加成 |
| **行业中性化 O(N²) 卡死 (2026-05-07修复)** | `_neutralize_industry_zscores` 每个因子循环用 `(df["_industry"]==x).sum()` 逐行全列比较，600只×12因子×100行业≈430M次操作 | 预计算 `industry_counts = df["_industry"].value_counts()` (O(N))，用 dict lookup 替代。消除主要CPU热点，详见 `references/industry-neutralization-on2-fix.md` |
| **b60f3c86dd1b cron超时 (2026-05-07修复)** | 模块名错误(`mid_cap_multi_factor`→`mid_cap_strategy`)、方法不存在(`run_daily()`→`--signal --output`)、双脚本冗余扫描全市场两遍 | 单次扫描+JSON格式化文本。借鉴writing-domain分阶段模式：K线(16:00)+两融(16:15)前置→21:00只扫描 |
| **policy_detect.py 13步网络下载瓶颈 (2026-05-07 发现)** | `policy_detect.py` 调用 akshare 拉取政策新闻，13步顺序下载，每步~400秒，总计~87分钟。两个脚本各调用一次（双重浪费）。这是 b60f3c86dd1b cron 超时的主要瓶颈。详见 `references/b60f3c86dd1b-cron-optimization-2026-05-07.md` | 方案1：缓存政策数据到本地（24h有效），避免每次扫描重新拉取。方案2：policy_detect 改为独立前置 cron（如16:30），主扫描 cron 读取缓存 |
| **cron 模块名/方法名错误 (2026-05-07 已修复)** | 旧 cron `b60f3c86dd1b` 步骤1导入 `from mid_cap_multi_factor import MidCapMultiFactor` — 文件不存在，`MidCapMultiFactor.run_daily()` 方法不存在。静默失败，浪费时间 | 正确用法：`mid_cap_strategy.py --signal --output /tmp/midcap_signal.json`。只存在 `mid_cap_strategy.py`（208行），无 `mid_cap_multi_factor.py`。通过 `--help` 确认 CLI |
| **cron 跨日溢出跳过次日推送** | b60f3c86dd1b 21:00周四跑完在周五00:48。调度器看到 last_run_at 在周五，跳过周五21:00的run。工作日晚间cron如果跑过午夜，第二天同一时段的run被静默跳过 | last_run_at 日期=执行日日期检查。如果上次run的日期和下次scheduled在同一天（但时间在后），需手动修复。改cron调度为灵活触发或做间隔控制。2026-05-08已验证发生 |
| **LLM推理cron从未执行 (2026-05-10修复)** — cron `81c6af2f5573` 资金流预采集 last_run_at=null。自然语言prompt描述步骤,依赖LLM代理推理执行;但实际从未触发 | 改为 `no_agent=true` + 独立shell脚本。cron调度仅执行shell命令,不经过LLM调用。详见 scripts/precache_fund_flow.sh |
| **N_WORKERS=8 OOM (系统仅2.5GB可用RAM)** | signal_engine/daily_signal_report 默认8 worker，每个worker约2GB，超出系统空闲内存。8个MP worker在3GB以下机器上会触发OOM kill或swap风暴 | 降为N_WORKERS=4。cron环境更保守建议2-3。修改 `mid_cap_strategy.py` 和 `daily_signal_report.py` 的默认值。详见 `references/o-memory-2026-05-08.md` |
| **Tushare 401 intermittent** | daily_kline_update.py 16:00 cron 返回 `401 - 令牌已过期或验证不正确`，但手动测试同一token正常。大概率是Tushare免费版rate limit（1次/分钟） | 加重试+退避。用 `_get_tushare_pro()` 在每次调用前重新set_token。回退到雪球路径自动生效。token文件 `~/.finquant/tushare_token` |
| **总股本数据库缺失** | `share_db.parquet` 不存在 → turnover无法计算，L1因子缺损 | 运行 `tushare_data_pipeline.py stock-basic` 生成share_db。fallback: 回退到 `data_common.load_share_db()` |
| **L4两融缓存为空** | margin cache目录 `~/.finquant/cache/margin/` 存在但无文件。cron 18edaa02cd7e 16:15 状态ok但当日无数据写入。AKShare两融接口当日收盘16:00后可能延迟发布 | 诊断：`ls ~/.finquant/cache/margin/`。非交易日/刚收盘可能无数据。前一交易日数据可用 `fetch_margin_daily()` 单独验证。2026-05-08当日无数据，但5/7有4045条可用 |
| **scan_signals性能瓶颈 — 北向资金AKShare晚间无限阻塞** | 扫描完成后 `scan_signals()` 执行北向资金获取 `ak.stock_hsgt_fund_flow_summary_em()`, EastMoney API在北京时间19:00-08:00不可用, 该调用阻塞60-120s才抛超时, 之后再降级雪球又走30s | 加时间窗口跳过: 检测北京时h≥19或h≤8时直接设northbound_net=0.0, 不调用AKShare。实测:(v4.0修复) 2.3s完成不含阻塞。详见`signal_engine.py` L900-920的`if not (_now_h >= 19 or _now_h <= 8)` |
| **财务缓存列名中英不一致 — L1因子全NaN (2026-05-10 发现+修复)** | `_compute_layer1` 搜索中文列名(`基本每股收益`/`每股净资产`/`净资产收益率`/`销售净利率`等)，但 `~/.finquant/cache/financial/` 下 5833 个 parquet 文件存的是英文列名(`pe`/`pb`/`eps`/`total_mv`等)。所有 6 个中文列名均不存在 → 全部 12 个 L1 因子为 NaN | **改为兼容模式**: `_compute_layer1()` 添加 `_fin_val(col_cn, col_en, col_en2=None)` 辅助函数，优先中文列名 → 回退英文列名 → 回退二级英文列名。当前英文列名下 8/12 因子可用(EP/BP/动量/低波/情绪正常)，ROE/净利率/营收增速/利润增长需等 `precache_financial.py --force` 刷新多期中文数据后生效。详见 `references/financial-cache-column-mismatch.md`。 |
| **资金流缓存列名不匹配 — 资金流评分恒为50 (2026-05-10 发现+修复)** | stock_fund_flow.py 的 COL_MAP 期望 JS 脚本返回 `mainNet`/`mainNetRatio`/`retailNet`，但实际缓存 parquet 文件列名为 `net_inflow`/`net_pct` (东方财富格式) 或 `main_flow`/`retail_flow` (逐只API格式)。`query_fund_flow` 找不到 `main_net` → 默认 0.0 → `ff_score=50` 恒常输出。 | **三维修复**: (1) 统一缓存文件命名为 `fund_flow_{date}.parquet`; (2) `stock_fund_flow.py` 新增 `_normalize_columns(df)` 函数, 用 `CACHE_COL_MAP` 将 `net_inflow`/`net_pct`/`main_flow`/`retail_flow` 等映射为统一 `main_net`/`main_net_ratio`/`retail_net`/`score`; (3) `precache_fund_flow_full.py` 输出列名改为 `main_net`。详见 `references/fund-flow-column-mismatch.md`。 |
### ❌ 行业中性化处理并行结果时代码重复

并行扫描的结果可能因网络原因有重复code, `df_z.loc[code, fk]` 返回Series而非scalar | 在 `_neutralize_industry_zscores` 函数内 `pd.DataFrame(rows, index=codes)` 后加 `df = df[~df.index.duplicated(keep='first')]`

## 配合技能与模块

- `finance-domain` — 提供终端+文件工具集。配合 finance-domain 使用。
- `chan_buy_signal.py` (~/quant/) — Layer 2 缠论二买信号检测 (IC +0.137, 胜率63.7%)
- `volume_indicators.py` (~/quant/) — Layer 3 量价指标 (OBV/MFI/VWAP/KAMA/POS)
- `signal_engine.py` (~/quant/, 1115行) — 五层信号合成引擎 (L1基本面+L2缠论+L3量价+L4两融共振+L5北向环境)
- `margin_data.py` (~/quant/, 380行) — L4融资融券数据源 (拉取/缓存/趋势/强度/融券压力)
- `daily_signal_report.py` (~/quant/, 276行) — 每日信号报告 (含L4统计/共振/北向)
- `chan-theory` — 缠论技术分析，可在因子选股后增加技术面过滤
- `a-share-kline-pipeline` — K线数据管线的维护和更新
- `domain-capability-upgrade` — 将域升级为领域专家的通用流程
- **cron 推送 (2026-05-08 v4.0 调整)**
  - `b60f3c86dd1b` **信号日报** — 每日17:00 运行 `mid_cap_strategy.py --signal --output /tmp/midcap_signal.json` → agent 解析 JSON 生成文本日报 → 推 QQ Bot。**v4.0从21:00前移到17:00**以避开晚间API黑窗(19:00-08:00)和消除跨日溢出(spillover bug)。前置依赖: afff56398abe(K线16:00) + 81c6af2f5573(资金流14:45)
  - `afff56398abe` **K线更新** — 16:00 no_agent脚本模式
  - `81c6af2f5573` **资金流预采集** — 15:05 no_agent脚本模式(2026-05-10从LLM模式改为脚本模式以消除last_run_at=null问题)
  - **删除**: 雪球发布(18619f5cdf16, 删于2026-05-08), 18:00提醒(704e9bfe5896, 删于2026-05-08, 合并入16:00文章推送)
  - **交叉验证**: 盘前8:00推送(前一交易日数据) + 盘后17:00推送(当日完整数据)

## 数据源可靠性 (2026-05-08 v4.0 更新)
- **资金流数据**：v4.0改用stock-sdk(腾讯数据源)，替代原东方财富push2(被证伪)。stock-sdk内部走腾讯gtimg.cn + 东方财富双路，白天可用性高。**注意**: 盘后(19:00-08:00)可能不可用，通过14:45预采集缓存到parquet避坑。详见`~/quant/stock_fund_flow.py`。
- **融资融券(L4)**: **v4.0已移除**，不再依赖AKShare两融接口。
- **替代方案**：Layer 3 改用 K线自算指标 (OBV/MFI/VWAP)，数据质量等于K线缓存，无第三方依赖
- **stock-sdk MCP 已可用但未集成**：Node.js 50+ tools，提供资金流排名、北向个股持仓、龙虎榜、涨停池、概念/行业板块K线、分钟K线、批量行情。这填补了现有引擎最大的数据空白（资金流/北向个股级）。**当前策略缺少Layer 5集成这些信号源**。详见 `a-share-kline-pipeline` skill 的 `references/stock-sdk-mcp-integration.md`
- **北向资金个股级**：AKShare 全部个股北向接口已失效（`stock_hsgt_individual_em` 停更于2024-08，`stock_hsgt_individual_detail_em` 崩溃）。市场级汇总 (`stock_hsgt_hist_em`) 仍可用。详见 `references/northbound-data-investigation.md`
- **北向资金晚间降级链 (2026-05-07 已修复)**：AKShare push2 晚间(19:00-08:00)不可用 → 雪球指数快照推断 → 默认 multiplier=1.0。三态回退：AKShare成功→用实际值；AKShare失败→从雪球4大指数涨跌幅推断北向方向(校准: ~50亿/1%平均涨幅)；雪球也无方向→multiplier=1.0静默降级。实现: `xueqiu_kline.py::get_northbound_flow()` + `kline_fallback.py::get_northbound_flow()` + `signal_engine.py` L1107-1119。详见 `references/northbound-xueqiu-fallback.md`
- **北向板块成员**：东方财富 clist BK0707 API 可获取1532只北向标的列表，但无个股净买额字段

## v4 (投产): 四维信号合成引擎 — L1+L2+资金流+L3

**状态: v4.0 2026-05-08 投产。L4两融已移除，替换为stock-sdk资金流。cron双推送：盘前8:00 + 晚间21:00。**

三个新模块位于 `~/quant/`，纯 pandas/numpy，零外部依赖：

| 模块 | 行数 | 功能 | 接口 |
|:-----|:----|:-----|:-----|
| `chan_buy_signal.py` | 454 | 缠论二买信号 — MACD底背驰→一买→缩量回踩→二买 | `detect_chan_buy2(df)` / `get_latest_signals(codes, dir)` |
| `volume_indicators.py` | 408 | 5大量价指标 — OBV+背离/MFI(14)/VWAP偏离(20)/KAMA(10,2,30)/POS(5,60) | `compute_all_indicators(df)` / `get_latest_indicators(df)` |
| `signal_engine.py` | ~1070 | v4.0: L1+L2+资金流+L3 复合评分引擎 — 12因子(25%)+缠论(30%)+资金流(20%)+量价(25%)+北向乘数+政策乘数 | `scan_signals(market, mc_min, mc_max)` / `today_signal()` |
| ~~`margin_data.py`~~ | ~~660~~ | **v4.0已移除, 替换为 stock_fund_flow** | |
| `stock_fund_flow.py` | ~280 | **v4.0新增** 资金流缓存模块 — 通过stock-sdk Node.js脚本拉取主力净流入,缓存到parquet | `fetch_and_cache_today()` / `preload_fund_flow(n_days=5)` / `query_fund_flow(code)` |
| `stock_sdk_fund_flow.js` | ~100 | **v4.0新增** Node.js封装,调用stock-sdk SDK获取个股资金流。通过NODE_PATH导入 | `--codes 600519,000858` / `--top 50` / `--rank` |
| `policy_detect.py` | 100 | 政策消息检测 — 从央视新闻联播关键词匹配，返回乘数 | `detect_policy(date_str)` → (multiplier, intensity) |

**信号合成公式 (v4.0, 2026-05-08)**:
```
composite = (L1_scaled×0.25 + L2_score×0.30 + ff_score×0.20 + L3_total×0.25) × northbound_mult × policy_mult
```
- L1 基本面: 权重 0.25 (从0.4降权, 因为L1依赖财务缓存, 更新滞后)
- L2 缠论: 权重 0.30 (最高权重, IC验证+0.137)
- 资金流(ff): 权重 0.20 (新增, stock-sdk源, 主力净流入+散户反向指标)
- L3 量价: 权重 0.25 (从K线自算, 零外部依赖)
- 北向乘数: 当日北向净流入>0 → ×1.05 (AKShare直接获取→雪球推断→静默1.0)
- 政策乘数: 央视新闻联播检测, 无消息=1.0, 温和=1.08/0.93, 重大=1.18/0.83
- **v4.0改动: 移除L4共振乘数, 资金流作为独立加法维度而非乘数**

**L1 基本面因子（v2.1 12因子+行业中性化）**:
- 价值25%: EP(15%) + BP(10%)
- 质量20%: ROE稳定性(10%) + 净利率(10%)
- 成长15%: 营收增速(8%) + 营业利润增速(7%)
- 动量20%: 12M动量剔除1M(12%) + 1M反转(8%)
- 低波10%: 60日波动率(5%) + 60日最大回撤(5%)
- 情绪10%: 1M换手率(5%) + 量比(5%)
- 行业中性化: 申万一级行业内Z-score（tushare源），小行业fallback全局Z-score
- 财务因子从 `~/.finquant/cache/financial/{code}.parquet` 读取，无缓存因子为NaN→中性化后填0

**复合比例注意**: L1 Z-scores 在 [-2,+2] 量级，L2/L3 在 [0-100] 量级。当前公式 L1×0.4 + L2×0.3 + L3×0.3 下 L1 贡献被压制。考虑缩放 L1（如 ×25 对齐 0-100）或调整权重。

**L2 二买评分（50/75/100）**: 基于 vol_ratio、pullback 深度、ATR 值

**L3 量价评分（4维度，各0-25分）**: MFI超卖 / VWAP偏离 / KAMA趋势 / OBV背离

**性能（2026-05-08 并行化后实测 4 workers）**: 
- 非并行前: 顺序扫描600只 ~120s (0.2s/只), 并行4路后扫描600只 **~35s** 预估
- **实测**: scan_signals(code_filter=8只) 并行4路: 1.6s扫描完成 + 0.7s中性化 + 北向跳过 → 总耗时 **2.3s** (无超时/无挂死)
- 瓶颈已消除: policy_detect整块移除(省87min), 北向AKShare晚间跳过(省2min), 盘后空数据不碰东财API
- 系统可用RAM仅2.5GB, 4 worker × ~每worker峰值~500MB → 安全
- **推荐设N_WORKERS=4** (平衡速度与内存), cron环境N_WORKERS=2-3
- 实测吞吐: 4 worker × 1只/s = 4只/s, 全量~2.5分钟 (618只)
- **信号引擎调用路径**: 全量扫描(cron mid_cap_strategy generate_signal) → 建议运行时设N_WORKERS=4
  
  **已知限制**: `scan_signals()` 内部的4路multiprocessing仅在调用方未复用该函数时生效；若上层脚本也用了multiprocessing(spawn), 则scan_signals不会再次并行。`mid_cap_strategy.py` 的 `generate_signal()` 已内置mp_context='fork'兼容。
- **L4 两融 v2.0 内存预加载（2026-05-01）**: 原来每只股票 `_compute_layer4` 逐文件读盘（2000只×每只4次函数调用×多次parquet打开≈12万次IO），改为 `scan_signals` 启动时调用 `preload_margin_index(10)` 一次性加载近10天两融到内存dict，每只查询O(1)。详见 `references/margin-preload-optimization.md`。
- 优化策略: 消除 `daily_signal_report` 串行预过滤（4966次parquet读取）+ `scan_signals` 独立市值过滤循环（二次读取），将市值检查合并入 `_compute_one_stock` 的单次读取

**已知限制**:
- **深市两融接口列名变更 (2026-05-01 已修复)**: `ak.stock_margin_detail_szse` 返回列名与代码映射表不匹配（无`日期`/`融资偿还额`/`融券偿还量`列，多了`证券简称`）。已更新 `SZSE_COL_MAP`、注入date列、补NaN到缺失列。详见 `references/szse-margin-column-fix.md`。
- **K线日期列类型不一致 (2026-05-01 已修复)**: parquet文件中"日期"列混合str和datetime.date类型，`_compute_one_stock` 日期截断比较报 `Invalid comparison`。修复：`astype(str)` 统一转字符串再比较。
- L2信号泛滥已修复（2026-05-01）: `_compute_one_stock` L652 增加 `if l2_score < 75: return None` 质量门禁 — 已投产
- **完整脚本审计报告**: `references/script-audit-2026-05-06.md` — 2026-05-06审计23个脚本，发现3个P0(含L2天花板BUG+db_web SQL注入)、2个公式错误(振幅分母)、若干硬编码日期/密码
- L1 财务数据依赖缓存（`~/.finquant/cache/financial/`），缓存列名中英文混用、值全为str类型（详见 `references/financial-cache-format.md`）
- tushare daily() 批量K线1次调用替代逐只AKShare耗时~3分钟（已投产）
- 深市两融API不提供`融资偿还额`/`融券偿还量`字段，L4 `l4_net_buy` 对深市股票恒为0（API天花板）

**完整API文档**: `references/signal-engine-modules.md`

---\n\n## L4 融资融券资金流层（已实现 v1.0，2026-05-01）\n\n### 数据源\n\nAKShare 两个接口均验证可用（2026-05-01），每日逐只披露，数据新鲜：\n\n| 接口 | 覆盖 | 字段 |\n|:-----|:--:|:-----|\n| `stock_margin_detail_sse` | ~2000只沪市 | 融资余额、融资买入额、融资偿还额、融券余量、融券卖出量 |\n| `stock_margin_detail_szse` | ~2080只深市 | 融资买入额、融资余额、融券余量、融券余额、融资融券余额 |\n\n合计约4000只两融标的，覆盖中盘50-400亿池子绝大部分。历史日期可用（测试了20260401/20260417/20260424/20260429）。\n\n### 四个指标（0-100分）\n\n| 指标 | 权重 | 计算 | 含义 |\n|:-----|:--:|:-----|:-----|\n| 融资余额趋势 | 30 | 5日融资余额变化率 Z-score | 杠杆资金持续加仓→高分 |\n| 净买入强度 | 25 | (买入额-偿还额)/当日成交额 | 杠杆方向+力度 |\n| 买入加速度 | 25 | 今日净买入 - 5日均净买入 | 加速进场信号 |\n| 融券压力(逆) | 20 | -1 × 融券余额变化率 | 空头撤退→高分 |\n\n### 共振判据\n\nL4和L2的对齐程度给乘数加成，不改现有三层加权体系：\n\n```\nL4≥60 且 L2≥75  →  composite × 1.30  (资金+技术共振，最强)\nL4≥60 且 L2<75  →  composite × 1.10  (资金先进，技术等确认)\nL4<40 且 L2≥75  →  composite × 0.80  (技术缺资金验证，衰减)\nL4<40 且 L2<75  →  composite × 0.90\n其他              →  composite × 1.00\n```\n\n### 北向资金降级为宏观环境信号\n\n个股北向接口全数失效，仅市场级汇总可用。降级为 L4 微幅加成：当日北向净流入>0 → L4总分×1.05。\n\n### 实施文件\n\n- 新建 `~/quant/margin_data.py` — 两融拉取+缓存模块（`~/.finquant/cache/margin/{date}.parquet`）\n- 修改 `signal_engine.py` — 新增 `_compute_layer4()` + 共振判据\n- 新增 cron 16:05 — 两融数据拉取\n\n---\n\n## Next-Gen: 四层信号融合系统 (设计文档)

一个完整的系统设计方案已在 `~/research-skill-graph/projects/quant-system-design/` 中完成（4个文件，888行），包含：

- **Layer 1**: 基本面因子（在v2.1基础上扩展至15+因子，加入本土化Fama-French）
- **Layer 2**: 缠论结构信号（基于czsc/chan.py自动识别买卖点）— **v3原型已用纯pandas实现**
- **Layer 3**: 量价智能验证（MFI/OBV/VWAP从K线自算 + 融资融券杠杆情绪 + 换手率异常检测）。**不用主力资金流向**——东方财富算法估算已被多份实证否定（BigQuant策略回测-45.94%，新浪2019实证5日净流入前100弱于后100）。详见 `references/layer3-volume-price-substitution.md`。— **v3原型已实现5个核心指标**
- **Layer 4**: 共振判据（多周期一致性+市场状态识别+自适应权重）

预期保守提升：年化32-38%/夏普1.6-1.8。最大风险：缠论信号缺乏量化验证。