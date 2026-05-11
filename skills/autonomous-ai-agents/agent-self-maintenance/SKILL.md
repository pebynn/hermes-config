---
author: hermes-agent
description: 'Autonomous agent evolution via P+B+C+D+N architecture. Proactive agenda + ops autopilot + memory curator + knowledge pipeline (daily graph/session-miner/cross-domain sync) + Lesson injection + Real-time learning + Domain-aware feedback + Notification. v2.3 adds knowledge pipeline acceleration, model cost optimization, domain maturity scoring.'
name: agent-self-maintenance
version: 2.4.0
---
# Agent Self-Evolution (P+B+C+D+N Architecture)

## When to Use

- User asks about "自主进化", "自我优化", "自我学习", "autonomous evolution", "系统提效"
- User asks about "主动性", "自主能力", "proactive agent", "agent initiative"
- Designing how agents learn from mistakes and prevent recurrence
- Setting up a mechanism where lessons flow from main agent → sub-agents
- Building a proactive daily agenda system (agenda-driven execution)
- Designing decision authority boundaries (what to auto-execute vs. what to ask)
- Building a notification dispatch layer for proactive error alerts
- User wants the system to "get smarter over time" without manual intervention
- System-wide optimization: cost reduction, knowledge pipeline, domain maturity

## Class Definition

The task class is: **autonomous agent evolution via lesson injection + feedback loops**

This is NOT:
- Scheduled cron audit (v1.0 approach — obsolete)
- DSPy/GEPA prompt optimization (self-evolution skill — non-functional)
- Cost circuit breaker (autonomous-optimization-architect — separate concern)

This IS: a real-time, multi-layer learning system where user corrections, task failures, and discovered pitfalls are encoded as lessons, injected into every future delegation context, and automatically promoted to hard constraints when recurring.

## Architecture: P+B+C+D+N (v2.1)

```
                         ┌──────────────────────────────────┐
                         │   PROACTIVITY (P) - NEW v2.1     │
                         │   Startup Protocol + Agenda      │
                         │   + Decision Matrix (L1/L2/L3)   │
                         │   + Pipeline Advancement         │
                         └──────────────┬───────────────────┘
                                        │ drives execution
                         ┌──────────────┴───────────────────┐
                         │   NOTIFICATION (N)               │
                         │   QQ Bot                         │
                         └──────────────┬───────────────────┘
                                        │ alerts
┌──────────┐   corrects   ┌────────────┴─────┐
│  USER    │ ────────────→│   MAIN AGENT     │
└──────────┘              │                  │
                          │  B: Lesson       │
                          │  Injection       │
                          │  C: Real-time    │
                          │  Learning        │
                          └────────┬─────────┘
                                   │ delegate(context + LESSONS)
                          ┌────────┴─────────┐
                          │  SUB-AGENTS      │
                          │  (6 domains)     │
                          │  D: Self-Learning│
                          │  + Cross-Domain  │
                          └──────────────────┘
```

### P - Proactivity Layer (主动执行层, v2.1 新增)

Addresses the root cause of main agent passivity — it's not a compliance problem, it's an architecture gap. The agent was designed to be reactive (wait for user input). Four sub-layers fix this:

**P1 - Startup Protocol**: Every new session auto-loads the daily agenda, runs quick self-diagnosis, reports status, and starts executing L1 items without waiting for user instruction. Embedded in SOUL.md §2 + using-superpowers SKILL.md.

**P2 - Decision Authority Matrix**: Every action is pre-classified as L1 (do it silently), L2 (do it then brief), or L3 (pause and ask). Only L3 reaches the user. Embedded in SOUL.md §3.

**P3 - Pipeline Advancement**: Complex tasks auto-decompose into stages. Each stage self-verifies on completion and automatically advances to the next. Only pauses at L3 decision points. Embedded in SOUL.md dispatch table.

**P4 - Task Checkpoint & Resume (v2.4, implemented 2026-05-08)**: Cross-session task persistence. When a long-span task is interrupted (user sends new message, session ends), its state is saved to `~/.hermes/agenda/task_tracker.json` and auto-carried forward on next session. The `pending_push.py` script adds/list/marks-done tasks. The `checkpoint_save.py` script records per-stage progress within a multi-phase task (stage N/M with produced artifacts). The `agenda_builder.py` v2.1 auto-inherits pending tasks across days with day counters and auto-promotion (3d→⚠️, 5d→🔥, 7d→🚨). See `references/task-checkpoint-resume.md`.

P5 - Cron Pipeline Engine (v2.5, implemented 2026-05-08): Long-span task execution via cron-driven pipeline. Addresses the root cause of failed multi-phase tasks — not interruption (P4 covers that), but the fundamental unreliability of executing long work within a session that gets context-switched by new user messages. The fix: offload execution to cron, keep orchestration in design.

P6 - WAIT Stage Type (v2.6, implemented 2026-05-08): Time-based pipeline advancement. A WAIT stage has no script — only an `until` field. The pipeline runner compares current time vs target on every tick. Not expired → silent skip. Expired → auto-advance to next stage. Supports relative ("7d", "30d") and absolute ("2026-06-07", "2026-06-07T00:00") formats. Used for observation periods, delayed evaluations, and scheduled checks. Example:

