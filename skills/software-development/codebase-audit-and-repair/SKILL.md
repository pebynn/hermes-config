---
name: codebase-audit-and-repair
description: Systematic multi-file code audit → severity triage (P0-P3) → batch-fix via parallel delegation. Read first, fix second, parallelize by file dependency.
version: 1.0.0
author: Hermes Agent
allowed-tools:
  - read_file
  - search_files
  - delegate_task
  - todo
  - memory
when-to-use: |-
  User says:
  - "审查/审核/audit/review X的代码"
  - "检查/check X的所有问题"
  - "全面检修/全面审查 X"
  - "帮我过一遍 X 的代码"
  - "帮我看看 X 的代码有什么问题"
  - "审一下/修一下 X 的代码和逻辑"
  - Any request to systematically audit a multi-file codebase (≥3 files or ≥500 lines)
  - "把 XX 里的问题都修了"

  This is NOT for:
  - Pre-commit review of a small diff (use requesting-code-review)
  - Debugging a specific bug (use systematic-debugging)
  - Implementing a plan step by step (use subagent-driven-development)
  - Quick code style fixes (just fix it directly)
---

# Codebase Audit & Repair

## Overview

A systematic process for auditing an existing multi-file codebase, identifying all issues, triaging by severity, and batch-fixing via parallel delegation.

**Core principle:** Read everything before touching anything. Fix in parallel where files are independent. Never fix without understanding the full picture first.

## Phases

### Phase 1: Survey & Read

1. List all files in scope — `search_files` or `read` the directory
2. Read each file completely. Do not skip or skim.
3. Build a mental model of:
   - File dependency graph (who imports/uses what)
   - Data flow between files
   - Contract boundaries (shared data structures, function signatures)
   - Which files are independent (can be fixed in parallel)

### Phase 2: Categorize Issues

Walk through each file systematically. Look for issues in these categories:

| Category | What to Check | Examples |
|:---------|:--------------|:---------|
| **Logic** | Formula correctness, unit conversions, conditional logic | Wrong net profit calc, price unit wrong |
| **Security** | Plaintext passwords, hardcoded secrets, injection | `--password` on CLI, API keys in code |
| **Consistency** | Skill/doc says X, code does Y | doc says 6-size expansion, code uses 3 |
| **Robustness** | Silent exception swallowing, missing validation | `except: pass`, no price cap |
| **Maintainability** | Hardcoded paths, dead code, duplicate logic | `/home/user/` paths, dead branches |
| **Test Coverage** | Missing tests for core logic | Pricing formula untested |

Assign severity:
- **P0** — Causes wrong financial results, data corruption, or lost money
- **P1** — Security hole, wrong behavior in common path, inconsistent with documented contract
- **P2** — Maintainability debt, dead code, hardcoded paths, silent failures
- **P3** — Nice-to-have: missing tests, minor style

### Phase 3: Plan Parallel Batches

Group fixes by **file conflict** (never fix the same file in parallel):

```
Batch 1: file_a.py (all its issues) → delegate_task(code-domain)
Batch 2: file_b.py (all its issues) → delegate_task(code-domain)
Batch 3: file_c.py + file_d.py (independent files, non-overlapping) → if one subagent handles both
```

**Rules:**
- Each file touched by exactly one subagent
- If two files share an import/interface contract, they go in the same batch or sequential batches
- Document the dependency rationale in the delegation context

**Delegate context must include:**
```python
delegate_task(
    goal=f"修复 {filename} 中的 N 个问题",
    context=f"""
    文件路径: /path/to/file.py

    问题清单:
    1) [问题] → [如何修]
    2) [问题] → [如何修]
    ...
    """
)
```

### Phase 4: Verify & Update Documentation

After all batches complete:
1. Spot-check key fixes (read the modified lines)
2. Update skill documentation if code behavior changed (pricing formula, size expansion, etc.)
3. Update memory if a new convention was established (env var names, path patterns)
4. Report final tally: files modified, issues fixed by severity

## Supporting References

- **`references/grep-for-code-analysis.md`** — Using grep/rg reliably from Python subprocess for code scanning. Covers the rg-exit-code-2 pitfall, efficiency patterns, and a full dead-code-detection skeleton.
- **`references/hygiene-scan-patterns.md`** — Reusable scanning/fixing scripts for: hardcoded credentials in Python scripts, silent exception blocks (bare `except: pass`/`except Exception: pass` with traceback insertion), and cross-file function body drift detection. Each pattern includes `rg` scan commands, a Python fixer function, and real-world results (139 silent exceptions fixed across 29 files).

## Pitfalls

- **Same file in parallel** — use `todo` to track which files are being fixed to avoid conflicts
- **Subagent re-reads stale content** — if you read a file before delegating, note in context that the subagent must `read_file` fresh
- **Over-scoping** — fix only the identified issues. No refactoring, no "while I'm here" features
- **Forgetting doc sync** — SKILL.md is part of the codebase. If behavior changes, docs must too
- **Missing security** — `--password` on CLI, hardcoded keys, and hardcoded paths are the most common finds. Use `references/hygiene-scan-patterns.md` for hardcoded credential + silent exception + function drift scanning scripts.
- **Incremental fixing across sessions** — fixing one bug per session creates the "越修越乱" anti-pattern. Each session introduces partial state, stale test data, and new bugs from incomplete fixes. When a pipeline has multiple bugs spanning sessions, audit ALL files in ONE pass, fix ALL bugs in ONE session, then end-to-end verify. Never spread the same class of bug fix across multiple sessions.
- **Same-class bugs in multiple files** — when you find a bug pattern (e.g. None-not-checked-before-subscript, loop-breaks-on-first-iteration), scan ALL scripts in the pipeline for the same pattern before fixing any single instance. Apply the fix consistently across all files.
