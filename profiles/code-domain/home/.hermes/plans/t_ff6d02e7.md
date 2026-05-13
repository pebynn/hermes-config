# R2-B Strategy Optimization Plan

**Task**: t_ff6d02e7
**Date**: 2026-05-13
**Target**: Close the 237.64% gap to 300% annual return (R1: 62.36%)
**Iron Rules**: LEVERAGE=1.0, no future functions, OUTPUT_FILE=backtest_B.csv, fallback_resolver.load_kline()

---

## 1. Structural Analysis of R1

### 1.1 Critical Bug: HOLD_WINNERS never applied
- Line 84: `HOLD_WINNERS = True` declared
- Lines 488-502: `do_rebalance` block closes ALL positions unconditionally
- **Result**: Winners that should compound across cycles are wiped every 3 days
- **Fix**: During rebalance, skip positions where `ret >= WINNER_THRESHOLD`

### 1.2 Dead Code
- `TREND_SCORE_ENABLED = True` — no trend scoring function exists, never called
- `RSI_THRESHOLD = 40` — RSI computed but never used as entry gate
- `MARKET_RET_FLOOR = -0.04` — "computed but NOT used"
- `ATR_STOP_MULT = 0.0` — effectively disabled

### 1.3 Overly Wide Entry Pool
- DECLINE_PREFILTER=-0.03: ~82% of A-shares typically above -3% 5d return
- DECLINE_QUANTILE=0.18: takes bottom 18% of that already-wide pool
- Result: 2051 trades in 12 months = ~170/month = ~8/day (too many low-conviction entries)

### 1.4 Premature Profit Taking
- TAKE_PROFIT=0.10: exits half position at +10%, limiting upside
- Combined with 3-day rebalance that wipes the remaining half

---

## 2. R2 Design: "质变而非量变" (Quality over Quantity)

### Strategy Philosophy
R2 shifts from "wide pool, fast cycle, early exit" to **"deep filter, long hold, let winners run"**.
Fewer, higher-conviction entries held longer with compounding across cycles.

### 2.1 Entry Tightening (reduce noise → increase per-trade return)

| Parameter | R1 | R2 | Rationale |
|-----------|----|----|-----------|
| DECLINE_PREFILTER | -0.03 | **-0.07** | Only stocks that dropped ≥7% in 5 days (deep reversals) |
| DECLINE_QUANTILE | 0.18 | **0.05** | Bottom 5% of remaining pool (highest conviction) |
| RSI gate (NEW) | (unused) | **RSI < 35** | Oversold confirmation — actual entry gate |
| Volume gate (NEW) | (unused) | **vol_ratio > 1.5** | High relative volume on entry day (capitulation) |
| SECTOR_HEAT_HARD_FILTER | 0.50 | **0.65** | Tighter sector gate |

### 2.2 Holding & Rebalance (structural fix)

| Parameter | R1 | R2 | Rationale |
|-----------|----|----|-----------|
| REBALANCE_DAYS | 3 | **7** | Weekly cycle, aligns with HOLD_WINNERS |
| HOLD_WINNERS | (bug: never applied) | **Actually implemented** | Winners stay across cycles |
| WINNER_THRESHOLD | 0.0 | **0.03** | Only hold positions up ≥3% |
| KEEP_LOSERS | False | **False** | Still dump losers |

### 2.3 Exit Optimization (let winners compound)

| Parameter | R1 | R2 | Rationale |
|-----------|----|----|-----------|
| TAKE_PROFIT | 0.10 | **0.20** | Half exit at +20% (was +10%) |
| TRAILING_STOP_PCT | -0.06 | **-0.05** | Tighter trail on remaining half |
| TIME_STOP_DAYS | 3 | **5** | Longer runway |
| TIME_STOP_RET_THRESHOLD | -0.03 | **-0.05** | Only kill deep time-stop losers |
| STOP_LOSS | -0.08 | **-0.08** | Keep unchanged |

### 2.4 Position Sizing

| Parameter | R1 | R2 | Rationale |
|-----------|----|----|-----------|
| MAX_POSITIONS | 15 | **8** | Concentrated bets |
| MAX_CAPITAL_PER_STOCK | 300,000 | **300,000** | Keep |
| DYNAMIC_SIZING | True | **True** | Keep, weights tighten with fewer positions |

### 2.5 Sector Heat

| Parameter | R1 | R2 | Rationale |
|-----------|----|----|-----------|
| SECTOR_HEAT_MIN | 0.5 | **0.6** | Narrower discrimination range |
| SECTOR_HEAT_MAX | 1.5 | **1.4** | Cap upside sector influence |

---

## 3. Implementation Changes

### 3.1 select_signals() — add RSI + volume gates
```python
# NEW: RSI oversold confirmation
if "rsi" in candidates.columns:
    candidates = candidates[candidates["rsi"] < RSI_THRESHOLD]

# NEW: Volume confirmation (high relative volume = capitulation)
if "vol_ratio" in candidates.columns:
    candidates = candidates[candidates["vol_ratio"] > VOL_RATIO_MIN]
```

### 3.2 execute_rebalance() — implement HOLD_WINNERS
```python
# R2: Keep winners across rebalance cycles
if do_rebalance:
    to_close = []
    for code in list(bt.portfolio.keys()):
        # ... get price ...
        ret = (price / entry_price) - 1
        if HOLD_WINNERS and ret >= WINNER_THRESHOLD:
            continue  # ← keep winners
        to_close.append((code, price, "rebalance_close_full"))
```

### 3.3 New constants
```python
RSI_THRESHOLD = 35        # R2: oversold gate (was unused at 40)
VOL_RATIO_MIN = 1.5       # R2: high relative volume
```

---

## 4. Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Signal scarcity | High — tight filters may produce 0 signals | Min(5) candidate floor preserved; if <3 signals on rebalance day, skip entry |
| Whipsaw with HOLD_WINNERS | Medium — winners may reverse | WINNER_THRESHOLD=0.03 keeps only clear winners; trailing stop still active on held positions |
| Over-concentration | Medium — 8 positions | MAX_CAPITAL_PER_STOCK cap prevents single-stock blowup |
| Missing opportunities in hot sectors | Low — wider rebalance window (7d) means more accumulation |

---

## 5. Alternative Designs Considered

1. **Add trend filter (ma20 > ma60)**: Rejected — reversal strategy by definition buys against trend; trend filter would block most signals
2. **Dynamic STOP_LOSS based on ATR**: Rejected — ATR_STOP_MULT=0.0 already; fixed 8% stop is simpler and proven
3. **Add take-profit tier 2 (full exit at +40%)**: Deferred to R3 — R2 focuses on structural fixes first
4. **Keep REBALANCE_DAYS=3 but fix HOLD_WINNERS only**: Rejected — 3-day cycle with 2051 trades is the core problem; need longer hold

---

## 6. Verification Checklist

- [ ] python3 -m py_compile passes
- [ ] LEVERAGE=1.0 verified
- [ ] No future functions (all signals lagged 1d)
- [ ] OUTPUT_FILE = backtest_B.csv
- [ ] HOLD_WINNERS actually keeps winners during rebalance
- [ ] RSI < 35 gate applied in select_signals
- [ ] vol_ratio > 1.5 gate applied
- [ ] DECLINE_PREFILTER = -0.07
- [ ] TAKE_PROFIT = 0.20
- [ ] REBALANCE_DAYS = 7
