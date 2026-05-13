# Strategy A Optimization Plan — Task t_3dbc9f2c

## Baseline (sina 100-stock)
- NAV: 0.8631 | Annual: -14.2%
- 560 trades | WR: 38.0% | Avg PnL: -0.31% | Hold: 2.8d avg
- Exit breakdown: dropped 61% (WR 35%, avg -0.71%) | hard_stop 22% (WR 0%, avg -7.16%) | trailing_profit 16% (WR 100%, avg +10.65%)

## Root Cause Analysis
1. **#1: Tiny universe (100 stocks)** — MySQL has 5350 stocks, 1.9M rows. Cross-sectional ranking with 100 stocks produces weak signals.
2. **#2: Weak entry signals** — 65% of "dropped" exits are losses; the factor model isn't discriminating well.
3. **#3: Hard stop ratio too high** — 22% hit rate, guaranteed -7-8% losses. ATR-based stop might be too tight.
4. **#4: Low trailing capture rate** — only 16% of exits hit trailing profit, but those average +10.65%.

## Optimization Strategy (4-round iterative)

### Round 1: Data Expansion (Quick Win)
- Switch to MySQL data source (5350 stocks vs 100)
- Expect: better cross-sectional ranking → higher WR, more trailing profits
- Risk: runtime increases; 1.9M rows

### Round 2: Factor & Filter Tuning
- Adjust factor weights based on IC analysis
- Add quality filters: stronger momentum threshold, volume confirmation
- Reduce MAX_RSI_ENTRY from 85 → 75 (avoid overbought entries)
- Increase MIN_RET_60D from 0.0 → 0.05 (only enter stocks with positive medium-term momentum)

### Round 3: Risk Control Iteration
- Current: HARD_STOP=8%, ATR_STOP_MULT=2.0
- Test HARD_STOP=10% (wider stop for volatile stocks)
- Test ATR_STOP_MULT=2.5-3.0
- Adjust TRAILING_ACTIVATE / TRAILING_DISTANCE
- Consider dynamic position sizing

### Round 4: Signal Refinement
- Add new factors: sector momentum, relative strength vs index
- Cooldown tuning
- Entry timing optimization (delay 0-1 days for confirmation)

## Parameter Space to Search
| Parameter | Baseline | Range | Direction |
|-----------|----------|-------|-----------|
| TOP_N | 5 | 3-8 | Higher = more diversification |
| N_DROP | 3 | 1-TOP_N | Lower = hold winners longer |
| HARD_STOP | 0.08 | 0.06-0.15 | Higher = fewer stop-outs |
| ATR_STOP_MULT | 2.0 | 2.0-4.0 | Higher = wider stops |
| TRAILING_ACTIVATE | 0.12 | 0.08-0.20 | Lower = activate earlier |
| TRAILING_DISTANCE | 0.06 | 0.03-0.10 | Lower = tighter trail |
| MAX_RSI_ENTRY | 85 | 65-85 | Lower = avoid overbought |
| MIN_RET_60D | 0.0 | 0.0-0.10 | Higher = quality filter |
| MIN_RET_5D | -0.05 | -0.10-0.0 | Tune pullback entry |
| COOLDOWN_DAYS | 3 | 1-10 | Tune re-entry speed |

## Target
- Annual return: 300% (NAV ~3.93 after 242 days)
- Win rate: 45-55%
- LEVERAGE: 1.0

## Verification
Each round: backtest → analyze → compare to baseline → tune params → repeat
