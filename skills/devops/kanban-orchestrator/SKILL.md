---
name: kanban-orchestrator
description: Decomposition playbook + specialist-roster conventions + anti-temptation rules for an orchestrator profile routing work through Kanban. The "don't do the work yourself" rule and the basic lifecycle are auto-injected into every kanban worker's system prompt; this skill is the deeper playbook when you're specifically playing the orchestrator role.
version: 2.2.0
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, routing]
    related_skills: [kanban-worker]
---

# Kanban Orchestrator — Decomposition Playbook

> The **core worker lifecycle** (including the `kanban_create` fan-out pattern and the "decompose, don't execute" rule) is auto-injected into every kanban process via the `KANBAN_GUIDANCE` system-prompt block. This skill is the deeper playbook when you're an orchestrator profile whose whole job is routing.

## ⚠️ Anti-Pattern: Using delegate_task in Kanban Mode

When operating as a kanban orchestrator, **never call delegate_task directly**. The orchestrator is a pure router — all work goes through kanban_create. delegate_task should only be used internally by kanban workers, never by the orchestrator.

```
✅ Correct:  kanban_create(title="analyze stocks", assignee="finance")
❌ Wrong:    delegate_task(goal="analyze stocks", domain="finance-domain")
```

The orchestrator's toolset should NOT include delegate_task. If it's present, remove it. Simple queries (read_file, web_search, terminal) can be done directly — only domain-level reasoning tasks need kanban workers.

## When to use the board (vs. just doing the work)

Create Kanban tasks when any of these are true:

1. **Multiple specialists are needed.** Research + analysis + writing is three profiles.
2. **The work should survive a crash or restart.** Long-running, recurring, or important.
3. **The user might want to interject.** Human-in-the-loop at any step.
4. **Multiple subtasks can run in parallel.** Fan-out for speed.
5. **Review / iteration is expected.** A reviewer profile loops on drafter output.
6. **The audit trail matters.** Board rows persist in SQLite forever.

If *none* of those apply — it's a small one-shot reasoning task — use `delegate_task` instead or answer the user directly.

## The anti-temptation rules

Your job description says "route, don't execute." The rules that enforce that:

- **Do not execute the work yourself.** Your restricted toolset usually doesn't even include terminal/file/code/web for implementation. If you find yourself "just fixing this quickly" — stop and create a task for the right specialist.
- **For any concrete task, create a Kanban task and assign it.** Every single time.
- **If no specialist fits, ask the user which profile to create.** Do not default to doing it yourself under "close enough."
- **Decompose, route, and summarize — that's the whole job.**

## The standard specialist roster (convention)

Unless the user's setup has customized profiles, assume these exist. Adjust to whatever the user actually has — ask if you're unsure.

| Profile | Does | Typical workspace |
|---|---|---|
| `researcher` | Reads sources, gathers facts, writes findings | `scratch` |
| `analyst` | Synthesizes, ranks, de-dupes. Consumes multiple `researcher` outputs | `scratch` |
| `writer` | Drafts prose in the user's voice | `scratch` or `dir:` into their Obsidian vault |
| `reviewer` | Reads output, leaves findings, gates approval | `scratch` |
| `backend-eng` | Writes server-side code | `worktree` |
| `frontend-eng` | Writes client-side code | `worktree` |
| `ops` | Runs scripts, manages services, handles deployments | `dir:` into ops scripts repo |
| `pm` | Writes specs, acceptance criteria | `scratch` |

### Model routing for kanban workers (2026-05)

Different worker roles benefit from different models. Pro for reasoning, flash for mechanical execution:

| Worker | Model | Reason |
|:--|:--|:--|
| researcher | v4-pro | Needs judgment on information quality |
| analyst/finance | v4-pro | Quantitative reasoning + signal judgment |
| writer | v4-pro | Content quality + instruction following |
| reviewer | v4-pro | Finding subtle issues needs reasoning |
| code/backend-eng | glm-5.1 or flash | Coding. flash for simple scripts, glm for complex |
| ops | v4-flash | Mechanical script execution |
| simple listing/fulfillment workers | v4-flash | Script execution, no reasoning needed |

