# Hermes Agent 系统架构 — 2026-05-10

## 总览

```
用户(CLI/QQBot)
    ↓
┌─────────────────────────────────────────────────┐
│  Hermes Gateway (PID 75270, 运行38h+)            │
│  消息路由 / session管理 / 多平台适配              │
└──────┬──────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│  主代理 (deepseek-v4-pro)                        │
│  SOUL.md(83行) — 调度决策核心                    │
│  ├─ 决策矩阵 L1/L2/L3                            │
│  ├─ 调度速查表(lesson_inject嵌每条路径)           │
│  └─ 5域资源表                                    │
└──────┬──────────────────────────────────────────┘
       ↓ delegate_task
┌──────────────────────────────────────────────────┐
│            6个域子代理 (Domain Agents)             │
├──────────┬──────────┬──────────┬─────────────────┤
│ code     │ ops      │ research │ finance         │
│ glm-5.1  │ v4-pro   │ v4-pro   │ v4-pro          │
│ 编码/git │ 运维/cron│ 深度调研 │ 量化/基本面      │
├──────────┴──────────┼──────────┴─────────────────┤
│ writing             │ ec (暂停)                   │
│ v4-pro              │ v4-pro                      │
│ A股内容自动化        │ 电商选品→上架→运营          │
└─────────────────────┴────────────────────────────┘
```

## 层架构

```
┌─── 协调层(Role横向) ───┐   ┌── 能力层(Domain纵向) ──┐
│ Researcher→Creator→     │   │ code │ ops │ research   │
│ Reviewer→Synthesizer    │   │ finance │ writing │ ec │
├─── 质量层(Gate纵向) ────┤   ├── 智能层(Reasoning) ───┤
│ data_guard(字段验证)    │   │ graphify 65K节点 78MB   │
│ Reviewer(语义审查)      │   │ sequential-thinking     │
│ quality_score(量化评分) │   │ deep-research 9角度     │
├─── 记忆层 ──────────────┤   │ brainstorming(设计)     │
│ MEMORY.md (2K chars)    │   └─────────────────────────┘
│ lessons/ (7域 150+条)   │
│ graphify 知识图谱        │
└─────────────────────────┘
```

## 数据流

```
外部数据源                    内部管线                    产出
────────────────────────────────────────────────────────────
东财/Sina/雪球/AKShare  →  collect_data.py         →  all_data.json
                               ↓
                          generate_charts.py        →  PNG图表(26张)
                               ↓
                          generate_review(_seo).py  →  复盘草稿(.md)
                               ↓
                          data_guard.py(门禁)       →  PASS/WARN/BLOCK
                               ↓
                          publish_draft.py          →  公众号草稿箱
                          (API→Cookie→Browser三级)

东财/AKShare/tushare   →  precache_kline.py        →  MySQL stock_kline
                                                    (708万行/5351只)
                               ↓
                          mid_cap_strategy.py       →  12因子评分
                          signal_engine.py          →  缠论二买信号
                               ↓
                          daily_signal_report.py    →  QQBot推送
```

## MCP 工具链 (15个Server)

| 类别 | Server | 用途 |
|:--|:--|:--|
| **治理** | skill-auditor | 技能安全审计 |
| | cost-guard | 成本追踪+熔断 |
| | prompt-optimizer | 指令优化+域识别 |
| | security-auditor | 文件安全扫描 |
| **知识** | graphify | 知识图谱(65K节点) |
| | llm-wiki | LLM知识库检索 |
| | sequential-thinking | 分步推理引擎 |
| **研究** | web-search (Tavily) | 网页搜索 |
| | web-extract (Jina/Crawl4AI) | 网页内容提取 |
| | deep-research | 9角度深度研究 |
| **数据** | stock-sdk | A股/港股/美股行情 |
| | mysql | stock_kline数据库 |
| **调度** | hermes-delegate | 任务队列 |
| | hermes-cron | Cron管理 |
| **其他** | time | 时区转换 |
| | whisper | 语音转文字 |

## Cron系统 (38个任务)

| 类型 | 数量 | 示例 |
|:--|:--|:--|
| no_agent脚本 | 16 | K线更新、资金流预采集、agenda构建、健康检查 |
| agent任务 | 22 | 每日复盘、早报、信号扫描、自优化 |

**关键cron时间线（交易日）：**
```
08:00  morning_brief(早报)
08:05  ops-autopilot(运维自愈)
09:00  auto-daily-review(自主审视)
10:00  rule-audit-daily(规则遵守审计)
15:05  资金流预采集
15:10  SEO复盘生成
15:15  小绿书短内容
15:25  管线健康检查
15:30  数据采集+图表
16:00  K线更新+每日复盘发布
17:00  多因子信号扫描
21:00  daily-digest(每日摘要)
22:00  error-learner(教训提炼)
```

## 强制执行层

| 脚本 | 触发 | 作用 |
|:--|:--|:--|
| enforce_delegate.py | 每次delegate前 | lesson_inject+死路检查+铁律注入 |
| cost-circuit-breaker.py | 每小时cron | 日消耗>$7.00自动暂停高消费cron |
| rule_audit.py | 每日10:00 cron | 扫描违规用语/死路提及 |
| data_guard.py | 每次发布前 | 字段验证+AI味检测+函数漂移 |
| auto_review.py | 每日09:00 cron | 系统健康+配置一致性+教训扫描 |

## 数据存储

| 存储 | 位置 | 规模 |
|:--|:--|:--|
| MySQL(stock_kline) | localhost:3306 | 708万行, 5351只, 2020-至今 |
| K线缓存 | ~/quant/.cache/ | 4939只, 435MB |
| 财务缓存 | ~/.finquant/cache/financial/ | 5845只 |
| 资金流缓存 | ~/.finquant/cache/fund_flow/ | 1466只 |
| Sessions | ~/.hermes/sessions/ | 705文件, 309MB |
| 知识图谱 | ~/brain/graphify-out/ | 78MB, 65K节点 |
| 教训 | ~/.hermes/lessons/ | 7域, 150+条 |

## profiles/ 域宪法

| 域 | profiles结构 | SOUL.md |
|:--|:--|:--|
| code-domain | 完整(11项目录) | ✅ |
| ops-domain | 完整(11项目录) | ✅ |
| research-domain | 完整(11项目录) | ✅ |
| finance-domain | 精简(4项) | ✅ |
| writing-domain | 精简(5项) | ✅ |
| ec-domain | 最小(3项) | ✅ |
