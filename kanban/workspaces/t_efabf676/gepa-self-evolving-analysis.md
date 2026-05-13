# GEPA + Self-Evolving Agents Survey — 研读报告

> 分析日期: 2026-05-13
> 来源: arXiv:2507.19457 (GEPA, ICLR 2026 Oral) + arXiv:2508.07407 (Survey) + github.com/NousResearch/hermes-agent-self-evolution

---

## 一、核心机制摘要

### 1.1 GEPA: Genetic-Pareto Prompt Evolution（ICLR 2026 Oral）

**核心洞见：** 语言是可解释的，比标量奖励的强化学习信号丰富得多。GEPA 用 LLM 阅读完整执行轨迹（推理链、工具调用、报错信息），通过自然语言反思诊断失败原因，定向修复。

**三根支柱：**

| 支柱 | 机制 | 效果 |
|------|------|------|
| **反思性提示变异 (Reflective Prompt Mutation)** | 执行候选体 → 捕获轨迹 + 反馈文本 → LLM 将成败归因到具体模块 → 生成定向修复 | 不是随机变异，而是"知道为什么失败再改" |
| **系统感知合并 (System-Aware Merge)** | 将 Pareto 前沿上多个互补候选体的经验合并到同一份提示中 | 避免贪心策略导致的局部最优 |
| **Pareto 前沿采样** | 对每个训练实例保留最佳候选体；从所有实例的 Pareto 最优集合中按出现频率采样下一个要变异的候选体 | 保持多样性，防止过早收敛 |

**关键数据：**
- 比 GRPO 好 6% 平均 (+20% 在某些任务)，使用 35x 更少的 rollout
- 比 MIPROv2 好 10%+（AIME-2025 +12%）
- 90x 更便宜：开源模型 + GEPA 击败 Claude Opus 4.1（Databricks 案例）
- $2-10/次 优化运行，无需 GPU

### 1.2 Self-Evolving AI Agents Survey（arXiv 2508.07407）

**统一框架：四组件反馈闭环**

```
系统输入 (I) → 智能体系统 (A) → 环境 → 优化器 (P) → 更新智能体系统
      ↑                                                       │
      └────────────────────── 迭代闭环 ────────────────────────┘
```

| 组件 | 内容 |
|------|------|
| **系统输入** | 任务级（提升整体性能）或实例级（优化单个样本） |
| **智能体系统** | 单智能体 / 多智能体架构 |
| **环境** | 基准数据集 / 动态真实环境 → 提供代理指标反馈 |
| **优化器** | 定义搜索空间 + 优化算法 → 更新智能体配置 |

**三大定律：**
1. **恒存律 (Endure)** — 自进化时必须保持安全和稳定
2. **增益律 (Enhance)** — 受第一条约束，必须保持或提升已有任务性能
3. **自治律 (Autonomize)** — 受前两条约束，必须能自主优化

**进化维度覆盖：**

| 维度 | 方法 | 代表工作 |
|------|------|---------|
| **模型行为** | 训练时 RL/DPO + 测试时推理策略搜索 | STILL-ALIVE, R-Zero, AlphaEvolve |
| **提示** | 编辑式/生成式/文本梯度/进化式 | GEPA, APE, OPRO, PromptBreeder |
| **记忆** | 短期（工作记忆压缩）+ 长期（结构化记忆/反思回放） | MemGPT, Reflexion, AMEM |
| **工具** | 训练时（ToolRL/ToolACE）+ 推理时（tool文档优化）+ 功能 | ToolGen, AdaTool, ReTool |
| **工作流** | 多智能体拓扑/角色/通信模式优化 | EvoFlow, AutoAgents, MAS-GPT |

---

## 二、GEPA 的 5 道护栏清单

> 来源：hermes-agent-self-evolution/PLAN.md（基于 GEPA 的工程落地规范，GEPA 论文本身没有定义这些护栏）

| # | 护栏 | 具体规则 | 技术验证 | 违反后果 |
|---|------|---------|---------|---------|
| 1 | **完整测试套件** | `pytest tests/ -q` 必须 100% 通过 | 每次变异后自动运行 | 零容忍，直接丢弃 |
| 2 | **大小限制** | Skill ≤15KB，工具描述 ≤500 chars，提示段落增幅 ≤20% | 长度惩罚项加入适应度函数 | 防止上下文窗口膨胀 |
| 3 | **缓存兼容性** | 新版本仅在新会话生效，绝不热替换正在进行的对话 | 部署时校验会话 ID | 破坏缓存→成本激增 |
| 4 | **语义保持** | 进化后文本不能偏离原始目的 | 适应度函数中的语义相似性检查 | 防止功能漂移（如代码审查技能变成摘要技能） |
| 5 | **PR 人类审批** | 所有变更走 PR 流程，绝不直接提交 | Git branch + gh pr create | 自动生成的代码必须经过人眼审查 |