flash is ~1/4 the cost of pro. Routing mechanical workers to flash saves $10-15/day at scale.

### Domain-to-kanban mapping (Hermes 6-domain system)

When migrating from delegate_task-based domains to kanban workers:

| Original domain | Maps to kanban worker(s) | Notes |
|:--|:--|:--|
| ec-domain | ec-sourcing + ec-listing + ec-fulfillment | **Must split**: 3 phases have different toolsets and models |
| writing-domain | writer + reviewer | **Must split**: creation and review need different system prompts |
| finance-domain | finance (single worker) | Keep as one: collection→calc→signal is tightly coupled |
| code-domain | code (single worker) | Direct 1:1 mapping |
| ops-domain | ops (single worker) | Direct 1:1 mapping |
| research-domain | researcher (single worker) | Direct 1:1 mapping |

**Splitting principle**: A domain should be split into multiple kanban workers when:
1. Its phases have different toolset needs (browser vs terminal-only)
2. Its phases have different model needs (pro-reasoning vs flash-mechanical)
3. Its phases are natural serial dependencies (kanban parent→child graph)
4. One phase needs to gate another (reviewer blocking publisher)

**Don't split when**: phases are tightly coupled (finance's collection→calculation→signal share the same dataset in memory).

## Decomposition playbook

### Step 1 — Understand the goal

Ask clarifying questions if the goal is ambiguous. Cheap to ask; expensive to spawn the wrong fleet.

### Step 2 — Sketch the task graph

Before creating anything, draft the graph out loud (in your response to the user). Example for "Analyze whether we should migrate to Postgres":

```
T1  researcher        research: Postgres cost vs current
T2  researcher        research: Postgres performance vs current
T3  analyst           synthesize migration recommendation       parents: T1, T2
T4  writer            draft decision memo                       parents: T3
```

Show this to the user. Let them correct it before you create anything.

### Step 3 — Create tasks and link

```python
t1 = kanban_create(
    title="research: Postgres cost vs current",
    assignee="researcher",
    body="Compare estimated infrastructure costs, migration costs, and ongoing ops costs over a 3-year window. Sources: AWS/GCP pricing, team time estimates, current Postgres bills from peers.",
    tenant=os.environ.get("HERMES_TENANT"),
)["task_id"]

t2 = kanban_create(
    title="research: Postgres performance vs current",
    assignee="researcher",
    body="Compare query latency, throughput, and scaling characteristics at our expected data volume (~500GB, 10k QPS peak). Sources: benchmark papers, public case studies, pgbench results if easy.",
)["task_id"]

t3 = kanban_create(
    title="synthesize migration recommendation",
    assignee="analyst",
    body="Read the findings from T1 (cost) and T2 (performance). Produce a 1-page recommendation with explicit trade-offs and a go/no-go call.",
    parents=[t1, t2],
)["task_id"]

t4 = kanban_create(
    title="draft decision memo",
    assignee="writer",
    body="Turn the analyst's recommendation into a 2-page memo for the CTO. Match the tone of previous decision memos in the team's knowledge base.",
    parents=[t3],
)["task_id"]
```

`parents=[...]` gates promotion — children stay in `todo` until every parent reaches `done`, then auto-promote to `ready`. No manual coordination needed; the dispatcher and dependency engine handle it.

### Step 4 — Complete your own task

If you were spawned as a task yourself (e.g. `planner` profile was assigned `T0: "investigate Postgres migration"`), mark it done with a summary of what you created:

```python
kanban_complete(
    summary="decomposed into T1-T4: 2 researchers parallel, 1 analyst on their outputs, 1 writer on the recommendation",
    metadata={
        "task_graph": {
            "T1": {"assignee": "researcher", "parents": []},
            "T2": {"assignee": "researcher", "parents": []},
            "T3": {"assignee": "analyst", "parents": ["T1", "T2"]},
            "T4": {"assignee": "writer", "parents": ["T3"]},
        },
    },
)
```

