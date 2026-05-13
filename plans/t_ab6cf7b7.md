# R2-A Strategy Momentum — Implementation Plan

**Task**: t_ab6cf7b7
**Date**: 2026-05-13
**Strategy File**: /home/pebynn/quant/evo_optimizer/strategy_momentum.py
**Output File**: /home/pebynn/quant/evo_optimizer/backtest_A.csv

---

## 1. R1 Baseline Assessment

| Metric | R1 Value | Target | Gap |
|--------|----------|--------|-----|
| Annual Return | 235.67% | 300% | -64.33% |
| Sharpe | 3.43 | — | — |
| Win Rate | 51.2% | — | — |
| Max DD | -31.91% | — | — |
| Total Trades | 868 | — | — |

**#1 Problem**: hard_stop triggered on 334 trades (38.5% of exits), average PnL -6.84%.
This is the single largest drag — hard_stop is systematically killing positions
that might recover or be better managed by dynamic stops.

---

## 2. Root Cause Analysis

### 2.1 Hard Stop Pathology
- Fixed -8% stop doesn't account for stock volatility
- For a stock with 3% daily ATR, -8% is ~2.7σ — barely protective
- For a stock with 1% daily ATR, -8% is ~8σ — way too wide, capital tied up
- 334 exits at avg -6.84% means cumulative ~-22.8x (not exactly additive due to
  position sizing, but severe drag)
- These exits cluster in volatile periods where price dips before recovering

### 2.2 Trailing Stop Too Lax
- TRAILING_ACTIVATE=8% means a stock must gain >8% before trailing activates
- TRAILING_DISTANCE=4% means 4% pullback from high before exit
- Combined: stock must gain 12%+ then pull back 4% for trailing to fire
- Many profitable trades top out at 5-7% then reverse — trailing never activates

### 2.3 Factor Weights
- ret_60d at 30% dominates — 60-day lookback is slow to react
- ret_20d at 22% is underweighted — medium-term momentum is stronger in A-shares
- Shorter-term factors (ret_5d, turnover_ratio) have negligible weight

---

## 3. Design — R2 Changes

### 3.1 Remove HARD_STOP → Replace with ATR Dynamic Stop
```
HARD_STOP = 0.0  # (was 0.08) — REMOVED
```
**New mechanism**: ATR-based initial stop loss
```
NEW: ATR_INIT_STOP_MULT = 2.5
Logic: if (day_low - entry_price) / entry_price <= -ATR_INIT_STOP_MULT * entry_atr_pct
       → stop out
```
- For a stock with ATR=3%: stop at -7.5% (tighter than old -8%)
- For a stock with ATR=1%: stop at -2.5% (much tighter, protects capital)
- For a stock with ATR=5%: stop at -12.5% (looser, allows volatility)
- **Volatility-aware** — respects each stock's natural range

### 3.2 Tighter Trailing Stop
```
TRAILING_ACTIVATE = 0.05   # (was 0.08) — activate at 5% profit
TRAILING_DISTANCE = 0.03   # (was 0.04) — 3% pullback triggers exit
```
- Stock gains 5% → trailing activates → 3% pullback → exit at ~2% profit
- Captures mid-sized winners that previously fell through the cracks

### 3.3 Factor Weight Overhaul — Double ret_20d
```
ret_60d_z:      0.30 → 0.18
ret_20d_z:      0.22 → 0.40  ★ DOUBLED
ret_5d_z:       0.03 → 0.04
vol_ratio_z:    0.05 → 0.04
rsi_14_z:       0.04 → 0.03
boll_pos_z:     0.03 → 0.04
atr14_pct_z:    0.04 → 0.04
turnover_ratio_z: 0.05 → 0.05
amount_ratio_z: 0.04 → 0.04
(All normalized so sum = 1.0)
```
**Rationale**: 20-day momentum is the sweet spot for A-share rebalancing cycles.
The 60-day factor is slow to react to regime changes. Doubling ret_20d makes
the ranking more responsive to emerging trends.

