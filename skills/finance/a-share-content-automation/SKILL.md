---
name: a-share-content-automation
description: A股内容自动化 - 从数据采集→量化分析→AI写作→发布的完整管线（盘前早报+每日复盘(含跨日对比)+周末周总结(定调版)+周末深度图文）
version: 3.1.0
author: Hermes
domain: finance-domain
---

# A股内容自动化

A股量化内容创作全流程自动化：每日收盘复盘 + 周末深度周总结。

**核心价值**：数据驱动 + AI写作 + 公众号草稿箱发布 + 人工审核保证质量

---

## ⚠️ CRITICAL: 产出优先于基础设施

当用户要求生成文章时，禁止先修改管线脚本。必须先用现有工具尝试产出，失败后报告原因，不可一边修工具一边声称"能产出"。详见 `references/failure-2026-05-10.md`。

## 工作流模式

### 模式0：盘前早报（周一至周五 8:00）

**时间线**：
- 08:00：自动采集隔夜外盘数据 + 昨日复盘摘要 → 模板化生成300-500字早报 → 推送到微信草稿箱

**特点**：
- **零AI成本**：纯Python模板化生成（无DeepSeek调用）。隔夜数据+财经新闻+昨日摘要→模板拼装
- 覆盖：美股三大指数（道指/纳指/标普500）、A50期货、恒生指数、今日财经要闻、昨日复盘回顾
- 综合判断：根据美股+A50涨跌比自动生成偏暖/偏弱/中性判断
- **多源降级链**（v3 2026-05-09）：
  - 美股：**stock_sdk** (MCP JSON-RPC bridge) → Sina hq.sinajs.cn → AKShare
  - A50：**stock_sdk** (MCP JSON-RPC bridge) → Sina (hf_CHA50CFD) → 雪球 → AKShare
  - 恒生：**stock_sdk** (MCP JSON-RPC bridge) → Sina (int_hangseng) → 雪球 → AKShare
  - 降级链通过 `fetch_with_fallback()` 统一管理，任一源成功即输出
  - 输出标注数据源 `[stock_sdk]` / `[Sina]` / `[雪球]` / `[AKShare]`
- **stock_sdk 桥接**：`shared/stock_sdk_client.py` 通过 MCP JSON-RPC 子进程协议调用 stock-sdk Node.js MCP Server，获取美股/恒生/A50实时行情。详见 `references/stock-sdk-client-bridge.md`

**文件命名**：`~/writing-data/drafts/YYYY-MM-DD-盘前早报.md`

**脚本**：`morning_brief.py`，位于 `~/writing-data/scripts/`
- `--check-only`：仅检查交易日不生成
- `--no-push`：生成早报但不推送微信

### 模式0.5：SEO优化复盘（交易日 15:10，独立于原复盘管线）

**脚本**: `generate_review_seo.py`（从 generate_review.py 复制改造，不修改原文件）
**cron**: `8aa4c853cff3` — 交易日 15:10
**数据源**: `data_collector_seo.py` — 轻量实时采集器，四源并行(Sina+stock-sdk+AKShare+雪球)
**特点**：
- 不再自行采集 — 依赖 15:10 cron 预采集的 `all_data_fresh.json`（2026-05-10 修复冗余采集）
- **标题优化**：情绪钩子+数字+关键词公式
- **SEO导语**：前100字含核心数据
- **关键词布局**：自动从数据提取8个搜一搜关键词
- **互动引导**：文末CTA
- 原复盘管线（模式1）保留不变，两者并行
- 管线全貌详见 `references/writing-domain-audit-2026-05-10.md`

**脚本**: `generate_short_posts.py`（新增）
**cron**: `108ce7535e38` — 交易日 15:15（与SEO复盘错开5分钟）
**特点**：
- 从 all_data.json 自动提取3-5个数据亮点
- 生成短图文（200字+配图），用于公众号"发布"功能（不占群发配额）
- 5种数据类型：index/fund/limit/sector/volume
- 详见 `references/seo-optimization-guide.md`

### 模式1：交易日每日复盘（周一至周五）

**时间线**：
- 15:30：自动采集当日数据 + 量化分析 + AI写作
- 18:00：微信推送通知，提醒查看草稿

**文章结构**（5章节+跨日对比模块，1500-2000字）：
```
一、大盘回顾（指数表现+量能+涨跌家数）→ 结合"趋势加速度"判断加速/刹车
二、资金风向标（主力资金+行业轮动）→ 结合"资金3日动向"判断持续性
三、热点解读（板块涨跌+龙头点评）→ 结合"热点持续性"识别主线vs昙花一现
四、趋势判断（新增，融入前三章）：基于跨日对比判断市场阶段
五、技术看盘（支撑/压力+关键信号）
六、明日策略（方向+关注+仓位）
```

**跨日对比模块 (2026-05-10 新增)**：
- 趋势加速度：今日指数/成交量/涨跌比 vs 前5日均值
- 资金3日动向：主力资金连续方向+强度变化
- 热点持续性：连续上榜板块识别（出现≥2次）
- 数据源：`_load_previous_days()` 扫描前N交易日 `all_data_fresh.json`
- 提示词注入：`_format_rolling_lines()` 生成跨日对比数据段，注入prompt

**文件命名**：`~/writing-data/drafts/YYYY-MM-DD-每日复盘.md`

### 模式2：周末周总结（周五16:00收盘后，一体化执行）**v3.0 — 2026-05-10 从回顾→定调**

**时间线**：
- 16:00：自动采集本周数据 + 识别热门前三板块 + 生成周度图表 + AI写作 + 推送到微信草稿箱（一步到位）

**周总结特点（v3.0 重构）**：
- 不再逐日罗列，改为一条主线串起本周行情
- 新增"资金共识度"判断（主力/北向/游资三方是否一致）
- 新增"下周风险点"（解禁/财报/外部事件）
- 板块分析加"持续性判断"（轮动→主线？）
- 字数2000-3000字

**文章结构**（6章节）：
```
一、本周脉络（替代逐日回顾 — 核心矛盾+多空争夺主线）
二、资金共识度（新增 — 主力累积方向+资金一致还是分歧）
三、热门前三板块深度分析（持续性判断：轮动还是主线？）
四、下周关注（政策节点/财报窗口/技术位置+值得跟踪板块）
五、下周风险点（新增 — 潜在利空+关键支撑）
六、结尾（风险提示+关注引导）
```

**硬性约束**（不变）：
- ⚠️ 全文严禁出现"建议"二字
- 第4节标题固定为"下周关注"，不是"操作建议"
- 风险提示不使用"投资建议"措辞，改为"投资参考"

**文件命名**：`~/writing-data/drafts/YYYY-MM-DD-周总结.md`

## ⚠️ CRITICAL: 产出优先于基础设施

当用户要求生成文章时，禁止先修改管线脚本。必须先用现有工具尝试产出，失败后报告原因，不可一边修工具一边声称"能产出"。详见 `references/failure-2026-05-10.md`。

### 模式3：周末内容策略（2026-05-11 实施）

原 `weekend_deep_dive.py` 已于2026-05-10回撤删除。**不重新创建**。

**周末发布节奏（2026-05-11 最终版）**：
- 周五 16:00：周总结(含信号引擎"下周关注") → 公众号草稿箱 (3858ff88add6)
### 周末发布节奏（2026-05-11 最终版）
- 周五 16:00：周总结 → 公众号草稿箱（含信号引擎"下周关注"）(3858ff88add6)
- 周六 08:00：量化周报 → 公众号草稿箱 (bc02d5952723，从周日15:30迁移)
- 周六 08:00/14:00：科普×2 → 公众号草稿箱 (9f73cbaa5f1e, d50d838746d6)
- 周日 08:00/14:00：科普×2 → 公众号草稿箱 (d403a750c641, 032e7102e419)

周末总产出: 1篇量化周报 + 4篇科普 = 5篇。全部复用现有管线。

QQ通知: 所有写作脚本已统一接入 `notify.py`（`from notify import article_published`）。文章推送草稿箱成功后自动调用。quant_weekly除外（用户要求独立处理）。notify.py写入JSON队列 → pipeline_runner每30min投递 → QQ Bot。

---

## 核心协议：识别本周最热方向

**执行时机**：周六日15:00

**数据源扫描**：
1. 扫描本周一至周五的原始数据目录 `~/writing-data/raw/YYYY-MM-DD/`
2. 检查交易日完整性（至少3个交易日才生成周总结）

**评分机制**：
- 综合评分 = 板块出现频率 × 2 + 累计涨幅 / 交易日数
- 按评分降序排列，取前3为热门板块

**分析维度**：
1. **板块热度**：统计涨幅Top10板块出现频率
2. **资金热度**：资金流入最多的行业
3. **涨停热度**：涨停股最多的概念板块
4. **持续性**：连续上涨的板块/题材

**输出格式**：前3板块逐一分析，每个板块含：
- 板块名称 + 出现次数 + 累计涨幅
- 为什么热（数据支撑）
- 龙头股表现
- 后续逻辑
- 本周数据支撑

---

## Cron任务模式

**一致性原则**：所有内容生成任务的执行时间保持一致
- 数据采集/分析时间：15:30（收盘后30分钟）
- 通知推送时间：18:00（人工审核窗口）

**标准Cron配置示例**：

```yaml
# 交易日每日复盘生成
- name: "A股每日复盘生成"
  schedule: "30 15 * * 1-5"
  enabled: true

# 交易日每日复盘通知
- name: "A股每日复盘推送通知"
  schedule: "0 18 * * 1-5"
  enabled: true

# 周末周总结生成
- name: "A股周总结分析生成"
  schedule: "30 15 * * 6,0"
  enabled: true

# 周末周总结通知
- name: "A股周总结推送通知"
  schedule: "0 18 * * 6,0"
  enabled: true
```

**通知内容模板**：
```
【A股复盘已生成】
文件位置: ~/writing-data/drafts/YYYY-MM-DD-每日复盘.md
请审核后发布到微信公众号草稿箱

或

【周总结已生成】
文件位置: ~/writing-data/drafts/YYYY-MM-DD-周总结.md
请审核后发布到微信公众号草稿箱
```

---

## 数据采集协议

## 数据采集协议

### 数据源准确性分级（2026-05-05 深度调研结论）

| 维度 | 准确性 | 数据源 | 可回填历史 |
|------|--------|--------|-----------|
| 指数收盘价/涨跌幅 | **A（100%）** | 腾讯(web.ifzq.gtimg.cn) / Sina / **stock-sdk-mcp** | ✅ |
| 两市合计成交额 | **A（100%）** | 上证+深证预计算 | ✅ |
| 涨跌停列表 | **A（100%）** | 雪球 / **stock-sdk-mcp `get_zt_pool`** | ✅ |
| 板块涨跌幅（当日） | **A（当日实时准确）** | Sina / **stock-sdk-mcp `get_industry_spot`** | ❌ 不可回填 |
| 主力资金（当日） | **B（L1估算）** | **stock-sdk-mcp `get_fund_flow_rank`** | ❌ 不可回填 |
| 行业资金流（当日） | **B（估算）** | **stock-sdk-mcp `get_fund_flow_rank`** / Sina | ❌ 不可回填 |
| 龙虎榜/大宗交易 | **A** | **stock-sdk-mcp `get_dragon_tiger_list`** | ✅ |

> ⚠️ 资金流向数据本质为第三方基于逐笔成交的L1分类估算，非交易所官方数据。任何数据源都无法声称100%准确。
> ⚠️ `stock_board_industry_hist_em()` 实测数据范围仅至2022年，不可用于当前数据回填。板块历史方案 = 当日准时采集 + JSON存盘 + 周总结读盘。
> 详见 `references/data-source-accuracy-report.md`

### 每日采集（交易日15:30）

**Cron**: `A股每日数据采集+图表生成（15:30）` — `30 15 * * 1-5`
执行: `collect_data.py --date $TODAY` → `generate_charts.py --date $TODAY`

**输出JSON含 `_meta` 元数据**：
```json
{
  "_meta": {
    "accuracy": {"indices": {"level": "A", "note": "交易所直连数据"}, ...},
    "sources": {"indices": "AKShare stock_zh_index_daily_em (东方财富)", ...},
    "limitations": {"main_force_flow": "无历史端点，不可回填；资金流向本质为估算非官方数据", ...},
    "collected_at": "2026-05-05 15:30:00"
  },
  "is_trading_day": true,
  "data_completeness": {"indices": true, "sectors": true, "main_force_flow": true, "sector_flow": true, "limit_up_down": true},
## 数据采集协议

### 数据源架构（v7 — 2026-05-10 雪球升格为二等数据源，写入主采集loop）

**fallback链（collect_data.py / data_collector_seo.py / fallback_pipeline.py）**：
```
Sina (hq.sinajs.cn, 一等实时源)
  └→ 雪球 (stock.xueqiu.com batch/quote, 二等实时源，无需Referer)
     └→ stock-sdk-mcp (腾讯, 三等源，晚间受限)
        └→ AKShare (东方财富, 四等/兜底源，IP已封锁)