### Step 5 — Report back to the user

Tell them what you created in plain prose:

> I've queued 4 tasks:
> - **T1** (researcher): cost comparison
> - **T2** (researcher): performance comparison, in parallel with T1
> - **T3** (analyst): synthesizes T1 + T2 into a recommendation
> - **T4** (writer): turns T3 into a CTO memo
>
> The dispatcher will pick up T1 and T2 now. T3 starts when both finish. You'll get a gateway ping when T4 completes. Use the dashboard or `hermes kanban tail <id>` to follow along.

## Common patterns

**Fan-out + fan-in (research → synthesize):** N `researcher` tasks with no parents, one `analyst` task with all of them as parents.

**Pipeline with gates:** `pm → backend-eng → reviewer`. Each stage's `parents=[previous_task]`. Reviewer blocks or completes; if reviewer blocks, the operator unblocks with feedback and respawns.

**Same-profile queue:** 50 tasks, all assigned to `translator`, no dependencies between them. Dispatcher serializes — translator processes them in priority order, accumulating experience in their own memory.

**Human-in-the-loop:** Any task can `kanban_block()` to wait for input. Dispatcher respawns after `/unblock`. The comment thread carries the full context.

**Multi-domain parallel research (when deep_research unavailable):** Use `execute_code` to batch `web_search()` calls covering N research directions in parallel (one tool call, ~2s per topic). Then `web_extract` the top 3-5 URLs for depth. Combine with `graph_search` for existing knowledge. This covers 10+ domains in <20s. Use this when the orchestrator needs to gather intelligence before routing — it's the orchestrator's own research capability (no need to spawn research workers for simple information gathering).

**Cross-session kanban result delivery (QQ Bot):** When dispatching multi-task kanban work that will complete across sessions, set up automatic delivery so the user gets results without waiting in the current session:

```bash
# 1. Subscribe each task to QQ Bot notification
for tid in t_xxx t_yyy t_zzz; do
  hermes kanban notify-subscribe --platform qqbot --chat-id A88D... "$tid"
done

# 2. Create summary cron that polls all tasks, aggregates results, pushes, then self-destructs
# Key: cron repeat=N, deliver=qqbot, Step 5 deletes itself via cronjob remove
```

The summary cron pattern: poll task statuses → if all done, aggregate summaries → push via notify.py → `cronjob action=remove` self-destruct. If any task blocked/failed, report the problem. If any still running, exit silently (next tick handles it). Use `repeat=N` to cap retries (e.g. repeat=20 for ~10h coverage at 30m intervals).

**Batch SOUL.md startup protocol injection:** All kanban workers should have a mandatory `## 🚀 Startup Protocol` section that forces graph_search + lessons loading before any task. Batch-inject across N profiles with `execute_code` reading each SOUL.md and using `patch()` with a known anchor line (e.g. `## 核心能力`). Template:

```markdown
## 🚀 Startup Protocol (MANDATORY — injected YYYY-MM-DD)

Before ANY task execution, load domain knowledge:

1. **Graph Knowledge**: `graph_search("{query}")` — query the knowledge graph
2. **Domain Lessons**: `read_file("~/.hermes/lessons/{domain}.md")` — load accumulated lessons
3. **This SOUL.md** is already in your context — re-read if uncertain about constraints

⏱️ Budget: ~30s startup overhead. Skip only if task body explicitly says "no_startup".
```

Mapping: `{query}` = `lesson:<domain>`, `{domain}` = profile name minus `-domain` suffix. EC workers (sourcing/listing/fulfillment) all use `lesson:ec` and `lessons/ec-domain.md`. Writer + reviewer both use `lesson:writing` and `lessons/writing-domain.md`.

## Cross-Session Notification (QQ Bot)

