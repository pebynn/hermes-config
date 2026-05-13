# 遗传算法轻量借鉴研究：P+B+C+D+N 系统基于规则的变异模板

> 研究日期：2026-05-13
> 状态：P2 研究储备 · 无代码实现
> 目标：在不安装 GEPA/DSPy 的前提下，将遗传算法的变异思想转化为可应用于 P+B+C+D+N 管线的规则模板

---

## 摘要

本报告研究 GEPA（Genetic Programming for Evolving Prompt Automata）和 DSPy MIPRO 中的核心变异算子，并设计了 7 个轻量级、基于规则的变异模板。这些模板无需 GA/GP 引擎或 DSPy 依赖，直接作用于 P+B+C+D+N 各层现有的 Python 脚本和 lessons 文件系统。每个模板包含触发条件、安全回滚机制和前后对比示例。可行性评估结论：**完全可行，无 DSPy 依赖，可直接在 `pre_kanban_create.py`/`post_kanban_complete.py` 等现有脚本中实现，约 150-250 行 Python 代码。**

---

## 1. 背景：GEPA 与 DSPy 的变异算子分析

### 1.1 GEPA（Tao et al., 2024）关键算子

| 算子 | 效果 | 在我们系统里的等价物 |
|------|------|---------------------|
| **RewriteNode** | 对提示词中某一段落进行 paraphrasing | 改写 lessons 条目的措辞以提升 worker 理解度 |
| **ReorderChildren** | 重排子指令顺序 | 重排 body 中 `lessons` 块的优先级顺序 |
| **ReplaceConstraint** | 收紧/放松某个约束条件 | 调整 `pre_kanban_create.py` 的成本阈值或 lessons 注入密度 |
| **ClarifyToolDesc** | 澄清工具/函数描述 | 优化 SOUL.md 中 worker 的工具描述 |
| **SwapInstruction** | 交换两个指令块的位置 | 重排 body 中 P/B/C/D/N 各层顺序 |
| **InsertExample** | 插入 few-shot 示例 | 从历史 kanban 任务提取成功案例注入 body |
| **MergeNodes/SplitNode** | 合并或拆分指令节点 | 聚合/拆分 lessons 文件中的条目 |

### 1.2 DSPy MIPROv2 关键机制

| 机制 | 效果 | 在我们的系统里的等价物 |
|------|------|------------------------|
| **Instruction Proposal** | 自动生成指令变体 | 从 `lessons/` 中的不同域 lessons 合成新的复合教训 |
| **Few-shot Selection** | 选择性注入示例 | 根据任务类型匹配最优的历史 lessons |
| **Constraint Tuning** | 贝叶斯参数调优 | 基于成本数据的自适应阈值调整 |

### 1.3 核心差异：GA 式 vs 规则式

| 维度 | GEPA/DSPy（GA 式） | 本方案（规则式） |
|------|-------------------|-----------------|
| 搜索空间 | 指数级随机搜索 | 确定性规则筛选 |
| 适应度函数 | 需 LLM 评分或用户反馈 | 无需额外评分（基于已收集的数据） |
| 依赖 | DSPy + LLM 调用循环 | 仅 `pre/post_kanban_create.py` 级脚本 |
| 收敛保证 | 无（局部最优风险） | 有（确定性触发 + 回滚） |
| 可解释性 | 低（黑盒变异） | 高（每步可 audit） |

---

## 2. P+B+C+D+N 基础设施概要

```
pre_kanban_create.py  ─── P+B 层 — lesson 注入 + 成本检查
  ↓
task body (enriched)  ─── 包含 lessons 块 + 原始 body
  ↓
worker 执行            ─── 读取 lessons + 按指导执行
  ↓
post_kanban_complete.py ─ D 层 — 解析 [LESSONS] 块 → 持久化到 lessons/ 文件
  ↓
cost-circuit-breaker.py ─ C 层 — 成本熔断，暂停高消费 cron
  ↓
rule_audit.py          ─ N 层 — 规则遵守审计 + 通知
```

### 关键文件

| 文件 | 层 | 行数 | 功能 |
|------|----|------|------|
| `scripts/pre_kanban_create.py` | P+B | 180 | 教训注入 + 成本检查 |
| `scripts/post_kanban_complete.py` | D | 206 | [LESSONS] 解析 + 持久化 |
| `scripts/bd_layer_enforce.py` | B+D | 99 | 一键 wrap + recover |
| `scripts/cost-circuit-breaker.py` | C | 93 | 成本熔断看门狗 ($8/day) |
| `scripts/rule_audit.py` | N | 116 | 规则遵守审计 (24h) |
| `lessons/` | B+D | — | YAML lessons 持久化仓库 |

