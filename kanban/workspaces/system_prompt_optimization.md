# System Prompt 优化调研报告

> 来源: GEPA Tier 3 (最高风险/最高回报进化目标)
> 日期: 2026-05-13
> 状态: P2 研究保留 — 需 L3 决策门禁后方可实施
> ⚠️ WARNING: System prompt 变更属高风险操作，本报告仅提供分析框架和参考方案，不经 L3 审批不得实施

---

## 目录

1. [Worker SOUL.md 全景扫描](#1-worker-soulmd-全景扫描)
2. [共性问题 (Anti-Patterns) 分析](#2-共性问题-anti-patterns-分析)
3. [GEPA 遗传帕累托优化原则](#3-gepa-遗传帕累托优化原则)
4. [3 个最问题 Worker 优化方案](#4-3-个最问题-worker-优化方案)
5. [实施路线图与风险](#5-实施路线图与风险)

---

## 1. Worker SOUL.md 全景扫描

### 1.1 活跃 Worker 一览

| # | Worker | 行数 | 字节 | 摘要 |
|:-|:-------|:----|:----|:-----|
| 1 | **code-domain** | 94 | 3,350 | 全栈开发，7步强制工作流，TDD |
| 2 | **finance-domain** | 146 | 7,067 | 量化投资，Mode切换，大量技能/工具 |
| 3 | **ops-domain** | 127 | 5,976 | 运维/SRE，CRITICAL约束前置，4层防御 |
| 4 | **ec-fulfillment** | 48 | 1,764 | 电商运营 — 差评拦截/DSR (薄) |
| 5 | **ec-listing** | 49 | 1,818 | PDD上架 (薄) |
| 6 | **ec-sourcing** | 51 | 1,960 | 17网选品 (薄) |
| 7 | **research-domain** | 160 | 6,801 | **最厚** — 研究分析，Mode切换，11技能 |
| 8 | **reviewer** | 56 | 2,121 | 内容审核，引用外部review-checklist |
| 9 | **writer** | 73 | 3,124 | 公众号写作，SEO优化，硬约束 |
| | **main (总指挥)** | 140 | 6,318 | 核心调度，不执行 |

### 1.2 行数与复杂度分布

```
research-domain ████████████████████████████████████ 160行 ← 最厚
finance-domain  █████████████████████████████████    146行
ops-domain      ███████████████████████████████      127行
main SOUL.md    █████████████████████████████████    140行 (总指挥)
───────────────────────────────────────────────────
code-domain     ████████████████████                 94行
writer          ████████████████                     73行
reviewer        ███████████                          56行
ec-sourcing     ███████████                          51行
ec-listing      ██████████                           49行
ec-fulfillment  ██████████                           48行
```

**发现**: 行数分布极不均匀(48→160行，3.3×差距)。3个EC worker(~50行)和reviewer(56行)属于"薄worker"，但同样携带完整的Startup Protocol和Lessons回传块，导致约40%的内容是重复模板。

### 1.3 全局 lessons.md 情况

| 域 | 大小 | 构建日期 |
|:--|:----|:---------|
| global.md | 14,304 | 2026-05-12 (最大) |
| ops-domain.md | 12,201 | 2026-05-12 |
| finance-domain.md | 6,359 | 2026-05-13 |
| writing-domain.md | 5,781 | 2026-05-11 |
| code-domain.md | 3,600 | 2026-05-13 |
| research-domain.md | 403 | 2026-05-07 (最小) |
| ec-domain.md | 1,071 | 2026-05-07 |
| quant.md | 402 | 2026-05-12 |

> lessons 文件大小差异极大 (403→14,304)，`research-domain.md` 仅 403 字节说明 lessons 回传机制在该域利用率极低。

---

## 2. 共性问题 (Anti-Patterns) 分析

### 2.1 🔴 A型: Startup Protocol 模板复制 (9/9 文件, ~81行浪费)

**位置**: 每个 SOUL.md §🚀 Startup Protocol

**问题**: 以下9行块在全部9个文件中**逐字重复**:

```markdown
## 🚀 Startup Protocol (MANDATORY — injected 2026-05-11)

Before ANY task execution, load domain knowledge:

1. **Graph Knowledge**: `graph_search(\"lesson:xxx\")` — query the 134K-node knowledge graph
2. **Domain Lessons**: `read_file(\"~/.hermes/lessons/xxx-domain.md\")` — load accumulated lessons learned
3. **This SOUL.md** is already in your context — re-read if uncertain about constraints

⏱️ Budget: ~30s startup overhead. Skip only if task body explicitly says \"no_startup\".
```

**影响**:
- 纯模板内容 9×9=81 行 (若按 160行上限的 SOUL 算，占 ~1%) — 但若作为 system prompt overhead 每天调用数十次，Token 浪费显著
- 如果 context-assemble 已经在注入此内容，则是**双重加载**
- 如果 context-assemble **没有**注入此协议，那每个 worker 需要自行 graph_search + read_file → 这30s开销在每个 worker 启动时重复消耗

**根本原因**: 没有中心化共享的"启动协议"。各 worker 独立维护拷贝。

**修复方向**: 抽取到 `global.md` 或 `~/.hermes/startup-protocol.md`，设计 context-assemble 确保在 worker 启动时自动注入 (注入一次，而非每 worker 自带一份)。

---

### 2.2 🔴 B型: Lessons 回传规范重复 (9/9 文件, ~90行浪费)

**每个 SOUL.md 末尾都有相同的 10 行 Lessons 回传块**:

```markdown
### Lessons 回传规范
kanban_complete 时在 summary 末尾附加 lessons 回传块：

[LESSONS]
- level: 🔴
  domain: <域>
  content: <具体教训描述>
  context: <触发场景>

级别说明：
- 🔴 CRITICAL — 系统级事故/级联故障
- 🟡 WARNING — 可恢复但需关注
- 🟢 INFO — 优化记录
```

**影响**: 9×10=90行纯模板，占 finance-domain 文件的 7%、code-domain 的 11%、ec-* 的 20%+。

**根本原因**: 此规范应通过 `bd_layer_enforce.py` 强制执行，而非在 prompt 中重复说明。worker 不需要"知道"规范细节 — 只需在 complete 时写上 `[LESSONS]` 块，`post_kanban_complete.py` 会解析它。

**修复方向**:
- SOUL.md 中仅保留一行: `完成时按 [LESSONS] 格式附教训 (post_kanban_complete.py 自动解析)`
- 具体 YAML 格式和级别说明移至 `global.md` 或 `bd_layer_enforce.py` 的文档

---

### 2.3 🔴 C型: 内容损坏 — 行号残留 (8/9 文件)

**8个文件**中有明显的行号修剪残留:

| 文件 | 受影响行 | 残留文本 |
|:-----|:---------|:---------|
| finance-domain:33 | `    23\|## 核心能力` | 前导空格+行号+竖线+内容 |
| ops-domain:32 | `    22\|**资深...` | 同上 |
| ec-fulfillment:16 | `     5\|## 核心能力` | 同上 |
| ec-listing:16 | `     5\|## 核心能力` | 同上 |
| ec-sourcing:16 | `     5\|## 核心能力` | 同上 |
| research-domain:36 | `    26\|## 核心能力` | 同上 |
| reviewer:16 | `     5\|## 核心能力` | 同上 |
| writer:29 | `    18\|## 核心能力` | 同上 |

**唯一干净的**: code-domain (94行，无残留)

**影响**:
1. 这是**内容损坏** — system prompt 中含有不正确的行号标记
2. 视觉上破坏文件格式，表明这些文件是在内容编辑过程中"带残余标记"保存的
3. 表明 SOUL.md 维护过程缺乏内容校验

**修复**: 直接 patch 删除所有 `\s+\d+\|` 前缀。

---

### 2.4 🟡 D型: 技能/工具重复 (research-domain)

research-domain 的技能列表中有**完全重复**:

```markdown
| `deep-research` — 9维度深度研究引擎               |  ← 第1次
| `deep-research` — 9维度研究引擎(...)               |  ← 第2次 (重复)
| `web-researcher` — 多源搜索(DuckDuckGo+Tavily)    |  ← 第1次
| `web-researcher` — 深度搜索+事实核查               |  ← 第2次 (重复)
```

同时，`web-researcher` 既出现在"可用工具"又出现在"配合技能"中，概念重叠。

**影响**: 重复条目浪费空间、混淆 behavior（两个同名的 deep-research skill，worker 加载哪个？）。

---

### 2.5 🟡 E型: 矛盾约束 — 绝对禁止 vs 快速模式 (code-domain)

code-domain §工作流纪律:

> **禁止**"这很简单不需要设计"、"先做一步再说"等跳过行为。

但 §运行模式:

> 默认strict模式：所有编码任务走完整7步。**除非任务body明确说"快速模式"**。

**矛盾所在**:
- "禁止跳过" vs "快速模式可以跳过"
- 当 task body 说"快速模式"时，worker 面临两难：遵逆行流纪律 say "禁止跳过" ？还是遵运行模式 say "允许跳过"？

**影响**: 造成 worker 的行为不确定性，可能出现时而跳过、时而不跳过的行为漂移。

**修复**: 明确定义快速模式的"跳过哪些步骤"，在 §运行模式 中用表格列出 strict vs 快速模式的差异。例如:

| 步骤 | strict | 快速模式 |
|:----|:-------|:---------|
| brainstorming | ✅ | ✅ (精简) |
| writing-plans | ✅ | ❌ |
| TDD | ✅ | ❌ |
| code-review | ✅ | ✅ (缩短) |

---

### 2.6 🟡 F型: 负向约束浪费 Token

code-domain 第29行:

> **不要试图用 skill_view 加载 superpowers:xxx 技能（会报错）。7步工作流已完整内嵌在本文件。**

**问题**: 如果 superpowers:xxx 在代码层面会报错，应该：
1. 修复报错问题，或
2. 在 skill_view 函数层面拦截并给出友好提示
3. 而不是在 system prompt 中占用 200+ 字符重复"不要"

更多负向约束示例:
- code-domain: "禁止'这很简单不需要设计'"
- writer: "禁止子代理生成内容直接发布"
- writer: "禁止仅代码检查就报'已验证'"
- main: "❌ web_search 替代 deep-research 协议"

**修复**: 负向约束应通过工具层拦截 + error message 实现，而非在 prompt 中列出。每移除一个负向约束省 50-200 tokens/次调用。

---

### 2.7 🟢 G型: 薄worker模板比例过高

| Worker | 总行数 | 模板内容行数 | 有效内容 | 模板占比 |
|:-------|:------|:------------|:---------|:---------|
| ec-fulfillment | 48 | ~19 (Startup 9 + Lessons 10) | 29 | **40%** |
| ec-listing | 49 | ~19 | 30 | **39%** |
| ec-sourcing | 51 | ~19 | 32 | **37%** |
| reviewer | 56 | ~19 | 37 | **34%** |

**影响**: 薄 worker 浪费约 40% 的 tokens 在重复内容上。

---

### 2.8 🟢 H型: 数据契约 (Data Bus) 独立性记录

每个 worker 都详细列出了 Data Bus 的数据流（生产者/消费者+总线路径），这些信息在单个 worker 视角下使用率很低:

- 大部分 worker 只在一个方向使用总线（要么生产、要么消费）
- 总线路径长度平均 ~100字符/条目
- 路径信息对 worker 自身的决策很少有用 — worker 应该"读取总线（如果存在）"而非被告知精确路径

**修复方向**: 将 Data Bus 表简化为"我读到什么/我写到什么"单行格式，完整 schema 引用外部文档。

---

## 3. GEPA 遗传帕累托优化原则

> GEPA (Genetic Pareto Evolution) 将 system prompt 视为一个"种群"，通过变异→选择→帕累托前沿→保留适应度高的基因模式。

### 原则 1: 模板基因抽取 (Boilerplate Extraction)

**基因型**: Startup Protocol + Lessons 回传格式 + 协作规则 → 属于"共享基因"，不应在每个个体中独立编码。

**操作**:
- 从所有 worker 中移除 Start Protocol block (9行×9)
- 从所有 worker 中移除 Lessons 格式定义块 (10行×9)
- 从所有 worker 中移除协作规则标准格式说明
- 统一放入 `~/.hermes/startup-protocol.md`，由 context-assemble 在合成 SOUL.md 时自动追加

**Token 节约**: ~180 行 → ~10 行引用行。每 worker 省 ~170 行。

---

### 原则 2: 行号污染修复 (Content Sanitization)

**操作**: 对所有 8 个受影响文件执行 regex 清理: `^\s+\d+\|` → 空字符串

**风险**: 极低（纯格式修复）

---

### 原则 3: 帕累托层分配 (Pareto-Layering)

每个 worker SOUL.md 的内容分成三层:

| 层 | 内容 | 留/移 | 节省潜力 |
|:--|:-----|:------|:---------|
| **L1 必选** (保留) | 身份声明、硬约束、核心能力、工作流、运行模式表 | ✅ 保留 | — |
| **L2 重要** (保留) | 工作准则/纪律、工具集概览、协作规范 | ✅ 精简 | ~20% |
| **L3 参考** (移到 skill) | 完整技能列表、完整工具描述、Data Bus 路径、沟通风格 | 📦 外移 | ~40% |

**L3 外移方式**: 引用 skill 或外部 `.md`，如:
```markdown
## 工具/技能（详见 skill:research-tools）
toolsets: ['web', 'search', 'file', 'terminal', 'skills']
```

vs 当前:
```markdown
## 可用工具集
toolsets: ['web', 'search', 'file', 'terminal', 'skills', 'session_search']
- web — web_search、web_extract 获取信息
- search — session_search 历史查阅
- file — 读取已有文档和资料
- terminal — 运行热词采集脚本...
- skills — 加载10个研究相关技能...
- mcp_web_search — Tavily 搜索（比内置更精准）
- mcp_web_extract — URL→Markdown...
...
```

Diffs: 40+ 行 → 2～3 行。

---

### 原则 4: 技能去重 (Deduplication)

**基因型**: 技能列表正确性 — 重复基因属于有害突变。

**操作**: 移除重复条目，规范化命名。

---

### 原则 5: 矛盾消解 (Constraint Deconfliction)

**操作**: 为所有支持 mode 切换的 worker 统一使用表格格式。code-domain 必须补全"快速模式"的步骤矩阵。

---

### 原则 6: 负向约束正向化 (Negation → Guardrails)

**基因型**: "不要做X" → 通过系统层级的 guardrail 让"X不可能发生"。  
**操作**: 将"不要试图用 skill_view 加载 superpowers"→ 移除，改在工具层拦截。将"禁止仅代码检查就报已验证"→ 保持，但缩短为"需实际运行验证"。

---

### 原则 7: 薄worker定额制 (Thin Worker Quota)

**定额**: 简单 kanban worker ≤ 40 行，复杂 worker ≤ 100 行。

| Current | Target | Delta |
|:--------|:-------|:------|
| research-domain 160 | ≤ 100 | -60 |
| finance-domain 146 | ≤ 100 | -46 |
| ops-domain 127 | ≤ 100 | -27 |
| code-domain 94 | ≤ 80 | -14 |
| writer 73 | ≤ 60 | -13 |
| ec-* 48-51 | ≤ 40 | -8~-11 |
| reviewer 56 | ≤ 40 | -16 |

---

## 4. 3 个最问题 Worker 优化方案

根据"行数最厚 + 问题最多 + 优化空间最大"标准，选定:

1. **research-domain** (160行 — 最厚 + 行号污染 + 技能重复 + 工具+技能重叠)
2. **finance-domain** (146行 — 次厚 + 行号污染 + 工具列表膨胀)
3. **code-domain** (94行 — 矛盾约束 + 负向指令密集 + 缺失mode表)

### 4.1 research-domain 优化方案

| 当前 | 问题 | 方案 | 节约 |
|:----|:-----|:-----|:-----|
| 9行 Startup Protocol | A型模板 | 引用外部文件 | -9 |
| 10行 Lessons 规范 | B型模板 | 留1行引用 | -9 |
| 行号残留 (line 36) | C型损坏 | 正则清理 | -1(修复) |
| deep-research×2 | D型重复 | 去重保留1条 | -2 |
| web-researcher×2 | D型重复 | 去重保留1条 | -2 |
| 11行工具列表 | F型膨胀 | 精简为2行概览 | -9 |
| 16行核心脚本+知识图谱注入 | L3内容 | 精简为链接 | -12 |
| 沟通风格 4行 | L3内容 | 移走或缩短 | -2 |
| 工作准则 6行+搜索策略4行 | 重复/可整合 | 整合为3条 | -7 |
| 热词采集管线5行 | 仅1个worker用 | 保留但精简 | -2 |
| 数据契约4行 | H型 | 精简 | -2 |

**优化后目标**: 160 → **~100 行** (-37.5%)

**优化后结构**:
```markdown
# research-domain — 研究分析专家
(引用: global.md#🔴CRITICAL | lessons/research-domain.md | graphify: lesson:research)

## ⚙️ 运行模式  [mode=default|researcher 表]
## 核心能力  [3-5行精简列表]
## 工作流程  [1管线图 + 简化准则]
## 工具集    [toolsets: ... — 1行 + 引用skill:research-tools]
## 协作规范  [1行Lessons指引 + 1行Data Bus引用]
```

### 4.2 finance-domain 优化方案

| 当前 | 问题 | 方案 | 节约 |
|:----|:-----|:-----|:-----|
| 9行 Startup Protocol | A型模板 | 引用 | -9 |
| 10行 Lessons 规范 | B型模板 | 留1行 | -9 |
| 行号残留 | C型损坏 | 修复 | -1 |
| 30+行脚本列表 | 清单膨胀 | 改为"详见~/quant/" | -25 |
| 12行关键规则 | 可精简 | 保留6条核心 | -6 |
| 10行工具表(table格式) | 膨胀 | 改为toolsets:行 | -8 |
| 12行配合技能表 | L3内容 | 改为参考行 | -10 |
| 5行沟通风格 | L3 | 缩短 | -2 |
| 5行交付物标准 | L3 | 移skill | -3 |
| 4行数据契约 | H型 | 精简 | -2 |
| 8行工作流 | 保留 | 无变化 | 0 |

**优化后目标**: 146 → **~80 行** (-45%)

### 4.3 code-domain 优化方案

| 当前 | 问题 | 方案 | 节约 |
|:----|:-----|:-----|:-----|
| 9行 Startup Protocol | A型模板 | 引用 | -9 |
| 10行 Lessons 规范 | B型模板 | 留1行 | -9 |
| 3行"superpowers会报错" | F型负向约束 | 移除(改为系统层) | -3 |
| "禁止跳过" vs "快速模式" | E型矛盾 | 补全mode表 | 0(改写) |
| 28行7步自检清单 | 膨胀 | 精简为5行checklist | -23 |
| 4行数据契约 | H型 | 精简 | -2 |
| 8行技术栈+工具链 | L3 | 缩短 | -4 |
| 16行7步工作流+说明 | 保留核心 | 合并为短列表 | -8 |

**优化后目标**: 94 → **~50 行** (-47%)

**关键改动**: 补全 mode 切换表，消除矛盾:

```markdown
| 步骤 | strict | 快速模式 |
|:----|:-------|:---------|
| brainstorming+plan | ✅ | ✅ (合并) |
| TDD | ✅ | ❌ |
| 编码 | ✅ | ✅ |
| debugging+code-review | ✅ | ✅ (缩短) |
| verification | ✅ | ✅ |
```

---

## 5. 实施路线图与风险

### 5.1 实施顺序

| 阶段 | 内容 | 影响 | 风险 | 依赖 |
|:----|:-----|:-----|:-----|:-----|
| **P0** 内容修复 | 行号污染清理 (8文件) | 极低 | <L1 | 无 |
| **P1** 模板抽取 | Startup Protocol + Lessons 规范移到共享 | 中 | L2 | context-assemble 确认 |
| **P2** 去重+精简 | 技能去重、工具列表精简 | 低 | L1 | 无 |
| **P3** 矛盾消解 | code-domain mode表补全 | 低 | L1 | 无 |
| **P4** 帕累托外移 | L3内容移入skill | 高 | L3 | skill文件需先创建 |

### 5.2 风险评估

| 风险 | 级别 | 描述 | 缓解 |
|:----|:-----|:-----|:-----|
| 模板抽取后 worker 缺乏启动指引 | 🟡 | 若 context-assemble 未注入协议 | 先在global.md中保留备份引用 |
| 帕累托外移后 worker 找不到工具信息 | 🟡 | 技能文件未更新 | 每个domain先创建tools-skills.md |
| 矛盾消解改变 worker 行为 | 🟡 | 快速模式行为变更 | 在 task body 中明确"快速模式"版约束 |
| 行号清理引入新错 | 🟢 | 正则替换可能伤及正常内容 | 每文件 diff review |

### 5.3 成本收益估算

假设每日每个 worker 被调用 10 次，system prompt 平均长度~6000 tokens:

| 优化 | 每worker节约 | 9 worker日节约 | 月度tokens节约 |
|:----|:------------|:--------------|:---------------|
| Startup+Lessons抽取 | ~200 tokens | 18,000 | 540,000 |
| 工具列表精简 | ~200 tokens | 18,000 | 540,000 |
| 帕累托外移 | ~400 tokens | 36,000 | 1,080,000 |
| 去重+矛盾消解 | ~100 tokens | 9,000 | 270,000 |
| **总计** | **~900 tokens** | **81,000** | **2,430,000** |

即每月节省约 240 万 tokens 的输入开销（按 deepseek-v4 价格约 ¥2-5/百万输入 tokens → 月省 ¥5-12）。

---

## 附录 A: 优化示例 (research-domain 草稿)

> 仅展示框架，需 L3 审批后完善细节

```markdown
# research-domain — 研究分析专家

> 📖 引用: global.md#CRITICAL | lessons/research-domain.md | graphify: lesson:research
> 启动协议见 global.md#startup-protocol | Lessons规范: kanban_complete时附加[LESSONS]块

**资深研究分析专家**：信息搜集、平台热词采集、趋势分析、报告撰写。

## ⚙️ 运行模式
主代理注入 mode= 切换:
| 约束 | default | researcher |
|:--|:--|:--|
| 采集数据 | ✅ | ✅ |
| 分析/推理 | ✅ | ❌ 只标记来源+待验证 |

## 核心能力
平台热词采集(淘宝/拼多多/抖音) | 网络搜索/交叉验证 | 竞品调研 | 趋势分析 | 报告撰写

## 工作流程
接收 → 拆子问题 → 多关键词搜索 → 深度提取 → 交叉验证 → 结构化输出
*需深度研究: 加载deep-research skill 9维度分析*

## 工具集
toolsets: ['web', 'search', 'file', 'terminal', 'skills']
MCP: web_search | web_extract | deep_research | llm_wiki | graphify
*详细工具说明: skill:research-tools*

## 配合技能 (skill:research-skills)
*10个技能: deep-research, web-researcher, compete, crawl4ai, scrapling, etc.*

## 数据总线
生产者: 调研结果→知识图谱 (DS-02) `~/.hermes/bus/research-to-graphify/`
```

对比当前 160行 → 约 50 行，信息密度翻倍。

---

## 附录 B: 行号污染修复脚本

```bash
# 对每个受影响的 SOUL.md 执行
for f in ~/.hermes/profiles/*/SOUL.md ~/.hermes/profiles/.archived/*/SOUL.md; do
  sed -i 's/^\s*[0-9]\+\s*|//' "$f"
  echo "Cleaned: $f"
done
```

> **注意**: 此脚本仅做演示，实施前需每文件 diff 确认。

---

## [LESSONS]

- level: 🟡
  domain: research-domain
  content: System prompt 优化调研揭示 9 大反模式 — A型(模板复制81行浪费)和B型(Lessons块90行浪费)是最严重的结构性问题，占薄worker 40%内容。帕累托外移Layer 3内容可将research-domain从160行压缩到~100行。
  context: t_48bdb336 — System Prompt 优化调研首次全worker扫描

- level: 🟢
  domain: research-domain
  content: 行号污染(8/9文件)是维护工具链问题 — 编辑SOUL.md时带行号保存。建议在 SOUL.md 编辑脚本中加入行号移除后处理hook。
  context: t_48bdb336 — 扫描发现8个SOUL.md文件有内容损坏

- level: 🟢
  domain: all-domains
  content: 薄worker(EC系)模板占比达37-40%。若统一抽取启动协议+Lessons规范，3个EC worker可压缩至~20行有效指令。
  context: t_48bdb336 — 薄worker模板率分析