When the orchestrator dispatches long-running kanban tasks that may complete after the current session ends, use `kanban notify-subscribe` so results reach the user via QQ Bot:

```bash
hermes kanban notify-subscribe --platform qqbot --chat-id A88D89DDAFEE6A7ED7EB35325B1AEA12 <task_id>
```

For batch task orchestration (5+ parallel workers), also create a summary cron:

```bash
hermes cronjob create --name "汇总+QQ推送" \
  --schedule "every 30m" --repeat 20 \
  --deliver "qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12" \
  --toolsets terminal,file
```

The summary cron: checks all task statuses → when all done → aggregates outputs → pushes QQ Bot → self-deletes. User preference: active session = report in-chat; session ended = QQ Bot fallback.

## Startup Protocol Injection (Worker Knowledge Loading)

All 9 kanban workers should load domain knowledge on startup. Batch-inject this pattern into worker SOUL.md:

```markdown
## 🚀 Startup Protocol (MANDATORY)

Before ANY task execution, load domain knowledge:

1. **Graph Knowledge**: `graph_search("lesson:<domain>")` — query the 134K-node knowledge graph
2. **Domain Lessons**: `read_file("~/.hermes/lessons/<domain>.md")` — load accumulated lessons
3. **This SOUL.md** is already in your context — re-read if uncertain about constraints

⏱️ Budget: ~30s startup overhead. Skip only if task body explicitly says "no_startup".
```

Insert before `## 核心能力` section. Use `patch` tool for bulk injection across all profiles.

## Worker Model Switching

When a worker model is underperforming (slow startup, timeouts, poor instruction following):

1. Edit `~/.hermes/profiles/<name>/config.yaml`:
```yaml
model:
  default: <target-model>
  provider: <provider>
  base_url: <base-url>
```

2. Verify with: `python3 -c "import yaml; yaml.safe_load(open('config.yaml')); print('✅')"`

3. Worker picks up new model on next dispatch. No gateway restart needed.

**Real case 2026-05-11**: code-domain switched from `glm-5.1` (16min timeout, 2 reclaims) to `deepseek-v4-pro` (6min completion). V4-pro costs ~2x but eliminates reclaim costs and improves instruction following for superpowers enforcement.

## Pitfalls

**`boards rm --delete` 不清理文件系统（2026-05-14 已验证）。** `hermes kanban boards rm --delete <slug>` 只清空 board 内的任务数据，但保留 board 目录和空 kanban.db 文件。board 列表读取的是文件系统目录，删除后 board 仍会显示为 `(empty)`。必须手动清理：

```bash
# 正确做法：两步
hermes kanban boards rm --delete <slug>
rm -rf ~/.hermes/kanban/boards/<slug>

# 批量清理非 default 看板
for slug in $(hermes kanban boards list | tail -n +2 | awk '{print $1}' | grep -v default); do
    hermes kanban boards rm --delete "$slug"
    rm -rf ~/.hermes/kanban/boards/"$slug"
done
```

归档目录 `_archived/` 同理，删除看板后归档残留需手动 `rm -rf ~/.hermes/kanban/boards/_archived/*`。

**Reassignment vs. new task.** If a reviewer blocks with "needs changes," create a NEW task linked from the reviewer's task — don't re-run the same task with a stern look. The new task is assigned to the original implementer profile.

**Argument order for links.** `kanban_link(parent_id=..., child_id=...)` — parent first. Mixing them up demotes the wrong task to `todo`.

**Don't pre-create the whole graph if the shape depends on intermediate findings.** If T3's structure depends on what T1 and T2 find, let T3 exist as a "synthesize findings" task whose own first step is to read parent handoffs and plan the rest. Orchestrators can spawn orchestrators.

**Tenant inheritance.** If `HERMES_TENANT` is set in your env, pass `tenant=os.environ.get("HERMES_TENANT")` on every `kanban_create` call so child tasks stay in the same namespace.

