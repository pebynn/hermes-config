---
name: autonomous-optimization-architect
description: LLM cost optimization, model routing, circuit breaker, and FinOps automation for Hermes Agent. Real Python scripts for session cost tracking, model failover, and config management.
version: 2.8.0
author: Hermes Agent
tags: [optimization, llm, routing, cost, circuit-breaker, finops, hermes-skill, actionable]
---

# Autonomous Optimization Architect

Optimize LLM API costs, configure multi-model routing with automatic failover,
set up circuit breakers to prevent cost runaway, and monitor token consumption
— all with Hermes-native Python scripts.

## Trigger Conditions

Load this skill when the user needs any of the following:

- Monitor and reduce LLM API costs (AI FinOps)
- Configure multi-provider model routing with automatic fallback
- Set up a circuit breaker to prevent cost spikes from runaway agents
- Analyze session logs for model usage, failures, and cost anomalies
- Schedule daily cost reports via Hermes cron
- Understand which domains (research, code, ecommerce, finance) consume the most tokens
- Auto-patch Hermes config.yaml to switch to cheaper fallback models
- Debug or audit the cost-tracker / circuit-guard / model-router-config scripts

## Skills Location

All files live under:
```
~/.hermes/skills/devops/autonomous-optimization-architect/
├── SKILL.md
├── scripts/
│   ├── cost-tracker.py          # Session log cost analysis
│   ├── circuit-guard.py         # Circuit breaker + auto-fallback
- `scripts/cost-circuit-breaker.py  # Daily cost auto-pause ($8.00 threshold, calibrated)`
│   └── model-router-config.py   # Model routing config management
├──  references/
│   ├── cost-thresholds.yaml              # Cost thresholds and circuit breaker params
│   ├── failover-chain.yaml              # Primary -> Fallback -> Cost-Saving chain
│   ├── session-file-formats.md          # Hermes session file structure reference
- `references/deepseek-pricing-cache.md` — Full pricing breakdown, cache mechanics, 12× cost correction
- `references/cost-calibration-workflow.md` — Step-by-step calibration against provider billing data
- `references/china-provider-fallbacks.md` — Z.ai vs 智谱, model naming, latency test
- `references/qqbot-gateway-setup.md` — QQ Bot QR scan setup, authorization, deliver to cron
```

## Available Scripts

### 1. cost-tracker.py

Parses ~/.hermes/sessions/ JSON/JSONL files, extracts model/provider info,
estimates LLM API costs, and groups by day, model, and domain.

```bash
# Full report for last 7 days
python3 scripts/cost-tracker.py

# JSON output for programmatic use
python3 scripts/cost-tracker.py --json

# Last 30 days, filter by model
python3 scripts/cost-tracker.py --days 30 --model deepseek-v4-pro

# Flag sessions exceeding $0.50
python3 scripts/cost-tracker.py --threshold 0.50 --json