### 3.4 Entry Filter Micro-adjustments
```
MAX_RSI_ENTRY: 85 → 82    # slightly more selective on overbought
MIN_RET_5D:   -0.03 → -0.02  # slightly more permissive (leaders can have pullback days)
```

### 3.5 Parameters UNCHANGED (from R1-A)
```
LEVERAGE = 1.0          # iron rule
TOP_N = 10              # R1-A already increased from 5
N_DROP = 5
ATR_STOP_MULT = 2.0     # (now used differently — may repurpose)
MIN_VOL_20D = 5e5
MIN_DAYS = 80
TC_COST = 0.001
MIN_RET_60D = 0.0
```

---

## 4. Code Changes — Specific Locations

### 4.1 Config Section (lines 15-43)
- Change HARD_STOP → 0.0 (line 22)
- Add ATR_INIT_STOP_MULT = 2.5 (after line 23)
- Change TRAILING_ACTIVATE → 0.05 (line 24)
- Change TRAILING_DISTANCE → 0.03 (line 25)
- Change MAX_RSI_ENTRY → 82 (line 30)
- Change MIN_RET_5D → -0.02 (line 32)
- Change FACTOR_WEIGHTS (lines 38-43): adjust values as per §3.3

### 4.2 Exit Logic (lines 177-211)
- Modify hard_stop block to use ATR-based stop instead:
  - Read entry_atr_pct from positions dict
  - Compute: atr_stop_price = ep * (1 - ATR_INIT_STOP_MULT * entry_atr_pct)
  - If day_low <= atr_stop_price → atr_stop_hits.add(code)
- Add atr_stop_hits to exit reasons (line 245-251 area)

### 4.3 Entry Logic (lines 286-291)
- No changes needed — entry_atr_pct already stored in position

---

## 5. Alternatives Considered

### Alt A: Keep HARD_STOP but lower to 5%
- Rejected: still one-size-fits-all, doesn't solve root cause
- Would just delay exits, not fix the problem

### Alt B: ATR trailing stop only (no initial ATR stop)
- Rejected: positions with <5% profit have zero protection
- Need initial stop for early-loss detection

### Alt C: Reduce TOP_N to 8 for concentration
- Rejected: "增大TOP_N到8" in spec was for pre-R1 baseline (TOP_N was 5)
- Current TOP_N=10 is already optimal for diversification

### Alt D: More aggressive weight overhaul (remove ret_60d entirely)
- Rejected: 60-day momentum still has predictive value
- Reducing from 30% to 18% is aggressive enough

---

## 6. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Removing HARD_STOP allows positions to fall >10% | Medium | ATR_INIT_STOP_MULT=2.5 provides volatility-aware protection |
| Tighter trailing causes premature exits | Medium | Only activates at 5% profit; 3% distance is still reasonable |
| Doubling ret_20d may cause whipsaw in sideways markets | Low | Other factors (RSI, boll_pos) provide diversification |
| ATR-based stop fails on gap-down opens | Medium | China A-shares have ±10% limit; gap-down beyond ATR stop is rare but possible |

---

## 7. Verification Plan

1. `python3 -m py_compile /home/pebynn/quant/evo_optimizer/strategy_momentum.py` — must pass
2. TDD test suite (test_strategy_momentum_r2.py) — all GREEN
3. Code review: no future functions, LEVERAGE=1.0 confirmed, no lookahead
4. Verify OUTPUT_FILE path is correct

---

## 8. Iron Rules Checklist

- [x] LEVERAGE=1.0
- [x] No future functions (use yesterday's factors for ranking)
- [x] OUTPUT_FILE = /home/pebynn/quant/evo_optimizer/backtest_A.csv
- [x] Data via fallback_resolver.load_kline()
- [x] No modification to core algorithm (ranking, NAV calculation)

---

*Design complete. Proceeding to TDD → Implementation.*