**Board deletion leaves empty directories.** (2026-05-14) `hermes kanban boards rm --delete <slug>` removes task data from the board's SQLite DB but leaves the board directory and empty `kanban.db` file behind. The board still appears in `boards list` with `(empty)` counts. To fully remove: manually `rm -rf ~/.hermes/kanban/boards/<slug>/` after the `rm --delete` command. Also check `_archived/` for accumulated archived board snapshots and clean those with `rm -rf ~/.hermes/kanban/boards/_archived/*` if they're no longer needed.

**Profile bloat kills startup time.** (2026-05-11) Worker profiles overloaded with unused bundled skills (himalaya, google-workspace, linear, codex, touchdesigner-mcp, etc.) increase startup time from ~10s to 60-90s. Audit profiles with `hermes kanban diagnostics` and remove unused skills from profile skills/ directories. Each unnecessary skill directory adds ~2-3s to cold-start. **Formula**: keep only `devops/kanban-worker` in profile skills/ — all domain-specific skills live in `~/.hermes/skills/` and are loaded by task configuration, not profile bundling. Removing 35-65 bundled skills per profile takes disk from MBs to ~200KB and reduces startup by 30-80s.

**🚨 CRITICAL: Auto-bundle trap on first dispatch.** (2026-05-11) The hermes-agent auto-bundles 80+ skills into a profile's skills/ directory on first dispatch, even if you created the profile with only `devops/kanban-worker`. This undoes all cleanup. After a new profile's first kanban worker run, you MUST re-clean the profile's skills/ directory. Check with: `ls ~/.hermes/profiles/<name>/skills/` — if you see `apple/`, `gaming/`, `creative/`, etc., the auto-bundle happened.

**Fix: chmod 555 lock.** `.skills_prompt_snapshot.json` does NOT prevent auto-bundle. The only working fix is filesystem-level read-only lock:
```bash
# Clean then lock
python3 ~/.hermes/skills/devops/kanban-orchestrator/scripts/lock_profile_skills.py <profile_name>
# Or lock all profiles
python3 ~/.hermes/skills/devops/kanban-orchestrator/scripts/lock_profile_skills.py --all
# Verify
python3 ~/.hermes/skills/devops/kanban-orchestrator/scripts/lock_profile_skills.py --verify
```
Lock both `skills/` and `skills/devops/` with `chmod 555`. Verified across 3 dispatches — lock holds.

**Profile config format trap.** (2026-05-11) When creating new kanban worker profiles, the config.yaml `model` section must use `default` (not `model`) and must include `provider` + `base_url`. Wrong format causes workers to crash with HTTP 500 / OPENROUTER_API_KEY errors because the system falls back to unconfigured providers.

**`dir:` workspace_kind NOT supported.** (2026-05-11) Despite documentation listing `dir:<path>` as a valid workspace_kind, the actual kernel rejects it with "unknown workspace_kind: dir:/path". Only `scratch` is confirmed working. For tasks needing shared persistent directories, use `scratch` workspace and instruct the worker to `cd` to the target directory in the task body. Workers can read/write outside their scratch workspace — the workspace_kind only controls where the worker starts.

```yaml
# ✅ Correct
model:
  default: deepseek-v4-flash
  provider: deepseek
  base_url: https://api.deepseek.com/v1

# ❌ Wrong — causes "openrouter requested but OPENROUTER_API_KEY not set"
model:
  model: deepseek-v4-flash
```

**Gateway auto-discovers new profiles.** (2026-05-11) Creating a new profile directory under `~/.hermes/profiles/` with SOUL.md + config.yaml is sufficient — the running gateway's dispatcher picks up new profiles on the next tick without restart. Verified with writer profile.

**Commander must NOT use delegate_task.** (2026-05-11) In kanban mode, the commander is a pure kanban router. delegate_task is a worker-internal tool only. Using both creates two scheduling paths that defeat kanban's unified dependency graph.

**Gateway restart needed for kanban config.** (2026-05-11) Adding `kanban.dispatch_in_gateway: true` to config.yaml requires gateway restart to take effect. Until then, use `hermes kanban dispatch` for manual one-shot dispatch.

