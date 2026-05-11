# Hindsight Plugin — Audit & Removal (2026-05-11)

## Audit (2026-05-10)
- Container running 41h but embed module corrupted: 0 functionality, 788MB memory consumed
- `hindsight_*` MCP tools unavailable (retain/recall/reflect all fail)
- `hindsight-health-check` cron running every 30min — pure waste

## Removal (2026-05-11)
- Container stopped: `docker stop hindsight && docker rm hindsight`
- Cron removed: `8832a6b1df66` (hindsight-health-check)
- Directory removed: `~/.hermes/hindsight/`
- 788MB memory freed

## Impact: NONE
- Memory tool already provides durable fact storage (system-injected every turn)
- session_search provides cross-session recall
- graphify provides knowledge graph (65K nodes)
- lesson_graph_bridge.py syncs lessons→graph nodes (reconnected via 夜间知识整理 cron)

## Current knowledge recall stack
```
MEMORY.md (system inject) → durable facts
session_search → cross-session transcripts
graph_search → knowledge graph nodes (65K)
lessons/ → domain-specific pitfalls
```