```

**实现文件**（2026-05-10 5文件）：
- `collect_data.py` — 指数采集 loop 在 Sina 失败后立即插入 `_collect_xueqiu_indices()`，使用懒加载的 `XueqiuSource` 单例。字段映射：`current→index, percent→change_pct, amount/1e8→turnover`
- `data_collector_seo.py` — 新增 `_collect_xueqiu_indices()`，四源并行采集 thread `_t4`，参与交叉验证和合并
- `fallback_pipeline.py` — 新增 `fetch_xueqiu_indices()` 实时 + `fetch_xueqiu_kline()` K线 两函数
- `generate_charts.py` — `chart_volume_comparison()` Sina KLine API 失败时降级雪球 `get_kline()`
- `pipeline_health_check.py` — 新增雪球API连通性检查项

**数据源优先级**: stock-sdk-mcp (腾讯) → AKShare (东方财富, 已封锁) → Sina → **雪球 (2026-05-10 升格为三等源)**

⚠️ **当前环境 EastMoney IP已永久封锁**。所有 `ak.stock_*_em()` 端点均不可用。stock-sdk-mcp 是唯一可靠的主数据源。

**雪球（第三备源，2026-05-10 升格）**：
- 之前仅用于验证/反向填充，现在嵌入主采集loop作为Sina失效后的数据源
- 优势：无需Referer头、cookie-auth可用、晚间不受限制
- 劣势：需要有效cookie（`xq_a_token` 约30天过期），首次需浏览器登录

所有采集数据输出 `all_data.json` 含 `_meta` 字段，标注各数据维度的精度等级（A/B）、数据来源和已知局限性。

| 维度 | 一等源 | 降级链 | 精度 | 历史回填 |
|------|--------|--------|------|---------|
| 大盘指数 | **stock-sdk-mcp** `get_a_share_quotes` / `get_market_overview` | Sina → **雪球 (2026-05-10)** | **A** | ✅ |
| 涨跌停 | **stock-sdk-mcp** `get_zt_pool` / `get_zt_pool(type="dt")` | — | **A** | ✅ |
| 板块涨跌幅 | **stock-sdk-mcp** `get_industry_list` | Sina | **A** (当日) | ❌ |
| 主力资金 | **stock-sdk-mcp** `get_fund_flow_rank` / `get_market_fund_flow` | — | **B** (L1估算) | ❌ |
| 涨跌家数 | **stock-sdk-mcp** `get_market_overview` northbound up/down count | AKShare updown_statistics | **B** | ❌ |

> stock-sdk-mcp 的 `get_history_kline` / `get_kline_with_indicators` / `get_industry_list` / `get_fund_flow_rank` 在 19:00-08:00 间可能不可用。
> 晚间不可用时的应对详见 `references/stock-sdk-mcp-usage.md`。

🚀 **stock-sdk-mcp（腾讯数据源）**（2026-05-08 提升为一等源）：
- MCP Server 已全局安装：`/home/pebynn/.hermes/node/bin/stock-mcp`
- 总指挥可直接调用 MCP 工具，无需 delegate（MCP 工具已注册：`mcp_stock_sdk_*`）
- 晚间 19:00-08:00 仍可用（部分接口有限制）
- 详见 `references/stock-sdk-mcp-usage.md`

所有采集数据输出 `all_data.json` 含 `_meta` 字段，标注各数据维度的精度等级（A/B）、数据来源和已知局限性。

| 维度 | 数据源 | 精度 | 历史回填 | 局限 |
|------|--------|------|---------|------|
| 大盘指数 | AKShare `stock_zh_index_daily_em` + Sina fallback + **雪球 fallback** | **A** (交易所直连) | ✅ | 晚间AKShare不可用时走Sina→雪球降级链；雪球可24h获取，已集成反向自动填充 |
| 板块涨跌幅 | AKShare `stock_board_industry_name_em` + Sina fallback | **A** (当日实时) | ❌ | Sina行业板块作为备用源 |
| 主力资金 | AKShare `stock_market_fund_flow` | **B** (L1估算) | ❌ | 无备用源；资金流向本质为估算 |
| 行业资金流 | AKShare `stock_sector_fund_flow_rank` | **B** (估算) | ❌ | 无备用源 |
| 涨跌停 | AKShare `stock_zt_pool_em/_dtgc_em` | **A** | ✅ | 无备用源；已过滤北交所/IPO/ST/退市 |
| 两市成交额 | 上证+深证预计算 | **A** | ✅ | — |

🚀 **雪球第三数据源（2026-05-07 集成，2026-05-10 升格为主采集源）**：
- 模块：`~/quant/xueqiu_kline.py`（双域共享基础设施）
- 之前：仅用于验证/反向填充 (`validate_indices_with_xueqiu`, `fill_indices_from_xueqiu`)
- 2026-05-10 升级：5个脚本嵌入主采集loop，Sina失败后直接调 `_collect_xueqiu_indices()` / `fetch_xueqiu_indices()`
  - `collect_data.py` — `_get_xueqiu_source()` 懒加载 + `_collect_xueqiu_indices()` 批量采集
  - `data_collector_seo.py` — 四源并行 `_t4` 线程
  - `fallback_pipeline.py` — 实时+ K线两函数
  - `generate_charts.py` — 成交量图降级
  - `pipeline_health_check.py` — 连通性检查
- 详见 `references/xueqiu-data-source.md` 和 `references/cross-validation-design.md`

⚠️ **已知死路**：`stock_board_industry_hist_em()` 实测数据只到2022年，不可用于当前数据回填。
⚠️ **北向资金** (`stock_hsgt_hist_em`) 已于 2024-08 停更，全管线已切换主力资金。

#### 早报多源降级（morning_brief.py v3 — 2026-05-09 stock_sdk为主源）

**盘前早报数据采集已升级为 stock_sdk 主源链：**
- 美股三大指数：**stock_sdk** (MCP JSON-RPC) → Sina (hq.sinajs.cn) → AKShare
- A50期货：**stock_sdk** (MCP JSON-RPC) → Sina → 雪球 → AKShare
- 恒生指数：**stock_sdk** (MCP JSON-RPC) → Sina → 雪球 → AKShare
- 每个数据点标注实际数据源（`[stock_sdk]`/`[Sina]`/`[雪球]`/`[AKShare]`），所有源失败才报错。
- **stock_sdk_client.py** (shared/) 通过 MCP JSON-RPC 子进程协议调用 stock-sdk Node.js MCP Server，实现美股/恒生/A50实时行情采集。晚间 US 闭市时段 stock_sdk 返回空 → 自动降级 Sina。
- `references/xueqiu-source-integration-2026-05-10.md` — 🆕 雪球数据源集成指南：字段映射/symbol映射/5个脚本各的集成模式/验证清单
- `references/stock-sdk-client-bridge.md` — 

#### collect_data.py 4-way 交叉验证 + 雪球主采集回退（2026-05-10 升级）

原有三个验证函数：

新增四个集合函数（2026-05-10，主采集用）：
- `fill_indices_from_xueqiu()` — 当 AKShare 指数缺失（晚间黑窗）时自动从雪球回填
- `validate_xueqiu_vs_sina()` — 雪球 vs 新浪直接对比，写入 `_cross_validation.xueqiu_vs_sina`

交叉验证输出结构：
```json
{
  "_cross_validation": {
    "indices": {"source": "Sina Finance", ...},       // AKShare ↔ Sina
    "xueqiu":  {"source": "Xueqiu", ...},             // AKShare ↔ 雪球
    "xueqiu_vs_sina": {"source": "Xueqiu vs Sina", ...} // 雪球 ↔ Sina
  }
}
```

### 每日采集（交易日15:30）

**核心数据**：
- 上证指数/深证成指/创业板指/科创50：涨跌幅、成交量、成交额
- 两市合计成交额：`market.total_turnover`（采集时由上证+深证预计算）
- 主力资金（AKShare `stock_market_fund_flow`）：净流入、净占比、超大单/大单明细

**板块/行业数据**：
- 涨幅Top5板块及代表股
- 跌幅Top5板块及代表股
- 资金流入Top5行业
- 资金流出Top5行业
- 涨停股（需过滤北交所/IPO/ST/退市，详见 `references/limit-stock-filtering.md`）
- 跌停股（同上过滤）
- 涨停家数/跌停家数 = 过滤后有效计数（非API原始返回数，排除规则见 `references/limit-stock-filtering.md`）
- ⚠️ **严禁AI编造数字** — Prompt中所有金额/涨跌幅/家数必须是精确值，AI不得自行计算、估算或编造任何数字（见 `references/anti-hallucination-mechanisms.md`）
- 两市合计成交额：采集时预计算 `上证+深证`，AI直接引用
- **主力资金**：使用 `ak.stock_market_fund_flow()`（北向已停更），含净流入/净占比/超大单/大单
- 成交额Top10
- 资金净流入Top10
- 资金净流出Top10

### 周末数据汇总（周五16:00，周总结自给自足）

**Cron**: `A股周总结一体化（周五16:00）` — `0 16 * * 5`
执行: `weekly_summary.py --date $(date +%F)`（含自动采集兜底+图表生成+DeepSeek写作+草稿箱发布）

**扫描范围**：
- 本周一至周五的 `~/writing-data/raw/YYYY-MM-DD/` 目录
- 至少3个交易日数据才生成周总结，否则跳过
- 若当日数据缺失，自动调用 `collect_data.py` 补采（不依赖外部 cron）

**统计指标**：
- 指数周涨跌幅
- 每日成交额变化趋势
- 主力资金整体流向（含置信度标注，估算值提醒AI不过度解读）

---

## 量化分析协议

### 每日分析（交易日）

**技术指标计算**：
- 指数均线位置（MA5/MA10/MA20）
- 涨跌家数比
- 市场情绪指标（涨停跌停比）
- 成交量对比（较昨日/五日均量）

**资金流向分析**：
- 主力资金整体方向（净流入/净流出、净占比）
- 行业资金轮动（流入Top5/流出Top5行业）

**关键信号识别**：
- 缠论二买信号（复用signal_engine）
- 资金流共振信号
- 背离/突破技术形态

### 周末深度分析

**最热方向分析维度**：
1. **驱动因素**：政策/业绩/事件驱动
2. **龙头表现**：涨幅+资金流+技术形态
3. **后续逻辑**：能否延续+催化剂
4. **风险点**：估值压力+获利回吐+政策不确定性

**数据支撑生成**：
- 板块内个股涨跌分布
- 资金流入流出明细
- 相关技术指标信号

---

## AI写作协议

### 模型选择

| 场景 | 推荐模型 | 理由 |
|------|---------|------|
| 每日复盘 | DeepSeek-V4 | 逻辑推理强，适合数据解读 |
| 周总结 | DeepSeek-V4 | 统一模型，简化维护 |

### 写作质量增强（v2.0 — 2026-05-05）

集成三个社区技能提升写作质量：

**avoid-ai-writing** — 清除AI写作痕迹（已内嵌到 generate_review.py + weekly_summary.py）：
- **Prompt层**：system prompt 嵌入完整禁用词清单（45+词，含财经AI高频："强势反弹""大举扫货""全线飘红""赚钱效应"等）+ 替代写法指南
- **代码层**：`scrub_ai_vocabulary()` Tier1自动替换（45词）+ 正则模式清除 + 第二遍审计
- **强制规则**：所有图文内容生成后必须经过 avoid-ai-writing 后处理，禁止跳过

**content-creator** — SEO优化：
- 标题含2-3个关键词（科创50/主力资金/涨停等）+ 具体数字 + 情绪钩子
- 前100字点题（微信公众号摘要预览区）
- 给出好/差标题对比示例

> 📋 完整写作质量管线规范（110+词Tier1清洗表 + Tier2聚类 + Tier3密度 + audit_guard.py审核守门员）→ `references/writing-quality-pipeline.md`（原 `a-share-writing-quality` 技能已归档至此）

**baoyu-infographic** — 封面图设计语言：
- dashboard + corporate-memphis 风格
- 深色底 (#0d1117) + 彩色指标条 + 数据卡片
- matplotlib 渲染（零API成本，FAL.ai 不可用时降级）

### 提示词设计原则

**每日复盘（v3 — 2026-05-06 动态标题）**：
- 标题根据当日最亮眼数据动态生成（`_compute_highlights()` 评分引擎：5维度评分×排序）
- Prompt 注入当日亮点，不硬编码"科创50"示例
- 严格按5章节结构输出
- 数据引用100%准确，禁止编造
- 数据引用100%准确，禁止编造
- Prompt数据区一律使用精确值，不用"约"/"近"/"超"
- 必含anti-Hallucination指令（见"数据准确性—防AI幻觉机制"章节）
- 结尾固定风险提示+AIGC标识

**周总结**：
- 标题根据本周实际热点动态生成，不强制固定格式
- 分析范围：热门前三板块（非单一方向），每个板块独立段落
- 第4节标题固定为"关注方向"（非"操作建议"）
- 全文严禁出现"建议"二字，用"关注""跟踪""观察""思路""要点"替代
- 字数1800-2800字（三板块需更多篇幅）
- Prompt包含逐日成交额数据（量能表格），AI无需自行计算
- 必含anti-Hallucination指令
- Prompt数据区一律使用精确值，不用"约"/"近"/"超"

### 字数控制

| 文章类型 | 字数范围 |
|---------|---------|
| 每日复盘 | 1500-2000字 |
| 周总结 | 1800-2800字 |

---

## 自动回复 — 股票代码查资金流向

**服务**: `wechat_auto_reply.py` — systemd服务 (wechat-reply.service)，端口8800
**原理**: 微信公众号开发者模式回调 → 解析用户消息 → 识别股票代码 → stock-sdk查行情+资金流 → 自动回复XML
**配置**: 公众号后台 → 服务器配置 → URL=http://113.110.7.84:8800/wechat, Token=hermes2026
**启动**: `systemctl --user restart wechat-reply.service`
**详见**: `references/seo-content-optimization.md` "自动回复服务"章节

### ❌ CTA写了但功能没建
在文末引导"回复股票代码查资金"之前，必须先运行自动回复服务并配置微信后台。否则用户收到的是"该公众号暂未开通此功能"。
**修复**: 先建后写，或标注"即将上线"。

## 发布协议

**模式**：AI生成 → 草稿箱 → 人工审核 → 次日发布

**支持的文章类型**：
- `daily` — 每日复盘（`publish_draft.py --type daily`）
- `weekly` — 周末周总结（`publish_draft.py --type weekly`）
- `科普` — 理财科普系列（`publish_kepu.py`，2026-05-10新增独立脚本）
- `盘前早报` — 模板化生成零AI成本（`morning_brief.py` 内建推送）
- `小绿书` — 短内容不占群发（`generate_short_posts.py` 内建推送）
- `SEO复盘` — 标题公式+搜一搜关键词（`generate_review_seo.py` 内建推送）

**草稿箱同步（三级降级，2026-05-08更新）**：
1. 开发者 API (`access_token`, 需IP白名单) → 已失效(40164)
2. 🍪 ~~Cookie 直连 API~~ → **已废弃**。`cgi-bin/operate_appmsg` 2026年API变更，创建草稿返回`ret=2`(列表)/`ret=200002`(参数错误)。`cookie_publish.py` 保留但不再推荐。
3. 🌐 **浏览器自动化 (`browser_publish.py`)** — Playwright + Cookie鉴权，**当前主力方案**。绕过IP白名单。详见 `references/wechat-mp-prosemirror-publishing.md`
4. 本地 HTML 保存（手动粘贴）— 最终兜底

**Cookie生命周期**：从Chrome DevTools导出的完整cookie集(~14项)有效期约7-14天。过期后需重新导出 `~/.hermes/credentials/wechat_cookies.json`。

**人工审核窗口**：
- 每日复盘：18:00通知 → 次日上午9:00前发布（复盘黄金时段）
- 周总结：周六日18:00通知 → 下周一上午9:00前发布

### 雪球长文发布（2026-05-07 浏览器自动化）

与微信草稿箱并行的独立发布渠道。

**脚本**：`publish_to_xueqiu.py`（Playwright浏览器自动化 + requests Cookie验证）

**认证**：需从浏览器导出**全部**cookies（xq_a_token + xq_r_token + acw_tc等），存为 `~/.hermes/credentials/xueqiu_cookies.json`。仅 xq_a_token 不足以维持Web登录态。

**Cookie验证**：用 `https://xueqiu.com/v4/stock/quote.json?code=SH000001`（不用 /setting/user——HTML含"login"字样误判）。

