# Lessons Blocked Audit (2026-05-07)

Deep audit of the autonomous evolution gap: lessons learned by the main agent that
never reach sub-agents during delegation.

## Finding: 7/10 Critical Lessons Blocked

| # | Lesson | Domain | Severity | Corrected | Location | Reaches Sub? |
|:-:|:--|:--|:--|:-:|:--|:--|
| 1 | 数据铁律：禁止自行计算涨跌幅 | writing | CRITICAL | 3x | 主agent memory | ❌ |
| 2 | Sina API parts映射铁律 | writing | CRITICAL | 2x | 主agent memory | ❌ |
| 3 | PDD API对个人不可行 | ec | CRITICAL | 3x | 主agent memory+user profile | ❌ |
| 4 | SKU降级方案 | ec | HIGH | 1x | 主agent memory | ❌ |
| 5 | 资金流look-ahead bug | finance | HIGH | 1x | 主agent memory | ❌ |
| 6 | K线astype(str)统一 | finance | MEDIUM | 1x | 主agent memory | ❌ |
| 7 | 渲染验证铁律 | writing | HIGH | 2x | 主agent memory | ❌ |

Only 3/10 lessons reached sub-agents:
- 东方财富API晚间维护 → writing-domain SOUL.md ✅
- avoid-ai-writing后处理 → writing-domain SOUL.md ✅
- DeepSeek→智谱fallback → config.yaml+circuit ✅

## Root Cause

The main agent's `delegate_task()` context parameter is manually written each time.
Lessons in memory are not automatically injected. Sub-agents start each session
with a blank context, knowing nothing about past mistakes.

## Fix: B+C+D+N Architecture

- **B**: Automatic lesson injection into every delegate context via step [1.5]
- **C**: Real-time lesson extraction on user correction
- **D**: Domain-aware lesson storage + sub-agent reverse learning
- **N**: Notification layer for error alerts and daily digests

## Impact

After B+C+D+N deployment:
- 7 blocked lessons migrated to `~/.hermes/lessons/{domain}.md`
- Every future delegation to writing-domain will include "🔴 数据铁律" warning
- Corrected≥3x lessons auto-promote to domain SOUL.md as hard constraints