```json
{"id": 4, "desc": "观察 data_guard 稳定性", "level": "WAIT", "until": "7d"}
{"id": 1, "desc": "等待评估日期", "level": "WAIT", "until": "2026-06-07"}
```

When a pipeline reaches a WAIT stage, it stays in `running` state (not `paused`). The cron ticks silently check the date. No user notification for WAIT — only when WAIT expires and the subsequent verification stage completes with findings.

**Real-world test results (2026-05-08):**

| Test | Stages | Result |
|:--|:--|:--|
| signal_engine ↔ chan_buy_signal 接口解耦 | 4 stages (Protocol→import→verify→L3 cleanup) | ✅ Stage 1-3 auto-completed, L3 paused->resumed->completed. End-to-end verified. |
| 共享工具函数合并 (safe_float+scrub_ai) | 3 stages (shared module→7 scripts→verify) | ✅ 10 function definitions removed across 7 files, all through shared import. Completed in one cron tick cycle. |

**Lessons from test:**
- Stage scripts must be idempotent (detect "already done" and skip silently)
- Shell escaping breaks when scripts contain emoji/Chinese in JSON-encoded pipeline definitions → use standalone .py scripts, not inline shell commands
- L3 pause+resume flow works: pause→notify_user→task_tracker→startup_protocol→resume→complete
- The pipeline approach is overkill for single-session tasks (use checkpoint instead). Essential for cross-day tasks.

Key insight distinguishing P5 from P4: checkpoint saves state when interrupted, but the **next session still has a cold-start cost** (re-reading code, rebuilding context). P5 solves this by making each stage a self-contained script that cron executes independently. The orchestrator designs the pipeline once; cron executes all stages. No session needed.

Infrastructure:
- `~/.hermes/scripts/pipeline_runner.py` — Engine: tick/status/resume/define. A cron job (fc7f76d16dd3, */30 * * * *) automatically advances active pipelines stage by stage.
- `~/.hermes/agenda/pipelines.json` — Pipeline definitions and state. Supports L1 (auto-advance), L2 (auto-advance with briefing), and L3 (pause, wait for user decision) stages.
- L3 decision flow: pipeline pauses → notify_user writes to task_tracker → next session startup protocol asks user → user decides → orchestrator calls `pipeline_runner.py resume <id>` → pipeline continues.
- Each stage is a Python script with verify= pattern (file exists:/path or shell command exit 0).
- Idempotent stages: scripts detect "already done" and skip (changes=0 but exit 0).
- See `references/pipeline-engine.md` for full design.

Pipeline lifecycle: running → paused(waiting_user) | failed | completed.
agenda_builder.py v2.1 displays active pipelines in daily.md pipeline section.
The startup protocol (using-superpowers) now checks pipelines.json before reporting status.

Architecture:
```python
# Defining a pipeline (in session):
pipeline = {
    "id": "pipe-signal-decouple",
    "goal": "signal_engine ↔ chan_buy_signal 接口解耦",
    "stages": [
        {"desc": "提取 Protocol", "script": "stage1.py", "verify": "file exists:/path", "level": "L1"},
        {"desc": "改 import", "script": "stage2.py", "verify": "", "level": "L1"},
        {"desc": "隔离验证", "script": "stage3.py", "level": "L2"},
        {"desc": "清理决策", "level": "L3"}   # L3 pauses pipeline
    ]
}
# Then: python3 pipeline_runner.py tick  # cron does this automatically
```

See `scripts/pipeline_runner.py` for the engine. See `scripts/pipeline_stage_1_protocol.py`, `pipeline_stage_2_import.py`, `pipeline_stage_3_verify.py` for stage script patterns (all idempotent, self-contained, with verification).

**Infrastructure**: `~/.hermes/agenda/daily.md` (cron-generated daily at 08:00) + `pending.md` (deprecated — use pending_push.py instead) + `pipeline.yaml` (task dependency definitions) + `state.json` (trend tracking across daily runs) + `task_tracker.json` (task database with day counters, replaces tasks/ directory approach).

**Autonomous Ops Layer (v2.2)**: Two LLM-driven crons close the loop between detection and action:

| Cron | ID | Schedule | Role |
|:--|:--|:--|:--|
| `ops-autopilot` | bd5de39ac76e | 08:05 daily | Reads daily.md → auto-fixes L1/L2 → QQ-pushes L3 summary |
| `memory-curator` | 2698791c5f60 | 02:00 daily | Checks memory usage → if >85%: consolidates/merges/upgrades to skills |

**Knowledge Pipeline (v2.3)**: Four crons accelerate knowledge flow from sessions → lessons → skills → wiki → graph:

