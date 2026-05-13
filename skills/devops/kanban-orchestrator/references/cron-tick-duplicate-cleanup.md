# Cron Tick Duplicate Cleanup

## Problem

Evolution orchestrator crons run every N minutes. A previous tick may create Round N+1 tasks before the current tick runs. The current tick sees no Round N+1 tasks on its first `list`, creates them, then discovers duplicates. Result: 2+ parallel code→finance→reviewer chains on the same board fighting over the same codebase.

## Detection

Before `kanban_create` for any new round, scan the board:

```bash
hermes kanban --board <board> list | grep "R<N>-<S>"
```

If any matching tasks exist (regardless of `running`/`todo`/`done` status), skip creation.

## Cleanup (when duplicates already exist)

Keep the chain you just created (it has correct dependency links via `hermes kanban link`). Cancel the older duplicate chain:

```python
import sqlite3

board_db = "/home/pebynn/.hermes/kanban/boards/<board>/kanban.db"
conn = sqlite3.connect(board_db)

# Cancel duplicate tasks
conn.execute("UPDATE tasks SET status='cancelled' WHERE id='<dup_code_id>'")
conn.execute("UPDATE tasks SET status='cancelled' WHERE id='<dup_finance_id>'")

# Remove duplicate dependency edges
conn.execute("DELETE FROM task_links WHERE parent_id='<dup_code_id>' AND child_id='<dup_finance_id>'")

conn.commit()
conn.close()
```

**Important**: Use `task_links` table for dependency edges, NOT `dependencies`. The kanban SQLite schema uses `task_links(parent_id, child_id)`.

## Prevention

1. Always scan the board before creating any new round
2. Match by task title prefix (e.g., "R3-A")
3. If a previous cron tick's tasks are still `running`, the orchestrator should exit silently (next tick handles evaluation)
4. If previous tasks are `done`/`cancelled`, evaluate their output before deciding next action

## Real Case (2026-05-13)

evo-a board: orchestrator created R3-A chain (t_b1fb7435→t_40034075→t_5cb346e5). Second `list` revealed pre-existing duplicate R3-A chain (t_45a0b56a→t_bea004c8) from previous cron tick. Both t_45a0b56a (running, code) and t_b1fb7435 (running, code) doing the same work. Cleaned by cancelling the older chain via SQL.
