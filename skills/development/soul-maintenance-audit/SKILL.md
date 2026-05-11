---
name: soul-maintenance-audit
description: Periodic audit and optimization of all Hermes SOUL.md files, MEMORY, and USER PROFILE — check content quality, consistency, dead references, THEN apply trimming patterns to reduce verbosity and token costs.
version: 1.7.0
author: Hermes Community
allowed-tools:
  - read_file
  - patch
  - write_file
  - terminal
  - search_files
trigger:
  - user asks to "check/audit SOUL files" or "review profile docs"
  - after bulk skill installations or domain config changes
  - user comments about "wordy" or "verbose" profile docs
  - periodic maintenance (every 2-3 months)
execution: manual
---

# SOUL.md Content Maintenance Audit

## Class of Task

Periodic content quality review of all Hermes profile identity documents (SOUL.md files) AND the associated MEMORY/PROFILE stores. This is NOT about config drift (see `hermes-config-sync`) or technical health (see `self-diagnosis`). It's about the **written content** of identity documents — are they concise, consistent, free of dead references, and following a unified format?

**Cost motivation**: SOUL.md + MEMORY + USER PROFILE are injected into every turn. Trimming these files directly reduces per-turn token costs. See `autonomous-optimization-architect` skill for the full cost optimization workflow.

## Standard Format

All domain SOUL.md files should follow this structure:

```
Core Capabilities → Toolsets → Supporting Skills → Collaboration Rules → Communication Style
```

## Audit Checklist

### 1. Inventory

List all SOUL.md files:

```bash
ls -la ~/.hermes/SOUL.md
ls -la ~/.hermes/profiles/*/SOUL.md
```

### 2. Per-File Checks

For each SOUL.md file, check:

| Check | What to look for | Fix |
|:------|:-----------------|:----|
| Dead links | References to skills/directories that don't exist | Remove or update |
| Script path validity | Paths in `核心脚本` tables that don't resolve to real files (relative paths from profile dir often wrong) | Use absolute paths or verify relative resolves correctly |
| Count accuracy | Quantitative claims like "15个技能" — count the actual list and cross-check | Update the number or trim/add to match |
| Verbose basics | Linux commands (`apt`, `ps`, `df`), framework tutorials that subagents already know | Remove — trust the LLM's training data |
| Parameter details | Script argparse details duplicated from `--help` | Keep function + output path, drop parameter lists |
| Redundant boilerplate | Identical 7-line collaboration rules block across all files | Keep 3-line summary, point to main SOUL.md for detail |
| Ambiguous paths | `SOUL.md` (ambiguous — could mean main or profile) | Use `~/.hermes/SOUL.md` |
| Format drift | Missing sections, different ordering across files | Standardize to format above |

### 3. Common Redundancies to Remove

- **Basic command lists** (`apt install`, `systemctl start`, `ps aux`, `df -h`, `docker ps`, etc.) — These are LLM training data, not profile content
- **Per-script parameter tables** with `--pe-max`, `--roe-min` etc. — Keep function names and output paths, reference `--help`
- **ASCII art pipeline diagrams** spanning 10+ lines — Compress to one-liner
- **Identical collaboration rules** copied into every file — Single source of truth in main SOUL.md
- **Markdown template blocks** (e.g. 28-line plan output template) — Replace with 3-line structural reference
- **Git specs / project structure preferences** in domain profiles — Subagents don't do branching or scaffolding
- **Duplicate output specs** when paths are already listed in phase definitions — Merge into the phase, delete standalone section
- **Excessive supporting skill lists** (12+ skills with full descriptions) — Trim to 6 most relevant, remove verbose descriptions
- **Command examples with full syntax** (`nohup x > y 2>&1 &`) — Replace with "see X skill" reference

### 5b. Concrete Trimming Patterns (from 2026-05-01 optimization)

| Pattern | Before | After |
|:--------|:-------|:------|
| **Pipe char in markdown** | `\\|\\| 详情/路径` (parsed as table delimiter) | Use inline code `` `\\|\\| 详情/路径` `` or change to `- 详情/路径` |
| **MCP server list inline** | 14 server names + descriptions in SOUL.md | Delete entirely — config.yaml is the source of truth |
| **Triple-defined protocols** | Same rule in 强制规则#0 + 任务澄清协议 + 检查链第零关 | Keep one (检查链), reference from others |
| **Verbose domain boundary** | 6-line explanatory paragraph per domain | 1-line inline note next to domain table |
| **Action checklist 4-gate** | 47 lines with per-gate checkboxes and verbose questions | 20 lines with table + 3 questions |
| **Tool layer table** | 9-row table with emoji + examples + conditions | 3-row table (allow/forbid by tier) |
| **MEMORY + PROFILE cleanup** | Not in audit scope | Added: remove stale entries, merge duplicates, compress verbose entries |

