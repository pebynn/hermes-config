---
name: data-accuracy-layer
description: Pipeline-level data quality enforcement — field mapping, cross-validation, chart gates, content auditing. Zero API calls, pure logic layer for writing-domain + quant-domain.
domain: ops-domain
version: 1.0.0
trigger:
- recurring data accuracy bugs (涨跌幅/涨跌家数/字段映射)
- script function drift across writing and quant domains
- incomplete chart uploads to WeChat drafts
- AI generated numbers not traceable to source data
---

# Data Accuracy Layer — Pipeline Data Quality Gate

## Why This Skill Exists

Every data accuracy bug in writing+quant domains follows the same pattern: some script defines its own field mapping, trusts a value without checking, or proceeds with incomplete data. **All previous fixes targeted symptoms, not structure.**

This skill defines a shared `data_guard.py` module that enforces data quality at every pipeline entry point. Zero API calls — all operations are pure logic (string/JSON/math comparisons).

## Architecture

```
                           ┌─ data_guard.py ─────────────────────────────┐
                           │                                              │
 data_source_1 ──┐         │  Layer 1: 字段映射(唯一事实来源)              │
 data_source_2 ──┼─cross──→│  Layer 2: 多源交叉验证(采集时)                │──→ MySQL/缓存
 data_source_3 ──┘         │  Layer 3: 图表质量门禁(生成后)                │──→ 不达标=停
                           │  Layer 4: 内容交叉验证(写文章时)              │──→ 数字追溯
                           │  Layer 5: 函数漂移检测(启动时)                │──→ 发现即警告
                           └──────────────────────────────────────────────┘
```

## Layer 1: Field Mapping (Single Source of Truth)

Every field mapping for every data source is defined in ONE place. Any script that defines its own mapping triggers Drift Detection.

```python
# data_guard.py — 全管线唯一定义处
SINA_PARTS = {
    "open": 1, "prev_close": 2, "close": 3,
    "high": 4, "low": 5, "volume": 8, "amount": 9,
}
# ⚠️ parts[9] = 成交额(元)！换算为亿必须 /1e8，不是 /10000
# ⚠️ parts[1] = 今开，不是收盘/当前价！

# 美股全球指数 gb_xxx 格式完全不同:
SINA_GLOBAL_PARTS = {
    "close": 1,            # 当前价(盘后最新)
    # ⚠️ parts[2] 是盘后近似涨跌幅，勿用！DJI: parts[2]=0.02 但真实=-1.79%
    # ⚠️ parts[8] 是昨收，不是52周最高！
    "prev_close": 8,       # 昨收价（非52周最高）
    # 涨跌幅必须用 calc_change_pct(parts[1], parts[8])，无直接字段
    "change_amount_after": 4,  # 盘后变动额(当前价-收盘价)
    "open": 5, "high": 6, "low": 7,
    "52w_low_or_other": 9,  # 含义待确认，不是52周最低
}

# A50期货 hf_CHA50CFD 格式:
SINA_FUTURES_PARTS = {
    "close": 0, "open": 7, "prev_close": 8,
    "high": 4, "low": 5,
    # 涨跌幅需手动算: (close - prev_close) / prev_close * 100
}

# 恒生指数 int_hangseng 格式(仅4字段):
SINA_HSI_PARTS = {
    "close": 1, "change_amount": 2, "change_pct": 3,
}

EASTMONEY_PUSH2 = {
    "latest_price": "f43",
    "change_pct": "f170",     # ×100 需归一化
}
STOCK_SDK = {
    "quote_price": "latest_price",
    "change_ratio": "change_ratio",  # ×100
}
```

**⚠️ 2026-05-09 审计发现的已知映射错误**:
- `fallback_pipeline.py` fields[1]标为"当前价"实为今开，fields[3]标为"今开"实为收盘
- `data_collector_seo.py` parts[9]/10000 得万元不是亿元(应为/1e8)
- `morning_brief.py` Sina美股parts[2]取涨跌幅错误（parts[2]是盘后近似值，DJI真实-1.79%但parts[2]=0.02）。已修正为 calc_change_pct(parts[1], parts[8])
- 2026-05-09审计: 新增 calc_change_pct() 到 shared_utils.py，全管线16处自行计算替换为统一函数