**发布**：Playwright headless→`/write`→填标题（`input[placeholder*='汉字']`）→填正文（`div.medium-editor-element`）→点发布。

**降级**：Cookie不完整时→Markdown备份到 `~/writing-data/xueqiu-backups/`+日志，cron不报错。

**命令行**：
```bash
python3 publish_to_xueqiu.py --date 2026-05-06 --type daily
python3 publish_to_xueqiu.py --date 2026-05-06 --type weekly
python3 publish_to_xueqiu.py --verify          # 验证Cookie有效性
python3 publish_to_xueqiu.py --cookie-guide     # 打印手动登录指引
```

**日志**：`~/writing-data/publish-logs/YYYY-MM-DD-xueqiu.log`

详见 `references/xueqiu-publishing.md`。

### ❌ 常见陷阱：清洗 markdown 后丢失图表引用

发布流程中如果先清洗 markdown（去除元数据、图表区、`![...](charts/xxx.png)` 引用），再调用图片上传，`process_images()` 会找不到图表引用跳过上传。

**正确顺序**：保留 `md_original`（含图表引用）用于上传，清洗后的 `md_text` 生成 HTML：
```python
md_original = md_text           # 保留原始
md_text = clean_markdown(md_text)  # 清洗
image_map = process_images(date_str, md_original, token)  # 用原始
html = md_to_wechat_html(md_text)        # 用清洗版
html = interleave_images(html, image_map)
```

### ❌ 图表配色修改后不做实际渲染验证 → 报假信号

修改图表配色代码后，不能只看 hex 值/logic 就声称修复完成。必须：
1. 实际运行图表生成脚本
2. 用像素采样或肉眼确认输出PNG颜色正确
3. 确认旧缓存PNG已被覆盖或删除

纯代码逻辑检查 = 假信号。用户不容忍此类"声称修复但实际未验证"的行为。

### ❌ 通用：改完代码就声称"已修复"但未跑管线验证

### ⚠️ 发布协议：IP白名单失效时的降级策略（L3决策点）

**现状（2026-05-10审计）**：服务器IP（113.117.56.38）不在微信公众号IP白名单中，`get_wechat_token()` 持续返回 40164 错误。此状况已持续多日，QQ Bot P0通知已发送。

**降级链（通用，适用于所有文章类型）**：
1. 🟢 **browser_publish.py** — Playwright浏览器自动化 + Cookie鉴权，绕过IP白名单。当前主力方案。详见 `references/wechat-mp-prosemirror-publishing.md`
2. 🟡 **本地HTML保存** — 所有文章类型最终兜底：`~/writing-data/published-html/YYYY-MM-DD-{type}.html`
3. 🔴 发布失败后 **写入QQ Bot通知**（脚本已自动处理）

**科普文章特殊处理**（2026-05-10新增）：
- 区别于复盘文章（使用 `publish_draft.py --type daily|weekly`），科普文章没有 `--type` 参数支持
- 需要独立脚本或手动改为调用 `browser_publish.py` 的通用发布能力
- 降级保存路径：`~/writing-data/published-html/YYYY-MM-DD-科普.html`

### ❌ 科普生成无主题去重 → 同一天生成3篇同标题K线文章

**根因**: `generate_popular.py` 的 `main()` 只做 `title = TOPIC_MAP.get(args.topic)` 然后直接调用 DeepSeek 生成，不检查已有草稿或已发表文章。5月9日同一个 "新手如何看K线？其实搞懂这3根就够了" 标题被生成了3篇（popular-4292/7194/科普-k线）。5月10日 pipeline 又生成第4篇。

**修复 (2026-05-10)**: `generate_popular.py` main() 新增去重层：
1. 扫描 `drafts/` 下所有 `.md` 文件的 `# 标题` 首行
2. 扫描 `published-html/` 下 HTML 的 `<title>` 标签
3. 精确匹配 → 跳过
4. 模糊匹配：标题字符集 overlap ≥6 且相似度 >60% → 跳过
5. 同时更新 `seo-keyword-matrix.md` 标记已发表关键词

### ❌ push_draft() 返回值未检查 → 草稿箱空

`generate_popular.py` 等脚本调用 `push_draft()` 时若不检查返回值，推送失败（token过期/网络瞬断/API限频）时脚本只打印 warning 但 exit_code=0。pipeline verify 检查 `file exists` 通过 → 标记 stage 完成 → 用户到草稿箱发现空的。

**修复**: `push_draft()` 返回 `bool`，调用方必须检查返回值，失败时重试（3次退避 3s/5s/10s）或显式 exit(1) 让 pipeline 感知失败。

**verify 规则升级**: pipeline stage verify 必须覆盖**所有**操作，不止文件存在性。推送类 verify 应检查：`python3 -c "import requests; r=requests.get('https://api.weixin.qq.com/cgi-bin/draft/get', params={'access_token': ...}); assert r.json().get('item_count',0)>0"`

任何涉及渲染、数据采集、API调用的改动，不能只看代码逻辑或语法就报"完成"。必须实际运行目标脚本并验证输出。包括但不限于：

- 图表配色 → 渲染后像素确认
- 数据采集 → 检查连续3天数据是否真不同
- API推送 → 查看草稿箱是否收到

### ❌ `data_collector_seo.py` 硬编码 `is_trading_day: True` → 周日生成虚构复盘

**根因**: `data_collector_seo.py` L423（修复前）无条件设置 `"is_trading_day": True`，无周末/节假日检查。5月10日周日被当作交易日 → Sina/雪球返回代理滞后数据 → AI基于假数据（上证4179点、成交30485亿、涨停134家全是北交所）生成完整的虚构复盘并推送到草稿箱。

**双重故障**:
1. 数据采集层：无交易日门禁，标注 `is_trading_day: True` 后下游全信
2. 内容生成层：`generate_review_seo.py` 不验证 `is_trading_day` 字段

**修复 (2026-05-10)**:
- `data_collector_seo.py`: 新增 `is_trading_day()` 函数（周末+2026节假日），`collect()` 开头门禁，非交易日返回 None
- `generate_review_seo.py`: `generate_review()` 开头检查 `data["is_trading_day"]`，False 直接退出
- 成交额上限从 100000亿→60000亿
- **铁律**: 所有写作管线数据采集脚本必须有交易日门禁，`is_trading_day` 必须是运行时计算值而非硬编码常量

### ❌ 图表 markdown 引用格式不对 → `extract_chart_references()` 不识别 → 图片不上传

**根因**: `publish_draft.py` 的 `extract_chart_references()` 用正则 `!\[.*\]\(charts/.*?\.png\)` 扫描 markdown 文件找图表引用。仅文字提及"（见kline.png）"不会被识别。结果：封面图上传成功，但4张内容图表全部跳过。

**症状**:
```
未找到图表引用，跳过内容图片上传（封面图仍会上传）
✅ HTML已更新 0 张图片引用为微信CDN地址
```

**修复**: 必须在 markdown 中添加标准图片语法：
```markdown
![上证日K线图](charts/kline.png)
```

**每条引用独立一行**，放在对应章节段落之后。不要在文章底部集中放置。

**验证**: 再次推送时输出应显示：
```
发现 N 张图表待上传...
✅ HTML已更新 N 张图片引用为微信CDN地址
```

### ❌ 周总结周涨幅用周一开盘价做基准而非上周五收盘价

**根因**: `weekly_summary.py` 比较周涨幅时从本周一的开盘价开始计算，而非从上周五的收盘价。比如本周三(5/6)开盘4135.45 vs 上周五(4/30)收盘~4112，差距约23点。

**症状**: 周涨幅数据不准确，偏高或偏低。

**修复**: 周涨幅 = (本周五收盘 - 上周五收盘) / 上周五收盘 × 100%。上周五收盘可从前一日数据获取（周三 `prev_close` 字段）或从 stock-sdk-mcp kline API 获取。

### ❌ stock-sdk-mcp 晚间可用但部分接口有限制

**可用接口（已验证 19:00-20:00）**:
- `get_a_share_quotes()` — 指数实时行情 ✅
- `get_market_overview()` — 市场总览（含指数/北向/涨跌停统计）✅
- `get_zt_pool()` / `get_zt_pool(type="dt")` — 涨跌停股池 ✅
- `get_northbound_realtime()` — 北向资金 ✅

**不可用接口**:
- `get_history_kline()` — K线历史 fetch failed
- `get_kline_with_indicators()` — K线+指标 fetch failed
- `get_industry_list()` — 行业列表 fetch failed
- `get_fund_flow_rank()` — 资金流排名 fetch failed

**应对**: 晚间优先用可用接口获取指数+涨停数据。K线数据用本地缓存 `kline_cache.json` 替代。行业/资金流数据标注"晚间不可用"。

### ❌ 2026-05-08: data_completeness 标签在 EastMoney API 全面封锁后仍报告 True

**根因**: 当 `collect_data.py` 中所有东财源（sectors/capital_flow/limit_up_down）因反爬封锁返回空数据时，`_meta.accuracy` 已标注 level=C、source="不可用 (EastMoney封锁)"，但 `data_completeness` 的6个标记**未同步降级**，仍返回 `True`。

**影响**:
- generate_review.py 看到 `completeness=True` → 认为数据完整 → AI生成文章但板块/资金/涨跌停数据全部为0或空
- generate_charts.py 因数据为空跳过 sector_heatmap/capital_flow/volume_compare/sector_rotation → 仅产出 kline+market_breadth
- 用户看到"数据不正确，没有配图"

**修复方向**: `data_completeness` 应读取 `_meta.accuracy[$key].level`，当 level=C 时自动设为 False。

**根因**：`collect_data.py` 中6个 `data_completeness` 标记（indices/sectors/main_force_flow/sector_flow/limit_up_down/up_down_stats）部分原来放在 try/except 块**外部**，无条件设为 `True`。当 API 超时/断连时，except 捕获异常设置空数据，但 completeness 标记仍为 `True`。下游消费方（generate_charts.py、generate_review.py、weekly_summary.py）看到 completeness=True 就认为数据完整，实际 capital_flow={}, sectors.industry=[], limit_up_down={}。

**症状**：
- all_data.json 中 `data_completeness` 全 `True`，但实际 key 全空
- 4张图表只生成2张（kline/market_breadth），缺失的2张因为数据空跳过
- 用户报告"数据不准确""配图不完整"

**修复（2026-05-06, 更新 2026-05-07）**：6个标记全部改为条件判断：
- `indices`: `any(v and v.get("index") for v in data["market"].values())`
- `sectors`: `len(data["sectors"].get("industry", [])) > 0`
- `main_force_flow`: `data["capital_flow"].get("main_force", {}).get("net_inflow") is not None`
- `sector_flow`: `bool(data["capital_flow"].get("sector_flow", {}).get("inflow_top5"))`
- `limit_up_down`: `lu.get("total", 0) > 0 or ld.get("total", 0) > 0`
- `up_down_stats` (新增): `data["up_down_stats"].get("up", 0) > 0`

**验证**：重新采集后 `data_completeness` 空数据维度应为 `false`，而非全 `true`。

### ❌ 封面图 fontname= 不如 FontProperties 稳健 → 跨脚本字体方式不统一

**根因**：`generate_charts.py` 使用 `fontproperties=FontProperties(fname=字体路径)` 直接指定字体文件，是最稳健的方式。但 `publish_draft.py` 的 `create_cover_image()` 使用 `fontname=font_name`（matplotlib fontconfig-based 匹配），当 fontconfig 缓存过期或字体名称匹配失败时，中文可能显示为空格。

**修复（2026-05-06）**：`create_cover_image()` 8处 `fontname=font_name` 全部改为 `fontproperties=fp_chinese/fp_chinese_bold`，并用 `FontProperties(fname=font_path)` 直接指向字体文件路径，与 `generate_charts.py` 保持一致。

**关键代码**：
```python
# ❌ 旧
fm.findfont(fname, fallback_to_default=False)  # fontconfig匹配
ax.text(..., fontname=font_name)

# ✅ 新
fp_test = fm.FontProperties(family=fname)
font_path = fm.findfont(fp_test, fallback_to_default=False)
fp_chinese = FontProperties(fname=font_path)
ax.text(..., fontproperties=fp_chinese)
```

### ❌ avoid-ai-writing 清洗覆盖面严重不足 → 技能标称与实际不符

**背景**：`a-share-content-automation` 技能文档声称集成了 `avoid-ai-writing`（1333⭐）和 `content-creator` 两个社区技能，用于文章去AI化。但实际实现仅：
- Prompt层：system prompt中嵌入20+中文禁用词
- 代码层：`scrub_ai_vocabulary()` 仅覆盖23个Tier1中文词

