# GEPA论文 + Self-Evolving Agents Survey 分析报告
## 时间: 2026-05-13

---

## 一、GEPA核心机制

### 1.1 算法概述
GEPA (Genetic-Pareto Prompt Evolution) 是 ICLR 2026 Oral 论文，由 Nous Research 用于 hermes-agent-self-evolution。

**核心流程：**
1. 读取Hermes执行trace（trajectory.py）→ 理解失败原因
2. 基于trace生成定向变异（非随机变异）
3. DSPy module包装目标组件
4. batch_runner并行评估候选变异
5. 5道护栏过滤
6. 生成Git分支+PR，人工审核后合并

**关键特性：**
- 纯API调用，无需GPU（$2-10/run）
- 至少3个示例即可工作
- 优于RL和之前的DSPy优化器
- 操作文本（prompts/code strings），不做权重微调

### 1.2 GEPA 5道护栏

| # | 护栏 | 实现方式 | 我们的映射 |
|:--|:--|:--|:--|
| 1 | pytest全绿 | constraints.py: 变异后跑pytest tests/ -q，必须100%通过 | audit_bd_layer.py 新增 |
| 2 | 大小限制 | constraints.py: Skill≤15KB, tool描述≤500字符 | audit_bd_layer.py 新增 |
| 3 | 缓存兼容 | constraints.py: 检查不引入中间会话变更 | audit_bd_layer.py 新增 |
| 4 | 语义漂移 | fitness.py: LLM-as-judge对比原始目的 | audit_bd_layer.py 新增 |
| 5 | PR人审 | pr_builder.py: 自动生成PR+metrics，不进直接commit | 映射到L2/L3决策矩阵 |

### 1.3 四层进化目标

| Tier | 目标 | 价值 | 风险 | 我们的状态 |
|:--|:--|:--|:--|:--|
| Tier1 | SKILL.md文件 | 最高 | 最低 | ✅ B+D层已覆盖 |
| Tier2 | Tool描述 | 中 | 低 | ❌ 未覆盖 |
| Tier3 | System Prompt | 高 | 高 | ❌ 未覆盖 |
| Tier4 | 代码进化 | 最高 | 最高 | ❌ 未覆盖 |

---

## 二、Survey统一框架与我们的差距

### 2.1 四组件框架

| 组件 | Survey定义 | 我们的系统 | 差距 |
|:--|:--|:--|:--|
| System Inputs | 数据/查询输入 | kanban任务+用户消息 | 不缺 |
| Agent System | prompt/tool/reasoning | skills+profiles+SOUL.md | 缺tool描述优化 |
| Environment | 反馈源(用户/任务结果) | B/D层lessons回收+graphify | 缺执行trace结构化分析 |
| Optimisers | 自动调整机制 | P+B+C+D+N手动触发 | 缺自动触发+遗传算法 |

### 2.2 关键差距

1. **没有遗传算法层**：我们的P+B+C+D+N是手动/规则触发，GEPA是自动遗传搜索
2. **没有执行trace分析**：B层注入教训是静态的，缺"理解为什么失败"的能力
3. **护栏不够**：只有audit_bd_layer.py的B/D注入率检查，缺pytest/大小/语义/缓存检查
4. **缺少退化检测**：EvoClaw benchmark显示持续进化会导致80%→38%退化
5. **缺少遗忘机制**：lessons/只增不减，没有过期降权

---

## 三、可立即落地的改进建议（按优先级）

### P0 - 本周
1. **补5道护栏到audit_bd_layer.py**
   - 大小检查（skill≤15KB，tool≤500chars）
   - pytest集成（变更后自动跑关联测试）
   - 缓存兼容检查
   - 语义漂移检测（LLM对比原始目的）
   - 对应L2/L3决策矩阵的审查门禁

2. **lessons/加过期降权**
   - 每条lesson加时间戳
   - 超过90天未确认→降权
   - 超过180天→归档

### P1 - 本月
3. **执行trace分析**
   - 从kanban run logs提取失败模式
   - 结构化存储到lessons/
   - 供B层注入时引用

4. **退化检测cron**
   - 每日对比B/D注入率趋势
   - 连续3天下降→QQ Bot告警

### P2 - 研究储备
5. GEPA轻量借鉴：Rule-based变异替代遗传搜索
6. Tool描述优化：扫描现有tool描述→对比GEPA优化结果
7. 多Agent经验共享：跨域lessons共享机制

---

## [LESSONS]

1. GEPA核心价值在"读取trace理解失败原因"而非遗传算法本身——我们的B/D层缺trace-level分析，只做文本注入
2. EvoClaw发现持续进化会退化(80%→38%)——必须有回归检测和自动回滚，仅靠audit不够
3. Survey框架的Optimiser组件是我们最薄弱的环节——P+B+C+D+N没有自动化闭环
4. 5道护栏中，语义漂移检测最容易被忽略但对质量影响最大——LLM-as-judge值得投入
5. lessons/只增不减会导致信息过载——需要遗忘机制和置信度衰减
