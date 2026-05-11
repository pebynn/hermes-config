# Constraint Enforcement Pattern (2026-05-10)

## Problem

SOUL.md text-based rules (纯文本约束) are systematically skipped by the main agent during real execution. Standalone paragraphs describing mandatory steps ("执行 [1.5] lesson_inject") have zero enforcement power. The agent reads them but doesn't execute them.

## Root Cause

Text rules in SOUL.md are documentation, not enforcement. The agent's attention is on the task, not on compliance checking. When a rule is described in a standalone paragraph, it's treated as background information, not an action item.

## Solution: Three-Tier Enforcement

| Tier | Mechanism | Example | Strength |
|:--|:--|:--|:--|
| Script-in-path | Embed executable script call in the operation path itself | `python3 enforce_delegate.py --domain {x}` on every delegate row | Strong — can't skip without skipping the whole operation |
| Cron audit | Daily cron scans for violations after the fact | `rule_audit.py` scans agent.log for forbidden words | Medium — catches violations but after they happen |
| MCP hard constraint | MCP tool that blocks non-compliant operations | `data_guard.py` BLOCK level stops pipeline | Strongest — can't proceed without passing |

## Implemented Enforcements

### 1. enforce_delegate.py (Script-in-path)
- Runs before every delegate_task
- Loads domain lessons + global lessons
- Checks dead_list for forbidden approaches
- Injects 5 user iron rules as context prefix
- BLOCK if goal matches dead list keywords
- Exit 0 = PASS, Exit 1 = BLOCKED

### 2. rule_audit.py (Cron audit)
- Daily 10:00 cron (d0fe2b894e97)
- Scans agent.log for: forbidden words (可以吗/怎么样/需要我), dead list mentions
- No LLM tokens consumed (no_agent=true)
- Reports violations for user review

### 3. cost-circuit-breaker.py (Cron hard constraint)
- Hourly cron (b720fd552d39)
- Auto-pauses session-miner + 周度自优化 if daily cost >$3.00
- No manual intervention needed

### 4. data_guard.py (MCP-level hard constraint)
- BLOCK level stops pipeline entirely
- WARN level records but allows continuation
- 5 pipeline entry points enforce data accuracy

## Design Principle

> 能脚本化的不靠文本，能cron审计的不靠自觉，能MCP硬约束的不靠prompt。

Translation: Script when possible, cron-audit when scriptable, MCP-harden when critical. Never rely on text rules alone.