| Cron | ID | Schedule | Role |
|:--|:--|:--|:--|
| `wiki-soul-sync` | 70762cf8bf22 | 04:00 daily | SOUL.md → ~/brain/soul/ auto-copy (no_agent) |
| `graphify-daily` | e1917ae814df | 03:00 daily | Knowledge graph incremental update (was weekly) |
| `session-miner` | 8b9037f1fbdf | 04:10 daily | Scans recent sessions → extracts new lessons (LLM). v2 hard limits: 15min timeout, 50 batch, 3s interval, 5 deep-analysis, no recursion. |
| `cross-domain-sync` | 03ca993eb819 | 04:30 daily | Detects cross-domain lesson applicability → global.md (LLM) |
| `cost-circuit-breaker` | b720fd552d39 | hourly | Auto-pauses session-miner + 周度自优化 if daily cost >$8.00 (≈¥57) (no_agent) |

**Cost Optimization (v2.3)**:
- Main agent model downgraded: deepseek-v4-pro ($2.8/1M) → deepseek-v4-flash ($0.28/1M) — 10x savings, est. $79/month
- Requires gateway restart to take effect: `systemctl --user restart hermes-gateway.service`
- Reasoning: orchestrator does text classification + routing only, no analysis/code/creation
- Skill pruning: 12 empty/unused categories deleted, 31→19 categories
- Memory: consolidated from 98%→67% (removed duplicates already in lessons/SOUL.md)

**Domain Maturity (v2.3)**:
- `domain_maturity.py` script: 6-dimension scoring (SOUL size, scripts, crons, lessons, tools, autonomy)
- Weekly cron `af78affac0c7` (Sunday 06:00): auto-generates maturity report
- Baseline scores: code 84% > ec 73% > writing 71% > ops 69% > research 62% > finance 46%
- Lesson promotion accelerated: 3 corrections→SOUL.md now 2 corrections→SOUL.md (50% faster)

Full design docs: `references/proactive-agenda-framework.md` + `references/autonomous-ops-pipeline.md` + `references/knowledge-pipeline-v2.3.md`

### B - Lesson Injection (前置注入)

In the instruction pipeline, step [1.5] automatically loads domain-specific lessons and injects them into delegate context BEFORE sub-agents receive the task:

```
User instruction
  → [1] MCP optimize → domain, priority
  → [1.5] lesson_inject(domain) → read ~/.hermes/lessons/{domain}.md + global.md
  → [2] context-assemble (session + skill + graph + LESSON_BLOCK)
  → [3] delegate_task(goal, context=enriched_context_with_lessons)
```

The lesson block is formatted prominently at the TOP of context:

```
╔══════════════════════════════════════╗
║  ⚠️ 已知陷阱 - 本次任务必读         ║
║  [🔴CRITICAL] ...                   ║
║  [🟠HARD] ...                       ║
║  [🟡INFO] ...                       ║
╚══════════════════════════════════════╝
```

### C - Real-time Learning (实时学习)

When user corrects or criticizes, the main agent immediately:

1. Extracts the lesson as one concise rule
2. Writes to `~/.hermes/lessons/{domain}.md`
3. If same lesson has been corrected ≥3 times → promotes to `profiles/{domain}/SOUL.md` as hard constraint

Three severity tiers with automatic promotion:

| Tier | Severity | Trigger | Storage | Effect on sub-agent |
|:--|:--|:--|:--|:--|
| L1 | 🟡 INFO | Corrected 1x | `lessons/{domain}.md` | Context bottom |
| L2 | 🟠 HARD | Corrected 2x | `lessons/{domain}.md` (⚠️ prefix) | Context middle, prominent |
| L3 | 🔴 CRITICAL | Corrected ≥3x | `profiles/{domain}/SOUL.md` | Hard constraint, unskippable |

### D - Domain-Aware + Sub-Agent Learning (域感知+子代理学习)

**Lesson store structure:**
```
~/.hermes/lessons/
├── code-domain.md
├── ec-domain.md
├── finance-domain.md
├── writing-domain.md
├── ops-domain.md
├── research-domain.md
└── global.md          # Cross-domain lessons
```

**Sub-agent reverse learning:** Sub-agents can return lessons discovered during execution:

```
Sub-agent response format:
  status: done
  需要: 无
  lessons:                          # NEW field
    - "17网反爬升级，搜索结果需等5秒"
    - "PDD材质按钮React事件变更，fill后需额外dispatchEvent"
```

Main agent auto-appends these to the domain's lesson file.

**Cross-domain propagation:** Lessons applicable to all domains go to `global.md`. Example: "DeepSeek抖动时走智谱fallback."

### N - Notification Layer (通知层)

Routes events by priority to push channels. **Primary delivery: QQ Bot** (gateway WebSocket, `qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12`). WeChat iLink is deprioritized (rate-limited, unreliable). All 12 delivery-required crons now route through QQ Bot.

| Priority | Event | Channel | Timing |
|:--|:--|:--|:--|
| 🔴 P0 | Circuit breaker trip, system outage | QQ Bot immediate | Real-time |
| 🟠 P1 | Cron failure, data issue | QQ Bot + notify.py queue | Real-time |
| 🟡 P2 | Lesson promotion, pattern detected | Daily digest (QQ Bot) | 21:00 batch |
| 🟢 P3 | Task completion, routine | Daily digest (QQ Bot) | 21:00 batch |
| 🔵 Evol | Self-evolution events | Local log + digest | 21:00 batch |