## Layer 2: Cross-Validation at Data Ingestion

Not "A vs B then store." Three checks:

1. **Value range check** — reject impossible values (close=0, change_pct>20%)
2. **Multi-source consensus** — compare 2+ sources, flag diff > threshold
3. **Self-consistency check** — up+down+flat ≈ 5000, volume>0 for trading days

```python
def validate_data(data: dict) -> dict:
    """Returns {pass: bool, blocked: bool, issues: [str]}"""
    
    # Range check: indices
    for idx_name, idx in data["market"].items():
        close = idx.get("close", 0)
        if close < 2000 or close > 10000:
            return {"pass": False, "blocked": True,
                    "issues": [f"{idx_name}.close={close} out of range"]}
        chg = idx.get("change_pct", 0)
        if abs(chg) > 20:   # A股指数涨跌幅不会超过10%
            return {"pass": False, "blocked": True,
                    "issues": [f"{idx_name}.change_pct={chg} unnormalized (÷100 needed)"]}
    
    # Self-consistency: up_down_stats
    stats = data.get("up_down_stats", {})
    total = stats.get("up", 0) + stats.get("down", 0) + stats.get("flat", 0)
    if total < 1000 or total > 6000:
        return {"pass": False, "blocked": True,
                "issues": [f"up_down_stats total={total} abnormal"]}
    
    return {"pass": True, "blocked": False, "issues": []}
```

**`blocked=True` means the pipeline stops here.** No downstream execution with bad data.

## Layer 3: Chart Quality Gate

After `generate_charts.py` runs, check that expected charts exist with valid content.

```python
EXPECTED_CHARTS = {
    "daily": ["kline.png", "sector_heatmap.png", "capital_flow.png", "market_breadth.png"],
    "weekly": ["kline.png", "sector_heatmap.png", "capital_flow.png", "market_breadth.png",
               "volume_compare.png", "sector_rotation.png"],
    "fallback": ["kline.png", "market_breadth.png", "board_ladder.png", "sector_distribution.png"],
}

def validate_charts(chart_dir: str, draft_type: str = "daily") -> dict:
    """Returns {pass: bool, blocked: bool, present: [str], missing: [str]}"""
    expected = EXPECTED_CHARTS.get(draft_type, EXPECTED_CHARTS["daily"])
    present = []
    missing = []
    for name in expected:
        path = Path(chart_dir) / name
        if path.exists() and path.stat().st_size > 1024:
            present.append(name)
        else:
            missing.append(name)
    return {
        "pass": len(present) >= len(expected),
        "blocked": len(present) < 4,  # hard minimum: 4 charts
        "present": present,
        "missing": missing,
    }
```

## Layer 4: Content Cross-Validation at Writing

**The fix for "AI fabricated numbers":** every number in the article must trace to a value in `all_data.json`.

```python
def cross_validate_content(article_text: str, data: dict) -> dict:
    """
    Extract all numbers from article, match against source data.
    Unmatched numbers = potentially fabricated = blocked.
    """
    numbers = re.findall(r'\d+[\.\d]*', article_text)
    # Flatten all numeric values from data dict
    valid_values = set()
    def _collect(v):
        if isinstance(v, (int, float)) and v != 0:
            valid_values.add(str(v))
        elif isinstance(v, dict):
            for _v in v.values(): _collect(_v)
        elif isinstance(v, (list, tuple)):
            for _v in v: _collect(_v)
    _collect(data)
    
    unmatched = [n for n in numbers if n not in valid_values]
    # Allow ~20% unmatched (rounding, formatting differences)
    threshold = len(numbers) * 0.2
    return {
        "pass": len(unmatched) <= threshold,
        "blocked": len(unmatched) > threshold,
        "total": len(numbers),
        "unmatched": len(unmatched),
        "unmatched_examples": unmatched[:5],
    }
```

