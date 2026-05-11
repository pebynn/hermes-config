# Knowledge Pipeline Architecture — post-kanban (2026-05-11)

## Flow
```
session ──→ error-learner(22:00) ──→ lesson_inject.py ──→ lessons/{domain}.md
    │                                                           │
    └──→ 夜间知识整理(03:00) ──→ Step 3: lessons→global.md      │
         (6步合并)               Step 4: lesson_graph_bridge.py─┘
                                 Step 5: new workflow→skill固化
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
              graphify-daily       skill-learnings(04:00)  wiki-soul(04:20)
              知识图谱索引          learnings→brain          SOUL→wiki
                    │
                    ▼
              总指挥 graph_search ← 分析任务context注入
```

## Layers
| Layer | Tool | Status |
|:--|:--|:--|
| Durable facts | MEMORY.md (system inject) | ✓ 2428 chars |
| User profile | USER.md | ✓ 1558 chars |
| Cross-session | session_search | ✓ |
| Knowledge graph | graphify 65K nodes | ✓ daily + lesson bridge |
| Domain pitfalls | lessons/ 7域 | ✓ error-learner injects |
| Skill patterns | skills/ SKILL.md | ✓ 夜间Step5 auto-detect |

## Dead components removed
- `enforce_delegate.py` → replaced by kanban routing
- `role_chain.py` → replaced by kanban dependency graph + reviewer worker
- `quality_score.py` → replaced by reviewer worker metadata
- `auto_review.py` → replaced by reviewer worker
- Hindsight → container broken, 0 functionality, 788MB freed

## Cron architecture (post-consolidation)
- 40 total (16 LLM + 24 script), down from 47
- 7凌晨 tasks → 1 夜间知识整理
- circuit-guard: hourly → every 2h
- 15:30 conflict resolved: data collection → no_agent script