**Active notification & ops infrastructure:**

| Component | Path / ID | Mode | Schedule |
|:--|:--|:--|:--|
| `notify.py` | `~/.hermes/scripts/notify.py` | File-queue → QQ Bot (PushPlus/Server酱 removed 2026-05-08) | On-demand |
| `daily-digest` | cron `d097864fb3ad` | QQ Bot batch summary | Daily 21:00 |
| `cron-failure-watchdog` | cron `00945f068dab` | Error log scanner + QQ Bot push | Every 30min |
| `cost-daily-report` | cron `c7dd3abfacf8` | QQ Bot cost summary | Daily 00:30 |
| `agenda-builder` | cron `e512e447fb29` | System health → daily.md (script-only, zero token) | Daily **00:00** (changed from 08:00 to auto-generate for the coming day) |
| `ops-autopilot` | cron `bd5de39ac76e` | Reads daily.md → auto-fix L1/L2 → QQ Bot L3 report (LLM) | Daily 08:05 |
| `memory-curator` | cron `2698791c5f60` | Memory >85% → consolidate/upgrade/prune (LLM) | Daily 02:00 |

**Watchdog design** (`watchdog_cron_failures.py`, 245 lines):
- Scans `~/.hermes/logs/errors.log` for ERROR entries in last 30 minutes
- Filters 12 noise patterns (asyncio task cleanup, rate limiting, DNS failures, CDP connection refused, session summarization 429s)
- SHA256 fingerprint dedup: same error not re-alerted within 30 minutes
- State file `~/.hermes/data/watchdog_state.json` tracks last check + alerted fingerprints
- Zero-cost: `no_agent=true` script-only cron, no LLM tokens consumed
- Silent when healthy: empty stdout → no push; only outputs when real errors found
- See `references/watchdog-cron-failures.md` for full design doc

## Implementation

### Phase 1: Lesson Infrastructure
1. Create `~/.hermes/lessons/` directory with 7 files (6 domains + global)
2. Migrate existing 7 blocked lessons from main agent memory to domain files
3. Add [1.5] lesson_inject step to main SOUL.md instruction pipeline

### Phase 2: Learning Loop
4. Implement real-time lesson extraction on user correction
5. Implement auto-promotion counter (≥3 → SOUL.md)
6. Add `lessons:` field to sub-agent response format

### Phase 3: Notification
7. QQ Bot is the primary delivery channel. All cron deliveries route through qqbot.
8. Configure notification dispatch script
9. Route all cron deliveries through QQ Bot (deliver: qqbot:...)

### Phase 4: Audit Cron
10. Daily cron: scan session failures → extract new lessons
11. Weekly cron: audit lesson effectiveness (same error still happening?)
12. Weekly digest: what was learned, what was promoted, what was fixed

## Key Finding (2026-05-07 Audit)

7/10 critical lessons are locked in main agent memory and NEVER reach sub-agents. The top blocked lessons:

- "数据铁律: 禁止自行计算涨跌幅" — corrected 3x, still blocked
- "Sina API parts映射铁律" — corrected 2x, still blocked
- "PDD API对个人不可行" — corrected 3x, still blocked
- "渲染验证铁律" — corrected 2x, still blocked

This is the root cause of repeated user corrections. B+C+D+N directly addresses this by injecting lessons into every delegate context.

## Related Skills

| Skill | Relationship |
|:--|:--|
| `self-diagnosis` | Health checks used by startup protocol (P layer). Also supplemented by agenda_builder.py v2.0 automated daily scan. |
| `self-evolution` | DSPy-based — **DELETED 2026-05-08** (non-functional, superseded) |
| `autonomous-optimization-architect` | Cost optimization + circuit breaker — complements notification layer |
| `soul-maintenance-audit` | SOUL.md trimming — phase 3 of context slimming |
| `reactive-skillify` | Lesson extraction on correction — used by C layer |
| `using-superpowers` | Startup protocol + decision matrix embedded for every new session |

## Supporting Files

