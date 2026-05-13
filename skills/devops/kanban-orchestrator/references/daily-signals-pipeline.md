# Daily Signals Pipeline with Cross-Validation (2026-05-13)

Proven pattern for generating daily A-share trading signals from multiple strategies with cross-validation and QQ Bot delivery.

## Architecture

```
Cron (16:10) → daily_signals.py → signals_$(date).json → send_signals_qq.py → QQ Bot
                   │                       │
                   ▼                       ▼
           MySQL kline table        ~/quant/signals/
           (5310 stocks)           (historical archive)
```

## Cron Setup

```bash
# Schedule: 16:10 on trading days (data pull at 15:30, 40min for completion)
cronjob: 10 16 * * 1-5
script: run_daily_signals.sh
no_agent: true
deliver: qqbot
```

## Data Freshness Check

Before generating signals, verify today's kline data has been loaded:

```bash
COUNT=$(python3 -c "
from data_common import _get_db_engine
e = _get_db_engine()
r = e.execute('SELECT COUNT(*) FROM kline WHERE trade_date = CURDATE()').fetchone()
print(r[0] if r else 0)
")

# Require >3000 stocks (out of ~5300 total)
if [ "$COUNT" -lt 3000 ]; then
    # Retry up to 5 times at 2-minute intervals
    for i in $(seq 1 5); do sleep 120; ...
done
```

## Signal JSON Format

```json
{
  "date": "2026-05-13",
  "consensus_3": ["603738(泰晶科技)"],
  "consensus_2": ["600198(大唐电信)"],
  "strategy_A": ["301373(凌玮科技)", "..."],
  "strategy_B": ["000955(欣龙控股)", "..."],
  "strategy_C": ["600198(大唐电信)", "..."],
  "raw_A": ["301373", "..."],
  "raw_B": ["000955", "..."],
  "raw_C": ["600198", "..."]
}
```

Always include BOTH raw codes and named codes. QQ Bot uses named format; analysis tools use raw.

## Strategy Signal Logic (Lightweight, No Full Backtest)

### A: Cross-Sectional Momentum (Iter16)
- Compute 7 factors (ret_5d/20d/60d, vol_ratio, rsi_14, boll_pos, atr14_pct) for all stocks
- Filter: RSI<85, ret_60d>0, ret_5d>-3%
- Z-score normalize, weighted score ranking, Top 5

### B: Mean Reversion (R10)
- 3-day return < -2%, 5-day return < -3%
- Volume ratio > 1.2x (surge confirmation)
- 20-day volatility < 4%
- Score = |ret_3d|*10 + vol_ratio*2 - vol_20d*50, Top 5

### C: Chan Theory (R22)
- Buy2 signal: bottom fractal → pullback with volume contraction
- RSI 45-65, ret_60d > 0, price > MA20
- Score = ret_20d*10 + vol_ratio*2, Top 5

## Cross-Validation Rules

- **consensus_3**: All three strategies agree → strongest signal
- **consensus_2**: Any two agree → moderate signal
- **single**: One strategy only → weak signal, strategy-tagged

## QQ Bot Delivery

Write to `~/.hermes/notify_queue/` in JSON format:
```json
{"target": "qqbot:A88D89DDAFEE6A7ED7EB35325B1AEA12", "message": "...", "timestamp": "..."}
```

The `pipeline_runner` cron scans every 30 minutes and delivers queued messages.

## Monthly Data Source Cross-Validation

Separate cron (1st of month, 10:00) pulls Sina data for 300 random stocks and compares strategy signals vs MySQL:

```
月度交叉验证 2026-06-01
A动量: MySQL 5只 | Sina 4只 | 重叠 3只(75%)
  共同推荐: 600xxx(...), 000xxx(...)
B反转: MySQL 5只 | Sina 5只 | 重叠 4只(80%)
C缠论: MySQL 5只 | Sina 3只 | 重叠 2只(67%)
```

Overlap >70% = data sources consistent. <50% = investigate data quality issue.

## File Layout

```
~/quant/
├── daily_signals.py          # Signal generation (16s runtime)
├── send_signals_qq.py        # QQ Bot delivery via notify queue
├── monthly_xval.py           # Monthly Sina-MySQL cross-validation
├── signals/                  # Historical signal JSON archive
│   └── signals_2026-05-13.json
└── reports/                  # Cross-validation reports
    └── xval_2026-06-01.txt
```
