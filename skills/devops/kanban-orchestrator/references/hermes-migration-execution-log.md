# Kanban Migration Execution Log — 2026-05-11

## Phase 0: Cleanup

- 249 redundant bundled skills removed from 6 domain profiles (45-65→1 each)
- Profile configs already clean (model + delegation only)
- Domain-specific skills live in `~/.hermes/skills/`, shared across profiles

## Phase 1: Worker Creation

5 new profiles created: ec-sourcing (flash), ec-listing (flash), ec-fulfillment (pro), writer (pro), reviewer (pro).
4 domain profiles kept unchanged: code-domain, finance-domain, ops-domain, research-domain.
2 archived: ec-domain, writing-domain → `.archived/`.

### Verifications
- writer smoke test: 26s, `kanban_complete(summary='ok')` ✓
- EC Stage 1: 17网选品8款商品24MB下载成功 ✓
- EC dependency chain: Stage1 done → Stage2 auto-promoted ✓
- Writing chain: writer → reviewer, reviewer rejected with CRITICAL findings → auto-created fix task ✓

### Pitfalls Hit

1. **dir: workspace_kind rejected**: Kernel rejects `dir:/path`. Only `scratch` works.
   Fix: use `scratch` + cd in task body.

2. **First dispatch auto-rebundle**: Worker spawn triggers re-bundle of 80+ skills.
   Fix: `chmod 555` on skills/ and skills/devops/ after cleaning.

3. **Config format**: Must use `model.default` not `model.model`.
   Wrong: `model: {model: deepseek-v4-flash}`
   Right: `model: {default: deepseek-v4-flash, provider: deepseek, base_url: ...}`

4. **Gateway auto-discovers profiles**: No restart needed for new profile dirs.

## Phase 2: Cron Migration

- 周度自优化 cron → kanban v3.0 (creates 3 parallel audit tasks)
- Writing pipeline cron created (15:35 Mon-Fri, kanban)
- Kanban health check cron (hourly, reclaims blocked tasks)

## Phase 3: Legacy Removal

17 obsolete scripts removed: enforce_delegate.py, role_chain.py, quality_score.py, pipeline_checkpoint.py, checkpoint_save.py, auto_review.py, archive_learning.py, profile_observe.py, 9 pipeline_stage_* scripts.

3 conflicting crons removed: auto-daily-review, 每日复盘草稿箱, writing-health-check.

SOUL.md rewritten for kanban architecture. MEMORY.md compressed from 6203→2428 chars.

## Optimization

- 7凌晨 knowledge maintenance tasks merged into 1 (`夜间知识整理` at 03:00). Cron 5896e6bcea04 converted to no_agent script to avoid 15:30 conflict with writing kanban. Hindsight container + cron fully removed (788MB freed).

## Phase 3: Knowledge Pipeline Fix

- `lesson_graph_bridge.py` had no cron trigger since creation — lessons never synced to graphify nodes
- Fixed: integrated into 夜间知识整理 Step 4
- Knowledge flow now complete: session → lesson_inject → lessons/ → lesson_graph_bridge → graphify → graph_search recall
- 15:30 conflict resolved: data collection → no_agent script, kanban writing → 15:35
- circuit-guard: hourly → every 2h
- skill-learnings-sync: LLM → no_agent script

## Final State

40 crons (16 LLM + 24 script). 9 active worker profiles. Kanban dispatcher via gateway.