| File | Purpose |
|:--|:--|
| `references/proactive-agenda-framework.md` | Full design doc for P layer: startup protocol, decision matrix, pipeline, agenda infra |
| `references/autonomous-ops-pipeline.md` | v2.2 ops pipeline: ops-autopilot + memory-curator + pipeline.yaml design |
| `references/d-layer-implementation.md` | How to implement sub-agent lesson feedback: SOUL.md patches, contract format, verification |
| `references/memory-consolidation-playbook.md` | When memory >85%: cleanup priorities, merge/delete patterns, retention rules |
| `references/knowledge-pipeline-v2.3.md` | v2.3 knowledge pipeline: 4 daily crons, session mining, cross-domain sync, cost analysis |
| `references/lessons-blocked-audit-2026-05-07.md` | Audit of 7 blocked lessons in memory |
| `references/session-miner-runaway-2026-05-10.md` | session-miner 10h runaway incident: root cause, cost, required guards |
| `references/constraint-enforcement-pattern.md` | Text→script enforcement: why pure-text SOUL.md rules fail, three-tier enforcement design |
| `references/system-audit-pattern.md` | 2026-05-10: comprehensive system audit checklist — lessons, config contradictions, task_tracker, cron, skills, memory |
| `references/5-way-audit-pattern.md` | 5-domain parallel audit methodology with model upgrade/restore, severity triage |
| `references/publish-fallback-pattern.md` | 3-tier publish degradation: fix sub-agent bypass pattern (API→Cookie→Browser→Local) |
| `references/bcdn-architecture.md` | Original BCDN architecture design |
| `references/notification-channels-china.md` | China-specific notification channel analysis |
| `references/watchdog-cron-failures.md` | Cron failure watchdog design |
| `references/task-checkpoint-resume.md` | P4: Cross-session task state persistence + resume protocol |
| `references/pipeline-engine.md` | P5: Cron-driven pipeline execution for long-span tasks |
| `references/pattern-generalization.md` | Cross-domain lesson linkage: solving "举一反三" via user.md + lessons + graph |
| `references/knowledge-architecture.md` | 2026-05-09 重构: memory(5铁律) + lessons(全文) + graph(索引) 三层架构 |
| `scripts/checkpoint_save.py` | Per-stage checkpoint within multi-phase tasks |
| `scripts/pending_push.py` | CLI for task lifecycle (add/list/mark-done) |
| `references/enforcement-architecture-v2.md` | v2 four-layer enforcement: memory→enforce_delegate→rule_audit→cost-breaker, design principles |
| `references/knowledge-architecture-v3.md` | v3 knowledge integration: graph_search in decision circuit, lesson_graph_bridge, profile references |
| `scripts/cost-circuit-breaker.py` | Hourly cost watchdog: auto-pause high-cost crons if daily >$8.00 (≈¥57) |
| `scripts/enforce_delegate.py` | Pre-delegate mandatory check: lesson_inject + dead_list + user_rules |
| `scripts/rule_audit.py` | Daily SOUL.md rule compliance scanner (forbidden words, dead list mentions) |
| `scripts/auto_review.py` | Daily system audit v2: health + lessons + config consistency + cost + cron depth |
| `scripts/profile_observe.py` | 用户偏好写入入口 (观察→lessons/global.md) |
| `scripts/pipeline_runner.py` | Pipeline engine: tick/status/resume/define |
| `scripts/pipeline_stage_1_protocol.py` | Example: stage script for protocol extraction |
| `scripts/pipeline_stage_2_import.py` | Example: stage script for import path refactoring |
| `scripts/pipeline_stage_3_verify.py` | Example: stage script for isolation verification |
| `scripts/pipeline_runner.py` | Pipeline engine: tick/status/resume/define |
| `scripts/pipeline_stage_1_protocol.py` | Example: stage script for protocol extraction |
| `scripts/pipeline_stage_2_import.py` | Example: stage script for import path refactoring |
| `scripts/pipeline_stage_3_verify.py` | Example: stage script for isolation verification |

## Pitfalls

1. **纯文本行为约束不可靠 → 脚本强制** — SOUL.md 中独立段落描述的操作步骤会被主代理在执行时跳过。**唯一有效的修复**：把步骤嵌入调度速查表的每条路径前缀。已落地：`enforce_delegate.py`(delegate前检查)、`cost-circuit-breaker.py`(成本熔断)、`rule_audit.py`(每日违规扫描)。**SOUL.md精简 (2026-05-10)**：从287行→83行(-72%)。删除所有脚本已强制的文本规则、重复定义、冗余调用链。原则：SOUL.md=最小必要规则的单一真相源。详细规范下放到references/和profiles/。

**知识串联集成 (2026-05-10)**：三动作实现graphify↔lessons↔profiles互通——(1)graph_search嵌入启动协议+enforce_delegate (2)lesson_graph_bridge.py双向同步 (3)域profiles加知识引用头+去重。

**hindsight移除 (2026-05-10)**：容器运行41h但embed模块损坏，0功能消耗788MB。已停止容器+释放内存。当前知识层：memory(系统注入)+lessons(enforce_delegate)+graphify(65K节点)已足够。
2. **Background process output is invisible to users** — when `terminal(background=True)` generates interactive content (QR codes, prompts), extract the URL/text and present it directly. Never assume the user can see background process output. This caused 3-4 failed QQ Bot onboarding attempts.
3. **Don't bloat delegate context** — only inject L2+ lessons. L1 goes in daily digest, not per-task context.
4. **Lesson duplication** — deduplicate before writing. If the same lesson exists in both lessons/ and SOUL.md, remove from lessons/.
5. **Notification spam** — P2/P3 events MUST be batched into daily digest. Never push routine completions individually.
6. **Sub-agent lesson quality** — validate sub-agent lessons before writing. Sub-agents may hallucinate lessons.
7. **Main agent boundary** — the orchestrator never writes lesson files directly during normal operation. Lesson extraction happens in the response phase after task completion.
22. **惩罚cron=惩罚用户,不是惩罚agent (2026-05-10)** — rule_audit v2最初设计了"CRITICAL违规→自动暂停cron"机制。用户严厉指正：被暂停cron的后果是用户的量化信号/早报/复盘管线停摆，惩罚的是用户而不是违反规则的agent。这是方向性错误。正确做法：rule_audit仅扫描+通知，不做自动操作。agent的约束只能通过(1)memory系统级注入 (2)enforce_delegate前置检查 (3)基础设施层MCP wrapper。纠正次数: 1。**关键教训：任何面向agent的约束设计，必须先问"这个惩罚落在谁头上？"**

