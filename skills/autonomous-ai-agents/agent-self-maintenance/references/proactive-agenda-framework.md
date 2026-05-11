# Proactive Agent Framework — Design Doc (P Layer)

## Problem

Main agent was designed as a reactive assistant: waits for user input, then acts.
This is an **architecture problem**, not a behavior problem. Text rules like
"be proactive" don't work — they get skipped in the instruction pipeline.

## Root Cause Analysis

| Symptom | Architecture Root Cause |
|:--|:--|
| New session starts blank, doesn't know what to do | No startup protocol; sessions have no persistent agenda |
| Asks "what next?" after every step of a complex task | No pipeline framework; tasks not decomposed into self-advancing stages |
| Asks "should I fix this?" for obvious bugs | No decision authority matrix; every action treated as equal |
| Same errors recur across sessions | No cross-session pending queue; forgotten between sessions |
| User must micromanage every step | No L1/L2/L3 classification; all decisions escalate to user |

## Solution: P+B+C+D+N Architecture

Four sub-layers in the Proactivity layer, all deployable within existing Hermes architecture
(no source code changes needed):

### P1 — Startup Protocol

**For**: session initialization
**Where**: `~/.hermes/SOUL.md` §启动协议 + `using-superpowers` SKILL.md
**What**: Every new session auto-executes before user speaks:
1. Read `~/.hermes/agenda/daily.md` — today's agenda
2. Run self-diagnosis quick scan (cron + disk + services, <5 sec)
3. Report: system status + pending tasks (sorted L1→L2→L3)
4. Start L1 items immediately, L2 items with brief report, L3 items report and wait
5. No filler questions like "what should I do next"

### P2 — Decision Authority Matrix

**For**: every action the agent takes
**Where**: `~/.hermes/SOUL.md` §决策权限矩阵
**What**: Pre-classify every possible action:

| Level | Scope | Action | Examples |
|:--|:--|:--|:--|
| L1 自主 | Routine, reversible, low cost | **Do it, don't tell** | Bug fixes, data anomalies, config drift, pipeline repair, health checks |
| L2 半自主 | Impactful but rollback-able | **Do it, then brief** | New monitoring, cron adjustments, system config optimization, script refactoring |
| L3 请示 | Irreversible, financial, external | **Pause, ask user** | API key changes, architecture overhauls, external publishing, funds operations |

**Only L3 reaches the user.** L1/L2 proceed without asking.

### P3 — Pipeline Advancement Framework

**For**: complex multi-stage tasks
**Where**: `~/.hermes/SOUL.md` §3 (流水线推进框架)
**What**: Tasks with ≥3 stages get explicit stage structure in delegate context:

```
## 流水线阶段
| Stage | Content | Verification | Decision Level |
|:--|:--|:--|:--|
| 1 | Data collection | Output file exists + syntax passes | L1 |
| 2 | Processing | Data non-empty + checks pass | L1 |
| 3 | Architecture decision | User must approve | L3→Pause |
```

**Default behavior**: Auto-advance. Stage N complete → verify → immediately start N+1.
Only pause at L3-marked stages, waiting for user confirmation.
Never ask "stage X is done, continue?"

### P4 — Task Persistence & Agenda Infrastructure

**For**: cross-session task awareness + day counting + auto-promotion
**Where**: `~/.hermes/agenda/` directory + cron `e512e447fb29` (daily 08:00)
**What**:

| File | Purpose | Update Mechanism |
|:--|:--|:--|
| `daily.md` | Today's agenda (services, crons, data freshness, resources, errors, pending) | `agenda_builder.py` v2.1, cron 08:00, zero token cost |
| `task_tracker.json` | Task database: description, priority, tags, day counter, last_seen | `pending_push.py` add/list/done; `agenda_builder.py` auto-increments days_pending |
| `pending.md` | Legacy queue (deprecated, tasks migrated to task_tracker.json) | `agenda_builder.py v2.1 sync_pending_to_tracker()` |
| `state.json` | Yesterday's state for trend comparison | `agenda_builder.py` writes after each run |

