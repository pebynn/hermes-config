# 综合进化升级方案 — P+B+C+D+N Agent Evolution Roadmap

> **生成日期**: 2026-05-13
> **任务**: 综合进化升级方案 (t_f7386342)
> **状态**: 终版 · 关闭外部进化评估集成项目
> **输入源**: GEPA 5护栏分析 / SkillClaw对比 / EvoClaw退化检测 / Rule-based变异模板 / Tool描述审计 / System Prompt优化 / Self-Evolving Survey分析

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [输入综合 — 我们学到了什么](#2-输入综合)
3. [决策框架 — 自建 vs 借用 vs 忽略](#3-决策框架)
4. [路线图 P0·P1·P2](#4-路线图)
5. [时间线目标](#5-时间线目标)
6. [决策门禁](#6-决策门禁)
7. [资源与成本估算](#7-资源与成本估算)
8. [风险登记册](#8-风险登记册)
9. [架构全景图](#9-架构全景图)
10. [Phase 0 资产盘点 — 已交付](#10-phase-0-资产盘点)

---

## 1. 执行摘要

经过 7 项子任务调研（GEPA 分析、SkillClaw 对比、EvoClaw 实现、变异模板设计、Tool 审计、Prompt 审计、Survey 研读），我们已完成外部进化评估集成项目的数据采集阶段。

**核心结论**: 我们的 P+B+C+D+N 管线在「安全基础设施」层面（护栏/GEPA 5护城河/成本控制/知识图谱）优于已知文献，但在「自动化闭环」层面存在缺口——缺乏轨迹感知的反思性诊断和自动触发进化。

**Phase 0 已交付资产**（本项目中已完成的 3 项）:
- EvoClaw 退化检测 cron (监督 B/D 注入率, zero-token)
- GEPA 5 护栏集成到 audit_bd_layer.py（大小/pytest/缓存/语义/人审）
- 7 个规则的变异模板设计（零 DSPy 依赖，~270 行代码）

**推荐立即执行 Phase 1（~2-3 天）**:
1. Trajectory Miner — 从 kanban.db 自动挖掘失败模式
2. MUT-01+MUT-02 Lessons 自动升级 + 成本自适应收紧
3. 系统 Prompt 模板抽取 → 每个 worker 省 37-47%

---

## 2. 输入综合

### 2.1 调研资产全景

| # | 输入 | 来源 | 形式 | 关键产出 | 状态 |
|:-|:-----|:-----|:-----|:---------|:-----|
| 1 | GEPA 5 护栏分析 | arXiv:2507.19457 (ICLR 2026 Oral) + hermes-agent-self-evolution | `gepa_survey_analysis.md` | 5 道护栏映射到 audit_bd_layer.py; 4 层进化目标; 差距矩阵 | ✅ 已完成 |
| 2 | GEPA + Survey 深度研读 | arXiv:2507.19457 + arXiv:2508.07407 | `gepa-self-evolving-analysis.md` | 反思性诊断为核心竞争力; Three Laws 框架; 10 项差距评级 | ✅ 已完成 |
| 3 | SkillClaw 论文对比 | arXiv:2604.08377 (Ma et al., Apr 2026) | `skillclaw_analysis.md` | 8 项能力对比; 8 借/12 不借策略; 优先级推荐 | ✅ 已完成 |
| 4 | EvoClaw 退化检测 | arXiv:2603.13428 (benchmark) | `evoclaw_degradation_detect.py` (378 行, 31/31 测试通过) | 7 天窗口退化监测; P1/P0 告警; 每日 cron | ✅ **已交付** |
| 5 | 遗传算法轻量变异模板 | GEPA 算子降维 | `rule_based_mutations.md` (555 行) | 7 个规则模板 (MUT-01~07); 无 DSPy 依赖; ~270 行实现 | ✅ 设计完成 |
| 6 | Tool 描述优化审计 | 全 MCP 服务扫描 (12 服务器, ~55 工具) | `tool_description_audit.md` | Top 10 最差工具; GEPA 帕累托优化模板 | ✅ 已完成 |
| 7 | System Prompt 优化 | 全 worker SOUL.md 扫描 (9 文件) | `system_prompt_optimization.md` (539 行) | 9 大反模式; 7 条 GEPA 遗传原则; 3 个最问题 worker 方案 | ✅ 已完成 |
| 8 | 生态地图 | 超过 15 篇论文/项目（详见附录: 参考文献） | 汇总于本节 | GEPA / SkillClaw / EvoClaw / DSPy / Reflexion / MemGPT / ToolGen / EvoFlow / PromptBreeder 等 | 📡 网络搜索不可用 |

### 2.2 关键发现汇总

| 调研项目 | 最重要的 3 条发现 |
|:---------|:----------------|
| **GEPA** | (1) 核心是"反思性诊断"而非遗传算法——LLM 读执行轨迹文本定位失败原因 (2) 35x 比 RL 更廉价 ($2-10/run, 无 GPU 需求) (3) 5 道护栏是工程落地实践，非论文理论贡献 |
| **SkillClaw** | (1) 自动跨用户轨迹挖掘是我们最大的缺口 (2) 我们赢在事前预防+质量护栏+成本控制 (3) 最值得借用的不是整个系统而是轨迹→Lesson 的自动管道 |
| **EvoClaw** | (1) 持续进化会导致性能退化 (80%→38%) (2) 需要 7 天窗口退化检测 + 自动回滚 (3) 已实现: daily cron, 3+ consecutive decline → P1, >50% drop → P0 |
| **Survey** | (1) Three Laws (恒存/增益/自治) 可作为进化质量框架 (2) 优化器(Optimiser)是我们最薄弱的四组件 (3) 进化维度覆盖 5 个（模型/提示/记忆/工具/工作流） |
| **变异模板** | (1) 可用 kanban.db/lessons/cost-tracker 数据自驱, 零 DSPy 依赖 (2) 7 个模板共 ~270 行, 分 4 阶段实现 (3) 核心思路: 规则触发 → 确定性变换 → 安全回滚, 放弃指数搜索 |
| **Tool 审计** | (1) 无大小违规 (<500 chars), 但 15/40 工具描述含糊 (2) 最大的问题: 0 工具提及错误条件 (3) stock-sdk 的中文描述是最佳参考模版 |
| **Prompt 审计** | (1) 9 大反模式中最严重: 模板复制 (81 行) + Lessons 块 (90 行) (2) 3 个最问题 worker: research/finance/code-domain (3) 帕累托外移 L3 内容可压缩 37-47% |

### 2.3 生态地图

以下为已知的 agent 自我进化论文/框架（Web 搜索不可用，清单基于已分析的论文引用链）:

| 类别 | 项目/论文 | 核心思路 | 关联度 |
|:----|:----------|:---------|:------|
| **反思性变异** | GEPA (ICLR 2026 Oral) | 读轨迹 → 反思 → 定向变异 → Pareto 筛选 | ⭐⭐⭐ 核心 |
| **同类比较** | SkillClaw (arXiv 2604.08377) | 多用户轨迹 → 自动技能编辑 | ⭐⭐⭐ 重要 |
| **退化检测** | EvoClaw (arXiv 2603.13428) | 持续进化导致 80%→38% 退化 | ⭐⭐⭐ 已实现 |
| **提示进化** | DSPy MIPROv2 | 贝叶斯式提示优化 | ⭐⭐ 参考 |
| **提示进化** | APE / OPRO (Zhou et al.) | 自动提示工程师 | ⭐ 参考 |
| **提示进化** | PromptBreeder | 遗传算法进化提示 | ⭐ 参考 |
| **记忆进化** | MemGPT / Reflexion | 工作记忆 + 反思回放 | ⭐⭐ 部分相关 |
| **工具进化** | ToolGen / AdaTool / ReTool | 工具创建和文档优化 | ⭐ 参考 |
| **工作流进化** | EvoFlow / AutoAgents / MAS-GPT | 多智能体配置自动调优 | ⭐ 参考 |
| **RL 方法** | GRPO / STILL-ALIVE / R-Zero | 强化学习进化智能体 | ⭐ 计算成本过高 |
| **工程框架** | hermes-agent-self-evolution | GEPA 在 hermes 上的工程落地 | ⭐⭐ 直接相关 |

---

## 3. 决策框架

### 3.1 核心原则

每条进化改进按以下三维度评估:
- **自建 (Build)** — 我们的核心差距, 有可持续价值, 适合内部深度集成
- **借用 (Borrow)** — 外部方法论可无缝融入现有基础设施, 不需要完整重写
- **忽略 (Ignore)** — 与我们的单用户/成本敏感/安全优先场景不匹配

### 3.2 决策矩阵

| # | 能力 | 来源 | 决策 | 理由 |
|:-|:-----|:-----|:-----|:------|
| 1 | **轨迹挖掘（kanban.db → lessons）** | SkillClaw 方法论 | ✅ **Borrow** — 写 `trajectory_miner.py` 扫描 kanban.db 完成的任务, LLM 提取重复模式生成候选 lessons | 已知的最大缺口；SkillClaw 思路适配现有基础设施（kanban.db 已有所有数据） |
| 2 | **反思性失败诊断** | GEPA 核心创新 | ✅ **Build** — 创建 `reflection/reflector.py` 捕获最后一次交互轨迹 + LLM 诊断（tool_misuse / prompt_ambiguity / context_loss） | GEPA 35x 的根源；当前系统完全缺失；可持续竞争优势 |
| 3 | **Pareto 候选体池 + 多样性维护** | GEPA Pareto 前沿 | ⚠️ **暂缓 (P2 Reserve)** — 我们的规则式变异模板确定性高, 不需要搜索空间 | 指数空间搜索对我们的确定性场景收益有限，待规则模板成熟后再评估 |
| 4 | **跨用户轨迹聚合** | SkillClaw | ❌ **Ignore** — 单用户系统（每个 worker 只服务一个用户） | 架构不匹配；投入产出比为负；需要多租户层的根本变化 |
| 5 | **自动技能编辑** | SkillClaw | ⚠️ **Borrow (有控制)** — 高频 lessons 自动生成 skill patch, 但通过 L2/L3 门禁 | 高频率 lessons → 自动创建技能 → 人工审核 → 部署；安全网不能丢 |
| 6 | **行为模式挖掘（工具调用序列分析）** | SkillClaw | ⚠️ **暂缓 (P2 Reserve)** — 需先有轨迹存储设施 | 依赖 trajectory store 基础设施，Phase 2 后评估 |
| 7 | **DSPy 框架安装** | GEPA | ❌ **Ignore** — 确认无 DSPy 依赖即可实现所有改进 | 独立验证：7 个变异模板 + trajectory miner 均无需 DSPy |
| 8 | **GRPO / RL 类方法** | Survey | ❌ **Ignore** — 计算成本高（GPU），需要大量 rollout | 与 $2-10/run 原则冲突；GEPA 本身证明可以 35x 更便宜替代 GRPO |
| 9 | **GEPA 5 护栏** | hermes-agent-self-evolution | ✅ **已实现** — 集成到 audit_bd_layer.py | P0 已完成：大小/pytest/缓存/语义/人审 |
| 10 | **Three Laws 框架** | Survey | ✅ **Borrow** — lessons 回传的质量准入标准 | 每条 lessons 必须满足"增益律"（至少不降低性能）才能入库 |
| 11 | **L2/L3 决策矩阵 + PR 审查** | GEPA 工程实践 | ✅ **已实现** — 映射到护栏 5 | 所有自动进化产物必须走审批管线 |
| 12 | **退化检测 + 自动回滚** | EvoClaw | ✅ **已实现** — evoclaw_degradation_detect.py + cron | P0 交付: 7 天窗口, P1/P0 告警, zero-token |
| 13 | **Tool 描述帕累托优化** | GEPA Tier 2 | ⚠️ **暂缓** — 无违规问题 (<500 chars), 改善集中在模糊性 | 设计 GEPA 风格优化模板但暂不实现自动化 |
| 14 | **System Prompt 帕累托外移** | GEPA Tier 3 (最高风险) | ✅ **Build (Phase 2)** — 抽取模板到共享文件, 行号清理, skills 去重 | 最高风险但最大回报：月省 240 万 tokens, research-domain 从 160→~100 行 |
| 15 | **多智能体拓扑自动优化** | Survey (EvoFlow) | ❌ **Ignore** — 单智能体架构 | 架构层改变，超越本项目的范围 |
| 16 | **B+D 有效性基准** | SkillClaw (WildClawBench) | ⚠️ **暂缓 (P3)** — 在没有自动化闭环前, 基准的 ROI 有限 | 先建自动进化闭环, 再建基准衡量闭环效果 |

---

## 4. 路线图

### 4.1 P0 — 立即 (本周, ~2-3 天)

| # | 项目 | 来源 | 工时 | 依赖 | 产出 |
|:-|:-----|:-----|:-----|:-----|:-----|
| **P0-1** | Trajectory Miner 脚本 | SkillClaw Borrow | 1-2 天 | `kanban.db` 已有数据 | `scripts/trajectory_miner.py` — daily cron, 扫描 7 天 completed tasks, LLM 模式检测, 输出候选 lessons |
| **P0-2** | MUT-01 + MUT-02 实现 | 规则变异模板 | 3 小时 | `post_kanban_complete.py` | Lesson 出现 ≥2 次 → 自动升级 🔴; 7 天日均成本 >$5 → 自动收紧 15% |
| **P0-3** | 跨任务模式检查钩子 | SkillClaw Borrow | 0.5 天 | `pre_kanban_create.py` | `kanban_complete` 前审查最近 20 个同域任务, 标记已知失败模式 |
| **P0-4** | 行号污染清理 + 去重 | Prompt 审计 | 1 小时 | 8 个 SOUL.md 文件 | 正则清理 `^\s+\d+\|` + 移除重复 skill 条目 |
| **P0-5** | EvoClaw 监控面板集成 | 已实现 | 0.5 天 | `evoclaw_history.json` | 在每日审计报告增加退化检测摘要行 |

**P0 总工时: ~3-4 天 | 依赖项: 0 | 交付物: 4 个脚本/1 个修复**

### 4.2 P1 — 本月 (~2 周)

| # | 项目 | 来源 | 工时 | 依赖 | 决策门禁 |
|:-|:-----|:-----|:-----|:-----|:---------|
| **P1-1** | System Prompt 模板抽取 | Prompt 审计 | 1-2 天 | context-assemble 确认支持引用 | L2: 需确认 context-assemble 的引用机制 |
| **P1-2** | Tool 描述 Top 10 修复 | Tool 审计 | 0.5 天 | 无 | L1: 纯文本修改, 低风险 |
| **P1-3** | MUT-04 + MUT-07 实现 | 规则变异模板 | 1 天 | P0-2 完成 | L2: 跨域重排和回退涉及 DAG 分析 |
| **P1-4** | Trajectory Store 配置 (session 持久化) | SkillClaw Borrow | 1 天 | P0-1 完成 | L2: 存储策略 + 保留周期 |
| **P1-5** | 累积改进仪表盘 | 审计需求 | 0.5 天 | P0-2 (MUT-01) + EvoClaw | L1: 纯指标显示 |

**P1 总工时: ~4-5 天 | 依赖项: P0 | 交付物: 3 个脚本/1 个配置/1 个报告**

### 4.3 P2 — 研究储备 (~1-2 月)

| # | 项目 | 来源 | 工时 | 前置条件 | 备注 |
|:-|:-----|:-----|:-----|:---------|:-----|
| **P2-1** | MUT-05 + MUT-06 实现（智能注入+反向抽取） | 规则变异模板 | 2 天 | P1-4 (trajectory store) | 需文本相似度工具 (cosine_similarity) |
| **P2-2** | 反思性诊断 (reflection/reflector.py) | GEPA 核心 | 1-2 天 | P1-4 (trajectory store) | 最高价值但最大架构影响; 需要决定"捕获哪些轨迹"的范围 |
| **P2-3** | Skill 自动进化守护进程 (周级 cron) | SkillClaw + GEPA | 2-3 天 | P2-1 + L2/L3 门禁就绪 | 高频 lessons → 自动 skill patch → 人工审核 |
| **P2-4** | Pareto 候选体池评估 | GEPA Pareto | 3-5 天 | 待规则模板成熟 | 先运行规则模板 4-6 周, 再评估是否需要 Pareto 空间 |
| **P2-5** | B+D 有效性基准 | SkillClaw WildClawBench 思路 | 2 天 | P1-5 (仪表盘) | A/B 对比: 有 B+D vs 无 B+D |

**P2 总工时: ~10-15 天 | 依赖: P1 | 决策点: P2-2/P2-4 需 L3 审批**

---

## 5. 时间线目标

```
Week 1 (5月第3周)    ████████████████░░░░  P0: 4+1 项
Week 2 (5月第4周)    ████████████████████  P1-1, P1-2, P1-3
Week 3 (6月第1周)    ░░░░████████████████  P1-4, P1-5, P2-1
Week 4 (6月第2周)    ░░░░░░░░████████████  P2-2, P2-3
Month 2-3            ░░░░░░░░░░░░░░░░░░░░  P2-4, P2-5 (ongoing evaluation)
```

| 里程碑 | 检查点 | 日期目标 |
|:-------|:-------|:---------|
| M0 | **P0 全部交付** | 2026-05-18 |
| M1 | **P1-1 System Prompt 压缩** | 2026-05-20 |
| M2 | **P1-3 Trajectory Store 上线** | 2026-05-25 |
| M3 | **P2-2 反思性诊断 MVP** | 2026-06-01 |
| M4 | **P2-3 Skill 自动进化守护进程** | 2026-06-10 |
| M5 | **本阶段结束评估** | 2026-06-15 |

---

## 6. 决策门禁

每条自动进化改进在经过以下 L1→L2→L3 门禁后才可上线:

### 6.1 门禁级别

| 级别 | 适用范围 | 审批者 | 响应时间 |
|:----|:---------|:-------|:---------|
| **L1** — 自动通过 | 内容修复（行号清理）、纯显示（仪表盘指标）、低风险工具描述改进 | 无需审批 | 即时 |
| **L2** — 人工确认 | 模板抽取、尺寸变更、跨域影响、成本配置变化 | 用户确认 | <30 分钟 |
| **L3** — 严格审查 | 自动 skill 编辑、反思性诊断、Pareto 池部署 | 用户审查 + 测试 | <2 小时 |

### 6.2 各改进项的门禁分配

| 项目 | 门禁级别 | Go 条件 | No-Go 条件 |
|:----|:---------|:--------|:-----------|
| P0-1 Trajectory Miner | **L2** | 候选 lessons review 机制确认 | LLM 模式检测 false positive >20% |
| P0-2 MUT-01/MUT-02 | **L1** (自动) | — | 升级后 lesson 回滚率 >30% |
| P0-3 跨任务检查 | **L2** | 最近 20 任务样本手动验证 | 标记 false positive >2/20 |
| P1-1 Prompt 模板抽取 | **L3** | context-assemble 确认引用支持; 3 个 worker 测试 | 任意 worker 失败率上升 >10% |
| P1-3 MUT-04/MUT-07 | **L2** | DAG 依赖分析正确性验证 | 跨域 body 重建后 worker blocked 率上升 |
| P2-2 反思性诊断 | **L3** | 轨迹捕获不影响现有 session; 分类准确率 >70% | 诊断 LLM 调用增加成本 >30% |
| P2-3 Skill 自动进化 | **L3** | P2-1 已运行 2 周; false positive <10% | 自动 patch 导致测试失败 |

### 6.3 回滚策略

| 触发条件 | 级别 | 操作 |
|:---------|:-----|:-----|
| 自动进化后 worker blocked 率上升 >15% | P1 | 自动回退到前 1 个成功配置, 通过 evoclaw 监控 |
| MUT-01 误升级导致 🔴 lessons 泛滥 | P1 | 恢复 previous_level, 锁定该 lesson 7 天 |
| 成本收紧导致任务创建阻塞 | P0 | 自动恢复原阈值 + 标记 LOCK 状态 |
| trajectory miner 产出噪音 lessons | P2 | 候选 lessons QUEUE 不自动注入, REVIEW_ONLY 模式 |

---

## 7. 资源与成本估算

### 7.1 开发人力

| 阶段 | 总工时 | 分项 | 
|:-----|:------|:-----|
| **P0** | ~18 小时 | Trajectory Miner (10h) + MUT-01/02 (3h) + 跨任务检查 (3h) + 行号修复 (1h) + EvoClaw 集成 (1h) |
| **P1** | ~24 小时 | Prompt 抽取 (10h) + Tool 修复 (3h) + MUT-04/07 (5h) + Trajectory Store (4h) + 仪表盘 (2h) |
| **P2** | ~40 小时 | MUT-05/06 (8h) + 反思性诊断 (12h) + Skill 守护进程 (12h) + Pareto 评估 (4h) + 基准 (4h) |
| **总计** | ~82 小时 | 约 2 周的全职开发 |

### 7.2 运行时成本 (增量)

| 组件 | 增量成本 | 解释 |
|:-----|:---------|:------|
| EvoClaw cron | **$0** — zero-token (no_agent=true) | 纯 stdlib + SQLite |
| Trajectory Miner (daily) | **~$0.02-0.05/次** — LLM 扫描 7 天数据 + 模式总结 | 取决于每日 completed tasks 数量 |
| MUT-01/02 | **$0** — 纯统计规则 | 无 LLM 调用 |
| MUT-04/07 | **$0** — 逻辑判断 + 字符串操作 | 无 LLM 调用 |
| 跨任务模式检查 | **~$0.01/任务** — 仅当相似度 >70% 时触发 LLM | 非每任务都触发 |
| 反思性诊断 | **~$0.02-0.05/次** — 每次失败后捕获+分析轨迹 | 仅在失败事件后触发 |
| Skill 自动进化守护进程 (weekly) | **~$0.05-0.10/周** — 总结 lessons + 建议 patch | 周级触发 |
| **P0 增量** | **~$0.60-1.50/月** | 主要来自 Trajectory Miner |
| **P0+P1+P2 增量** | **~$3.00-8.00/月** | 远低于 GEPA 的 $2-10/次优化运行 |

### 7.3 Token 节约估计

| 优化项 | 每调用节约 | 月度 Token 节约 | 月度成本节约 |
|:-------|:----------|:--------------|:------------|
| Prompt 模板抽取 (9 worker) | ~200 tokens/worker | 2,430,000 | ¥5-12 ($0.7-1.7) |
| Tool 描述精简 | ~50 tokens/worker | 607,500 | ¥1-3 |
| Skills 去重 | ~30 tokens/worker | 364,500 | ¥0.5-1.5 |
| **合计** | **~280 tokens/worker** | **~3,402,000** | **¥6.5-16.5 ($0.9-2.4)** |

> 注: 基于 deepseek-v4 价格 ~¥2-5/百万输入 tokens, 假设每 worker 日调用 10 次

---

## 8. 风险登记册

| # | 风险 | 概率 | 影响 | 级别 | 缓解 |
|:-|:-----|:-----|:-----|:-----|:-----|
| R1 | Trajectory Miner 产生大量 false positive lessons | 高 | 中 | 🟡 | 不自动注入, 经 REVIEW_QUEUE + 人工确认后入库 |
| R2 | System Prompt 抽取后 context-assemble 未正确注入 | 中 | 高 | 🔴 | 先在 global.md 保留备份引用, 逐步迁移 |
| R3 | MUT-02 成本收紧过度 → 任务创建阻塞可逆性不足 | 低 | 高 | 🟡 | 硬编码下限 $3.00, 熔断自动恢复 |
| R4 | MUT-01 误升级 → 🔴 lessons 泛滥致 B 层 token 膨胀 | 中 | 中 | 🟡 | 保留 previous_level, 7 天回滚窗口 |
| R5 | 反思性诊断的 LLM 调用增加总成本 >30% | 低 | 低 | 🟢 | 仅失败事件触发, 非每任务 |
| R6 | Skill 自动进化导致 skill 损坏 | 中 | 高 | 🔴 | 全部通过 L2/L3 门禁, PR 模式不直接 commit |
| R7 | 规则模板之间相互干扰 (MUT-01/03/06 可同时触发) | 中 | 低 | 🟢 | mutation_orchestrator 按优先级排序, 低优先跳过 |
| R8 | Web 搜索不可用 (Tavily credit) 影响依赖搜索的研究任务 | 高 | 低 | 🟢 | 本次综合报告已通过本地文件完成, 生态地图标记"网络不可用" |

---

## 9. 架构全景图

```
                     ┌──────────────────────────────────────┐
                     │        P+B+C+D+N 进化管线 (当前)      │
                     └──────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      P0 — 本周 (3-4天)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [P0-1 — NEW] trajectory_miner.py (daily cron)                  │
│    kanban.db completed tasks ──► LLM pattern detection          │
│    └──► REVIEW_QUEUE ──► user confirms ──► lessons/*.md        │
│                                                                  │
│  [P0-2 — NEW] Rule-Based Mutations Phase 1                      │
│    MUT-01: Lesson auto-upgrade (≥2 appearances → 🔴)           │
│    MUT-02: Cost threshold auto-tighten (15% per cycle)          │
│    └──► post_kanban_complete.py + cost-circuit-breaker.py      │
│                                                                  │
│  [P0-3 — NEW] Cross-task pattern checker hook                   │
│    pre-kanban_complete ──► review last 20 tasks in same domain  │
│    └──► flag known failure patterns                              │
│                                                                  │
│  [P0-4 — FIX] 行号污染清理 + Skills 去重                        │
│    regex cleanup on 8/9 SOUL.md files + dedup research-domain   │
│                                                                  │
│  [P0-5 — INTEG] EvoClaw daily summary into audit report         │
│    Already shipped: evoclaw_degradation_detect.py               │
│                                                                  │
│  ✅ 已交付资产:                                                  │
│    EvoClaw degradation cron │ GEPA 5 guardrails                 │
│    7 mutation templates (设计) │ audit_bd_layer.py              │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                      P1 — 本月 (4-5天)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [P1-1 — HIGHEST IMPACT] System Prompt 帕累托外移               │
│    Startup Protocol + Lessons 规范 + Data Bus → 共享文件         │
│    L3 内容外移到 skill/ref 文件                                  │
│    目标: research-domain 160→100行, finance 146→80行             │
│                                                                  │
│  [P1-2 — LOW EFFORT] Tool 描述 Top 10 修复                      │
│    security-auditor/whisper/graphify/llm-wiki 等                 │
│                                                                  │
│  [P1-3 — AUTO] Rule-Based Mutations Phase 2                     │
│    MUT-04: Cross-domain instruction reorder                     │
│    MUT-07: Rollback mode detection + auto-recover               │
│                                                                  │
│  [P1-4 — INFRA] Session trajectory store                        │
│    Enable session persistence for offline analytics             │
│                                                                  │
│  [P1-5 — META] Cumulative improvement dashboard                 │
│    B/D rate trends, lesson growth, decay activity               │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                      P2 — 研究储备 (10-15天)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [P2-1 — SMART] MUT-05 + MUT-06                                  │
│    Reverse lesson extraction from blocked tasks                  │
│    Historical experience matching injection                      │
│    Needs: text similarity tool                                   │
│                                                                  │
│  [P2-2 — CORE] 反思性失败诊断 (reflection/reflector.py)         │
│    Trajectory capture ──► LLM classification ──► structured      │
│    failure diagnosis ──► lessons DB                              │
│    Needs: trajectory store (P1-4)                                │
│                                                                  │
│  [P2-3 — AUTO] Skill 自动进化守护进程 (weekly cron)              │
│    High-freq lessons → skill patch → L2/L3 gate → apply         │
│    Needs: MUT-05/06 + review mechanism                            │
│                                                                  │
│  [P2-4 — EVAL] Pareto 候选体池评估                               │
│    Run rule-based mutations 4-6 weeks, evaluate necessity        │
│                                                                  │
│  [P2-5 — META] B+D effectiveness benchmark                       │
│    A/B comparison: with B+D vs without                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. Phase 0 资产盘点

### 本次项目已交付的资产:

| 资产 | 类型 | 状态 | 位置 |
|:-----|:-----|:-----|:-----|
| EvoClaw 退化检测脚本 | ✅ **已实现** | 31/31 测试通过, cron `cace2a5bd5ad` | `~/.hermes/scripts/evoclaw_degradation_detect.py` |
| EvoClaw 测试套件 | ✅ **已实现** | 13/13 TDD + 18 audit = 31 | `~/.hermes/scripts/tests/test_evoclaw_degradation_detect.py` |
| EvoClaw 历史数据库 | ✅ **已实现** | JSON 持久化 | `~/.hermes/metrics/evoclaw_history.json` |
| GEPA 5 护栏分析报告 | ✅ **已完成** | 105 行 | `gepa_survey_analysis.md` |
| GEPA + Survey 深度研读 | ✅ **已完成** | 256 行 | `gepa-self-evolving-analysis.md` |
| SkillClaw 对比报告 | ✅ **已完成** | 271 行 | `skillclaw_analysis.md` |
| 规则变异模板设计 | ✅ **已完成** | 555 行, 7 个模板 | `rule_based_mutations.md` |
| Tool 描述审计 | ✅ **已完成** | 286 行, 12 服务器 | `tool_description_audit.md` |
| System Prompt 优化 | ✅ **已完成** | 539 行, 9 反模式 | `system_prompt_optimization.md` |
| **本进化升级方案** | ✅ **已完成** | 本文件 | `evolution_upgrade_plan.md` |

### 待创建资产 (本阶段结束后):

| 待创建 | 预计工时 | 优先级 |
|:------|:--------|:-------|
| `scripts/trajectory_miner.py` | 1-2 天 | ⭐ P0 |
| `reflection/reflector.py` | 1-2 天 | ⭐ P2 |
| `mutation_orchestrator.py` | 1 天 | ⭐ P1 |
| `~/.hermes/startup-protocol.md` (共享引用) | 0.5 天 | ⭐ P1 |

---

## 附录: 参考文献

> ⚠️ 网络搜索不可用 (Tavily credit exhausted), 以下基于已分析论文的引用链

| 文献 | 来源 | 分析文件 |
|:-----|:-----|:--------|
| GEPA (Tao et al., ICLR 2026 Oral) — arXiv:2507.19457 | arXiv | `gepa_survey_analysis.md`, `gepa-self-evolving-analysis.md` |
| Self-Evolving AI Agents Survey — arXiv:2508.07407 | arXiv | `gepa-self-evolving-analysis.md` |
| SkillClaw (Ma et al., Apr 2026) — arXiv:2604.08377 | arXiv | `skillclaw_analysis.md` |
| EvoClaw — arXiv:2603.13428 | arXiv | `evoclaw_degradation_detect.py` (参考) |
| hermes-agent-self-evolution (Nous Research) | GitHub | `gepa-survey-analysis.md` |
| DSPy MIPROv2 (Khattab et al.) | Stanford NLP | `rule_based_mutations.md` |
| APE (Zhou et al., 2023) | ICLR 2024 | `gepa-self-evolving-analysis.md` |
| OPRO (Yang et al., 2024) | ICLR 2024 | Survey 引用 |
| Reflexion (Shinn et al., 2023) | NeurIPS 2023 | Survey 引用 |
| MemGPT (Packer et al., 2024) | arXiv | Survey 引用 |
| ToolGen (Cai et al., 2024) | ICLR 2025 | Survey 引用 |
| EvoFlow (Hu et al., 2025) | arXiv | Survey 引用 |
| PromptBreeder (Fernando et al., 2024) | GECCO 2024 | `gepa-self-evolving-analysis.md` |
| GRPO (Shao et al., 2024) | DeepSeek | `gepa-self-evolving-analysis.md` (对比) |
| WildClawBench | SkillClaw companion | `skillclaw_analysis.md` |

---

## [LESSONS]

- level: 🔴 CRITICAL
  domain: research-domain
  content: 综合进化升级方案关闭调研阶段 — 7 项子任务产出全部汇总, 核心结论是「安全基础设施我们领先, 自动化闭环是最大缺口」。P0 阶段 3-4 天可交付 trajectory miner + MUT-01/02 + 跨任务检查 + 行号修复。建议立即执行 P0 而非继续调研。
  context: t_f7386342 — 综合升级方案的 7 个子任务输入全部就绪, 无等待项。web_search 在最终阶段不可用(Tavily credit), 但生态地图已通过所有本地文件构建完成。

- level: 🟡 WARNING
  domain: research-domain
  content: Tavily API credit 在项目末期耗尽, 导致 8/8 的「生态地图」部分无法在线搜索最新文献。应在调研早期阶段(第 1-2 子任务)集中完成 Web 搜索, 避免末期依赖。
  context: t_f7386342 — web_search 返回 402 insufficient credit, 浏览器因 no-sandbox 不可用。生态地图基于已有论文的引用链构建。

- level: 🟢 INFO
  domain: research-domain
  content: 本项目的 7 项调研子任务产出了 7 个结构化 markdown 文件(总 ~55KB) + 1 个已实现脚本(378 行, 31/31 测试通过) + 1 个综合计划文档。这是 research-domain 目前为止最密集的调研周期 — 全部输出 5 天内完成。
  context: t_f7386342 — 回溯: 从 t_457f1d86 (EvoClaw) → t_ae9ffb59 (SkillClaw) → t_48bdb336 (Prompt审计) → t_5eed626c (Tool审计) → t_f6de2309 (变异模板) → t_f7386342 (综合方案)

- level: 🟢 INFO
  domain: research-domain
  content: 「自建 vs 借用 vs 忽略」决策框架首次用于综合升级方案 — 15 项进化能力中 5 项自建/4 项借用/2 项已实现/4 项忽略。GEPA 反思性诊断、SkillClaw 轨迹挖掘、Survey Three Laws 是最有价值的借用。
  context: t_f7386342 — 决策框架标准化输出, 可供未来论文对比任务复用