### lessons 文件格式

每个 lessons 文件包含按严重级别分组的教训条目：
- `🔴 CRITICAL`：注入到 B 层，worker 首次工作时强制读取
- `🟠 HIGH`：可选注入，仅在相关任务中使用
- `🟡 INFO`：仅作知识积累，不自动注入

---

## 3. 7 个基于规则的变异模板

### MUT-01：Lesson 优先级自动升级（对应 GEPA：ReplaceConstraint）

**目的**：将反复出现的 🟡/🟠 lessons 自动升级为 🔴 CRITICAL，提高注入优先级。

**GEPA 映射**：约束收紧——当一个温和约束被多次违反时，自动收紧。

**触发条件**：
- `post_kanban_complete.py` 发现同一 content 被写入 ≥2 次
- 当前级别非 🔴 CRITICAL

**规则**：
```
if lesson.appearances >= 2 and lesson.level != "🔴":
    new_level = min(lesson.level + 1, "🔴")
    # 从 🟡 → 🟠 → 🔴 逐级升级
    migrate_to_critical_section(lesson)
    emit_alert("UPGRADE", lesson.content[:60])
```

**安全检查（回滚）**：
- 升级后 7 天内没有出现新同类教训 → 自动降回原级别
- 升级时在 `lessons/` 中保留 `previous_level` 字段

**示例 Before/After**：

```
Before (第1次出现, 🟡):
  - level: 🟡  domain: research  content: "task body > 3000 tokens时worker忽略尾部指令"

After (第3次出现, 自动升级为🔴):
  - level: 🔴  domain: research  content: "task body > 3000 tokens时worker忽略尾部指令"
  - previous_level: 🟡
  - appearances: 3
```

---

### MUT-02：成本阈值自适应收紧（对应 GEPA：ReplaceConstraint）

**目的**：根据历史成本数据动态调整各域的预算阈值，避免过度消费。

**GEPA 映射**：约束参数变异——根据历史适应度调整约束强度。

**触发条件**：
- 某域近 7 天日均成本 > $5.00（默认阈值）
- 且该域当前阈值未锁定（未被 `cost-circuit-breaker.py` 的 HIGH_COST_JOBS 覆盖）

**规则**：
```
new_threshold = max(3.00, current_threshold * 0.85)  # 每次收紧15%
update_domain_config(domain, "cost_threshold", new_threshold)
add_lesson(f"🔴 {domain}: 成本阈值自动收紧至${new_threshold:.2f}")
```

**安全检查（回滚）**：
- 如果收紧后该域 3 天内无 `blocked` 事件 → 保持收紧
- 如果收紧后触发 `cost-circuit-breaker.py` 熔断 → 自动恢复原阈值并标记 `lock`

**示例 Before/After**：

```
Before:
  cost_threshold = $8.00 (domain: research)
  7天日均成本 = $6.32

After:
  cost_threshold = $6.80 (15% 收紧)
  lesson: "research域成本阈值自动收紧至$6.80（原$8.00，因7天日均$6.32）"
```

---

### MUT-03：Task Body 智能精简（对应 GEPA：RewriteNode）

**目的**：对过长或重复的 task body 进行自动精简，提高 worker 信息密度。

**GEPA 映射**：重写节点——保留核心语义，消除冗余。

**触发条件**：
- `pre_kanban_create.py` 检测到 body > 2000 tokens
- 且 body 包含重复句式或修饰性语言（如 "请帮忙看看"、"能否分析一下"）

**规则**：
```
tokens = estimate_tokens(body)
if tokens > 2000:
    # 1. 提取所有 🔴 lessons 块（必须保留）
    # 2. 提取所有编号/列表/命令式语句（核心指令）
    # 3. 移除：客套语、重复描述、情感修饰
    # 4. 合并同类约束
    compressed = extract_core_instructions(body) + compact_lessons(lessons)
    dry_run: preview_diff(body, compressed)
```

**安全检查（回滚）**：
- 精简版 body 必须通过 `contains_all_critical_lessons()` 校验
- worker 返回结果中 `blocked` 事件增多 ≥50% → 回退到未精简版本并标记 `no_compress`
- 仅限 `--dry-run` 模式预览差异，永不自动替换（需人工确认）