23. **诊断→修复→汇报,三者缺一不可 (2026-05-10)** — 用户说"给出结论也要给出解决方案，或者说给出结论你能解决的就直接解决掉。而不是给我结论就没下文了"。仅诊断不给解决方案是最常见的失败模式。触发信号：输出只说了"问题是X"但没有跟进动作。正确反应: 诊断→立即分级(L1/L2/L3)→L1/L2直接动手修→只汇报修了什么和结果。

17. **用户给的架构思路必须落地为操作路径，不能只存 memory** — 当用户给出具体的工程/架构设计思路时（如"daily自动继承未完成任务+计时"），必须立即评估可行性并落地为脚本/SOUL.md规则/MCP工具改动。只记到 memory 一定会忘。用户在纠正此问题时明确说"我昨天给提的思路你好像忘了或者根本就没当回事"。纠正次数: ≥2，已写入 global.md lessons。正确反应: 收到架构建议 → 判断是否可脚本化 → 立即创建/修改文件 → 通知用户已落地。

18. **"不要问我，自己解决"不是态度建议，是执行指令** — 当用户说"我不需要你来问我"或"这是你该解决的问题"时，这不是在讨论方法论，而是直接命令我停止请示、自己搞定。正确反应: 立即停止追问 → 独立出方案 → 直接动手 → 不汇报过程只汇报结果。反例: 继续解释"那我的方案是..."或"让我分析一下..."——这是再次请示。正例: 直接 building 然后汇报结果。纠正次数: ≥2，已写入 global.md。

19. **P4 checkpoint 和 P5 pipeline 的本质区别决定了选型，不是替代关系** — 
    - P4 checkpoint: 适用于1-2小时可闭环的密集任务。中断后恢复，但下次会话有冷启动成本（重读代码）。
    - P5 pipeline: 适用于跨3天以上、中间可能被20+条指令打断的任务。cron独立执行，会话一切换不受影响。
    - 选型测试: "如果用户发20条新指令后再回来，任务还能自动完成吗？" → 能→P5，不能→P4。
    - 初期设计错误: 只做了P4 checkpoint就以为解决了长跨度问题。用户指正后才意识到这是两个不同的维度。 — 当用户给出具体的工程/架构设计思路时（如"daily自动继承未完成任务+计时"），必须立即评估可行性并落地为脚本/SOUL.md规则/MCP工具改动。只记到 memory 一定会忘。用户在纠正此问题时明确说"我昨天给提的思路你好像忘了或者根本就没当回事"。纠正次数: ≥2，已写入 global.md lessons。正确反应: 收到架构建议 → 判断是否可脚本化 → 立即创建/修改文件 → 通知用户已落地。
9. **Cron scheduler hot-reload lag** — newly created cron jobs may not be picked up by the running scheduler until gateway restart. If a new cron's next_run_at passes without execution, manually run the script to confirm it works, then the scheduler will pick it up on next restart.
10. **Cron audit misjudges Weixin vs QQ Bot** — last_delivery_error showing Weixin send failed on a cron whose deliver is now qqbot is a STALE error from before migration. Do not flag as current issue unless the error timestamp is recent.
12. **Main agent passivity is architecture, not behavior** — "just be proactive" as a text rule does nothing. The fix requires: (a) startup protocol that auto-loads agenda, (b) decision matrix pre-classifying every action, (c) pipeline framework auto-advancing stages. Embed in instruction pipeline, not as standalone rules. Full design: `references/proactive-agenda-framework.md`.
13. **Agenda generation locale issues** — `free -h | grep Mem` fails on Chinese-locale systems where the label is "内存". Use `grep -E 'Mem|内存'` instead.
14. **Post-reboot cron gap** — Fixed-schedule cron jobs (e.g., `0 8 * * *`) do NOT backfill after a reboot. If `uptime` is short (<1h) and current time has passed scheduled windows, those jobs silently drop. The startup protocol's self-diagnosis must explicitly check: (a) system boot time from `uptime -s`, (b) compare against cron schedule table for current day, (c) trigger `cronjob action=run` for missed L1/L2 jobs. The ops-autopilot (08:05) can't catch these because it also misses its slot — the first user-facing session after reboot is responsible for detection & recovery. See `self-diagnosis` skill §7.5 for detailed procedure.
16. **Multi-phase plans without execution mechanism are not credible** — proposing a 5-phase plan spanning weeks is an anti-pattern if the only follow-through mechanism is "I'll remember to do it." Checkpoint (P4) is not enough — it saves state but the next session still has cold-start cost. The correct approach for tasks spanning 3+ days or surviving multiple context switches: design a cron pipeline (P5), write each stage as an independent script, submit to pipeline_runner.py, and let cron execute. The orchestrator's role shifts from "executor" to "designer of execution machinery." Test: if the user interrupts 20 times, does the task still complete? If only checkpoint, no. If pipeline, yes. See `references/pipeline-engine.md`.

