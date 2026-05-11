---
allowed-tools:
- cronjob
- terminal
- read_file
- search_files
author: unknown
description: 'Systematic diagnosis of failed Hermes cron jobs. Step-by-step checklist:
  timeout limits, script path mismatches, delivery platform dead, API keys expired,
  scheduler health.'
execution: manual
name: cron-job-failure-diagnosis
trigger:
- 'cron job returns last_status: error'
- cron job produces empty/no response
- cron delivery fails with 'platform not configured/enabled'
- cron output file shows '(No response generated)'
- user reports 'cron did not run' or 'scheduled task did not execute'
version: 1.3.0
---

# Cron Job Failure Diagnosis — Hermes

## Why This Skill Exists

Hermes cron jobs fail silently in the background. The scheduler ticker may be running, the job may trigger, but failures happen in an isolated agent session with limited context. Standard debugging skills don't check the cron-specific locations.

## Prevention: Check Before Creating Cron Jobs

**Apply this checklist BEFORE creating any new cron job.** Conflicts waste tokens, cause silent failures, and degrade scheduler reliability.

### P1. Check Schedule Conflicts

Run conflict detection before adding any new cron:

```bash
python3 ~/.hermes/skills/development/cron-job-failure-diagnosis/scripts/check_cron_conflicts.py
```

This checks:
- **Same-time conflicts**: multiple crons at the exact same minute → stagger by ≥5 min
- **30-min congestion**: ≥4 crons within a 30-min window → consolidate or spread out
- **Duplicate jobs**: same function, same schedule → remove one (prefer no-agent script over LLM)

### P2. Delivery Platform Decision

**Know what's alive and what's dead:**

| Platform | Status | Notes |
|----------|--------|-------|
| QQ Bot (qqbot:*) | ✅ Active | WebSocket to `wss://api.sgroup.qq.com`, session times out every 30min but auto-reconnects. Cron delivery works. |
| WeChat/iLink | ❌ Deprecated | iLink service decommissioned. Do NOT create new crons targeting weixin:*. All existing WeChat delivery should be migrated to QQ Bot. |

**Verify QQ Bot connectivity:**
```bash
grep 'QQBot.*WebSocket connected\|QQBot.*Ready' ~/.hermes/logs/gateway.log | tail -3
```
Expected: `WebSocket connected to wss://api.sgroup.qq.com/websocket` + `Ready, session_id=...`
If missing → check `systemctl --user status hermes-gateway.service`

**Delivery split by content type:**

| Content type | Delivery | Examples |
|-------------|----------|----------|
| User-facing results | `qqbot:*` | 早报/复盘/周报/信号日报/雪球发布确认/量化周报/教训提炼/自优化报告 |
| Data pipeline intermediate | `local` | K线更新/两融数据/图表生成 |
| System maintenance | `local` | agenda-builder/graphify/gbrain-sync/memory-curator/wiki-soul-sync/session-miner/circuit-guard |

**Density rules for qqbot deliveries:**
- ≤5 push deliveries per day total
- ≥30min gap between consecutive pushes (QQ Bot handles this via async queue, but dense scheduling wastes tokens)
- If schedule collides with existing push → merge into a single prompt rather than adding a separate cron
- Non-urgent monitors prefer `deliver: local`

### P3. Check Pipeline Order

If the new cron belongs to an existing pipeline (e.g., A股数据 → 分析 → 发布):

- Verify dependency order: data collection MUST precede analysis which MUST precede publish
- Stagger dependent stages by ≥15 min to allow completion
- Same-pipeline tasks at the same minute cause data freshness issues

### P4. Check Merge Opportunity

When a new cron would create a 3rd+ job in the same hour block:

- Assess: can this be merged into an existing cron's prompt?
- Merged crons cost 1 LLM invocation instead of N → significant savings
- Example: `circuit-guard-hourly` + `hourly-circuit-check` were duplicates at `0 * * * *` — removed the LLM-based one

### P5. Stdout Hygiene for no_agent Script Crons

**Critical rule**: When a cron job has `no_agent: true` and `deliver: qqbot` (or any messaging platform), **every `print()` to stdout ends up in the chat**. The cron delivery channel treats stdout as the message body — there is no "local log vs. delivered content" distinction.

**Good pattern — debug to stderr, events to stdout:**
```python
# ❌ Wrong: routine tick messages go to QQ every 30 min
print("⏳ WAIT 未到期，下次 tick 再检查")
print("[tick] pipeline=X stage=2 ...")

# ✅ Correct: debug/status to stderr (local logs only)
print("⏳ WAIT 未到期，下次 tick 再检查", file=sys.stderr)
print("[tick] pipeline=X stage=2 ...", file=sys.stderr)

# Real notifications to stdout (delivered to QQ)
print("✅ Pipeline 完成: 数据采集")
```