# Filter by domain
python3 scripts/cost-tracker.py --domain code
```

**Cost model** (edit MODEL_COST_MAP in the script to add models):

DeepSeek input pricing has TWO components: cache-miss (full) and cache-hit (~1/10).
With 85% cache-hit rate (validated from DeepSeek billing records), effective input cost is dramatically lower.

| Model              | Cache-Miss $/M | Cache-Hit $/M | Output $/M | Effective Input* |
|--------------------|----------------|---------------|------------|------------------|
| deepseek-v4-pro    | $0.435         | $0.0036       | $0.87      | $0.068           |
| deepseek-v4-flash  | $0.14          | $0.0028       | $0.28      | $0.023           |
| deepseek-chat      | $0.28          | $0.028        | $0.42      | $0.066           |
| Unknown (default)  | $1.00          | $1.00         | $4.00      | $1.00            |

> *Effective input = 85% cache-hit × cache-hit price + 15% cache-miss × cache-miss price.
> V4 Pro has 75% temporary discount until 2026-05-31. Without discount: cache-miss ~$1.74, output ~$3.48.
> **Always verify** against official DeepSeek pricing page. Cache-hit pricing changed permanently to 1/10 in April 2026.
> See `references/deepseek-pricing-cache.md` for full pricing breakdown and cache mechanics.

**Domain detection**: The script scans session content for keywords to classify
each session as `research`, `code`, `ec`, `finance`, or `general`.

**Output fields** (JSON mode):
```json
{
  "period": {
    "total_sessions": 42,
    "total_cost": 1.2345,
    "total_input_tokens": 500000,
    "total_output_tokens": 120000
  },
  "by_model": { "deepseek-v4-pro": {"cost": 1.0, "sessions": 20, ...} },
  "by_domain": { "research": {"cost": 0.5, "sessions": 10} },
  "by_source": {
    "interactive": {"cost": 5.2, "sessions": 30, "input_tokens": 200000, "output_tokens": 80000},
    "cron": {"cost": 0.15, "sessions": 6, "input_tokens": 5000, "output_tokens": 2000},
    "request_dump": {"cost": 0.0, "sessions": 101, "input_tokens": 0, "output_tokens": 0}
  },
  "by_day": { "2026-05-10": {"cost": 0.35, "sessions": 5} },
  "flagged_sessions": [...]
}
```

**`by_source` breakdown** distinguishes:
- `interactive` — session_*.json archives (conversational)
- `cron` — *.jsonl transcripts (scheduled agent runs)
- `request_dump` — API request/response files (currently all failed, $0.00)

### 2. circuit-guard.py

Reads Hermes config.yaml, checks model costs against configured limits,
detects repeated failure patterns from session logs, and auto-patches
config.yaml to switch to fallback models.

```bash
# Check status (human-readable default)
python3 scripts/circuit-guard.py

# JSON output for programmatic use
python3 scripts/circuit-guard.py --json

# Verbose mode with error details
python3 scripts/circuit-guard.py --verbose

# Auto-patch config.yaml if circuit is broken
python3 scripts/circuit-guard.py --auto-fix

# Combined: verbose + auto-fix
python3 scripts/circuit-guard.py --auto-fix --verbose

# Custom paths
python3 scripts/circuit-guard.py \
  --config ~/.hermes/config.yaml \
  --thresholds references/cost-thresholds.yaml
```

**Output (default — human-readable):**
```
Hermes Circuit Guard — Status: OK
  Active model:   deepseek-v4-pro
  Fail count:     0 / 5 (threshold)
  Window:         30 min
  Total sessions: 120
```

**Output (--json):**
```json
{
  "status": "ok|warning|circuit_broken",
  "active_model": "deepseek-v4-pro",
  "suggestion": "Circuit broken: 6 failures in 30min window...",
  "fail_count": 6,
  "fail_threshold": 5,
  "window_minutes": 30,
  "cost_24h": 0.0,
  "total_sessions": 120
}
```

**Auto-fix**: When status is `circuit_broken` or `warning`, the `--auto-fix`
flag backs up config.yaml to `config.yaml.bak.<timestamp>` and updates
`model.default` and `delegation.model` to the fallback model.

**Threshold config** (references/cost-thresholds.yaml):
```yaml
# Calibrated against real DeepSeek billing (2026-05-10)
# Real: 15 days ¥600 ≈ $84, avg $5.6/day, peaks $11-18/day
per_session_max: 2.00
per_day_max: 8.00
circuit_breaker:
  consecutive_failures: 5
  window_minutes: 30
```

### 3. model-router-config.py

Manages Hermes config.yaml delegation model settings and generates failover
chain configurations.

```bash
# Show current model and delegation config
python3 scripts/model-router-config.py show

# Validate configuration completeness
python3 scripts/model-router-config.py validate

# Suggest optimal model routing
python3 scripts/model-router-config.py suggest

# Pretty-print JSON output
python3 scripts/model-router-config.py show --pretty
```

**Actions**:

| Action     | Description |
|------------|-------------|
| `show`     | Display current model, provider, providers list, and delegation config |
| `validate` | Check config completeness — missing keys, API keys, provider config |
| `suggest`  | Analyze cost/performance and recommend optimal routing based on failover chain |

## Hermes Integration

### How the scripts work together

```
cost-tracker.py -----> JSON report -----> circuit-guard.py
      ^                                      |
      |                                      v
  Session logs                        model-router-config.py
  (~/.hermes/sessions/)                      |
                                             v
                                       Hermes config.yaml
                                       (auto-patched on circuit break)
