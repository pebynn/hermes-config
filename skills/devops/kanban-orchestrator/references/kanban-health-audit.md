# Kanban Health Audit — Comprehensive Checklist (2026-05-13)

Full audit procedure for diagnosing kanban system health. Run when user asks "审查kanban" or when blocked tasks accumulate.

## 1. Infrastructure Check

```bash
# Gateway + dispatcher
ps aux | grep -E 'kanban|gateway|hermes' | grep -v grep

# Dashboard (separate process!)
ss -tlnp | grep 9119

# RAM (exit_code=9 often means resource pressure)
free -h
```

## 2. Board Inventory

```bash
# Active boards
hermes kanban boards list

# All kanban.db files (including archived boards)
find ~/.hermes -name "kanban.db" -exec ls -lh {} \;

# 0-byte files = stale artifacts → delete
find ~/.hermes -name "kanban.db" -size 0 -delete
```

## 3. Task Status Deep Dive

Use execute_code with sqlite3 on the main kanban.db:

```python
# Status summary
SELECT status, COUNT(*) FROM tasks GROUP BY status;

# Blocked tasks with full details
SELECT * FROM tasks WHERE status='blocked';

# Event history for each blocked task
SELECT * FROM task_events WHERE task_id=? ORDER BY created_at DESC LIMIT 5;

# Active tasks
SELECT * FROM tasks WHERE status IN ('ready','running','todo');

# Done tasks with NULL results
SELECT id, title FROM tasks WHERE status='done' AND result IS NULL;

# Stale claim locks
SELECT id, status, claim_lock, claim_expires FROM tasks WHERE claim_lock IS NOT NULL;
```

## 4. B/D Layer Compliance

```bash
python3 ~/.hermes/scripts/audit_bd_layer.py
```

Check body injection on blocked/done tasks:
```python
SELECT id, title, 
  CASE WHEN body LIKE '%[LESSONS]%' OR body LIKE '%成本预估%' THEN 1 ELSE 0 END as b_injected,
  CASE WHEN result IS NOT NULL AND result != '' THEN 1 ELSE 0 END as d_recovered
FROM tasks WHERE status IN ('blocked','done');
```

## 5. Worker Profile Health

```bash
# Skill count per profile (should be 1 = kanban-worker only)
for f in ~/.hermes/profiles/*/skills/; do
  count=$(ls "$f" 2>/dev/null | wc -l)
  echo "$f → $count"
done

# Auto-bundle contamination check
ls ~/.hermes/profiles/code-domain/skills/
```

## 6. Cron Health

```bash
cronjob(action='list')
# Check for delivery errors (QQ Bot failures)
# Check for last_status='error' on critical crons
```

## 7. Common Fix Procedures

### Blocked tasks → archive (obsolete work)
```bash
hermes kanban unblock <tid>
# Then via SQL:
UPDATE tasks SET status='archived' WHERE id='<tid>';
```

### Stale claim locks cleanup
```sql
UPDATE tasks SET claim_lock=NULL, claim_expires=NULL 
WHERE status='archived' AND claim_lock IS NOT NULL;
```

### Dashboard restart
```bash
hermes dashboard --port 9119 &   # use terminal(background=true)
ss -tlnp | grep 9119             # verify
```

## 8. Archived Board Cleanup

Archived boards pile up in `~/.hermes/kanban/boards/_archived/` — each has its own `kanban.db` with stale task data. When a summary cron references task IDs on an archived board, it silently fails (404) every tick.

### Audit: find archived boards
```bash
ls ~/.hermes/kanban/boards/_archived/
# Pattern: <slug>-<unix_ts>/  — e.g., strat-a-1778606779/
```

### Audit: check cron references against archived boards
```python
# After cronjob(action='list'), for each cron that references task IDs:
# 1. Extract task IDs from cron prompt_text
# 2. Check if those IDs exist in main kanban.db OR any archived board DB
# 3. If all IDs are on archived boards → cron is dead, needs cleanup
```

### Safe cleanup procedure
```bash
# 1. Archive the stale cron (not delete — preserves config)
#    Via cronjob action='remove' or hermes cron remove <id>
hermes cron remove db99483f4cfa

# 2. Optionally purge archived boards older than N days
find ~/.hermes/kanban/boards/_archived/ -maxdepth 1 -mtime +7 -exec rm -rf {} \;

# 3. Compact main kanban.db
sqlite3 ~/.hermes/kanban.db "VACUUM;"
```

### When NOT to clean
- If archived boards contain run history needed for debugging recent task failures
- If archived tasks are referenced by still-active parent→child dependency chains

## 9. Diagnosis Patterns

| Symptom | Likely Cause | Fix |
|:--|:--|:--|
| exit_code=9 (SIGKILL) on multiple simultaneous tasks | Resource pressure during concurrent spawn | Reduce concurrent dispatch, or retry sequentially |
| exit_code=9 + OOM in dmesg | Actual memory exhaustion | Reduce worker count, add swap |
| Tasks done but result=NULL | Worker called kanban_complete without summary | Manual review needed, check comments |
| Blocked with "waiting for parent" + parent archived | Dependency chain broken by archive | Unblock → archive, or recreate parent |
| QQ Bot delivery: channel=400 c2c=500 | Bot token expired or channel invalid | Check QQ Bot token, verify chat_id |
| Summary cron 404 on all task IDs | Boards referenced by cron were archived | Remove stale cron, clean archived boards (see §8) |
| `sqlite3.OperationalError: no such table: tasks` in gateway log | Board DB exists but has 0 tables — never schema-initialized | DDL copy from healthy board → recreate DB → restart gateway (see `references/empty-db-recovery.md`) |
