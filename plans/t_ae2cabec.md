# R5-C Strategy Plan: Chan Theory — Concentrated + Dynamic

## Task ID: t_ae2cabec
## File: /home/pebynn/quant/evo_optimizer/strategy_chan.py

---

## 1. R4-C Diagnostic Analysis

### Current State
| Metric | Value |
|--------|-------|
| ann_return | +40.02% |
| win_rate | 48.3% |
| sharpe | 0.50 |
| MDD | -18.64% |
| trades | 317 |
| profit_factor | 2.14 |

### Exit Structure Analysis
| Exit Reason | Count | % | Avg PnL |
|-------------|-------|---|---------|
| stop_loss | 155 | 48.9% | -6.83% |
| take_profit_partial | 65 | 20.5% | +18.10% |
| trailing_stop | 57 | 18.0% | +13.63% |
| max_hold | 40 | 12.6% | +8.58% |

### Root Cause Analysis
1. **Stop loss is the #1 drag** — 48.9% of exits are stop_loss, avg -6.83%.
   - With STOP_LOSS=-4%, the actual avg stop PnL is -6.83% due to gap-downs
   - Many of these would survive if stop were widened to -7%
2. **Equal weight dilution** — 8-10 positions at ~0.10-0.125 each means even a +18% partial win only contributes ~1.8% to NAV
3. **Partial close complexity** — creates tiny residual weights (0.025) that barely matter
4. **Short max hold** — 20-day cap cuts winners before they fully develop, yet avg max_hold exit is still +8.58%
5. **Entry quality** — VOL_RATIO_MIN=2.0 may be too permissive, letting in marginal setups

---

## 2. 设计方案 (方案选择 + 替代方案)

### 方案选择: R5-C Concentrated Dynamic Strategy

### 2.1 Parameter Changes (6 modificatins)

| Parameter | R4-C → R5-C | Rationale |
|-----------|-------------|-----------|
| MAX_HOLDINGS | 10→5 | Concentrate capital, amplify winners |
| MIN_HOLDINGS | 8→3 | Lower floor to match concentrated sizing |
| STOP_LOSS | -0.04→-0.07 | Reduce premature exits; avg stop currently -6.83% |
| TAKE_PROFIT | 0.12→0.15 | Higher bar = bigger winners |
| TAKE_PROFIT_PARTIAL | 0.75→REMOVED (1.0) | Full close at TP, simplify exits |
| MAX_HOLD_DAYS | 20→40 | Let winners run; max_hold avg already +8.58% |
| VOL_RATIO_MIN | 2.0→3.0 | Higher volume threshold = stronger momentum |
| OUTPUT_FILE | backtest_C_R4.csv→backtest_C_R5_v1.csv | New round separate output |

### 2.2 Exit Logic Simplification

**R4-C (complex):** stop_loss (-4%) → take_profit_partial (75% at +12%) → trailing_stop + breakeven → max_hold (20d)

**R5-C (simple):** stop_loss (-7%) → take_profit_full (+15%) → max_hold (40d)