```

1. **cost-tracker.py** analyzes session logs → produces structured cost report
2. **circuit-guard.py** reads the cost report + session failures → decides if
   circuit should break → can auto-patch config.yaml
3. **model-router-config.py** validates and suggests routing configs based on
   the failover chain template

### Cron job recipes

Schedule these with Hermes cron for automated cost monitoring:

**Daily cost report** (runs every day at 9 AM):

```bash
cronjob action=create \
  schedule="0 9 * * *" \
  name="daily-cost-report" \
  prompt="Run python3 scripts/cost-tracker.py --days 1 --json and summarize costs. If any session exceeded $2.00, flag it. If total daily cost exceeds $8.00, warn the user." \
  skills='["autonomous-optimization-architect"]' \
  workdir="~/.hermes/skills/devops/autonomous-optimization-architect"
```

**Hourly circuit check** (runs every hour):

```bash
cronjob action=create \
  schedule="0 * * * *" \
  name="hourly-circuit-check" \
  prompt="Run python3 circuit-guard.py --verbose. If status is 'circuit_broken', run circuit-guard.py --auto-fix and notify the user. If status is 'warning', warn the user." \
  skills='["autonomous-optimization-architect"]' \
  workdir="~/.hermes/skills/devops/autonomous-optimization-architect"
```

## 4-Phase Workflow

### Phase 1: Baseline & Boundaries

Set hard limits on how much each session/domain can spend.

```bash
# 1. Get current cost baseline (last 7 days)
python3 scripts/cost-tracker.py --days 7

# 2. Edit thresholds in references/cost-thresholds.yaml
vim references/cost-thresholds.yaml

# 3. Validate your config
python3 scripts/model-router-config.py validate

# 4. View current model setup
python3 scripts/model-router-config.py show
```

### Phase 2: Failover Mapping

For each expensive model, define cheaper alternatives as fallbacks.

```bash
# 1. View suggested failover chain
python3 scripts/model-router-config.py suggest

# 2. Edit the failover chain template
vim references/failover-chain.yaml

# 3. Check that config.yaml delegation section is correct
python3 scripts/model-router-config.py show
```

### Phase 3: Shadow Deployment (Future)

A future `scripts/shadow-tester.py` will route a percentage of real traffic
to experimental models, comparing results without impacting production.
Currently, phase 3 is covered by circuit-guard.py's session analysis and
cost-tracker.py's domain-level cost monitoring, which provide the data
needed to evaluate model performance before switching.

### Phase 4: Autonomous Escalation

Set up cron jobs to automatically detect issues and switch models:

```bash
# Automated: hourly circuit check with auto-fix
python3 scripts/circuit-guard.py --auto-fix --verbose

# Manual: check what happened
python3 scripts/cost-tracker.py --days 1 --threshold 0.50

# Manual: see current routing
python3 scripts/model-router-config.py show
```

## Context-Slimming Optimization (v2.2.0)

Beyond model selection and routing, a significant cost driver is **context injection**:
SOUL.md, MEMORY, and USER PROFILE are injected into every turn of every session.
Trimming these files yields compounding savings — each byte removed saves tokens
across all future turns.

### Diagnosis Workflow

```bash
# 1. Get overall cost baseline
tokscale --no-spinner models
tokscale --no-spinner monthly

