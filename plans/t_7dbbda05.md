# R2-B Strategy Evolution Plan

**Task**: t_7dbbda05 — B-R2-策略改进
**Created**: 2026-05-13
**Baseline**: R1-B = 38.31% annual, Sharpe 1.331, MDD -28.31%, Win 51.5%, 792 buys
**Target**: >50% annual, win rate >45%, no upper bound

---

## 1. Data-Driven Diagnosis

### 1.1 R1-B Profit/Loss Attribution

| Exit Reason | Trades | Avg PnL | Total PnL | % of Total |
|:------------|-------:|--------:|----------:|-----------:|
| rebalance_close_full | 372 | +1,955 | +727,277 | +125.7% |
| take_profit_half | 290 | +1,143 | +331,599 | +57.3% |
| stop_loss | 357 | -239 | -85,276 | -14.7% |
| trailing_stop | 13 | -8,761 | -113,897 | -19.7% |
| time_stop | 42 | -6,692 | -281,070 | -48.6% |

**Key insight**: time_stop (42 trades) and trailing_stop (13 trades) together account for -68.3% of all losses despite being only 5.1% of trades.

### 1.2 Monthly Return Decomposition

| Month | Return | Notes |
|:------|-------:|:------|
| 2025-05 | +3.20% | |
| 2025-06 | +22.17% | Peak month |
| 2025-07 | +15.18% | |
| 2025-08 | +3.64% | |
| 2025-09 | +8.27% | |
| 2025-10 | +4.44% | |
| 2025-11 | +1.80% | |
| 2025-12 | **-6.99%** | First bear — 38 stop_losses/-269K |
| 2026-01 | +16.85% | Recovery |
| 2026-02 | +7.25% | |
| 2026-03 | **-17.18%** | Worst — 42 stop_losses/-252K, 8 time_stops/-80K |
| 2026-04 | **-7.73%** | Continued decline |

Three bear months account for -31.9pp of losses. In bull months, strategy performs excellently.

### 1.3 Structural Ceiling Reality

Per diagnosis report: 1x leverage pure reversal ceiling = 50-75% annual. R1-B at 38.31% is below ceiling. Path to >50% exists via leak plugging + regime awareness.

---

## 2. Design Decisions

### 2.1 What NOT to Change (preserve winning formula)

- Pure |ret_5d| × sector_boost scoring (NOT multi-factor composite — diagnosis proves this destroys returns)
- MAX_POSITIONS = 8 (optimal balance)
- STOP_LOSS = -12% (wide stop allows bounce, proven effective)
- TAKE_PROFIT = 13% half-sell (good capture rate)
- REBALANCE_DAYS = 3 (cycle-timed)
- MOM_20D_MIN = 5% (right breadth)
- DECLINE_PREFILTER = -4%, DECLINE_QUANTILE = 0.18
- SECTOR_HEAT_HARD_FILTER = 0.55
- LEVERAGE = 1.0 (iron rule)

### 2.2 Four Targeted Changes

#### Change 1: Time Stop Reform 🔴 Highest Impact
**Problem**: 42 time_stop trades lost -281,070 total (avg -6,692). Current rule waits 3 days, then exits if ret < -3%. By day 3, decay is already severe.

**Fix**: 
- TIME_STOP_DAYS: 3 → 2
- TIME_STOP_RET_THRESHOLD: -0.03 → -0.01
- Rationale: Exit losers faster. A stock held 2 days with ret < -1% is unlikely to bounce on day 3. Estimated save: 60-70% of -281K ≈ +170K to +197K.

#### Change 2: Trailing Stop Tighten 🟡 Medium Impact
**Problem**: 13 trailing_stop trades lost -113,897 (avg -8,761). Current -6% from peak is too wide — stocks give back most gains before exit.

**Fix**:
- TRAILING_STOP_PCT: -0.06 → -0.03
- Rationale: -3% from peak captures profits faster. The -6% trail was designed for bigger trends but reversal stocks rarely trend long. Estimated save: ~50-70K.

#### Change 3: Market Regime Filter 🟡 Medium Impact
**Problem**: Strategy bleeds in bear markets (2025-12: -6.99%, 2026-03: -17.18%, 2026-04: -7.73%). No regime awareness — full exposure always.