**Audio test**: Before committing, run the script and check what goes to stdout vs stderr:
```bash
echo "=== Would go to QQ ===" && python3 script.py 2>/dev/null
echo "=== Local only ===" && python3 script.py 1>/dev/null
```

**Commit to this pattern for any no_agent cron that runs on a schedule <1h:**
- `print("...", file=sys.stderr)` for: tick traces, WAIT not-due messages, retry attempts, status quo confirmations
- `print("...")` (stdout) for only: completions, failures, L3 pauses, user-actionable events
- If the script has no events on a routine tick, stdout should be **completely empty**

**Failure signature if violated**: QQ Bot receives ⏳WAIT 未到期 / tick debug / retry logs every cron cycle. User sees spam every N minutes.

### P5b. Choose no_agent for Script-Only Crons

**Critical rule**: If a cron job just runs a Python/shell script (no LLM reasoning needed), set `no_agent=true` and point `script` at the script path.

**Why**: LLM-driven crons (`no_agent=false`) consume from the LLM credential pool. When pool is exhausted (expired keys, rate limited), the cron fails with 401 even though the **script itself doesn't need an LLM**. This wasted an entire afternoon of K线 updates (2026-05-08).

**Pattern:**
```yaml
# ❌ Wrong: LLM-driven cron for a pure script
schedule: "0 16 * * 1-5"
no_agent: false       # starts an agent, eats credential pool
prompt: "Run python3 ~/quant/daily_kline_update.py"  # agent just runs terminal...

# ✅ Correct: script-mode cron
schedule: "0 16 * * 1-5"
no_agent: true
script: "daily_kline_update.sh"   # wrapper in ~/.hermes/scripts/
```

