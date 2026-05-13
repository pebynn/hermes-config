# Implementation Plan: t_81453ae4 — GEPA 5 Guardrails + Lessons Forgetting Mechanism

## Task
Adapt GEPA 5 guardrails to `~/.hermes/scripts/audit_bd_layer.py` based on gepa_survey_analysis.md P0 recommendations.

## Architecture Overview

Single-file script at `~/.hermes/scripts/audit_bd_layer.py`. All new features gated behind `--extended` flag. Existing audit logic (kanban.db scan, B/D injection rate, QQ Bot alert) preserved.

```
audit_bd_layer.py
├── [EXISTING] scan_kanban_db() → B/D injection rate check
├── [EXISTING] alert_qq_bot() → QQ Bot notification
├── [NEW] check_size_limits() → Guardrail 1
├── [NEW] check_pytest_integration() → Guardrail 2
├── [NEW] check_cache_compat() → Guardrail 3
├── [NEW] check_semantic_drift() → Guardrail 4
├── [NEW] check_review_gate() → Guardrail 5
├── [NEW] manage_lesson_decay() → Lessons forgetting
└── [NEW] run_extended_audit() → Orchestrator for --extended
```

## Design Decisions

### 方案选择
- **单文件脚本**: 保持原有架构，新增函数不破坏现有逻辑
- **--extended 标志**: 向后兼容，默认只跑原有audit
- **最小依赖**: 只用 stdlib + sqlite3 + subprocess，语义漂移检测可选LLM调用
- **lessons存储**: JSONL格式 `~/.hermes/lessons/lessons.jsonl`，每条一行
- **告警输出**: stdout (兼容现有cron) + QQ Bot (可选)

### 替代方案
- 多文件模块化 → 拒绝：任务要求单文件
- 数据库存储lessons → 拒绝：过度设计，JSONL足够
- 每次跑所有护栏 → 采用：--extended一次性跑5道

### 风险
- 语义漂移检测需LLM API调用，可能慢且消耗tokens → 默认跳过，需--semantic显式启用
- lessons文件并发写 → 使用flock或单进程假设(cron单实例)
- pytest集成找不到测试 → 跳过并报告

## Detailed Design

### Guardrail 1: Size Check (`check_size_limits`)
- Scan `~/.hermes/profiles/*/skills/**/SKILL.md`
- Check: file size ≤ 15KB
- Check: each tool description in YAML frontmatter ≤ 500 chars
- Report: [file, current_size, limit, pass/fail]

### Guardrail 2: pytest Integration (`check_pytest_integration`)
- Find changed skills/scripts (mtime within 24h, or git diff)
- Map changed files to test files:
  - `profiles/*/skills/X/SKILL.md` → `profiles/*/skills/X/tests/`
  - `scripts/X.py` → `scripts/tests/test_X.py`
- Run pytest on associated tests
- Report: [file, test_file, result, failures]

### Guardrail 3: Cache Compatibility (`check_cache_compat`)
- Scan `~/.hermes/lessons/` and `~/.hermes/memory/` for recent changes
- Check if session caches (in `~/.hermes/sessions/`) would be invalidated
- Logic: if lesson files modified, flag that downstream sessions may use stale cache
- Report: [affected_cache, change_type, recommendation]

### Guardrail 4: Semantic Drift (`check_semantic_drift`)
- Requires `--semantic` flag (LLM call, expensive)
- For each skill: extract original purpose from name/description
- Compare with current SKILL.md content via LLM
- If drift > threshold, flag for review
- Report: [skill, original_purpose, current_summary, drift_score]

### Guardrail 5: Review Gate (`check_review_gate`)
- Tier mapping:
  - L1 (SKILL.md) → audit check only
  - L2 (Tool descriptions, minor updates) → automated review
  - L3 (System prompt, code evolution) → human review required
- Check recent git changes against L2/L3 matrix
- Report what needs review and at what level

### Lessons Forgetting (`manage_lesson_decay`)
- File: `~/.hermes/lessons/lessons.jsonl`
- Schema per entry:
```json
{
  "id": "uuid",
  "content": "lesson text",
  "level": "red|yellow|green",
  "domain": "code-domain|ops-domain|...",
  "timestamp": "ISO8601",
  "confirmed_at": "ISO8601|null",
  "weight": 1.0,
  "status": "active|decayed|archived"
}
```
- Decay rules:
  - >90 days since last confirmation → weight *= 0.5, status="decayed"
  - >180 days since last confirmation → status="archived", move to `lessons/archive/`
- Cron: run daily, process all lessons

## Implementation Order
1. Write test file `~/.hermes/scripts/tests/test_audit_bd_layer.py`
2. Implement `audit_bd_layer.py` with:
   a. Base structure + existing audit logic scaffold
   b. Lessons decay mechanism (simplest, no external deps)
   c. Size check guardrail
   d. Cache compatibility guardrail
   e. pytest integration guardrail
   f. Review gate guardrail
   g. Semantic drift guardrail (with --semantic flag)
3. Debug + verify
4. Self-review

## Test Strategy
- Unit tests for each guardrail function
- Integration test for `run_extended_audit()`
- Mock filesystem for skill/lesson scanning
- Mock kanban.db for existing audit
- At least 1 RED test before implementation (TDD)
