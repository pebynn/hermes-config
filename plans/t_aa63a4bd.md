# R2-A Strategy A v2 增量优化计划

## 任务标识
- **Task ID**: t_aa63a4bd
- **策略文件**: `/home/pebynn/quant/strategies/strategy_a_momentum/strategy_v2.py`
- **测试文件**: `/home/pebynn/quant/strategies/strategy_a_momentum/test_strategy_v2.py`
- **时间**: 2026-05-13

## R1 基线 (target range 2026-01-06 ~ 2026-05-13)
| 指标 | 值 | 目标 | 状态 |
|:--|:--|:--|:--|
| 年化收益 | 81.52% | 150% | ❌ |
| 胜率 | 37.7% | 45% | ❌ |
| 夏普 | 4.55 | - | ✅ |
| 回撤 | -2.95% | - | ✅ |
| 交易数 | 77 | - | - |
| 参数数 | 7 | ≤5 | ❌ |

退出原因分布:
- stop (硬止损-8%): 40.3% (31笔) — **最大拖累**
- trail (移动止盈): 33.8% (26笔, avg +7.81%, WR 73.1%) — **最大贡献者**
- end (期末): 13.0% (10笔)
- jan_apr (空仓退出): 7.8% (6笔, avg -0.8%)
- drop (换仓淘汰): 5.2% (4笔)

IC权重: flow=0.412, mom=0.353, turn=0.059, vol=0.176 — **turn因子接近零权重**

## 设计方案

### 改动1: 止损阈值 8% → 10%
- **方案选择**: STOP_LOSS_V2 = 0.08 → 0.10
- **理由**: 40.3%交易被-8%止损出局，WR=0 at stop。放宽容忍度至10%减少过早止损
- **替代方案**: 12% — 可能过于宽松，回撤加深
- **风险**: 单笔最大亏损从-8%增至-10%，可能加深最大回撤

### 改动2: 移动止盈收紧 8% → 6%
- **方案选择**: TRAILING_STOP = 0.08 → 0.06
- **理由**: 移动止盈是最大利润贡献者(WR 73.1%)，收紧可保留更多利润
- **替代方案**: 保持8%不变 — 错过利润保护
- **风险**: 过早止盈可能错失更大涨幅

### 改动3: 移除1月/4月空仓期
- **方案选择**: JAN_APR_EMPTY_V2 = True → False
- **理由**: 仅6笔jan_apr退出(avg -0.8%)，机会成本可能大于保护效果
- **替代方案**: 缩短空仓期为仅1月前两周
- **风险**: 1月/4月季节性回撤可能重现

### 改动4: 删除turn因子
- **方案选择**: 从因子计算/IC权重/综合得分中完全移除turn
- **理由**: IC权重仅0.059(接近零)，实际未贡献信号
- **具体改动**:
  a. compute_factors_v2: 移除turnover计算及'turn'列输出
  b. compute_rolling_ic_weights: 3因子(flow/mom/vol)替代4因子
  c. compute_composite_score_v2: 移除turn项
  d. default_weights: flow=0.50, mom=0.35, vol=0.15
  e. _update_ic: 移除turn因子IC
  f. ic_history: 仅3个key
- **替代方案**: 保留turn但降权 — 无效，权重已接近零
- **风险**: turnover可能在特定市场环境有用(如放量突破)，但当前权重0.059说明作用微乎其微

### 改动5: 入场动量强度过滤
- **方案选择**: 买入时检查候选股的5日动量(5日收益率)是否超过阈值
- **具体实现**: 
  - 新增常量 MOM_ENTRY_THRESHOLD = 0.02 (5日收益>2%才可买入)
  - 在买入逻辑中: 检查 xt 中该股票5日收盘收益是否>阈值
  - 需要新增一个辅助函数 `check_momentum_threshold(xt, code, threshold)`
- **替代方案**: 用成交量过滤(5日成交量>20日均量) — 成交量过滤可能与turn类似接近无效
- **风险**: 阈值过高(如5%)可能严重减少交易机会；选择保守的2%起步

### 改动6: 配置参数压缩 7→5
- **当前config**: top_n, stop_loss, trailing_stop, portfolio_stop, ic_window, ic_temperature, jan_apr_empty = 7个
- **压缩方案**:
  - 移除 jan_apr_empty (改动3将其固定为False，不再暴露为配置项)
  - 将 ic_temperature 移出 config dict，保持为 hardcoded 常量
  - 最终config: top_n, stop_loss, trailing_stop, portfolio_stop, ic_window = **5个** ✅
- **注意**: ic_temperature 仍是常量但不出现在 config dict 中

### 改动7: 新增 --start/--end CLI参数
- **理由**: 任务要求 `python3 strategy_v2.py --start 2026-01-06 --end 2026-05-13` 可运行
- **实现**: 在 argparse 中增加 --start 和 --end 参数，运行时覆盖模块级常量

## 风险总览
| 风险 | 等级 | 缓解 |
|:--|:--|:--|
| 止损放宽→单笔亏损加深 | 中 | 收紧移动止盈部分抵消；回测验证回撤 |
| 移除turn→信息丢失 | 低 | IC权重0.059证明无信息量 |
| 收紧trailing→错失趋势利润 | 中 | 6%从8%下调保守，trail是核心利润源 |
| 移除空仓期→季节性风险 | 低 | 仅6笔交易受影响，收益影响小 |
| 动量过滤→交易减少 | 中 | 2%阈值保守，观测交易数变化 |

## 不修改的部分
- LEVERAGE_V2 = 1.0 🔒 铁律
- trailing_stop 机制本身 (已验证有效)
- IC权重机制 (已验证有效)
- TOP_N_V2 = 10
- VOL_WEIGHT_DEFAULT 逻辑 (调整至3因子后重分配)
- NAV计算方式 (已验证prev_close tracking正确)
- compute_factors_v2 的 flow/mom/vol 计算逻辑

## 实施顺序
1. 修改常量定义
2. 删除turn因子 (factor computation + IC + scoring + weights)
3. 新增动量过滤逻辑
4. 新增 --start/--end CLI
5. 更新测试用例
6. 运行测试 (TDD → GREEN)
7. 运行目标区间回测验证