**Fix**:
- Compute market proxy (equal-weight all-stock daily return)
- Track MA20 and MA60 of cumulative proxy
- When MA20 < MA60 (bear): reduce total exposure to 50%
- MARKET_TIMING_ENABLED = True (new flag)
- Implementation: scale target_exposure in execute_entry by market timing factor

#### Change 4: Score Decay Early Exit 🟢 Lower Impact
**Problem**: Held positions where the reversal thesis has weakened (abs(ret_5d) shrinks) are held until rebalance, accumulating time decay.

**Fix**:
- Track entry_abs_ret5d when position is opened
- Daily check: if current abs(ret_5d) < entry_abs_ret5d × 0.50, exit early
- SCORE_DECAY_RATIO = 0.50 (new parameter)
- Rationale: The reversal signal has faded — exit and free capital for fresh candidates

---

## 3. Alternative Approaches Considered

### 3.1 Weekly Confirmation (rejected for R2)
Adding ret_1w < -2% as pre-filter. While theoretically sound (multi-timeframe confirmation), it adds a filter layer. The diagnosis shows filters = reduced returns (R6-B fell from 75% to 13% with over-filtering). Reserved for R3 if R2 underperforms.

### 3.2 Sector Rotation (rejected for R2)
Dynamic sector weighting based on 20-day momentum rank. Requires significant new code, adds complexity. The current sector_boost already provides sector-aware scoring.

### 3.3 ATR-based Position Sizing (rejected for R2)
Scaling positions by inverse ATR (smaller in high-vol). The diagnosis showed ATR sizing (R10) contributed to收益塌缩 by penalizing high-vol reversal candidates. Reserved for future exploration.

---

## 4. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|:-----|:----------|:-------|:-----------|
| Overtightening time_stop kills valid bounces | Medium | -2-3pp | Use -1% not 0% threshold; still allows mild underwater holds |
| Market timing false signals | Low | -1-2pp | MA20/MA60 cross is slow — misses only prolonged bears |
| Score decay exits too early | Low | -1pp | 50% decay ratio is conservative — only kills clearly faded signals |
| Combined changes interact badly | Low | Variable | Only 4 changes, all in exit logic. Entry logic untouched. |

---

## 5. Implementation Plan

### File: `/home/pebynn/quant/backtest/strategy_reversal_R2.py`
- Copy of current `strategy_reversal.py` with modifications
- New parameters at top
- Modified `execute_exit` for time_stop
- Modified exit loop for score decay check
- New `compute_market_proxy` function
- Modified `execute_entry` for market timing scaling

### File: `/home/pebynn/quant/backtest/test_strategy_R2.py`
- TDD test cases for each change:
  1. test_time_stop_2days — verifies exit at day 2 with ret < -1%
  2. test_trailing_stop_3pct — verifies trail at -3% from peak
  3. test_market_regime_filter — verifies halved exposure in bear
  4. test_score_decay_exit — verifies early exit on faded signal

### Backtest Output: `/home/pebynn/quant/backtest/R2_backtest_*.csv`

---

## 6. Success Criteria

| Metric | R1-B Baseline | R2-B Target | Threshold |
|:-------|:-------------:|:-----------:|:---------:|
| Annual Return | 38.31% | >50% | >45% acceptable |
| Sharpe Ratio | 1.331 | >1.5 | >1.2 acceptable |
| Max Drawdown | -28.31% | >-22% | >-25% acceptable |
| Win Rate | 51.5% | >48% | >45% acceptable |
| Monthly Win Rate | 75% (9/12) | >75% | >66% acceptable |
| time_stop avg PnL | -6,692 | >-3,000 | Must improve |
| trailing_stop avg PnL | -8,761 | >-4,000 | Must improve |

---

## 7. Rollback Plan

If R2-B underperforms R1-B:
1. All changes are in NEW file — original `strategy_reversal.py` is untouched
2. Can run A/B comparison: R1 vs R2 on same data
3. If R2 < R1: disable changes one-by-one (ablation) to find culprit
4. Fallback: use R1-B as-is (38.31% is already solid)