## Layer 5: Function Drift Detection

Scan all scripts in both domains for same-named functions with different implementations.

**Key improvement (2026-05-11):** Not all drift is bad. Entry functions (`main`, `run`, `test_main`) naturally differ across scripts. Use `ENTRY_FUNCTION_EXCLUDE` set to filter these out. Use baseline-aware alerting — only alarm when drift count grows >30% vs previously established baseline, preventing false alarms from legitimate function differentiation.

```python
ENTRY_FUNCTION_EXCLUDE = {"main", "run", "test_main"}
# Baseline file: ~/.hermes/cache/drift_baseline.json
# Alert threshold: max(baseline_count * 1.3, baseline_count + 3)
```

Full implementation and rationale: `references/drift-detection-exclusion-pattern.md`

```python
import ast, hashlib

SCAN_DIRS = [
    "~/writing-data/scripts/",
    "~/quant/",
]

def detect_drift() -> list:
    """Returns list of {func_name, scripts: [{path, hash}], diff: <impl>}"""
    funcs = {}  # name -> [{path, hash, source}]
    for d in SCAN_DIRS:
        for f in Path(d).expanduser().glob("*.py"):
            tree = ast.parse(f.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    source = ast.unparse(node)
                    h = hashlib.md5(source.encode()).hexdigest()
                    funcs.setdefault(node.name, []).append({
                        "path": str(f), "hash": h, "source": source[:80]
                    })
    drift = []
    for name, instances in funcs.items():
        if name.startswith("_"):
            continue
        hashes = set(i["hash"] for i in instances)
        if len(hashes) > 1 and len(instances) > 1:
            drift.append({
                "func_name": name,
                "scripts": [i["path"] for i in instances],
                "count": len(instances),
            })
    return drift
```

## Deployment

```
~/writing-data/shared/
└── data_guard.py      # ~400 lines, pure Python stdlib
```

Each pipeline entry point adds 3-5 lines:

```python
from shared.data_guard import validate_data, validate_charts, cross_validate_content

# In collect_data.py:
gate = validate_data(data)
if gate["blocked"]:
    data["_meta"]["blocked"] = True
    json.dump(data, f)
    sys.exit(1)

# In publish_draft.py:
gate = validate_charts(chart_dir, draft_type)
if gate["blocked"]:
    print(f"CHART GATE BLOCKED: missing {gate['missing']}")
    sys.exit(1)

# In generate_review.py:
gate = cross_validate_content(draft, data)
if gate["blocked"]:
    print(f"CONTENT GATE BLOCKED: {gate['unmatched']}/{gate['total']} numbers untraceable")
    sys.exit(1)
```

## Affected Scripts

| Script | Gate | Lines added |
|:--|:--|:--:|
| collect_data.py | Layer 2 (validate_data) | +3 |
| generate_charts.py | Layer 3 (validate_charts) | +5 |
| generate_review.py | Layer 4 (cross_validate_content) | +5 |
| weekly_summary.py | Layer 4 (cross_validate_content) | +5 |
| publish_draft.py | Layer 3 (chart gate) | +5 |
| fallback_pipeline.py | Layer 2 (validate_data) | +3 |
| daily_kline_update.py | Layer 1 (share field maps) | +2 |

All other scripts benefit from Layer 5 (drift detection) without any code change.

## Why This Solves the Recurring Problem

