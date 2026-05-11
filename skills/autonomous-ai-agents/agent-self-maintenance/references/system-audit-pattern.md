# System Audit Pattern (2026-05-10)

## Trigger
User says "审查下所有发现过又没有修复的问题" or "自查" or questions system reliability.

## What to audit (comprehensive, not just health)

| Layer | Check | Method |
|:--|:--|:--|
| **Lessons** | Stale lessons (code deleted, issue fixed) | grep for "待修复\|TODO\|FIXME" across all lessons/*.md |
| **Config** | SOUL.md ↔ config.yaml ↔ memory contradictions | Diff model/provider settings across all 3 sources |
| **task_tracker** | Stale items, false alarms, items marked "等待决策" >3 days | Read task_tracker.json, verify each "pipeline验证失败" |
| **Cron** | Error status, script existence, dependency chain intact | cronjob list → check last_status + script files exist |
| **Skills** | Referenced scripts exist, no dead references | skill-auditor or manual check of scripts/ paths in skills |
| **Memory** | Contradictions with SOUL.md or config | Compare key settings (model, provider, paths) |
| **Errors.log** | Recurring patterns (not just one-off noise) | grep last 48h, cluster by message, count frequency |

## Pattern discovered 2026-05-10

This audit found:
- 1 SOUL.md↔memory model contradiction (flash vs v4-pro)
- 1 stale lesson (prefetch_capflow — code deleted, lesson remained)
- 3 false alarms in task_tracker (SEO script "不存在" but exists at 42KB)
- 4 cron errors needing diagnosis
- Self-review cron depth gap (only checks health, not consistency)

## Fix principle
L1/L2 issues found in audit → fix immediately, don't list and wait.
L3 issues → brief summary for user decision.

This pattern should be embedded in auto_review.py (cron 48e31b9eff71) to catch issues proactively rather than waiting for user to ask.
