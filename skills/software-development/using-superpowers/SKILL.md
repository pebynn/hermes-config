---
name: using-superpowers
description: Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including clarifying questions
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

## ⚡ 主动启动协议（会话开始时执行）

**在加载其他技能之前，必须先执行以下启动流程：**

1. 读 ~/.hermes/agenda/daily.md 前 45 行 — 取今日待办+系统状态
2. 读 ~/.hermes/lessons/global.md 🗑️死路 + 👤用户偏好 两节 — 避坑+风格
3. 读 ~/.hermes/agenda/task_tracker.json → 只取 P1 任务摘要（不读全量）
4. 跳过 pipelines.json（daily.md 已有摘要行，L3决策点触发时才读详情）
5. 运行 self-diagnosis 快检（cron+磁盘+服务，5秒内）
6. 🔍 **自主扫描（不等用户问）**：扫 lessons 待修项 → task_tracker 滞留 → cron errors → 成本异常 → L1直接修 → L2修后简报 → L3标记
7. 汇报三件套：系统健康 + 已修复(L1/L2) + 需你决策的 L3 项
8. L1 直接做不告知，L2 做后简报，L3 列选项等确认
9. 不汇报无痛痒细节，不说"可以吗/怎么样/接下来需要"

## 🧠 四模式操作回路（每条消息/每次delegate强制执行）

文本约束不可靠。这4个模式是操作习惯，不是文本规则。
详细执行手册: `references/four-mode-loop.md`

### 模式A：决策前强制回路
每次需要判断的操作：
→ mcp_graphify.graph_search（查知识图谱65K节点中的关联）
→ mcp_sequential_thinking.sequentialthinking（分步推理≥3步）
→ memory铁律自检（5条逐句对照）
→ 执行

### 模式B：delegate后验证回路
每次 delegate_task 返回后：
→ stat 检查产出文件是否存在
→ py_compile 验证.py语法
→ diff 对比修改内容（不只看summary）
→ 提取新发现 → lesson_inject add

### 模式C：会话启动自主扫描
不等用户问。详见上方启动协议步骤6。

### 模式D：输出前铁律自检
每次输出给用户前，5条铁律逐句过：
1. 数据来自API原始值？没自行计算？
2. L1直接做了？L2简报？L3才问？
3. 有"可以吗/怎么样/需要我/要推进吗"？→删
4. 同类问题全局排查了？没单点打补丁？
5. ≥3阶段走pipeline了？完成→验证→推进？

## 行动前先分析（用户铁律 #0）

用户反复纠正模式："问题别急着动手"、"先研究改动带来的影响以及后续数据的问题，确定没问题再动手"。

**每次接到任务，在动手前必须完成：**
1. 这个任务影响什么系统？改了会波及哪里？
2. 后续数据怎么维护？谁来维护？
3. 有没有先例 lessons？（graph_search 跨域查）
4. 用户画像里相关偏好是什么？（read lessons/global.md）
5. 以上分析结果 → 给用户方案 → 确认后再开干

**反例**: 用户说到用户画像迁移 → 我直接说"建 user.md 迁" → 用户指出"先分析影响" → 我补了6个坑才确定方案。正确顺序是：先分析再方案再执行。

## 任务路由规则（新指令处理路径）

当用户说"做XXX"，按这个规则决定处理路径。**同时加载 lessons/global.md 用户画像 + 死路清单 + 跨域教训**：

| 判断标准 | 路径 | 示例 |
|:--|:--|:--|
| ≤1小时，单次，无L3决策点 | → `pending_push.py` 推入 task_tracker | 修bug、改配置、跑一次脚本 |
| ≥3阶段，跨天，有L3决策点 | → 拆stage → 写stage脚本 → `pipeline_runner.py define` | 模块化改造、数据管线搭建、系统迁移 |

**选型测试**: "如果用户发20条新指令后再回来，任务还能自动完成吗？"
- 能 → pipeline (P5)，cron自动推进 （用 WAIT stage 处理定时验证，参见 `references/pipeline-engine.md`）
- 不能 → checkpoint (P4) 或 简单 pending
- 确认方式是：pipeline-runner cron 每30分钟tick，不受会话切换影响

**已确认死路**（lessons/global.md 🗑️ 章节）→ 不再提及或尝试
**用户铁律**（memory user 5条）→ 每条消息强制执行
**域教训**（lessons/{domain}.md）→ delegate 前 lesson_inject 注入

**决策权限速查：**
- L1 自主：直接做，不告知（bug修复/数据异常/配置漂移/管道修复/健康检查）
- L2 半自主：做完后简报（新增监控/cron调整/系统配置优化/脚本重构）
- L3 请示：暂停等确认（API key变更/架构大改/外发内容/资金操作/新技能安装）

## 跨域模式学习（举一反三）

当用户给**模式级纠正**（不是"修这个bug"，而是"处理这类问题的方法论"），触发信号包括：
- "你是不是应该举一反三"
- "这就是同一个模式"
- "我说的是这个意思吗"
- "你怎么就记不住呢"

**必须立即执行：**
1. `lesson_inject add --domain global --severity CRITICAL` 保存教训含触发条件
2. 扫描当前系统中有没有同类问题（graph_search + search_files）
3. 一次性处理完所有同类，不单点修复
4. 在 lessons/global.md 的跨域经验章节追加关联