# 2. Identify cost drivers (model vs context)
# Pro tip: if flash is your most-used model but cost is still high,
# the problem is context volume, not model price.
```

### Four-Step Context Slim

1. **Config changes** — Enable `compression.enabled: true`, reduce `memory_char_limit` and `user_char_limit` by ~33%
2. **MEMORY cleanup** — Remove stale/one-time entries (completed bug fixes, past process notes, merged config changes). Target: remove 15-20% of entries.
3. **USER PROFILE compression** — Merge duplicate preference entries. Many profiles accumulate 5+ entries saying the same thing in different words.
4. **SOUL.md rewrite** — Identify redundant sections (tool tables ≈ action checklists, protocol sections repeated in different words). Rewrite to ~50% of original length.

### Expected Savings

| Area | Typical Reduction | Token Savings/Turn |
|:-----|:-----------------|:-------------------|
| SOUL.md | 40-60% (12KB → 5KB) | ~1,800 tokens |
| MEMORY | 15-25% (6KB → 4.5KB) | ~400 tokens |
| USER PROFILE | 20-30% (3KB → 2KB) | ~250 tokens |
| compression on | N/A | Variable, high in long sessions |

For a user doing 50-100 turns/day at $0.01/1M tokens (flash), context slimming saves $0.50-1.50/month directly, plus indirect savings from shorter prompts leading to shorter responses.

### Reference

- `soul-maintenance-audit` skill — for the SOUL.md trimming patterns and checklist
- See `references/context-slim-results-2026-05-07.md` for real SOUL.md compression results (43% reduction: 122→70 lines)
- See `references/context-slim-example-2026-05-01.md` for a real session before/after.

## Core Principles

1. **Every external call must have a cheaper fallback** — never let an agent
   retry an expensive model infinitely.
2. **Cost tracking before optimization** — always measure baseline costs
   before suggesting changes.
3. **Circuit breakers must be automatic** — no human-in-the-loop for cost
   protection routines.
4. **Backup before patching** — circuit-guard.py always backs up config.yaml
   before making changes.
5. **Structured parsing over string matching** — never use `"error" in content`
   for error detection; it catches tool responses, user messages, and
   delegate_task results. Always parse JSON and check structured fields
   like `data["reason"]`, `data["error"]["status_code"]`, and
   `data["finish_reason"]`.
6. **Context costs are real** — SOUL.md/MEMORY/PROFILE injection is a per-turn fixed overhead. Slim these files before reaching for model downgrades.

## Pitfalls

### Cache-hit pricing ignorance — costs overstated up to 12× (v2.6, 2026-05-10)

The cost-tracker originally used flat input pricing ($2.80/M for V4 Pro) with zero cache-hit
awareness. This overstated actual costs by roughly 12× because:

1. **DeepSeek input pricing has TWO tiers**: cache-miss (full) and cache-hit (~1/10).
   V4 Pro cache-hit is $0.0036/M vs cache-miss $0.435/M — a 120× difference.
2. **Agent conversations have 80-90% cache hit rate**: system prompts (SOUL.md/MEMORY/PROFILE)
   are hundreds of KB and reused every turn. Multi-turn conversations accumulate cached context.
   Only the newest user message is cache-miss.
3. **Pricing was also outdated**: V4 Pro has a 75% temporary discount ($0.435/$0.87 vs the
   ~$1.74/$3.48 non-discounted rate valid after 2026-05-31).

**Fix**: `cost-tracker.py` v2.6 splits input tokens into cache-hit (85%) and cache-miss (15%)
and prices each independently. The `_estimate_cost()` function auto-detects DeepSeek models
and applies `DEFAULT_CACHE_HIT_RATE = 0.85`.

**Real-world impact** (15-day window, Apr 26-May 10, calibrated against ¥600 real billing):
- Old: $119.01 total (30 days, outdated pricing + no cache) — 12× overstated
- Fixed: $82.56 total (15 days) — 1.7% error vs real $84
- Calibration: token estimation multipliers 2800/1200 (input/output per message)
- Actual daily average: $5.60 (peaks $11-18), threshold set to $8.00

See `references/deepseek-pricing-cache.md` for the full pricing research and calculation methodology.
The old `circuit-guard.py` used `'"error"' in content` to detect failures in
JSON files. This caused false positives on:
- Delegate_task tool responses with `{"error": "Subagent timed out..."}`
- User messages containing the word "error"
- Any JSON field called "error" with a non-failure value

**Fix**: Always parse JSON and check structured fields — `data["reason"]`,
`data["error"]["status_code"]`, `data.get("finish_reason")`.

### Three JSON file types, three structures
`session_*.json` and `request_dump_*.json` have completely different schemas.
Model lives at `data["model"]` in session archives but at
`data["request"]["body"]["model"]` in request dumps. Always use filename
patterns (`fpath.name.startswith("request_dump_")`) to branch.

### model.default config drift — orchestrator stuck on reasoning model (v2.8, 2026-05-14)

`model.default` must be a non-reasoning model (`deepseek-v4-flash` or `deepseek-chat`) for the orchestrator. Using `deepseek-v4-pro` as default forces every orchestrator turn through hidden CoT — adding 3-5× latency and inflating costs for pure dispatch work.

**Detection**:
```bash
grep -A1 '^model:' ~/.hermes/config.yaml | grep default
# ✓ deepseek-v4-flash or deepseek-chat
# ✗ deepseek-v4-pro (reasoning — 3-5× slower for orchestration)
```

This is distinct from worker models (kanban dispatcher overrides per-worker). The orchestrator itself should never use a reasoning model as default.

### compression.enabled relapse (v2.8, 2026-05-14)

Hermes内置压缩引擎有已知bug(tool_calls孤儿+过早触发)。04-30修复为`enabled: false`，但05-14发现又被重新启用。此配置漂移导致用户在<15%上下文使用率时被压缩。

**检测**:
```bash
grep -A2 '^compression:' ~/.hermes/config.yaml | grep enabled
# 必须: enabled: false
```
发现`true`立即改回。考虑加入BD层日常审计防止复发。

`deepseek-v4-pro` is a native reasoning model that **always engages thinking
mode** regardless of `reasoning_effort` config. For script writing, data
processing, and batch operations, it is 4-5x slower than `deepseek-v4-flash`
because:

- Generates hidden CoT tokens before every response (planning → analysis → output)
- Raw token generation is ~3x slower (quality-optimized, not throughput-optimized)
- `reasoning_effort: none` has NO effect — v4-pro server-side ignores it

**Model selection rule**: flash for scripts/code/data, pro for analysis/strategy.
Full diagnosis at `references/deepseek-model-performance.md`.

### cost-circuit-breaker.py — daily cost auto-pause (v2.7, 2026-05-10, calibrated)
Script at `~/.hermes/skills/agent-self-maintenance/scripts/cost-circuit-breaker.py` that runs hourly (cron b720fd552d39).
Threshold: $8.00/day (≈¥57 at ~7.14 rate). Calibrated against real DeepSeek billing: 15-day ¥600 ≈ $84,
avg $5.60/day, peaks ~$11-18. Auto-pauses high-consumption agent cron jobs
(session-miner 8b9037f1fbdf, 周度自优化 15d19bd7a80f) when exceeded.
Designed as no_agent script for reliability — no LLM dependency.

**CRITICAL: `~/.hermes/scripts/` sync pitfall** — Cron jobs that use relative script paths 
(e.g., `script: "cost-circuit-breaker.py"`) resolve to `~/.hermes/scripts/`, which is a 
**separate copy** from the source in `skills/.../scripts/`. When updating the source skill 
script, you MUST also copy to `~/.hermes/scripts/`:
```bash
cp ~/.hermes/skills/autonomous-ai-agents/agent-self-maintenance/scripts/cost-circuit-breaker.py \
   ~/.hermes/scripts/cost-circuit-breaker.py
