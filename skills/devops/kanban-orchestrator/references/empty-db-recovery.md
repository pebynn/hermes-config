# Empty Board DB Recovery Pattern (2026-05-13)

## Symptom

Gateway log shows:
```
ERROR gateway.run: kanban dispatcher: tick failed on board <slug>
sqlite3.OperationalError: no such table: tasks
```

`hermes kanban boards` shows board as `(empty)` but the board directory and kanban.db file exist on disk.

## Root Cause

The board's kanban.db is a valid SQLite file but was never schema-initialized (0 tables). This can happen when:
- Board directory auto-created by gateway on startup but schema initialization failed silently
- DB file corrupted/truncated to empty state
- Board created via CLI without proper init

## Diagnosis (≥2 paths, diagnostic iron law)

### Path 1: Direct SQLite check
```python
import sqlite3
conn = sqlite3.connect("/home/pebynn/.hermes/kanban/boards/<slug>/kanban.db")
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables: {tables}")  # [] = empty/corrupt
conn.close()
```

### Path 2: CLI + file size
```bash
# Board shows (empty)
hermes kanban --board <slug> list
# DB file exists but is tiny (4096B = empty SQLite header only)
ls -lh ~/.hermes/kanban/boards/<slug>/kanban.db
# Compare with healthy board
ls -lh ~/.hermes/kanban/boards/<healthy>/kanban.db  # ~100KB+
```

## Cascade Risk

When one board's DB is corrupt, the gateway dispatcher may also fail on OTHER boards on subsequent ticks — the failed SQLite connection can cause stale handles across the dispatcher's connection pool. **Don't assume only the board mentioned in the first error is affected.** Check all active boards.

## Recovery (2-step, L1 autonomous)

### Step 1: Copy DDL from healthy board + recreate
```python
import sqlite3, os

# Extract DDL from a healthy board
healthy = "/home/pebynn/.hermes/kanban/boards/<healthy-slug>/kanban.db"
src = sqlite3.connect(healthy)
cur = src.cursor()
cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL ORDER BY name")
ddls = [r[0] for r in cur.fetchall()]
src.close()

# Delete broken DB and recreate with DDL
broken = "/home/pebynn/.hermes/kanban/boards/<broken-slug>/kanban.db"
os.remove(broken)
conn = sqlite3.connect(broken)
for ddl in ddls:
    conn.execute(ddl)
conn.commit()
conn.close()
```

### Step 2: Restart gateway to force fresh DB connections
```bash
systemctl --user restart hermes-gateway.service
sleep 15
# Verify
grep "kanban dispatcher" ~/.hermes/logs/gateway.log | tail -3
hermes kanban boards
```

## Verification

After recovery:
1. Gateway log: no more `sqlite3.OperationalError` or `no such table` errors
2. `hermes kanban boards` shows board exists (even if empty of tasks)
3. DB has all 7 tables: tasks, task_runs, task_events, task_comments, task_links, kanban_notify_subs, sqlite_sequence

## Prevention

- After creating new kanban boards, verify schema immediately:
  ```python
  conn = sqlite3.connect("<board-db>")
  assert len(conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()) >= 6
  ```
- Monitor gateway log for `no such table` pattern — catch early before cascade
