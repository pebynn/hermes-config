# Memory Bridge Pattern for Kanban Architecture

Date: 2026-05-11

## Problem

Kanban workers (both orchestrator and leaf) **cannot access the memory tool**. This is enforced by the kanban system:

- `kanban-orchestrator`: "orchestrators cannot use clarify, memory, send_message, or execute_code"
- `kanban-worker`: "leaf subagents cannot call memory"

Additionally, Hindsight (hindsight_retain/recall/reflect MCP tools) is broken — the daemon has never successfully started (see `references/hindsight-audit.md`).

The built-in `memory` tool (separate from Hindsight) still works. Only the commander/router can use it.

## Solution: Commander-Side Memory Bridge

All memory operations happen at the commander layer, before task creation and after task completion.

### Before kanban_create: Inject background knowledge

```
1. Search memory for relevant facts about the task domain
2. Extract key facts: user preferences, past outcomes, known pitfalls, data rules
3. Inject into kanban_create body as a [背景知识] block:

"""
[背景知识]
- 用户偏好: 极简沟通，直接给结果不解释过程
- 上次此任务: 2026-05-08，产出在 ~/PDD/商品/2026-05-08/listing-ready/
- 已知问题: 17网验证码偶发触发 → Selenium备选方案
- 数据铁律: 所有数字来自API原始值，禁止自行计算涨跌幅/涨跌家数
- 成本: ¥40/天，v4-pro主模型，flash做简单任务
"""
```

### After kanban worker completes: Extract and persist learnings

```
1. kanban_show(task_id) → read complete metadata
2. Extract:
   - decisions made (changed_files, key parameters)
   - lessons learned (errors encountered, workarounds discovered)
   - cross-domain implications (does this affect other domains?)
3. memory(action=add, content=...) → persist to built-in memory store
4. Update relevant cron job state or task tracker
```

### Example workflow

```
# Create task with memory injection
relevant_memories = [
  "用户偏好极简沟通",
  "上次选品产出在 ~/PDD/商品/2026-05-08/",
  "17网反爬：单IP >15min封禁"
]

kanban_create(
  title="sourcing: 中老年女装选品",
  assignee="ec-sourcing",
  parents=[],
  body=f"""
  [背景知识]
  {chr(10).join(f"- {m}" for m in relevant_memories)}
  
  [任务]
  从17网选品8件中老年女装...
  [产出目录]
  ~/PDD/商品/{{today}}/listing-ready/
  """
)

# After completion, persist learnings
result = kanban_show(task_id)
if result["outcome"] == "completed":
    metadata = result["metadata"]
    memory(action="add", content=f"ec-sourcing完成: {metadata.get('products')}件, 产出{metadata.get('output_dir')}")
    if metadata.get("lessons_learned"):
        memory(action="add", content=f"ec-sourcing教训: {metadata['lessons_learned']}")
```

## Why This Matters

Without the memory bridge:
- Each kanban worker starts with zero context about past sessions
- Known pitfalls are repeated because workers can't read lessons
- User preferences are lost (each worker is a fresh session)
- Knowledge gained during task execution is lost (no memory tool to persist)

With the memory bridge:
- Workers get targeted background knowledge via the body field
- Commander aggregates learnings across workers
- Built-in memory tool serves as the single source of cross-session truth
