# Superpowers Enforcement Pattern — From Text Rules to Hard Constraints

*Captured 2026-05-11 from code-domain audit + fix session*

## Problem

`code-domain` SOUL.md defined a 7-step superpowers workflow (brainstorming → writing-plans → TDD → code → debugging → code-review → verification). But audit revealed:

1. `~/.hermes/plans/` completely empty — `writing-plans` step never produced a plan file
2. No brainstorming intermediate artifacts
3. Worker was rushed by timeout reclaims (2 reclaims before success)
4. Text rules in SOUL.md were silently skipped

## Root Cause

Text-only behavioral constraints are unreliable. The agent will skip "suggested" workflow steps under time pressure, especially after reclaim/retry cycles.

## Solution: Three-Part Hardening

### Part 1: Mandatory Product Requirements

Each superpower step must produce a tangible file artifact:

```markdown
### 强制产物要求
- **writing-plans**: 必须产出 `~/.hermes/plans/<task_id>.md`，无此文件不得进入第4步编码
- **brainstorming**: 设计结论写入plan文件的设计方案节，至少包含"方案选择+替代方案+风险"
- **verification-before-completion**: 必须实际运行测试/验证命令，不得仅凭代码检查声称"已验证"
```

### Part 2: Self-Check Checklist

Each step has a concrete, verifiable completion criterion:

```markdown
### 7步自检（每步完成后必须确认，不得跳过）
1. ✅ brainstorming完成 → plan文件已有"设计方案"节
2. ✅ writing-plans完成 → plan文件存在且≥100行
3. ✅ TDD完成 → 测试用例已写且至少1个RED
4. ✅ 编码完成 → 测试从RED→GREEN
5. ✅ debugging完成 → 无遗留ERROR/WARNING
6. ✅ code-review完成 → 自审通过，无P0问题
7. ✅ verification完成 → 实际运行验证通过

**任一自检未通过 → 回退到上一步，不得继续。**
```

### Part 3: Model Upgrade

The original `glm-5.1` model had poor instruction following and 15+ minute cold starts causing reclaims. Switched to `deepseek-v4-pro` which:
- Starts in ~6 minutes vs 15+
- Better instruction following (essential for superpowers compliance)
- Costs ~2x but eliminates reclaim waste

## Pattern Applicability

This hardening pattern is reusable across any worker with a defined workflow:

| Worker | Workflow | Hardening Needed |
|:--|:--|:--|
| code-domain | 7-step superpowers | ✅ Applied (2026-05-11) |
| writer | AI→avoid-ai-writing→audit_guard→publish | Could benefit from artifact requirements |
| reviewer | 7-step review-checklist | Already has checklist (2026-05-11) |
| ops-domain | diagnose→fix→verify | Could benefit from verification artifacts |

## Key Lesson

Text rules saying "you must do X" will not enforce X under pressure.
**The only reliable enforcement is a tangible, verifiable artifact that must exist before proceeding.**