`avoid-ai-writing` 技能定义的完整能力：Tier1(60+英文词)+Tier2(聚类检测)+Tier3(密度检测)+结构层(段落/句式/EmDash)+Second-pass审计+上下文profile匹配 → **全未实现**。
`content-creator` 的 `seo_optimizer.py` → **从未集成调用**。

**2026-05-06实测**：当天文章漏过的AI痕迹包括"飙升至""领涨全场""从历史经验看""是积极信号""投资者可关注后续数据更新"等。

**参考**：`references/ai-writing-gap-audit-2026-05-06.md` — 完整差距审计+泄露模式清单+升级路线图。

### ❌ 微信API 50002 "user limited" → 无重试导致发布失败

`publish_draft.py` 遇到微信API返回 errcode=50002（user limited，当日配额耗尽/账号限频）时直接降级到本地HTML，不尝试重试。该错误通常是暂时的（数分钟后恢复），加退避重试可大幅提高成功率。

**建议**：`publish_draft.py` 对 50002 错误加指数退避重试（5min→10min→30min，最多3次）。
### ❌ 周总结交易日过滤：`get_week_dates()` 不验实际交易日 → 节假日被当作交易日

**根因**：`weekly_summary.py` 的 `get_week_dates()` 简单返回本周一至周五所有日期，不做交易日历过滤。五一/国庆/春节等长假期间，Mon-Fri 不一定是交易日。`scan_available_data()` 只看 `all_data.json` 是否存在，不验证数据真实性，导致节假日采集的假数据被当作合法交易日纳入周总结。

**修复（2026-05-05）**：
1. 新增 `fetch_trading_calendar()` 函数，调用 AKShare `tool_trade_date_hist_sina()` 获取实际交易日列表（带内存缓存）
2. `get_week_dates()` 遍历 Mon-Fri 时对每个日期做交易日历成员检查，非交易日自动跳过
3. AKShare 不可用时缓存为空集 → 不过滤（降级兼容），配合 `scan_available_data()` 的 ≥3天阈值兜底

**验证**：2026-05-04(Mon)和2026-05-05(Tue)为五一假期非交易日，经过滤后本周实际交易日 = 5/6(Wed)+5/7(Thu)+5/8(Fri) 仅3天。

### ❌ 周总结 AI 输出含"建议"违禁词 → Prompt 约束不够 + 无后处理兜底

**根因**：虽然 prompt 末尾有"全文严禁出现'建议'二字"的约束，但 DeepSeek 等中文写作模型对此类否定指令遵从度不足，仍会输出"操作建议""投资建议""仓位管理建议"等短语。仅靠 prompt 约束不够可靠。**每日复盘（generate_review.py）同样受影响**。

**修复（2026-05-05）**：两层防御纵深（详见 `references/ai-suggestion-ban-defense.md`）
1. **Layer 1 - Prompt加固**：将"建议"禁令从 prompt 末尾提升到数据段**之前**，用"硬性约束（违反则全文无效）"措辞
2. **Layer 2 - 后处理硬拦截**：代码层扫描 → 逐项替换 → 句式替换 → 兜底裸词删除 → 第4节标题校验
3. **已应用到脚本**：`weekly_summary.py` + `generate_review.py`（两个脚本均实现相同后处理链路）

### ❌ 周总结图表路径：图表在交易日目录，引用在end_date目录

`generate_weekly_charts()` 将图表生成到 `CHARTS_DIR/<trading_date>/`（如周五），但 `publish_draft.py` 按 `--date` 参数查找 `CHARTS_DIR/<end_date>/`（如周日），两者不同导致图表引用为空。

**修复**：`weekly_summary.py` 生成图表后自动拷贝到 `CHARTS_DIR/<end_date>/`，`publish_draft.py` 按 `--date` 参数正常查找即可。

### ❌ 周总结 `interleave_images()` 只匹配每日复盘章节标题 → 图上传了但从不插入HTML

`publish_draft.py` 的 `interleave_images()` 章节关键词映射只配了每日复盘的标题（"大盘回顾""资金风向标""热点""技术看盘"），周总结的章节完全不同（"本周行情回顾""最热方向深度分析""下周展望""关注方向"）。结果：图片上传到微信素材库成功，但 `interleave_images()` 永远匹配不到章节标题，图片链接从未插入HTML → 发布后的草稿箱文章无配图。

**修复（2026-05-05）**：
1. `interleave_images()` 新增 `draft_type` 参数
2. `draft_type="weekly"` 时使用周总结专属映射：
   - "本周行情回顾" → kline.png + capital_flow.png（两张）
   - "最热方向" → sector_heatmap.png
   - "下周展望" → market_breadth.png
3. 同章节多图用 `defaultdict(list)` 聚合，一次性插入不覆盖
4. 两处调用点（token成功路径和降级路径）都传 `draft_type`

### ❌ 雪球 import 路径错误 → 3-way交叉验证从未生效（2026-05-07 修复）

**根因**：`collect_data.py` 的 `validate_indices_with_xueqiu()` 从 `~/quant/` import `xueqiu_kline`，但文件实际位于 writing-domain skills 目录内。每次运行抛出 `ImportError` → 返回 `status: "skipped"` → 雪球**从未参与过实际交叉验证**。

**修复（2026-05-07）**：
1. `xueqiu_kline.py` 迁移到 `~/quant/xueqiu_kline.py`（双域共享基础设施）
2. 原位置创建 symlink：`~/.hermes/profiles/writing-domain/.../scripts/xueqiu_kline.py` → `~/quant/xueqiu_kline.py`
3. collect_data.py 的 import 路径无需修改（已指向 `~/quant/`）

**预防**：双域共享模块放在 `~/quant/` 或 `~/tools/`，各域通过 symlink 或 sys.path 访问。模块迁移后验证 import 成功再报"已完成"。

### ❌ 数据采集全量跑在AKShare黑窗期 → 超时300s+卡死

**根因**：东方财富 push2 API 北京时间 19:00-08:00 不可用，每个 `_em` 端点超时30s，collect_data.py 串行调用6+端点累积 >180s 超时。

**应对**：06:00-08:00 期间不跑全量采集，用 `python3 -c "from xueqiu_kline import ..."` 做雪球功能验证即可。全流程端到端测试等到08:00后。

**根因**：雪球 API 用 `error_code: 0` 表示成功，非零表示错误。初次接入误判 `if "error_code" in data` → 把成功当作错误抛出。

**修复**：`if data.get("error_code", 0) != 0` — 显式检查非零。

**影响**：`xueqiu_kline.py` 的 `_api_get()` 方法。

### ❌ browser_publish.py 无法加载页面 → channel='chromium'

**根因**：Ubuntu 24.04 Wayland 环境下 ms-playwright 自带 chromium 无法加载 `mp.weixin.qq.com`（导航超时30s）。snap chromium 可用。

**修复**：脚本双降级 — 先尝试 `channel='chromium'`（snap chromium），失败后回退 ms-playwright。

### ❌ 编辑器页面重定向到登录页 → 用了直接URL跳转

**根因**：编辑器在"新的创作"→"文章"点击后以**新标签popup**形式打开，不能通过 `page.goto(editor_url)` 直接跳转。即使cookie有效，直接URL跳转到 `cgi-bin/appmsg?t=media/appmsg_edit_v2...` 也会被重定向到 `loginpage`。

**修复**：用 `context.expect_page()` 拦截popup：
```python
with context.expect_page() as popup_info:
    page.get_by_text("文章", exact=True).first.click()
editor = popup_info.value
```

### ❌ cookie_publish.py operate_appmsg API已失效

**根因**（2026-05-08确认）：`cgi-bin/operate_appmsg` 的内部草稿创建功能已变更：
- 不带 `sub=create` → `ret=2`（仅列表查询模式）
- 带 `sub=create` → `ret=200002 参数错误`
- `cgi-bin/draft/add`、`cgi-bin/operate_draft` → 404

**当前方案**：浏览器自动化 (`browser_publish.py`) 为唯一可行的非白名单方案。

**根因**：Playwright headless 访问 `/write` → cookie 验证通过✅ → 编辑器可见✅ → 填写成功✅ → 点击 `a.submit__confirm__btn` 被 React 事件拦截。即使非 headless 模式也不生效。雪球 Web 前端有严格的 bot 检测。

**当前方案**：`publish_to_xueqiu.py` 降级保存 Markdown 备份到 `~/writing-data/xueqiu-backups/`，含手动发布指引。

**关键DOM**：标题在 `div.medium-editor-element` 第一行（无独立输入框），需先点"写长文"tab激活。

### ❌ 自行计算数据触发用户严厉纠正

**用户铁律（2026-05-08用户明确纠正）**：所有数字必须来自API原始返回值。禁止自行计算涨跌幅、成交额、涨跌家数、板块热度等任何衍生数据。

**触发场景**：当agent用涨停家数×28推断上涨家数、用上证+深证成交额手动求和代替API返回的合计值、或用个股行情汇总代替官方涨跌家数时，用户会直接纠正。

**正确做法**：
1. 每个数据点必须有明确的数据源标注（`[stock-sdk-mcp]`、`[AKShare]`等）
2. 涨跌家数从 `stock-sdk-mcp get_market_overview()` 的 northbound 里面提取 upCount/downCount（沪股通+深股通），或从 `stock_zh_updown_statistics` 直接读取
3. 合计成交额用API返回的预计算值，不手动加总
4. 多源数据必须交叉验证：关键点位（如上证收盘价）与用户确认核对
5. 数据缺失时如实标注"数据不可用"，绝不自行推断或捏造

### ❌ 涨跌家数推断逻辑捏造数据 — generate_review.py `int(lu*28)` 

**根因**: `generate_review.py` 第71-117行涨跌家数获取逻辑存在严重设计缺陷：
1. 先尝试 `ak.stock_zh_a_spot_em()` 遍历5000+只股票统计涨跌 — 晚间API不可用，白天也慢
2. 失败后进入降级推断：`up_count = int(涨停数 × 28)` — 纯属捏造，无统计依据
3. `down_count = max(int(跌停数 × 15), 500)` — 同样捏造

**2026-05-07实锤**: 涨停99家 → `int(99*28)=2772` 上涨，`int(4*15)=60 → max(60,500)=500` 下跌，`5000-2772-500=1728` 平盘。真实数据为 **3513/1831/161**（Wind含北交所）。

**修复 (2026-05-07)**:
1. **collect_data.py** 新增 `stock_zh_updown_statistics` API 调用，采集真实涨跌家数到 `all_data.json` 的 `up_down_stats` 字段
2. **generate_review.py** 删除全部推断逻辑（-40行），改为从 `data["up_down_stats"]` 直接读取
3. 数据缺失时标记为 -1（由写作prompt如实标注），禁止任何推断

**`up_down_stats` 字段结构**:
```json
{
  "up_down_stats": {
    "up": 3513, "down": 1831, "flat": 161,
    "limit_up": 99, "limit_down": 4,
    "source": "AKShare stock_zh_updown_statistics (东财原始数据)"
  }
}
```

### ❌ publish_draft.py 无图表引用时跳过封面图 → 40007 invalid media_id

**根因**: `process_images()` 在 `extract_chart_references()` 返回空时直接 `return md_text, image_map, None`，连封面图一起跳过。创建草稿时缺少 `thumb_media_id` 导致微信API返回 40007。

**症状**: 文章无内联图表引用时，publish_draft.py 输出 "未找到图表引用，跳过图片上传" → 草稿推送失败 `[40007] invalid media_id`。

**修复 (2026-05-07)**: `process_images()` 重构为封面图独立上传逻辑 — 无论有无内容图表，封面图都必须上传。`if chart_refs:` 分支仅控制内容图片，封面图在分支外独立执行。

### ❌ 图表堆在尾部 → 删除"尾部图表引用"时正文配图也丢失

**根因**: 文章尾部有独立的 "📊 数据图表引用" 和 "📊 数据图表" 段落，用户要求删除尾部引用时一次性清空，导致正文中本应内嵌的图表也被误删。

**约定 (2026-05-07)**: 图表必须内嵌在正文相关段落中（如 capital_flow.png 嵌入"资金风向标" section、volume_compare.png 嵌入"大盘回顾" section），不在尾部设独立图表段。publish_draft.py 的 `interleave_images()` 按章节关键词自动插入。

### ❌ delegate_task 子代理因父会话中断被取消

**症状**: delegate_task 派发长时任务（写作/数据分析）时，子代理做了一半（20+ tool call、800+秒）被中断，status=interrupted。

**原因**: delegate_task 子代理与父会话绑定，用户发新消息 → 父会话上下文切换 → 子代理被取消。

**应对**: 对预期运行时间长的任务（>5分钟），优先使用 **cron job** 而非 delegate_task。cron job 独立运行不受父会话影响。delegate_task 仅用于短时（<3分钟）的查询/修改类任务。

### ❌ 双脚本函数漂移：generate_review.py 有但 weekly_summary.py 缺失 → 运行时崩溃

**根因**：多个 session 中只给 `generate_review.py` 添加了新函数（Tier2/Tier3/结构检测等），但未同步到 `weekly_summary.py`。`weekly_summary.py` 的 `scrub_ai_vocabulary()` 内部调用 `detect_ai_clusters()` 和 `ai_density_score()`，但这些函数在 weekly_summary.py 中未定义。

**症状（2026-05-07 发现）**：语法检查通过但运行时抛出 `NameError`，导致周总结管线静默失败。

**缺失的5个函数**：`detect_ai_clusters()`、`ai_density_score()`、`check_ai_structure()`、`second_pass_audit()`、`post_process_pipeline()`

**预防**：任何 generate_review.py 的函数新增/修改必须同步到 weekly_summary.py。差异审计：`diff <(grep "^def " generate_review.py | sort) <(grep "^def " weekly_summary.py | sort)`

### ❌ Sina 美股 gb_xxx parts[2] 不是涨跌幅 — 必须从 close/prev_close 计算 (2026-05-09 重大修正)