**关键观察：** 这 5 道护栏是 GEPA 项目在 hermes-agent 上落地的工程约束，而非 GEPA 算法的理论属性。GEPA 算法本身的约束只有 Pareto 前沿维护（避免局部最优），其他 4 道是工程实践要求。

---

## 三、与现有系统的差距分析

### 现有系统组件速览

| 组件 | 缩写 | 作用 | 进化覆盖 |
|------|------|------|---------|
| Prompts | P | 系统提示、persona、行为指引 | 有手动调整 |
| Base/Benchmarks | B | 基准测试套件 | 被动运行，不进化为闭环 |
| Context | C | 上下文文件管理 | 静态 |
| Domain | D | 领域配置、收敛约束 | 静态规则 |
| N | ? | 可能是 Network 或 Notifications | — |
| 强制执行层 | B/D | 规则引擎/约束守卫 | 硬编码规则 |
| Lessons | — | 域教训回传 | 被动记录 |
| Graphify | — | 知识图谱 | 事后注入，非闭环 |

### 差距矩阵

| 维度 | GEPA / Survey 要求 | 当前系统状态 | 差距评级 |
|------|-------------------|-------------|----------|
| **进化闭环** | 读取执行轨迹 → 诊断失败 → 定向变异 → 评估 → 部署 | 无主动进化循环；lesson 是事后手动记录，不自动触发改进 | 🔴 **关键** |
| **反思性诊断** | LLM 阅读轨迹文本，用自然语言归因失败原因 | 无。错误信息只被记录，不经过总结-定向修复流程 | 🔴 **关键** |
| **Pareto 多样性** | 维护多个 Pareto 最优候选体，按频率采样 | 只有一个"当前最佳"。无候选体池，无多样性策略 | 🔴 **关键** |
| **自动评估 + 反馈函数** | µf 返回数值分数 + 文本反馈（编译错误、rubric 细节） | 只有二进制 pass/fail，无结构化反馈返回优化器 | 🟡 **重要** |
| **搜索空间定义** | 明确指定哪些模块（提示/工具描述/代码）可被变异 | 模块边界模糊，无进化搜索空间声明 | 🟡 **重要** |
| **跨组件联合优化** | 同时优化 prompt + tool description + 代码 | 每个组件独立调整 | 🟡 **重要** |
| **护栏自动化** | 5 道护栏自动执行，进化产物不自检 | lessons 和 graphify 是事后手动触发 | 🟢 **中等** |
| **持续进化** | MASE 范式：检测弱项 → 自动优化 → PR → 部署 | 无自动触发机制 | 🔴 **关键** |
| **多智能体拓扑** | 多智能体系统的角色/通信/拓扑自动优化 | 单智能体架构 | 🟢 **中等** |
| **安全性评估** | Three Laws 框架 + 基准回归监控 | 无系统安全评估 | 🟡 **重要** |

### 差距本质：从「被动记录」到「主动闭环」

```
当前状态：
  失败 → 人工调试 → 手动改 prompt → [可能] lessons 回传 → [可能] graphify
                                                                       ↑
                                                                  手动触发，慢

GEPA 闭环：
  失败 → 读取轨迹 → LLM 诊断 → 定向变异 → 自动评估 → Pareto 筛选 → PR → 部署
                                                                       ↑
                                                                  自动循环，快
```

---

## 四、可立即落地的改进建议（优先级排序）

### P0: 引入反思性故障诊断（~1-2天）

**现状：** 当 agent 出错时，错误被记录到日志/session 中，但不进行结构化失败归因。

**方案：**
```
错误触发 → 捕获最后一次交互的完整轨迹（user_msg + agent_reasoning + tool_results + output）
         → LLM 诊断：为什么失败？属于哪类问题？（tool_misuse / prompt_ambiguity / context_loss）
         → 将诊断摘要写入 lessons 数据库（含结构化分类）
```

**文件清单：**
- 新增 `reflection/reflector.py` — 轨迹捕获 + LLM 诊断
- 修改 `lessons/research-domain.md` — 增加故障分类 schema

### P1: 构建候选体池 + Pareto 采样（~3-5天）

**现状：** 只有一个"当前 prompt"版本，没有候选体版本管理。

**方案：**
```
候选体池（本地 JSON/DB）：
  - 每个 prompt/skill/tool-description 持有多个变异版本
  - 每个版本关联评估分数（per-task 粒度）
  - Pareto 前沿过滤 → 非支配候选体按频率采样
```

