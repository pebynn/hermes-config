# Cost Tracker Calibration Workflow

## When to recalibrate

Recalibrate `MSG_INPUT_TOKENS` / `MSG_OUTPUT_TOKENS` in `cost-tracker.py` when:
- Provider changes pricing model (e.g., V4 Pro discount expires May 31)
- Context slimming significantly changes system prompt sizes
- Session archive format changes (affects message_count accuracy)
- Monthly, as a sanity check against billing dashboard

## Calibration steps

### 1. Get ground truth
Go to DeepSeek console → Billing → select date range → note total ¥ cost.
For other providers: check their billing dashboard.

### 2. Run cost-tracker for same period
```bash
python3 scripts/cost-tracker.py --days N --json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Estimated: \${data[\"period\"][\"total_cost\"]:.2f}')
print(f'Sessions: {data[\"period\"][\"total_sessions\"]}')
"
```

### 3. Calculate correction factor
```
correction = real_cost_usd / estimated_cost_usd
new_input_multiplier = MSG_INPUT_TOKENS * correction
new_output_multiplier = MSG_OUTPUT_TOKENS * correction
```
Round to nearest 100 for readability.

### 4. Apply
Edit `MSG_INPUT_TOKENS` and `MSG_OUTPUT_TOKENS` in cost-tracker.py.
Re-run to verify: error should be < 5%.

### 5. Update thresholds
Adjust `cost-thresholds.yaml` and `cost-circuit-breaker.py` threshold:
- `per_day_max` ≈ 3× daily average
- Circuit breaker threshold ≈ 2.5× daily average

## Current calibration (2026-05-10)

| Parameter | Value | Source |
|:----------|:------|:-------|
| Period | Apr 26 - May 10 (15 days) | — |
| Real cost | ¥600 ≈ $84.00 | DeepSeek billing dashboard |
| Initial estimate | $10.32 | cost-tracker v2.5 (350/150) |
| Correction factor | 8.14× | 84.00 / 10.32 |
| MSG_INPUT_TOKENS | 2800 | 350 × 8.14, rounded |
| MSG_OUTPUT_TOKENS | 1200 | 150 × 8.14, rounded |
| Calibrated estimate | $82.56 | 1.7% error |
| Daily avg | $5.60 | — |
| Daily peaks | $11-18 | — |
| Circuit breaker | $15.00 | 2.7× daily avg |

## Pitfalls

- Don't calibrate on short periods (1-3 days) — daily variance is high
- Don't use a single multiplier for all models — V4 Pro has discount, flash doesn't
- Recalibrate after major config changes — context slimming reduces tokens dramatically
- Check billing currency — some providers bill in CNY, others USD