**When the script lives outside ~/.hermes/scripts/**: Create a thin wrapper:
```bash
#!/bin/bash
exec /path/to/quant_env/bin/python3 /path/to/actual_script.py "$@"
```
Save it to `~/.hermes/scripts/<name>.sh`, then reference it from cron config.

### P6. Check MCP Process Proliferation Before Diagnosing Cron Failures

Multiple MCP server processes (e.g. 5x `mcp-graphify.py`) cause cron job conflicts, graph corruption, or silent failures.

Before diving into a cron failure diagnosis, run:
```bash
ps aux | grep mcp- | grep -v grep
```

If any MCP server has >1 process:
```bash
# Kill all but the latest for each server
for srv in mcp-graphify mcp-mysql mcp-hermes-cron; do
  count=$(ps aux | grep "$srv"'.py' | grep -v grep | wc -l)
  if [ "$count" -gt 1 ]; then
    echo "Killing $count - 1 instances of $srv..."
    ps aux | grep "$srv"'.py' | grep -v grep | sort -k11 | head -n -1 | awk '{print $2}' | xargs kill
  fi
done
```

MCP process proliferation typically happens after repeated gateway restarts. Normal state is exactly 1 process per MCP server.

If this is a proactive cron creation (not user-requested), inject the cron conflict lesson:

```bash
python3 ~/.hermes/scripts/lesson_inject.py inject --domain ops-domain
```

The lesson store already contains "创建cron前必须检查已有调度冲突" (ops-domain, HIGH severity).

## Diagnosis Checklist (in order)

### 1. Check Cron Job Status

```
cronjob list
```

Look for:
- `last_status`: `error` vs `ok`
- `last_delivery_error`: free-text error message
- `last_run_at`: when did it last try
- `state`: `scheduled` vs `paused`

### 2. Check Raw Job Config

```
cat ~/.hermes/cron/jobs.json | python3 -m json.tool
```

Compare `next_scheduled_at` against current time. Empty means job is not queued.

### 3. Read Cron Output

```
ls -lt ~/.hermes/cron/output/<job_id>/
cat ~/.hermes/cron/output/<job_id>/<latest>.md
```

The output file contains the full agent response. Common failures:
- `"(No response generated)"` — agent timed out or empty model response
- `"[SILENT]"` — agent chose not to report (legitimate)
- Error traceback — script-level failure

### 4. Check Terminal Timeout

```
grep TERMINAL_TIMEOUT ~/.hermes/.env
```

If cron script runs longer than `TERMINAL_TIMEOUT` (default 60s), terminal command is killed.

**Fix:** Increase to 600 (or match actual script runtime).

### 5. Check Script Path and Version

```
ls -la /path/to/script.py
diff /path/to/script.py /path/to/standalone_copy.py | head -30
```

**Fix:** Sync skill script with newer standalone version.

#### 5a. Script Path Double-Resolution Bug (Hermes-side bug)

**Symptom:** Output file says `Status: script failed` with path like:
`/home/pebynn/.hermes/scripts/.hermes/profiles/writing-domain/skills/.../script.py`

Note the double `.hermes` — the cron runner resolved a relative script path against `~/.hermes/scripts/` even though the path was already relative to `~/.hermes/`.

**Diagnosis:**
```bash
# Compare what the output file says vs actual location
cat ~/.hermes/cron/output/<job_id>/<latest>.md | grep 'Script not found'
find ~/.hermes/profiles -name "script_name.py"
```

**Workaround:** Set the job's `script` field to an absolute path (not relative) via `cronjob edit`.

#### 5b. no_agent Mode Mismatch (Hermes-side bug)

**Symptom:** Output file header says `Mode: no_agent (script)` but `jobs.json` shows `"no_agent": false` and `"script": null`. The cron runner treated an agent-mode job as a script job.

**Diagnosis:**
```bash
# Compare mode in output vs config
head -1 ~/.hermes/cron/output/<job_id>/<latest>.md
python3 -c "import json; [print(j['no_agent'], j['script']) for j in json.load(open('/home/pebynn/.hermes/cron/jobs.json'))['jobs'] if j['id']=='<job_id>']"
```

**Root cause (suspected):** The cron runner may derive a script path from the job's prompt or cached state when the execution context is ambiguous.

**Workaround 1:** Delete and recreate the cron job with a fresh config.
**Workaround 2:** If the job was meant to be agent-mode (its prompt has `cd ... && python3 ...` inline), ensure `no_agent` stays `false` and re-save.
**Workaround 3:** If script-mode is intentional, set `"script"` to the full absolute path and `"no_agent": true`.

### 6. Check Delivery Platform

If `last_delivery_error` contains "platform not configured/enabled":

```
grep -i weixin ~/.hermes/logs/gateway.log | tail -5
grep WEIXIN_TOKEN ~/.hermes/.env
ls ~/.hermes/weixin/accounts/
```

**Fix:** QR login to get fresh token, or restore from accounts file.

### 7. Check .env Format Corruption

```
head -5 ~/.hermes/.env | od -c | head -5
```

If lines start with digits and `|` (e.g., `21|WEIXIN_TOKEN=...`), strip them:

```
python3 -c "
import re
with open('/home/pebynn/.hermes/.env') as f:
    content = f.read()
cleaned = re.sub(r'^\d+\|', '', content, flags=re.MULTILINE)
with open('/home/pebynn/.hermes/.env', 'w') as f:
    f.write(cleaned)
"
```

### 8. Check Gateway/Scheduler Health

```
systemctl --user status hermes-gateway.service
grep 'Cron ticker' ~/.hermes/logs/gateway.log | tail -3
```

**Fix:** Restart gateway if ticker stopped.

### 9. Force Re-run

```bash
cronjob run job_id=<id>
sleep 70
ls -lt ~/.hermes/cron/output/<job_id>/
```

### 10. Add Local File Fallback (Prevent Future Silent Loss)

Delivery may succeed one day and fail the next (WeChat session timeout, platform restart). **Always pair delivery with a local file save** so data is never lost:

```bash
mkdir -p /home/pebynn/文档
python3 -c "
import json, glob
from datetime import date
jobs = json.load(open('/home/pebynn/.hermes/cron/jobs.json'))
# Find latest output for job
jd = '<job_id>'
files = sorted(glob.glob(f'/home/pebynn/.hermes/cron/output/{jd}/*.md'))
if files:
    content = open(files[-1]).read()
    today = date.today().strftime('%Y-%m-%d')
    path = f'/home/pebynn/文档/多因子{today}.md'
    open(path, 'w').write(content)
    print(f'Saved to {path}')
"
```

**Update cron prompt** to include this step as a mandatory post-run action regardless of delivery status.

### 11. iLink Rate Limiting Diagnosis

**症状**: `last_delivery_error` 含 `iLink sendmessage rate limited: ret=-2`，多个 cron job 同时报此错误。

**根因**: WeChat iLink 网关有严格频率限制。密集投递（如多个 cron 在同一分钟或多个 job 在相近时间）触发全局限频，冷却约 1 小时。

**诊断路径**:

1. 检查 errors.log 中的 `[session_id]` — 揭示哪个会话在消耗配额
   ```bash
   tail -30 ~/.hermes/logs/errors.log | grep 'rate limited'
   ```

2. 判断是旧队列还是新投递
   - session_id 时间戳是过去的 → 旧队列在重试，每次重试刷新冷却计时器
   - Gateway 重启后旧队列仍会重试（cron delivery 持久化）

3. 检查 WeChat 投递密度
   ```bash
   cronjob list | grep 'weixin:'
   ```

**修复（三管齐下）**:

- **立即**: 等冷却周期过（约 1h），不要反复测试（每次测试刷新计时器）
- **中期**: cron 归并减少 weixin 投递密度（≤5 条/天，间隔 ≥2h）
- **长期**: 非紧急任务改 `deliver: local`

**防止复发**: 
- session-watchdog、cost-report 等高频任务走 local
- WeChat 投递任务间隔 ≥2h
- 同时间段合并（如 08:00+08:05 → 08:00 单次）

## Quick Reference: Common Failure Signatures

| Symptom | Likely Root Cause | Fix |
|---------|------------------|-----|
| "No response generated" | TERMINAL_TIMEOUT too low | Increase to 600 |
| "platform not configured/enabled" | Delivery token is placeholder | QR login or restore |
| Script runs old logic | Script path points to stale version | Sync from standalone copy |
| Cron ticker not logging | Gateway crashed | Restart gateway |
| WeChat sends fail with errcode=-14 | Active push session expired | User sends message to bot to refresh, or schedule cron delivery (uses response path) |
| `iLink sendmessage rate limited: ret=-2` | WeChat iLink 已废弃 | 改用 QQ Bot 投递（见 `references/qqbot-connectivity-check.md`） |
| `Timeout context manager should be used inside a task` | aiohttp `TimerContext.__enter__` loses task context after event loop reconnection + rate limiting | **Fixed in code** (2026-05-03): `_api_post` in weixin.py retries via `asyncio.create_task()`. Verify fix present if seen again. |
| .env vars not read | Line number corruption | Strip N| prefixes |
| "Authentication Fails" | API key expired | Run api-key-rotation skill |
| "Script not found" with double `.hermes` in path (e.g. `.../scripts/.hermes/...`) | Hermes path resolution bug — script path resolved against `~/.hermes/scripts/` when already relative to `~/.hermes/` | Set `script` to absolute path (§5a) |
| Output header says `Mode: no_agent (script)` but `no_agent: false` in config | Cron runner mode mismatch — agent job executed as script | Recreate job or fix config (§5b) |
| Cron step silent-waste | `python3 -c \"from nonexistent_module import X\"` in cron stderr not captured, step silently skips | Test import inline first |
| F-string backslash in cron script | `print(f\\\"...{len('\\\\\\\\n'.join(x))}\\\")` passes `py_compile` on Python 3.12 but fails on 3.11 venv runtime | Pre-compute to variable before f-string usage (see `references/python311-fstring-backslash-compat.md`) |
| Worker process zombies | Previous failed cron leaves orphaned subprocesses (e.g. 8x multiprocessing workers) consuming CPU, competing with new runs | Kill orphans before re-run: `pkill -9 -f script_name` |
| **Shell escaping in cron scripts** | Inline `python3 -c` with complex strings (Chinese, emoji, JSON) breaks — shell interprets quotes/backslashes differently across layers | Use standalone .py files in `~/.hermes/scripts/`, never inline `python3 -c "..."` with special characters. If a pipeline stage script, put it in `~/.hermes/scripts/pipeline_stage_*.py` and reference by absolute path. |
| Session reuse on re-run | `cronjob run` on job with existing session may extend old session, carrying stale/broken prompt context | Kill old workers first, then re-run |
| **Run-spillover skips next run** | Weekday cron (e.g. Mon-Fri 21:00) runs at 21:00 and finishes after midnight (e.g. 00:48). Scheduler sees last_run_at date = next day, thinks the job already ran that day, and skips the same day's scheduled run. **Most common with signal scans that take 30min+** | Detect: compare last_run_at date with next_run_at date. If last_run_at falls on a weekday and next_run_at skips to the next weekday, spillover occurred. Fix: (a) set N_WORKERS lower so job finishes same hour, (b) use `cronjob run` to force the missed run, (c) move cron earlier (e.g. 21:00→17:00) so it finishes before midnight. The **definitive fix** is to schedule crons that take >15min early enough (≥4h before midnight) to avoid spillover entirely. |
| **Credential pool exhaustion on script crons** | LLM-driven cron (no_agent=False) fails with 401 even though script doesn't need an LLM — credential pool is empty/has expired keys. Cron agent tries to run the script via terminal tool but the agent itself can't start. | **Fix: Set `no_agent=true` and point `script` at a wrapper.** Script-only crons should never go through the LLM credential pool. Create a wrapper in `~/.hermes/scripts/` if the actual script lives elsewhere. |
| **Python env mismatch in no_agent scripts** | Default `python3` missing pandas/numpy/quant deps; script runs via shell subprocess, errors on `ModuleNotFoundError` | Auto-redirect: check `sys.executable` vs target python, re-exec with `subprocess.run([TARGET_PY] + sys.argv)`. Reference: `pipeline_kline_integrity.py` fix (2026-05-08). |
| **no_agent stdout flood to QQ** | Script prints debug/tick/status to stdout on every run; `deliver: qqbot` pushes it verbatim | Move routine prints to `sys.stderr`, keep only notifications on stdout (§P5) |
| **Pipeline-runner (no_agent) last_status: error** | Pipeline stage script failed, or runner tick logic errored. Since `no_agent`, error not in agent.log. | Run `python3 ~/.hermes/scripts/pipeline_runner.py status` for per-pipeline errors. Common causes: (a) python dep mismatch; (b) verify script syntax error; (c) transient from gateway restart. |
| **MCP process proliferation** | Multiple MCP server processes accumulate (e.g. 5x `mcp-graphify.py`), causing cron job conflicts, graph corruption, or silent failures. | Before diagnosing cron failure, check `ps aux | grep mcp-<name> | wc -l`. If >1, kill all but the latest: `ps aux | grep mcp-servername.py | grep -v grep | sort -k11 | head -n -1 | awk '{print $2}' | xargs kill` |
| **Runaway cron job (10h+ runtime)** | Cron agent job runs far beyond expected duration, consuming tokens continuously. Caused by unbounded loops (e.g., processing all 500+ historical sessions one-by-one with LLM calls). Last_status may show `ok` because the job hasn't errored — it's just still running. | Detect: compare `last_run_at` vs current time. If gap >2h for a job expected to finish in <30min, it's runaway. Fix: `cronjob pause <id>` to stop the bleed, then add guards: hard timeout, batch limit, rate limiting. See `agent-self-maintenance` pitfall #9. |
| **Cost tracker shows $0.00** | `cost-daily-report` and `mcp_cost_guard_query_cost` both report zero cost across all sessions/models/days. This means runaway spends go undetected — user discovers from provider billing dashboard. | Check: `python3 ~/.hermes/scripts/cost-daily-report.py`. If output shows $0.0000 for all lines, the cost tracking backend is broken. Fix TBD — likely session cost aggregation pipeline failure. |
| **Non-trading day cron errors (false alarm)** | Market-data crons (K线更新, 两融数据, 复盘生成) fail with `last_status: error` on weekends/holidays. Do NOT retry or escalate. | Check `date +%u` (1=Mon, 7=Sun). If weekend AND market-data cron → auto-silence. Only escalate on trading day failures. |
| **Non-trading day hallucinated output (silent data poison)** | Cron runs and `last_status: ok` on a non-trading day, but generated content is entirely fabricated. Data collector has no trading-day gate → API returns stale/proxy data → AI generates fiction. Unlike the false-alarm case above, this is invisible to cron status monitoring. | Check: did the cron produce output on a known non-trading day? Look for `is_trading_day: True` in the data JSON. Fix: add `is_trading_day()` gate at collector entry point (weekend + holiday list). Also add turnover sanity check (A-share max ~5-6万亿). |
| **Playwright pipe failure on cron scripts** | Browser automation cron hangs with timeout because `--remote-debugging-pipe` doesn't work. | Convert to Selenium — see `references/playwright-to-selenium-fallback.md` for full mapping table. |
| **Kanban-based cron failure: task stuck blocked** | Kanban cron creates tasks via kanban_create, but worker spawn_failed or protocol_violation causes task to block. Cron itself reports `ok` but pipeline stalled. | Check `sqlite3 ~/.hermes/kanban.db "SELECT id,status,last_failure_error FROM tasks WHERE status='blocked'"`. Common causes: `unknown workspace_kind: dir:` (use `scratch`), auto-rebundle (skills count >1), config format (model.default vs model.model). Run `kanban_create` to reclaim blocked tasks. Auto-recovery: `bdc248cc237e` cron reclaims hourly. |
| **Runaway cron job (10h+ runtime)**
