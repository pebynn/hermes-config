# Cross-Session Result Delivery Pattern

Date: 2026-05-11

## Problem

Orchestrator spawns multi-task kanban batches. Tasks complete at different times, possibly after the current session ends. User needs results delivered without having to ask repeatedly.

## User Preference (2026-05-11)

- **Session active**: Deliver results directly in the conversation
- **Session ended**: Deliver via QQ Bot (qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12)
- **Format**: Concise summary, no verbose explanations

## Pattern: Dual-Layer Delivery

### Layer 1: Individual Task Notifications

Subscribe QQ Bot to each kanban task so the user gets pinged on completion:

```bash
for tid in t_xxx t_yyy t_zzz; do
  hermes kanban notify-subscribe --platform qqbot --chat-id A88D89DDAFEE6A7ED7EB35325B1AEA12 "$tid"
done
```

This delivers: "Task t_xxx: <summary>" on completion — one message per task.

### Layer 2: Summary/Aggregation Cron

Create a cron job that polls all tasks, aggregates results, and self-cleans after delivery:

```bash
hermes cron create \
  --name "Kanban升级方案汇总+QQ推送" \
  --schedule "every 30m" \
  --repeat "20 times" \
  --deliver "qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12" \
  --tools "terminal,file" \
  --prompt "..."
```

The cron's prompt should:

1. **Check status**: `hermes kanban show <tid>` for each task
2. **Decision tree**:
   - All done → aggregate and push summary
   - Any blocked/failed → report issues briefly
   - Still running → exit silently
3. **Aggregate**: Collect each task's summary into a concise report
4. **Self-clean**: `cronjob(action='remove', job_id='<self>')` after successful delivery

### Summary Format

```
Kanban全域升级汇总
━━━━━━━━━━━━━━━
✅ Domain1: <1-line summary>
✅ Domain2: <1-line summary>
━━━━━━━━━━━━━━━
📁 Output files: <paths>
```

## Why Separate Layers

- Layer 1 (notify-subscribe) works even if the orchestrator session is dead
- Layer 2 (summary cron) provides the full picture, not individual pings
- Self-cleaning cron avoids accumulating one-shot monitor jobs
- 20-retry limit prevents infinite polling if a task is permanently stuck

## Pitfalls

- **Don't subscribe the orchestrator itself** to task notifications — it wastes tokens
- **Don't make the summary cron permanent** — use `--repeat N` with self-clean
- **The summary cron should use only terminal/file tools** — minimal cost per tick
- **Check for the `hermes kanban notify-subscribe` command availability** — it requires the platform to be configured in gateway
