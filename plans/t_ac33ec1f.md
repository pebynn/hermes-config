# R6-C Strategy Code Optimization Plan
task: t_ac33ec1f
date: 2026-05-13
base: /home/pebynn/quant/evo_optimizer/strategy_chan.py (R5-C → R6-C)

---

## 1. Brainstorming — Design Analysis

### Context
R5-C (previous round) introduced: golden cross filter, concentrated holdings (3-5), dynamic weights (40/35/25), widened stop (-7%), raised TP (+15%), candle confirmation, extended hold (40d), volume ratio 3.0.
Results: ann_return 10.52%, win_rate 38.1%, max_drawdown -40.11%, only 63 trades, 54% stop-loss trigger rate.

Root causes identified:
1. Golden cross + MA60 slope redundancy → delayed entry → buy at local peaks
2. Volume ratio 3.0 too restrictive → only 63 candidates
3. Concentrated 3-5 holdings → amplified drawdown
4. Late entry → high stop-loss hit rate

### R6-C Change Map (6 changes)

#### Change 1: Remove golden cross filter
- **Action**: Delete GOLDEN_CROSS_WINDOW constant, delete ma20_ma60_cross from precompute_indicators, remove golden cross check from check_entry_conditions
- **Keep**: MA60 slope > 0 AND close > MA60
- **Rationale**: Task analysis shows golden cross + MA60 slope are redundant — both confirm uptrend. Golden cross introduces 3-day lag that causes buying at local peaks.
- **Alternative**: Could keep golden cross but widen window to 20 days. Rejected — task explicitly says remove.

