# Pipeline Notification Chain

When a pipeline runner tick encounters a meaningful event (L3 pause, completion, failure), it needs to reach the user. The chain:

```
pipeline_runner.py tick()
  → notify_user(message) called
  → writes to task_tracker.json (agenda picks up at next generation)
  → writes .pipeline_notify file (dedup: same msg not re-sent)
  → prints to stdout
  → cron system captures stdout
  → cron deliver target (qqbot:...) sends to user's QQ

Quiet mode: only prints when something changes.
  No-output ticks → no QQ Bot message → no noise.
```

## Dedup Mechanism

`.pipeline_notify` stores the last sent message hash. `notify_user()` compares against it before printing. Same message within same tick → suppressed.

## Cron Target

`pipeline-runner` cron (fc7f76d16dd3) has `deliver: qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12` and `no_agent: true`. This means:
- stdout from the script → captured by cron system
- delivered to QQ Bot as a text message
- no LLM tokens consumed per tick

## When Notifications Fire

| Event | Output | Channel |
|:--|:--|:--|
| L3 pipeline pause | `[pipeline] Pipeline 'X' 到 stage N，等待决策` | QQ Bot + agenda |
| Pipeline complete | `[pipeline] Pipeline 完成: X` | QQ Bot + agenda |
| Pipeline failed (2 retries) | `[pipeline] Pipeline 失败: X — error` | QQ Bot + agenda |
| WAIT expiry | No direct notification (WAIT is silent) | Next stage handles output |
| Normal tick (no change) | No output | None (quiet mode) |

## Redundancy

Two layers: QQ Bot (immediate push) + task_tracker (agenda morning pickup). If QQ Bot is down, agenda still shows the paused task at next generation (00:00).
