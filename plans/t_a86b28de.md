# R2-A 代码优化计划

## 任务概览
- 任务ID: t_a86b28de
- 源文件: /home/pebynn/quant/evo_optimizer/strategy_momentum.py
- 输出文件: /home/pebynn/quant/evo_optimizer/round2_A_code.py
- 工作目录: /home/pebynn/quant/evo_optimizer/

## R1-A 回测基线
| 指标 | 值 | 目标 |
|------|-----|------|
| 年化回报 | 235.67% | ≥300% |
| 胜率 | 51.2% | 45-55% ✓ |
| 最大回撤 | -31.91% | - |
| 交易笔数 | 868 | - |
| 硬止损触发 | 38.5% (334/868) | <30% |
| 平均亏损 | -6.84% | - |
| 平均盈利 | +9.65% | - |
| 盈亏比 | 1.41:1 | >1.8:1 |
| 追踪止盈触发 | 46.8% (406次) | - |

## 根因分析
1. **硬止损过宽(8%)**: 触发率38.5%，每笔亏损-6.84%，侵蚀大量利润。缩小20-30%可减少触发并降低单笔损失。
2. **追踪止盈距离固定(4%)**: 46.8%触发率说明止盈过于激进。浮动盈利达8%后用ATR动态追踪可以更灵活地保护利润。
3. **should_enter缺少成交量检查**: MIN_VOL_20D已定义但未在should_enter中使用。低成交量股票容易产生噪声信号。
4. **缺少波动率过滤**: 极高波动率(ATR>8%)的股票假突破多，应排除。

## 设计方案

### 方案选择

#### 1. 硬止损优化 (HARD_STOP)
**方案A**: 从8%降至6%（25%缩减，中间值）
**方案B**: 从8%降至5%（37.5%缩减，激进）
**选择**: 方案A (HARD_STOP=0.06)
**理由**: 25%缩减在20-30%范围内；6%是-5%/-6%建议中的保守选择，避免过度紧止损导致频繁触发。
**风险**: 止损过紧可能在正常波动中被震出，需配合成交量过滤降低假信号。

#### 2. 动态追踪止盈
**方案A**: 固定缩小TRAILING_DISTANCE (4%→3%)
**方案B**: ATR动态追踪 — 盈利>8%后用ATR*1.5作为追踪距离，最小3%
**选择**: 方案B
**理由**: 任务明确要求"ATR*1.5"。高波动股票ATR大→追踪距离大→让利润奔跑；低波动ATR小→追踪紧→锁定利润。比固定距离更智能。
**实现**: TRAILING_ACTIVATE保持0.08；新增TRAILING_ATR_MULT=1.5；动态距离=max(ATR*1.5, 0.03)
**风险**: ATR计算基于14日历史波动，极端行情可能滞后；最小3%地板防止过度追踪。

#### 3. 低质量信号过滤
**方案A**: 仅在should_enter中加入vol_ratio检查
**方案B**: should_enter中加入vol_ratio + atr14_pct双重过滤
**选择**: 方案B
**理由**: 成交量+波动率双重过滤更全面。成交量过低=无人关注；波动率过高=噪声主导。
**新增过滤条件**:
- turnover_ratio > 0.5 (成交额不能低于20日均值50%)
- atr14_pct < 0.08 (ATR不能超过8%，排除极端波动股)
**风险**: 过滤过严可能导致候选池不足；通过放宽ret_5d下限(-0.03→-0.04)补偿。

#### 4. 辅助优化
- N_DROP: 5→7 (更快剔除排名下降的持仓，让资金流向更强信号)
- ret_5d下限: -0.03→-0.04 (配合新过滤条件，避免候选池过小)

### 替代方案（已排除）
- ATR_STOP_MULT调整: 当前2.0已合理，不需改动
- LEVERAGE改变: 铁律禁止(LEVERAGE=1.0)
- TOP_N改变: 10已足够分散
- 完全移除硬止损: 会导致mdd失控

## 参数变更汇总
| 参数 | R1值 | R2值 | 变更 |
|------|------|------|------|
| HARD_STOP | 0.08 | 0.06 | -25% |
| TRAILING_ACTIVATE | 0.08 | 0.08 | 不变 |
| TRAILING_DISTANCE | 0.04 | 删除 | 改为动态 |
| TRAILING_ATR_MULT | - | 1.5 | 新增 |
| TRAILING_MIN_DIST | - | 0.03 | 新增 |
| N_DROP | 5 | 7 | +40% |
| MIN_RET_5D | -0.03 | -0.04 | 放宽 |
| turnover过滤 | 未使用 | >0.5 | 新增 |
| atr14_pct上限 | 未使用 | <0.08 | 新增 |

## TDD 测试计划
测试文件: /home/pebynn/quant/evo_optimizer/tests/test_round2_A.py

### 测试用例
1. **test_hard_stop_reduced**: 验证HARD_STOP=0.06，模拟亏损达到-6%触发止损
2. **test_dynamic_trailing_atr**: 验证盈利>8%后使用ATR*1.5追踪距离
3. **test_trailing_min_floor**: 验证即使ATR极小，追踪距离不低于3%
4. **test_volume_filter_blocks_low_turnover**: turnover_ratio<0.5时should_enter返回False
5. **test_atr_filter_blocks_high_volatility**: atr14_pct>0.08时should_enter返回False
6. **test_n_drop_increased**: N_DROP=7，验证超过N_DROP个持仓被剔除
7. **test_no_future_function**: 验证所有计算仅使用历史数据

## 实施步骤
1. 复制strategy_momentum.py → round2_A_code.py
2. 修改参数配置区
3. 重写追踪止盈逻辑（动态ATR）
4. 增强should_enter函数
5. 语法检查
6. 运行TDD测试
7. 端到端回测验证

## 风险矩阵
| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 紧止损增加whiplash | 中 | 中 | ATR*1.5动态追踪提供额外缓冲 |
| 过滤过严候选不足 | 低 | 中 | 放宽ret_5d下限+增加N_DROP |
| ATR计算在停牌/新股上为NaN | 中 | 低 | should_enter已有np.isnan检查 |
| 动态追踪复杂度引入bug | 低 | 高 | TDD覆盖+代码review |