**Task inheritance + day counter** (agenda_builder.py v2.1):
- Each cron run: for every task, if last_seen != today → days_pending += 1
- Day markers: `新` (0d) → `🕐 第N天` (1-2d) → `⚠️ 已滞留N天` (3-4d, auto P1) → `🔥` (5-6d) → `🚨` (7d+)
- Thresholds: `PROMOTE_AFTER_DAYS = {3: '⚡', 5: '🔥', 7: '🚨'}`

### P5 — Session-End Hook + Resume

**For**: preventing task loss across sessions + auto-resume on next session
**Where**: `~/.hermes/scripts/pending_push.py` + SOUL.md §2 + using-superpowers SKILL.md
**What**: When session has unfinished tasks, agent calls:
```
python3 ~/.hermes/scripts/pending_push.py "task description" P1 "tag1,tag2"
```
On next session: SOUL.md startup protocol reads task_tracker.json → reports "你有N个活跃任务，X已第N天" → asks "是否继续？". Resumes via session_search for context.

## Implementation Checklist (2026-05-08)

| # | Component | Path | Status |
|:--|:--|:--|:--|
| P1 | Startup protocol in SOUL.md | `~/.hermes/SOUL.md` §启动协议 | ✅ |
| P1 | Startup protocol in skill | `using-superpowers` SKILL.md | ✅ |
| P2 | Decision matrix | `~/.hermes/SOUL.md` §决策权限矩阵 | ✅ |
| P2 | L1/L2/L3 labels in dispatch table | `~/.hermes/SOUL.md` 调度模式表 | ✅ |
| P3 | Pipeline framework | `~/.hermes/SOUL.md` §3 | ✅ |
| P4a | Agenda directory | `~/.hermes/agenda/` | ✅ |
| P4b | Agenda builder v2.0 | `~/.hermes/scripts/agenda_builder.py` (350 lines) | ✅ |
| P4c | Agenda cron | `e512e447fb29` (daily 08:00, no_agent) | ✅ |
| P5 | pending_push.py | `~/.hermes/scripts/pending_push.py` | ✅ |
| P5 | Session-end hook rule | `~/.hermes/SOUL.md` §4 | ✅ |

## Agenda Builder v2.0 Capabilities

The upgraded `agenda_builder.py` generates actionable daily.md with:

| Section | Detection | Noise Filtering | Actionable Output |
|:--|:--|:--|:--|
| Service Health | Gateway, MySQL, DeepSeek API, Camofox | — | Icon + fix command |
| Cron | Parse `hermes cron list` for last_status=error | Skip Weixin/iLink stale errors | Detail + job name |
| Data Freshness | MySQL K-line count, review draft files | Handle pre-market hours gracefully | Fix suggestion |
| Resources | Disk, memory, sessions, trends | Check auto_prune status | Fix command if needed |
| Errors | cat errors.log last 500 lines | 13 noise patterns filtered | Category + count + detail |
| Pending Tasks | Read pending.md | — | Sorted L1→L2→L3 |

## Key Design Principles

1. **Every output line is actionable.** "Disk 10%" → useless. "Disk 10% (normal)" or "Disk growing +2%/week, will fill in 5 weeks" → actionable.
2. **No noise.** Filter before presenting. 13 known noise patterns auto-suppressed.
3. **Trend-aware.** Compare today vs yesterday. Detect deterioration before it becomes critical.
4. **Decision-ready.** Pre-classify every item as L1/L2/L3. Agent knows what to do without asking.
5. **Zero token cost for generation.** Pure script, no LLM. Cron is `no_agent=true`.

## Pitfalls Discovered During Implementation

1. **`free -h | grep Mem` fails on zh_CN locale** — label is "内存", not "Mem". Fix: `grep -E 'Mem|内存'`.
2. **`hermes cron list --json` doesn't exist** — must parse text output.
3. **`mysqladmin ping` needs credentials** — use `pgrep mysqld` for process check, credentials for data queries.
4. **Session auto_prune may not trigger** — check for files older than retention_days, not just the config flag.
5. **SSE parse errors are noise** — add to filter list alongside asyncio task cleanup patterns.
