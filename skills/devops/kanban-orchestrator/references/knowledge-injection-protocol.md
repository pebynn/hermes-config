# Knowledge Injection Protocol for Kanban Workers

Date: 2026-05-11 | Updated: 2026-05-11 (batch execution results)

## Problem

Kanban workers start as fresh sessions with no context about the user's system. They don't know:
- What knowledge exists in graphify (134K nodes, 295K edges)
- What lessons have been learned in the domain (lessons/*.md)
- What the domain's rules and constraints are (SOUL.md)
- Cross-domain implications of their task

Without knowledge injection, workers operate blind — repeating mistakes that could have been avoided.

## Solution: SOUL.md Startup Protocol Injection

Inject a mandatory `## 🚀 Startup Protocol` section into each worker's SOUL.md, placed before `## 核心能力` (or equivalent capability section). The protocol loads graph knowledge + domain lessons before ANY task.

### Template

```markdown
## 🚀 Startup Protocol (MANDATORY — injected 2026-05-11)

Before ANY task execution, load domain knowledge:

1. **Graph Knowledge**: `graph_search("{query}")` — query the 134K-node knowledge graph
2. **Domain Lessons**: `read_file("~/.hermes/lessons/{lesson_file}")` — load accumulated lessons learned
3. **This SOUL.md** is already in your context — re-read if uncertain about constraints

⏱️ Budget: ~30s startup overhead. Skip only if task body explicitly says "no_startup".
```

### Domain Mapping

| Profile | graph_search query | lessons file | SOUL.md anchor line (for patch) |
|:--|:--|:--|:--|
| finance-domain | `lesson:finance` | lessons/finance-domain.md | `## 核心能力` |
| code-domain | `lesson:code` | lessons/code-domain.md | `## Superpowers 纪律` |
| ops-domain | `lesson:ops` | lessons/ops-domain.md | `**资深 DevOps/SRE` |
| research-domain | `lesson:research` | lessons/research-domain.md | `## 核心能力` |
| writer | `lesson:writing` | lessons/writing-domain.md | `## 核心能力` |
| reviewer | `lesson:writing` | lessons/writing-domain.md | `## 核心能力` |
| ec-sourcing | `lesson:ec` | lessons/ec-domain.md | `## 核心能力` |
| ec-listing | `lesson:ec` | lessons/ec-domain.md | `## 核心能力` |
| ec-fulfillment | `lesson:ec` | lessons/ec-domain.md | `## 核心能力` |

### Batch Injection Technique

Use `execute_code` to batch-patch all 9 SOUL.md files in one operation:

```python
# Pseudocode — actual implementation in kanban-orchestrator SKILL.md
for name, cfg in profiles.items():
    content = read_file(cfg["path"])
    # Find anchor line, insert startup block before it
    patch(path=cfg["path"], old_string=anchor_line, new_string=startup_block + "\n" + anchor_line)
```

Key details:
- Use a known unique anchor line in each file (e.g. `## 核心能力`) so `patch()` has a unique match
- Check if already injected (search for "Startup Protocol" in content) before patching
- EC workers (sourcing/listing/fulfillment) all share `ec-domain.md` lessons
- Writer and reviewer both use `writing-domain.md` lessons

### Execution Results (2026-05-11)

- ✅ 9/9 profiles injected successfully (0 failed, 0 skipped)
- ⏱️ Execution time: ~22s (18 tool calls: 9 reads + 9 patches)
- 📁 All profiles verified via `read_file` post-injection

## Why This Matters

- **Without injection**: Worker repeats known mistakes (pitfalls are in lessons but worker doesn't read them)
- **Without injection**: Worker misses cross-domain implications (e.g., writing-domain data rules apply to finance-domain too)
- **Without injection**: 134K knowledge graph nodes are dead data, never consumed
- **With injection**: ~30s startup cost per dispatch, ≈0 cost in tokens (graph_search is local/small)