**根因**: `morning_brief.py` 的 `_parse_sina_us_index()` 将 `parts[2]` 作为涨跌幅直接使用。实测验证 Sina 美股全球指数 (gb_dji/gb_ixic/gb_inx) 的 `parts[2]` 是**盘后近似涨跌幅**，与真实涨跌幅差距巨大（DJI: parts[2]=0.02 vs 真实-1.79%）。此外 `parts[8]` 是**昨收价**而非之前误标的"52周最高"。

**实测字段映射 (2026-05-09)**:
- parts[1]=当前价, parts[2]=盘后涨跌幅(勿用!), parts[3]=时间戳, parts[4]=盘后变动额
- parts[5]=今开, parts[6]=最高, parts[7]=最低, parts[8]=昨收

**修复**: 改用 `calc_change_pct(parts[1], parts[8])` 从当前价和昨收价计算涨跌幅。全管线16处自行计算涨跌幅统一替换为 `calc_change_pct()`（shared_utils.py 新增函数）。

**完整映射表**: 详见 `references/sina-api-field-map.md`

### ❌ data_collector_seo.py Sina 成交额单位错误 — parts[9]/10000 得万元不是亿元 (2026-05-09 审计)

**根因**: `data_collector_seo.py` L193 用 `parts[9] / 10000` 并注释 `parts[9]=成交额(万)`，但 Sina A股指数 parts[9] 单位是**元**，不是万元。

**实测验证**: 上证 parts[9]=1331673066131(元)
- `/1e8` = 13316.73 亿 ← collect_data.py 正确用法
- `/10000` = 133167306.61 ← data_collector_seo.py 错误，得到万元但字段名 turnover 应为亿元

**修复**: `parts[9] / 10000` → `parts[9] / 1e8`，注释更正为 `parts[9]=成交额(元)`

### ❌ fallback_pipeline.py Sina 字段映射注释错误 — fields[1]标为"当前价"实为今开 (2026-05-09 审计)

**根因**: `fallback_pipeline.py` L72-74 注释说 `名称,当前,昨收,今开,最高,最低`，但标准映射是 `名称,今开,昨收,收盘,最高,最低`。

**实际映射**:
- fields[1] 标为"当前价" → 实际是**今开**(开盘价)
- fields[3] 标为"今开" → 实际是**收盘价**

**影响**: 盘后差距小(收盘≈今开附近)，盘中差距可能达数十点。返回的"index"(当前价)实际是今开价。

**修复**: 
```python
"index": safe_float(fields[3]),      # 收盘价(当前价)
"prev_close": safe_float(fields[2]), # 昨收
"open": safe_float(fields[1]),       # 今开
```

### ❌ generate_charts.py try块缩进断裂 — SyntaxError L155 (2026-05-09 审计)

**根因**: data_guard 注入时 L155 `df, errors = kline_data(...)` 缩进(4空格)与 L148 `try:` 同级，脱离 try 块，导致 SyntaxError。

**影响**: **所有图表生成不可用**，复盘管线下游全部阻断。py_compile 直接报错。

**修复**: L155-157 改为8空格缩进(在 try 块内部)。

### ❌ safe_float 漂移复发 — 新脚本绕过 shared_utils 本地重新定义 (2026-05-09 审计)

**根因**: `data_collector_seo.py` L34 和 `wechat_auto_reply.py` L33 各自定义了 `def safe_float()`，不从 `shared.shared_utils` 导入。之前的合并已统一7处到 shared_utils，但新增脚本又绕回去了。

**影响**: 修 shared_utils 的 safe_float 时，2个脚本不受影响→不同步。

**修复**: 删除本地定义，改为 `from shared.shared_utils import safe_float`。data_collector_seo.py 还需删除本地 `pct_change` 定义。

**预防**: 新增脚本时必须检查是否已有 shared 版本。data_guard Layer 5 漂移检测应覆盖此场景。

### ❌ 自行计算涨跌幅散落多脚本 — 统一 calc_change_pct() (2026-05-09 审计)

**根因**: 5个脚本中16处自行用 `(close - prev_close) / prev_close * 100` 计算涨跌幅。修改一处时其他遗漏→不一致。与 safe_float 漂移同类问题。

**修复**: `shared/shared_utils.py` 新增 `calc_change_pct(close, prev_close)` 函数，全管线16处替换为统一调用：
- `collect_data.py`: 5处
- `morning_brief.py`: 4处 (含A50 Sina)
- `data_collector_seo.py`: 1处
- `fallback_pipeline.py`: 1处

**预防**: 任何需要计算涨跌幅的地方必须用 `from shared.shared_utils import calc_change_pct`，禁止内联计算。

### ❌ fallback_pipeline.py unconditionally sets data_completeness flag to True when data is empty (L230-233 已修复)

**根因**: `fallback_pipeline.py`（Sina备用管线）在采集不到 sector/flow/limit 数据时，将4个 `data_completeness` 标志设为 `True`:
```python
data["data_completeness"]["sectors"] = True          # ← 实际sectors为空
data["data_completeness"]["main_force_flow"] = True  # ← 实际capital_flow为空
```
但 `_meta` 字段已正确标注 "C级/不可用"。下游脚本读 `data_completeness=True` 以为数据完整。

**修复 (2026-05-08)**: 4处 `True` → `False`

**验证**: 修复后 `all_data.json` 的 `data_completeness` 与 `_meta.accuracy` 一致。

### ❌ matplotlib .ttc 字体渲染失败 → 图表中文显示为方框/空格  

**根因**: `generate_charts.py` 和 `fallback_pipeline.py` 的 `setup_chinese_font()` 通过 font_manager name 匹配，但 `.ttc` TrueType Collection 文件 fontconfig 解析不稳定。rcParams `font.sans-serif` 对 .ttc 字体可能不生效，产生 "Glyph missing from font(s) DejaVu Sans" 警告。

**修复 (2026-05-08)**: 两脚本改为按文件路径直接查找 + `FontProperties(fname=path)`:
```python
font_candidates = [
    ("WenQuanYi Zen Hei", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    ("AR PL UMing CN",     "/usr/share/fonts/truetype/arphic/uming.ttc"),
    ...
]
for name, fpath in font_candidates:
    if Path(fpath).exists():
        font_path = fpath; break

fp = FontProperties(fname=font_path, size=12)
ax.set_title("标题", fontproperties=fp)
```
所有 `set_title/set_xlabel/set_ylabel/suptitle/legend.text` 必须传入 `fontproperties=`

### ❌ fallback_pipeline.py 缺少 up_down_stats 字段 → 涨跌家数显示-1

**根因**: Sina管线只采集指数K线和个股行情，未计算涨/跌/平盘家数。`all_data.json` 的 `up_down_stats` 字段缺失，`generate_review.py` 读到-1。

**修复 (2026-05-08)**: 从 `fetch_a_share_spot()` 返回的个股 `changepercent` 字段统计算法家数:
```python
up = sum(1 for s in stocks if safe_float(s.get("changepercent")) > 0)
down = sum(1 for s in stocks if safe_float(s.get("changepercent")) < 0)
data["up_down_stats"] = {"up": up, "down": down, "flat": flat, ...}
```

**根因**：`quant_weekly.py` 为了 cron 可靠性（避免循环导入）内联了一份 `scrub_ai_vocabulary()`，但该副本不包括 Tier2/Tier3 检测（`detect_ai_clusters()`、`ai_density_score()`），只做了 Tier1 替换+正则模式。

**当前状态（2026-05-07）**：
- `weekly_summary.py` `scrub_ai_vocabulary()` = Tier1(110词)+Tier2(聚类)+Tier3(密度)，返回 `(content, count, warnings)`
- `quant_weekly.py` `scrub_ai_vocabulary()` = Tier1(110词)+正则模式，返回 `(content, count, [])`
- `generate_review.py` `scrub_ai_vocabulary()` = 独立实现

**预防**：三份 `scrub_ai_vocabulary()` 的 Tier1 词表必须保持同步。任何一处修改替换词表，需要检查另外两处。建议未来重构为共享模块 `~/writing-data/shared/scrubber.py`。


### ❌ `requests.post(url, json=body)` 中文变 Unicode

**根因**: `requests.post(url, json=body)` 内部调用 `json.dumps(body, ensure_ascii=True)`，中文被转义为 `\\uXXXX`。WeChat API 当作字面文本存储。

**修复**（3个脚本已全部应用）:
```python
# ❌ 旧写法
resp = requests.post(url, params=..., json=body, timeout=30)

# ✅ 新写法
body_json = json.dumps(body, ensure_ascii=False)
resp = requests.post(
    url,
    params=...,
    data=body_json.encode("utf-8"),
    headers={"Content-Type": "application/json; charset=utf-8"},
    timeout=30
)
```

**硬防线**（publish_draft.py `push_to_wechat_draft` 函数，运行前检测）:
```python
body_json = json.dumps(body, ensure_ascii=False)
if "\\u" in body_json:
    print("❌ 致命: JSON序列化含unicode转义，拒绝发送")
    return None
```
序列化后立即扫描 `\u` 转义符。任何原因（代码回退/Python版本差异）导致中文变unicode转义都会被拦截，不再静默发送损坏内容到草稿箱。

**影响脚本**: `publish_draft.py` (微信草稿API), `generate_review.py` (DeepSeek API), `weekly_summary.py` (DeepSeek API)

### ❌ 标题截取导致预览不完整

旧代码在 `push_to_wechat_draft()` 中预截取标题和摘要：
```python
safe_title = title[:15] + "…" if len(title) > 15 else title
safe_digest = digest[:14] + "…" if len(digest) > 14 else digest
```

微信API限制为 title≤64字符、digest≤120字节，正常标题不会超限。预截取反而导致标题被腰斩。已移除截取逻辑，直接传原文，由API自行拒绝超长内容。

### ❌ 涨停/跌停数据结构变更：list → {total, samples}

`collect_data.py` 输出的 `limit_up`/`limit_down` 字段可能为**两种格式**：
1. `[{name, code, ...}, ...]` — 旧格式，直接列表
2. `{"total": 58, "samples": [{name, code, ...}, ...]}` — 新格式，含总数

`weekly_summary.py` 的 `aggregate_weekly_data()` 已适配两种格式：
```python
limit_up_raw = data.get("limit_up_down", {}).get("limit_up", {})
limit_up = limit_up_raw.get("samples", []) if isinstance(limit_up_raw, dict) else limit_up_raw
```
若该函数报 `AttributeError: 'str' object has no attribute 'get'`，检查 `all_data.json` 中的 `limit_up` 字段格式。

### ❌ 周总结交易日过滤：`get_week_dates()` 不验实际交易日 → 节假日被当作交易日

**根因**：`weekly_summary.py` 的 `get_week_dates()` 简单返回本周一至周五所有日期，不做交易日历过滤。五一/国庆/春节等长假期间，Mon-Fri 不一定是交易日。`scan_available_data()` 只看 `all_data.json` 是否存在，不验证数据真实性，导致节假日采集的假数据被当作合法交易日纳入周总结。

**修复（2026-05-05）**：
1. 新增 `fetch_trading_calendar()` 函数，调用 AKShare `tool_trade_date_hist_sina()` 获取实际交易日列表（带内存缓存）
2. `get_week_dates()` 遍历 Mon-Fri 时对每个日期做交易日历成员检查，非交易日自动跳过
3. AKShare 不可用时缓存为空集 → 不过滤（降级兼容），配合 `scan_available_data()` 的 ≥3天阈值兜底

**验证**：2026-05-04(Mon)和2026-05-05(Tue)为五一假期非交易日，经过滤后本周实际交易日 = 5/6(Wed)+5/7(Thu)+5/8(Fri) 仅3天。

### ❌ 周总结 AI 输出含"建议"违禁词 → Prompt 约束不够 + 无后处理兜底

**根因**：虽然 prompt 末尾有"全文严禁出现'建议'二字"的约束，但 DeepSeek 等中文写作模型对此类否定指令遵从度不足，仍会输出"操作建议""投资建议""仓位管理建议"等短语。仅靠 prompt 约束不够可靠。**每日复盘（generate_review.py）同样受影响**。

**修复（2026-05-05）**：两层防御纵深（详见 `references/ai-suggestion-ban-defense.md`）
1. **Layer 1 - Prompt加固**：将"建议"禁令从 prompt 末尾提升到数据段**之前**，用"硬性约束（违反则全文无效）"措辞
2. **Layer 2 - 后处理硬拦截**：代码层扫描 → 逐项替换 → 句式替换 → 兜底裸词删除 → 第4节标题校验
3. **已应用到脚本**：`weekly_summary.py` + `generate_review.py`（两个脚本均实现相同后处理链路）

### ❌ 周总结图表路径：图表在交易日目录，引用在end_date目录

`generate_weekly_charts()` 将图表生成到 `CHARTS_DIR/<trading_date>/`（如周五），但 `publish_draft.py` 按 `--date` 参数查找 `CHARTS_DIR/<end_date>/`（如周日），两者不同导致图表引用为空。

**修复**：`weekly_summary.py` 生成图表后自动拷贝到 `CHARTS_DIR/<end_date>/`，`publish_draft.py` 按 `--date` 参数正常查找即可。

### ❌ 周总结 `interleave_images()` 只匹配每日复盘章节标题 → 图上传了但从不插入HTML

`publish_draft.py` 的 `interleave_images()` 章节关键词映射只配了每日复盘的标题（"大盘回顾""资金风向标""热点""技术看盘"），周总结的章节完全不同（"本周行情回顾""最热方向深度分析""下周展望""关注方向"）。结果：图片上传到微信素材库成功，但 `interleave_images()` 永远匹配不到章节标题，图片链接从未插入HTML → 发布后的草稿箱文章无配图。

**修复（2026-05-05）**：
1. `interleave_images()` 新增 `draft_type` 参数
2. `draft_type="weekly"` 时使用周总结专属映射：
   - "本周行情回顾" → kline.png + capital_flow.png（两张）
   - "最热方向" → sector_heatmap.png
   - "下周展望" → market_breadth.png
3. 同章节多图用 `defaultdict(list)` 聚合，一次性插入不覆盖
4. 两处调用点（token成功路径和降级路径）都传 `draft_type`

### ❌ `requests.post(url, json=body)` 中文变 Unicode

## 合规红线

