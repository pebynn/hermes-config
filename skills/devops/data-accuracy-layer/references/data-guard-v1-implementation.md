# Worked Example: data_guard v1 + shared_utils Consolidation

## Shared Utils Consolidation (2026-05-08)

### Before

`safe_float()` defined locally in 7 scripts:
- `collect_data.py`, `fallback_pipeline.py`, `generate_charts.py`, `generate_review.py`, `morning_brief.py`, `quant_weekly.py`, `weekly_summary.py`

`scrub_ai_vocabulary()` defined locally in 3 scripts:
- `generate_review.py`, `quant_weekly.py`, `weekly_summary.py`

Each had slightly different implementations — subtle bugs.

### After

All consolidated into one shared module:

```python
# ~/writing-data/scripts/shared/shared_utils.py
def safe_float(val, default=0.0) -> float:
    """Single implementation, used by all 7 scripts"""
    if val is None: return default
    if isinstance(val, (int, float)): return float(val)
    try: return float(str(val).strip().replace(",", ""))
    except: return default

def scrub_ai_vocabulary(content: str) -> tuple:
    """Single implementation, used by all 3 scripts"""
    patterns = [(r"首先,?|其次,?|最后,?", ""),
                (r"值得注意的是，?", ""),
                (r"总的来詛，?", ""),
                ...]
    # Apply patterns, return (cleaned, count, hits)
```

Import pattern in every consumer:
```python
from shared.shared_utils import safe_float, scrub_ai_vocabulary
# Use as before — no API change, just import location change
```

### Verification

10 function definitions removed across 7 files. Syntax verified on all. Import verified with `python3 -c "from shared.shared_utils import safe_float, scrub_ai_vocabulary; ..."`.

### ⚠️ 2026-05-09 审计: safe_float 漂移复发

新脚本绕过了 shared_utils，本地重新定义了 safe_float:
- `data_collector_seo.py` L34 — `def safe_float(v, default=0.0)`
- `wechat_auto_reply.py` L33 — `def safe_float(v, default=0.0)`

另外 `data_collector_seo.py` 还本地定义了 `def pct_change(close, prev_close)`。

**必须修复**: 删除本地定义，改为 `from shared.shared_utils import safe_float`。

**预防**: Layer 5 漂移检测应在每次 cron 运行时扫描所有脚本，发现同名函数不同实现时报警。

## Data Guard v1 (2026-05-09)

File: `~/writing-data/scripts/shared/data_guard.py` (145 lines)

Three capabilities:

1. **Field mapping**: 9 standard fields (Sina/EastMoney/AKShare unified)
2. **Value range validation**: 5 rules (涨跌幅±21%, 换手率0-100%, etc.)
3. **Audit logging**: Every data access recorded to `~/writing-data/logs/data_guard.log`

### Entry points

```python
# In collect_data.py — sector flow goes through guard
from shared.data_guard import sector_flow
df, errors = sector_flow(source='eastmoney')

# In generate_charts.py — K-line data goes through guard
from shared.data_guard import kline_data
df, errors = kline_data("sh000001", source="akshare")
```

### Observation Period

Data guard v1 has a 7-day observation period (WAIT stage in pipeline pipe-data-guard). After 7 days, a verification script checks the audit log for errors. If zero errors → old direct API paths can be removed.

Full pipeline: `pipe-data-guard` in pipelines.json (4 stages: audit → build → integrate → WAIT 7d → verify → L3 cleanup decision).
