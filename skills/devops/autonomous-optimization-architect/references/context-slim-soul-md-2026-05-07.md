# SOUL.md Context Slimming — Real Results (2026-05-07)

## Before

```
122 lines, 5,209 bytes
```

Structure:
- 正确做法示例: 42 lines (5 delegation examples, verbose)
- 错误做法禁止: 10 lines (3 anti-patterns)
- 可调度资源: 10 lines (domain table)
- 工具边界: 8 lines (tool boundary table)
- Superpowers集成: 11 lines
- 核心规则: 28 lines (actual rules)

## After

```
70 lines, 2,945 bytes (-43%)
```

What was removed:
- 5 verbose delegation examples → condensed into "调度模式速查" table (6 rows)
- 3 anti-pattern examples → condensed into "禁止" section (3 lines)
- Superpowers section merged into 核心规则 #2
- No content lost — all rules preserved in compressed form

## Token Savings

At ~0.25 tokens/char (Chinese), ~4 chars/token (English):
- Before: ~1,300 tokens injected per turn
- After: ~740 tokens injected per turn
- Savings: ~560 tokens/turn

For 50-100 turns/day: ~28,000-56,000 tokens/day saved.
At DeepSeek flash pricing ($0.28/M input): ~$0.008-0.016/day → ~$0.25-0.50/month.

## Methodology

Pattern: Find sections that say the same thing in multiple ways. 
- Examples + rules = pick one (rules, add compact examples)
- Tables = OK (dense information)
- Verbose narratives = compress to bullet points
- Section headers that are purely organizational = merge into parent

## Next Targets

1. MEMORY: 5,891/6,000 chars (98%) — consolidate related entries
2. USER PROFILE: ~2,900/4,000 — merge duplicate preferences
3. Domain SOUL.md files: audit for redundancy