#### Change 2: Volume ratio 3.0 → 2.0
- **Action**: VOL_RATIO_MIN = 2.0
- **Rationale**: At 3.0, 80% of candidates were eliminated (63 trades vs R4's 317). Returning to 2.0 expands the candidate pool.
- **Risk**: May include weaker momentum stocks, but offset by MA60 slope + close>MA60 filters.

#### Change 3: Holdings 3-5 → 8-10, equal weight
- **Action**: MAX_HOLDINGS = 10, MIN_HOLDINGS = 8, equal weight (1/N)
- **Remove**: DYNAMIC_WEIGHTS [0.40, 0.35, 0.25]
- **Rationale**: Concentrated positions amplified drawdown (-40.11%). Diversification across 8-10 stocks reduces single-stock risk.
- **Weight logic**: Replace dynamic weight loop with simple `eq_weight = 1.0 / len(selected)` for all selected.

#### Change 4: Stop loss -7% → -5%
- **Action**: STOP_LOSS = -0.05
- **Rationale**: Tighter stop reduces single-trade loss magnitude. R5-C's -7% allowed large losers to compound drawdown.
- **Risk**: May increase stop-loss trigger rate further. Mitigated by improved entry timing (no golden cross delay).

#### Change 5: Buy2 active window 12 → 20 days
- **Action**: BUY2_ACTIVE_DAYS = 20
- **Rationale**: Wider window allows catching buy2 signals that occur earlier, avoiding late entry at local peaks. The 12-day window previously forced entries close to signal peaks.

#### Change 6: Take profit 15% full + 8% partial at 50%
- **Action**: TAKE_PROFIT = 0.15 (keep), add TAKE_PROFIT_PARTIAL = 0.08, PARTIAL_CLOSE_FRAC = 0.50
- **Implementation design**: In the exit check loop, check partial TP (8%) BEFORE full TP (15%). When partial TP hits:
  1. Record a trade for the sold half with exit_reason="take_profit_partial", weight=pos_weight * 0.5
  2. Update position: weight = pos_weight * 0.5 (the retained half)
  3. Continue checking for full TP (15%) or stop loss (-5%) on the remaining half
- **Partial TP trade recording**: Each partial close generates 2 trades — the partial exit and later the final exit of remaining.
- **Rationale**: Lock in partial gains at 8% while letting the rest run to 15%. Reduces risk of round-trip losses.

### What R5-C features to KEEP
- Candle confirmation (MULTI_TIMEFRAME_CONFIRM=True) — not identified as regression cause
- MA60 slope filter — explicitly to be kept (task says "保留 MA60斜率>0")
- Market cap floor (MIN_MARKET_CAP=2e9, MIN_DAILY_AMOUNT=20M)
- max_hold_days = 30 (revert from R5-C's 40 to R23 baseline — matches task spirit of reverting to R4-like settings; 30d with partial TP at 8% is achievable)
- REBALANCE_INTERVAL = 7
- LEVERAGE = 1.0 (iron rule)
- No-future-function: vol_ma20.shift(1), next_i = i+1 for entry

### What R5-C features to REMOVE
- GOLDEN_CROSS_WINDOW = 3
- ma20_ma60_cross from precompute_indicators
- Golden cross check in check_entry_conditions
- DYNAMIC_WEIGHTS = [0.40, 0.35, 0.25]
- MAX_HOLD_DAYS = 40 → revert to 30

### Risks
1. **Partial TP complexity**: The exit logic becomes more complex with 2-tier TP. Risk of bugs in weight tracking. Mitigation: thorough TDD tests.
2. **More trades, more stops**: With volume ratio 2.0 + 8-10 holdings, more trades may mean more stop-loss hits. Need to verify stop-loss rate improves.
3. **Candle confirmation retained**: May filter some good entries. If R6-C results still poor, consider removing in R7-C.

---

## 2. Implementation Plan

### File changes
- Modify: `/home/pebynn/quant/evo_optimizer/strategy_chan.py` (R5-C → R6-C)
- Create: `/home/pebynn/quant/evo_optimizer/test_r6c_tdd.py`

### Config changes (section ~52-84)
```
MAX_HOLDINGS: 5 → 10
MIN_HOLDINGS: 3 → 8
STOP_LOSS: -0.07 → -0.05
TAKE_PROFIT: 0.15 (keep)
MAX_HOLD_DAYS: 40 → 30
VOL_RATIO_MIN: 3.0 → 2.0
BUY2_ACTIVE_DAYS: 12 → 20
DELETE: GOLDEN_CROSS_WINDOW = 3
DELETE: DYNAMIC_WEIGHTS = [0.40, 0.35, 0.25]
ADD: TAKE_PROFIT_PARTIAL = 0.08
ADD: PARTIAL_CLOSE_FRAC = 0.50
OUTPUT_FILE: backtest_C_R6_v1.csv
```

### precompute_indicators changes
- Remove `ma20_ma60_cross` computation block (lines 279-304)
- Remove `"ma20_ma60_cross": ma20_ma60_cross` from return dict

### check_entry_conditions changes
- Remove golden cross check (condition 2, lines 342-345)
- Renumber conditions accordingly

### Exit logic changes (main loop + final cleanup)
- Add partial TP check BEFORE full TP check
- When partial TP hits at entry_idx+la:
  - Record trade: exit_reason="take_profit_partial", weight=pos_weight * 0.5
  - Reduce position weight by 50%
  - Continue loop for remaining half
- Track a `partial_taken` flag per position to prevent double-trigger

### Position sizing changes
- Remove dynamic weight logic (lines 629-642)
- Replace with equal weight: `eq_weight = 1.0 / len(selected)`

---

## 3. TDD Test Plan

### Iron rules (3 tests — must always pass)
1. LEVERAGE = 1.0
2. vol_ma20 uses .shift(1)
3. Entry uses next_i = i + 1

### R6-C parameter tests (9 tests — RED on R5-C)
4. STOP_LOSS = -0.05
5. TAKE_PROFIT = 0.15 (kept)
6. TAKE_PROFIT_PARTIAL = 0.08 (NEW)
7. PARTIAL_CLOSE_FRAC = 0.50 (NEW)
8. GOLDEN_CROSS_WINDOW deleted (must NOT exist)
9. DYNAMIC_WEIGHTS deleted (must NOT exist)
10. MAX_HOLDINGS = 10
11. MIN_HOLDINGS = 8
12. VOL_RATIO_MIN = 2.0
13. BUY2_ACTIVE_DAYS = 20
14. MAX_HOLD_DAYS = 30
15. OUTPUT_FILE contains backtest_C_R6_v1.csv

### R6-C code structure tests (5 tests)
16. Golden cross NOT in precompute_indicators return
17. Golden cross NOT in check_entry_conditions
18. Equal weight allocation (no dynamic weights in position sizing)
19. Partial take_profit logic exists (exit_reason="take_profit_partial")
20. Partial close weight tracking

### R4-C/R5-C kept features (4 tests)
21. MIN_MARKET_CAP = 2e9
22. MIN_DAILY_AMOUNT = 20M
23. Candle confirmation constants exist
24. MA60 slope check in entry conditions

Total: 24 tests. Expected: >= 9 RED on R5-C (parameter changes).

---

## 4. Verification Plan
1. Run TDD: `python test_r6c_tdd.py` → all GREEN
2. Syntax check: `python -c "import py_compile; py_compile.compile('strategy_chan.py', doraise=True)"`
3. Backtest run: `python strategy_chan.py --source sina` (quick test)
4. Check output: verify backtest_C_R6_v1.csv exists with trades