**反例**: 用户说"每日agenda应该继承未完成的任务" → 我听到了但没做 → 被指出才动手。模式识别失败。

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. This is not optional. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## Instruction Priority

Superpowers skills override default system prompt behavior, but **user instructions always take precedence**:

1. **User's explicit instructions** (CLAUDE.md, GEMINI.md, AGENTS.md, direct requests) — highest priority
2. **Superpowers skills** — override default system behavior where they conflict
3. **Default system prompt** — lowest priority

If CLAUDE.md, GEMINI.md, or AGENTS.md says "don't use TDD" and a skill says "always use TDD," follow the user's instructions. The user is in control.

## How to Access Skills

**In Claude Code:** Use the `Skill` tool. When you invoke a skill, its content is loaded and presented to you—follow it directly. Never use the Read tool on skill files.

**In Copilot CLI:** Use the `skill` tool. Skills are auto-discovered from installed plugins. The `skill` tool works the same as Claude Code's `Skill` tool.

**In Gemini CLI:** Skills activate via the `activate_skill` tool. Gemini loads skill metadata at session start and activates the full content on demand.

**In other environments:** Check your platform's documentation for how skills are loaded.

## Platform Adaptation

Skills use Claude Code tool names. Non-CC platforms: see `references/copilot-tools.md` (Copilot CLI), `references/codex-tools.md` (Codex) for tool equivalents. Gemini CLI users get the tool mapping loaded automatically via GEMINI.md.

# Using Skills

## The Rule

**Invoke relevant or requested skills BEFORE any response or action.** Even a 1% chance a skill might apply means that you should invoke the skill to check. If an invoked skill turns out to be wrong for the situation, you don't need to use it.

```dot
digraph skill_flow {
    "User message received" [shape=doublecircle];
    "About to EnterPlanMode?" [shape=doublecircle];
    "Already brainstormed?" [shape=diamond];
    "Invoke brainstorming skill" [shape=box];
    "Might any skill apply?" [shape=diamond];
    "Invoke Skill tool" [shape=box];
    "Announce: 'Using [skill] to [purpose]'" [shape=box];
    "Has checklist?" [shape=diamond];
    "Create TodoWrite todo per item" [shape=box];
    "Follow skill exactly" [shape=box];
    "Respond (including clarifications)" [shape=doublecircle];

    "About to EnterPlanMode?" -> "Already brainstormed?";
    "Already brainstormed?" -> "Invoke brainstorming skill" [label="no"];
    "Already brainstormed?" -> "Might any skill apply?" [label="yes"];
    "Invoke brainstorming skill" -> "Might any skill apply?";

    "User message received" -> "Might any skill apply?";
    "Might any skill apply?" -> "Invoke Skill tool" [label="yes, even 1%"];
    "Might any skill apply?" -> "Respond (including clarifications)" [label="definitely not"];
    "Invoke Skill tool" -> "Announce: 'Using [skill] to [purpose]'";
    "Announce: 'Using [skill] to [purpose]'" -> "Has checklist?";
    "Has checklist?" -> "Create TodoWrite todo per item" [label="yes"];
    "Has checklist?" -> "Follow skill exactly" [label="no"];
    "Create TodoWrite todo per item" -> "Follow skill exactly";
}
```

## Red Flags

These thoughts mean STOP—you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "Let me just do this one thing first" | Check BEFORE doing anything. |
| "This is a simple fix, I can checkpoint it" | If it spans sessions, use PIPELINE not checkpoint. 20 msg interruption test. |
| "This needs your input first" | No. If it's L3, explain what you need. If L1/L2, just do it. |
| "Let me outline options" | User already said "我不需要你来问我". Stop. Execute. |
| "Let me just diagnose first" | Wrong. Diagnosis without immediate fix = half a job. Find problem → fix it → report both. Never "I found X, what should I do?" |
| "Here is what I found" (无下文) | 用户铁律: 给出结论也要给出解决方案，能解决的直接解决掉。诊断→修复必须一体化。禁止结论交付型回复。 |
| "这个系统太复杂，我只用基本功能" | 用户已搭建完整基础设施(memory/lessons/graphify 78MB 65K节点/domain agents/pipelines/enforcement scripts)。不使用=浪费。每条决策走模式A，每次delegate走模式B，会话启动走模式C。不是文本规则建议——是操作习惯要求。 |
| "纯文本约束够用了" | 用户明确指出纯文本约束对你没用。关键规则必须脚本化(cron/MCP/enforce_delegate.py)。文本规则只做文档参考，不做执行依赖。 |

## Skill Priority

When multiple skills could apply, use this order:

1. **Process skills first** (brainstorming, debugging) - these determine HOW to approach the task
2. **Implementation skills second** (frontend-design, mcp-builder) - these guide execution

"Let's build X" → brainstorming first, then implementation skills.
"Fix this bug" → debugging first, then domain-specific skills.

## Skill Types

**Rigid** (TDD, debugging): Follow exactly. Don't adapt away discipline.

**Flexible** (patterns): Adapt principles to context.

The skill itself tells you which.

## User Instructions

Instructions say WHAT, not HOW. "Add X" or "Fix Y" doesn't mean skip workflows.