```
This was discovered when cron b720fd552d39 was still running the old $2.10 threshold 
after the source had been updated to $8.00.

### Request dumps are ALL FAILED — no real usage data exists (v2.6, 2026-05-10)

Hermes only writes `request_dump_*.json` for FAILED API calls. Audit of 101 files showed:
55 `non_retryable_client_error`, 46 `max_retries_exhausted`. **Zero files with `response.usage`**.

This means ALL cost numbers from cost-tracker.py are **estimates from message_count × MSG_INPUT_TOKENS/MSG_OUTPUT_TOKENS** —
not real API billing data. The only ground truth is the provider's billing dashboard
(DeepSeek console shows actual token consumption and cost).

**Calibration workflow** (added v2.6):
1. Get real cost from provider billing dashboard (e.g., DeepSeek console shows ¥ total)
2. Run `cost-tracker.py --days N --json` and compare with real cost
3. Adjust `MSG_INPUT_TOKENS` and `MSG_OUTPUT_TOKENS` in cost-tracker.py to match
4. Current calibration (2026-05-10): 2800/1200, derived from ¥600 ÷ $10.32 = 8.1× multiplier
   over the original 350/150

**`by_source` breakdown** (added v2.6): The report now separates costs into three sources:
- `interactive` — session_*.json archives, estimated from message_count
- `cron` — *.jsonl transcripts, estimated from message_count (was $0.00 before v2.6)
- `request_dump` — failed API calls (always $0.00, kept for failure tracking)

To get real costs: check DeepSeek billing dashboard and calibrate the estimation coefficients.

### Zero token data fixed — message_count estimation with calibrated multipliers (v2.6, 2026-05-10)
Previously cost-tracker.py showed $0.00 for all sessions because Hermes session archives
don't store per-request usage data. Fixed: when usage data is absent, estimate from
`session.message_count × MSG_INPUT_TOKENS + message_count × MSG_OUTPUT_TOKENS`.
Default multipliers are 2800/1200 (calibrated against real DeepSeek billing: 8.1× over original 350/150).
See `MSG_INPUT_TOKENS` / `MSG_OUTPUT_TOKENS` constants in cost-tracker.py.

### Agent cron job cost runaway — the session-miner incident (v2.5)
The session-miner cron (8b9037f1fbdf) ran for 10.5 hours on its first execution, making
642 session_search LLM calls against 545 historical sessions. Burned ~¥15-20 before manual
intervention. Root cause: no timeout, no batch limit, no rate limiter on LLM-based cron jobs.
**Prevention**: every agent cron must have explicit limits in its prompt — time cap (≤15min),
batch cap (≤50 items), rate cap (≥3s between LLM calls). The cost-circuit-breaker provides
a second line of defense at the system level.

### Z.ai is unreachable from China — use 智谱 direct instead (v2.3.0)

The Z.ai gateway (`api.z.ai`) times out from China-based servers because
it routes through non-China infrastructure. The 智谱 direct endpoint
(`open.bigmodel.cn`) is reliable (~0.15s latency) and uses the **same**
`$GLM_API_KEY`. Never configure `api.z.ai` as a fallback provider.

### GLM model naming differs between Z.ai and 智谱 direct (v2.3.0)

Z.ai uses names like `glm-4-flash`; 智谱 direct has NO such model.
Lightweight fallback on 智谱 direct is `glm-4.5-air`.
**Always verify available models** by calling `GET /models` before
committing a provider config. Blindly copying model names across
gateways will produce 404 errors.

### Cross-provider fallback is mandatory (v2.3.0)

A same-provider fallback chain (`deepseek-v4-pro → deepseek-v4-flash`)
provides **zero protection** when the provider itself has network issues.
The `fallback_model` MUST use a different provider than the primary.
See `references/china-provider-fallbacks.md` for the full analysis.

### API key in .env but not exported in shell (v2.3.0)

Hermes loads keys from `~/.hermes/.env` internally for agent runs, but
manual shell testing with `curl` may fail because the key isn't exported.
When testing providers manually, extract the key from the file:
`grep GLM_API_KEY ~/.hermes/.env | cut -d= -f2`

## Technical Constraints

- Python 3.10+ required
- All scripts use stdlib only (json, os, datetime, pathlib, collections)
- PyYAML is optional — scripts fall back to manual YAML parsing
- All session files in ~/.hermes/sessions/ are treated as read-only
- Circuit guard auto-fix creates a .bak file before modifying config.yaml
- Session file format reference: `references/session-file-formats.md`

## Integration with Agent Self-Evolution (v2.3.1)

The `agent-self-maintenance` skill (v2.0, B+C+D+N architecture) adds a notification dispatch layer. This skill's circuit breaker events should route through that layer rather than using raw WeChat iLink:

- Circuit breaker trips (P0 events) → QQ Bot immediate via notify.py file-queue
- Cost reports (P3 events) → batch into daily digest, not individual push
- See `agent-self-maintenance` SKILL.md §N for current notification channel config

| Role | Focus | This Skill's Differentiator |
|------|-------|-----------------------------|
| Security Auditor | Vulnerabilities, secret leaks | Token consumption attacks, prompt injection costs, infinite retry loops |
| Infrastructure Ops | Server uptime, CI/CD | Third-party API availability — DeepSeek/OpenAI downtime with seamless fallback |
| Benchmarking | Load testing, DB perf | Semantic benchmarking — testing cheaper models on real Hermes task data |
| Tool Evaluator | Human-driven SaaS selection | Machine-driven continuous model A/B testing on production traffic |
