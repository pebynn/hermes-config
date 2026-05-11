# Worked Example: A-Share Quant Trading System Design (2026-05)

## Overview

A complete 9-lens deep research project resulting in a 4-layer signal fusion system design for A-share mid-cap quantitative trading. All 4 output files are in `~/research-skill-graph/projects/quant-system-design/`.

## Research Question

"设计完整A股量化交易系统：四层信号叠加，调研主流平台，给出可落地方案"

## Entry Points

| File | Path | Purpose |
|:----|:----|:--------|
| Executive Summary | `projects/quant-system-design/executive-summary.md` | 82 lines — core architecture, expected performance, platform benchmark, roadmap |
| Deep Dive | `projects/quant-system-design/deep-dive.md` | 573 lines — 9 lenses, full mathematical definitions, architecture pseudocode, risk framework |
| Key Players | `projects/quant-system-design/key-players.md` | 111 lines — platform/OS/literature/person/data-source reference |
| Open Questions | `projects/quant-system-design/open-questions.md` | 122 lines — risks, unknowns, decision points, next action items |

## Architecture (Summary)

```
Layer 1 — Fundamental Factors (40% weight): 15+ factors, Fama-French localized
Layer 2 — Chan Theory Structure (20%): Bi/segment/pivot auto-detection (czsc/chan.py)
Layer 3 — Volume-Price & Money Flow (20%): KAMA/POS trend + fund flow divergence
Layer 4 — Resonance Criterion (20%): Multi-period consistency + adaptive weights
```

## Parallel Burst Pattern Used

This research used 6 simultaneous web_search calls covering:
1. Platform comparison (JoinQuant/RiceQuant/BigQuant/Juejin)
2. Open-source frameworks (vnpy/backtrader/qlib)
3. Chan theory quantification (chan.py/czsc)
4. Multi-factor + technical fusion (research papers)
5. A-share quant history (evolution stages)
6. International research (multi-signal overlay)

Then 4 follow-up extracts for deeper dives.

## Key Findings

- mid-cap-multi-factor v2.1 baseline: 28.35% annualized / 1.54 Sharpe / 8.08% max drawdown
- SVM fusion of multi-factor + volume-price: +11.43% annualized improvement (Hu Xinhuan 2024)
- 东北证券 32 indicators: KAMA Sharpe 1.26, POS annualized 15.85% best
- BigQuant StockRanker + 2000+ factor factory — best architecture reference
- 中欧 三元低相关 strategy — industry best practice
- Major risk: money flow indicator shows NEGATIVE correlation with forward returns
- 缠论 quantitative performance: ZERO published backtest verification — biggest unknown
- JoinQuant strategy leaderboard top: 103% annualized / 23% drawdown (small-cap + multi-factor)

## Next Steps

P0: Install czsc → backtest Chan signals on existing 5052 kline files
P0: Test AKShare moneyflow API coverage
P1: Build 4-layer signal synthesis engine prototype
P1: Monte Carlo backtest framework (1000 runs)
