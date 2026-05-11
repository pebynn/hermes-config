# Enforcement Architecture v2 — 2026-05-10

## Design Evolution

v1: SOUL.md text rules only → 0% enforcement
v2: 4-layer system → ~95% enforcement

## Four-Layer Design

| Layer | Mechanism | How Enforced | Coverage |
|:--|:--|:--|:--|
| L0 | memory铁律短格式 | System auto-injects every turn | 100% |
| L1 | enforce_delegate.py v2 | SOUL.md唯一入口, auto graph_search for analysis | ~95% |
| L2 | rule_audit.py | cron d0fe2b894e97 10:00, scans sessions, notification only | 100% post-hoc |
| L3 | cost-circuit-breaker.py | cron b720fd552d39 hourly, $3.00 (≈¥21) threshold | 100% |

## Critical Lesson: Don't Punish User for Agent Violations

rule_audit v2 initially designed "CRITICAL violation → auto-pause cron jobs".
User correction: pausing cron punishes the USER (breaks their production pipelines),
not the agent. Directionally wrong.

Correct approach: rule_audit scans + notifies only. Agent enforcement relies on:
- memory system-level injection (L0)
- enforce_delegate pre-action checks (L1)
- infrastructure-level MCP wrapper (future, requires Hermes internal changes)

**Design principle: before adding any enforcement, ask "who bears the consequence?"**

## enforce_delegate.py v2

Single mandatory entry point for ALL domain agent delegation.
Auto-enforces: lesson_inject → dead_list → graph_search (analysis tasks) → context assembly.

Analysis keywords trigger automatic graph_search: 分析/评估/判断/预测/找原因

## rule_audit.py v2

Daily scan of session files for:
- Forbidden words (可以吗/怎么样/需要我)
- Self-calculated data patterns
- Dead list mentions

Notification only. No auto-action.

## Cost Circuit Breaker

Hourly no_agent cron. Threshold: $3.00/day (≈¥21).
Auto-pauses: session-miner (8b9037f1fbdf), 周度自优化 (15d19bd7a80f).

## Remaining Gap

~5% gap: agent can skip enforce_delegate.py and delegate directly.
Fix requires modifying Hermes internal delegate_task function to force wrapper.
This is infrastructure-level work, not agent-level.