**文件清单：**
- 新增 `evolution/pool.py` — 候选体池管理
- 新增 `evolution/pareto.py` — Pareto 前沿计算
- 新增 `evolution/selector.py` — 采样策略

### P1: 结构化反馈函数 µf（~2-3天）

**现状：** 评估结果只有 pass/fail/score，没有可用于定向修复的文本反馈。

**方案：**
```python
def feedback_function(task_input, agent_output, expected_output) -> (float, str):
    score = compute_score(agent_output, expected_output)
    # 附加结构化文本反馈
    feedback = {
        "correctness": rubric_check(agent_output, expected_output),
        "efficiency": token_count_analysis(agent_output),
        "errors": extract_error_messages(agent_output),
        "behavior": behavioral_check(agent_output)  # tool选择是否合理
    }
    return score, format_feedback(feedback)
```

**影响：** 这是 GEPA 式反思性变异的前提条件。

### P2: 5 道护栏自动化（~2-3天）

**现状：** 大部分护栏靠人工检查。

**方案：**
- **护栏 1（测试套件）**: 每次变异后自动运行 `pytest`
- **护栏 2（大小限制）**: `evolution/constraints.py` 自动校验 + 长度惩罚
- **护栏 3（缓存兼容）**: 变异产物标记版本号，runtime 检查会话一致性
- **护栏 4（语义保持）**: LLM-as-judge 比较原版和变异版的语义相似度（≥0.8 阈值）
- **护栏 5（PR 审批）**: `gh pr create --fill` 自动生成 PR

### P2: 进化闭环触发机制（~3-5天）

**现状：** 所有改进都是人工发起的。

**方案：**
```python
# cron job: 每周检查
if skill_failure_rate > THRESHOLD:
    trigger_evolution(skill_name)
    # 自动运行反思+诊断+变异+评估→PR
```

**触发条件：** skill 失败率 > 20% / 用户纠错率上升 / 基准分数下降。

### P3: 知识图谱进化产物关联（~1天）

**现状：** graphify 是事后手动注入，不与进化流程关联。

**方案：** 进化产物自动写入知识图谱：
```
Evolved: skill_xyz v3 (parent: v2)
- 替换了什么：X 行 → Y 行
- 原因：failure_rate 从 25%→12%
- 关联 session/错误：session_ABC
```

---

## 五、[LESSONS]

```
[LESSONS]
- level: 🔴 CRITICAL
  domain: research-domain
  content: GEPA 的核心竞争力不在进化算法本身，而在"反思性诊断"——用 LLM 阅读执行轨迹的文本，而非只用标量奖励信号驱动优化。我们当前系统完全缺失这一层。
  context: 研读 GEPA 论文发现其 35x 比 RL 更高效的根源是自然语言轨迹反思而不是 Pareto 采样

- level: 🟡 WARNING
  domain: research-domain
  content: 现有 lessons + graphify 是事后人工触发机制，而 GEPA/self-evolving survey 框架要求的是自动化闭环（检测→诊断→变异→评估→部署）。差距不只是功能缺失，而是范式差异——从被动记录到主动进化。
  context: 对比现有系统和 self-evolving agent 四组件框架

- level: 🟡 WARNING
  domain: research-domain
  content: GEPA 论文的 5 道护栏实际是工程落地约束，不是理论创新。其中"语义保持"和"缓存兼容性"对我们系统的 lessons/graphify 自动注入最直接相关——进化后的 skill/prompt 必须通过语义相似度阈值才能进入 lessons 数据库。
  context: 分析 hermes-agent-self-evolution 项目的 guardrails 清单

- level: 🟢 INFO
  domain: research-domain
  content: Survey 论文的 "Three Laws"（恒存/增益/自治）可以作为 lessons 回传和 graphify 注入策略的质量框架——任何 lessons 必须满足"增强性"（至少不降低现有性能）才能被采纳到知识图谱。
  context: 阅读 survey 论文 2.3 节
```

---

## 六、数据契约注入

按照 DS-02 规范，本次调研结果将写入总线供 graphify 消费。

### 关键节点总结

| 节点 | 类型 | 关联关系 |
|------|------|---------|
| GEPA: 反思性诊断 | 算法机制 | 父: self-evolving-agent 框架 |
| GEPA: Pareto 采样 | 算法机制 | 父: 进化优化 |
| Survey: 四组件框架 | 理论框架 | 覆盖: model/prompt/memory/tool/workflow 进化 |
| Survey: Three Laws | 安全约束 | 关联: lessons 回传策略 |
| hermes-agent 5 道护栏 | 工程约束 | 映射: 测试/大小/缓存/语义/审批 |