- Remove TRAILING_STOP entirely
- Remove TAKE_PROFIT_PARTIAL logic (partial close, residual weights, breakeven flag)
- Remove peak_price tracking for trailing stop (keep for potential future use but don't act on it)
- This simplifies ~100 lines of exit logic

**Alternative considered:** Keep trailing stop but simplified. **Rejected** — the task body explicitly says "止盈全清: 去掉PARTIAL=75%, TP=+15%全清", which implies full simplification.

**Risk:** Without trailing stop, winning positions that never hit +15% will exit at max_hold. R4 max_hold exits avg +8.58% which is acceptable.

### 2.3 New Entry Filter: MA20/MA60 Golden Cross

The task says "BUY2+MA60金叉双重确认". This means: in addition to existing entry conditions, MA20 must have recently crossed above MA60.

**Design:**
- Already have MA20 and MA60 arrays in `precompute_indicators`
- Add new array `ma20_ma60_cross`: boolean, True if MA20 crossed above MA60 within last 3 bars
- Check in `check_entry_conditions`: golden cross must be active
- This is a new Condition 5 (replacing MA60 slope which becomes part of golden cross)

**Alternative:** Use MA60 slope > 0 AND golden cross separately. **Decision:** Golden cross (MA20 > MA60 for N days post-cross) implies trend is established, so MA60 slope check becomes redundant. Keep it as additional confirmation to be safe — MA60 slope > 0 + golden cross = strong trend confirmation.

### 2.4 Dynamic Position Sizing

The task says: "signal score排名前3加权(40/35/25%)"

**Design:**
- Score = vol_ratio (simplest, already computed)
- Rank selected candidates by vol_ratio descending
- Top 3 get weights [0.40, 0.35, 0.25]
- Positions 4-5 (if selected) get weight 0.0 (not allocated)
- This means effective max positions = 3 with dynamic sizing

**If N < 3 candidates** (but ≥ MIN_HOLDINGS=3):
- If exactly 3: [0.40, 0.35, 0.25]
- If < 3: equal weight (fallback — shouldn't happen with MIN_HOLDINGS=3)

**Alternative:** Normalize [0.40, 0.35, 0.25] to sum=1.0 (they already do). Only top 3 ever get capital.

**Risk:** With only 3 positions, diversification drops significantly. MDD may increase. Mitigation: the stronger entry filters (VOL_RATIO_MIN=3.0 + golden cross) should ensure quality.

### 2.5 Maintained Rules (Iron Rules)
- LEVERAGE = 1.0 (no change)
- No future function: vol_ma20 uses shift(1), entry uses next bar open
- Dual source: mysql+tdx via fallback_resolver
- MIN_MARKET_CAP = 2e9 and MIN_DAILY_AMOUNT = 20M (from R4-C, kept)
- BUY2_ACTIVE_DAYS = 12 (kept)

---

## 3. Implementation Plan

### 3.1 File Changes
Only ONE file to modify: `/home/pebynn/quant/evo_optimizer/strategy_chan.py`

Sections to change:
1. **Config section** (lines 49-77): Update parameters
2. **precompute_indicators** (line 245): Add golden cross indicator
3. **check_entry_conditions** (line 290): Add golden cross filter
4. **main()** exit logic (lines 426-558): Simplify exits
5. **main()** sizing logic (lines 626-643): Dynamic weights
6. **Final sweep** (lines 645-722): Simplify exits

### 3.2 New TDD Test File
Create: `/home/pebynn/quant/evo_optimizer/test_r5c_tdd.py`
- Based on test_r4c_tdd.py template
- Test iron rules (3 tests)
- Test parameter changes (6 tests)
- Test simplified exit logic (2 tests)
- Test golden cross filter (3 tests)
- Test dynamic sizing (3 tests)
- Test VOL_RATIO_MIN (1 test)
- **Target total: ~18 tests**

### 3.3 Deletions
- TRAILING_STOP constant (remove)
- TAKE_PROFIT_PARTIAL constant (remove) 
- CANDLE_VOL_RATIO_5D constant (unused, remove)
- Partial close logic in main() exit loop (~40 lines)
- Partial close logic in final sweep (~30 lines)
- peak_price and breakeven_stop tracking in both loops

---

## 4. 风险评估 (风险)

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| MDD increases with 3-position concentration | Medium | High | Stronger entry filters offset |
| Fewer trade opportunities (VOL 3.0 + golden cross tightens) | Medium | High | Accept — quality over quantity |
| Removing trailing stop misses late exits | Low | Medium | TP at +15% should catch most |
| MA20/MA60 cross filter too rare | Low | Medium | 3-day window provides flexibility |
| Dynamic sizing causes under-allocation | Low | Low | Normalize to 1.0 |

---

## 5. Expected Impact

Target: ann_return 40% → 70-100% (still far from 300% but progressive improvement)
- Concentrated positions: ~2x multiplier on individual winner contribution
- Wider stop: ~30 fewer stop-outs (from 155), each saving ~7% loss → +10pp net
- Higher TP + full close: winners contribute full weight instead of partial
- Longer hold: max_hold exits avg +8.58% → potentially +12-15% with 40d
- Golden cross: fewer but higher-quality entries → higher win rate on selected trades