### 5c. MEMORY/PROFILE Slimming (v1.4)

The audit now extends beyond SOUL.md to include MEMORY and USER PROFILE stores:

- **MEMORY**: Remove entries that are one-time task completions, fix notes for bugs already resolved, process documentation now in SOUL.md, or meta-entries about past cleanups.
- **USER PROFILE**: Merge duplicate preference statements (common issue: "don't teach syntax" appears in 3+ entries worded differently). Compress verbose entries by 40-60%.
- **Target**: MEMORY < 50% of limit, PROFILE < 45% of limit.

See `autonomous-optimization-architect` skill `references/context-slim-example-2026-05-01.md` for concrete before/after metrics.

### 4. Format Consistency Check

Verify all profiles follow the same section order:

```bash
echo "=== Section headers ==="
for f in ~/.hermes/profiles/*/SOUL.md; do
  echo "--- $(basename $(dirname $f)) ---"
  grep '^## ' "$f"
done
```

All should have: `## 核心能力` → `## 可用工具集` → `## 配合技能` → `## 协作规则` → `## 沟通风格`

### 5. Reference Integrity

Check that all skill references in `## 配合技能` sections actually exist:

```bash
# Extract all referenced skill names from 配合技能 sections
grep -A20 '## 配合技能' ~/.hermes/profiles/*/SOUL.md | grep '`[a-z]' | sed 's/.*`\([a-z-]*\)`.*/\1/' | sort -u
# Compare against installed skills
ls ~/.hermes/skills/*/*/SKILL.md 2>/dev/null | xargs -I{} dirname {} | xargs -I{} basename {} | sort -u
```

For deeper quality checks on referenced skills, use `mcp_skill_auditor`:
- `audit_skill(name='<skill>')` — per-skill check: frontmatter completeness (author/version), cross-reference validity, script syntax
- `audit_all_skills` — bulk scan, identifies skills with issues across the entire library
- Common issues found: missing author field, `related_skills` referencing non-existent skills, broken cross-references

### 5c. Script Path Verification (P1-priority)

> ⚠️ **Systemic pitfall:** Profile SOUL.md scripts almost always live under `~/.hermes/skills/development/<X>/scripts/`, NOT under `~/.hermes/profiles/<domain>/`. Relative paths like `ops-domain/scripts/` or `ecommerce-auto-pipeline/scripts/` will NEVER resolve from the profile directory. This was observed in 3 of 5 domains in the 2026-05-01 audit. **Always convert to absolute paths** starting with `~/.hermes/skills/development/...`.

For each `核心脚本` table in each SOUL.md, verify the path resolves using this logic:

```bash
# 1. Read the path from SOUL.md
# 2. Decision tree:
#    - Starts with '/' or '~' → resolve directly, test -f
#    - Relative (no leading / or ~) → search globally, flag as BROKEN even if found
# 3. Flag: if global find succeeds but profile-relative fails → P1, must fix to absolute