**示例 Before/After**：

```
Before (2432 tokens):
  您好！我们有一个任务需要您帮忙分析一下。
  能不能看看这个research-domain最近7天的运营情况呢？
  我们需要重点关注以下几个方面：
  1. 首先，请查看cost数据
  2. 其次，再分析一下lessons的注入率情况
  3. 最后，希望您能给出改进建议
  麻烦您了，感谢您的帮助！

After (1248 tokens):
  任务：research-domain 7天运营分析
  1. 查看cost数据
  2. 分析lessons注入率
  3. 给出改进建议
  引用 lessons: [🔴 共3条 — 见下方]
```

---

### MUT-04：跨域 Instruction 重排（对应 GEPA：ReorderChildren）

**目的**：当任务跨越多个域时，按依赖关系自动调整指令执行顺序。

**GEPA 映射**：子节点重排——根据 DAG 依赖分析优化执行拓扑排序。

**触发条件**：
- body 中检测到 ≥2 个域的 assignee 关键字
- 或 body 包含明确的跨域流水线描述

**规则**：
```
domains_detected = detect_domains(body)
# 依赖序：P(pre_check) → B(inject) → C(cost) → D(recover) → N(audit)
ordered = topological_sort(domains_detected)
rewrite_body(body, instruction_order=ordered)
add_context_marker("CROSS_DOMAIN_REORDERED")
```

**安全检查（回滚）**：
- 重排后必须保持原始语义覆盖
- 在 body 头部插入 `⚠️ 本body已按P→B→C→D→N依赖序重排` 标记
- 如果 worker 返回错误 tagged as `order_confusion` → 恢复原始顺序

**示例 Before/After**：

```
Before:
  - 首先运行 rule_audit.py (N层审计)
  - 然后执行 pre_kanban_create.py (B层注入)
  - 最后检查成本 (C层)

After (按依赖序重排):
  ⚠️ 本body已按P→B→C→D→N依赖序重排
  - [P] 执行 pre_kanban_create.py (B层注入 — 需先注入lessons)
  - [C] 检查成本 (需在inject之后做成本估算)
  - [N] 运行 rule_audit.py (审计需在所有操作之后)
```

---

### MUT-05：反向 Lessons 抽取（对应 GEPA：InsertExample）

**目的**：从失败/blocked 任务的历史记录中反向抽取教训，填补 lessons 空白区域。

**GEPA 映射**：示例插入——从种群历史中提取有价值片段加入当前个体。

**触发条件**：
- 某域连续 3 个任务 outcome 为 `blocked` 或 `crashed`
- 且该 3 个任务的 `post_kanban_complete.py` 均产生 `lessons_found=0`

**规则**：
```
failed_tasks = get_recent_blocked_tasks(domain, count=3, days=7)
if all(t.lessons_found == 0 for t in failed_tasks):
    patterns = cross_compare_failures(failed_tasks)
    # 查找共通失败模式
    if patterns:
        draft = distill_lesson(patterns, domain)
        add_pending_lesson(domain, draft, level="🟠 HUMAN_REVIEW")
        # 需要人工审核，不自动注入
```

**安全检查（回滚）**：
- **永不自动注入** — 只生成 draft，标记为 `HUMAN_REVIEW`
- 注入前需要从 `lessons.md：HUMAN_REVIEW` 区移除该标记
- 如果 30 天后仍无人审核，自动标记为 `STALE`

**示例 Before/After**：

```
Before (3个blocked任务, 0个lessons产出):
  任务A: pre_kanban_create.py cost_blocked → worker还未注入就熔断
  任务B: 同域，同样 cost_blocked
  任务C: 同域，同样 cost_blocked

After (自动抽取):
  🟠 HUMAN_REVIEW domain: finance
  content: "当日成本>$6时不要创建新的kanban任务，等待次日凌晨自动恢复"
  context: "2026-05-13 finance-domain 3任务cost_blocked（<$8熔断线但>=$6预警线）"
```

---

### MUT-06：历史经验匹配注入（对应 GEPA：ClarifyToolDesc + InsertExample）

**目的**：为新 worker 或新任务类型自动匹配最相关的历史 lessons，提高首次成功率。

**GEPA 映射**：工具描述澄清 + 示例插入——根据上下文匹配最优示例。