20. **诊断≠修复：给出结论必须同时给出解决方案并直接执行** — 用户说"给出结论也要给出解决方案，或者说给出结论你能解决的就直接解决掉。而不是给我结论就没下文了"。这不是态度建议，是执行指令。诊断问题 → 立即分级(L1/L2/L3) → L1/L2直接动手修 → 只汇报修了什么和结果。永远不要只列问题清单就走人。触发信号：发现自己只说了"问题是X"但没有跟进动作 → 立即补上修复。纠正次数: ≥1 (2026-05-10)。

21. **SOUL.md纯文本约束不可靠 → 关键规则必须脚本化强制** — 用户明确指出"纯文本约束对你没用"。文本规则(SOUL.md段落/独立lesson)在真实执行中会被跳过。唯一有效的强制方式：把规则做成(1)脚本嵌入操作路径 (2)cron自动审计 (3)MCP工具硬约束。已落地：`enforce_delegate.py`(delegate前强制检查) + `rule_audit.py`(每日违规扫描) + `cost-circuit-breaker.py`(成本硬熔断) + `data_guard.py`(数据铁律门禁)。设计原则：能脚本化的不靠文本，能cron审计的不靠自觉，能MCP硬约束的不靠prompt。纠正次数: ≥1 (2026-05-10)。

| Component | Test | Result |
|:--|:--|:--|
| session-miner hard limits | Prompt rewritten: 15min timeout, 50 batch, 3s rate limit, no recursion | ✅ |
| cost-tracker silent zero | Patched: estimate from message_count×avg_tokens (was always $0.00) | ✅ |
| cost-circuit-breaker | New cron (b720fd552d39): hourly check, auto-pause if daily >$8.00 (≈¥57) | ✅ |
| finance stale lesson | prefetch_capflow lesson removed (code already deleted per V4死路) | ✅ |
| SOUL.md model contradiction | Aligned: "主代理默认 v4-pro" matches config.yaml reality | ✅ |
| task_tracker cleanup | 8 stale items → 5 valid (removed false alarms + already-resolved) | ✅ |

### Verification Results (2026-05-08)

Full end-to-end deployment of P+B+C+D+N architecture:

### P Layer (v2.2 + P4 v2.4)
| Component | Test | Result |
|:--|:--|:--|
| Startup protocol | using-superpowers SKILL.md patched | ✅ |
| Decision matrix | SOUL.md §3 + dispatch table L1/L2/L3 tags | ✅ |
| Pipeline framework | SOUL.md §3 stage table + auto-advance rule | ✅ |
| Task Checkpoint (P4) | task_tracker.json + pending_push.py + agenda_builder v2.1 inheritance | ✅ |
| Resume on startup | using-superpowers startup protocol → reads task_tracker.json, reports active tasks, asks to continue | ✅ |
| Agenda infra | ~/.hermes/agenda/{daily,pending,pipeline,state,task_tracker} | ✅ |
| agenda-builder | Script deployed (v2.1 with task inheritance + day counter + auto-promotion), cron e512e447fb29 (08:00) | ✅ |
| ops-autopilot | LLM cron bd5de39ac76e (08:05) with QQ Bot | ✅ |
| memory-curator | LLM cron 2698791c5f60 (03:00) | ✅ |
| memory first run | Manual run: 98%→67%, 26→23 entries | ✅ |
| pending_push.py | Session-end hook script + SOUL.md §4 | ✅ |

### B+C+D+N Layers (v2.0, verified 2026-05-07)

Full end-to-end test and deployment of B+C+D+N architecture:

| Layer | Test | Result |
|:--|:--|:--|
| B | `lesson_inject.py inject --domain writing-domain` → LESSON_BLOCK | ✅ |
| B | LESSON_BLOCK injected into delegate_task context | ✅ |
| B | Sub-agent confirmed receiving CRITICAL lessons in context | ✅ |
| B | [1.5] embedded as prefix in every dispatch path (not standalone rule) | ✅ |
| C | `lesson_inject.py add` → new lesson written with correction count | ✅ |
| C | Auto-increment on duplicate title (correction counting) | ✅ |
| C | ≥3 correction auto-promotion alert | ✅ |
| C | Main SOUL.md Rule 5: real-time extraction on user correction | ✅ |
| C | Gateway QQ Bot authorization → `GATEWAY_ALLOW_ALL_USERS=true` in .env | ✅ |
| N | daily-digest cron runs every 21:00 | ✅ |
| N | notify.py --digest + --retry both functional | ✅ |
| N | cron-failure-watchdog deployed: every 30min, no_agent, 12-pattern noise filter | ✅ |
| N | All 12 delivery crons migrated from Weixin iLink → QQ Bot | ✅ |
| N | Dead DSPy evolution cron (32ac475113d5) removed | ✅ |
| error-learner | Manual run: all 6 steps complete, circuit-guard ok. Scheduled daily 22:00 | ✅ |
| lesson-promoter | Manual run completed. Scheduled weekly Mon 03:00 | ✅ |
| D | Sub-agent `lessons:` response field | ✅ |