# Quick bulk check for all profiles:
for f in ~/.hermes/profiles/*/SOUL.md; do
  domain=$(basename $(dirname $f))
  echo "=== $domain ==="
  # Extract paths from core scripts table (columns 3 of pipe tables under 核心脚本)
  grep -A20 '核心脚本' "$f" | grep '^\|.*\|.*\|' | awk -F'|' '{print $4}' | grep -o '[\~/][^ ]*' | while read p; do
    if [[ "$p" == /* ]] || [[ "$p" == ~* ]]; then
      expanded=$(eval echo "$p")
      test -f "$expanded"/*.py 2>/dev/null && echo "  OK: $p" || echo "  BROKEN: $p (dir not found)"
    else
      # Relative path — auto-fail from profile dir perspective
      echo "  P1-RELATIVE: $p (won't resolve from ~/.hermes/profiles/$domain/)"
      found=$(find ~/.hermes/skills -path "*/$p/*.py" 2>/dev/null | head -3)
      [ -n "$found" ] && echo "    → Found at: $found" || echo "    → NOT FOUND anywhere"
    fi
  done
done
```

### 6. Redundancy Across Files

Check if the same content appears in multiple SOUL.md files (or in the main SOUL.md). Common duplications:
- Collaboration rules (every profile has the same 7-line block)
- Processing pipeline descriptions (research → ec-domain flow appears in both main and ec-domain)
- Model configuration rationale

## Sub-agent SOUL.md Self-Study (v1.5)

When SOUL.md rules change or after a domain capability upgrade, run this batch workflow:

1. **Dispatch** all domain sub-agents simultaneously with `delegate_task(model="deepseek-v4-pro")`, each reading its own SOUL.md
2. **Report format**: (a) most violated rules, (b) contradictions found, (c) self-assessment score
3. **Fix bugs**: sub-agents report SOUL.md bugs (ghost MCP references, wrong tool descriptions) — patch them
4. **Save to wiki**: `~/brain/soul/<domain>.md` with frontmatter, then `gbrain put`

Common finding across all domains: "先计划后执行" rule violated universally — sub-agents jump to execution without review. This is structural when using delegate_task (fire-and-forget), not a discipline gap.

## Post-Edit Self-Violation Pitfall (v1.5)

> ⚠️ **CRITICAL**: After editing SOUL.md rules, the agent frequently violates the new rules in the very next response. This was observed in a 2026-05-01 session where \"Pro/Flash 分工\" was added, then the agent immediately drew architecture diagrams and analyzed solutions — precisely what the rule forbids.

**Prevention**: After any SOUL.md edit, the next response must be a **minimal confirmation** (≤2 sentences). No analysis, no diagrams, no explanation of what was changed or why. Just "已修" or equivalent.

## System-Prompt-Bloat → Performance-Degradation Spiral (v1.6)

> ⚠️ **CRITICAL**: This is the most impactful finding from the 2026-05-04 system self-audit. The agent was rated 70.3/100 and user reported "越来越蠢" (progressively dumber). Root cause: system prompt bloat.

### The Causal Chain

```
SOUL.md layered rules (121 lines, accumulated as bandaids)
  + Memory 29 entries injected every turn (domain-irrelevant pollution)
  + 118 skill names listed every turn
  + USER PROFILE verbose entries
  = ~11,200+ tokens eaten before conversation starts
    ↓
Context window starvation → truncated reasoning → forgetting earlier instructions
    ↓
User perceives "越来越蠢"
```

### Key Metrics from 2026-05-04 Audit

| Component | Size | Problem |
|:----------|:-----|:--------|
| SOUL.md | 121 lines, 6706 chars | 14 instances of "不", 5 of "禁止" — negative rules piled as bandaids |
| MEMORY | 29 entries, 78% usage | PDD/scrapling/GBrain injected even during quant tasks |
| Skills list | 118 names | All listed every turn regardless of domain |
| Checkpoints | 52 snapshots | Historical bloat |

### Three-Cut Fix (Proven 2026-05-04)

1. **SOUL.md strip**: 121 lines → ~40 lines. Delete layered "don't do X" bans. Keep: dispatch table + tool tiers + delegate spec + 3 core rules.
2. **Memory partition**: Split into "core rules (8 entries, always inject)" + "domain knowledge (21 entries, inject only when relevant domain is active)". Short-term: merge overlapping entries (PDD 5→1, quant 5→1).
3. **Model downgrade**: deepseek-v4-pro → deepseek-v4-flash for pure orchestration.

### Post-Fix Result

| Metric | Before | After |
|:-------|:------:|:-----:|
| Memory entries | 39 | 29 |
| Memory usage | 94% (7534/8000) | 78% (6244/8000) |
| orchestrator misconfig | research-domain true | false |

### Anti-Pattern: Rule Accumulation as Band-Aids

When the agent makes a mistake, the instinct is to add a new rule to SOUL.md. This creates a vicious cycle:
- More rules → more context eaten → less room for reasoning → more mistakes → more rules

**Fix**: Instead of adding rules, delete overlapping ones. The three-tier tool permission table already covers most cases. Trust the model's training rather than micro-managing every possible violation.

## Config Alignment: memory/user_char_limit vs Official Spec (v1.7)

> ⚠️ **2026-05-10 发现**: memory_char_limit=6000, user_char_limit=4000 — 分别是官方推荐 (2200/1375) 的 2.7x 和 2.9x。每会话多注入 ~2,500 chars 的无用上下文。

**检查方法**:
```bash
grep -A3 "^memory:" ~/.hermes/config.yaml | grep char_limit
# 官方推荐: memory 2200, user 1375
# 合理上限: memory 4000, user 2000 (用户可自定义)
```

超过合理上限时建议降回，配合 MEMORY/USER 压缩确保不丢失信息。

## Optimization Bias: 不要只减成本，要提升能力 (v1.8)

> ⚠️ **2026-05-10 实战教训**: 用户要求"多维度能力提升(任务处理/记忆/架构/思考宽度深度)"，我连续几轮只做上下文压缩、删技能、减配置 — 全是减成本。被指出"很片面"后才意识到：架构优化 ≠ 瘦身。

**诊断信号**: 当你发现自己连续做了 3+ 个"删/减/压缩"操作而没有任何"新增能力"操作时，你陷入了成本优化的隧道视野。

**正确姿势**:
1. 收到"优化系统"类任务 → 先列两个清单: 减成本项 + 增能力项
2. 减成本 (上下文/冗余/重复): 可快速执行
3. 增能力 (推理/关联/自主性): 需调研官方文档和社区方案
4. 两项交替推进，不在一类上连续做 >3 个操作

**反例**: 减了 18 个技能(✅) → 压缩记忆 57%(✅) → 调配置(✅) → 用户问"能力提升呢？"(❌ 没做)

## Bulk File Operation Safety (v1.7)

> ⚠️ **2026-05-10 事故**: 批量 `mv` 归档技能时，脚本未做范围校验，将 18 个目标外的 89 个技能也移入归档。必须在 2 分钟内检测并回滚。

**三步安全法**:
```bash
# 1. 先 dry-run 列出所有将被操作的目标
for d in $LIST; do [ -d "$d" ] && echo "WILL MOVE: $d"; done | wc -l
# 2. 人工确认数量匹配预期
# 3. 执行，执行后立即验证
for d in $LIST; do [ -d "$d" ] && mv "$d" .archived/; done
echo "Moved: $(find .archived -name SKILL.md | wc -l), Expected: N"
```

此规则适用于所有批量 `mv`/`rm`/`cp`/`find -delete` 操作，不限于技能管理。

## Profile SOUL.md Compression Results (v1.7)

| 域 | 压缩前 | 压缩后 | 压缩率 |
|:--|:--|:--|:--|
| ec-domain | 8,893 chars | 1,468 chars | -83% |
| code-domain | 8,188 chars | 913 chars | -89% |
| 6域总计 | 37,010 chars | 21,304 chars | -42% |

压缩策略: 技能中已有的详细领域知识从 profile 删除，profile 只保留角色定义+调度规则+硬约束+风格。

## SOUL.md 主文件精简 (v1.8, 2026-05-10)

**287行→83行(-72%)** 的精简原则：

1. **删除重复定义**：L1/L2/L3在三处出现→保留决策矩阵一处
2. **删除脚本已强制的规则**：lesson_inject/enforce_delegate已脚本化→删除文本版规则6(实时学习)
3. **合并到调度速查表**：指令流水线/delegate规范/故障恢复全部嵌入速查表
4. **下放references/**：Role路由/工作流模板移到已有独立文件
5. **集中禁止清单**：7条散落禁止→一个区块
6. **域profiles加知识引用头**：每个域SOUL.md首部加 `📖 知识引用: global.md#🔴CRITICAL | lessons/{domain}.md | graphify:lesson:{domain}`
7. **调度速查表硬约束为enforce_delegate唯一入口**：所有delegate路径统一为 `enforce_delegate.py -d {d} -g "{任务}"` → delegate_task(context=enriched)
8. **启动协议改为硬检查清单格式**：每项 `[ ]` 标记，不可跳过。追加 delegate前/输出前 两套检查清单。

留下的8模块：核心定位+决策矩阵+启动协议(含硬检查清单)+调度速查表+资源表+工具边界+禁止清单+全局架构图。

**关键洞察**：SOUL.md不是"所有规则的堆砌场"，是"最小必要规则的单一真相源"。添加规则前先问：它在别处是否已有定义？是否能做成脚本而非文本？

## Memory Dedup Against SOUL.md (v1.5)

MEMORY entries that duplicate SOUL.md rules are wasted context tokens. When trimming MEMORY:
- Cross-reference each MEMORY entry against SOUL.md sections
- If the rule is in SOUL.md, the MEMORY entry is redundant — remove or collapse to a one-line pointer
- Example: "速度优化规则" / "执行准则" / "沟通协议" were in both MEMORY and SOUL.md — trimmed to one-line references

## Output

After an audit session, the user should receive:

1. **Change log** — What was removed/added/changed per file (old lines → new lines)
2. **Line count reduction** — Before/after for each file
3. **Format compliance** — Which files match the standard format, which don't

## Reference

- `hermes-config-sync` — For config/SOUL.md changes that must cascade to profiles
- `self-diagnosis` — For technical system health checks (services, scripts, delegation)
- `references/audit-findings-2026-05-01.md` — Concrete audit example: 15 findings across 6 SOUL.md files, severity distribution, systemic path-failure pattern
- `references/domain-script-health-check.md` — Cross-domain Python script validation protocol: syntax→import→deps→side-effect scan→entry-point guard audit. Catches dangerous imports (e.g. DB DELETE on `import`). Use when user asks to "检验 domain 脚本" or during periodic maintenance.
