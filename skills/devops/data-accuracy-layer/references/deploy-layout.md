# data_guard.py — Deploy Layout

## File Locations

```
~/writing-data/shared/
└── data_guard.py              # ~400 lines, core module

~/.hermes/scripts/
├── data_guard_wrapper.py      # CLI wrapper for cron/terminal
└── drift_detect.py            # Standalone drift detection script

~/.hermes/scripts/drift_detect.py  → cron: 每日06:00 (3dc57f9de476)
```

## Pipeline Integration Points

| Script | Insertion | Lines added | Gate type |
|:-------|:----------|:-----------:|:----------|
| `collect_data.py` | After json.dump(), before return | +17 | validate_ingested_data(Layer2) |
| `generate_charts.py` | After logger success msg | +16 | check_chart_files(Layer3) |
| `generate_review.py` | After draft save | +17 | enforce_pipeline_gate(Layer4+5) |
| `weekly_summary.py` | After draft save, before publish | +16 | enforce_pipeline_gate(Layer4+5) |
| `publish_draft.py` | Before step3 (md→html conversion) | +17 | enforce_pipeline_gate(all layers) |

All gates use `sys.path.insert(0, ~/writing-data/shared)` + try/except ImportError for graceful degradation.

## Field Mappings (6 data sources)

Defined in data_guard.py `PART 1`:

- `SINA_INDEX` — 6 fields for hq.sinajs.cn index quotes
- `SINA_STOCK` — 10 fields for hq.sinajs.cn individual stock quotes
- `SINA_FUTURE` — 6 fields for hf_CHA50CFD futures
- `EASTMONEY_PUSH2` — 9 fields for push2.eastmoney.com
- `STOCK_SDK` — 9 fields for stock-sdk-mcp (Tencent)
- `TUSHARE` — 10 fields for tushare pro.daily()

## Value Ranges for Validation

```python
VALUE_RANGES = {
    "sh_close": (2900, 3800),
    "sz_close": (8500, 13000),
    "cy_close": (1800, 3000),
    "kc_close": (900, 1400),
    "index_change_pct": (-8, 8),
    "stock_change_pct": (-12, 12),
    "turnover_wan": (-1, 1e10),
    "limit_up_total": (0, 300),
    "limit_down_total": (0, 300),
}
```

## Expected Charts

```python
EXPECTED_CHARTS = {
    "daily": ["kline.png", "sector_heatmap.png", "capital_flow.png", "market_breadth.png"],
    "weekly": ["kline.png", "sector_heatmap.png", "capital_flow.png", "market_breadth.png",
               "volume_compare.png", "sector_rotation.png"],
    "fallback": ["kline.png", "market_breadth.png", "board_ladder.png", "sector_distribution.png"],
}
```

Minimum: ≥4 daily/weekly, ≥2 fallback. Each file must be >1KB.

## CLI Usage

```bash
# Full pipeline gate (all layers)
python3 ~/.hermes/scripts/data_guard_wrapper.py gate --date 2026-05-08 --type daily

# Data validation only
python3 ~/.hermes/scripts/data_guard_wrapper.py validate --date 2026-05-08

# Chart file check
python3 ~/.hermes/scripts/data_guard_wrapper.py charts --date 2026-05-08

# Function drift detection
python3 ~/.hermes/scripts/data_guard_wrapper.py drift
# or standalone:
python3 ~/.hermes/scripts/drift_detect.py

# Title review
python3 ~/.hermes/scripts/data_guard_wrapper.py title --date 2026-05-08
```

## audit_guard Integration

`data_guard.enforce_pipeline_gate()` imports and calls `audit_guard.audit_draft()` for 4-dimension audit:
1. Compliance (BLOCK level)
2. Data accuracy cross-validation (WARN level)
3. AI flavor detection (WARN level)
4. Format quality check (WARN level)

audit_guard.py is at `~/writing-data/scripts/audit_guard.py` (1041 lines). It is NOT duplicated — data_guard IMPORTS it.

## avoid-ai-writing Skill

The `avoid-ai-writing` skill (community, ~14KB) is installed at `~/.hermes/skills/writing/avoid-ai-writing/SKILL.md`. It defines 3-tier word lists (Tier1/2/3), structural checks, and context profiles.

The writing pipeline integrates its principles via:
- `generate_review.py` → `scrub_ai_vocabulary()` (3-tier cleaning)
- `audit_guard.py` → `check_ai_flavor()` (AI word density + structure detection)
- `weekly_summary.py` → `scrub_ai_vocabulary()` (same 3-tier)

Note: `scrub_ai_vocabulary()` exists in 3 scripts with slight differences — drift detection monitors this.

## Cron Jobs

| ID | Name | Schedule | Script |
|:---|:-----|:---------|:-------|
| 3dc57f9de476 | data-guard-drift-detect | 每日06:00 | drift_detect.py (no_agent) |

## Related Skills

- `a-share-content-automation` — Writing pipeline knowledge (partially overlaps with data-accuracy-layer for data source validation sections)
- `self-diagnosis` — Health check that verifies data_guard integration