## Recovery stuck workers

When a worker profile keeps crashing, hallucinating, or getting blocked by its own mistakes (usually: wrong model, missing skill, broken credential), the kanban dashboard flags the task with a ⚠ badge and opens a **Recovery** section in the drawer. Three primary actions:

1. **Reclaim** (or `hermes kanban reclaim <task_id>`) — abort the running worker immediately and reset the task to `ready`. The existing claim TTL is ~15 min; this is the fast path out.
2. **Reassign** (or `hermes kanban reassign <task_id> <new-profile> --reclaim`) — switch the task to a different profile and let the dispatcher pick it up with a fresh worker.
3. **Change profile model** — the dashboard prints a copy-paste hint for `hermes -p <profile> model` since profile config lives on disk; edit it in a terminal, then Reclaim to retry with the new model.

Hallucination warnings appear on tasks where a worker's `kanban_complete(created_cards=[...])` claim included card ids that don't exist or weren't created by the worker's profile (the gate blocks the completion), or where the free-form summary references `t_<hex>` ids that don't resolve (advisory prose scan, non-blocking). Both produce audit events that persist even after recovery actions — the trail stays for debugging.

## Setup Checklist (2026-05-11 verified)

### Initialization

```bash
hermes kanban init                              # Create ~/.hermes/kanban.db
hermes kanban boards list                       # Verify board
```

### Config

```yaml
# ~/.hermes/config.yaml
kanban:
  dispatch_in_gateway: true      # Dispatcher runs inside gateway (default)
  dispatch_interval_seconds: 10  # Tick interval (default: 60)
  failure_limit: 2               # Consecutive non-success → auto-block
```

### Dispatcher

The standalone `hermes kanban daemon` command is **deprecated**. The dispatcher now runs inside the gateway:

```bash
hermes gateway start   # Starts gateway + embedded dispatcher
```

For manual one-shot dispatch (testing):
```bash
hermes kanban dispatch --dry-run   # Preview what would spawn
hermes kanban dispatch --max 3     # Spawn up to 3 ready tasks
```

### First Task Verification

```bash
# Create test task
hermes kanban create "test: kanban alive" --assignee ops-domain --body "echo ok"

# Dispatch (if gateway not running)
hermes kanban dispatch --max 1

# Check
hermes kanban show t_<id>
# Expect: status=running → (wait 30-60s) → status=done
```

### Pitfalls

**Gateway must be running for auto-dispatch.** If the gateway is not started, tasks stay in `ready` forever. Use `hermes kanban dispatch` for one-shot manual dispatch during testing.

**First worker startup is slow (30-90s).** Profiles with many bundled skills take time to load. This is normal — subsequent workers from the same profile may be faster due to filesystem caching.

**Worker profiles need clean toolsets.** Profiles overloaded with unused skills (himalaya, google-workspace, etc.) increase startup time. Audit profiles before assigning as kanban workers — see `references/profile-cleanup.md`.

**Don't run both standalone daemon AND gateway dispatcher.** They will race for claims. Stick to `dispatch_in_gateway: true`. If you truly need the old standalone daemon, use `hermes kanban daemon --force`.

**🚨 `mcp_deep_research_deep_research` requires TAVILY_API_KEY.** (2026-05-11) The deep-research MCP tool fails silently with "TAVILY_API_KEY environment variable is not set" if the key is missing. This tool cannot be used for research tasks until the key is configured. Verified on 2026-05-11 — tool returns error, not useful results.

**Fallback: parallel web_search via execute_code.** When deep_research is unavailable, use `execute_code` to batch multiple `web_search() + web_extract()` calls in parallel. This covers 10+ research directions in one tool call (~17s for 10 topics). Combine with `web_extract` on the top 3-5 URLs for deeper content. This pattern achieves ~80% of deep_research coverage at ~20% of the cost.