**触发条件**：
- `pre_kanban_create.py` 检测到 task title 或 domain 与 lessons 文件中某条目的 `context` 字段匹配度 > 70%
- 或该 worker 是首次执行该域任务

**规则**：
```
title_tokens = tokenize(body)
best_lessons = []
for lesson in load_all_lessons():
    similarity = cosine_similarity(title_tokens, tokenize(lesson.context))
    if similarity > 0.7:
        best_lessons.append((lesson, similarity))

top = sorted(best_lessons, key=lambda x: x[1], reverse=True)[:3]
# 注入 top 3 lessons，优先于普通 lessons 显示
inject_with_priority(top, position="FIRST")
```

**安全检查（回滚）**：
- 注入后 worker 返回 blocked → 自动从 top 列表中移除该 lesson 并标记 `false_positive`
- 仅在 `pre_kanban_create.py` 的 `--dry-run` 模式下可用，生产模式需人工启用

**示例 Before/After**：

```
任务 title: "IC半衰加权因子权重研究"

Before (通用 lessons 注入):
  - level: 🔴  domain: research  content: "search credit不足时使用mcp_web_search"
  - level: 🔴  domain: finance  content: "计算IC时注意数据频率匹配"

After (历史匹配注入):
  ⭐ 历史经验匹配（基于title相似度87%）
  - [2026-05-11] IC半衰加权任务完成总结：IC_IR加权最优，夏普1.06
  - [2026-05-09] 注意IC计算时使用forward_returns而非close-to-close
  - [2026-04-28] 半衰参数lambda=0.94经验值，需按行业调节
  ---
  （后续通用 lessons 区）
  - level: 🔴  domain: research  content: "search credit不足时使用mcp_web_search"
```

---

### MUT-07：Rollback 模式检测与自动恢复（对应 GEPA：Fitness-based Selection）

**目的**：当某 worker 连续表现退化时，自动回退到上次成功状态组合。

**GEPA 映射**：适应度选择——淘汰低适应度个体，回退到精英个体。

**触发条件**：
- 同一 worker 连续 2 次任务 outcome 为 `blocked`
- 且最近一次成功的配置已记录在 `cost-circuit-breaker.py` 的快照中

**规则**：
```
worker_history = get_worker_runs(worker_id, limit=10)
recent_blocked = [r for r in worker_history[-3:] if r.outcome == "blocked"]

if len(recent_blocked) >= 2:
    last_good = worker_history[-3 - len(recent_blocked) - 1]  # 最近的success
    if last_good:
        rollback_config(worker_id, snapshot=last_good.config_snapshot)
        add_lesson(f"🔴 {worker_id}: 自动回退到{last_good.created_at}的配置")
        lower_cost_threshold(worker_id, factor=0.7)  # 降低成本阈值防复发
```

**安全检查（回滚）**：
- 回退前创建当前状态的快照（可以恢复）
- 仅回退 `pre_kanban_create.py` 和 `cost-circuit-breaker.py` 中的配置参数
- 不修改 `lessons/` 内容和 SOUL.md
- 记录到 `rule_audit.py` 的 N 层审计中

**示例 Before/After**：

```
Before:
  research-domain worker:
    任务A: blocked (cost meltdown + lesson not found)
    任务B: blocked (same cause)
    任务C: success (3天前, cost=$4.20, lessons_injected=5)

After:
  自动回退到任务C状态：
    - cost_threshold: $8.00 → $4.90 (70%)
    - lessons_inject_count: 3 → 5 (恢复)
    - add_lesson: "research-domain: 自动回退到2026-05-10配置，成本阈值降至$4.90"
```

---

## 4. 模板汇总矩阵

| 编号 | 名称 | GEPA 映射 | 作用层 | 触发频率 | 风险级别 | 自动化程度 |
|------|------|-----------|--------|---------|---------|-----------|
| MUT-01 | Lesson 优先级升级 | ReplaceConstraint | D → B | 低频 (≥2次/lesson) | 🟡 | 自动 |
| MUT-02 | 成本阈值自适应收紧 | ReplaceConstraint | C | 中频 (周级) | 🟡 | 自动 |
| MUT-03 | Task Body 智能精简 | RewriteNode | P | 中频 (长body时) | 🔴 | 仅dry-run |
| MUT-04 | 跨域 Instruction 重排 | ReorderChildren | P | 低频 (跨域任务) | 🟡 | 半自动 |
| MUT-05 | 反向 Lessons 抽取 | InsertExample | D → B | 低频 (失败模式) | 🟠 | HUMAN_REVIEW |
| MUT-06 | 历史经验匹配注入 | ClarifyToolDesc + InsertExample | B | 中频 (新任务时) | 🟠 | dry-run only |
| MUT-07 | Rollback 模式检测 | Fitness Selection | C | 低频 (连续失败) | 🟡 | 自动回退 |