### 强制要求
1. **AIGC标识**：每篇文章末尾标注"AI辅助创作"
### 数据准确性 — 防AI幻觉机制

**核心原则**：AI只在Prompt中直接使用已提供的数据值，不做任何计算或估算。

**机制1：预计算派生值**
- 采集层（collect_data.py）需预先计算好AI可能自行推导的数据，如：`total_turnover`（上证+深证成交额合计）
- AI Prompt中只引用预计算值，不要求AI做加法/减法/百分比转换

**机制2：标注数据时效性**
- Prompt数据中所有金额/数值均为当日精确值
- 主力资金数据为实时数据，无延迟

**机制3：去除模糊措辞**
- Prompt数据中不得使用"约"/"近"/"超"等模糊限定词 — 所有数字均为精确值
- 例：❌ "两市合计成交额约XXX亿" → ✅ "两市合计成交额: XXX亿"

**机制4：系统级Anti-Hallucination指令**
- 每条AI生成Prompt的约束区必须包含：
  ```
  ⚠️ 数字准确性（关键！）：以上所有数据中的金额（成交额、资金净流入等）、涨跌幅、家数均为精确数值，AI只需直接使用这些数据撰写文章。严禁自行计算、估算或编造任何数字。文章中出现的每一个数据（包括但不限于成交额、涨跌幅、家数、点位）必须能在上文数据中找到对应来源。
  ```

**机制5：降级方案不依赖AI**
- AI API不可用时的降级方案（generate_fallback_report / generate_fallback_weekly）直接使用数据模板，不含任何AI生成内容
- 降级方案同样遵守"只引用不计算"原则

### 质量标准
- 数据准确率：100%（零错误）
- 文章结构：严格按模板执行
- 内容原创性：避免直接复制公开研报内容
- 发布时间：每日17:00前完成草稿箱同步

### 域边界
- 不做预测分析（仅复盘当日行情）
- 不生成个股推荐
- 不包含量化策略细节

---

## 数据目录结构

```
~/writing-data/
├── raw/                 # 原始数据
│   └── YYYY-MM-DD/
│       └── all_data.json
├── charts/              # 分析图表（新增）
│   └── YYYY-MM-DD/
│       ├── kline.png
│       ├── sector_heatmap.png
│       ├── capital_flow.png
│       ├── market_breadth.png
│       ├── volume_compare.png
│       └── sector_rotation.png
├── analysis/            # 分析报告
│   └── YYYY-MM-DD-analysis.md
├── drafts/              # 复盘文章/周总结草稿
│   ├── YYYY-MM-DD-每日复盘.md
│   ├── YYYY-MM-DD-周总结.md
│   └── YYYY-MM-DD-量化周报.md
├── quant-weekly-archive/  # 量化周报快照（供周度对比）
│   └── YYYY-MM-DD-snapshot.json
└── publish-logs/        # 发布日志
    ├── YYYY-MM-DD-publish.log
    ├── YYYY-MM-DD-weekly-analysis.log
    └── YYYY-MM-DD-quant-weekly.log
```

---

## 成本结构

| 项目 | 工具/服务 | 成本 |
|------|-----------|------|
| 数据采集 | AKShare | 免费 |
| 量化分析 | signal_engine.py / pandas | 免费 |
| AI写作 | 通义千问 / DeepSeek | 免费（有额度） |
| 草稿箱同步 | 微信公众号API | 免费 |
| 通知推送 | WeChat iLink | 免费 |
| **合计** | | **0元** |

---

## 多平台交叉验证（v6 — 2026-05-07 雪球三源完整）

每次数据采集后自动执行多平台比对，确保数据准确性。

### 验证流程（5步）

| 步骤 | 函数 | 作用 |
|:--|:--|:--|
| 1 | `validate_indices_with_sina()` | Sina vs AKShare 指数对比（收盘价/涨跌幅/成交额） |
| 2 | `validate_sectors_with_sina()` | Sina vs AKShare 行业板块对比 |
| 3 | `validate_indices_with_xueqiu()` | 雪球 vs AKShare 指数对比（第三数据源，晚间可用） |
| 4 | `fill_indices_from_xueqiu()` 🆕 | 雪球→AKShare 反向自动填充（AKShare缺失时用雪球补全） |
| 5 | `validate_xueqiu_vs_sina()` 🆕 | 雪球 vs Sina 直接对比（双独立源互相校验，阈值 0.5%） |

### 验证维度

| 数据维度 | 主源 | 验证源 | 偏差阈值 |
|:--|:--|:--|:--|
| 大盘指数（收盘价/涨跌幅/成交额） | AKShare `stock_zh_index_daily_em` | Sina `hq.sinajs.cn` + **雪球 `stock.xueqiu.com`** | 涨跌幅差 >0.05%=minor, >0.5%=mismatch |
| 行业板块涨跌幅 | AKShare `stock_board_industry_name_em` | Sina 行业板块 API | 涨跌幅差 >1.0%=discrepancy |

### 自动修复

当 AKShare 指数数据缺失时（晚间东财 push2 API 不可用），自动从雪球回填。填充结果写入 `all_data.json` 的 `_cross_validation` 字段：

```json
{
  "_cross_validation": {
    "indices": { "source": "Sina Finance", ... },
    "sectors": { ... },
    "xueqiu": { "source": "Xueqiu", ... },
    "xueqiu_vs_sina": { "source": "Xueqiu vs Sina cross-check", ... }
  }
}
```

### 实现函数

- `validate_indices_with_sina(date_str, our_data)` — Sina 指数交叉验证
- `validate_sectors_with_sina(date_str, our_sectors)` — Sina 板块交叉验证
- `validate_indices_with_xueqiu(date_str, our_data)` — 雪球指数交叉验证（晚间可用）
- **`fill_indices_from_xueqiu(date_str, data, xq_validation)`** 🆕 — 当 AKShare 返回 index=0/change_pct=0 时，自动从雪球快照回填 close/open/high/low/turnover
- **`validate_xueqiu_vs_sina(sina_validation, xq_validation)`** 🆕 — 雪球 vs 新浪直接对比，逐项校验四大指数

所有函数在 `collect_data.py` 的保存前自动调用。详见 `references/cross-validation-design.md`。

## collect_data.py 2026-05-08 重构：stock-sdk + Sina 一等源

**背景**：EastMoney 对当前服务器 IP 执行了全面反爬封锁（push2/push2his 全部端点返回空响应，exit=52），所有 `ak.stock_*_em()` 均不可用。这不是晚间黑窗，是硬封锁，持续多日未恢复。

**改动范围**：`~/writing-data/scripts/collect_data.py`

### 数据源优先级链

```
stock-sdk.getSimpleQuotes (腾讯 qt.gtimg.cn ✅)
  └─ Sina hq.sinajs.cn (✅ 大盘指数)
    └─ stock-sdk.getAllAShareQuotes (✅ 全A涨跌家数+涨跌停)
      └─ stock-sdk.getHistoryKline (⚠️ 晚间接通)
        └─ AKShare stock_*_em (❌ 东财封锁，30s超时保护)
```

### 具体改动

| 维度 | 改前 | 改后 |
|------|------|------|
| 大盘指数 | MySQL(死路)→AKShare→Sina验证 | **Sina hq.sinajs.cn主采** → stock-sdk → AKShare兜底(30s超时) |
| 涨跌家数 | AKShare updown_statistics(超时→空) | **stock-sdk getAllAShareQuotes统计** ✅ 已验证3201/1617/120 |
| 涨跌停 | AKShare zt_pool_em(超时→空) | **stock-sdk涨跌幅≥9.5%估算** ✅ 已验证124涨停/3跌停 |
| 板块/资金流 | AKShare直调(超时→脚本卡死) | **subprocess 30s超时保护** → 失败标注C级不可用 |
| 交易日判断 | AKShare get_index_daily(超时→误判) | **stock-sdk getSimpleQuotes** + 工作日兜底(Weekday→视为交易日) |

### stock-sdk 采集器 (scripts/stock_sdk_collector.js)

`collect_data.py` 通过 `subprocess.run(['node', '/tmp/stock_sdk_collector.js'])` 调用：

```python
import subprocess, json
env = os.environ.copy()
env["NODE_PATH"] = "/home/pebynn/.hermes/node/lib/node_modules"
r = subprocess.run(
    ["node", "/tmp/stock_sdk_collector.js"],  # collect_data.py L63 hardcodes /tmp/
    capture_output=True, text=True, timeout=120, env=env
)
```

**⚠️ /tmp/ 路径脆弱性**: `collect_data.py`（L63）硬编码为 `/tmp/stock_sdk_collector.js`，但源文件实际在 skill 目录 `~/.hermes/skills/finance/a-share-content-automation/scripts/stock_sdk_collector.js`。`/tmp/` 重启即清空，每次服务器重启后需手动恢复:
```bash
cp ~/.hermes/skills/finance/a-share-content-automation/scripts/stock_sdk_collector.js /tmp/
```
缺失症状: `collect_data.py` 输出 `⚠️ stock-sdk 采集器未找到: /tmp/stock_sdk_collector.js`，涨跌家数和涨跌停数据全部缺失（up_down_stats={}）。
data = json.loads(r.stdout)
# data.up_down_stats: {up, down, flat, limit_up, limit_down}
# data.limit_stocks: {limit_up: {total, samples}, limit_down: {total, samples}}
```

### AKShare 超时保护模式

所有仍保留的 AKShare 调用必须包装在 `subprocess.run(..., timeout=30)` 中，防止东财端点挂死整个脚本：

```python
_r = subprocess.run(
    [sys.executable, "-c", """
import akshare as ak, json
try:
    df = ak.stock_board_industry_name_em()
    # ... process data ...
    print("OK:" + json.dumps(result))
except Exception as e:
    print("FAIL:" + str(e))
"""],
    capture_output=True, text=True, timeout=30
)
if "OK:" in _r.stdout:
    data = json.loads(_r.stdout.split("OK:",1)[1])
```

### 交易日判断回退链

```python
# 方法1: stock-sdk getSimpleQuotes(15s) → 有行情=交易日
# 方法2: AKShare交易日历 → 确认是交易日
# 方法3: 工作日兜底 → Mon-Fri 默认视为交易日
from datetime import datetime as _dt
d = _dt.strptime(date_str, "%Y-%m-%d")
if d.weekday() < 5:  # Mon=0, Fri=4
    is_trading = True
