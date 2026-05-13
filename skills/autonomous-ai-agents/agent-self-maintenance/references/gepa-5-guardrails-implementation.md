# GEPA 5 Guardrails + Lessons Decay — Implementation (2026-05-13)

## Background

Read and analyzed two papers:
1. **GEPA**: Genetic-Pareto Prompt Evolution (ICLR 2026 Oral) — Nous Research hermes-agent-self-evolution core algorithm
2. **Survey**: A Comprehensive Survey of Self-Evolving AI Agents (arXiv 2508.07407) — 4-component unified framework

## Implemented: 5 Guardrails in audit_bd_layer.py

Deployed to `~/.hermes/scripts/audit_bd_layer.py` (719 lines).

### Usage
```bash
# Basic (original B/D injection audit)
python3 ~/.hermes/scripts/audit_bd_layer.py

# Extended (all 5 guardrails + lessons decay)
python3 ~/.hermes/scripts/audit_bd_layer.py --extended

# Full (with LLM-based semantic drift)
python3 ~/.hermes/scripts/audit_bd_layer.py --extended --semantic --alert

# JSON output
python3 ~/.hermes/scripts/audit_bd_layer.py --extended --json
```

### Guardrail 1: Size Check
- Skill files ≤15KB
- Tool descriptions ≤500 chars
- Scans all SKILL.md under profiles/

### Guardrail 2: Pytest Integration
- Detects changed .py/.md/.sh files in last 24h
- Maps to test files (scripts/tests/test_<name>.py or skill/tests/)
- Auto-finds pytest binary (venv → system → PATH)
- Returns skipped if pytest not available

### Guardrail 3: Cache Compatibility
- Scans lessons/ and memory/ for recent changes
- Checks if active sessions (last 48h) might use stale cache
- Reports invalidation risk count

### Guardrail 4: Semantic Drift Detection
- Heuristic mode (--semantic): checks if skill name/description appears in body
- LLM mode: calls API to compare original purpose vs current content
- Skips `.archived/` directories

### Guardrail 5: Review Gate (L2/L3 Matrix)
- L2 patterns (tools, SKILL.md, minor updates) → automated review
- L3 patterns (SOUL.md, system, core code) → human review required
- Reports what needs review at what level

## Lessons Decay Mechanism

Time-based forgetting:
- >90 days unconfirmed → weight *= 0.5, status = "decayed"
- >180 days unconfirmed → status = "archived", moved to archive/
- Each lesson stored as JSONL with id, timestamp, confirmed_at, weight

## Gap Analysis (vs GEPA/Survey)

| Gap | Status | Priority |
|:--|:--|:--|
| Genetic algorithm layer | Not implemented | P2 |
| Execution trace analysis | Not implemented | P1 |
| 5 guardrails | ✅ Deployed | P0 |
| Regression/退化 detection | Not implemented | P1 |
| Forgetting mechanism | ✅ Deployed | P0 |
| Tool description optimization | Not implemented | P2 |
| System prompt optimization | Not implemented | P2 |

## Bug Fixes During Validation

1. **Semantic drift false positives**: `.archived/` skills flagged. Fixed: skip directories containing ".archived" in path.
2. **Pytest not found**: System Python has no pytest. Fixed: probe 3 possible pytest locations (venv → sys.executable → PATH).
3. **Pytest availability check**: subprocess.run exceptions only catch FileNotFoundError/TimeoutExpired, not non-zero returncode. Fixed: check `result.returncode == 0`.
4. **test_paths variable ordering**: `.sh` matching code added before test_paths initialization. Fixed: initialize test_paths = set() at function start.
5. **.sh file test matching**: Shell scripts weren't matched to test files. Fixed: added test file lookup during .sh scanning loop.

## Research-Domain Kanban Worker Issue

Research-domain workers crash or get stuck on arxiv/semanticscholar calls because worker sandbox network access differs from orchestrator MCP tools. Pattern: do research via orchestrator's web_extract → write analysis file → create code-only kanban task referencing pre-fetched file.

## Source Analysis

Analysis file: `~/.hermes/kanban/workspaces/gepa_survey_analysis.md`