### 自动化程度定义

| 级别 | 说明 |
|------|------|
| 自动 | 无需人工干预，直接在 `pre/post_kanban_create.py` 中实现 |
| 半自动 | 执行后通过 N 层（`rule_audit.py`）通知用户，30分钟内可撤消 |
| dry-run only | 仅生成预览差异，不自动执行修改 |
| HUMAN_REVIEW | 生成 draft 后标记等人，永不自动注入 |

---

## 5. 与 P+B+C+D+N 各层整合方案

### 5.1 代码变更量估算

| 层级 | 需要修改的文件 | 新增代码量 | 复杂度 |
|------|---------------|-----------|--------|
| B 层 | `pre_kanban_create.py` | +60 行 | 低 |
| D 层 | `post_kanban_complete.py` | +80 行 | 中 |
| C 层 | `cost-circuit-breaker.py` | +30 行 | 低 |
| N 层 | `rule_audit.py` | +40 行 | 低 |
| 新文件 | `mutation_orchestrator.py` | +60 行 | 中 |
| **总计** | **5 文件** | **~270 行** | **低** |

### 5.2 整合方案

```python
# mutation_orchestrator.py — 伪代码
# 在 pre_kanban_create.py 和 post_kanban_complete.py 之间作为钩子调用

class MutationOrchestrator:
    def __init__(self):
        self.templates = [
            LessonPromoter(),           # MUT-01
            CostThresholdAdapter(),     # MUT-02
            BodyCompressor(),           # MUT-03
            InstructionReorderer(),     # MUT-04
            LessonExtractor(),          # MUT-05
            HistoryMatcher(),           # MUT-06
            RollbackDetector(),         # MUT-07
        ]

    def on_pre_create(self, domain, body):
        """pre_kanban_create.py 完成后调用"""
        body = MUT-03.compress(body)            # 精简
        body = MUT-04.reorder(domain, body)      # 重排
        body = MUT-06.inject_history(domain, body)  # 历史匹配
        return body

    def on_post_complete(self, domain, result):
        """post_kanban_complete.py 完成后调用"""
        lessons = MUT-01.check_upgrade(domain)   # 升级检查
        MUT-02.adjust_threshold(domain)          # 成本复盘
        MUT-05.extract_lessons(domain)           # 反向抽取
        MUT-07.detect_rollback(domain)           # 回退检测
```

### 5.3 数据集成

各模板通过 `~/.hermes/` 下的现有数据源交互，不需新增数据库：

| 模板 | 数据源 | 写入目标 |
|------|--------|---------|
| MUT-01 | `lessons/*.md` 的 appearances 计数器 | 同级 lesson 升级标记 |
| MUT-02 | `data/cost_tracker.json` 的 by_day | `lessons/*.md` + 配置 |
| MUT-03 | `kanban.db` 的 task body | 仅 stdout dry-run |
| MUT-04 | `kanban.db` 的 parents 依赖链 | body 头部标记 |
| MUT-05 | `kanban.db` 的 run history | `lessons/*.md` 的 PENDING |
| MUT-06 | `lessons/*.md` + `kanban.db` title | body lessons 块首部 |
| MUT-07 | `kanban.db` 的 run outcomes | 配置文件 + `lessons/*.md` |

---

## 6. 可行性评估

### 6.1 是否可以无 DSPy 依赖工作？ ✅ 是

| 担心的依赖 | 实际情况 |
|-----------|---------|
| LLM 评分作为适应度函数 | 不需要 — 使用 `blocked rate` / `cost data` / `lesson appearances` 作为适应度信号 |
| DSPy 的自动提示重写 | 不需要 — 规则式替换（如 "must"→"should", "请"→""） |
| DSPy 的贝叶斯优化 | 不需要 — 使用固定倍率（15%/30%/70%）而非贝叶斯搜索 |
| DSPy 的 Teleprompter | 不需要 — `pre_kanban_create.py` 本身已经是 prompt 注入器 |
| 神经网络/梯度计算 | 不需要 — 所有决策基于计数和阈值比较 |