```

### 审计铁律（2026-05-08 教训）

当审计脚本是否需要调整时，不能只看 SQL 查询和函数调用链。
必须 **trace 每个数据值到它的最终 API 端点**，验证该端点当前是否可用。
SQL 表里可能有数据，但如果脚本写死了通过 AKShare 采集，SQL 表再新也没用。

## ⚠️ Known Limitations (2026-05-08 Audit)

This skill (82KB + 46 reference files) has grown beyond usefulness. Core problems:

1. **Function drift** — `safe_float()` defined independently in 7 scripts, `scrub_ai_vocabulary()` in 3 with different implementations. Same bug fixed in one script, missed in others.
2. **No data contract** — Pipeline runs regardless of data quality (sectors=false → still generates review with missing data)
3. **No chart gate** — publish_draft proceeds even with 0/4 charts uploaded
4. **No content cross-validation** — Article numbers never checked against source data

**Full audit**: `references/pipeline-root-cause-audit-2026-05-08.md`

**Architecture fix**: See `data-accuracy-layer` skill for the proposed `data_guard.py` solution.

### 工具链
- `terminal` — Cron任务执行
- `write_file` — 文章保存
- `send_message` — 微信通知

### 域配置
- `writing-domain` — A股写作域（profiles目录）
  - `a-share-data-collector` — 数据采集技能
  - `a-share-review-writer` — 写作技能
  - `a-share-publisher` — 发布技能

---

## 验证清单

### 每日复盘验证
- [ ] 15:30数据采集完成，raw目录有数据
- [ ] 量化分析生成，analysis目录有报告
- [ ] 复盘文章生成，drafts目录有md文件
- [ ] 草稿箱同步成功，publish-logs有日志
- [ ] 18:00微信通知送达

### 周总结验证
- [ ] 扫描本周数据，至少3个**实际交易日**（经交易日历过滤，非简单Mon-Fri）
- [ ] 识别出热门前三板块，有评分+数据支撑
- [ ] 周总结文章生成，字数1800-2800字
- [ ] 标题格式：【本周热门】板块名领涨，下一周怎么看？
- [ ] 第4节标题为"关注方向"，全文无"建议"二字（验证后处理日志）
- [ ] 图表生成传了 `--weekly` 参数，标题含"本周"前缀
- [ ] 草稿箱同步成功（自动），publish-logs有日志
- [ ] **图片验证**：`python3 publish_draft.py --date YYYY-MM-DD --type weekly` — 确认输出含 "✅ HTML已更新 4 张图片引用为微信CDN地址"
- [ ] **图片验证**：`python3 publish_draft.py --date YYYY-MM-DD --type weekly` — 确认输出含 "✅ HTML已更新 4 张图片引用为微信CDN地址"

---

## 故障排查

**⚠️ 当管线出现多个串联bug/用户说"越修越乱"时，先运行全貌审计再动手。** 详见 `references/pipeline-health-audit.md` — 5维度审计清单（cron状态/脚本完整性/数据目录/输出质量/端到端干跑）。

**⚠️ 晚间API黑窗**：东方财富 push2/push2his API 北京时间 19:00-08:00 不可用（RemoteDisconnected / Empty reply）。此时所有 `_em` 后缀 AKShare 端点均超时。应对：Sina 备用数据源（见 `references/sina-fallback-data-source.md`）+ 图表缓存优先 + 30s 超时保护。cron 已配置在15:30，正常不会触发。

**⚠️ 零散修补陷阱**：不要每次只修一个bug然后声称"完成"。用户会说"越修越乱"。正确做法：
1. 先跑全管线语法检查 + 导入测试（5个脚本）
2. 跑一次端到端干跑（collect→charts→review→publish，用历史交易日数据）
3. 确认所有步骤通过后再汇报
4. 任何渲染相关改动（图表配色/封面图）必须实际运行生成并确认输出

**问题：周总结未生成**
- 检查：本周交易日是否<3个？→ 正常跳过
- 检查：raw目录数据是否完整？→ 重新采集
- 检查：Cron任务是否运行？→ 查看cron日志

**问题：周总结发布了但无配图**
- 检查：`publish_draft.py` 是否用 `--type weekly`？→ 必须指定
- 根因：旧版 `interleave_images()` 只匹配每日复盘章节标题（"大盘回顾"等），不识别周总结章节（"本周行情回顾"等）→ 图传了但不插入HTML
- 修复：已写入代码（2026-05-05），`interleave_images()` 现支持 `draft_type="weekly"`，使用周总结专属章节映射
- 验证：`python3 publish_draft.py --date YYYY-MM-DD --type weekly` → 查看输出是否有 "✅ HTML已更新 N 张图片引用为微信CDN地址"

**问题：微信通知未送达**
- 检查：WeChat iLink gateway是否运行？→ `systemctl restart hermes-weixin-gateway`
- 检查：session是否过期？→ 重新扫码登录
- 检查：cron任务deliver配置？→ 确认`deliver: weixin:xxx`

**问题：微信草稿箱发布失败（40164 / 61004）**
- 检查：服务器IP是否在公众号IP白名单？→ `python3 publish_draft.py --check-ip`
- 检查：WECHAT_APP_SECRET是否正确？→ `grep WECHAT_APP_SECRET ~/.hermes/.env`
- 检查：token是否过期？→ 脚本自动缓存+刷新，手动删除 `~/.hermes/credentials/wechat_access_token.json` 强制刷新

**问题：数据不准确**
- 检查：AKShare数据源是否异常？→ 检查 `_cross_validation` 字段，Sina备用源自动修复
- 检查：日期格式是否一致？→ 统一astype(str)
- 检查：parquet列类型是否统一？→ 读取后强制转换
- 晚间19:00-08:00 AKShare 全部不可用，这是正常现象，等待开盘

**问题：图表中文显示为空格/方框**
- 致命陷阱：系统安装的 `.ttc` 字体 matplotlib 无法渲染 → 提取为单 `.ttf`（见 `references/chinese-font-rendering.md`）
- 验证方法：像素密度检测只用 RGB 通道 `arr[:,:,:3]`，RGBA 会永久返回 0%
- `publish_draft.py` 封面图必须用 `fontproperties=FontProperties(fname=...)`，禁止 `fontname=`

---

## 参考文件

- `references/article-templates.md` — 文章模板（每日复盘+周总结）
- `references/cron-schedule.md` — Cron任务配置示例
- `references/data-collection.md` — 数据采集协议
- `references/writing-to-quant-import-pattern.md` — 🆕 Writing域→quant库跨域导入规范（sys.path.insert + data_common 优雅降级）
- `references/anti-hallucination-mechanisms.md` — 5道防AI幻觉防线：预计算→精确注入→系统指令→时效标注→降级方案
- `references/akrake-pitfalls.md` — AKShare API坑点：北向→主力资金切换、日期格式、列名、涨跌停过滤、hist端点非全历史陷阱
- `references/quant-weekly-architecture.md` — 🆕 量化周报架构文档：数据源优先级/7章节结构/跨脚本依赖/设计决策（quant_weekly.py）
- `references/dual-domain-shared-infrastructure.md` — 双域共享基础设施模式（xueqiu_kline 提升到 ~/quant/ 供双域共用）
- `references/akshare-evening-fallback.md` — 🆕 AKShare push2 API晚间不可用 + Sina财经兜底方案（18:00-08:00）
- `references/akshare-endpoint-coverage.md` — AKShare各端点实测数据覆盖范围（2026-05-05实测），含已验证可用/A级的端点清单
- `references/data-collection-pitfalls.md` — 数据采集致命陷阱：iloc[-1]取最新、非交易日校验、实时端点无历史、涨跌停双格式
- `references/data-source-comparison.md` — A股数据源全面对比：AKShare/Tushare/Baostock/Adata/付费方案，资金流向历史替代方案
- `references/limit-stock-filtering.md` — 涨跌停数据过滤规则（北交所/IPO/ST/退市排除）+ 验证案例
- `references/wechat-draft-api-limits.md` — 微信草稿箱API字段限制与错误码
- `references/browser-publishing.md` — 🆕 浏览器自动化发布微信草稿（Playwright+ProseMirror)+base64图片内嵌+按章节插入+去元数据（2026-05-08验证）
- `references/chinese-font-rendering.md` — matplotlib/mplfinance 中文字体渲染修复方案（含 .ttc→.ttf 提取）
- `references/seo-content-optimization.md` — SEO内容优化管线：标题公式/搜一搜关键词/关注转化钩子/轻量数据采集器/小绿书短内容（2026-05-09新增）
- `references/qq-notification-pattern.md` — QQ通知共享模块：notify_utils.py + 写作质量审计清单（2026-05-10）

---

## AKShare API参考

完整API坑点与修复方案见 `references/akshare-pitfalls.md`，以下是关键摘要：

- 大盘指数：`stock_zh_index_daily_em`（有amount+volume列）
- **板块历史日K线：`stock_board_industry_hist_em(symbol="板块名")`** — 替代 `stock_board_industry_name_em()`，支持按日期过滤出当日/某历史日板块涨跌幅
- 概念板块历史：`stock_board_concept_hist_em(symbol="概念板块名")` — 同上模式
- 涨跌幅公式：`(close - prev_close) / prev_close * 100`
- 北向资金：`stock_hsgt_hist_em(symbol="北向资金")`，列名 `当日成交净买额`
- 涨停：`stock_zt_pool_em(date="YYYYMMDD")`
- 跌停：`stock_zt_pool_dtgc_em(date="YYYYMMDD")`
- 板块名称列表：`stock_board_industry_name_em()`

---

### Cron冲突预防（扩展 — 2026-05-09 新增SEO管线）

新增两条SEO管线cron，与现有采集管线独立运行：
- **15:10** — SEO复盘生成 (8aa4c853cff3)：`data_collector_seo.py`轻量采集 → `generate_review_seo.py`AI写作 → 自动推公众号草稿箱
- **15:15** — 小绿书短内容 (108ce7535e38)：`data_collector_seo.py`同源采集 → `generate_short_posts.py`提取亮点 → 自动推公众号草稿箱

**时间线冲突检查**：15:10/15:15 与 14:45(资金流预采集)、15:30(原数据采集) 不冲突。`all_data_fresh.json` 独立文件名，不覆盖原 `all_data.json`。

**SEO优化详情**：详见 `references/seo-content-optimization.md`。

## 实际可执行脚本（2026-05-07 含审核守门员）

writing-domain 7个脚本均可独立运行：

> ⚠️ **路径标准化 (2026-05-08)**: 所有脚本已统一迁移至 `~/writing-data/scripts/`。原 skill 子目录 (`skills/a-share-xxx/scripts/`) 不再使用。

| 脚本 | 标准化路径 | 功能 |
|:-----|:-----|:-----|
| generate_review_seo.py 🆕 | `~/writing-data/scripts/` | SEO优化版复盘：情绪钩子标题+搜一搜关键词+CTA关注引导（副本，不改原脚本） |
| generate_short_posts.py 🆕 | `~/writing-data/scripts/` | 小绿书短内容：从数据提取5类亮点→3-5条短图文→不占群发 |
| morning_brief.py | `~/writing-data/scripts/` | 盘前早报：隔夜外盘+新闻+昨日复盘→模板化生成300-500字→推微信草稿箱（零AI成本） |
| collect_data.py | `~/writing-data/scripts/` | 采集大盘/板块/资金流/涨跌停 |
| generate_charts.py | `~/writing-data/scripts/` | 🔧 生成6张分析图表（4基础+2动态）。**shebang**: `#!/home/pebynn/tools/quant_env/bin/python3`（quant_env 含 matplotlib/pandas） |
| generate_review.py | `~/writing-data/scripts/` | 读数据→图表→DeepSeek生成复盘→后处理管线 |
| audit_guard.py | `~/writing-data/scripts/` | 🔧 审核守门员（统一核心）：合规+数据准确性+AI味+格式质量→四维审计 |
| publish_audit_guard.py | `~/writing-data/scripts/` | 轻量wrapper：import audit_guard() + --auto-publish开关（原 publisher/audit_guard.py 重命名） |
| publish_draft.py | `~/writing-data/scripts/` | 发布管线入口：审核→发布。`--strict`阻止WARN，`--audit-only`仅审核 |
| weekly_summary.py | `~/writing-data/scripts/` | 周热点识别+深度周总结→自动推草稿箱 |
| quant_weekly.py | `~/writing-data/scripts/` | 量化周报：多因子信号+缠论二买+主力资金+行业轮动+风险预警，1200-1800字 |
| publish_to_xueqiu.py | `~/writing-data/scripts/` | 雪球长文发布。Cookie认证，`--type daily|weekly` |
| cookie_publish.py | `~/writing-data/scripts/` | 🍪 Cookie直连 API 发布（绕过IP白名单，publish_draft.py 降级依赖） |
| browser_publish.py 🆕 | `~/writing-data/scripts/` | 🌐 浏览器自动化发布 (Playwright+ProseMirror): Cookie鉴权→popup编辑器→base64图片内嵌→保存草稿。已接入L3降级链 |
| fallback_pipeline.py 🆕 | `~/writing-data/scripts/` | 🔄 Sina备用管线 (EastMoney封锁自动切换): 采集指数+K线缓存+个股行情+图表生成。2026-05-10 新增雪球fallback |
| data_collector_seo.py 🆕 | `~/writing-data/scripts/` | 📡 轻量实时采集(Sina+stock-sdk+交叉验证)，SEO管线专用 |
| stock_sdk_client.py 🆕 | `~/writing-data/scripts/shared/` | 🔌 MCP JSON-RPC桥接：通过子进程调用stock-sdk MCP Server，供standalone cron脚本使用。导出 fetch_us_indices/fetch_hang_seng/fetch_a50_futures |
| weekend_deep_dive.py 🆕 | `~/writing-data/scripts/` | 周末深度图文：周度叙事+量化信号+消息面+前瞻 → 2500-3500字 → 公众号草稿箱。周六10:00自动运行 |
| generate_short_posts.py 🆕 | `~/writing-data/scripts/` | 📱 小绿书短内容(从数据提取3-5亮点→图文→自动推草稿箱) |
| generate_popular.py 🆕 | `~/writing-data/scripts/` | 📖 理财科普系列(AI写作→封面图→推草稿箱)。用法: `--topic 新手亏钱`, `--no-push`, `--dry-run`。支持8个预设选题(Topic Map)。详见 `references/finance-popularization-pipeline.md` |
| pipeline_health_check.py | `~/writing-data/scripts/` | 管线健康检查：7维26项自动化验证 |
| pipeline_health_check.py | `~/writing-data/scripts/` | 管线健康检查：7维26项自动化验证 |
| validate_wechat_api.py | `~/writing-data/scripts/` | 微信API全链路健康检查（保留在原位） |
| xueqiu_kline.py | `~/quant/xueqiu_kline.py` | 雪球K线+实时行情API（双域共享基础设施） |

```bash
# 全管线一键运行（含审核守门员）— 脚本路径 2026-05-08 标准化
python3 ~/writing-data/scripts/collect_data.py --date 2026-05-05
python3 ~/writing-data/scripts/generate_charts.py --date 2026-05-05
python3 ~/writing-data/scripts/generate_review.py --date 2026-05-05

# 审核守门员 (发布前检查 — 统一核心，4维审计)
python3 ~/writing-data/scripts/audit_guard.py --date 2026-05-05

# 发布（含审核门禁）
python3 ~/writing-data/scripts/publish_draft.py --date 2026-05-05
# 审核→PASS: 自动发布 | WARN: 继续(可用--strict阻止) | BLOCK: 阻止

# 仅审核不发布
python3 ~/writing-data/scripts/publish_draft.py --date 2026-05-05 --audit-only

# Publisher版audit wrapper (含--auto-publish)
python3 ~/writing-data/scripts/publish_audit_guard.py --date 2026-05-05 --auto-publish

# 周末周总结（含自动推送到草稿箱）
python3 ~/writing-data/scripts/weekly_summary.py

# 手动单独发布（正常情况无需手动调用）
python3 ~/writing-data/scripts/publish_draft.py --date 2026-05-05 --type weekly
python3 ~/writing-data/scripts/publish_draft.py --date 2026-05-05 --type daily

# 微信API健康检查（全链路验证）
python3 ~/writing-data/scripts/validate_wechat_api.py
python3 ~/writing-data/scripts/publish_draft.py --validate --date 2026-05-05  # 验证后自动发布
```

## 图表生成

每篇复盘文章自动配6张分析图表（4基础+2动态），发布时交错插入对应章节。

### 基础图表（每期必出）

| 图表 | 文件 | 插入位置 | caption |
|:--|:--|:--|:--|
| 上证日K线图 | kline.png | "大盘回顾" section后 | 上证指数日K线走势 |
| 板块涨跌热力图 | sector_heatmap.png | "热点" section后 | 行业板块涨跌幅 Top10 |
| 资金流向分析 | capital_flow.png | "资金流向" section后 | 主力资金近20日净流入 |
| 全A涨跌分布 | market_breadth.png | "技术看盘" section后 | 全A个股涨跌分布 |

### 晚间备用图表（数据缺失时从涨停池生成）

当标准数据源不可用（晚间19:00-08:00或EastMoney封锁），无法生成sector_heatmap/capital_flow/volume_compare/sector_rotation时，用涨停池数据补充2张增加多样性：

1. **sector_distribution.png** — 涨停行业分布条形图。从 `stock-sdk-mcp get_zt_pool(type="zt")` 的 `industry` 字段统计各行业涨停家数，取TOP15显示，<3家的合并为"其他"。配色：≥6家 `#D32F2F`，≥3家 `#FF6B35`，其余 `#FFB74D`。
2. **board_ladder.png** — 连板梯队柱状图。从 `continuousBoardCount` 字段统计各连板数的家数。80家首板/13家2连板/4家3连板/1家4连板。配色从蓝到红梯度。
3. 深色底 `#0d1117`，数据来源标注 `[stock-sdk-mcp zt_pool]`
4. 文中插入位置：行业分布图在"热点解读"段落后，连板梯队在连板小标题旁

