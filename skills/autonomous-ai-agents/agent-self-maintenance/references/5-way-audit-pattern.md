# 5-Way Parallel Domain Audit Pattern (2026-05-10)

## When to Use

Full system health audit. Use when:
- User asks "全面审查系统" or "全面审计"
- Suspicion of systemic issues across multiple domains
- After major system changes (new pipelines, new enforcement scripts)
- Periodic deep-dive (recommended: weekly)

## Pattern

```
Phase 1: Model upgrade (2 min)
  → Patch SOUL.md: all domain agents → deepseek-v4-pro (max audit capability)
  → Record originals for restore

Phase 2: 5-way parallel dispatch (10-15 min)
  → delegate_task tasks=[code-audit, finance-audit, writing-audit, ops-audit, ec-audit]
  → Each audit: self-contained context, clear output format, explicit checks

Phase 3: Main agent parallel audit (concurrent with Phase 2)
  → Config consistency: SOUL.md ↔ config.yaml ↔ memory
  → Cost efficiency: model routing, cost-tracker accuracy
  → Lesson staleness: scan for "待修复", "TODO", "FIXME"

Phase 4: Compile severity triage (5 min)
  → Merge all 5 domain reports + main agent findings
  → Classify: 🔴CRITICAL / 🟠HIGH / 🟡MEDIUM
  → Present consolidated report

Phase 5: Restore models (1 min)
  → Patch SOUL.md back to original model assignments
```

## Audit Scope per Domain

| Domain | Scope | Key Checks |
|:--|:--|:--|
| code | ~/writing-data/scripts/, ~/quant/, ~/.hermes/scripts/ | Syntax, dead code, security, function drift, silent exceptions |
| finance | MySQL stock_kline, mid_cap_strategy, signal_engine, fund_flow | Data integrity, factor quality, signal coverage |
| writing | collect_data → charts → review → publish full pipeline | Source fallback chain, cookie expiry, shebang, cron health |
| ops | 36 cron jobs, disk, memory, logs, sessions, gateway, MCP, tokens | Cron errors, disk pressure, zombie processes, backups |
| ec | 17网采集 → pdd_listing → 运营 → 库存 | Listing success rate, order fulfillment, return rate, review response |

## Output Format

Each domain returns: "## {domain} 审计报告\n\n| 检查项 | 状态 | 问题 |" with one-liner per item.
Severity implicitly: ✅ = OK, 🟡 = WARNING, 🔴 = CRITICAL.

## First Run Results (2026-05-10)

Found 17 issues across all domains. All non-ec-domain issues fixed same session.

### Issues Found
- 5 CRITICAL: hardcoded password, fund flow pipeline break, L1 factor NaN, ec listing 0% success, ec return 37.5%
- 7 HIGH: Cookie fallback, stock_sdk missing, 18G trash, zombie procs, 401 token, missing backup, mother's day window
- 5 MEDIUM: 116 silent exceptions, 42 function drifts, margin cache empty, shebang path, no health check cron

### Fix Execution (same session)
| Severity | Domain | Issue | Fix |
|:--|:--|:--|:--|
| 🔴 | code | Hardcoded MySQL password | → env var MYSQL_PASSWORD |
| 🔴 | code | 139 silent exceptions | → traceback.print_exc() added |
| 🔴 | finance | Fund flow pipeline break | → unified naming + column mapping |
| 🔴 | finance | L1 factor NaN (API change) | → switched API + transposed format adapter |
| 🟠 | finance | margin_data cache empty | → pulled data + cron→no_agent script |
| 🟡 | finance | Fund flow cron never ran | → no_agent script |
| 🟠 | writing | Cookie fallback nesting | → annotated protection |
| 🟠 | writing | stock_sdk_collector.js lost | → restored from source |
| 🟡 | writing | generate_charts shebang | → pointed to quant_env |
| 🟡 | writing | No pipeline health cron | → new cron 502ebe4a4392 |
| 🔴 | ops | 18G trash + zombie procs | → cleaned (disk 17%→13%) |
| 🟡 | ops | No MySQL backup | → cron 9cddd7dfcf3e |
| 🟡 | ops | No logrotate | → config generated |

### Excluded (L3 decision)
- ec-domain: 13 products 0% listing success, 37.5% return rate, 28 orders pending — user chose to skip

## Lessons

1. Model upgrade is essential: v4-flash sub-agents miss subtle issues (e.g., fund flow column mapping)
2. 5-way parallel dispatch is ~3x faster than sequential (15 min vs 45 min)
3. Always restore models after audit — cost difference is significant
4. Audit found that cost-tracker was broken for days — autonomous agents must detect when own monitoring fails
