# B+C+D+N Architecture — Full Specification

Version: 2.0.0 | Date: 2026-05-07

## Problem

The main Hermes agent (orchestrator) learns from user corrections but sub-agents
(which do 90% of actual work) start each session blank. 7/10 critical lessons
never reach the execution layer. Result: user repeatedly corrects the same mistakes.

## Solution: Four-Layer Feedback System

### Layer B: Lesson Injection (前置注入)

Automatic, mandatory step in the instruction pipeline:

```
User instruction
 → [1] MCP optimize → domain, priority
 → [1.5] lesson_inject(domain) → ~/.hermes/lessons/{domain}.md + global.md
 → [2] context-assemble
 → [3] delegate_task(goal, context=enriched + LESSON_BLOCK)
```

Lesson block appears at TOP of sub-agent context:
```
╔══════════════════════════════════╗
║  ⚠️ 已知陷阱 - 本次任务必读     ║
║  [🔴CRITICAL] 数据铁律: ...     ║
║  [🟠HIGH] API黑窗: ...          ║
╚══════════════════════════════════╝
```

### Layer C: Real-time Learning (实时学习)

User correction → immediate lesson extraction → write to domain file.
Auto-promotion: same lesson corrected ≥3 times → promoted to domain SOUL.md.

Three tiers:
- L1 🟡: Corrected 1x → lessons/{domain}.md (context bottom)
- L2 🟠: Corrected 2x → lessons/{domain}.md with ⚠️ (context middle)
- L3 🔴: Corrected ≥3x → profiles/{domain}/SOUL.md (hard constraint)

### Layer D: Domain-Aware + Sub-Agent Learning (域感知)

Lesson store by domain:
```
~/.hermes/lessons/
├── {code,ec,finance,writing,ops,research}-domain.md
└── global.md
```

Sub-agents return discovered lessons:
```
status: done
lessons: ["17网反爬升级，搜索结果需等5秒"]
```

Main agent auto-appends to domain lesson file.

### Layer N: Notification (通知)

Priority routing:
- P0 (circuit break, outage) → PushPlus immediate
- P1 (cron failure) → PushPlus immediate
- P2 (lesson promotion) → daily digest (21:00)
- P3 (task complete) → daily digest only

## Infrastructure

| Component | Path | Purpose |
|:--|:--|:--|
| Lesson store | `~/.hermes/lessons/` | 7 domain files + global |
| Injector | `~/.hermes/scripts/lesson_inject.py` | CLI for inject/add/list |
| Notifier | `~/.hermes/scripts/notify.py` | Multi-channel dispatch |
| error-learner | cron 575103045eb1 | Daily 22:00: scan failures → extract lessons |
| lesson-promoter | cron 60c82974423f | Mon 03:00: promote ≥3x lessons |
| daily-digest | cron d097864fb3ad | Daily 21:00: send digest |

## Effectiveness Measurement

Track per lesson:
- `corrections_since_injection`: Did same error recur after injection?
- If yes → upgrade severity or rewrite lesson
- If no → lesson working, keep current tier
