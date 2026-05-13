# R13-B Strategy Optimization Plan

**Task**: t_96b5ec8e
**Date**: 2026-05-13
**File**: strategy_reversal_B.py

## 设计方案 (Design Decision)

### 方案选择: R9-B基线回退 + 2项定向探索

R12-B表现严重退化 (8.50% ann vs R9-B 56.31% ann)，R10-R12的4层累积改动全部为负贡献。
本次R13-B采取**最小化差异策略**：从R9-B最佳基线出发，仅做2项定向微调。

### 替代方案 (Considered & Rejected)
- **方案B: 仅改MARKET_TIMING和SECTOR** → 拒绝，R10的STOP_LOSS/TP2/权重改动也是退化原因
- **方案C: 新参数网格搜索** → 拒绝，R12已证明大范围改动有害

### 风险
- R9-B有-14.89% MDD，回退到R9基线意味着承受更大回撤
- SECTOR_MAX_POSITIONS=0 (unlimited) 可能导致行业集中风险
- ATR_STOP_MULT=0 移除仓位风控，单票风险上升

---

## 参数变更清单 (12项)

### R9-B基线恢复 (10项 REVERT)
| # | 参数 | R12-B → R13-B | 说明 |
|---|------|--------------|------|
| 1 | STOP_LOSS | -0.08 → **-0.12** | R9基线，虽0次止损退出但回测最高 |
| 2 | TP2_FULL_PCT | 0.22 → **0.18** | R9基线 |
| 3 | MAX_CAPITAL_PER_STOCK | 500000 → **300000** | R9基线，恢复分散化 |
| 4 | MARKET_TIMING_MODE | "hybrid" → **"ma_cross"** | hybrid被R12证明有害 |
| 5 | SECTOR_MAX_POSITIONS | 4 → **0** | R9无限=最高年化 |
| 6 | DECLINE_WEIGHT | 0.35 → **0.40** | R9基线 |
| 7 | RSI_WEIGHT | 0.25 → **0.30** | R9基线 |
| 8 | VOL_WEIGHT | 0.20 → **0.30** | R9基线 |
| 9 | MOM_WEIGHT | 0.20 → **0.0** | R9无动量权重 |
| 10 | ATR_STOP_MULT | 2.0 → **0.0** | R9无ATR仓位控制 |

### 定向探索 (2项 EXPLORE)
| # | 参数 | R9-B → R13-B | 说明 |
|---|------|-------------|------|
| 11 | TP1_HALF_PCT | 0.08 → **0.10** | 增加单笔盈利但不显著减少触发次数 |
| 12 | TRAILING_STOP_PCT | -0.05 → **-0.04** | 更快锁定利润 |

### 保持不变的参数 (R9=R12)
- MAX_POSITIONS = 8 (R9=R12一致)
- MOM_20D_MIN = 0.05 (R9=5%, R12恢复到此值)
- LEVERAGE = 1.0 (铁律)
- SECTOR_HEAT_HARD_FILTER = 0.65
- DECLINE_PREFILTER = -0.03
- DECLINE_QUANTILE = 0.18
- VOL_RATIO_MIN = 1.0
- REBALANCE_DAYS = 3
- TIME_STOP_DAYS = 5
- FUNDAMENTAL_FILTER_ENABLED = True (R5/R9已启用)
- MARKET_TIMING_ENABLED = True
- MOMENTUM_FILTER_ENABLED = True
- VOLUME_CONFIRM_ENABLED = True
- MARKET_CAP_FILTER_ENABLED = True

---

## 实施步骤

1. TDD: 编写 test_strategy_reversal_B.py 覆盖所有12项参数断言
2. 修改 strategy_reversal_B.py 的12个参数
3. 更新文件头docstring为R13-B
4. 更新 print 输出中的策略名称
5. 运行测试 → GREEN
6. 运行回测 (--source sina)
7. 代码审查自检

## TDD测试清单 (12项参数断言)
1. test_leverage_is_1 → LEVERAGE == 1.0
2. test_stop_loss_r9_baseline → STOP_LOSS == -0.12
3. test_tp1_explore_10pct → TP1_HALF_PCT == 0.10
4. test_tp2_r9_baseline → TP2_FULL_PCT == 0.18
5. test_trailing_explore_minus_4pct → TRAILING_STOP_PCT == -0.04
6. test_market_timing_ma_cross → MARKET_TIMING_MODE == "ma_cross"
7. test_sector_max_positions_unlimited → SECTOR_MAX_POSITIONS == 0
8. test_max_capital_per_stock_300k → MAX_CAPITAL_PER_STOCK == 300_000
9. test_scoring_weights_r9 → DECLINE=0.40, RSI=0.30, VOL=0.30
10. test_mom_weight_zero → MOM_WEIGHT == 0.0
11. test_atr_stop_mult_zero → ATR_STOP_MULT == 0.0
12. test_no_future_functions → 无未来函数
13. test_sector_heat_hard_filter → SECTOR_HEAT_HARD_FILTER == 0.65

### TDD测试详细规格
```python
# test_strategy_reversal_B.py
# 从 strategy_reversal_B 导入所有需要验证的参数
from strategy_reversal_B import (
    LEVERAGE, STOP_LOSS, TP1_HALF_PCT, TP2_FULL_PCT, TRAILING_STOP_PCT,
    MARKET_TIMING_MODE, SECTOR_MAX_POSITIONS, MAX_CAPITAL_PER_STOCK,
    DECLINE_WEIGHT, RSI_WEIGHT, VOL_WEIGHT, MOM_WEIGHT, ATR_STOP_MULT,
    MOM_20D_MIN, SECTOR_HEAT_HARD_FILTER, MAX_POSITIONS,
    FUNDAMENTAL_FILTER_ENABLED, MARKET_TIMING_ENABLED,
    MOMENTUM_FILTER_ENABLED, VOLUME_CONFIRM_ENABLED,
    MARKET_CAP_FILTER_ENABLED, OUTPUT_FILE,
)
```

### 评分权重逻辑验证
R9-B评分: composite = z_decline*0.40 + z_rsi*0.30 + z_vol*0.30 (无 mom)
R12-B评分: composite = (z_decline*0.35 + z_rsi*0.25 + z_vol*0.20 + z_mom*0.20) / total_weight
R13-B评分: 恢复R9-B (MOM_WEIGHT=0.0 时 has_mom=False 跳过动量项)

### ATR仓位控制验证
R12: ATR_STOP_MULT=2.0 → 动态调整仓位 (ATR风险预算)
R13: ATR_STOP_MULT=0.0 → 跳过ATR仓位调整 (if ATR_STOP_MULT > 0 不触发)

## 验证计划
1. `python3 -m pytest test_strategy_reversal_B.py -v` → all GREEN
2. `python strategy_reversal_B.py --source sina` → 回测运行成功
3. 检查 backtest_B.csv, backtest_B_trades.csv, backtest_B_nav.csv 产出
4. 检查 BACKTEST_SUMMARY 行输出
5. Confirm print header shows "Strategy B-R13" not "B-R12"

## 潜在问题
- MOM_WEIGHT=0.0 会导致 total_weight 不加 MOM_WEIGHT，代码中 `if has_mom:` 分支会跳过，不影响
- SECTOR_MAX_POSITIONS=0 跳过行业上限检查，execute_entry和select_signals两处均已保护 `if SECTOR_MAX_POSITIONS > 0`
- MARKET_TIMING_MODE="ma_cross" 时 ma20_slope_5d 仍会被计算但不会使用，无副作用
