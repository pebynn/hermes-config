# Role Chain → Kanban Native Replacement

Date: 2026-05-11

## What Role Chain Does (subagent-delegation-protocol v3.0)

The Role Chain mechanism enforces a quality pipeline via software-layer scripts:

```
Researcher → Creator → Reviewer → Synthesizer
                ↑
         role_chain.py defines chain + blocker points
         quality_score.py scores output → triggers reviewer on FAIL
         pipeline_checkpoint.py saves/resumes pipeline state
```

## Why Replace It

1. **role_chain.py injects role constraints via text** — same domain agent gets different prompts per role. Fragile.
2. **quality_score.py is an extra LLM call** — scores output text, then decides whether to invoke reviewer. Redundant when reviewer is a dedicated worker.
3. **pipeline_checkpoint.py persists state to files** — redundant when kanban tasks are natively persisted in SQLite.

## Kanban Native Replacement

Each role becomes a dedicated kanban worker with its own profile, tools, and constraints:

```
Researcher worker (research-domain, tools: web+browser+file)
    ↓ (kanban dependency: parent→child)
Creator worker (writing-domain, tools: terminal+file+web)
    ↓
Reviewer worker (reviewer profile, tools: file+web, read-only)
    ↓
Synthesizer worker (ops-domain, tools: terminal+file)
```

### Chain definition → kanban dependency graph
```
T1 = kanban_create("research: 市场数据", assignee="research", parents=[])
T2 = kanban_create("write: 复盘文章", assignee="writer", parents=[T1])
T3 = kanban_create("review: 质量审查", assignee="reviewer", parents=[T2])
T4 = kanban_create("publish: 发布", assignee="ops", parents=[T3])

# T3 reviewer FAIL → T4 auto-blocked by dependency engine
# No script needed to enforce this
```

### Role constraints → dedicated worker profiles
```
reviewer worker system prompt:
  "你只审查不修改。对照 data_guard 门禁审查。输出结构化 findings。"
  tools: [file, web]  # read-only, no terminal write
  
writer worker system prompt:
  "基于上游数据创作。不自采数据。遵守 data_guard 数据规则。"
  tools: [terminal, file, web]
```

### Quality gate → reviewer worker kanban_block
```
Old: quality_score.py scores → <70 → triggers reviewer
New: reviewer worker reads output → finds issues → kanban_block("3处数据错误需要修复")
     → dispatcher: T4(publish) stays blocked
     → operator reviews and creates fix task
```

## Scripts Made Obsolete

| Script | Kanban Replacement |
|:--|:--|
| role_chain.py | kanban dependency graph + dedicated worker profiles |
| quality_score.py | reviewer worker's complete metadata |
| pipeline_checkpoint.py | kanban SQLite task persistence |
| enforce_delegate.py (delegation checks) | kanban-orchestrator skill conventions |
| pipeline_health_check_wrapper.py | reviewer worker periodic health scan |
| publish_audit_guard.py (Colors class) | reviewer worker审查逻辑 |

## Scripts That Stay

| Script | Why |
|:--|:--|
| data_guard.py | Data quality gates, called by workers internally |
| auto_review.py v2 | Cross-domain system audit, non-LLM |
| rule_audit.py | SOUL compliance scanning |
| drift_detect.py | Function signature consistency |
| cost-tracker / cost-circuit-breaker | Cost management |
| lesson_inject.py | Lesson extraction |
| notify.py | QQ Bot notifications |
| 30+ no_agent script crons | Pure script, no LLM needed |
