# Context Slimming Results (2026-05-07)

## SOUL.md Compression

**Before**: 122 lines / 5,209 bytes
**After**: 70 lines / 2,945 bytes → **43% reduction**

### What was removed

| Section | Before | After | Reasoning |
|:--|:--|:--|:--|
| 正确做法（示例） | 42 lines, 5 scenarios | 0 lines (removed) | Already encoded in 核心规则 + 调度模式速查 |
| 错误做法（禁止） | 10 lines | 0 lines (merged) | Merged into 禁止 section + core rules |
| Superpowers 集成 | 11 lines | 1 line | Condensed: "主代理仅用3治理技能" |
| 可调度资源 | 9 lines | 9 lines | Kept (essential reference) |
| 工具边界 | 8 lines | 8 lines | Kept (essential reference) |
| 核心规则 | 28 lines | 26 lines | Updated with lesson_inject [1.5] step |

### What was preserved

- **调度模式速查表**: 6 scenarios in table format (fast lookup)
- **禁止列表**: 3 items
- **可调度资源表**: 6 domains with model assignments
- **工具边界表**: What main agent can/cannot do
- **MCP 安全闸门**: Critical security rule
- **5 核心规则**: Updated pipeline, Superpowers, delegate spec, fault handling, reporting

### Technique

1. **Scan for verbose examples** of rules already stated elsewhere → remove
2. **Convert long-form text to tables** where structure allows
3. **Merge duplicated concepts** from multiple sections into one
4. **Keep only the quick-reference version** — the long explanation belongs in skills

### Token Savings

- ~1,800 tokens/turn for SOUL.md injection
- 50-100 turns/day × $0.00028/1K tokens (flash) = $0.50-1.00/month
- Indirect: shorter context → marginally shorter responses

### Same technique applies to

- Memory entries (currently 5,891/6,000 chars → target 4,000)
- User profile (currently 2,908/4,000 → target 2,200)
- Domain SOUL.md files (writing-domain SOUL.md is ~180 lines)
