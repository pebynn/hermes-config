# Multi-Board Strategy Progress Check Pattern

2026-05-13 (updated: target 150%, board pattern evo-*)

## Problem

When the orchestrator needs to check 3 strategy boards (evo-a, evo-b, evo-c) efficiently, running `hermes kanban --board <slug> list` 3 times is the simplest approach. Direct SQL is faster for complex aggregates.

## Pattern: CLI-first (simpler, preferred for cron)

```bash
for board in evo-a evo-b evo-c; do
  echo "=== $board ==="
  hermes kanban --board $board list
done
```

## Pattern: SQL (for detailed metrics extraction)

```python
import sqlite3, glob

# Find all evo board DBs
dbs = glob.glob('/home/pebynn/.hermes/kanban/boards/evo-*/kanban.db')

for db_path in sorted(dbs):
    board_name = db_path.split('/')[-2]  # evo-a, evo-b, evo-c
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Task status breakdown
    cur.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
    counts = dict(cur.fetchall())
    
    # Currently running task
    cur.execute("SELECT id, title FROM tasks WHERE status='running' LIMIT 1")
    running = cur.fetchone()
    
    # Latest done task with result
    cur.execute("""
        SELECT id, title, substr(result, 1, 200)
        FROM tasks WHERE status='done'
        ORDER BY completed_at DESC LIMIT 1
    """)
    latest = cur.fetchone()
    
    print(f"[{board_name}] done={counts.get('done',0)} running={counts.get('running',0)} "
          f"ready={counts.get('ready',0)} todo={counts.get('todo',0)} blocked={counts.get('blocked',0)}")
    if running: print(f"  ▶ running: {running[1][:60]}")
    if latest: print(f"  ✓ latest: {latest[1][:60]}")
    
    conn.close()
```

## Key decision after query

1. Extract metrics from reviewer comment or audit.json (年化, 胜率, LEVERAGE)
2. Compare against targets: **年化>150%**, **胜率>45%**, **LEVERAGE=1.0**
3. Route per termination decision table:
   - 达标+OOS verified → done, move to production
   - 达标+OOS unverified → create OOS verification task
   - 未达标 → create next evolution round (code→finance→reviewer)
   - Running → wait, no action
   - 结构性不可达 → escalate to research

## Pitfall: "Ready" tasks with completed work

A task showing `status=ready` (not `done`) may have already completed its work in a comment. Always check:
```bash
hermes kanban --board <board> show <task_id> | grep -A30 "Comments"
```
If comment contains results → manually `kanban complete` the task.

## Pitfall: "Running" dependent tasks that should be "todo"

After creating a chain (code→finance→reviewer), all 3 may show `running` due to dispatcher race. 
Recovery: `hermes kanban --board <board> reclaim <finance_id>` + `reclaim <reviewer_id>`.
