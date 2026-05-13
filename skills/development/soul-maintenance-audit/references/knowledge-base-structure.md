# Knowledge Base Directory Structure

> Added 2026-05-13: New 6th layer in the Hermes knowledge ecosystem (alongside MEMORY, SOUL, Graph, Wiki, Lessons).

## Location

```
~/.hermes/knowledge/
├── index.md                # Directory index with cross-references
├── decisions/              # Key architectural decisions
│   └── YYYY-MM-DD-title.md # Decision + rationale + cost + follow-up
├── evolution/              # System evolution timeline
│   └── title.md            # Phase timeline + core lessons
└── patterns/               # Recurring failure patterns
    └── title.md            # Characteristics + instances + root cause + fix
```

## Entry Template: decisions/ (expanded, proven 2026-05-14)

For termination-level (🔴) decisions, the expanded structure below captures more actionable detail than the minimal template:

```markdown
# D###: Title

**Date**: YYYY-MM-DD
**Level**: 🔴/🟠/🟡
**Decision-maker**: user-requested / auto-audit / evolution audit

## Problem Discovery
[What was observed, concrete metrics/numbers]

## Impact
[Who/what is affected, scope, severity]

## Root Cause Analysis (for termination decisions)
[Numbered causes, causal chain]

## Decision
[What was decided, clear action verb]

## Rationale
[Numbered reasons, trade-offs considered]

## Follow-up
[Concrete action items, links to patterns/lessons]

## Related
- [D###](../decisions/...)
- [P###](../patterns/...)
- Dead paths: [list if applicable]
```

Example: D004 (2026-05-13-pead-strategy-unreachable.md) followed this structure with concrete metrics (年化-12.67%, 胜率0%, 6笔全败).

## Entry Template: patterns/ (expanded, proven 2026-05-14)

```markdown
# P###: Pattern Name

**Occurrences**: N
**Cross-domain**: domain1, domain2
**First discovered**: YYYY-MM-DD
**Severity**: 🔴/🟠/🟡

## Characteristics
1. Observable signal 1
2. Observable signal 2

## Instances
### Instance 1: Title (YYYY-MM)
- **Stage/context**: ...
- **Root cause**: ...
- **Impact/consequence**: ...
- **Resolution**: ...

### Instance 2: Title (YYYY-MM)
...

## Root Cause
[Why it happens — systemic cause, not per-instance symptom]

## Fix / Prevention
1. **Detection**: [how to catch it before damage]
2. **Gate**: [where to insert the check in the pipeline]
3. **Repair**: [how to fix when already occurred]

## Cross-Domain Applicability
- **domain1** (primary): [how it manifests]
- **domain2**: [how it manifests]
- **domain3**: [how it manifests]

## Related
- [D###](../decisions/...)
- [lessons file](~/.hermes/lessons/...)
- Dead paths: [if applicable]
```

## Entry Template: evolution/

```markdown
# E###: Title

**Time span**: YYYY-MM → YYYY-MM
**Last updated**: YYYY-MM-DD

## Phase 1: Name (dates)
- Key events
- Lessons learned

## Phase 2: Name (dates)
...

## Core Lessons Table
| # | Lesson | Phase |
|--:|:--|:--|

## Current Architecture
[ASCII diagram]
```

## index.md Template

```markdown
# Hermes Knowledge Base Index

> Last updated: YYYY-MM-DD HH:MM CST
> Source: all domain lessons + session audits + decision records

## Directory Structure
[Table with dir/purpose/count]

## Architecture Decisions
[Table: ID/Date/Title/Level]

## Recurring Failure Patterns
[Table: ID/Pattern/Occurrences/Cross-domain]

## System Evolution
[Table: ID/Title/Time span]

## Related Resources
- Lessons: ~/.hermes/lessons/ (N domains + N daily audits)
- Graphify: MCP graphify (N nodes synced)
- SOUL.md: ~/.hermes/SOUL.md
```

## Audit Checklist

When auditing the knowledge layer:

| Check | What to look for | Fix |
|:------|:-----------------|:----|
| Index freshness | index.md counts vs actual file counts | Update index |
| Orphan entries | .md files not listed in index.md | Add to index |
| Dead links | Cross-references to deleted decisions/patterns | Remove or update |
| Pattern → Decision linkage | Patterns without related decision links | Add cross-refs |
| Lesson sync | CRITICAL lessons in lessons/ not reflected in knowledge/ | Create decision/pattern entry |
| Graphify sync | knowledge/ entries not in graph.json | Run lessons_to_graphify_sync.py |
| Stale entries | >30 days since last update, no new instances | Consider archiving |

## Graphify Sync Pitfall

The `lessons_to_graphify_sync.py` script directly parses `graph.json`. Common failure modes:

1. **JSON parse error**: `JSONDecodeError at line N` — graph.json tail corrupted. Fix: `python3 -c "import json; json.load(open('graph.json'))"` to isolate, then regenerate from source data.
2. **Timeout**: Large graphs (200K+ nodes) may approach timeout. Current observation (2026-05-14): 204K nodes / 373K edges processed successfully within 120s. If this degrades, consider dedicated cron `e07573d46f12` for graphify-sync only.
3. **Dry-run first**: Always `--dry-run` before live sync to catch parse errors without mutating graph.

## Cron Automation

The daily knowledge management pipeline runs as a cron job (凌晨03:00) with this workflow:
1. Memory 整理 → check usage, record decisions/lessons
2. Knowledge 结构化 → scan lessons/, create D/P/E entries, update index.md
3. Lessons 同步 → extract structured knowledge from new lessons
4. Graphify 注入 → `python3 ~/.hermes/scripts/lessons_to_graphify_sync.py`
5. 输出简报 → summary of new/updated entries

The agent prompt for this cron is the canonical definition of the knowledge management workflow.

## Cross-References

- `lessons_to_graphify_sync.py` — syncs lessons/ → graph.json
- `soul-maintenance-audit` — parent skill, v2.1 adds this as 6th layer
- `index.md` — living directory index