| What went wrong before | How Layer N prevents it |\n|:--|:--|\n| Sina parts[1] mapped to close instead of open → all data wrong | Layer 1: field mapping in ONE place, drift detection catches copy |\n| `int(lu*28)` fabricated 2772/500 → 真实 3513/1831/161 | Layer 4: number 2772 can't be found in all_data.json → blocked |\n| data_completeness=True but capital_flow={} | Layer 2: value range check blocks empty data |\n| chart uploaded 0/4 because markdown missing image refs | Layer 3: <4 charts = blocked |\n| 3 copies of scrub_ai_vocabulary, all different | Layer 5: auto-detected on every startup |\n| Fallback pipeline repeated same data_completeness bug | Layer 5: same function name, different impl → flagged |\n| **2026-05-09**: safe_float drifted again in 2 new scripts (data_collector_seo.py, wechat_auto_reply.py) | Layer 5: would catch on next scan. **New scripts must import from shared, never redefine.** |\n| **2026-05-09**: data_collector_seo.py parts[9]/10000 instead of /1e8 → turnover off by 10000x | Layer 1: if SINA_PARTS[\"amount\"] mapping was actually used by all scripts, this wouldn't happen |\n| **2026-05-09**: 16 places inline-calc change_pct → unified to calc_change_pct() in shared_utils.py | Layer 5: drift detector would find `(close-prev)/prev*100` pattern. calc_change_pct() is now the ONLY way |\n| **2026-05-09**: morning_brief.py Sina US parts[2]=0.02 as change_pct (real=-1.79%) | Layer 1: SINA_GLOBAL_PARTS now marks parts[2] as unreliable, requires calc_change_pct(parts[1], parts[8]) |

## Cross-Reference: script-contract-layer

data-accuracy-layer enforces **data quality** within each script (field mapping correctness, cross-validation at ingress, chart gates, content audit).

script-contract-layer enforces **code quality** between scripts (explicit dependency declarations, Protocol-based interface contracts, versioned module boundaries, drift detection at startup).

Together they form two layers of pipeline integrity:
```
Layer 7: Role Chain + Reviewer     ← 内容质量（AI味/合规/格式审查）
Layer 6: quality_score.py          ← 自动评分（数据准确+AI味+合规+格式）
Layer 5: data-accuracy-layer       ← 数据质量（intra-script correctness）
Layer 4: Content cross-validation
Layer 3: Chart quality gate
Layer 2: Cross-validation at ingestion
Layer 1: Field mapping (single source of truth)
```

### Layer 6: quality_score.py — 自动质量评分

`~/.hermes/scripts/quality_score.py` 在子代理产出后自动评分：

```bash
python3 ~/.hermes/scripts/quality_score.py --output "..." --goal "..." --domain writing
```

四维评分: 数据准确(40) + AI味(20) + 合规(20) + 格式(20)。≥70且无硬伤→PASS，否则→FAIL触发Reviewer复核。

### Layer 7: Role Chain + Reviewer — 内容质量审查

`~/.hermes/scripts/role_chain.py` 强制执行高风险任务的多角色审查链。Reviewer是独立agent，不参与创作，对照门禁逐项检查。Reviewer FAIL → 发布管道阻断，不可跳过。

详解见 `subagent-delegation-protocol` skill 的 "Role Chain" 章节。

The function drift detector (Layer 5) is the runtime safety net; script-contract-layer is the design-time prevention.

## Reference Files

- `references/drift-detection-baseline.md` — Baseline-aware drift detection pattern: eliminate false alarms by establishing a baseline and only alerting on >30% growth. Replaced daily error-status cron with stable exit 0.

- `a-share-content-automation` — Writing pipeline skill (hosts the full audit at `references/pipeline-root-cause-audit-2026-05-08.md`)
- `cron-job-failure-diagnosis` — Cron no_agent=True pattern for script-only crons
- `script-contract-layer` — Complementary skill: inter-script contract enforcement

### Support Files

| File | Purpose |
|:--|:--|
| `references/drift-detection-exclusion-pattern.md` | Two-part fix: ENTRY_FUNCTION_EXCLUDE + baseline-aware alerting (2026-05-11) | for auditing MySQL stock_kline.kline table — row counts, field null analysis, gap detection, coverage distribution, table sizing. Also documents MCP MySQL tool SELECT mis-classification bug and the mysql CLI bypass. |
