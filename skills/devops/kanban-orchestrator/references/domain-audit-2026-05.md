# Hermes Domain Capability Audit — 2026-05-11

9-worker assessment under kanban architecture. Scores: Functionality / Autonomy / Extensibility (1-10).

## Score Matrix

| Worker | Func | Auto | Ext | Model | Status |
|:--|:--|:--|:--|:--|:--|
| code-domain | 7 | 5 | 8 | glm-5.1 | Active |
| ops-domain | 6 | 7 | 6 | v4-flash | Active |
| research-domain | 5 | 4 | 9 | v4-pro | Underused |
| finance-domain | 8 | 7 | 6 | v4-pro | Most mature |
| writer | 7 | 5 | 8 | v4-pro | Active pipeline |
| reviewer | 6 | 5 | 7 | v4-pro | Active pipeline |
| ec-sourcing | 3 | 2 | 5 | v4-flash | Frozen |
| ec-listing | 3 | 2 | 4 | v4-flash | Frozen |
| ec-fulfillment | 3 | 3 | 6 | v4-pro | Frozen |

## Priority Roadmap

### P0 — Autonomy Foundation (this week)
1. Knowledge injection protocol: all 9 workers load graph_search + lessons on startup
2. Error learning loop: kanban failures → error-learner → lessons → graphify
3. Hub de-fragilization: prompt-optimizer.infer_domain before kanban_create

### P1 — Domain Upgrades (this month)
4. Finance pipeline: data→factors→signals→push, 4-stage kanban
5. Code+reviewer auto-fix loop: review→fix→verify→merge
6. Research→graphify auto-pipe

### P2 — Extensibility (quarterly)
7. Self-evolution experiment (finance factor weights)
8. Cross-domain data bus v2
9. Worker startup time optimization

## EC Decision Points
- EC domain frozen, lowest capability scores
- Options: A) keep frozen B) architectural upgrade now C) merge to single worker
- Decision pending

## Immediate L1 Actions (no confirmation needed)
1. Patch 9 worker SOUL.md with mandatory startup sequence
2. Commander prompt: add infer_domain pre-check
3. error-learner cron: add kanban event collection
