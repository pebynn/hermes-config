# Autonomous Ops Pipeline (v2.2)

## Architecture

```
03:00  memory-curator (LLM)     → memory >85% → consolidate/upgrade/prune
08:00  agenda-builder (script)  → system health scan → daily.md (zero token)
08:05  ops-autopilot (LLM)      → reads daily.md → auto-fix L1/L2 → QQ-push L3
全天    cron-failure-watchdog     → every 30min → error.log scan → QQ Bot alert
21:00  daily-digest (LLM)       → batch summary → QQ Bot
22:00  error-learner (LLM)      → lesson extraction + injection
```

## Component Details

### agenda-builder (e512e447fb29)

Script-only cron at `~/.hermes/scripts/agenda_builder.py` (350 lines, v2.0).

**Checks performed:**
- Service health: Gateway (systemctl), MySQL (pgrep), DeepSeek API (curl)
- Cron status: `hermes cron list` text parsing for last_status=error
- Data freshness: MySQL K-line row count, draft file existence
- Pipeline schedule: today's expected pipeline stages
- Resources: disk %, memory used/available, session file count with stale-detection
- Error intelligence: scans errors.log, filters 13 noise patterns, groups by category

**Output:** `~/.hermes/agenda/daily.md` — structured markdown with actionable fix commands.

### ops-autopilot (bd5de39ac76e)

LLM-driven cron, runs 5 minutes after agenda-builder. Tools: terminal, file, web, search, cronjob.

**Workflow:**
1. Load state: daily.md + pending.md + pipeline.yaml + cronjob list + memory usage
2. Diagnose issues by severity (🔴 P0 → 🟠 P1 → 🟡 P2)
3. Auto-fix L1/L2: cron retry, service restart, file cleanup, cache pruning
4. Check pipeline dependencies: if preconditions met → trigger next stage
5. Rollover incomplete tasks to pending.md
6. Report via QQ Bot: what was fixed + what needs user decision

### memory-curator (2698791c5f60)

LLM-driven cron, runs daily 03:00. Tools: terminal, file, memory, skill_manage.

**Workflow:**
1. Check memory usage % via memory tool
2. If <80%: skip
3. If ≥80%: audit entries → categorize as delete/merge/upgrade/keep
4. Execute: remove obsolete, merge related, upgrade stable workflows to skills
5. Target: usage <70%, entry_count ≤22

**Upgrade paths:**
- Stable workflow (5+ uses) → skill_manage create/patch
- Critical lesson (3+ corrections) → ensure in lessons/ or SOUL.md
- Configuration rules → ensure in config or SOUL.md

### pipeline.yaml

Located at `~/.hermes/agenda/pipeline.yaml`. Defines:

- **Pipeline stages** with cron IDs, schedule times, dependencies, produce files
- **Rollover rules**: on failure → record to pending.md, retry next cycle
- **Auto-fix rules**: pattern-matched actions for common failures

## Decision Flow

```
daily.md issue detected
  → L1 (bug fix, data anomaly, pipeline repair, health check)
    → ops-autopilot fixes immediately, reports in summary only
  → L2 (new monitoring, cron adjust, config tweak, script refactor)
    → ops-autopilot evaluates, fixes if straightforward, else records
  → L3 (API key change, architecture change, external publish, funding)
    → ops-autopilot queues for QQ Bot notification → user decides
```

## Key Design Decisions

1. **Zero-token agenda generation**: agenda-builder is script-only (no_agent=true). All intelligence is in the detection logic, not LLM reasoning.
2. **LLM for action, not detection**: ops-autopilot uses LLM to decide HOW to fix, not WHAT to fix. The daily.md already contains the what.
3. **Memory cost control**: memory-curator runs daily to prevent token bloat. Target <70% from a 6000-char budget. Realized savings: 98%→72% in first manual run.
4. **One QQ Bot push per day**: ops-autopilot is the single daily ops report. Watchdog only fires on exceptions.
