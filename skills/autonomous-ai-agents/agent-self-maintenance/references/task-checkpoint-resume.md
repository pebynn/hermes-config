# Task Checkpoint & Resume — P4 Layer (Implemented 2026-05-08)

## Problem

The orchestrator cannot reliably execute long-span tasks across sessions because:
1. Session context replaced on new user message — intermediate state lost
2. No mechanism to persist "what's pending, how long has it been"
3. Next session starts from scratch — no auto-resume

## Solution: task_tracker.json + pending_push.py + checkpoint_save.py + agenda_builder inheritance

Instead of per-task directories (original design, abandoned), a single-file approach:

### Core files

```
~/.hermes/agenda/task_tracker.json           — Task database (JSON array)
~/.hermes/scripts/pending_push.py            — CLI: add/list/mark-done
~/.hermes/scripts/checkpoint_save.py         — CLI: save per-stage progress within a task
~/.hermes/scripts/agenda_builder.py           — v2.1: daily agenda with inheritance + day counting
~/.hermes/SOUL.md                             — Startup protocol: checks tracker on session start
```

### task_tracker.json

```json
{
  "tasks": [
    {
      "id": "task-20260508-0",
      "desc": "signal_engine ↔ chan_buy_signal 接口解耦",
      "added": "2026-05-08",
      "last_seen": "2026-05-08",
      "days_pending": 0,
      "priority": "P1",
      "tags": ["quant", "refactoring"],
      "source": "manual",
      "checkpoints": [
        {"stage": 1, "total_stages": 3, "description": "...", "produced": [...], "timestamp": "..."}
      ],
      "progress": "阶段 1/3"
    }
  ],
  "last_updated": "2026-05-08"
}
```

### pending_push.py — Task lifecycle CLI

```bash
python3 pending_push.py "task desc" P1 "tag1,tag2"    # Add new task
python3 pending_push.py --done "desc fragment"          # Mark done (removes from tracker)
python3 pending_push.py --list                          # List active tasks
```

### checkpoint_save.py — Per-stage progress within a task

For multi-phase tasks (e.g., 3 stages of refactoring), save intermediate progress:

```bash
python3 checkpoint_save.py "task-20260508-0" 1 3 \
    "已提取 Protocol 契约" \
    '["~/quant/contracts/chan_buy_contract.py"]'

python3 checkpoint_save.py --show "task-20260508-0"
# Output:
#   任务: signal_engine ↔ chan_buy_signal 接口解耦
#   进度: 阶段 1/3
#   Checkpoints:
#     [2026-05-08 23:37] 阶段1/3: 已提取 Protocol 契约
#       └─ ~/quant/contracts/chan_buy_contract.py
```

### agenda_builder.py v2.1 — Auto-inheritance logic (runs daily 08:00 cron)

1. `sync_pending_to_tracker()` — imports new tasks from legacy pending.md
2. `inherit_tasks()` — for each task, if `last_seen != today` → days_pending += 1
3. `get_tasks_for_daily()` — formats task list with day markers:
   - 0 days: `新`
   - 1-2 days: `🕐 第N天`
   - 3-4 days: `⚠️ 已滞留N天` + auto-promote to P1
   - 5-6 days: `🔥 已滞留N天`
   - 7+ days: `🚨 已滞留N天`

### SOUL.md startup protocol (session start)

```
2. 读 ~/.hermes/agenda/task_tracker.json → 检查活跃任务（含滞留天数）
6. 有活跃任务 → 汇报后主动问"是否继续未完成任务？"
```

## What This Replaces

Original design (never implemented) used `~/.hermes/tasks/<id>/manifest.json + checkpoint.json`. Replaced by single-file task_tracker.json because:
- Multi-file per task is overkill for the orchestrator's use case
- A single JSON array is simpler to read/write/backup
- Day counters and auto-promotion are the key feature, not per-step checkpoints
- Per-step checkpoints belong in `checkpoint_save.py`, not in per-task directories

## When to Use

Open a task in tracker when:
- Task expected to survive a session boundary
- Task has verifiable phases (file exists, test passes)
- Task might be interrupted by higher-priority work

Don't bother for:
- Single-session tasks (just do it)
- Research/creative work (can't checkpoint mid-thought)
- Emergency fixes (solve it, close it, move on)

## Session Resume Flow

```
Session start
  → SOUL.md §2: read task_tracker.json
  → Report: "你有1个活跃任务: signal_engine解耦, 第1天, 要继续吗?"
  → User: "继续"
  → Read session_search for last relevant session
  → Continue from where it was left
  → On completion: pending_push.py --done "signal_engine"
  → Next daily.md will show "(无待办)"
```

## Multi-Phase Task Workflow (proven pattern)

Based on the signal_engine decoupling (2026-05-08, 3 stages):

```
Stage 1: Extract Protocol contract
  → checkpoint_save.py task 1 3 "extracted protocol" '["path"]'
  → Verify: syntax pass + import pass

Stage 2: Modify consumer to use contract
  → checkpoint_save.py task 2 3 "import path changed"
  → Verify: consumer.py loads without error

Stage 3: Verify isolation + write test
  → checkpoint_save.py task 3 3 "done"
  → Verify: test script passes 3/3
  → pending_push.py --done "desc"
```

Key rule: each stage must have a VERIFIABLE PRODUCTION (file written, test passes, data unchanged). Don't checkpoint on "I decided to do X" — checkpoint on "I wrote file X and verified it works."

## Pitfalls

1. **Don't over-populate** — only track genuinely multi-session tasks. 1-3 active tasks max.
2. **Completion discipline** — always `--done` when finished. Stale tasks clutter the list.
3. **auto-promotion is a signal, not a binding** — P1 auto-promotion at 3 days means "flag for review", not "must do now".
4. **Checkpoint vs session_search** — task_tracker records WHAT is pending; session_search records HOW to resume it. Both needed.
5. **checkpoint_save.py only for multi-phase tasks** — single-phase tasks just use pending_push.py add/done.
6. **Stage boundaries must be verifiable** — don't checkpoint "started working on it". Checkpoint when a file exists, a test passes, or a command succeeds.