**Hub cascade fragility.** (2026-05-11) Research confirms: a single bad routing decision by the orchestrator can infect 100% of downstream tasks (vs 9.7-15.9% from leaf errors). Mitigation: always run `prompt-optimizer.infer_domain` before `kanban_create` to validate routing. Log routing rationale in task body for auditability.

**Boards `rm --delete` leaves empty directories.** (2026-05-14) `hermes kanban boards rm --delete <slug>` removes task data but leaves the board directory (`~/.hermes/kanban/boards/<slug>/`) with an empty `kanban.db` file. The board list is filesystem-based, so the stale board still shows up as `(empty)`. Fix: `rm -rf ~/.hermes/kanban/boards/<slug>` after `--delete`. Also clean `_archived/` directory for archived board remnants.

**Cron scripts must live under `~/.hermes/scripts/`.** (2026-05-14) The cron system rejects absolute paths and home-relative paths like `/home/pebynn/quant/signal_a_v2.sh`. Scripts must be placed in `~/.hermes/scripts/` and referenced by filename only. For scripts that need to run in a specific working directory, use `cd /target/dir && exec python3 script.py` inside the wrapper.

## Cross-Session Result Delivery (2026-05-11)

When orchestrator spawns a multi-task batch that may complete after the session ends:

- **Session active**: Deliver results directly in conversation (summarize done tasks, note running ones)
- **Session ended**: Dual-layer auto-delivery — see `references/cross-session-delivery-pattern.md`

Pattern: `hermes kanban notify-subscribe` on each task (Layer 1) + one-shot summary cron that self-cleans after aggregation (Layer 2). Cron checks `hermes kanban show` every 30min, aggregates when all done, pushes concise report to QQ Bot, then removes itself.

## Reference Files

- `references/cross-session-delivery-pattern.md` — Dual-layer result delivery: task notification subscriptions + self-cleaning summary cron for multi-task batches (2026-05-11).
- `references/hermes-migration-analysis.md` — Full migration analysis from delegate_task to kanban architecture: non-essential structures audit, domain restructuring plan, workspace strategy, cost impact (2026-05-11).
- `references/hermes-migration-execution-log.md` — Actual Phase 0/1/2 execution results: 249 skills removed, 5 new profiles created, smoke test results, profile config trap documented (2026-05-11).
- `references/profile-creation-template.md` — Step-by-step template for creating kanban worker profiles: SOUL.md, config.yaml (correct format), model routing table, verification steps (2026-05-11).
- `references/memory-bridge-pattern.md` — Pattern for injecting memory into kanban tasks since workers can't access the memory tool. Commander-side memory operations before task creation and after completion (2026-05-11).
- `references/knowledge-injection-protocol.md` — Mandatory worker startup protocol: graph_search + lessons + SOUL.md loading. Fixes the gap where 132K knowledge graph nodes are never consumed (2026-05-11).
- `references/hindsight-audit.md` — Hindsight plugin daemon is completely broken (never started). Built-in memory tool still works. hindsight_* MCP tools unavailable. hindsight-health-check cron should be paused (2026-05-11).
- `references/role-chain-kanban-replacement.md` — How kanban native features replace role_chain.py, quality_score.py, and pipeline_checkpoint.py. Scripts that become obsolete vs. scripts that stay (2026-05-11).
- `references/multi-agent-patterns-2026.md` — Condensed research from 5 core articles + 10 search directions on multi-agent patterns that survived production: agent-flow, orchestrator-worker, self-improvement (HyperAgents), skill architecture (arXiv:2602.12430), cascade failures, reliability math (2026-05-11).
- `references/domain-audit-2026-05.md` — 9-worker capability assessment matrix (functionality/autonomy/extensibility scores), P0-P2 priority roadmap, EC domain decision points (2026-05-11).
- `scripts/lock_profile_skills.py` — Clean + chmod 555 lock a profile's skills/ dir to prevent auto-rebundle. Run `python3 lock_profile_skills.py --all` after profile creation. Use `--verify` for read-only check (2026-05-11).
