# Hermes System: delegate_task → Kanban Migration Analysis

Date: 2026-05-11

## Architecture Decision

**Target**: Pure kanban router mode. The commander (Hermes Agent) only uses kanban tools (kanban_create/show/comment/block). delegate_task is removed from the commander's toolset and becomes internal to kanban workers only.

```
旧：commander → delegate_task → domain agent → return
新：commander → kanban_create → dispatcher → worker(delegate_task inside) → kanban_complete → commander reads
```

## Non-Essential Structures Identified

### 1. Domain Profile Bundled Skills (30+ unused directories)
Each domain profile bundles identical unused skills: himalaya, google-workspace, linear, codex, hermes-agent, kanban-worker, kanban-orchestrator. Writing-domain additionally bundles touchdesigner-mcp (20+ files) and pretext.

### 2. Config Bloat
TTS providers (6 backends), STT, voice recording, human_delay, approvals, personalities, quick_commands, hooks — all template config, never used.

### 3. Redundant MCP Agents
mcp-hermes-delegate and mcp-hermes-cron duplicate existing delegate_task and cronjob tool functionality.

### 4. Scripts Replaceable by Kanban
- role_chain.py → kanban dependency graph
- quality_score.py → reviewer worker metadata
- pipeline_checkpoint.py → kanban SQLite persistence

## Domain Restructuring

| Original (6) | Kanban Workers (8) | Change |
|:--|:--|:--|
| ec-domain | ec-sourcing + ec-listing + ec-fulfillment | Split 1→3 |
| writing-domain | writer + reviewer | Split 1→2 |
| finance-domain | finance | Unchanged |
| code-domain | code | Unchanged |
| ops-domain | ops | Unchanged |
| research-domain | researcher | Unchanged |

## Workspace Strategy

| Worker | Workspace | Reason |
|:--|:--|:--|
| ec-sourcing | dir:~/PDD | Downloads shared with listing |
| ec-listing | dir:~/PDD | Reads sourcing output |
| ec-fulfillment | dir:~/PDD | Reads listing results |
| research | scratch | Results via kanban_complete metadata |
| finance | dir:~/quant | Factor results consumed by cron scripts |
| writer | dir:~/writing-data | Articles for publish pipeline |
| reviewer | scratch | Read-only, findings via metadata |
| code | scratch or worktree | Task-dependent |
| ops | dir: per task | Task-dependent |

## Cross-worker data passing

Two mechanisms:
1. **File sharing** (dir workspace): For large data (images, datasets)
2. **kanban_complete metadata**: For structured results (status, summary, key metrics)

## Cost Impact

Estimated daily: ¥40 → ¥55-70. Increase from:
- Worker startup system prompt: ~5K tokens/worker ($0.01)
- More workers per task (1→3-5)
Offset by:
- flash model for mechanical workers (ec-listing/fulfillment/ops) saves ¥10-15/day

## Migration Phases

**Phase 0**: Cleanup — remove bundled skill bloat, config bloat, redundant MCP agents
**Phase 1**: Infrastructure — start dispatcher, create worker profiles, test on non-critical task
**Phase 2**: Pipeline migration — ec 3-stage first (best fit), then content Role Chain, then quant signals
**Phase 3**: Cron job conversion — only LLM-using crons, script-only crons stay unchanged
