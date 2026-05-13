# Plan: t_6c3e3bf1 — 反转策略代码优化 (300%年化自主优化)

## 目标
- 年化300%，胜率45-55%，无杠杆(LEVERAGE=1.0)
- 回测区间: 2025-05-01 → 2026-04-30
- 数据源: MySQL全A股 (~5000 stocks)
- 修改文件: `/home/pebynn/quant/strategy_reversal_opt.py`

## 设计方案

### 方案选择: 多阶段自主参数优化 + 多因子复合评分

**核心理念:** 将策略改造为自优化引擎 — 定义参数空间 → 网格搜索 → 回测 → 分析 → 缩小搜索空间 → 重复。

**替代方案评估:**
| 方案 | 思路 | 可行性 | 风险 |
|------|------|--------|------|
| A: 贝叶斯优化 | 高斯过程搜索参数 | 样本效率高但实现复杂 | 核函数选择敏感 |
| B: 遗传算法 | 种群进化 | 全局搜索强但收敛慢 | 5000股回测成本高 |
| **C: 阶段性网格搜索** | **粗→细渐进搜索** | **简单可靠，可解释** | 可能陷入局部最优 |
| D: 手动迭代 | 人工调参 | 灵活但低效 | 耗时长 |

**选择方案C:** 阶段性网格搜索 — 结合历史R9/R10最佳参数作为先验，4阶段总约50个组合，每个约30-60秒，总耗时约30-50分钟。

### 优化架构

```
Phase 1: 粗粒度参数网格 (8-12组合)
  ├─ REBALANCE_DAYS: [1, 2, 3]
  ├─ DECLINE_QUANTILE: [0.10, 0.18, 0.25]
  ├─ MAX_POSITIONS: [12, 18, 24]
  ├─ POSITION_CAP: [200K, 300K, 400K]
  └─ 选取Top-3 → Phase 2

Phase 2: 退出参数精细网格 (10-15组合)
  ├─ 固定Phase1最佳参数
  ├─ STOP_LOSS: [-0.06, -0.08, -0.10, -0.12]
  ├─ TAKE_PROFIT: [0.10, 0.13, 0.15, 0.18, 0.20]
  ├─ TRAILING_STOP_PCT: [-0.03, -0.05, -0.07]
  └─ 选取Top-3 → Phase 3

Phase 3: 多因子权重优化 (10-15组合)
  ├─ 固定前两阶段最佳参数
  ├─ 引入5因子体系:
  │   f1: |ret_3d| (短期跌幅)  weight: [0, 0.5, 1, 2]
  │   f2: |ret_5d| (中期跌幅)  weight: [1] (anchor=1)
  │   f3: |ret_10d| (长期跌幅) weight: [0, 0.5, 1]
  │   f4: RSI_oversold (40-RSI clipped) weight: [0, 0.5, 1, 2]
  │   f5: vol_ratio (量比)     weight: [0, 0.3, 0.5, 1]
  │   f6: reversal_bar (日内反转强度) weight: [0, 0.5, 1]
  │   sector_boost: [0, 0.5, 1] (板块动量权重)
  └─ 选取Top-3 → Phase 4

Phase 4: 风控精细调参 (8-12组合)
  ├─ MAX_SECTOR_EXPOSURE: [0.3, 0.4, 0.5, None]
  ├─ MIN_SCORE_THRESHOLD: [0, 0.02, 0.04]
  ├─ CASH_RESERVE: [0, 0.1, 0.2]
  └─ 输出最终最佳参数
```

### 多因子复合评分公式

```
raw_score = w1*|ret_3d| + w2*|ret_5d| + w3*|ret_10d| 
          + w4*RSI_oversold + w5*vol_ratio 
          + w6*reversal_bar + w7*sector_boost
          
score = raw_score * MONTE_CARLO_discount(vol_20d, ret_vol_corr)
```

### 新增信号过滤

1. **日内反转强度 (reversal_bar):** (close-low)/(high-low) — 收盘靠近低点=强反转潜力
2. **成交量确认 (vol_ratio):** 当日成交量/20日均量 > 1.2
3. **波动率惩罚:** vol_20d过高 → score折扣
4. **市场环境过滤:** 中证1000指数方向 (可选)

### 风控增强

1. **最大行业暴露:** 单行业仓位占比 ≤ 40%
2. **最低分数阈值:** score < MIN_SCORE → 不入场
3. **现金预留:** 保持10%现金应对机会
4. **止损随波动率调整:** stop_loss = base_stop * (vol_20d / median_vol)

### 已知风险

| 风险 | 缓解 |
|------|------|
| 过度拟合2025-05→2026-04区间 | 加入WALK_FORWARD验证(可选) |
| 网格搜索局部最优 | Phase间从Top-3而非仅Top-1出发 |
| 5000股回测性能 | 使用Sina parquet加速(如已就绪)，或限制候选池 |
| 信号稀疏性(低波动期) | MIN_POSITIONS fallback机制 |
| 行业映射覆盖率 | 使用data_common.get_industry_map()（4939股覆盖） |

### 输出格式

每轮优化输出:
```
---OPT_ROUND <N>---
best_params: {param: value, ...}
best_metrics: {ann, sharpe, mdd, wr, ...}
top3: [{params, metrics}, ...]
---END_ROUND---
```

最终输出:
```
---FINAL_RESULT---
best_params: {...}
best_metrics: {...}
total_rounds: N
total_backtests: M
---END_RESULT---
```

## 实施步骤

### 文件结构
```
strategy_reversal_opt.py  ← 主文件(修改)
  ├─ class OptConfig: 参数空间定义 + 最佳参数存储
  ├─ class ReversalBacktest: 回测引擎(已有，微调)
  ├─ def compute_factor_score(): 多因子评分(新增)
  ├─ def run_single_backtest(): 单次回测(重构自main)
  ├─ def optimize_phase(): 单阶段优化(新增)
  ├─ def main_optimize(): 主优化循环(新增)
  └─ if __name__: 入口(修改)
```

### TDD测试计划

测试文件: `test_strategy_reversal_opt.py`

测试用例:
1. `test_opt_config_exists` — OptConfig类存在且包含参数空间
2. `test_factor_score_shape` — compute_factor_score返回正确shape
3. `test_factor_score_weights` — 权重参数正确应用
4. `test_no_future_leak` — 因子计算无未来信息泄漏
5. `test_single_backtest_runs` — run_single_backtest正常完成
6. `test_optimization_output` — optimize_phase输出正确格式
7. `test_leverage_is_one` — LEVERAGE=1.0不变
8. `test_date_range` — 回测区间2025-05到2026-04

## 执行约定

1. 每个Phase必须先跑完所有组合再分析
2. 每轮输出完整指标(年化/夏普/回撤/胜率/交易次数)
3. 多目标优化: 年化优先，胜率45-55%约束内最大化年化
4. 如Phase间无改善(年化提升<5%)，提前终止并报告
5. 所有修改限于strategy_reversal_opt.py单文件