### 5-Way Parallel Audit Pattern (v2.5, 2026-05-10)

Comprehensive system audit methodology:
1. Temporarily upgrade all domain agents to deepseek-v4-pro for maximum audit capability
2. Dispatch all 5 domain audits (code/ec/finance/writing/ops) in parallel via delegate_task
3. Main agent simultaneously audits config consistency, cost efficiency, lesson staleness
4. Compile consolidated severity report (CRITICAL/HIGH/MEDIUM)
5. Restore original model assignments

See `references/5-way-audit-pattern.md` for full methodology and first-run results.

The writing-domain's phased pipeline inspired a reusable pattern now applied to finance-domain:

```
Phase 1 (pre-collect):  Data-heavy crons run first
  5896e6bcea04 (15:30 data+charts)    →  afff56398abe (16:00 k-line)
  18edaa02cd7e (16:15 margin data)

Phase 2 (compute-only): Scan uses pre-collected data, no re-fetch
  d075c207d860 (16:00 review gen)     →  b60f3c86dd1b (21:00 signal scan)

Pattern: pre-collect → compute → report
  Prevents redundant API calls and duplicate full-market scans
```

Also applied to finance cron fix (b60f3c86dd1b): eliminated duplicate full-market scans by merging mid_cap_strategy + daily_signal_report into single scan + JSON-to-text formatting.

### Known Gaps (v2.3 → v2.5, updated 2026-05-11)

1. **D-layer (sub-agent reverse learning)**: Sub-agents don't return `lessons:` field in `kanban_complete`. Worker SOUL.md now has startup protocol to LOAD lessons but no mechanism to RETURN discovered lessons. Fix: add lessons field to kanban_complete metadata, collected by error-learner cron.
2. **Cron scheduler hot-reload**: New cron jobs may not be picked up until gateway restart. Workaround: manual run to confirm script works, scheduler picks up on next restart.
3. **Domain maturity scoring inflated**: Script counts all profiles' shared scripts directory for each domain. Scores are relative rankings, not absolute.
4. **Self-review cron depth insufficient**: ✅ RESOLVED. auto_review.py upgraded to v2.
5. **Pre-kanban cost estimation**: No cost check before `kanban_create`. Unlike delegate_task which had enforce_delegate pre-check, kanban tasks skip cost guard. Gap: high-cost kanban workers (v4-pro) could be spawned without budget awareness.
6. **Code-domain superpowers enforcement**: ✅ RESOLVED 2026-05-11. Three-part hardening applied: mandatory product requirements + self-check checklist + model upgrade (glm-5.1→deepseek-v4-pro). See `references/superpowers-enforcement-pattern.md`.
7. **Kanban worker knowledge loading**: ✅ RESOLVED 2026-05-11. Startup Protocol injected into all 9 worker SOUL.md files (graph_search + lessons + SOUL.md re-read). See kanban-orchestrator §Startup Protocol Injection.

### Enforcement Architecture (v2, 2026-05-10)

Pure-text SOUL.md rules don't enforce. Four-layer design now active:

| Layer | Mechanism | How Enforced | Coverage |
|:--|:--|:--|:--|
| L0 | memory铁律短格式 | System auto-injects every turn | 100% |
| L1 | enforce_delegate.py v2 | SOUL.md唯一入口, auto-triggers graph_search for analysis tasks | ~95% |
| L2 | rule_audit.py --enforce | cron d0fe2b894e97 10:00, scans sessions, auto-pauses crons on CRITICAL | 100% post-hoc |
| L3 | cost-circuit-breaker.py | cron b720fd552d39 hourly, $8.00 threshold | 100% |

Full design: `references/enforcement-architecture-v2.md`

### Knowledge Architecture Integration (v3, 2026-05-10)

Three actions to interconnect graphify↔lessons↔profiles:
1. graph_search embedded in decision circuit (SOUL.md startup protocol + enforce_delegate v2)
2. lesson_graph_bridge.py — lesson→graphify bidirectional sync
3. Domain profiles with mandatory knowledge references (global.md + lessons + graphify)

Full design: `references/knowledge-architecture-v3.md`

Key scripts deployed this session:

| Script | Cron | Enforces |
|:--|:--|:--|
| enforce_delegate.py | pre-delegate hook | lesson_inject + dead_list + 5 iron rules |
| cost-circuit-breaker.py | b720fd552d39 (hourly) | Cost >$8.00 auto-pause high-cost crons |
| rule_audit.py | d0fe2b894e97 (10:00 daily) | Forbidden words + dead list scan |
| auto_review.py v2 | 48e31b9eff71 (09:00 daily) | Health + lessons + config + cost + cron |
| data_guard.py | 3dc57f9de476 (06:00 daily) | Data accuracy gate + function drift |
