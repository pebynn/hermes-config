# System Audit Findings — 2026-05-01

## Methodology

4-track parallel delegation:
1. `hermes-config-audit` → ops-domain (config.yaml, .env, auth.json, profiles)
2. `soul-maintenance-audit` → code-domain (6 SOUL.md content quality)
3. System health → ops-domain (services, disk, venv, pycache)
4. Script path verification → code-domain (23 paths across 6 SOUL.md)

## Findings Distribution

| Severity | Count | Examples |
|:---------|:-----|:---------|
| P1 | 6 | MySQL 密码硬编码, 174 过期技能副本, 2 处路径断裂, 计数不准, 路径缺失 |
| P2 | 6 | 冗余协作规则×5, format drift, 退货率差异, 61 skills no author, pycache×3, .env no comments |
| P3 | 3 | 计划模板冗余, 后台任务块, 21 无效交叉引用 |

## Key Patterns Discovered

### 1. Systemic Relative Path Failure (P1)
3 of 5 domains (code-domain, ops-domain, ec-domain) used relative paths in SOUL.md `核心脚本` tables that cannot resolve from `~/.hermes/profiles/<domain>/`. Only finance-domain used absolute `~/quant/` paths — zero issues.

Root cause: scripts live under `~/.hermes/skills/development/<X>/scripts/`, but profiles are at `~/.hermes/profiles/<domain>/`. Relative paths go nowhere.

Fix: convert all to absolute `~/.hermes/skills/development/X/scripts/`.

### 2. Stale Skill Copies in profiles/*/skills/ (P1)
174 expired skill copies under `~/.hermes/profiles/*/skills/`. Sub-agents loaded via profile may pick up outdated versions.

### 3. Count Inaccuracy (P1)
code-domain SOUL.md claimed "15个技能" but listed 20. After adding 3 more, it became 23 but still said "20个".

Rule: always count the actual list items, never trust the claim.

### 4. Cross-reference Drift (P2)
`requesting-code-review` referenced non-existent `github-code-review` skill. Author field empty in 61/112 skills (cosmetic but pervasive).

### 5. Format Drift (P2)
finance-domain has a completely different section structure from the other 4 domains. Not necessarily wrong (domain-specific needs), but worth noting for maintainers.

## What Worked Well

- Parallel 4-track delegation completed in ~11 min vs estimated 30+ min serial
- All 23 script paths verified, 0 actual missing files
- All 13 cron jobs healthy, 0 failures
- Gateway (3h40m uptime) and Camofox both green
- 112 skills, all cross-references in SOUL.md `配合技能` sections valid (0 dead links)
- skill-auditor MCP correctly identified frontmatter issues and cross-reference problems

## System Health Baseline

| Metric | Value |
|:-------|:------|
| Gateway uptime | ~3.7h |
| MCP servers | 13 online |
| Cron jobs | 13 enabled, 3 never-run (new) |
| venv size | 2.8G |
| checkpoints | 301M |
| Disk free | 800G+ |
| SKILL.md count | 112 |
| .env lines | 33 (0 comments) |