### 新增图表（v5 — 2026-05-06）

| 图表 | 文件 | 说明 |
|:--|:--|:--|
| 成交量对比图 | volume_compare.png | 近10日成交量 vs 5日/20日均量 |
| 板块轮动图 | sector_rotation.png | 涨幅Top5 vs 跌幅Top5 双栏对比 |

生成函数在 `generate_charts.py` 中：`chart_volume_comparison()` + `chart_sector_rotation()`。

**配色规范：红涨绿跌（A股惯例）**

A股市场约定红色=上涨、绿色=下跌。所有图表统一使用此配色：

| 图表 | 涨 | 跌 | 实现位置 |
|:--|:--|:--|:--|
| K线 | 阳线红色 | 阴线绿色 | `mpf.make_marketcolors(up='red', down='green')` |
| 板块/资金流 | `#D32F2F`(红) | `#388E3C`(绿) | `colors` list comprehension |
| 涨跌停阈值线 | 涨停线红色 | 跌停线绿色 | `axvline(color=...)` |

⚠️ 注意：mplfinance 默认 styles 多为西方配色(绿涨红跌)，不能直接用内置 style，必须用 `make_mpf_style(marketcolors=...)` 显式覆盖。

**交错逻辑**（publish_draft.py → `interleave_images(html, image_map, draft_type)`）：
1. publish_draft.py 将 HTML 中的旧"数据图表"尾部 section 移除
2. 根据 `draft_type` 选择章节关键词映射：
   - **每日复盘**：大盘回顾→kline, 资金风向标→capital_flow, 热点→sector_heatmap, 技术看盘→market_breadth
   - **周总结**：本周行情回顾→kline+capital_flow(双图), 最热方向→sector_heatmap, 下周展望→market_breadth
3. 查找匹配的 `<h2>/<h3>` 标签，在 `</h>` 后插入 `<img>` + caption
4. 同章节多图用 `defaultdict(list)` 聚合一次性插入，不覆盖
5. 图片无 CDN URL 时不插入（静默跳过），不影响章节内容

**中文字体**：Ubuntu使用 `WenQuanYi Zen Hei`，需 `pip install mplfinance`。mplfinance 不继承 matplotlib rcParams — 必须对每个中文元素传入 `fontproperties=FontProperties(fname=字体路径)`。`fontname=` 参数依赖 fontconfig 匹配，不可靠，禁止使用。详见 `references/chinese-font-rendering.md`。

**API超时保护**：所有图表函数在调用 AKShare API 前必须加 signal alarm 超时（25-30s），防止晚间 API 黑窗导致管线卡死。同时检查缓存文件（>1KB），已存在则跳过。代码模板见 `references/evening-api-blackout.md`。

- `references/seo-content-optimization.md` — 🆕 SEO内容优化管线：标题公式/搜一搜策略/三源采集+交叉验证/小绿书策略/自动回复服务/新增cron (2026-05-09)
- `references/mcp-multi-source-fallback-pattern.md` — MCP服务降级 → 本地缓存回填 + 手动模式步骤（2026-05-08案例）
- `references/sina-api-field-map.md` — ❗ Sina API 字段映射铁律：parts[1]=今开 NOT 收盘（2026-05-06致命修复）
- `references/pipeline-health-check.md` — 管线健康检查脚本：7维26项自动化验证
- `references/evening-api-blackout.md` — 东方财富 push2 API 晚间维护窗口
- `references/cross-validation-design.md` — 多平台交叉验证设计：Sina/东方财富对比规则、自动修复逻辑、输出格式
- `references/development-roadmap-2026-05-07.md` — 🆕 多维度发展方向深度调研 + P1启动流水线（10维度×优先级矩阵）：行业板块涨跌幅（34行业）、指数行情、字段映射（⚠️ parts[1]=今开非收盘）
- `references/pipeline-health-audit.md` — 管线全貌审计清单（cron/脚本/数据/产出/干跑5维度）
- `references/data-source-fallback.md` — 多源降级策略（AKShare→Sina）+ 交叉验证 + 故障窗口
- `references/domain-audit-2026-05-06.md` — 2026-05-06 writing-domain审计记录（4个问题+修复）
- `references/ai-writing-gap-audit-2026-05-06.md` — avoid-ai-writing/content-creator集成差距审计（泄露模式+升级路线）
- `references/avoid-ai-writing-v3-spec.md` — 🆕 v3完整集成规范：Prompt禁用词清单+Tier1-3清洗词表+SEO评分+动态亮点评分引擎（2026-05-06）
- `references/cookie-publishing.md` — Cookie直连API发布（绕过IP白名单）。⚠️ 需要完整cookie集(poc_sid+data_bizuin+data_ticket+wxuin+slave_sid等≥6项)，仅poc_sid不足以通过API认证。登录后需导航到编辑器页面才能触发data_ticket等关键cookie。详见文档。⚠️ Playwright chromium版本不匹配时用symlink修复，勿重下167MB。
- `references/wechat-draft-api-limits.md` — 微信草稿箱 API 字段限制与错误码

## 微信素材库图片上传（新增）

publish_draft.py 支持自动上传图表到微信素材库：
- `POST /cgi-bin/material/add_material?type=image`
- 替换文章中本地路径为微信CDN URL (`mmbiz.qpic.cn`)
- API不可用时降级本地HTML保存

## 环境变量自动兜底

所有脚本会在启动时自动从 `~/.hermes/.env` 加载环境变量（放在 imports 之后、业务逻辑之前）：

```python
# Load .env as fallback for cron/non-shell environments
from pathlib import Path
_env_file = Path.home() / ".hermes" / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().split("\n"):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _val = _line.split("=", 1)
            _key = _key.strip()
            _val = _val.strip().strip('"').strip("'")
            if _key and _val and _key not in os.environ:
                os.environ[_key] = _val
```

**规则**：
- 显式设置的环境变量优先（shell export > .env）
- .env 文件格式：`KEY=value`，支持引号包裹的值
- 注释行（#开头）和空行自动忽略
- 5个writing-domain脚本均已内嵌此模式

| 变量 | 用途 | 定义位置 |
|:-----|:-----|:---------|
| `DEEPSEEK_API_KEY` | AI写作（DeepSeek V4） | `~/.hermes/.env` |
| `WECHAT_APP_SECRET` | 微信公众号发布 | `~/.hermes/.env` |
| `DASHSCOPE_API_KEY` | 通义千问备用 | `~/.hermes/.env` |

## 封面图生成（v2.0 — 信息图风格，2026-05-05）

publish_draft.py 自动生成信息图风格封面图（当 `~/writing-data/charts/YYYY-MM-DD/cover.png` 不存在时）：

**设计**：baoyu-infographic dashboard + corporate-memphis 风格
- 顶部彩色指标条：四大指数涨跌（红涨绿跌▲▼箭头）+ 成交额
- 中部主标题区：金色装饰线 + 标题（34pt）+ 日期
- 底部数据卡片：涨停数/跌停数/主力资金/最热板块
- 配色：GitHub深色底 `#0d1117`，红 `#ff4444` 涨绿 `#00c853` 跌，金 `#ffb347` 高亮
- 尺寸：900x500px @150dpi，零API成本

**数据来源**：读取 `~/writing-data/raw/YYYY-MM-DD/all_data.json`，自动提取 index/change_pct/turnover/net_inflow/limit_up_down/sectors

**降级**：数据文件不存在时仍生成骨架封面（仅标题+日期，无数据卡片）

通过 `create_cover_image(date_str, draft_type)` 的 `draft_type` 参数区分：
- `"daily"` → 标题 "A股每日复盘"
- `"weekly"` → 标题 "本周热门"，副标题 "A股周总结 · {date_str}"

## 微信IP白名单诊断

```bash
# 检查服务器公网IP并输出配置指引
python3 publish_draft.py --check-ip
```

故障排查时先运行该命令，再将IP添加到「微信公众号后台 → 设置与开发 → 基本配置 → IP白名单」。脚本每次获取 token 时也会自动检测 IP 白名单状态。

**Cookie直连方案故障排查**：
1. `python3 cookie_publish.py --login` → 扫码登录后**必须导航到编辑器页面**才能提取完整cookie集（含data_ticket等关键cookie）
2. 验证cookie完整性：`jq length ~/.hermes/credentials/wechat_cookies.json` → 应≥6
3. 如返回`ret=-6` → cookie过期/不完整，重新 --login

## 安全注意事项

⚠️ **API密钥一律走环境变量**，禁止在 config.yaml 中硬编码：
```yaml
# ❌ 错误（明文暴露）
ai_apis:
  deepseek:
    api_key: "sk-c31...8c9f"

# ✅ 正确
ai_apis:
  deepseek:
    api_key: "${DEEPSEEK_API_KEY}"
```

密钥定义在 `~/.hermes/.env`，权限应为 `600`。微信 AppSecret 等敏感凭证同样适用此规则。

---

## Cron任务实际配置（2026-05-07 最新 — QQ Bot推送，微信iLink已废弃）

⚠️ 微信iLink因rate limited不可靠已于2026-05-07全线切换到QQ Bot。QQ Bot deliver格式：`qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12`。

| 任务ID | 名称 | 执行时间 | deliver | 功能 |
|--------|------|---------|---------|------|
| 8dc31c90bf0d | 早间合并：盘前早报+巡检+信号 | 周一至周五08:00 | **qqbot** | morning_brief.py → 系统健康(磁盘/内存/网关) → 合并一条消息 |
| 5896e6bcea04 | A股每日数据采集+图表生成 | 周一至周五15:30 | local | collect_data.py → generate_charts.py（3-way交叉验证） |
| d075c207d860 | A股每日复盘生成+公众号草稿箱+通知 | 周一至周五16:00 | **qqbot** | generate_review.py → publish_draft.py → 推草稿箱 → **直接QQ通知用户** (原18:00提醒已合并至此步骤) |
| ~~18619f5cdf16~~ | ~~雪球每日复盘发布~~ | ~~周一至周五16:30~~ | ~~local~~ | **已删除**(2026-05-08) |
| ~~704e9bfe5896~~ | ~~A股复盘文章生成提醒~~ | ~~周一至周五18:00~~ | ~~local~~ | **已删除**(2026-05-08, 合并至16:00步骤) |
| 3858ff88add6 | A股周总结一体化 | 周五16:00 | **qqbot** | 采集+分析+AI写作+自动推草稿箱+QQ通知 |
| bc02d5952723 | A股量化周报生成 | 周六08:00 | **qqbot** | quant_weekly.py |
| *系统crontab* | 周末深度图文 ⭐ | 周六10:00 | *独立crond* | weekend_deep_dive.py → 公众号草稿箱 |

### 周末发布节奏（2026-05-11 最终版）
- 周五 16:00：周总结 → 公众号草稿箱（含信号引擎"下周关注"）(3858ff88add6)
- 周六 08:00：量化周报 → 公众号草稿箱 (bc02d5952723，从周日15:30迁移)
- 周六 08:00/14:00：科普×2 → 公众号草稿箱 (9f73cbaa5f1e, d50d838746d6)
- 周日 08:00/14:00：科普×2 → 公众号草稿箱 (d403a750c641, 032e7102e419)

周末总产出: 1篇量化周报 + 4篇科普 = 5篇。全部复用现有管线。

QQ通知: 所有写作脚本已统一接入 `notify.py`（`from notify import article_published`）。文章推送草稿箱成功后自动调用。quant_weekly除外（用户要求独立处理）。notify.py写入JSON队列 → pipeline_runner每30min投递 → QQ Bot。
3. publish_draft.py 推送到微信公众号草稿箱
4. QQ Bot通知（含草稿箱ID）

toolsets已添加 `web`（微信API需要网络访问）。

**根因排查顺序**：
1. IP白名单 → `errcode=40164` (最常⻅)
2. Token过期 → 脚本自动刷新
3. AppSecret错误 → 检查.env
4. 配额耗尽 → `errcode=50002`

### QQ Bot工作日推送线（6条，含周末）

```
08:00  早报+巡检+信号  ← 三合一
09:55  GLM抢购         ← c2cdfe68c822（非writing域）
16:00  每日复盘
18:00  复盘提醒
21:00  回测+信号日报
```

> ⚠️ QQ Bot推送通过Hermes deliver通道，走notify.py队列 → dispatch。gateway的WebSocket C2C路径仅用于inbound-response交互，与cron deliver路径不同。

### 管线时序 (2026-05-11 审计后最终版)

```
── 交易日 ──
08:00 → 盘前早报+巡检+信号 (8dc31c90bf0d)
15:10 → 轻量实时采集+SEO复盘→推公众号草稿箱 (8aa4c853cff3, no_agent)
15:15 → 小绿书短内容→推公众号草稿箱 (108ce7535e38, no_agent)
15:25 → 管线健康检查 (502ebe4a4392)
15:30 → 每日数据采集+图表生成 (5896e6bcea04)
16:00 → 每日复盘→推草稿箱→QQ通知 (d075c207d860)
16:00 → [仅周五] 周总结一体化→推草稿箱 (3858ff88add6)
17:00 → 策略信号扫描→QQ推送 (b60f3c86dd1b)

── 周末 ──
周六08:00 → 量化周报→推草稿箱 (bc02d5952723)
周六08:00 → 科普: 主力资金 (9f73cbaa5f1e)
周六14:00 → 科普: 追涨 (d50d838746d6)
周日08:00 → 科普: 市盈率 (d403a750c641)
周日14:00 → 科普: 新手亏钱 (032e7102e419)
```

### Cron管理命令
```bash
# 查看所有任务
hermes cron list

# 查看任务详情
hermes cron show 704e9bfe5896

# 暂停/启用任务
hermes cron pause 704e9bfe5896
hermes cron resume 704e9bfe5896

# 删除任务
hermes cron delete 704e9bfe5896
```