### 6.2 实现难度

| 模板 | 难度 | 关键挑战 | 估算工时 |
|------|------|---------|---------|
| MUT-01 | ⭐⭐ | 模糊匹配（内容相似度判定） | 2h |
| MUT-02 | ⭐ | 纯数值比较，逻辑简单 | 1h |
| MUT-03 | ⭐⭐⭐ | 语义保留 vs 精简平衡 | 4h |
| MUT-04 | ⭐⭐ | 跨域 DAG 依赖分析 | 2h |
| MUT-05 | ⭐⭐⭐ | 失败模式识别（需模式匹配） | 3h |
| MUT-06 | ⭐⭐ | 余弦相似度计算 | 2h |
| MUT-07 | ⭐⭐ | 快照管理 + 回退安全 | 3h |

### 6.3 潜在风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| MUT-03 过度精简丢失上下文 | worker 误判 | 仅 dry-run，永不自动替换 |
| MUT-02 成本阈值过度收紧 → 任务永远无法创建 | 管线阻塞 | 硬编码下限 $3.00，低于则警告 |
| MUT-01 误升级 → 🔴 lessons 泛滥 | B 层 token 膨胀 | 🟠 HUMAN_REVIEW 需要人工确认 |
| MUT-05/06 的相似度匹配 false positive | 注入无关 lessons | 最多 3 条 + N 层通知审计 |
| 模板之间相互干扰 | 不可预测的行为 | `mutation_orchestrator.py` 按优先级排序，低优先跳过 |

### 6.4 优先级建议

```
Phase 1（MVP，~4h）: MUT-01 + MUT-02 — 仅 D 层的统计数据驱动升级 + C 层的自适应阈值
  → 0 增加 token 消耗，对现有管线零侵入
  → 可立即在 post_kanban_complete.py 和 cost-circuit-breaker.py 中实现

Phase 2（~8h）: MUT-04 + MUT-07 — 跨域流水线优化 + 容错机制
  → 需要构建 mutation_orchestrator.py
  → 提升长线运行稳定性

Phase 3（~9h）: MUT-05 + MUT-06 — 智能化 lessons 注入
  → 需要相似度计算 + 模式匹配
  → 最大的 QoL 提升，但也需要最谨慎的回滚机制

Phase 4（可选）: MUT-03 — 仅 dry-run 预览
  → 需要评估收益后再决定是否启用
```

---

## 7. 结论

**不需要 GEPA 框架，不需要 DSPy 依赖。** P+B+C+D+N 管线现有的 `lessons/` 文件系统、`kanban.db` 运行历史、`cost-tracker.json` 成本数据已经提供了足够的信息素来驱动 7 个规则式变异模板。

核心思路：将遗传算法中的 **变异 → 评估 → 选择** 循环降级为 **规则触发 → 确定性变换 → 安全回滚** 三步。放弃指数级搜索空间换取确定性、可解释性和零额外 LLM 调用。

三条不需要 DSPy 的核心理由：
1. 适应度信号来自 `kanban.db` 的 `outcome` 字段和 `cost_tracker.json` 的成本数据，不需要 LLM 打分
2. 变异操作（重排/精简/升级）是字符串级别的确定性操作，不需要 GP 引擎
3. lessons 本身已经是经过人工验证的"优秀个体"，不需要 MIPRO 的贝叶斯搜索

**推荐立即执行 Phase 1（MUT-01 + MUT-02）**，两项加起来约 3h 工作量，对现有管线零侵入，即可获得 lessons 自动升级和成本自适应收紧的功能。

---

[LESSONS]
- level: 🟢
  domain: research
  content: "GEPA变异算子在没有GA引擎的情况下，可通过规则模板（trigger+safety+transformation）直接复用在P+B+C+D+N管线中"
  context: "遗传算法轻量借鉴研究完成，设计了7个模板，确认无DSPy依赖"
- level: 🟢
  domain: research
  content: "系统的blocked_rate/cost_data/lesson_appearances可作为GA适应度信号的替代品，不需要LLM评分"
  context: "研究了现有kanban.db + cost_tracker.json + lessons/的数据结构"
- level: 🟡
  domain: research
  content: "MUT-03（body精简）和MUT-05/06（智能注入）包含语义分析需求，需要实现或引入轻量级文本相似度工具"
  context: "跨域task title匹配需要cosine_similarity，当前infrastructure无此依赖"
